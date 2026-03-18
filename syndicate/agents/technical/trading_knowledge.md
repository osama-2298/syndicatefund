# Technical Analysis Trading Knowledge

## 29-Indicator Weighted Scoring System (Crypto-Optimized)

### Core Indicators (Weight 1.0 — always check these)
- **RSI(14)**: <30 oversold, >70 overbought. Hidden divergence = trend continuation signal. Regular divergence = reversal warning
- **MACD**: Line/signal crossover + histogram momentum. Centerline cross confirms trend. Declining histogram = momentum fading even if still positive
- **Bollinger Bands**: Width squeeze (<0.05) = imminent breakout. Price walking upper band = strong uptrend, not "overbought." Band expansion after squeeze = trade in direction of breakout
- **OBV (On-Balance Volume)**: Most reliable divergence detector. OBV rising while price flat = accumulation. OBV falling while price rising = distribution (bearish divergence)
- **Ichimoku Cloud** (crypto-optimized: 10/30/60, NOT traditional 9/26/52): Price above cloud = bullish filter. Tenkan/Kijun cross above cloud = high-quality buy. Cloud twist = trend change incoming. Chikou span confirmation required
- **EMA(12/26)**: EMA cross above SMA = momentum building. All EMAs stacked bullishly (12>26>50>200) = strongest trend signal
- **SMA(20/50/200)**: Golden cross (50>200) = regime shift bullish, 64% contrarian buy at death cross with median +89% 12mo. Price above all = textbook uptrend
- **MFI (Money Flow Index)**: Volume-weighted RSI. <20 with rising price = institutional accumulation. >80 with falling price = distribution

### Strong Indicators (Weight 0.75)
- **CCI**: >100 = strong uptrend, <-100 = strong downtrend. Zero-line cross confirms direction
- **Aroon**: Aroon Up >70 and Down <30 = strong uptrend. Crossover = early trend change signal
- **DEMA/MESA**: Faster trend detection than standard MA. Use for early entry confirmation

### Supporting Indicators (Weight 0.5)
- **ADX**: >25 = trending market (use trend-following). <20 = ranging (use mean reversion). >40 = very strong trend, don't fade it
- **DMI**: +DI > -DI = bullish pressure. Crossover with ADX >25 = confirmed trend start
- **VWAP**: Institutional benchmark. Price above VWAP = institutional buying bias. Reclaim after sell-off = bullish
- **ATR**: Volatility gauge. Use for position sizing and stop placement. ATR expansion = trend strengthening

## 7-Tier Signal Classification
1. **STRONG_BUY**: 80%+ indicators aligned bullish + ADX >25 + volume confirms + no bearish divergence
2. **BUY**: 65-80% aligned + at least 2 core indicators bullish
3. **WEAK_BUY**: 50-65% aligned, mixed signals but leaning bullish
4. **NEUTRAL**: No clear direction, indicators evenly split
5. **WEAK_SELL**: 50-65% aligned bearish
6. **SELL**: 65-80% bearish + core indicators confirm
7. **STRONG_SELL**: 80%+ bearish + high volume + bearish divergences

## High-Conviction Setup Criteria
A setup qualifies as high-conviction when ALL of:
- Signal is STRONG_BUY or STRONG_SELL with confidence >= 0.7
- Price above/below Ichimoku cloud (confirming direction)
- OBV confirms (no divergence against the signal)
- ADX > 25 (confirmed trend, not ranging noise)
- Volume ratio > 1.2x average (institutional participation)
- No Bollinger Band squeeze (or breaking out of one in signal direction)

## Divergence Detection Framework
- **Regular Bullish**: Price makes lower low, indicator makes higher low → reversal UP likely
- **Regular Bearish**: Price makes higher high, indicator makes lower high → reversal DOWN likely
- **Hidden Bullish**: Price makes higher low, indicator makes lower low → trend CONTINUATION up
- **Hidden Bearish**: Price makes lower high, indicator makes higher high → trend CONTINUATION down
- **Priority**: OBV divergence > RSI divergence > MACD divergence (OBV is most reliable)

## Bollinger Band Squeeze Detection
- Squeeze = BB width in bottom 20th percentile of last 100 periods
- Squeeze duration > 10 periods = higher probability of large breakout
- Trade in direction of breakout, NOT before. Wait for close outside band
- Volume spike on breakout confirms. No volume = false breakout risk

## 100-Point Technical Scoring Model
- **Trend Strength (30 pts)**: MA arrangement (stacked?), price position vs key MAs, trend duration
- **Momentum (25 pts)**: RSI health zone, MACD direction + histogram, volume coordination
- **Chart Patterns (20 pts)**: Reversal patterns, consolidation quality, candlestick signals
- **Support/Resistance (15 pts)**: Distance to key levels, breakout quality, Fibonacci alignment
- **Market Sentiment (10 pts)**: Relative strength vs BTC, sector linkage

## Risk Management Rules
- **Position sizing**: Kelly Criterion x 0.5 (conservative half-Kelly). Never exceed 20% single position
- **Stop placement**: Support level - 2% or 2-3x ATR below entry. NEVER arbitrary round numbers
- **Staged entry**: 50% initial → 30% on confirmation → 20% on momentum (pyramid 50/30/20)
- **Take profit**: 30% at 1R, 30% at 2R, trail remainder with 3x ATR trailing stop
- **Risk-reward minimum**: 1:2 ratio required. If stop is 5%, target minimum 10%

## Backtested Strategy Benchmarks (Know What Works)
- **SMA Crossover (50/200)**: Sharpe ~0.6, Win Rate ~45%, strong in trending markets, fails in chop
- **RSI Reversal (<30 buy, >70 sell)**: Sharpe ~0.5, better with trend filter (only buy RSI<30 above SMA200)
- **MACD + RSI Combined**: Sharpe 1.0-1.44, best performer. Requires both to confirm
- **Bollinger Band Breakout**: Sharpe ~0.7, works best after squeeze periods
- **Mean Reversion**: Sharpe ~0.8, only in ranging (ADX <20) regimes
- **Transaction costs**: Always assume 80 bps round-trip for crypto (0.1% commission + 0.05% slippage x2)
