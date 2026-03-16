# Technical Indicator Performance Data for Crypto Markets

**Research compiled: March 2026**
**Data sources: Academic papers, backtesting platforms, quantitative strategy sites, on-chain analytics**

---

## Table of Contents
1. [RSI (Relative Strength Index)](#1-rsi-relative-strength-index)
2. [MACD (Moving Average Convergence Divergence)](#2-macd-moving-average-convergence-divergence)
3. [Moving Average Crossovers (Golden Cross / Death Cross)](#3-moving-average-crossovers-golden-cross--death-cross)
4. [Price Relative to SMA 200](#4-price-relative-to-sma-200)
5. [Volume Spikes](#5-volume-spikes)
6. [Bollinger Bands](#6-bollinger-bands)
7. [Funding Rate Extremes](#7-funding-rate-extremes)
8. [Multi-Timeframe Alignment](#8-multi-timeframe-alignment)
9. [RSI Divergence](#9-rsi-divergence)
10. [Indicator Comparison and Sharpe Ratios](#10-indicator-comparison-and-sharpe-ratios)
11. [Academic Research Summary](#11-academic-research-summary)

---

## 1. RSI (Relative Strength Index)

### 1a. RSI < 30 on BTC (Oversold)

**Historical rarity:** Bitcoin's 14-day RSI has fallen below 30 only three times in its entire history (most recently February 2026 at 25.6). The previous two sub-30 readings preceded rallies of +1,700% and +9,900% respectively, though these played out over multi-year timeframes.

**Forward returns (daily RSI < 30):**

| Metric | Value | Notes |
|--------|-------|-------|
| 7-day avg return | +4% to +8% | Modest bounce typical; varies by market regime |
| 30-day avg return | +5% to +15% | Higher in secular bull markets, near-flat or negative in bear markets |
| Win rate (positive 30-day return) | ~60-65% | Improves to ~70% when combined with support level confirmation |
| Recovery probability | ~65% | Approximate likelihood of short-term reversal in highly volatile assets |

**Backtest study (RSI oversold + support level break, BTC daily, 2022-2025):**
- Total trades: 294
- Win rate: 22.11% (strict profit-target based)
- Profit factor: 1.16
- Annualized return: 19.67%
- Max drawdown: 23.34%
- Average trade duration: ~2 days

**Key context:** In the 2022 bear market, oversold readings produced only meager bounces and multi-week consolidations that gave way to deeper sell-offs. In bull markets (2023-2024), oversold readings on daily RSI were extremely rare and reliably marked swing lows.

**RSI-based strategy total return (2018-2022):** 773.65% vs. 275.22% buy-and-hold (2.8x outperformance), though this used an optimized RSI approach, not simple buy-at-30.

### 1b. RSI > 70 on BTC (Overbought)

**Forward returns (daily RSI > 70):**

| Metric | Value | Notes |
|--------|-------|-------|
| 7-day avg return | -1% to +5% | Highly regime-dependent; trending markets continue up |
| 30-day avg return | -3% to +10% | Strong bull markets frequently stay overbought for weeks |
| Signal reliability as sell | LOW | RSI stayed above 70 for most of 2021 bull run |

**Key finding (PMC academic study):** For cryptocurrencies that increased in value during the analyzed period, more cryptocurrencies achieved above-average results AFTER the RSI hit the overbought level. This means selling at RSI > 70 in a bull market is counterproductive.

**Historical example:** By November 2024, RSI reached 76 as Bitcoin peaked near $110,000 -- a classic overbought signal that did precede a correction. But during the 2021 bull run, RSI stayed above 70 for extended periods while price continued rising.

**Recommended approach:** RSI > 70 is more useful as a risk-management alert (reduce position size, tighten stops) than as a sell signal. Only reliable when combined with bearish divergence + volume decline.

### 1c. RSI 70-30 Strategy (Traditional)

**Backtest on S&P 500 (proxy for mean-reversion assets, 1993-present):**
- Strategy: Buy when RSI(14) < 30, sell when RSI(14) > 70
- Total trades: 191 over 30+ years
- Average gain per trade: ~1%
- Max drawdown: exceeded -30%
- Annual return: significantly underperformed buy-and-hold

**Optimized RSI strategy (buy RSI < 45, sell RSI > 75):**
- 30 trades from 1993-present
- Annual return: 8.51% vs. 10.1% buy-and-hold (including dividends)

**Conclusion:** The mechanical 70/30 RSI strategy lacks robustness. It needs additional filters (volume, trend, support/resistance) to be profitable.

---

## 2. MACD (Moving Average Convergence Divergence)

### 2a. MACD Bullish Crossover Win Rates by Timeframe

| Timeframe | Win Rate (standalone) | Win Rate (with RSI filter) | Notes |
|-----------|----------------------|---------------------------|-------|
| 1H | ~37-40% | ~50-55% | High trade frequency, many whipsaws |
| 4H | ~45-50% | ~55-65% | Better signal quality, fewer false signals |
| 1D | ~50-55% | ~65-73% | Most commonly used; best standalone performance |
| 1W | ~55-60% | ~70-77% | Fewest signals but highest reliability |

**Specific backtest: 1H MACD crossover on BTC (Dec 2018 - Nov 2025):**
- Total trades: 2,262
- Sharpe ratio: 0.33
- Annual return: 49.39%
- Max drawdown: 51.85%

**With daily/1H trend filter (same period):**
- Trades: ~1,000
- Sharpe ratio: 0.80 (2.4x improvement)

**With trailing stop added:**
- Sharpe ratio: 1.07

**Multi-coin portfolio (BTC + ETH + ADA):**
- Annual return: 68.70%
- Sharpe ratio: 1.44

### 2b. MACD Bearish Crossover

| Timeframe | Win Rate (standalone) | Notes |
|-----------|----------------------|-------|
| 1H | ~35-40% | More false signals than bullish in trending market |
| 4H | ~40-48% | Moderate reliability |
| 1D | ~45-52% | Best for identifying trend changes |
| 1W | ~50-55% | Reliable for macro trend shifts |

**Key finding:** MACD bearish crossovers are LESS reliable than bullish crossovers in crypto because crypto has a structural long bias and tends to have sharper rallies than declines. Bearish MACD signals perform best in confirmed downtrends.

### 2c. MACD + RSI Combined Strategy

- Gate.io's January 2026 analysis: **77% win rate** in backtesting when combining RSI with MACD
- Adding Bollinger Bands as third confirmation: maintains **73-77% range** while reducing false signals
- General consensus: Combined MACD + RSI achieves **55-73% win rate** depending on market conditions

### 2d. MACD Performance Context

- In trending markets: ~65% win rate
- In choppy/ranging markets: ~45% win rate
- Standalone MACD crossovers win only ~40% of the time on BTCUSDT in raw backtests
- The indicator is a lagging indicator by nature; it works best for trend confirmation, not prediction

---

## 3. Moving Average Crossovers (Golden Cross / Death Cross)

### 3a. Golden Cross (SMA 50 > SMA 200) on BTC

**Short-term returns after golden cross:**

| Period | Average Return | Median Return | Win Rate |
|--------|---------------|---------------|----------|
| 7 days | +4.4% | ~+3% | ~65% |
| 30 days | +9.6% to +14.8% | ~+8% | ~70-81% |
| 3 months | +15% to +35% | ~+20% | ~65-75% |
| 6 months | +30% to +60% | ~+35% | ~70% |
| 12 months | +50% to +150%+ | ~+80% | ~70% |

**Specific historical golden cross events on BTC:**

| Date | Subsequent Rally |
|------|-----------------|
| February 2023 | +43% |
| September 2023 | +148% |
| October 2024 | +72.55% |
| September 2024 | +64% |
| April-August 2025 | +35% |

**Macro-environment filter:**
- During macroeconomic easing cycles: **81.2% success rate**, average 30-day return of **+14.8%**
- During tightening cycles: **59.3% success rate**, average 30-day return of **+7.3%**

**Volatility filter:**
- Low volatility (below 25th percentile): **74.3% success rate**, avg return **+13.8%**
- High volatility: **52.7% success rate**, avg return **+5.9%**

**First-ever weekly golden cross (January 2024):** The 50-week SMA crossed above the 200-week SMA for the first time in Bitcoin's history, preceding a continued bull run.

### 3b. Death Cross (SMA 50 < SMA 200) on BTC

**Forward returns after death cross:**

| Period | Average Return | Median Return | Positive Hit Rate |
|--------|---------------|---------------|-------------------|
| 1-3 weeks | ~0% (50/50) | +0.25% to +2.35% | ~50% |
| 2-3 months | +15% to +26% | ~+15% | ~60% |
| 6 months | Wide range | +30% | ~64% |
| 12 months | Wide range | +89% | ~64% |

**Critical regime distinction:**

| Market Type | 12-Month Return After Death Cross |
|-------------|-----------------------------------|
| 2024 (Post-ETF, structural bull) | +94% |
| 2023 (bear market ending) | Marked the bottom |
| 2022 (structural bear) | -52% |
| 2018 (structural bear) | -35% |
| 2014 (structural bear) | -48% to -56% |

**Key insight:** The death cross is historically a LAGGING indicator and more often appears NEAR market lows than at the start of prolonged declines. It has been a contrarian buying opportunity in 64% of cases. However, in structural bear markets (2014, 2018, 2022), it correctly signaled further downside.

---

## 4. Price Relative to SMA 200

### 4a. Price Above SMA 200

**General characteristics:**
- Volatility is substantially LOWER when the market trades above the SMA 200
- When market is below SMA, volatility is up to **80% higher** (average 64% higher across all MA values)
- Bitcoin has historically spent the majority of its time above the 200-day MA during bull market cycles

**200-Day SMA trading strategy (equities proxy, applicable framework):**
- End value of 218 vs. 190 for buy-and-hold (S&P 500 backtest)
- A 60-40 portfolio using 200-day SMA signal achieved:
  - CAGR: 9.9% (vs. 9.0% buy-and-hold)
  - Max drawdown: -15.7% (vs. -31% buy-and-hold)
  - Sharpe ratio: 0.70 (vs. 0.49 buy-and-hold)

**For Bitcoin specifically:**
- When BTC is above its 200-day MA: historically bullish regime with average annualized returns significantly above the full-period average
- When BTC is below its 200-day MA: historically coincides with bear markets; the 200-week MA has marked cycle bottoms in every major cycle

### 4b. Price Below SMA 200

- Higher volatility environment (64% higher on average)
- Historically corresponds to bear market phases in Bitcoin
- The 200-week moving average has served as the ultimate floor in every Bitcoin cycle
- Buying when price is below the 200-week MA has been the highest-conviction long-term entry signal in Bitcoin's history

---

## 5. Volume Spikes

### 5a. Volume Spike (>2x Average) with Price Up

**Follow-through characteristics:**

| Metric | Value | Notes |
|--------|-------|-------|
| Immediate follow-through (1-3 days) | ~55-65% | Higher if volume stays elevated |
| Breakout confirmation threshold | Volume >= 150% of 20-day average | More conservative than 2x |
| Sustained breakout probability | ~60-68% | When volume stays above average for 2-3 subsequent candles |
| False breakout rate | ~30-40% | Single-day spikes without follow-through volume |

**Key pattern:** Consistently high volume in the days FOLLOWING a breakout indicates sustained interest. A big spike that immediately drops off suggests a news-driven event or single large buyer without follow-through.

**Bullish confirmation:** If price pulls back slightly on LOWER volume after a volume spike breakout, this is actually bullish -- sellers did not come in force, and the breakout level likely holds as new support.

### 5b. Volume Spike (>2x Average) with Price Down

| Metric | Value | Notes |
|--------|-------|-------|
| Continuation (further selling) | ~50-60% | In downtrends, volume spikes down often mark capitulation |
| Reversal probability | ~40-50% | Capitulation volume can mark local bottoms |
| Climax selling identification | High volume + long lower wick | Often marks exhaustion |

**Key insight:** Volume spikes on down moves are harder to interpret. In bear markets, they often signal further downside. In bull markets, they more frequently represent capitulation / shakeout events that mark local bottoms. Context (trend, market structure) is critical.

**Important caveat:** Overemphasizing a single volume spike is a common trap. Consistency and patterns in volume matter more than one-off events. Isolated spikes are often news-related bursts without follow-through.

---

## 6. Bollinger Bands

### 6a. Bollinger Band Squeeze to Breakout

**Direction accuracy:**

| Condition | Accuracy | Notes |
|-----------|----------|-------|
| Squeeze breakout (standalone) | ~50% | Cannot predict direction from squeeze alone |
| Squeeze breakout with volume confirmation | ~60-65% | Volume >= 150% avg on breakout candle |
| Squeeze breakout with trend + volume confirmation | ~70-80% | When additional indicators confirm direction |

**Win rates by market condition:**

| Market Condition | Win Rate | Risk-Reward |
|-----------------|----------|-------------|
| Trending market (continuation signals) | 60-70% | 1:2 to 1:3 |
| Trending market (reversal signals) | 55-65% | 1:1.5 to 1:2 |
| Ranging market (bounce signals) | 65-75% | 1:1 to 1:2 |
| Low volatility squeeze play | 40-50% | 3:1+ |
| Any market (properly confirmed squeeze) | 70-75% | Varies |

**Crypto-specific notes:**
- Consider wider standard deviations (2.5 or 3 instead of 2) for crypto due to higher volatility
- The squeeze-breakout strategy works particularly well in crypto because these markets often consolidate before explosive moves
- A breakout accompanied by at least 50% above-average volume is significantly more likely to succeed
- Bollinger Band width at its lowest 6-month reading is a reliable squeeze signal

---

## 7. Funding Rate Extremes

### 7a. Funding Rate < -0.05% (Deeply Negative)

**Historical bounce data:**

| Metric | Value | Notes |
|--------|-------|-------|
| Bounce probability (7 days) | ~70-75% | Short-term mean reversion is highly likely |
| Average bounce size | +5% to +15% | Depends on how extreme the reading |
| Short squeeze probability | ~40-50% | When OI is also elevated |
| Prior signals at cycle bottoms | COVID crash, FTX collapse, 2021 China ban | All preceded significant recoveries |

**Recent data (Feb-Mar 2026):**
- Bitcoin's 30-day funding-rate percentile fell to 6%, its lowest since early 2023
- 25 of 30 days showed negative funding rates
- Funding hit approximately -6% (annualized) on February 28

**Historical pattern:** High negative funding rates combined with bearish bottoms have historically matched Bitcoin price bottoms. During events like the COVID-19 crash, FTX collapse, and 2021 China mining ban, extreme short positioning was followed by fast recovery.

### 7b. Funding Rate > +0.1% (Extremely Positive)

**Historical correction data:**

| Metric | Value | Notes |
|--------|-------|-------|
| Correction probability (7 days) | ~60-70% | Overcrowded longs tend to unwind |
| Average correction size | -5% to -15% | More severe when OI is also at extremes |
| Time to correction | 1-7 days typically | Can persist longer in strong bull markets |

**Important nuance:** High funding rates do NOT necessarily predict price drops. In bull markets, funding naturally runs higher as more traders go long. Funding rate > 0.1% during a strong uptrend may simply reflect momentum, not an imminent reversal.

**Professional approach:** Combine funding with:
- Open interest (OI): gauge scale of leveraged positions
- Price action: whether sentiment aligns with momentum
- Volume and liquidations: detect when positions are getting squeezed

### 7c. Mean Reversion Strategy Using Funding Rates

- Mean reversion on funding rate extremes has a **high win ratio** with many small winners and occasionally a big loser
- Works best in ranging/choppy markets
- Gets repeatedly stopped out during strong trends (e.g., 2023-2024 bull run)
- Should be paired with RSI oversold + lower Bollinger Band for best alignment

---

## 8. Multi-Timeframe Alignment

### 8a. Win Rate Improvement Data

**Research findings (8,734 trades analyzed):**

| Condition | Win Rate | Notes |
|-----------|----------|-------|
| Single timeframe signal | ~30-40% | Baseline for most retail traders |
| Two timeframe alignment (e.g., Daily + 4H) | ~55-60% | Significant improvement |
| Three timeframe alignment (1D + 4H + 1H all bullish) | **64.7%** | Aggregate across study |
| Non-aligned signals | ~30.9% | When indicators disagree across timeframes |

**The alignment edge:** The difference between aligned and non-aligned signals was **33.8 percentage points** in 6-month returns. This single additional step (~10 seconds of analysis) represents the largest edge enhancement of any technique studied.

### 8b. Recommended Timeframe Combinations

| Trading Style | Trend TF | Setup TF | Execution TF |
|--------------|----------|----------|---------------|
| Swing trading | Weekly | Daily | 4H |
| Day trading | Daily | 4H | 1H |
| Scalping | 4H | 1H | 15min |

**Best practice:** Only take trades in the direction confirmed by the highest timeframe. If the weekly is bearish, do not take long signals on the 4H even if they appear valid.

### 8c. Multi-Timeframe MACD Filter Results

A backtested strategy using 1H MACD signals filtered by Daily MACD direction:
- Sharpe ratio improved from 0.33 to 0.80 (2.4x improvement)
- Trade count reduced by ~55% (fewer but higher quality)
- Adding trailing stop further improved Sharpe to 1.07

---

## 9. RSI Divergence

### 9a. Bullish RSI Divergence (Price lower low, RSI higher low)

**Performance data:**

| Metric | Value | Notes |
|--------|-------|-------|
| Signal accuracy (standalone) | ~45-55% | Many false signals in strong downtrends |
| Signal accuracy (with confirmation) | ~60-70% | Candlestick pattern or structure break |
| BTC forward return (60 days) | Up to 10x higher vs bearish divergence | Significantly more profitable |
| Best timeframe | 1H and above | Higher timeframes more reliable |

### 9b. Bearish RSI Divergence (Price higher high, RSI lower high)

**Performance data:**

| Metric | Value | Notes |
|--------|-------|-------|
| Signal accuracy (standalone) | ~40-50% | Less reliable in crypto's structurally bullish environment |
| Signal accuracy (with confirmation) | ~55-65% | Needs volume decline + break of structure |
| BTC-specific effectiveness | LOW | Authors advise against using for rising cryptos like BTC/ETH |

### 9c. Key Findings

- Divergences suggest the trend MAY be weakening but do NOT guarantee reversals
- In very strong trends, markets can simply pause/consolidate before continuing
- Bullish divergence is substantially more reliable and profitable than bearish divergence in crypto
- Longer timeframe divergences are more reliable than shorter timeframe signals
- Combining divergence with candlestick confirmation or market structure breaks significantly improves accuracy

---

## 10. Indicator Comparison and Sharpe Ratios

### 10a. Individual Indicator Rankings (Crypto)

| Indicator | Standalone Win Rate | Sharpe Ratio (approx.) | Best Use Case |
|-----------|-------------------|----------------------|---------------|
| RSI (14) | 40-55% | 0.3-0.7 | Mean reversion entries |
| MACD crossover | 40-55% | 0.3-0.8 | Trend confirmation |
| SMA 50/200 crossover | 55-65% | 0.5-0.8 | Long-term trend identification |
| Bollinger Band squeeze | 50-60% | 0.4-0.7 | Volatility breakout detection |
| Volume analysis | N/A (confirming) | N/A | Confirmation only |
| Funding rate extremes | 60-75% | 0.5-0.9 | Contrarian entries |

### 10b. Combined Strategy Rankings

| Combination | Win Rate | Sharpe Ratio | Notes |
|-------------|----------|-------------|-------|
| MACD + RSI | 65-77% | 0.8-1.2 | Most popular combination |
| MACD + RSI + Bollinger | 73-77% | 0.9-1.3 | Reduced false signals |
| MACD + RSI + multi-TF filter | 65-75% | 1.0-1.44 | Best risk-adjusted returns |
| MACD + trailing stop + diversification | 55-65% | 1.07-1.44 | Optimized for Sharpe |
| RSI + funding rate + Bollinger | 65-75% | 0.7-1.0 | Best for mean reversion |

### 10c. Key Sharpe Ratio Benchmarks

| Benchmark | Sharpe Ratio |
|-----------|-------------|
| S&P 500 long-term | 0.5-0.7 |
| Strong hedge fund | >1.5 |
| Bitcoin buy-and-hold (12-month, 2025) | 2.42 |
| Good crypto strategy | >1.0 |
| Very good crypto strategy | >2.0 |
| Excellent crypto strategy | >3.0 |

### 10d. Academic Finding on Best Indicators

- Price-based signals (RSI, MACD) are more effective for **short-term** prediction
- Volume-based signals are more powerful for **long-term** prediction
- Machine learning techniques can significantly improve the performance of any technical indicator
- MACD and Supertrend achieved results **more than 2x higher** than RSI-based trend detection
- RSI was found to be **more accurate** than MACD in signal quality (but MACD in total return)

---

## 11. Academic Research Summary

### 11a. Key Studies

**"Effectiveness of Technical Trading Rules in Cryptocurrency Markets" (Annals of Operations Research, 2019):**
- Tested nearly 15,000 technical trading rules across five major categories
- Found significant predictability and profitability for each class of rule in each cryptocurrency
- Technical rules offer substantially higher risk-adjusted returns than buy-and-hold
- Provides protection against lengthy and severe drawdowns

**"Effectiveness of the RSI Signals in Timing the Cryptocurrency Market" (PMC, 2023):**
- For rising cryptocurrencies (BTC, ETH, BNB, ADA), overbought signals actually preceded continued gains
- RSI was more useful as a trend-strength indicator than a reversal indicator
- The signal works counterproductively when used to short rising assets

**"The Validity of Technical Analysis in the Cryptocurrency Market" (ResearchGate, 2023):**
- Technical analysis demonstrates validity, especially with machine learning enhancement
- Results vary significantly by cryptocurrency and time period

### 11b. Critical Caveats from Academic Literature

1. **Data snooping problem:** After controlling for data snooping and market frictions, statistically significant positive excess returns are rarely achieved
2. **Bitcoin exception:** Technical trading rules cannot generate positive returns in the out-of-sample period for Bitcoin specifically, but can for other cryptocurrencies
3. **Transaction costs:** Many profitable strategies become unprofitable when realistic transaction costs are applied
4. **Regime dependency:** Strategy performance varies drastically between bull and bear markets
5. **Overfitting risk:** Strategies optimized on historical data often fail out-of-sample

### 11c. What the Research Consensus Says

**Works:**
- Multi-indicator combinations outperform single indicators
- Multi-timeframe analysis significantly improves win rates
- Mean reversion strategies have high win rates in ranging markets
- Moving average strategies reduce drawdowns vs. buy-and-hold
- Funding rate extremes are reliable contrarian signals

**Doesn't work (or is unreliable):**
- Single-indicator mechanical strategies (e.g., buy RSI < 30, sell RSI > 70)
- Shorting overbought conditions in bull markets
- MACD signals in ranging/choppy markets
- Volume spikes in isolation without follow-through confirmation
- Any indicator without contextual market regime awareness

---

## Summary: Recommended Signal Thresholds for a Trading System

| Signal | Threshold | Expected Edge | Confidence |
|--------|-----------|---------------|------------|
| RSI oversold (buy) | RSI(14) < 30, daily | +5-15% 30-day return, ~60-65% win rate | MODERATE (needs confirmation) |
| RSI overbought (reduce risk) | RSI(14) > 70, daily | Alert only, not reliable sell signal | LOW as sell signal |
| MACD bullish cross (buy) | Daily, with RSI filter | ~65-73% win rate | MODERATE-HIGH |
| MACD bearish cross (sell/short) | Daily, with RSI filter | ~50-60% win rate | LOW-MODERATE |
| Golden cross (strong buy) | SMA50 > SMA200, daily | +9.6% avg 30-day, +30-150% 6-12 month | HIGH (lagging) |
| Death cross (caution) | SMA50 < SMA200, daily | Contrarian buy in 64% of cases | MODERATE (regime-dependent) |
| BB squeeze breakout | Bandwidth at 6-month low | ~70-75% with confirmation | MODERATE-HIGH |
| Funding rate extreme negative | < -0.05% | ~70-75% bounce probability | HIGH (short-term) |
| Funding rate extreme positive | > +0.1% | ~60-70% correction probability | MODERATE |
| Multi-TF alignment | 3 timeframes agree | 64.7% win rate vs ~31% when misaligned | HIGH |
| Bullish RSI divergence | Price LL, RSI HL | ~60-70% with confirmation | MODERATE |

---

## Sources

### RSI Research
- [Bitcoin RSI Charts - Bitbo](https://charts.bitbo.io/monthly-rsi/)
- [RSI Backtest - AInvest](https://www.ainvest.com/aime/share/backtest-performance-buying-bitcoin-rsi-oversold-support-level-break-2022-58c870/)
- [Effectiveness of RSI Signals in Timing Cryptocurrency Market - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9920669/)
- [RSI Trading Strategy (91% Win Rate) - Quantified Strategies](https://www.quantifiedstrategies.com/rsi-trading-strategy/)
- [70-30 RSI Trading Strategy - Quantified Strategies](https://www.quantifiedstrategies.com/70-30-rsi-trading-strategy/)
- [RSI 14 Debunked - Quantified Strategies](https://www.quantifiedstrategies.com/rsi-14-debunked/)
- [RSI Crossover Backtested on Bitcoin - Medium](https://medium.com/@AtomicScript/episode-3-rsi-crossover-strategy-1273d8b3f290)
- [Bitcoin RSI Screams Oversold - CoinDesk](https://www.coindesk.com/markets/2026/02/04/bitcoin-s-rsi-screams-oversold-here-is-what-it-means)
- [Bitcoin 14-Day RSI Falls Below 30 - CoinDesk](https://www.coindesk.com/markets/2026/02/19/bitcoin-s-14-day-rsi-falls-below-30-for-third-time-ever-months-of-consolidation-likely)
- [Bitcoin RSI at 27 - CoinFomania](https://coinfomania.com/bitcoin-rsi-oversold-historic-signal-analysis/)

### MACD Research
- [MACD Indicator in Crypto Trading - Zignaly](https://zignaly.com/crypto-trading/indicators/macd-crypto-indicator)
- [MACD Trading Strategy - Quantified Strategies](https://www.quantifiedstrategies.com/macd-trading-strategy/)
- [Bitcoin MACD Strategy Backtest - GitHub](https://github.com/VermeirJellen/Bitcoin_MACD_Strategy)
- [Bitcoin MACD Strategy Backtest 2023 - Medium](https://medium.com/thecapital/bitcoin-backtest-how-effective-was-the-macd-strategy-in-2023-0f3a4e5dd6f0)
- [MACD Trading Strategy 100 Times - Trading Rush](https://tradingrush.net/i-risked-macd-trading-strategy-100-times-heres-what-happened/)
- [Comparative Study of MACD-Based Trading - arXiv](https://arxiv.org/pdf/2206.12282)
- [MACD vs RSI Crypto Accuracy - Altrady](https://www.altrady.com/blog/crypto-trading-strategies/macd-trading-strategy-macd-vs-rsi)
- [MACD RSI and KDJ Indicators - Gate.com](https://www.gate.com/crypto-wiki/article/how-to-use-macd-rsi-and-kdj-indicators-for-crypto-trading-signals-a-technical-analysis-guide-20251227)

### Moving Average / Golden Cross / Death Cross Research
- [Bitcoin 50/200 Day MA Chart - Bitbo](https://charts.bitbo.io/50-200-day-ma/)
- [Golden Cross vs Death Cross Crypto Guide - ChartScout](https://chartscout.io/golden-cross-vs-death-cross-crypto-trading-guide)
- [Bitcoin Golden Cross Price Analysis - Pocket Option](https://pocketoption.com/blog/en/knowledge-base/trading/bitcoin-golden-cross/)
- [Bitcoin Golden Cross Analysis - Decrypt](https://decrypt.co/354918/bitcoin-bullish-signal-golden-cross-price-analysis)
- [Bitcoin Golden Cross 2000% Gains - CoinTelegraph](https://cointelegraph.com/news/bitcoin-golden-cross-that-sparked-2000-gains-is-here)
- [Bitcoin Death Cross Historical Pattern - CoinDesk](https://www.coindesk.com/markets/2025/11/16/bitcoin-approaches-death-cross-as-market-tests-major-historical-pattern)
- [Bitcoin Death Cross Last Time - Benzinga](https://www.benzinga.com/crypto/cryptocurrency/25/12/49447424/bitcoins-death-cross-looks-scary-until-you-realize-what-happened-last-time)
- [Bitcoin Death Cross Buying Opportunity - CoinShares via AInvest](https://www.ainvest.com/news/bitcoin-death-cross-historically-buying-opportunity-coinshares-2504/)
- [200 Day Moving Average Trading Strategy - Quantified Strategies](https://www.quantifiedstrategies.com/200-day-moving-average-trading-strategy/)
- [Best SMA for Bitcoin Backtest - Metaduro](https://metaduro.com/blog/best-sma-for-bitcoin-this-one-destroys-buy-hold-backtest-results)

### Bollinger Bands Research
- [Bollinger Bands Trading Strategies - Quantified Strategies](https://www.quantifiedstrategies.com/bollinger-bands-trading-strategy/)
- [Bollinger Band Squeeze Breakout Guide - Mind Math Money](https://www.mindmathmoney.com/articles/the-bollinger-band-squeeze-trading-strategy-a-comprehensive-guide)
- [Bollinger Bands Squeeze for Breakouts - Fortune Prime Global](https://fortuneprimeglobal.com/education/bollinger-band-squeeze-for-profitable-breakouts/)

### Funding Rate Research
- [Deeply Negative Funding Rates BTC Bounce - CryptoPotato](https://cryptopotato.com/analyst-deeply-negative-funding-rates-hint-at-btc-bounce/)
- [Bitcoin Funding Rate History - CoinGlass](https://www.coinglass.com/FundingRate/BTC)
- [Bitcoin Funding Rates - CryptoQuant](https://cryptoquant.com/asset/btc/chart/derivatives/funding-rates)
- [What Bitcoin Funding Rate Tells You - CoinTelegraph](https://cointelegraph.com/learn/articles/what-bitcoin-sfunding-rate-really-tells-you)
- [Mean Reversion in Crypto Perps - Flipster](https://flipster.io/en/blog/mean-reversion-in-crypto-how-to-trade-oversold-and-overbought-perps)
- [Mean Reversion Strategy in Crypto Rate Trading - Rho Trading](https://www.rho.trading/blog/mean-reversion-strategy-in-crypto-rate-trading)

### Multi-Timeframe Research
- [Multi-Timeframe Alignment Success Rates - Medium](https://medium.com/@contentorybaxter/multi-timeframe-alignment-success-rates-the-47-point-win-rate-gap-between-trading-with-bb-lb-f01a525f512a)
- [Multi-Timeframe Analysis Crypto - BingX](https://bingx.com/en/learn/article/how-to-use-multiple-timeframe-analysis-for-better-entry-and-exit-points-in-crypto-trading)
- [Multiple Time Frames Trading - altFINS](https://altfins.com/knowledge-base/trading-multiple-time-frames/)

### Academic Studies
- [Technical Trading and Cryptocurrencies - Springer](https://link.springer.com/article/10.1007/s10479-019-03357-1)
- [The Validity of Technical Analysis in Cryptocurrency - ResearchGate](https://www.researchgate.net/publication/374375103_The_validity_of_technical_analysis_in_the_cryptocurrency_market_evidence_from_machine_learning_methods)
- [On the Drivers of Technical Analysis Profits - ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S1057521923000327)
- [Technical Analysis Meets Machine Learning - arXiv](https://arxiv.org/pdf/2511.00665)
- [Effectiveness of Technical Trading Rules - ResearchGate](https://www.researchgate.net/publication/332399382_The_effectiveness_of_technical_trading_rules_in_cryptocurrency_markets)
- [Crypto Technical Analysis RSI MACD Bollinger Guide 2026 - SpotedCrypto](https://www.spotedcrypto.com/crypto-chart-analysis-rsi-macd-guide/)
- [10 Best Technical Indicators for Crypto Trading 2026 - CryptoNews](https://cryptonews.com/cryptocurrency/best-indicators-for-crypto-trading/)

### Sharpe Ratio and Performance
- [Bitcoin Sharpe Ratio Chart - Newhedge](https://newhedge.io/bitcoin/sharpe-ratio)
- [Sharpe Sortino Calmar Ratios Crypto Guide - XBTO](https://www.xbto.com/resources/sharpe-sortino-and-calmar-a-practical-guide-to-risk-adjusted-return-metrics-for-crypto-investors)
- [Optimal Crypto Allocation for Portfolios - VanEck](https://www.vaneck.com/corp/en/news-and-insights/blogs/digital-assets/matthew-sigel-optimal-crypto-allocation-for-portfolios/)
