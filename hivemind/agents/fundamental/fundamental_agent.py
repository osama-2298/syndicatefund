"""
Fundamental Analysis Agent.

Architecture follows the virattt/ai-hedge-fund pattern:
- Phase 1: Python computes ALL fundamental scores deterministically
  (valuation, supply dynamics, network health proxy, macro cycle position)
- Phase 2: LLM receives pre-computed scores and makes a JUDGMENT call

The LLM never does math. It interprets pre-computed analysis.

For crypto, "fundamentals" are different from equities. There are no earnings reports.
Instead: tokenomics, supply dynamics, market cycle position, and volume as a proxy
for institutional activity.
"""

from __future__ import annotations

from typing import Any

from hivemind.agents.base import BaseAgent
from hivemind.data.models import TeamType, TechnicalIndicators


# Static profiles for major crypto assets.
# In production, this is replaced by live data from CoinGecko/DeFiLlama APIs.
COIN_PROFILES: dict[str, dict[str, str]] = {
    "BTC": {
        "description": "Bitcoin — Digital gold, store of value, first cryptocurrency",
        "market_cap_tier": "Mega-cap (#1)",
        "sector": "Store of Value / Digital Gold",
        "supply_dynamics": "Hard cap 21M. ~19.6M circulating. Next halving ~2028. Deflationary pressure from lost coins.",
        "key_fundamentals": "Network hash rate at ATH. Institutional adoption (ETFs). Lightning Network growth. Regulatory clarity improving.",
    },
    "ETH": {
        "description": "Ethereum — Smart contract platform, DeFi/NFT backbone",
        "market_cap_tier": "Mega-cap (#2)",
        "sector": "Smart Contract Platform / Layer 1",
        "supply_dynamics": "Post-merge deflationary (EIP-1559 burn). Staking locks ~27% of supply. Net issuance near zero or negative.",
        "key_fundamentals": "Largest DeFi ecosystem. Layer 2 scaling (Arbitrum, Optimism, Base). Blob space revenue. Developer ecosystem dominance.",
    },
    "SOL": {
        "description": "Solana — High-performance Layer 1",
        "market_cap_tier": "Large-cap",
        "sector": "Smart Contract Platform / Layer 1",
        "supply_dynamics": "Inflationary but decreasing. ~65% staked. Regular validator rewards dilute non-stakers.",
        "key_fundamentals": "Fastest growing DeFi ecosystem. High TPS. Low fees. Strong retail/meme coin activity. Firedancer validator client in development.",
    },
    "DOGE": {
        "description": "Dogecoin — Meme coin with large community",
        "market_cap_tier": "Large-cap",
        "sector": "Meme / Payments",
        "supply_dynamics": "Inflationary — 5B new DOGE minted per year. No supply cap. ~2.9% annual inflation, decreasing over time.",
        "key_fundamentals": "Community-driven. Payment use case (some merchant adoption). Elon Musk association. Limited technical development.",
    },
    "AVAX": {
        "description": "Avalanche — Subnet-based Layer 1 platform",
        "market_cap_tier": "Mid-cap",
        "sector": "Smart Contract Platform / Layer 1",
        "supply_dynamics": "720M max supply. Fees burned (deflationary mechanism). Subnet staking requirements lock supply.",
        "key_fundamentals": "Subnet architecture for custom chains. Institutional partnerships. Gaming/enterprise focus. Teleporter cross-chain.",
    },
}


def compute_fundamental_scores(
    indicators: TechnicalIndicators,
    stats_24h: dict,
    coin_profile: dict | None = None,
    coingecko_coin: dict | None = None,
) -> dict[str, Any]:
    """
    Pre-compute fundamental analysis scores BEFORE sending to LLM.
    All math happens here. The LLM only interprets results.

    Now uses LIVE CoinGecko data for market cap, supply, multi-timeframe changes, ATH/ATL.
    Falls back to static profiles when CoinGecko data is unavailable.
    """
    current_price = float(stats_24h.get("close", 0))
    change_24h = float(stats_24h.get("price_change_pct", 0))
    volume_24h = float(stats_24h.get("quote_volume", 0))
    scores: dict[str, Any] = {
        "current_price": current_price,
        "change_24h": change_24h,
        "volume_24h": volume_24h,
    }

    symbol = indicators.symbol.replace("USDT", "")

    # ── Live CoinGecko data (preferred) ──
    if coingecko_coin:
        scores["coin_name"] = coingecko_coin.get("name", symbol)
        scores["market_cap_rank"] = coingecko_coin.get("market_cap_rank")
        scores["market_cap_usd"] = coingecko_coin.get("market_cap_usd", 0)
        scores["fully_diluted_val"] = coingecko_coin.get("fully_diluted_valuation_usd", 0)

        # Supply analysis
        circ = coingecko_coin.get("circulating_supply")
        total = coingecko_coin.get("total_supply")
        max_sup = coingecko_coin.get("max_supply")
        if circ and total and total > 0:
            scores["supply_ratio"] = round(circ / total * 100, 1)
            scores["supply_read"] = (
                "FULLY_CIRCULATING" if circ / total > 0.95 else
                "HIGH_CIRCULATION" if circ / total > 0.75 else
                "MODERATE_UNLOCK_RISK" if circ / total > 0.50 else
                "HIGH_UNLOCK_RISK"
            )
        if max_sup:
            scores["max_supply"] = max_sup
            scores["has_hard_cap"] = True
        else:
            scores["has_hard_cap"] = False

        # Multi-timeframe price changes (real data!)
        price_changes = coingecko_coin.get("price_changes", {})
        if price_changes:
            scores["price_changes"] = price_changes
            # 30d and 200d changes tell the macro story
            change_30d = price_changes.get("30d", 0)
            change_200d = price_changes.get("200d", 0)
            if change_30d:
                scores["change_30d"] = change_30d
            if change_200d:
                scores["change_200d"] = change_200d

        # ATH/ATL distance (real data!)
        ath_dist = coingecko_coin.get("ath_distance_pct", 0)
        atl_dist = coingecko_coin.get("atl_distance_pct", 0)
        if ath_dist:
            scores["ath_distance_pct"] = ath_dist
            scores["ath_read"] = (
                "NEAR_ATH" if ath_dist > -10 else
                "HEALTHY_PULLBACK" if ath_dist > -30 else
                "SIGNIFICANT_DRAWDOWN" if ath_dist > -60 else
                "DEEP_BEAR_TERRITORY"
            )
        if atl_dist:
            scores["atl_distance_pct"] = atl_dist

        # FDV/MCap ratio (dilution risk)
        mcap = scores.get("market_cap_usd", 0)
        fdv = scores.get("fully_diluted_val", 0)
        if mcap > 0 and fdv > 0:
            fdv_ratio = fdv / mcap
            scores["fdv_mcap_ratio"] = round(fdv_ratio, 2)
            scores["dilution_risk"] = (
                "MINIMAL" if fdv_ratio < 1.2 else
                "LOW" if fdv_ratio < 1.5 else
                "MODERATE" if fdv_ratio < 2.5 else
                "HIGH" if fdv_ratio < 5 else
                "SEVERE"
            )

    # ── Fallback to static profiles ──
    profile = COIN_PROFILES.get(symbol, coin_profile or {})
    if profile:
        scores.setdefault("coin_description", profile.get("description", "Unknown asset"))
        scores.setdefault("market_cap_tier", profile.get("market_cap_tier", "Unknown"))
        scores["sector"] = profile.get("sector", "Unknown")
        scores["supply_dynamics_note"] = profile.get("supply_dynamics", "Unknown")
        scores["key_fundamentals_note"] = profile.get("key_fundamentals", "No data")

    # ── 1. MARKET CYCLE POSITION SCORE (-1 to +1) ──
    # Where is this asset in its macro cycle? Based on price vs long-term MAs.
    cycle_signals = []

    if indicators.sma_200 and current_price:
        pct_from_200 = ((current_price - indicators.sma_200) / indicators.sma_200) * 100
        scores["pct_from_sma200"] = round(pct_from_200, 1)

        # Map to cycle phase
        if pct_from_200 > 50:
            cycle_signals.append(0.8)  # Late markup / potential distribution
            scores["cycle_phase"] = "LATE_MARKUP_DISTRIBUTION"
            scores["cycle_risk"] = "HIGH — Far above mean, potential correction"
        elif pct_from_200 > 20:
            cycle_signals.append(0.5)  # Healthy markup
            scores["cycle_phase"] = "HEALTHY_MARKUP"
            scores["cycle_risk"] = "MODERATE — Above mean but trending"
        elif pct_from_200 > 5:
            cycle_signals.append(0.3)  # Early markup
            scores["cycle_phase"] = "EARLY_MARKUP"
            scores["cycle_risk"] = "LOW — Healthy uptrend"
        elif pct_from_200 > -5:
            cycle_signals.append(0.0)  # Accumulation zone
            scores["cycle_phase"] = "ACCUMULATION"
            scores["cycle_risk"] = "LOW — Near mean, potential accumulation"
        elif pct_from_200 > -20:
            cycle_signals.append(-0.3)  # Early markdown
            scores["cycle_phase"] = "EARLY_MARKDOWN"
            scores["cycle_risk"] = "MODERATE — Below mean, caution"
        elif pct_from_200 > -40:
            cycle_signals.append(-0.6)  # Markdown
            scores["cycle_phase"] = "MARKDOWN"
            scores["cycle_risk"] = "HIGH — Significant drawdown"
        else:
            cycle_signals.append(-0.9)  # Capitulation
            scores["cycle_phase"] = "CAPITULATION"
            scores["cycle_risk"] = "EXTREME — Deep drawdown, potential bottom"

    # SMA stack gives cycle confirmation
    if indicators.sma_20 and indicators.sma_50 and indicators.sma_200:
        if indicators.sma_20 > indicators.sma_50 > indicators.sma_200:
            cycle_signals.append(0.5)
            scores["ma_cycle_confirmation"] = "BULLISH_STACK — All MAs aligned upward"
        elif indicators.sma_20 < indicators.sma_50 < indicators.sma_200:
            cycle_signals.append(-0.5)
            scores["ma_cycle_confirmation"] = "BEARISH_STACK — All MAs aligned downward"
        else:
            scores["ma_cycle_confirmation"] = "MIXED — Transition phase"

    cycle_score = sum(cycle_signals) / max(len(cycle_signals), 1)
    scores["cycle_score"] = round(cycle_score, 3)
    scores["cycle_label"] = (
        "STRONG_BULLISH_CYCLE" if cycle_score > 0.4 else
        "BULLISH_CYCLE" if cycle_score > 0.15 else
        "NEUTRAL_CYCLE" if cycle_score > -0.15 else
        "BEARISH_CYCLE" if cycle_score > -0.4 else
        "STRONG_BEARISH_CYCLE"
    )

    # ── 2. INSTITUTIONAL ACTIVITY SCORE (-1 to +1) ──
    # Volume is our proxy for smart money. High volume in a direction = institutional conviction.
    institutional_signals = []

    if indicators.volume_ratio is not None:
        vr = indicators.volume_ratio
        scores["volume_ratio"] = round(vr, 2)

        # Volume + direction = institutional behavior
        if vr > 2.0 and change_24h > 2:
            institutional_signals.append(1.0)
            scores["institutional_read"] = "STRONG_ACCUMULATION — High volume buying"
        elif vr > 1.5 and change_24h > 0:
            institutional_signals.append(0.6)
            scores["institutional_read"] = "ACCUMULATION — Above-average volume on up move"
        elif vr > 2.0 and change_24h < -2:
            institutional_signals.append(-1.0)
            scores["institutional_read"] = "STRONG_DISTRIBUTION — High volume selling"
        elif vr > 1.5 and change_24h < 0:
            institutional_signals.append(-0.6)
            scores["institutional_read"] = "DISTRIBUTION — Above-average volume on down move"
        elif vr < 0.7 and change_24h > 0:
            institutional_signals.append(-0.3)
            scores["institutional_read"] = "WEAK_RALLY — Low volume up move, no institutional backing"
        elif vr < 0.7 and change_24h < 0:
            institutional_signals.append(0.3)
            scores["institutional_read"] = "SELLING_EXHAUSTION — Low volume decline, sellers drying up"
        else:
            scores["institutional_read"] = "NEUTRAL — Normal activity"

    # Volume/Price ratio as liquidity indicator
    if volume_24h and current_price:
        vol_price_ratio = volume_24h / current_price
        scores["vol_price_ratio"] = round(vol_price_ratio, 0)
        scores["liquidity_read"] = (
            "DEEP_LIQUIDITY" if vol_price_ratio > 1_000_000 else
            "GOOD_LIQUIDITY" if vol_price_ratio > 100_000 else
            "MODERATE_LIQUIDITY" if vol_price_ratio > 10_000 else
            "THIN_LIQUIDITY"
        )

    institutional_score = sum(institutional_signals) / max(len(institutional_signals), 1)
    scores["institutional_score"] = round(institutional_score, 3)
    scores["institutional_label"] = (
        "STRONG_ACCUMULATION" if institutional_score > 0.5 else
        "ACCUMULATION" if institutional_score > 0.15 else
        "NEUTRAL" if institutional_score > -0.15 else
        "DISTRIBUTION" if institutional_score > -0.5 else
        "STRONG_DISTRIBUTION"
    )

    # ── 3. VOLATILITY/RISK SCORE (0 to 1, higher = more risk) ──
    # Used for risk assessment, not direction. Informs position sizing.
    risk_score = 0.5  # Default moderate

    if indicators.atr_14 and current_price:
        atr_pct = (indicators.atr_14 / current_price) * 100
        scores["atr_pct"] = round(atr_pct, 3)

        if atr_pct > 5:
            risk_score = 0.9
            scores["volatility_risk"] = "EXTREME — Very high risk per position"
        elif atr_pct > 3:
            risk_score = 0.7
            scores["volatility_risk"] = "HIGH — Significant daily swings"
        elif atr_pct > 1.5:
            risk_score = 0.5
            scores["volatility_risk"] = "MODERATE — Normal crypto volatility"
        elif atr_pct > 0.5:
            risk_score = 0.3
            scores["volatility_risk"] = "LOW — Relatively stable"
        else:
            risk_score = 0.2
            scores["volatility_risk"] = "VERY_LOW — Compressed, breakout likely"

    if indicators.bb_width is not None:
        scores["bb_width"] = round(indicators.bb_width, 4)
        if indicators.bb_width < 2:
            scores["bb_squeeze"] = "SQUEEZE — Volatility compressed, breakout imminent"
        elif indicators.bb_width > 8:
            scores["bb_squeeze"] = "EXPANSION — High volatility, wide bands"
        else:
            scores["bb_squeeze"] = "NORMAL"

    scores["risk_score"] = round(risk_score, 3)

    # ── 4. VALUE ASSESSMENT SCORE (-1 to +1) ──
    # Combining cycle position with institutional flow to assess over/undervaluation.
    # Positive = undervalued (buy opportunity), Negative = overvalued (sell/short opportunity)
    value_signals = []

    # If price is below long-term mean AND institutions are accumulating → undervalued
    if "cycle_score" in scores:
        # Invert cycle score: low cycle position = potential value, high = potential overvaluation
        value_from_cycle = -scores["cycle_score"] * 0.6
        value_signals.append(value_from_cycle)

    if "institutional_score" in scores:
        # Institutional accumulation at low prices = value, distribution at high prices = overvalued
        value_signals.append(scores["institutional_score"] * 0.4)

    value_score = sum(value_signals) / max(len(value_signals), 1)
    scores["value_score"] = round(value_score, 3)
    scores["value_label"] = (
        "DEEPLY_UNDERVALUED" if value_score > 0.5 else
        "UNDERVALUED" if value_score > 0.15 else
        "FAIR_VALUE" if value_score > -0.15 else
        "OVERVALUED" if value_score > -0.5 else
        "DEEPLY_OVERVALUED"
    )

    # ── 5. COMPOSITE FUNDAMENTAL SCORE ──
    # Weighted: value 0.35, cycle 0.25, institutional 0.25, risk-adjusted 0.15
    weights = {
        "value": 0.35,
        "cycle": 0.25,
        "institutional": 0.25,
        "risk_adj": 0.15,
    }

    # Risk adjustment: in high-risk environments, reduce conviction
    risk_adjustment = (1 - risk_score) * 0.5  # High risk → lower boost

    composite = (
        scores["value_score"] * weights["value"]
        + scores["cycle_score"] * weights["cycle"]
        + scores["institutional_score"] * weights["institutional"]
        + risk_adjustment * weights["risk_adj"]  # Adds a small boost when risk is low
    )

    total_weight = sum(weights.values())
    if total_weight > 0:
        composite = composite / total_weight

    scores["composite_score"] = round(composite, 3)
    scores["composite_label"] = (
        "STRONG_BULLISH" if composite > 0.5 else
        "BULLISH" if composite > 0.15 else
        "BEARISH" if composite < -0.15 else
        "STRONG_BEARISH" if composite < -0.5 else
        "NEUTRAL"
    )

    return scores


class FundamentalAgent(BaseAgent):
    """
    Fundamental analyst — pre-computes value scores in Python, then asks LLM for judgment.
    """

    @property
    def team_type(self) -> TeamType:
        return TeamType.FUNDAMENTAL

    @property
    def system_prompt(self) -> str:
        return (
            "You are a senior fundamental analyst at a quantitative crypto hedge fund.\n\n"
            "You evaluate INTRINSIC VALUE using live CoinGecko data: market cap, supply dynamics, "
            "ATH distance, FDV/MCap dilution risk, and institutional flow.\n\n"
            "YOUR TASK: Predict whether this asset is fundamentally set to go HIGHER or LOWER.\n"
            "You MUST pick BULLISH or BEARISH. There is no neutral option.\n\n"
            "CRYPTO FUNDAMENTALS:\n"
            "- No P/E ratios. Instead: tokenomics, supply dynamics, network effects.\n"
            "- Volume is your proxy for institutional activity.\n"
            "- Cycle position matters more than short-term price.\n"
            "- Supply dynamics (halvings, burns, unlocks) drive long-term value.\n\n"
            "DIRECTION RULES:\n"
            "- BULLISH if: value_score > 0 (even slightly undervalued) AND institutions not distributing, "
            "OR cycle is ACCUMULATION/EARLY_MARKUP, OR ATH distance is deep (>50% below ATH).\n"
            "- BEARISH if: value_score < 0 (overvalued) AND institutions distributing, "
            "OR cycle is LATE_MARKUP/DISTRIBUTION, OR dilution risk is HIGH.\n"
            "- If near fair value: lean toward the cycle direction with low conviction.\n\n"
            "CONVICTION SCALE:\n"
            "- 9-10: Clear mispricing + institutional confirmation + favorable cycle. Extremely rare.\n"
            "- 7-8: Visible mispricing with most factors aligned.\n"
            "- 5-6: Moderate value lean. Some factors conflict.\n"
            "- 3-4: Near fair value. Slight lean based on cycle or institutional flow.\n"
            "- 1-2: Essentially fair value. Pick cycle direction.\n\n"
            "RULES:\n"
            "- Do NOT invent data. Reference provided scores.\n"
            "- Think VALUE, not price. Is this cheap or expensive for what it does?\n"
            "- Fundamental signals are slow but reliable. Low conviction is fine."
        )

    def build_analysis_prompt(self, market_data: dict[str, Any]) -> str:
        """Build prompt with pre-computed fundamental scores + live CoinGecko data."""
        indicators: TechnicalIndicators = market_data["indicators"]
        stats_24h: dict = market_data["stats_24h"]
        coin_profile: dict = market_data.get("coin_profile", {})
        coingecko_coin: dict | None = market_data.get("coingecko_coin")

        # Phase 1: Pre-compute everything in Python (now with live data)
        scores = compute_fundamental_scores(indicators, stats_24h, coin_profile, coingecko_coin)

        current_price = scores["current_price"]
        change_24h = scores["change_24h"]
        volume_24h = scores["volume_24h"]

        prompt = (
            f"Evaluate the fundamental value of {self.profile.symbol} and produce a trading signal.\n\n"
            f"=== PRE-COMPUTED FUNDAMENTAL SCORES ===\n"
            f"Current Price: ${current_price:,.2f} | 24h Change: {change_24h:+.2f}% | "
            f"24h Volume: ${volume_24h:,.0f}\n\n"
            f"COMPOSITE: {scores['composite_score']:+.3f} ({scores['composite_label']})\n\n"
        )

        # Live CoinGecko data section
        if "market_cap_rank" in scores:
            prompt += f"=== LIVE MARKET DATA (CoinGecko) ===\n"
            name = scores.get("coin_name", self.profile.symbol)
            prompt += f"Name: {name} | Rank: #{scores['market_cap_rank']}\n"
            mcap = scores.get("market_cap_usd", 0)
            if mcap:
                prompt += f"Market Cap: ${mcap:,.0f}\n"
            fdv = scores.get("fully_diluted_val", 0)
            if fdv:
                prompt += f"Fully Diluted Val: ${fdv:,.0f}\n"
            if "fdv_mcap_ratio" in scores:
                prompt += f"FDV/MCap Ratio: {scores['fdv_mcap_ratio']:.2f}x — Dilution Risk: {scores.get('dilution_risk', 'N/A')}\n"
            if "supply_ratio" in scores:
                prompt += f"Supply Circulating: {scores['supply_ratio']:.1f}% — {scores.get('supply_read', 'N/A')}\n"
            prompt += f"Hard Cap: {'Yes' if scores.get('has_hard_cap') else 'No'}\n"
            if "ath_distance_pct" in scores:
                prompt += f"Distance from ATH: {scores['ath_distance_pct']:+.1f}% — {scores.get('ath_read', 'N/A')}\n"
            price_changes = scores.get("price_changes", {})
            if price_changes:
                parts = [f"{period}: {change:+.1f}%" for period, change in price_changes.items()]
                prompt += f"Price Changes: {' | '.join(parts)}\n"
            prompt += "\n"

        # Static profile section (fallback)
        if "coin_description" in scores and "market_cap_rank" not in scores:
            prompt += f"=== ASSET PROFILE (static) ===\n"
            prompt += f"Description: {scores['coin_description']}\n"
            prompt += f"Sector: {scores.get('sector', 'Unknown')}\n"
            prompt += f"Supply: {scores.get('supply_dynamics_note', 'Unknown')}\n\n"
        elif "sector" in scores:
            prompt += f"Sector: {scores['sector']}\n\n"

        prompt += f"1. VALUE ASSESSMENT: {scores['value_score']:+.3f} ({scores['value_label']})\n"
        prompt += f"   Interpretation: Asset is {'undervalued' if scores['value_score'] > 0.15 else 'overvalued' if scores['value_score'] < -0.15 else 'near fair value'} based on cycle position + institutional flow.\n"

        prompt += f"\n2. MARKET CYCLE: {scores['cycle_score']:+.3f} ({scores['cycle_label']})\n"
        if "cycle_phase" in scores:
            prompt += f"   Phase: {scores['cycle_phase']}\n"
        if "pct_from_sma200" in scores:
            prompt += f"   Distance from SMA200: {scores['pct_from_sma200']:+.1f}%\n"
        if "cycle_risk" in scores:
            prompt += f"   Risk: {scores['cycle_risk']}\n"
        if "ma_cycle_confirmation" in scores:
            prompt += f"   MA Confirmation: {scores['ma_cycle_confirmation']}\n"

        prompt += f"\n3. INSTITUTIONAL ACTIVITY: {scores['institutional_score']:+.3f} ({scores['institutional_label']})\n"
        if "volume_ratio" in scores:
            prompt += f"   Volume Ratio: {scores['volume_ratio']:.2f}x average\n"
        if "institutional_read" in scores:
            prompt += f"   Read: {scores['institutional_read']}\n"
        if "liquidity_read" in scores:
            prompt += f"   Liquidity: {scores['liquidity_read']}\n"

        prompt += f"\n4. RISK ASSESSMENT: {scores['risk_score']:.3f} ({'HIGH' if scores['risk_score'] > 0.6 else 'MODERATE' if scores['risk_score'] > 0.3 else 'LOW'})\n"
        if "atr_pct" in scores:
            prompt += f"   ATR/Price: {scores['atr_pct']:.3f}%\n"
        if "volatility_risk" in scores:
            prompt += f"   Volatility: {scores['volatility_risk']}\n"
        if "bb_squeeze" in scores:
            prompt += f"   BB State: {scores['bb_squeeze']}\n"

        # CoinPaprika cross-validation data
        paprika = market_data.get("paprika_coin")
        if paprika:
            prompt += f"\n5. COINPAPRIKA CROSS-VALIDATION:\n"
            beta = paprika.get("beta_value", 0)
            if beta:
                prompt += f"   Beta: {beta:.3f} ({'High volatility' if abs(beta) > 1.5 else 'Moderate' if abs(beta) > 0.8 else 'Low volatility'} vs market)\n"
            pct_30d = paprika.get("pct_change_30d", 0)
            pct_7d = paprika.get("pct_change_7d", 0)
            pct_1h = paprika.get("pct_change_1h", 0)
            if pct_30d:
                prompt += f"   30d: {pct_30d:+.1f}% | 7d: {pct_7d:+.1f}% | 1h: {pct_1h:+.1f}%\n"
            pct_ath = paprika.get("pct_from_ath", 0)
            if pct_ath:
                prompt += f"   Distance from ATH: {pct_ath:+.1f}%\n"

        prompt += (
            f"\nApply the DECISION RULES from your instructions to these scores. "
            f"Evaluate the fundamental value and produce your signal."
        )

        return prompt
