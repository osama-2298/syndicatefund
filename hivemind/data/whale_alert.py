"""Whale Alert API — tracks large crypto transactions across all blockchains.

Free tier: 10 requests/minute, basic entity attribution.
Endpoint: GET https://api.whale-alert.io/v1/transactions

Massive upgrade from our current 3-wallet approach — covers ALL large transactions
with sender/receiver entity labels (exchange, fund, unknown).
"""

import time
from datetime import datetime, timezone
import httpx
import structlog

logger = structlog.get_logger()

# Free API key (register at whale-alert.io for your own)
# For now, this works without a key for basic queries
WHALE_ALERT_BASE = "https://api.whale-alert.io/v1"


class WhaleAlertClient:
    """Track large crypto transactions via Whale Alert."""

    def __init__(self, api_key: str = ""):
        self._client = httpx.Client(timeout=15.0)
        self._api_key = api_key

    def get_recent_transactions(self, min_value_usd: int = 1_000_000,
                                 currency: str = "bitcoin",
                                 limit: int = 50) -> dict:
        """Get recent large transactions.

        Args:
            min_value_usd: Minimum transaction value in USD
            currency: "bitcoin", "ethereum", "tether", etc.
            limit: Max number of transactions

        Returns:
            {
                "transactions": list of {hash, from_owner, to_owner, amount, amount_usd, ...},
                "exchange_inflows_usd": float,  # Money going TO exchanges (sell pressure)
                "exchange_outflows_usd": float,  # Money leaving exchanges (accumulation)
                "net_flow_direction": "ACCUMULATION" | "DISTRIBUTION" | "NEUTRAL",
                "whale_activity_level": "EXTREME" | "HIGH" | "MODERATE" | "LOW",
                "count": int,
            }
        """
        # Calculate start time (last 1 hour)
        start = int(time.time()) - 3600

        params = {
            "start": start,
            "min_value": min_value_usd,
            "limit": limit,
            "currency": currency,
        }
        if self._api_key:
            params["api_key"] = self._api_key

        try:
            resp = self._client.get(f"{WHALE_ALERT_BASE}/transactions", params=params)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning("whale_alert_fetch_failed", error=str(e))
            return self._empty_result()

        transactions = data.get("transactions", [])
        if not transactions:
            return self._empty_result()

        exchange_in = 0.0
        exchange_out = 0.0
        parsed = []

        for tx in transactions:
            amount_usd = tx.get("amount_usd", 0)
            from_owner = tx.get("from", {}).get("owner_type", "unknown")
            to_owner = tx.get("to", {}).get("owner_type", "unknown")
            from_name = tx.get("from", {}).get("owner", "unknown")
            to_name = tx.get("to", {}).get("owner", "unknown")

            # Track exchange flows
            if to_owner == "exchange":
                exchange_in += amount_usd  # Sending TO exchange = likely selling
            if from_owner == "exchange":
                exchange_out += amount_usd  # Taking FROM exchange = accumulation

            parsed.append({
                "amount": tx.get("amount", 0),
                "amount_usd": amount_usd,
                "from_owner": from_name,
                "to_owner": to_name,
                "from_type": from_owner,
                "to_type": to_owner,
                "blockchain": tx.get("blockchain", ""),
                "symbol": tx.get("symbol", ""),
            })

        total = exchange_in + exchange_out
        if total > 0:
            if exchange_out > exchange_in * 1.5:
                direction = "ACCUMULATION"
            elif exchange_in > exchange_out * 1.5:
                direction = "DISTRIBUTION"
            else:
                direction = "NEUTRAL"
        else:
            direction = "NEUTRAL"

        # Activity level
        if total > 500_000_000:
            level = "EXTREME"
        elif total > 100_000_000:
            level = "HIGH"
        elif total > 20_000_000:
            level = "MODERATE"
        else:
            level = "LOW"

        return {
            "transactions": parsed[:20],
            "exchange_inflows_usd": round(exchange_in, 2),
            "exchange_outflows_usd": round(exchange_out, 2),
            "net_flow_direction": direction,
            "whale_activity_level": level,
            "count": len(transactions),
        }

    def _empty_result(self):
        return {
            "transactions": [],
            "exchange_inflows_usd": 0,
            "exchange_outflows_usd": 0,
            "net_flow_direction": "UNKNOWN",
            "whale_activity_level": "UNKNOWN",
            "count": 0,
        }

    def close(self):
        self._client.close()
