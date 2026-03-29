"""Binance Futures liquidation data — the most violent signal in crypto.

Cascading liquidations create 5-15% moves in minutes. Long liquidations cascade DOWN,
short liquidations cascade UP. Monitoring spikes gives 30-60 seconds lead time.

Uses REST API for recent liquidations (WebSocket is for real-time server mode).
Endpoint: GET https://fapi.binance.com/fapi/v1/allForceOrders
"""

import time
from datetime import datetime, timezone
import httpx
import structlog

logger = structlog.get_logger()


class LiquidationMonitor:
    """Fetch recent liquidation data from Binance Futures."""

    def __init__(self):
        self._client = httpx.Client(timeout=15.0)
        self._base_url = "https://fapi.binance.com"

    def get_recent_liquidations(self, symbol: str = None, limit: int = 100) -> dict:
        """Get recent forced liquidation orders.

        Returns:
            {
                "total_long_liquidated_usd": float,
                "total_short_liquidated_usd": float,
                "net_direction": "LONG_SQUEEZE" | "SHORT_SQUEEZE" | "BALANCED",
                "intensity": "EXTREME" | "HIGH" | "MODERATE" | "LOW",
                "count": int,
                "largest_single_usd": float,
                "liquidations": list[dict],  # raw data
            }
        """
        # Use allForceOrders endpoint
        params = {"limit": limit}
        if symbol:
            params["symbol"] = symbol

        try:
            resp = self._client.get(f"{self._base_url}/fapi/v1/allForceOrders", params=params)
            resp.raise_for_status()
            raw = resp.json()
        except Exception as e:
            logger.warning("liquidation_fetch_failed", error=str(e))
            # Fallback: try the data-api endpoint
            try:
                resp = self._client.get("https://fapi.binance.com/fapi/v1/allForceOrders", params=params)
                resp.raise_for_status()
                raw = resp.json()
            except Exception:
                return {"total_long_liquidated_usd": 0, "total_short_liquidated_usd": 0,
                        "net_direction": "UNKNOWN", "intensity": "UNKNOWN", "count": 0,
                        "largest_single_usd": 0, "liquidations": []}

        if not raw:
            return {"total_long_liquidated_usd": 0, "total_short_liquidated_usd": 0,
                    "net_direction": "BALANCED", "intensity": "LOW", "count": 0,
                    "largest_single_usd": 0, "liquidations": []}

        long_usd = 0.0
        short_usd = 0.0
        largest = 0.0

        for liq in raw:
            price = float(liq.get("price", 0) or liq.get("ap", 0))
            qty = float(liq.get("origQty", 0) or liq.get("q", 0))
            side = liq.get("side", "")
            notional = price * qty

            if side == "SELL":  # Forced sell = long position liquidated
                long_usd += notional
            elif side == "BUY":  # Forced buy = short position liquidated
                short_usd += notional

            largest = max(largest, notional)

        total = long_usd + short_usd

        # Determine direction
        if total < 1000:
            direction = "BALANCED"
        elif long_usd > short_usd * 2:
            direction = "LONG_SQUEEZE"  # Longs getting wiped = bearish cascade
        elif short_usd > long_usd * 2:
            direction = "SHORT_SQUEEZE"  # Shorts getting wiped = bullish cascade
        else:
            direction = "BALANCED"

        # Intensity based on USD volume
        if total > 100_000_000:  # $100M+
            intensity = "EXTREME"
        elif total > 20_000_000:  # $20M+
            intensity = "HIGH"
        elif total > 5_000_000:  # $5M+
            intensity = "MODERATE"
        else:
            intensity = "LOW"

        return {
            "total_long_liquidated_usd": round(long_usd, 2),
            "total_short_liquidated_usd": round(short_usd, 2),
            "net_direction": direction,
            "intensity": intensity,
            "count": len(raw),
            "largest_single_usd": round(largest, 2),
            "liquidations": raw[:20],  # Keep last 20 for detail
        }

    def close(self):
        self._client.close()
