"""
Blockchain.com API client — free, no auth.

Provides real Bitcoin on-chain data:
- Hash rate, difficulty, mining stats
- Transaction count, mempool size
- Estimated transaction volume
- Miner revenue

This is the primary on-chain data source for BTC.
"""

from __future__ import annotations

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()

BASE_URL = "https://api.blockchain.info"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
def get_btc_onchain_stats() -> dict:
    """
    Fetch comprehensive BTC on-chain statistics.

    Returns real network data: hash rate, difficulty, tx count,
    miner revenue, mempool, and more.
    """
    with httpx.Client(timeout=15.0) as client:
        # Main stats
        resp = client.get(f"{BASE_URL}/stats")
        resp.raise_for_status()
        data = resp.json()

        # Mempool count
        try:
            mempool_resp = client.get(f"{BASE_URL}/q/unconfirmedcount")
            mempool_resp.raise_for_status()
            mempool_count = int(mempool_resp.text.strip())
        except Exception:
            mempool_count = None

    hash_rate = data.get("hash_rate", 0)
    difficulty = data.get("difficulty", 0)
    n_tx = data.get("n_tx", 0)
    n_blocks = data.get("n_blocks_mined", 0)
    minutes_between = data.get("minutes_between_blocks", 0)
    est_tx_volume = data.get("estimated_transaction_volume_usd", 0)
    miners_revenue = data.get("miners_revenue_usd", 0)
    total_fees = data.get("total_fees_btc", 0) / 1e8 if data.get("total_fees_btc") else 0

    # Hash rate health assessment
    if hash_rate > 500_000_000_000_000:  # 500 EH/s
        hash_health = "ALL_TIME_HIGH — Network security at peak"
    elif hash_rate > 300_000_000_000_000:
        hash_health = "STRONG — Very healthy network"
    elif hash_rate > 100_000_000_000_000:
        hash_health = "MODERATE — Normal levels"
    else:
        hash_health = "LOW — Potential concern"

    # Mempool assessment
    if mempool_count is not None:
        if mempool_count > 100_000:
            mempool_read = "CONGESTED — High demand, fees rising"
        elif mempool_count > 30_000:
            mempool_read = "BUSY — Above normal activity"
        elif mempool_count > 5_000:
            mempool_read = "NORMAL — Healthy activity"
        else:
            mempool_read = "QUIET — Low demand"
    else:
        mempool_read = "UNKNOWN"

    # Block time assessment
    if minutes_between < 8:
        block_time_read = "FAST — Blocks coming quickly, hash rate recently increased"
    elif minutes_between < 12:
        block_time_read = "NORMAL — On target (~10 min)"
    else:
        block_time_read = "SLOW — Hash rate may have dropped, difficulty adjustment pending"

    return {
        "hash_rate": hash_rate,
        "hash_rate_eh": round(hash_rate / 1e18, 2),
        "hash_health": hash_health,
        "difficulty": difficulty,
        "n_transactions_24h": n_tx,
        "n_blocks_mined_24h": n_blocks,
        "minutes_between_blocks": round(minutes_between, 1),
        "block_time_read": block_time_read,
        "est_tx_volume_usd": est_tx_volume,
        "miners_revenue_usd": miners_revenue,
        "total_fees_btc": round(total_fees, 4),
        "mempool_count": mempool_count,
        "mempool_read": mempool_read,
        "market_price_usd": data.get("market_price_usd", 0),
    }
