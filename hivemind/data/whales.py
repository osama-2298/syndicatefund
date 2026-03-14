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
        Check all known exchange wallets and compute aggregate flow signals.
        Inflows to exchanges = selling pressure.
        Outflows from exchanges = accumulation.
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

        # Assessment
        # Note: without historical baseline, we can only report current state
        # In production, we'd compare against previous cycle's reading
        return {
            "exchange_balances": balances,
            "total_exchange_btc": round(total_exchange_btc, 2),
            "num_wallets_tracked": len(balances),
            "assessment": (
                "Exchange reserves tracked. Compare against previous cycles "
                "to determine if BTC is flowing in (selling pressure) or out (accumulation)."
            ),
        }
