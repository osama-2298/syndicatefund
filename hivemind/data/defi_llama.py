"""
DeFiLlama API client — completely free, no auth.

Provides: TVL data per chain and per protocol, DeFi protocol metrics.
This is the primary data source for the On-Chain team.
"""

from __future__ import annotations

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()

BASE_URL = "https://api.llama.fi"

# Map Binance symbols to DeFiLlama chain names
SYMBOL_TO_CHAIN: dict[str, str] = {
    "ETH": "Ethereum",
    "SOL": "Solana",
    "AVAX": "Avalanche",
    "BNB": "BSC",
    "MATIC": "Polygon",
    "ARB": "Arbitrum",
    "OP": "Optimism",
    "NEAR": "Near",
    "SUI": "Sui",
    "APT": "Aptos",
    "SEI": "Sei",
    "ADA": "Cardano",
    "DOT": "Polkadot",
    "ATOM": "Cosmos",
    "FTM": "Fantom",
    "BASE": "Base",
}


class DeFiLlamaClient:
    """Synchronous DeFiLlama API client."""

    def __init__(self) -> None:
        self._client = httpx.Client(
            base_url=BASE_URL,
            timeout=20.0,
            headers={"Accept": "application/json"},
        )
        self._chains_cache: list[dict] | None = None

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> DeFiLlamaClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
    def get_chains_tvl(self) -> list[dict]:
        """
        Get TVL for all chains. Returns list sorted by TVL descending.
        Cached after first call.
        """
        if self._chains_cache is not None:
            return self._chains_cache

        resp = self._client.get("/v2/chains")
        resp.raise_for_status()
        data = resp.json()

        chains = []
        for chain in data:
            tvl = chain.get("tvl", 0)
            if tvl and tvl > 0:
                chains.append({
                    "name": chain.get("name", ""),
                    "tvl": tvl,
                    "token_symbol": chain.get("tokenSymbol", ""),
                    "gecko_id": chain.get("gecko_id", ""),
                })

        chains.sort(key=lambda x: -x["tvl"])
        self._chains_cache = chains
        return chains

    def get_chain_tvl(self, symbol: str) -> dict | None:
        """
        Get TVL data for a specific chain by its token symbol.
        Returns TVL, rank, and TVL dominance.
        """
        base = symbol.replace("USDT", "")
        chain_name = SYMBOL_TO_CHAIN.get(base)
        if chain_name is None:
            return None

        chains = self.get_chains_tvl()
        total_tvl = sum(c["tvl"] for c in chains)

        for i, chain in enumerate(chains):
            if chain["name"] == chain_name:
                tvl = chain["tvl"]
                return {
                    "chain": chain_name,
                    "tvl": tvl,
                    "tvl_rank": i + 1,
                    "tvl_dominance_pct": round((tvl / max(total_tvl, 1)) * 100, 2),
                    "total_defi_tvl": total_tvl,
                }

        return None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
    def get_top_protocols(self, limit: int = 20) -> list[dict]:
        """Get top DeFi protocols by TVL."""
        resp = self._client.get("/protocols")
        resp.raise_for_status()
        data = resp.json()

        protocols = []
        for p in data[:limit]:
            protocols.append({
                "name": p.get("name", ""),
                "symbol": p.get("symbol", ""),
                "chain": p.get("chain", ""),
                "tvl": p.get("tvl", 0),
                "change_1d": p.get("change_1d", 0),
                "change_7d": p.get("change_7d", 0),
                "category": p.get("category", ""),
                "chains": p.get("chains", []),
            })

        return protocols

    def get_defi_summary(self) -> dict:
        """
        Get a high-level DeFi summary: total TVL, top chains, TVL concentration.
        """
        chains = self.get_chains_tvl()
        total_tvl = sum(c["tvl"] for c in chains)

        top_5 = chains[:5]
        top_5_tvl = sum(c["tvl"] for c in top_5)

        return {
            "total_tvl": total_tvl,
            "num_chains": len(chains),
            "top_5_chains": [
                {"name": c["name"], "tvl": c["tvl"], "pct": round((c["tvl"] / max(total_tvl, 1)) * 100, 1)}
                for c in top_5
            ],
            "top_5_concentration_pct": round((top_5_tvl / max(total_tvl, 1)) * 100, 1),
        }
