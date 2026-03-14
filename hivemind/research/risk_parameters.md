# Optimal Risk Management Parameters for a Crypto Hedge Fund by Market Regime

## Research Summary

This document compiles empirically-backed risk management parameters from academic research,
institutional practice, and quantitative finance literature. Where exact numbers are cited, the
source methodology is noted. These are not arbitrary suggestions -- they are drawn from real fund
operations, peer-reviewed papers, and industry-standard frameworks.

---

## Table of Contents

1. [Universal Risk Constants](#1-universal-risk-constants)
2. [Bull Market Parameters](#2-bull-market-parameters)
3. [Bear Market Parameters](#3-bear-market-parameters)
4. [Ranging/Sideways Market Parameters](#4-rangingsideways-market-parameters)
5. [Crisis/Black Swan Parameters](#5-crisisblack-swan-parameters)
6. [Regime Detection Thresholds](#6-regime-detection-thresholds)
7. [Confidence & Consensus Thresholds](#7-confidence--consensus-thresholds)
8. [Kelly Criterion Application](#8-kelly-criterion-application)
9. [Institutional Benchmarks](#9-institutional-benchmarks-bridgewater-renaissance-multi-managers)
10. [Sources](#10-sources)

---

## 1. Universal Risk Constants

These parameters remain constant or near-constant across all regimes as hard limits.

| Parameter | Value | Source / Rationale |
|---|---|---|
| **Max risk per trade** | 1-2% of portfolio | Industry standard across prop firms, hedge funds, institutional desks. CME Group 2% rule. Conservative crypto: 1%. |
| **Daily loss limit (circuit breaker)** | 3% of portfolio | The 3-5-7 rule: 3% max single trade, 5% max all open positions, 7% max total portfolio exposure. Trading bots should halt at 3% daily loss. |
| **Max portfolio heat (all open positions)** | 5-7% of portfolio | 3-5-7 rule: never more than 5% of capital at risk across all open positions simultaneously. Some sources cite 5-6%. |
| **Risk-reward minimum** | 1:1.5 (short-term), 1:2 to 1:3 (trend) | Short-term trades need at least 1:1.5. Trend-following strategies target 1:2 or 1:3. At 1:3, only 30% win rate needed for profitability. |
| **Volatility target (portfolio level)** | 10-15% annualized | Bridgewater All Weather targets 10-12%. Systematic trend-followers often target 10-15%. Scaling factor = Target Vol / Recent Vol. |
| **Single position concentration limit** | 2-5% of portfolio (high vol assets) | UCITS 5/10/40 rule (max 10% single issuer). Professional traders use 2-5% for high-vol crypto. Diversified funds cap 5% single name. |

---

## 2. Bull Market Parameters

**Regime definition**: Quarterly returns above the 84th percentile of historical distribution (academic standard). ADX > 25, price above 200-day MA, VIX < 15 equivalent.

### Position Sizing

| Parameter | Recommended Value | Data Source |
|---|---|---|
| **Max position size (single asset)** | 8-10% of portfolio | Bull markets allow larger positions. Institutional crypto: up to 10% for high-conviction. Regulatory diversified limit: 10% max single name (UCITS). |
| **Risk per trade** | 1.5-2% of portfolio | Upper range of the 1-2% standard. Bull regime allows slightly more aggressive sizing due to favorable risk/reward. |
| **Number of open positions** | 10-15 concurrent | Optimal diversification: 5-15 assets. Bull market favors more positions to capture broad upside. Bluesky study used top 14 cryptos. |
| **Gross exposure** | 150-200% | Low-vol environments allow 150-200% gross exposure. Bridgewater All Weather uses ~1.8x leverage. |
| **Net exposure (long bias)** | 60-80% net long | Bull market: 70/30 long-short allocation (AdaptiveTrend paper, Sharpe 2.41). Directional long-biased funds go 60-80% net long. |
| **Long/Short ratio** | 70:30 to 80:20 | AdaptiveTrend (2022-2024): 70/30 long-short with Sharpe 2.41, max DD -12.7%. Justified by crypto positive drift. |

### Stop Loss & Drawdown

| Parameter | Recommended Value | Data Source |
|---|---|---|
| **Stop loss width** | 2x ATR (swing), 1.5x ATR (day) | Bull markets: lower ATR multiplier because volatility is moderate. Day traders: 1.5-2x ATR. Swing: 2-3x ATR. |
| **Max drawdown before position cut** | 5% from peak | Multi-manager standard (Millennium): 5% drawdown = allocation cut in half. |
| **Max drawdown before full halt** | 10% from peak | Millennium: 10% drawdown = fired. Industry: 8-10% for PM termination. |
| **Trailing stop activation** | After 2x risk achieved | Lock in gains after 2:1 R:R hit. Dynamic trailing tied to intra-day volatility regimes. |

### Expected Performance (Bull)

| Metric | Benchmark |
|---|---|
| **Target Sharpe ratio** | 1.5-2.5 |
| **Win rate (trend following)** | 40-45% (but large winners) |
| **Expected annual return** | 50-200%+ (crypto bull, high variance) |
| **Max acceptable drawdown** | 15-20% |

---

## 3. Bear Market Parameters

**Regime definition**: Quarterly returns below the 16th percentile. Price below 200-day MA, ADX > 25 (trending down), rising volatility, BTC drawdown > 20% from ATH.

### Should You Trade at All?

**Yes, but with dramatically reduced size and shifted allocation.** Data supports this:

- Systematic long/short crypto strategy produced 224% mean annual returns vs 108% for BTC buy-and-hold, with Sharpe of 1.96 vs 1.18 (Bluesky Capital study).
- AdaptiveTrend maintained Sharpe 2.41 through bear markets (2022-2024 backtest including full bear cycle).
- QuantPedia: Trend-following (MAX strategy) "remains alive and well" in bear markets. Mean-reversion (MIN strategy) "yielded low or even negative returns" during bear periods.
- Directional long-biased crypto funds suffered drawdowns exceeding 60% during 2022 bear cycle.

**Key takeaway**: Trade, but shift to short-biased, reduce size, and raise quality thresholds.

### Position Sizing

| Parameter | Recommended Value | Data Source |
|---|---|---|
| **Max position size** | 3-5% of portfolio | Reduce to 50-60% of bull market position size. "Within 20% of a bull market peak, cut position size in half." |
| **Position size reduction factor** | 0.5x (half of bull sizing) | Cut base position in half when bear starts, cut again as it worsens. Volatility scaling: Position = Base * (Target Vol / Current Vol). |
| **Risk per trade** | 0.5-1% of portfolio | Lower range of standard. Bear regime demands tighter risk per trade. |
| **Number of open positions** | 5-8 concurrent | Fewer, higher-conviction positions. Quality over quantity. Reduce to avoid correlated drawdowns (avg crypto correlation: 0.56, rises to 0.7+ in bear). |
| **Gross exposure** | 100-130% | Stress periods: contract from 150-200% to 100-130% to meet margin requirements and reduce risk. |
| **Net exposure** | -10% to +20% net | Market-neutral to slightly short. L/S equity funds in bear: 10% net short to 20% net long. |
| **Long/Short ratio** | 40:60 to 30:70 | Flip the bull allocation. Short-biased. Target more short positions in weak assets. |

### Stop Loss & Drawdown

| Parameter | Recommended Value | Data Source |
|---|---|---|
| **Stop loss width** | 3-4x ATR | Bear markets: widen stops due to higher volatility. "In volatile markets, increase multiplier to 2.5x-3x." Crypto may need 3-4x. |
| **Max drawdown before position cut** | 3% from peak | Tighter than bull. Multi-manager: flagged at 1.5%, questioned at 2.5%, stopped at 5%. |
| **Max drawdown before full halt** | 7-8% from peak | More conservative than bull. Preserve capital for eventual recovery. |
| **Daily loss limit** | 2% | Tighter than the universal 3%. Rapid cuts to survive bear regime. |

### Bear Market Strategy Performance Data

| Strategy | Bear Performance | Source |
|---|---|---|
| Trend following (long) | Negative to flat | QuantPedia: "remains alive" but reduced returns |
| Trend following (short) | Strong positive | Bear regimes beneficial for trend-followers due to clustered declines |
| Mean reversion | Negative returns | QuantPedia: "yielded low or even negative returns" 2022-2024 |
| Long/short systematic | Sharpe ~2.0 | Bluesky Capital: maintained strong risk-adjusted performance |
| Buy and hold | -50% to -85% drawdown | BTC max DD 84%, crypto basket 92.9% (Bluesky data) |

---

## 4. Ranging/Sideways Market Parameters

**Regime definition**: Returns between 16th and 84th percentiles. ADX < 25 (no trend), VIX in 15-25 range, price oscillating around moving averages without clear direction.

### Mean Reversion vs Trend Following

**Mean reversion dominates in ranging markets.** The data:

- QuantPedia: "Sideways markets provide the best mean reversion trading environments."
- Mean reversion win rates: 60-80% but smaller average gains.
- Trend following in sideways markets: "frequent small losses" (whipsaw).
- Best practice: "Trade both strategies -- times when trend following performs poorly while mean reversion flourishes are different."

### Position Sizing

| Parameter | Recommended Value | Data Source |
|---|---|---|
| **Max position size** | 5-7% of portfolio | Moderate -- between bull and bear sizing. |
| **Risk per trade** | 1-1.5% of portfolio | Standard range. Mean reversion strategies can use slightly tighter since win rate is higher. |
| **Number of open positions** | 8-12 concurrent | Mean reversion allows more simultaneous positions due to shorter hold periods and higher win rates. |
| **Gross exposure** | 120-150% | Moderate leverage. |
| **Net exposure** | 0% to +30% net | Near market-neutral. Slight long bias acceptable due to crypto's secular upward drift. |
| **Long/Short ratio** | 55:45 to 60:40 | Near balanced. Mean reversion trades both directions. |

### Stop Loss & Drawdown

| Parameter | Recommended Value | Data Source |
|---|---|---|
| **Stop loss width** | 1.5-2x ATR | Tighter stops in ranging markets. Mean reversion: tight stops because if the reversion thesis fails, exit quickly. |
| **Max drawdown before position cut** | 4% from peak | Mid-range threshold. |
| **Max drawdown before full halt** | 8-10% from peak | Standard range. |
| **Take profit target** | 1.5-2x ATR from entry | Mean reversion: define clear exit at mean/Bollinger band midpoint. Don't hold for trend. |

### Ranging Market Strategy Performance

| Strategy | Ranging Performance | Source |
|---|---|---|
| Mean reversion | Win rate 60-80%, small gains | QuantPedia: best environment for MR |
| Trend following | Frequent small losses (whipsaw) | QuantPedia: worst environment for TF |
| Combined MR + TF | Optimal overall | "Trading both strategies increases odds" |
| Market-neutral pairs | Strong | Low correlation benefit, stat-arb works |

---

## 5. Crisis/Black Swan Parameters

**Regime definition**: VIX > 40 (or crypto equivalent), ATR > 1.5x the 6-month average, correlation spike (crypto avg > 0.7), rapid drawdown > 20% in days/weeks, exchange liquidation cascades.

### What Do Real Funds Do?

**Historical data on hedge fund behavior during crises:**

#### 2008 Financial Crisis
- Average hedge fund lost 18% (worst year on record)
- Hedge fund volatilities increased by 2x on average
- Factor exposures doubled or tripled vs "tranquil" period
- Funds reduced equity holdings by 15% on average (29% cumulative with compounding)
- Dozens of funds imposed redemption "gates" to prevent bank runs on assets
- Industry AUM fell 25% in second half of 2008
- Funds held more cash prior to crisis (anticipatory behavior)

#### 2020 COVID Crash (March)
- Hedge fund Treasury exposures continued decreasing through September 2020
- Both long and short UST positions contracted for 6+ months post-crisis
- Slow return to pre-crisis positioning

#### 2022 Crypto Winter (Luna/FTX)
- Directional long-biased crypto funds: drawdowns exceeding 60%
- BTC max drawdown: 84% from peak
- Crypto basket max drawdown: 92.9%
- Correlation among top 14 cryptos surged above 0.7

### Crisis Parameters

| Parameter | Recommended Value | Data Source |
|---|---|---|
| **Max position size** | 1-2% of portfolio | Absolute minimum sizing. Capital preservation mode. |
| **Position size reduction factor** | 0.25x (quarter of bull sizing) | Cut to 25% of normal. "In crisis regimes, shift dramatically toward capital preservation." |
| **Risk per trade** | 0.25-0.5% of portfolio | Minimal risk. Conservative traders use 0.5-1% even in normal conditions. |
| **Number of open positions** | 0-3 (or fully cash) | Minimal exposure. Many real funds go 100% to cash/stablecoins. |
| **Gross exposure** | 0-50% | Drastic deleveraging. Some funds go to zero. |
| **Net exposure** | -20% to 0% net | Market-neutral or defensive net short. |
| **Cash/stablecoin allocation** | 50-100% | Capital preservation is the priority. Real funds hold more cash prior to and during crises. |
| **Stop loss width** | 1x ATR (very tight) or no new trades | Either very tight stops or simply do not enter new positions. |
| **Max drawdown before full halt** | 5% from peak | Immediate halt. Preserve capital above all else. |
| **Daily loss limit** | 1% | Hard circuit breaker. |
| **Correlation monitoring** | Halt if avg pair correlation > 0.8 | When everything correlates, diversification fails. Go to cash. |

### Crisis Playbook (Decision Tree)

```
IF crisis detected:
  1. Immediately reduce gross exposure to 50% or less
  2. Close all positions with negative momentum
  3. Retain only highest-conviction shorts (if any)
  4. Move 50-100% to cash/stablecoins
  5. Disable new long entries
  6. Set daily loss limit to 1%
  7. Re-evaluate regime daily
  8. DO NOT bottom-fish until regime shifts to "bear" or "ranging"
```

---

## 6. Regime Detection Thresholds

### Volatility-Based Regime Classification

| Regime | Realized Vol (annualized) | ATR Condition | ADX | Crypto Equivalent |
|---|---|---|---|---|
| **Low volatility (Bull/Range)** | < 50% annualized | ATR < 1.0x 6-month avg | < 25 (range) or > 25 (bull trend) | BTC 30-day vol < 50% |
| **Medium volatility (Transitional)** | 50-80% annualized | ATR 1.0-1.5x 6-month avg | Variable | BTC 30-day vol 50-80% |
| **High volatility (Bear/Crisis)** | > 80% annualized | ATR > 1.5x 6-month avg | > 25 (bear trend) | BTC 30-day vol > 80% |
| **Crisis** | > 120% annualized | ATR > 2.0x 6-month avg | > 30 | Correlation spike + liquidation cascades |

### Trend Detection

| Indicator | Bull | Bear | Ranging |
|---|---|---|---|
| **Price vs 200-day MA** | Above | Below | Oscillating around |
| **ADX** | > 25 | > 25 | < 25 |
| **50/200 MA cross** | Golden cross | Death cross | Flat/intertwined |
| **Momentum (ROC 20d)** | > 0 | < 0 | Near zero, oscillating |

### BTC-Specific Historical Volatility Ranges

- **Bitcoin annualized volatility**: 91.73% average (Bluesky data)
- **Daily return range**: -38.27% to +40.04%
- **Kurtosis**: 10.85 (extreme fat tails)
- **Crypto basket kurtosis**: 27 (even fatter tails)

---

## 7. Confidence & Consensus Thresholds

### Confidence Threshold (Signal Quality Filter)

Research from the MDPI Confidence-Threshold Framework for Cryptocurrency:

| Threshold (tau) | Accuracy | Coverage | Avg Profit/Trade | Use Case |
|---|---|---|---|---|
| **0.50 (baseline)** | 74.12% | 47.83% | 102.45 bps | No filtering -- execute everything above coin flip |
| **0.60 (moderate)** | ~78% | 44.9% | ~120 bps | Grid-search optimal for profit * coverage product. Best balance of quantity and quality. |
| **0.70 (elevated)** | ~80% | ~30% | ~135 bps | Higher quality, fewer trades |
| **0.80 (high)** | 82-95% | 0.28% (very selective) | 151.11 bps | Maximum per-trade profitability. Extreme selectivity. |
| **Always execute** | 76.34% | 100% | 89.23 bps | No confidence filter baseline |

**Recommended by regime:**

| Regime | Confidence Threshold | Rationale |
|---|---|---|
| **Bull** | 0.55-0.60 | Lower threshold OK -- favorable environment, more trades capture upside |
| **Bear** | 0.70-0.80 | High threshold -- only take highest conviction signals |
| **Ranging** | 0.60-0.70 | Moderate -- filter out whipsaw noise but trade enough for MR |
| **Crisis** | 0.85+ or no trading | Extreme selectivity or halt entirely |

### Consensus Threshold (Multi-Signal Agreement)

Based on ensemble consensus systems and multi-indicator research:

| Consensus Level | Meaning | Recommended Use |
|---|---|---|
| **3/5 experts agree (60%)** | Moderate consensus | Standard execution threshold. "Visual entry points with strength percentage (60% = 3/5 experts agree)." |
| **4/5 experts agree (80%)** | Strong consensus | High-conviction trades only. Use in bear/crisis for additional filtering. |
| **5/5 experts agree (100%)** | Unanimous | Extremely rare signals. Maximum position size when all models agree. |

**Recommended by regime:**

| Regime | Consensus Threshold | Rationale |
|---|---|---|
| **Bull** | 60% (3/5 agree) | More permissive -- capture broad uptrend |
| **Bear** | 75-80% (4/5 agree) | Demand strong agreement before risking capital |
| **Ranging** | 65-70% | Moderate filtering for mean reversion signals |
| **Crisis** | 80-100% | Near-unanimous or do not trade |

### Shannon Entropy Filter

- **High entropy** = unpredictable/noisy market => REDUCE or halt trading
- **Low entropy** = clear directional signal => INCREASE position size
- Entropy threshold should be optimized per asset/timeframe
- Values above threshold lead to "increased frequency of false signals, resulting in unnecessary losses"

---

## 8. Kelly Criterion Application

### Full Kelly vs Fractional Kelly

| Kelly Fraction | Growth Rate Retained | Volatility vs Full Kelly | Recommended For |
|---|---|---|---|
| **Full Kelly (1.0)** | 100% | 100% | Theoretical only. Never in practice for crypto. |
| **Half Kelly (0.50)** | 75% of max growth | 25% of full Kelly variance | Aggressive systematic funds with verified edge |
| **Quarter Kelly (0.25)** | ~56% of max growth | ~6% of full Kelly variance | Conservative institutional. Standard for uncertain environments. |
| **10% Kelly (0.10)** | ~19% of max growth | ~1% of full Kelly variance | Crisis mode or highly uncertain edge estimates |

### Professional Practice

- **Professional crypto traders**: 10-25% of full Kelly (Quarter Kelly most common)
- **Institutional consensus**: 25-50% of Kelly recommendation
- **Half Kelly**: Reduces volatility ~25% while retaining ~75% of long-term growth
- **Quarter Kelly**: Cuts volatility in half with minimal return impact
- **Why fractional**: Accounts for model error, fat tails (BTC kurtosis 10.85), regime shifts, transaction costs, slippage

### Kelly by Regime

| Regime | Kelly Fraction | Rationale |
|---|---|---|
| **Bull** | 25-50% (Quarter to Half Kelly) | Higher confidence in edge estimates during favorable conditions |
| **Bear** | 10-25% (Tenth to Quarter Kelly) | Reduce due to heightened uncertainty and fat tail risk |
| **Ranging** | 20-30% | Moderate -- mean reversion has higher win rate but smaller payoffs |
| **Crisis** | 0-10% | Near zero or do not trade. Edge estimates unreliable. |

---

## 9. Institutional Benchmarks (Bridgewater, Renaissance, Multi-Managers)

### Bridgewater Associates (All Weather / Risk Parity)

| Parameter | Value |
|---|---|
| **Portfolio volatility target** | 10-12% annualized |
| **Leverage** | ~1.8x via futures |
| **Risk allocation** | Equal risk contribution per asset class |
| **Rebalancing** | Dynamic -- scale inversely to volatility |
| **Philosophy** | No regime prediction. Balance across all environments. |

### Renaissance Technologies (Medallion Fund)

| Parameter | Value |
|---|---|
| **Position sizing method** | Kelly criterion-based, precisely calibrated per trade probability |
| **Number of daily trades** | ~300,000 |
| **Average position size** | ~$100K per trade (at $10B AUM) |
| **Holding period** | Very short (intraday to days) |
| **Fund cap** | $10-15B (employees only) -- capacity constraint as risk management |
| **Diversification** | Thousands of uncorrelated bets |
| **Market exposure** | Market-neutral (long/short pairs, eliminate beta) |
| **Risk monitoring** | Continuous real-time, evolving volatility and correlation estimates |

### Multi-Manager Hedge Funds (Millennium, Citadel, Point72)

| Parameter | Value |
|---|---|
| **Total fund max drawdown** | 2.5-5% depending on firm |
| **PM flagged at** | 1.5% drawdown -- head of risk asks basic questions |
| **PM formal review at** | 2.5% drawdown -- documented meeting to justify positions |
| **PM allocation halved at** | 5% drawdown (Millennium default) |
| **PM terminated at** | 8-10% drawdown from peak (Millennium: 10%) |
| **Daily loss conversation** | Mid-single digit % triggers immediate allocation reduction |

### Systematic Trend-Following Benchmarks (CTAs)

From Concretum Group analysis (40 futures markets, 1980-2024):

| Method | IRR p.a. | Max Drawdown | Hit Ratio (trade) | Hit Ratio (monthly) |
|---|---|---|---|---|
| **Volatility Targeting (VT)** | 11.46% | 25.65% | 42.5% | 60% |
| **Volatility Parity (VP)** | 12.83% | ~25% | 42.4% | 59% |
| **VP + Pyramiding** | 20.00% | 48.69% | 39.3% | 56% |

Key parameter: **0.10% daily volatility contribution per trade** (= $100K risk per $100M portfolio per day).

---

## 10. Parameter Summary Matrix

### Quick Reference: All Regimes at a Glance

| Parameter | Bull | Bear | Ranging | Crisis |
|---|---|---|---|---|
| **Max position size** | 8-10% | 3-5% | 5-7% | 1-2% |
| **Risk per trade** | 1.5-2% | 0.5-1% | 1-1.5% | 0.25-0.5% |
| **# Open positions** | 10-15 | 5-8 | 8-12 | 0-3 |
| **Gross exposure** | 150-200% | 100-130% | 120-150% | 0-50% |
| **Net exposure** | +60% to +80% | -10% to +20% | 0% to +30% | -20% to 0% |
| **Long/Short ratio** | 70:30 to 80:20 | 30:70 to 40:60 | 55:45 to 60:40 | 0:100 to 40:60 |
| **Stop loss (ATR mult.)** | 1.5-2x | 3-4x | 1.5-2x | 1x or no trades |
| **Confidence threshold** | 0.55-0.60 | 0.70-0.80 | 0.60-0.70 | 0.85+ |
| **Consensus threshold** | 60% (3/5) | 75-80% (4/5) | 65-70% | 80-100% |
| **Max DD before cut** | 5% | 3% | 4% | 2% |
| **Max DD before halt** | 10% | 7-8% | 8-10% | 5% |
| **Daily loss limit** | 3% | 2% | 2.5% | 1% |
| **Kelly fraction** | 25-50% | 10-25% | 20-30% | 0-10% |
| **Cash allocation** | 5-15% | 30-50% | 15-25% | 50-100% |
| **Position size factor** | 1.0x (base) | 0.5x | 0.7x | 0.25x |

---

## 11. Sources

### Academic Papers & Research
- [Confidence-Threshold Framework for Cryptocurrency Price Direction Prediction (MDPI 2024)](https://www.mdpi.com/2076-3417/15/20/11145)
- [AdaptiveTrend: Systematic Trend-Following with Adaptive Portfolio Construction in Cryptocurrency Markets (2025)](https://arxiv.org/abs/2602.11708)
- [Revisiting Trend-Following and Mean-Reversion Strategies in Bitcoin (QuantPedia/SSRN)](https://quantpedia.com/revisiting-trend-following-and-mean-reversion-strategies-in-bitcoin/)
- [Crisis and Hedge Fund Risk (Yale ICF)](http://depot.som.yale.edu/icf/papers/fileuploads/2561/original/07-14.pdf)
- [Good and Bad Properties of the Kelly Criterion (UC Berkeley)](https://www.stat.berkeley.edu/~aldous/157/Papers/Good_Bad_Kelly.pdf)
- [Practical Implementation of the Kelly Criterion (Frontiers in Applied Math)](https://www.frontiersin.org/journals/applied-mathematics-and-statistics/articles/10.3389/fams.2020.577050/pdf)
- [Volatility-Managed Portfolios (Journal of Finance)](https://amoreira2.github.io/alan-moreira.github.io/VolPortfolios_published.pdf)
- [Drawdowns (Duke University)](https://people.duke.edu/~charvey/Research/Published_Papers/P147_Drawdowns.pdf)
- [Conditional Volatility Targeting (Financial Analysts Journal)](https://www.tandfonline.com/doi/full/10.1080/0015198X.2020.1790853)

### Industry & Institutional Sources
- [Bluesky Capital: Analysis of a Systematic Long-Short Crypto Investment Strategy](https://www.blueskycapitalmanagement.com/analysis-of-a-systematic-long-short-crypto-investment-strategy/)
- [Bridgewater Associates: The All Weather Strategy](https://www.bridgewater.com/research-and-insights/the-all-weather-strategy)
- [Man Group: You're Fired! When Do You Sack the Fund Manager?](https://www.man.com/insights/youre-fired)
- [Man Group: Volatility is Back -- Better to Target Returns or Target Risk?](https://www.man.com/insights/volatility-is-back-better-to-target-returns-or-target-risk)
- [Man Group: The Impact of Volatility Targeting](https://www.man.com/insights/the-impact-of-volatility-targeting)
- [Concretum Group: Position Sizing in Trend-Following](https://concretumgroup.com/position-sizing-in-trend-following-comparing-volatility-targeting-volatility-parity-and-pyramiding/)
- [QuantPedia: Introduction to Volatility Targeting](https://quantpedia.com/an-introduction-to-volatility-targeting/)
- [Goldman Sachs Asset Management: Combining Investment Signals in Long/Short Strategies](https://www.gsam.com/content/dam/gsam/pdfs/institutions/en/articles/2018/Combining_Investment_Signals_in_LongShort_Strategies.pdf)
- [VanEck: Optimal Crypto Allocation for Portfolios](https://www.vaneck.com/us/en/blogs/digital-assets/matthew-sigel-optimal-crypto-allocation-for-portfolios/)

### Industry Practice & Forums
- [Wall Street Oasis: Multi-Manager Risk Limits](https://www.wallstreetoasis.com/forum/hedge-fund/multi-manager-risk-limits)
- [Wall Street Oasis: Recovering from Drawdowns in Multi-Managers/Pods](https://www.wallstreetoasis.com/forum/hedge-fund/recovering-from-drawdowns-in-mmpods)
- [Mergers & Inquisitions: Multi-Manager Hedge Funds](https://mergersandinquisitions.com/multi-manager-hedge-funds/)
- [CME Group: The 2% Rule](https://www.cmegroup.com/education/courses/trade-and-risk-management/the-2-percent-rule)
- [CFA Institute: Why Static Portfolios Fail When Risk Regimes Change](https://blogs.cfainstitute.org/investor/2026/02/20/why-static-portfolios-fail-when-risk-regimes-change/)
- [CFA Institute: Portfolio Concentration -- How Much Is Optimal?](https://blogs.cfainstitute.org/investor/2018/04/23/portfolio-concentration-how-much-is-optimal/)

### Crypto-Specific Risk Management
- [Crypto Insights Group: Industry Guide to Crypto Hedge Funds (2025)](https://www.cryptoinsightsgroup.com/resources/industry-guide-to-crypto-hedge-funds-2025-edition)
- [Coinbase Institutional: Asset Allocator's Guide to Crypto Hedge Funds](https://www.coinbase.com/institutional/research-insights/research/market-intelligence/asset-allocators-guide-to-crypto-hedge-funds)
- [LuxAlgo: 5 ATR Stop-Loss Strategies for Risk Control](https://www.luxalgo.com/blog/5-atr-stop-loss-strategies-for-risk-control/)
- [LuxAlgo: Market Regimes Explained](https://www.luxalgo.com/blog/market-regimes-explained-build-winning-trading-strategies/)
- [Kelly Criterion for Crypto (OSL Academy)](https://www.osl.com/hk-en/academy/article/what-is-the-kelly-bet-size-criterion-and-how-to-use-it-in-crypto-trading)

### Volatility & Regime Research
- [VCRIX -- A Volatility Index for Crypto-Currencies (ScienceDirect)](https://www.sciencedirect.com/science/article/abs/pii/S1057521921002416)
- [Regime Switching Forecasting for Cryptocurrencies (Springer)](https://link.springer.com/article/10.1007/s42521-024-00123-2)
- [Cryptocurrency Volatility Markets (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC8326316/)
