"""Smart Money Sentiment Agent — derivatives + institutional positioning. REAL ANALYST."""

from __future__ import annotations
from pathlib import Path
from typing import Any
from syndicate.agents.base import BaseAgent
from syndicate.agents.team_manager import _load_manager_knowledge
from syndicate.data.models import TeamType

_TRADING_KB = _load_manager_knowledge(Path(__file__).parent / "trading_knowledge.md")


class SmartMoneySentimentAgent(BaseAgent):
    @property
    def team_type(self) -> TeamType:
        return TeamType.SENTIMENT

    @property
    def system_prompt(self) -> str:
        base = (
            "You are a derivatives analyst at a crypto hedge fund.\n\n"
            "ANALYZE funding, positioning, and taker flow to read institutional behavior.\n\n"
            "RESEARCH-BACKED EVIDENCE:\n"
            "- Funding < -0.05%: 70-75% bounce probability within 7 days (research-confirmed).\n"
            "- Funding > +0.10%: 60-70% correction probability.\n"
            "- When whales and retail disagree: whales are right ~65% of the time.\n"
            "- Taker buy/sell > 1.1 = aggressive institutional buying.\n"
            "- Taker buy/sell < 0.9 = aggressive institutional selling.\n\n"
            "VARIANT PERCEPTION: The derivatives market often sees things before spot.\n"
            "Negative funding + bullish technicals = the derivatives crowd is WRONG.\n"
            "They're short against an intact trend. Squeeze fuel.\n"
            "Positive funding + bearish technicals = the derivatives crowd is WRONG.\n"
            "They're long into a weakening trend. Liquidation risk.\n\n"
            "WHAT WOULD INVALIDATE: 'Short squeeze thesis dies if OI collapses (shorts cover voluntarily)\n"
            "or if a fundamental catalyst (exchange hack, regulatory action) justifies the shorts.'\n\n"
            "NO DERIVATIVES DATA: Give conviction 0. Non-negotiable.\n"
            "You MUST pick BULLISH or BEARISH."
        )
        if _TRADING_KB:
            base += f"\n=== TRADING KNOWLEDGE ===\n{_TRADING_KB}\n"
        return base

    def build_analysis_prompt(self, market_data: dict[str, Any]) -> str:
        smart_money = market_data.get("smart_money")
        prompt = f"What are institutions and whales doing with {self.profile.symbol}?\n\n"

        if smart_money:
            prompt += "=== DERIVATIVES DATA (live from Binance Futures) ===\n\n"

            # Funding
            funding_pct = smart_money.get("funding_rate_pct", 0)
            funding_sent = smart_money.get("funding_sentiment", "UNKNOWN")
            prompt += f"FUNDING RATE: {funding_pct:+.4f}% — {funding_sent}\n"
            if funding_pct < -0.03:
                prompt += f"  ** Shorts are PAYING significantly. Squeeze setup. Historical bounce rate: 70-75% **\n"
            elif funding_pct > 0.05:
                prompt += f"  ** Longs are heavily crowded. Liquidation risk elevated. **\n"

            # Top traders
            if "top_trader_ratio" in smart_money:
                ratio = smart_money["top_trader_ratio"]
                long_pct = smart_money["top_trader_long_pct"]
                signal = smart_money.get("top_trader_signal", "")
                prompt += f"\nTOP TRADERS (whales): {long_pct:.0f}% long / {100-long_pct:.0f}% short (ratio: {ratio:.3f})\n"
                prompt += f"  Signal: {signal}\n"

            # Taker flow
            if "taker_buy_sell_ratio" in smart_money:
                taker = smart_money["taker_buy_sell_ratio"]
                taker_sig = smart_money.get("taker_signal", "")
                prompt += f"\nTAKER FLOW: Buy/Sell ratio = {taker:.4f}\n"
                prompt += f"  {taker_sig}\n"
                if taker > 1.15:
                    prompt += f"  Aggressive BUYERS dominating — institutional accumulation likely\n"
                elif taker < 0.85:
                    prompt += f"  Aggressive SELLERS dominating — institutional distribution likely\n"

            # Divergence
            divergence = smart_money.get("divergence")
            magnitude = smart_money.get("divergence_magnitude", 0)
            if divergence and divergence not in ("ALIGNED", None):
                prompt += f"\nSMART MONEY DIVERGENCE: {divergence} (magnitude: {magnitude:.3f})\n"
                prompt += f"  ** When whales and retail disagree, follow the whales. **\n"
            elif divergence == "ALIGNED":
                prompt += f"\nWhales and retail are ALIGNED (no divergence detected).\n"
        else:
            base = self.profile.symbol.replace("USDT", "")
            prompt += f"** NO DERIVATIVES DATA for {base}. No Binance futures exist for this coin. **\n"
            prompt += f"Give conviction 0. You cannot analyze what you cannot see.\n"

        # Cross-exchange funding rates (from multi-exchange scan)
        cross_funding = market_data.get("cross_exchange_funding")
        if cross_funding:
            prompt += "\n=== CROSS-EXCHANGE FUNDING RATES ===\n"
            rates = cross_funding.get("rates", {})
            for exchange, rate in sorted(rates.items()):
                prompt += f"  {exchange.upper()}: {rate:+.4f}%\n"
            spread = cross_funding.get("spread_pct", 0)
            ann = cross_funding.get("annualized_spread_pct", 0)
            if spread > 0.01:
                highest = cross_funding.get("highest", {})
                lowest = cross_funding.get("lowest", {})
                prompt += (
                    f"\n  SPREAD: {spread:.4f}% ({ann:.1f}% annualized)\n"
                    f"  Highest: {highest.get('exchange', '?').upper()} ({highest.get('rate_pct', 0):+.4f}%)\n"
                    f"  Lowest: {lowest.get('exchange', '?').upper()} ({lowest.get('rate_pct', 0):+.4f}%)\n"
                    f"  ** Cross-exchange funding divergence detected. Carry arb potential. **\n"
                )

        prompt += "\nWhat are the smart money players telling you? Form your thesis."
        return prompt
