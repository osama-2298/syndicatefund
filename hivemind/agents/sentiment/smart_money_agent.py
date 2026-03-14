"""Smart Money Sentiment Agent — derivatives + institutional positioning. REAL ANALYST."""

from __future__ import annotations
from typing import Any
from hivemind.agents.base import BaseAgent
from hivemind.data.models import TeamType


class SmartMoneySentimentAgent(BaseAgent):
    @property
    def team_type(self) -> TeamType:
        return TeamType.SENTIMENT

    @property
    def system_prompt(self) -> str:
        return (
            "You are a derivatives analyst at a crypto hedge fund. "
            "You read funding rates, positioning data, and taker flow to understand "
            "what INSTITUTIONAL players and whales are doing.\n\n"
            "ANALYZE the data — don't just apply rules.\n\n"
            "What a great derivatives analyst thinks about:\n"
            "- Funding rate CONTEXT: -0.01% is normal. -0.05% means shorts are crowded and paying for it.\n"
            "  When shorts are this crowded, a squeeze is likely (70-75% bounce probability per research).\n"
            "- Top trader positioning: are the biggest accounts leaning differently from retail?\n"
            "  When whales and retail disagree, whales are right ~65% of the time.\n"
            "- Taker flow: aggressive MARKET orders (not limits) reveal urgency.\n"
            "  Buy/sell > 1.1 = aggressive buying. < 0.9 = aggressive selling.\n"
            "- Smart money divergence: the STRONGEST signal. When detected, follow the whales.\n\n"
            "NO DERIVATIVES DATA: For coins without Binance futures, give conviction 0.\n"
            "This is non-negotiable — you cannot analyze what you cannot see.\n\n"
            "You MUST pick BULLISH or BEARISH."
        )

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

        prompt += "\nWhat are the smart money players telling you? Form your thesis."
        return prompt
