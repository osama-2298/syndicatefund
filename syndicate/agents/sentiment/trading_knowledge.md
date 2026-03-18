# Sentiment & Smart Money Trading Knowledge

## Smart Money On-Chain Signal Tracking
- **Smart money addresses**: Track wallets with >60% win rate over 100+ trades
- **Key signals**: Smart Money ADD holdings (accumulation), REDUCE holdings (distribution)
- **Signal lifecycle**: ACTIVE (just triggered) → TIMEOUT (no follow-through) → COMPLETED (hit target)
- **Chain-specific patterns**: BSC has faster meme cycles, Solana DEX has institutional flow, Ethereum mainnet = largest whale activity
- **Volume-weighted signals**: A whale buying $5M is more significant than 100 wallets buying $50K each
- **Tag system**: DEX Paid (token dev bought liquidity = committed), Whale Buy/Sell, KOL (influencer) trades

## Social Hype & Ranking Interpretation
- **Social Hype Leaderboard**: Measures real-time social sentiment acceleration. Rising hype + falling price = divergence (potential bottom). Rising hype + rising price = momentum confirmation
- **Smart Money Inflow Rank**: Institutional buying ranked by volume. Top 10 by inflow = strongest institutional conviction. Cross-reference with social hype — smart money often moves BEFORE social hype
- **Meme Token Pulse**: Launchpad token activity. High new-launch volume = risk-on sentiment. Dying launch activity = risk-off
- **Address PnL Leaderboard**: Follow the money. Top 10 traders by PnL are worth tracking. If top traders are net long = bullish. Net short = bearish. More reliable than any sentiment survey

## Crowd Psychology Patterns (Backtested)
- **Extreme Fear (F&G 0-10)**: Historically 8.0 Sharpe, +440% median 12-month return. BUT requires structure confirmation (price above key support)
- **Extreme Greed (F&G 75-100)**: Not automatically bearish. Can persist in strong bulls. Only bearish when COMBINED with rising funding + declining OBV
- **Social media lag**: Reddit sentiment lags price by 12-24h. Twitter lags by 2-6h. Smart money leads by 1-3 days. Trade the LEADER, not the lagger
- **Contrarian timing**: Extreme crowd sentiment is contrarian 80% of the time at extremes, but only 50% in the middle (40-60 range is noise)
- **Narrative analysis**: "This time is different" = usually isn't. "Bottom is in" during crash = too early. "Dead cat bounce" during actual reversal = missed opportunity. READ the narrative, don't just count mentions

## Derivatives Market Intelligence
- **Funding rates**: Negative < -0.03% = 70-75% bounce within 7 days. Positive > +0.10% = 60-70% correction probability
- **Open Interest + Price**: Rising OI + rising price = new money entering (trend healthy). Rising OI + falling price = shorts building (potential squeeze). Falling OI = positions closing (trend weakening)
- **Taker buy/sell ratio**: >1.15 = aggressive institutional buying (strongest short-term bullish signal). <0.85 = aggressive institutional selling
- **Long/Short ratio divergence**: When top traders (whales) and retail disagree, follow whales — correct 65% of the time
- **Cross-exchange funding**: Different rates across exchanges signal market inefficiency. Binance typically leads. Large spread = arb opportunity AND market stress signal
- **Liquidation cascades**: Large liquidation events (>$100M in 4h) often mark short-term bottoms. Smart money buys the liquidation wick

## Regime Detection via Sentiment
- **Bull regime signals**: F&G consistently 50-75, social volume rising, smart money net long, funding mildly positive (0.01-0.03%)
- **Bear regime signals**: F&G consistently 20-40, social volume declining, smart money reducing, funding negative
- **Transition signals**: Sharp F&G move (>20 points in a week), smart money flow reversal, social narrative shift (from "when moon" to "is crypto dead" or vice versa)
- **HMM-based regime identification**: Historical returns cluster into 2-3 regimes. High-vol regime = reduce position sizes. Low-vol regime = increase sizes. Transition regime = reduce conviction

## Statistical Rigor for Sentiment Signals
- **Information Coefficient**: A sentiment signal needs IC > 0.02 to add value (most social signals fail this test)
- **Signal decay**: Social media sentiment signals decay within 2-8 hours. Derivatives signals persist 1-3 days. On-chain whale signals persist 3-7 days
- **Multiple testing**: When checking 20 sentiment metrics, expect 1 false positive by chance. Require confirmation from multiple independent sources
- **Sample size**: Minimum 30 observations of a sentiment pattern before trusting it as a signal
