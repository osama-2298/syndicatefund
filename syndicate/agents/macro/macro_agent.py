"""
Macro Analysis Agent.

Analyzes market-wide conditions using CoinGecko global data:
- Total crypto market cap and direction
- BTC dominance (capital rotation signal)
- ETH dominance
- Overall market volume trends
- Market-wide momentum (is money flowing in or out of crypto?)

This agent doesn't analyze individual coins — it reads the macro environment
and tells us whether the overall market is favorable for risk-on trades.

Data source: CoinGecko /global endpoint (free, no auth).
"""

from __future__ import annotations

from typing import Any

from syndicate.agents.base import BaseAgent
from syndicate.data.models import TeamType


def compute_macro_scores(
    global_data: dict,
    btc_stats_24h: dict,
    btc_change_30d: float | None = None,
) -> dict[str, Any]:
    """
    Pre-compute macro market scores from CoinGecko global data.
    All math happens here.
    """
    scores: dict[str, Any] = {}

    # ── 1. MARKET CAP TREND (-1 to +1) ──
    mcap_change_24h = global_data.get("market_cap_change_24h_pct", 0)
    scores["total_market_cap_usd"] = global_data.get("total_market_cap_usd", 0)
    scores["mcap_change_24h"] = round(mcap_change_24h, 2)

    if mcap_change_24h > 3:
        scores["mcap_trend"] = "STRONG_INFLOW"
        mcap_signal = 0.8
    elif mcap_change_24h > 1:
        scores["mcap_trend"] = "MODERATE_INFLOW"
        mcap_signal = 0.4
    elif mcap_change_24h > -1:
        scores["mcap_trend"] = "FLAT"
        mcap_signal = 0.0
    elif mcap_change_24h > -3:
        scores["mcap_trend"] = "MODERATE_OUTFLOW"
        mcap_signal = -0.4
    else:
        scores["mcap_trend"] = "STRONG_OUTFLOW"
        mcap_signal = -0.8

    scores["mcap_signal"] = round(mcap_signal, 3)

    # ── 2. BTC DOMINANCE (-1 to +1) ──
    # Rising BTC dominance = risk-off (money flowing from alts to BTC)
    # Falling BTC dominance = risk-on (money flowing from BTC to alts)
    btc_dom = global_data.get("btc_dominance", 50)
    scores["btc_dominance"] = btc_dom

    if btc_dom > 60:
        scores["btc_dom_read"] = "HIGH — Risk-off, capital concentrating in BTC"
        dom_signal = -0.5  # Bearish for alts
    elif btc_dom > 55:
        scores["btc_dom_read"] = "ELEVATED — Moderate flight to safety"
        dom_signal = -0.2
    elif btc_dom > 45:
        scores["btc_dom_read"] = "BALANCED — Normal distribution"
        dom_signal = 0.1
    elif btc_dom > 38:
        scores["btc_dom_read"] = "LOW — Alt season conditions, risk-on"
        dom_signal = 0.5
    else:
        scores["btc_dom_read"] = "VERY_LOW — Extreme alt season, possible froth"
        dom_signal = 0.3  # Still positive but watch for reversal

    scores["btc_dom_signal"] = round(dom_signal, 3)

    # ETH dominance
    eth_dom = global_data.get("eth_dominance", 15)
    scores["eth_dominance"] = eth_dom

    # ── 3. VOLUME TREND (-1 to +1) ──
    total_vol = global_data.get("total_volume_usd", 0)
    scores["total_volume_usd"] = total_vol

    # BTC 24h change as market direction proxy
    btc_change = float(btc_stats_24h.get("price_change_pct", 0))
    scores["btc_24h_change"] = round(btc_change, 2)

    if btc_change > 3:
        vol_direction = 0.7
        scores["market_direction"] = "STRONG_BULLISH"
    elif btc_change > 1:
        vol_direction = 0.3
        scores["market_direction"] = "BULLISH"
    elif btc_change > -1:
        vol_direction = 0.0
        scores["market_direction"] = "NEUTRAL"
    elif btc_change > -3:
        vol_direction = -0.3
        scores["market_direction"] = "BEARISH"
    else:
        vol_direction = -0.7
        scores["market_direction"] = "STRONG_BEARISH"

    scores["vol_direction_signal"] = round(vol_direction, 3)

    # ── 4. LONGER-TERM MACRO (if 30d data available) ──
    if btc_change_30d is not None:
        scores["btc_change_30d"] = round(btc_change_30d, 2)
        if btc_change_30d > 20:
            scores["macro_30d_read"] = "STRONG_UPTREND"
            macro_30d = 0.6
        elif btc_change_30d > 5:
            scores["macro_30d_read"] = "UPTREND"
            macro_30d = 0.3
        elif btc_change_30d > -5:
            scores["macro_30d_read"] = "RANGING"
            macro_30d = 0.0
        elif btc_change_30d > -20:
            scores["macro_30d_read"] = "DOWNTREND"
            macro_30d = -0.3
        else:
            scores["macro_30d_read"] = "STRONG_DOWNTREND"
            macro_30d = -0.6
        scores["macro_30d_signal"] = round(macro_30d, 3)

    # ── 5. COMPOSITE MACRO SCORE ──
    signals = [mcap_signal, dom_signal, vol_direction]
    if "macro_30d_signal" in scores:
        signals.append(scores["macro_30d_signal"])

    composite = sum(signals) / len(signals)
    scores["composite_score"] = round(composite, 3)
    scores["composite_label"] = (
        "STRONG_RISK_ON" if composite > 0.4 else
        "RISK_ON" if composite > 0.15 else
        "NEUTRAL" if composite > -0.15 else
        "RISK_OFF" if composite > -0.4 else
        "STRONG_RISK_OFF"
    )

    return scores


class MacroAgent(BaseAgent):
    """
    Macro analyst — reads market-wide conditions using real CoinGecko global data.
    """

    @property
    def team_type(self) -> TeamType:
        return TeamType.MACRO

    @property
    def system_prompt(self) -> str:
        return (
            "You are a senior macro analyst at a quantitative crypto hedge fund.\n\n"
            "You read MARKET-WIDE conditions using real data: total market cap, BTC dominance, "
            "Polymarket prediction markets (Fed rates, recession odds), and global liquidity.\n\n"
            "YOUR TASK: Predict whether the macro environment favors HIGHER or LOWER crypto prices.\n"
            "You MUST pick BULLISH or BEARISH. There is no neutral option.\n"
            "Your signal applies to ALL positions — it's a risk-on/risk-off call.\n\n"
            "DIRECTION RULES:\n"
            "- BULLISH if: market cap growing, BTC dominance stable/falling (money entering crypto "
            "and rotating into alts), prediction markets show low recession risk, Fed dovish.\n"
            "- BEARISH if: market cap shrinking, BTC dominance rising sharply (flight to safety), "
            "prediction markets show high recession risk, Fed hawkish.\n"
            "- Use Polymarket data heavily — it reflects real-money conviction on macro events.\n\n"
            "CONVICTION SCALE:\n"
            "- 9-10: All macro signals strongly aligned + prediction markets confirm. Rare.\n"
            "- 7-8: Clear macro direction with most signals + prediction markets agreeing.\n"
            "- 5-6: Moderate lean. Some mixed signals but net direction visible.\n"
            "- 3-4: Slight lean. Macro is transitional.\n"
            "- 1-2: No clear macro read. Pick the direction the composite leans.\n\n"
            "RULES:\n"
            "- Do NOT invent data. Reference provided scores.\n"
            "- Keep reasoning to 2-3 sentences.\n"
            "- Macro moves slowly. Low conviction is expected and fine."
        )

    def build_analysis_prompt(self, market_data: dict[str, Any]) -> str:
        """Build prompt with pre-computed macro scores."""
        global_data: dict = market_data["global_data"]
        btc_stats: dict = market_data["stats_24h"]
        btc_change_30d = market_data.get("btc_change_30d")

        scores = compute_macro_scores(global_data, btc_stats, btc_change_30d)

        total_mcap = scores["total_market_cap_usd"]
        prompt = (
            f"Read the macro crypto market environment and produce a signal for {self.profile.symbol}.\n\n"
            f"=== PRE-COMPUTED MACRO SCORES (Real CoinGecko Data) ===\n"
            f"COMPOSITE: {scores['composite_score']:+.3f} ({scores['composite_label']})\n\n"
            f"1. MARKET CAP TREND: {scores['mcap_signal']:+.3f}\n"
            f"   Total Crypto Market Cap: ${total_mcap:,.0f}\n"
            f"   24h Change: {scores['mcap_change_24h']:+.2f}% — {scores['mcap_trend']}\n\n"
            f"2. BTC DOMINANCE: {scores['btc_dom_signal']:+.3f}\n"
            f"   BTC Dominance: {scores['btc_dominance']:.1f}%\n"
            f"   ETH Dominance: {scores['eth_dominance']:.1f}%\n"
            f"   Read: {scores['btc_dom_read']}\n\n"
            f"3. MARKET DIRECTION: {scores['vol_direction_signal']:+.3f}\n"
            f"   BTC 24h: {scores['btc_24h_change']:+.2f}%\n"
            f"   Direction: {scores['market_direction']}\n"
        )

        if "macro_30d_signal" in scores:
            prompt += (
                f"\n4. 30-DAY MACRO: {scores['macro_30d_signal']:+.3f}\n"
                f"   BTC 30d Change: {scores['btc_change_30d']:+.2f}%\n"
                f"   Trend: {scores['macro_30d_read']}\n"
            )

        # Prediction market data (Polymarket — real money probabilities)
        pred_markets = market_data.get("prediction_markets")
        if pred_markets:
            highlights = pred_markets.get("highlights", [])
            if highlights:
                prompt += f"\n5. PREDICTION MARKETS (Polymarket — real money bets):\n"
                for m in highlights[:7]:
                    question = m.get("question", m.get("event_title", "?"))
                    if len(question) > 60:
                        question = question[:59] + "…"
                    probs = m.get("probabilities", {})
                    vol = m.get("volume", 0)
                    prob_str = " / ".join(f"{k}: {v:.0f}%" for k, v in probs.items() if v > 0)
                    vol_str = f"${vol:,.0f}" if vol > 0 else "?"
                    prompt += f"   {question}\n     → {prob_str} (vol: {vol_str})\n"

        # BTC derivatives for macro risk reading
        btc_deriv = market_data.get("btc_derivatives")
        if btc_deriv:
            funding = btc_deriv.get("funding", {})
            oi = btc_deriv.get("open_interest", {})
            if funding or oi:
                prompt += f"\n6. BTC DERIVATIVES (risk gauge):\n"
                if funding:
                    prompt += f"   Funding: {funding.get('current_rate_pct', 0):+.4f}% — {funding.get('sentiment', 'N/A')}\n"
                if oi:
                    prompt += f"   Open Interest: {oi.get('open_interest', 0):,.0f} BTC\n"

        prompt += "\nRead the macro environment and produce your signal."
        return prompt
