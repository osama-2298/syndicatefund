"""
DeFiLlama API client — completely free, no auth.

Provides: TVL data per chain and per protocol, DeFi protocol metrics.
This is the primary data source for the On-Chain team.
"""

from __future__ import annotations

from datetime import datetime, timezone

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

    def get_token_unlocks(self) -> list[dict]:
        """Get upcoming token unlock events across all protocols.

        Endpoint: GET https://api.llama.fi/api/emissions
        Free, no API key required.

        Returns list of:
            {
                "name": str,          # Protocol name
                "symbol": str,        # Token symbol
                "next_event_date": str,  # ISO date of next unlock
                "days_until": int,    # Days until next unlock
                "unlock_pct": float,  # % of circulating supply being unlocked
                "unlock_usd": float,  # USD value of unlock (approximate)
                "risk_level": "HIGH" | "MEDIUM" | "LOW",  # Based on % and timing
            }

        HIGH risk = >2% of supply unlocking within 7 days
        MEDIUM risk = >1% within 14 days
        LOW risk = everything else
        """
        # Known trading symbols we care about (from SYMBOL_TO_CHAIN + major tokens)
        known_symbols = set(SYMBOL_TO_CHAIN.keys()) | {
            "BTC", "ETH", "SOL", "AVAX", "BNB", "MATIC", "ARB", "OP",
            "NEAR", "SUI", "APT", "SEI", "ADA", "DOT", "ATOM", "FTM",
            "DYDX", "UNI", "AAVE", "MKR", "LDO", "CRV", "LINK", "INJ",
            "TIA", "JUP", "STRK", "ZK", "W", "EIGEN", "PENDLE", "JTO",
        }

        try:
            resp = self._client.get("/api/emissions")
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            # Try fallback endpoint
            try:
                resp = self._client.get("/api/emissions/breakdown")
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                logger.warning("token_unlocks_unavailable", error=str(e))
                return []

        now = datetime.now(timezone.utc)
        unlocks: list[dict] = []

        # The API returns a list of protocols with emission/unlock data.
        # Each entry may have different shapes; we extract what we can.
        if not isinstance(data, list):
            # If it's a dict, try to get a list from common keys
            if isinstance(data, dict):
                data = data.get("protocols", data.get("data", []))
            if not isinstance(data, list):
                return []

        for protocol in data:
            if not isinstance(protocol, dict):
                continue

            name = protocol.get("name", "")
            symbol = (protocol.get("symbol") or protocol.get("token", "") or "").upper()

            # Only process protocols matching our trading symbols
            if symbol not in known_symbols:
                continue

            # Look for upcoming unlock events
            events = protocol.get("events", protocol.get("unlocks", []))
            if not isinstance(events, list):
                # Try to parse from emission schedule
                events = self._parse_emission_events(protocol)

            for event in events:
                if not isinstance(event, dict):
                    continue

                # Parse event date
                event_date_raw = event.get("date") or event.get("timestamp") or event.get("datetime")
                if event_date_raw is None:
                    continue

                try:
                    if isinstance(event_date_raw, (int, float)):
                        event_date = datetime.fromtimestamp(event_date_raw, tz=timezone.utc)
                    else:
                        # Try ISO format
                        date_str = str(event_date_raw).replace("Z", "+00:00")
                        event_date = datetime.fromisoformat(date_str)
                        if event_date.tzinfo is None:
                            event_date = event_date.replace(tzinfo=timezone.utc)
                except (ValueError, OSError):
                    continue

                days_until = (event_date - now).days
                if days_until < 0 or days_until > 90:
                    # Skip past events and events too far out
                    continue

                # Parse unlock amount
                unlock_pct = float(event.get("unlock_pct", 0) or event.get("percentage", 0) or 0)
                unlock_usd = float(event.get("unlock_usd", 0) or event.get("value", 0)
                                   or event.get("usd_value", 0) or 0)

                # Determine risk level
                if unlock_pct > 2.0 and days_until <= 7:
                    risk_level = "HIGH"
                elif unlock_pct > 1.0 and days_until <= 14:
                    risk_level = "MEDIUM"
                else:
                    risk_level = "LOW"

                unlocks.append({
                    "name": name,
                    "symbol": symbol,
                    "next_event_date": event_date.strftime("%Y-%m-%d"),
                    "days_until": days_until,
                    "unlock_pct": round(unlock_pct, 2),
                    "unlock_usd": round(unlock_usd, 2),
                    "risk_level": risk_level,
                })

        # Sort by days_until ascending, then by risk level
        risk_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        unlocks.sort(key=lambda u: (risk_order.get(u["risk_level"], 3), u["days_until"]))

        return unlocks

    @staticmethod
    def _parse_emission_events(protocol: dict) -> list[dict]:
        """Try to extract unlock events from various emission schedule formats."""
        events: list[dict] = []

        # Some protocols store schedules as timeline arrays
        schedule = protocol.get("schedule") or protocol.get("emission_schedule") or []
        if isinstance(schedule, list):
            for entry in schedule:
                if isinstance(entry, dict) and ("date" in entry or "timestamp" in entry):
                    events.append(entry)

        # Check for a single "next_unlock" field
        next_unlock = protocol.get("next_unlock") or protocol.get("nextEvent")
        if isinstance(next_unlock, dict):
            events.append(next_unlock)

        return events

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
    def get_dex_volumes(self) -> dict:
        """Get aggregated DEX trading volumes.

        Endpoint: GET https://api.llama.fi/overview/dexs
        Free, no API key required.

        Returns:
            {
                "total_24h_volume": float,    # Total DEX volume in USD
                "total_7d_volume": float,
                "volume_change_24h_pct": float,
                "top_dexes": list[dict],      # Top 5 by volume
                "chain_volumes": dict,         # Per-chain DEX volume
            }
        """
        try:
            resp = self._client.get("/overview/dexs")
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning("dex_volumes_unavailable", error=str(e))
            return {}

        total_24h = float(data.get("total24h", 0) or data.get("totalVolume24h", 0) or 0)
        total_7d = float(data.get("total7d", 0) or data.get("totalVolume7d", 0) or 0)
        change_24h = float(data.get("change_1d", 0) or data.get("change24h", 0) or 0)

        # Extract top DEXes by 24h volume
        protocols = data.get("protocols", data.get("dexs", []))
        top_dexes: list[dict] = []
        if isinstance(protocols, list):
            # Sort by 24h volume descending
            sorted_protos = sorted(
                protocols,
                key=lambda p: float(p.get("total24h", 0) or p.get("dailyVolume", 0) or 0),
                reverse=True,
            )
            for p in sorted_protos[:5]:
                vol = float(p.get("total24h", 0) or p.get("dailyVolume", 0) or 0)
                top_dexes.append({
                    "name": p.get("name", "Unknown"),
                    "volume_24h": vol,
                    "change_24h_pct": float(p.get("change_1d", 0) or p.get("change24h", 0) or 0),
                    "chains": p.get("chains", []),
                })

        # Extract per-chain volumes
        chain_volumes: dict[str, float] = {}
        chain_data = data.get("totalDataChart", data.get("allChains", []))
        # Some responses include chain-level breakdown directly
        all_chains_data = data.get("allChains", [])
        if isinstance(all_chains_data, list):
            for chain_entry in all_chains_data:
                if isinstance(chain_entry, dict):
                    chain_name = chain_entry.get("name", chain_entry.get("chain", ""))
                    chain_vol = float(chain_entry.get("total24h", 0)
                                      or chain_entry.get("dailyVolume", 0) or 0)
                    if chain_name and chain_vol > 0:
                        chain_volumes[chain_name] = chain_vol

        # If no chain breakdown from allChains, try to aggregate from protocols
        if not chain_volumes and isinstance(protocols, list):
            for p in protocols:
                chains = p.get("chains", [])
                vol = float(p.get("total24h", 0) or p.get("dailyVolume", 0) or 0)
                if vol > 0 and isinstance(chains, list) and len(chains) == 1:
                    chain_name = chains[0]
                    chain_volumes[chain_name] = chain_volumes.get(chain_name, 0) + vol

        return {
            "total_24h_volume": total_24h,
            "total_7d_volume": total_7d,
            "volume_change_24h_pct": round(change_24h, 2),
            "top_dexes": top_dexes,
            "chain_volumes": chain_volumes,
        }
