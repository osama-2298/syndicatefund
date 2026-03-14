"""
Whale wallet tracking — Blockchain.info, free, no auth.

Monitors known exchange and whale wallets for large BTC movements.
Exchange inflows = selling pressure. Exchange outflows = accumulation.

Known wallet addresses curated from public blockchain data.
"""

from __future__ import annotations

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()

BASE_URL = "https://blockchain.info"

# Known major exchange wallets (legacy format — bc1q addresses return 404)
EXCHANGE_WALLETS: dict[str, str] = {
    "Binance Hot": "34xp4vRoCGJym3xR7yCVPFHoCNxv4Twseo",
    "Binance Cold": "3LYJfcfHPXYJreMsASk2jkn69LWEYKzexb",
    "Bitfinex": "3D2oetdNuZUqQHPJmcMDDHYoqkyNVsFk9r",
    "Kraken": "3AfAJRiVqEiLnQ8FodJg37WiNJkFuGEjMZ",
}

# Satoshi in a BTC
SATOSHI = 100_000_000


class WhaleTracker:
    """Tracks BTC whale wallets for flow signals."""

    def __init__(self) -> None:
        self._client = httpx.Client(timeout=15.0)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> WhaleTracker:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, max=5))
    def get_wallet_balance(self, address: str) -> float:
        """Get BTC balance for an address."""
        resp = self._client.get(f"{BASE_URL}/q/addressbalance/{address}")
        resp.raise_for_status()
        satoshis = int(resp.text.strip())
        return satoshis / SATOSHI

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, max=5))
    def get_recent_transactions(self, address: str, limit: int = 5) -> list[dict]:
        """Get recent transactions for a wallet."""
        resp = self._client.get(
            f"{BASE_URL}/rawaddr/{address}",
            params={"limit": limit},
        )
        resp.raise_for_status()
        data = resp.json()

        txs = []
        for tx in data.get("txs", [])[:limit]:
            # Calculate net flow for this address
            inputs_from_addr = sum(
                inp.get("prev_out", {}).get("value", 0)
                for inp in tx.get("inputs", [])
                if inp.get("prev_out", {}).get("addr") == address
            )
            outputs_to_addr = sum(
                out.get("value", 0)
                for out in tx.get("out", [])
                if out.get("addr") == address
            )
            net_satoshis = outputs_to_addr - inputs_from_addr
            net_btc = net_satoshis / SATOSHI

            txs.append({
                "hash": tx.get("hash", "")[:16] + "...",
                "time": tx.get("time", 0),
                "net_btc": round(net_btc, 4),
                "fee_btc": round(tx.get("fee", 0) / SATOSHI, 6),
            })

        return txs

    def get_exchange_flows(self) -> dict:
        """
        Check exchange wallets and compare against PREVIOUS cycle to detect flow direction.
        Stores history in a JSON file for cycle-to-cycle comparison.
        """
        balances: dict[str, float] = {}
        total_exchange_btc = 0.0

        for name, address in EXCHANGE_WALLETS.items():
            try:
                balance = self.get_wallet_balance(address)
                balances[name] = round(balance, 2)
                total_exchange_btc += balance
            except Exception as e:
                logger.warning("whale_balance_failed", wallet=name, error=str(e))

        total_exchange_btc = round(total_exchange_btc, 2)

        # Load previous readings and compute delta
        history = self._load_history()
        previous_total = history[-1]["total"] if history else None
        delta_btc = round(total_exchange_btc - previous_total, 2) if previous_total is not None else None

        # Determine flow direction
        if delta_btc is None:
            flow_direction = "FIRST_READING"
            assessment = f"First reading: {total_exchange_btc:,.0f} BTC on exchanges. No prior cycle to compare."
        elif delta_btc < -100:
            flow_direction = "OUTFLOW"
            assessment = f"Exchange reserves DOWN {abs(delta_btc):,.0f} BTC from last cycle = ACCUMULATION (bullish signal)"
        elif delta_btc > 100:
            flow_direction = "INFLOW"
            assessment = f"Exchange reserves UP {delta_btc:,.0f} BTC from last cycle = DISTRIBUTION (bearish signal)"
        else:
            flow_direction = "STABLE"
            assessment = f"Exchange reserves roughly stable ({delta_btc:+,.0f} BTC). No significant flow detected."

        # Save current reading to history
        from datetime import datetime, timezone
        history.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total": total_exchange_btc,
            "balances": balances,
        })
        # Keep last 50 readings
        if len(history) > 50:
            history = history[-50:]
        self._save_history(history)

        return {
            "exchange_balances": balances,
            "total_exchange_btc": total_exchange_btc,
            "previous_total_btc": previous_total,
            "delta_btc": delta_btc,
            "flow_direction": flow_direction,
            "num_wallets_tracked": len(balances),
            "cycles_tracked": len(history),
            "assessment": assessment,
        }

    def _load_history(self) -> list[dict]:
        """Load whale balance history from JSON file."""
        import json
        from pathlib import Path
        path = Path("data/whale_history.json")
        if not path.exists():
            return []
        try:
            return json.loads(path.read_text())
        except Exception:
            return []

    def _save_history(self, history: list[dict]) -> None:
        """Save whale balance history to JSON file."""
        import json
        from pathlib import Path
        path = Path("data/whale_history.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(history, indent=2, default=str))
