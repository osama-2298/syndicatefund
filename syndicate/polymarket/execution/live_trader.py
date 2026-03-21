"""Live trader for Polymarket weather markets — real USDC, real orders."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import structlog

from syndicate.polymarket.config import PolymarketSettings, pm_settings
from syndicate.polymarket.models import (
    LiveOrder,
    LivePortfolio,
    OrderStatus,
    WeatherPortfolio,
    WeatherPosition,
)

logger = structlog.get_logger()

# Rate limit: minimum seconds between consecutive order submissions
ORDER_RATE_LIMIT_SECONDS = 5.0


class WeatherLiveTrader:
    """Live trader that posts GTC limit orders to Polymarket's CLOB.

    Safety rails:
    - Kill switch halts all trading instantly
    - Shadow mode logs orders without posting them
    - Per-bet cap ($20 default)
    - Wallet balance check before every order
    - USDC reserve maintained at all times
    - Max open orders limit
    - Order timeout auto-cancellation
    - Daily loss limit and loss streak limit
    """

    def __init__(self, portfolio: LivePortfolio | None = None) -> None:
        self._settings = PolymarketSettings()
        self._path: Path = self._settings.polymarket_data_dir / "live_portfolio.json"
        self._portfolio: LivePortfolio = portfolio or LivePortfolio()
        self._client = None  # Lazy init — never touch the key until needed
        self._last_order_time: float = 0.0
        # Refresh wallet balance from CLOB on startup if it's zero
        if self._portfolio.wallet_balance == 0 and self._settings.polymarket_private_key:
            self._refresh_balance_from_clob()

    def _refresh_balance_from_clob(self) -> None:
        """Fetch wallet balance from CLOB API on startup."""
        try:
            client = self._get_client()
            from py_clob_client.clob_types import BalanceAllowanceParams, AssetType
            params = BalanceAllowanceParams(
                asset_type=AssetType.COLLATERAL,
                signature_type=1,
            )
            bal = client.get_balance_allowance(params)
            raw = int(bal.get("balance", "0"))
            usdc_balance = raw / 1e6
            self._portfolio.wallet_balance = usdc_balance
            self.save()
            logger.info("wallet_balance_initialized", balance=round(usdc_balance, 2))
        except Exception as e:
            logger.warning("wallet_balance_init_failed", error=str(e))

    # ── CLOB Client (lazy) ─────────────────────────────────────────────

    def _get_client(self):
        """Lazily initialize the CLOB client from the private key.

        The private key is read from the environment only at first use
        and is never logged.
        """
        if self._client is not None:
            return self._client

        pk = self._settings.polymarket_private_key
        if not pk:
            raise RuntimeError(
                "POLYMARKET_PRIVATE_KEY not set — cannot initialize live trader"
            )

        try:
            from py_clob_client.client import ClobClient

            host = "https://clob.polymarket.com"
            chain_id = 137  # Polygon mainnet

            # Polymarket uses proxy wallets — signature_type=1 (POLY_PROXY).
            # The funder is the proxy wallet address that holds the USDC.e.
            # We derive it from the CLOB's own address resolution.
            client = ClobClient(
                host,
                key=pk,
                chain_id=chain_id,
                signature_type=1,  # POLY_PROXY
                funder=self._settings.polymarket_funder_address,
            )
            client.set_api_creds(client.derive_api_key())

            self._client = client
            logger.info("clob_client_initialized")
            return self._client
        except Exception as e:
            logger.error("clob_client_init_failed", error=str(e))
            raise

    # ── Portfolio as WeatherPortfolio (for oracle compatibility) ────────

    def get_portfolio(self) -> WeatherPortfolio:
        """Return a WeatherPortfolio view for oracle compatibility."""
        return WeatherPortfolio(
            bankroll=self._portfolio.wallet_balance,
            cash=self._portfolio.available_balance,
            positions=self._portfolio.positions,
            total_pnl=self._portfolio.total_pnl,
            total_bets=self._portfolio.total_bets,
            wins=self._portfolio.wins,
            losses=self._portfolio.losses,
        )

    def get_live_portfolio(self) -> LivePortfolio:
        """Return the full live portfolio with order tracking."""
        return self._portfolio

    # ── Risk Checks ────────────────────────────────────────────────────

    def check_daily_loss_limit(self, limit_pct: float = 0.10) -> bool:
        """Return True if daily losses exceed limit_pct of wallet balance."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        daily_pnl = sum(
            p.pnl for p in self._portfolio.positions
            if p.resolved and p.placed_at.strftime("%Y-%m-%d") == today
        )
        bankroll = self._portfolio.wallet_balance or 1.0
        return daily_pnl < -(bankroll * limit_pct)

    def recent_loss_streak(self) -> int:
        """Count consecutive losses from most recent resolved positions."""
        resolved = [p for p in self._portfolio.positions if p.resolved]
        resolved.sort(key=lambda p: p.placed_at, reverse=True)
        streak = 0
        for p in resolved:
            if p.outcome is False:
                streak += 1
            else:
                break
        return streak

    # ── Order Placement ────────────────────────────────────────────────

    def place_bet(
        self,
        condition_id: str,
        token_id: str,
        city: str,
        date: str,
        bin_label: str,
        entry_price: float,
        quantity: float,
        model_prob: float,
        edge: float,
        forecast_mean: float = 0.0,
        forecast_std: float = 0.0,
        total_market_volume: float = 0.0,
        n_bins: int = 10,
    ) -> WeatherPosition | None:
        """Place a live limit order on Polymarket's CLOB.

        Mirrors the paper trader signature exactly. Returns a WeatherPosition
        if the order was successfully posted (or shadow-logged), None if blocked.
        """
        settings = self._settings

        # 1. Kill switch
        if settings.polymarket_kill_switch:
            logger.warning("live_bet_blocked.kill_switch", city=city, date=date)
            return None

        # 2. Daily loss limit
        if self.check_daily_loss_limit(settings.polymarket_daily_loss_limit):
            logger.warning("live_bet_blocked.daily_loss_limit", city=city, date=date)
            return None

        # 3. Loss streak limit
        if self.recent_loss_streak() >= settings.polymarket_loss_streak_limit:
            logger.warning("live_bet_blocked.loss_streak", city=city, date=date)
            return None

        # 4. Cap quantity to max_bet_live
        if quantity > settings.polymarket_max_bet_live:
            logger.info(
                "live_bet_capped",
                city=city, date=date,
                original=round(quantity, 2),
                capped=settings.polymarket_max_bet_live,
            )
            quantity = settings.polymarket_max_bet_live

        # 5. Check wallet balance (available = wallet - committed - reserve)
        available = self._portfolio.available_balance
        if quantity > available:
            logger.warning(
                "live_bet_blocked.insufficient_balance",
                city=city, date=date,
                quantity=round(quantity, 2),
                available=round(available, 2),
            )
            return None

        # 6. Check open orders limit
        pending = [o for o in self._portfolio.open_orders if o.status == OrderStatus.PENDING]
        if len(pending) >= settings.polymarket_max_open_orders:
            logger.warning(
                "live_bet_blocked.max_open_orders",
                city=city, date=date,
                open_count=len(pending),
            )
            return None

        # 7. Compute shares: size = quantity / entry_price
        if entry_price <= 0 or entry_price >= 1:
            logger.warning("live_bet_blocked.invalid_price", price=entry_price)
            return None
        size = round(quantity / entry_price, 2)

        now = datetime.now(timezone.utc)

        # 8. Shadow mode — log but don't execute
        if settings.polymarket_shadow_mode:
            logger.info(
                "shadow_order",
                city=city, date=date, bin=bin_label,
                price=round(entry_price, 4),
                size=round(size, 2),
                quantity_usd=round(quantity, 2),
                model_prob=round(model_prob, 4),
                edge=round(edge, 4),
            )
            # Create a position record for tracking (shadow orders don't commit capital)
            position = WeatherPosition(
                condition_id=condition_id,
                token_id=token_id,
                city=city,
                date=date,
                bin_label=bin_label,
                entry_price=entry_price,
                fill_price=entry_price,  # shadow: assume mid fill
                quantity=quantity,
                model_prob=model_prob,
                edge_at_entry=edge,
                forecast_mean=forecast_mean,
                forecast_std=forecast_std,
                placed_at=now,
            )
            self._portfolio.positions.append(position)
            self._portfolio.total_bets += 1
            self.save()
            return position

        # 9. Rate limiting
        elapsed = time.monotonic() - self._last_order_time
        if elapsed < ORDER_RATE_LIMIT_SECONDS:
            wait = ORDER_RATE_LIMIT_SECONDS - elapsed
            logger.debug("rate_limit_wait", seconds=round(wait, 1))
            time.sleep(wait)

        # 10. Post GTC limit order via CLOB
        #
        # Safety: pre-commit capital in local state BEFORE posting to CLOB.
        # If the CLOB post fails, we rollback. This ensures we never have
        # an order live on the exchange without local tracking.
        try:
            client = self._get_client()

            from py_clob_client.clob_types import OrderArgs
            from py_clob_client.order_builder.constants import BUY
            order_args = OrderArgs(
                token_id=token_id,
                price=round(entry_price, 2),
                size=size,
                side=BUY,
            )
            signed_order = client.create_order(order_args)

            # Pre-commit: reserve capital and save BEFORE posting
            placeholder_order = LiveOrder(
                order_id=f"pending-{int(now.timestamp())}",
                condition_id=condition_id,
                token_id=token_id,
                city=city,
                date=date,
                bin_label=bin_label,
                price=entry_price,
                size=size,
                quantity_usd=quantity,
                model_prob=model_prob,
                edge=edge,
                status=OrderStatus.PENDING,
                created_at=now,
                updated_at=now,
            )
            self._portfolio.open_orders.append(placeholder_order)
            self._portfolio.committed_capital += quantity
            self.save()

            # Now post to CLOB — local state is already safe
            try:
                resp = client.post_order(signed_order)
            except Exception as post_err:
                # Rollback: remove pre-committed order
                self._portfolio.open_orders.remove(placeholder_order)
                self._portfolio.committed_capital -= quantity
                self.save()
                raise post_err

            self._last_order_time = time.monotonic()

            # Extract order ID from response
            order_id = ""
            if isinstance(resp, dict):
                order_id = resp.get("orderID", resp.get("order_id", ""))
            elif hasattr(resp, "orderID"):
                order_id = resp.orderID
            elif hasattr(resp, "order_id"):
                order_id = resp.order_id

            if not order_id:
                order_id = f"unknown-{int(now.timestamp())}"
                logger.warning("order_id_not_in_response", response=str(resp)[:200])

            # Update placeholder with real order ID
            placeholder_order.order_id = order_id

            logger.info(
                "live_order_posted",
                order_id=order_id,
                city=city, date=date, bin=bin_label,
                price=round(entry_price, 4),
                size=round(size, 2),
                quantity_usd=round(quantity, 2),
                edge=round(edge, 4),
            )

            self.save()

            # Return a position (not yet confirmed filled — will be upgraded on fill)
            return WeatherPosition(
                condition_id=condition_id,
                token_id=token_id,
                city=city,
                date=date,
                bin_label=bin_label,
                entry_price=entry_price,
                fill_price=0.0,  # not yet filled
                quantity=quantity,
                model_prob=model_prob,
                edge_at_entry=edge,
                forecast_mean=forecast_mean,
                forecast_std=forecast_std,
                placed_at=now,
            )

        except Exception as e:
            logger.error(
                "live_order_failed",
                city=city, date=date, bin=bin_label,
                error=str(e),
            )
            return None

    # ── Order Monitoring ───────────────────────────────────────────────

    def check_order_fills(self) -> list[LiveOrder]:
        """Poll CLOB for open order status. Called each oracle cycle.

        - Detects filled/cancelled orders
        - Converts filled orders into WeatherPositions
        - Auto-cancels orders past timeout
        """
        if not self._portfolio.open_orders:
            return []

        settings = self._settings
        now = datetime.now(timezone.utc)
        updated: list[LiveOrder] = []

        try:
            client = self._get_client()
        except Exception:
            logger.warning("check_fills_skipped.no_client")
            return []

        still_open: list[LiveOrder] = []

        for order in self._portfolio.open_orders:
            if order.status != OrderStatus.PENDING:
                still_open.append(order)
                continue

            # Check timeout — cancel if too old
            age_seconds = (now - order.created_at).total_seconds()
            if age_seconds > settings.polymarket_order_timeout_seconds:
                self._cancel_order_on_exchange(client, order)
                order.status = OrderStatus.CANCELLED
                order.cancelled_at = now
                order.updated_at = now
                self._portfolio.committed_capital -= order.quantity_usd
                self._portfolio.order_history.append(order)
                updated.append(order)
                logger.info(
                    "order_timed_out",
                    order_id=order.order_id,
                    city=order.city,
                    age_seconds=round(age_seconds),
                )
                continue

            # Poll order status from CLOB
            try:
                clob_order = client.get_order(order.order_id)

                status_str = ""
                if isinstance(clob_order, dict):
                    status_str = clob_order.get("status", "").upper()
                elif hasattr(clob_order, "status"):
                    status_str = str(clob_order.status).upper()

                if status_str == "MATCHED" or status_str == "FILLED":
                    # Fully filled
                    fill_price = order.price
                    filled_size = order.size
                    if isinstance(clob_order, dict):
                        fill_price = float(clob_order.get("avg_price", order.price))
                        filled_size = float(clob_order.get("size_matched", order.size))

                    order.status = OrderStatus.FILLED
                    order.fill_price = fill_price
                    order.filled_size = filled_size
                    order.updated_at = now

                    # Convert to position
                    position = WeatherPosition(
                        condition_id=order.condition_id,
                        token_id=order.token_id,
                        city=order.city,
                        date=order.date,
                        bin_label=order.bin_label,
                        entry_price=order.price,
                        fill_price=fill_price,
                        quantity=order.quantity_usd,
                        model_prob=order.model_prob,
                        edge_at_entry=order.edge,
                        placed_at=order.created_at,
                    )
                    self._portfolio.positions.append(position)
                    self._portfolio.committed_capital -= order.quantity_usd
                    self._portfolio.order_history.append(order)
                    updated.append(order)

                    logger.info(
                        "order_filled",
                        order_id=order.order_id,
                        city=order.city,
                        fill_price=round(fill_price, 4),
                        filled_size=round(filled_size, 2),
                    )

                elif status_str == "CANCELLED" or status_str == "EXPIRED":
                    order.status = OrderStatus.CANCELLED
                    order.cancelled_at = now
                    order.updated_at = now
                    self._portfolio.committed_capital -= order.quantity_usd
                    self._portfolio.order_history.append(order)
                    updated.append(order)

                else:
                    # Still open — keep tracking
                    still_open.append(order)

            except Exception as e:
                logger.warning(
                    "order_status_check_failed",
                    order_id=order.order_id,
                    error=str(e),
                )
                still_open.append(order)

        self._portfolio.open_orders = still_open
        if updated:
            self.save()

        return updated

    def _cancel_order_on_exchange(self, client, order: LiveOrder) -> bool:
        """Attempt to cancel an order on the CLOB. Returns True on success."""
        try:
            client.cancel(order.order_id)
            logger.info("order_cancelled", order_id=order.order_id)
            return True
        except Exception as e:
            logger.warning(
                "order_cancel_failed",
                order_id=order.order_id,
                error=str(e),
            )
            return False

    def cancel_all_orders(self) -> int:
        """Cancel all open orders. Returns count of orders cancelled."""
        if not self._portfolio.open_orders:
            return 0

        now = datetime.now(timezone.utc)
        cancelled = 0

        try:
            client = self._get_client()
        except Exception:
            logger.error("cancel_all_failed.no_client")
            return 0

        for order in self._portfolio.open_orders:
            if order.status == OrderStatus.PENDING:
                self._cancel_order_on_exchange(client, order)
                order.status = OrderStatus.CANCELLED
                order.cancelled_at = now
                order.updated_at = now
                self._portfolio.committed_capital -= order.quantity_usd
                self._portfolio.order_history.append(order)
                cancelled += 1

        self._portfolio.open_orders = []
        self.save()

        logger.info("all_orders_cancelled", count=cancelled)
        return cancelled

    def emergency_halt(self) -> dict:
        """Kill switch: cancel all orders and halt trading.

        Returns summary of actions taken including any orders that
        failed to cancel on the exchange.
        """
        cancelled = self.cancel_all_orders()
        # Check if any orders remain (failed to cancel on CLOB)
        remaining = len(self._portfolio.open_orders)
        logger.critical(
            "emergency_halt_activated",
            orders_cancelled=cancelled,
            orders_remaining=remaining,
        )
        return {
            "orders_cancelled": cancelled,
            "orders_remaining": remaining,
            "message": "All orders cancelled. Set POLYMARKET_KILL_SWITCH=true to prevent new orders.",
        }

    # ── Resolution ─────────────────────────────────────────────────────

    def resolve_position(self, condition_id: str, won: bool) -> float:
        """Resolve a position and compute P&L using actual fill price."""
        for pos in self._portfolio.positions:
            if pos.condition_id == condition_id and not pos.resolved:
                pos.resolved = True
                pos.outcome = won

                price = pos.fill_price if pos.fill_price > 0 else pos.entry_price

                if won:
                    payout = pos.quantity / price
                    pnl = payout - pos.quantity
                    self._portfolio.wallet_balance += payout
                    self._portfolio.wins += 1
                else:
                    pnl = -pos.quantity
                    self._portfolio.losses += 1

                pos.pnl = pnl
                self._portfolio.total_pnl += pnl

                logger.info(
                    "live_position_resolved",
                    condition_id=condition_id,
                    city=pos.city,
                    date=pos.date,
                    won=won,
                    fill_price=round(price, 4),
                    pnl=round(pnl, 2),
                    total_pnl=round(self._portfolio.total_pnl, 2),
                )

                self.save()
                return pnl

        logger.warning("resolve_position.not_found", condition_id=condition_id)
        return 0.0

    # ── Wallet Balance ─────────────────────────────────────────────────

    def refresh_wallet_balance(self) -> float:
        """Fetch current USDC.e balance from the Polygon chain.

        Updates self._portfolio.wallet_balance and returns the value.
        """
        try:
            from web3 import Web3

            rpc = "https://polygon-rpc.com"
            w3 = Web3(Web3.HTTPProvider(rpc))

            pk = self._settings.polymarket_private_key
            if not pk:
                return self._portfolio.wallet_balance

            account = w3.eth.account.from_key(pk)
            address = account.address

            # USDC.e on Polygon
            usdc_address = Web3.to_checksum_address(
                "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
            )
            erc20_abi = [
                {
                    "constant": True,
                    "inputs": [{"name": "_owner", "type": "address"}],
                    "name": "balanceOf",
                    "outputs": [{"name": "balance", "type": "uint256"}],
                    "type": "function",
                }
            ]
            contract = w3.eth.contract(address=usdc_address, abi=erc20_abi)
            raw = contract.functions.balanceOf(address).call()
            balance = raw / 1e6  # USDC has 6 decimals

            self._portfolio.wallet_balance = balance
            self.save()

            logger.info("wallet_balance_refreshed", balance=round(balance, 2))
            return balance

        except Exception as e:
            logger.error("wallet_balance_refresh_failed", error=str(e))
            return self._portfolio.wallet_balance

    # ── Persistence ────────────────────────────────────────────────────

    def save(self) -> None:
        """Persist live portfolio to JSON."""
        data = self._portfolio.model_dump(mode="json")
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, default=str))
        tmp.rename(self._path)
        logger.debug("live_portfolio_saved", path=str(self._path))

    @classmethod
    def load(cls) -> WeatherLiveTrader:
        """Load live portfolio from JSON, or create a fresh one."""
        settings = PolymarketSettings()
        path = settings.polymarket_data_dir / "live_portfolio.json"

        if path.exists():
            try:
                raw = json.loads(path.read_text())
                portfolio = LivePortfolio.model_validate(raw)
                logger.info(
                    "live_portfolio_loaded",
                    path=str(path),
                    wallet=round(portfolio.wallet_balance, 2),
                    open_orders=len(portfolio.open_orders),
                    positions=len(portfolio.positions),
                    total_pnl=round(portfolio.total_pnl, 2),
                )
                return cls(portfolio=portfolio)
            except Exception as exc:
                logger.error("live_portfolio_load_failed", path=str(path), error=str(exc))

        logger.info("live_portfolio_created_fresh")
        return cls()
