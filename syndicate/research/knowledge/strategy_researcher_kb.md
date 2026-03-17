# Dr. Noor Hadid — Strategy Researcher Knowledge Base

## Syndicate Autonomous AI Crypto Hedge Fund
**Role:** Strategy Researcher — Trade Attribution & Hypothesis Testing
**Version:** 1.0 | March 2026
**Classification:** Internal — Core Reference Material

---

# Table of Contents

1. [Role Definition & Mandate](#1-role-definition--mandate)
2. [Syndicate Trading Architecture Reference](#2-syndicate-trading-architecture-reference)
3. [Trade Attribution Methodology](#3-trade-attribution-methodology)
4. [Historical Bear Market Data](#4-historical-bear-market-data)
5. [Fear & Greed Trading Data](#5-fear--greed-trading-data)
6. [Position Sizing Theory & Practice](#6-position-sizing-theory--practice)
7. [Conviction Calibration Deep Dive](#7-conviction-calibration-deep-dive)
8. [Stop Loss & Exit Management](#8-stop-loss--exit-management)
9. [Institutional Benchmarks](#9-institutional-benchmarks)
10. [Hypothesis Testing Framework](#10-hypothesis-testing-framework)
11. [Report Writing Guidelines](#11-report-writing-guidelines)

---

# 1. Role Definition & Mandate

## 1.1 What Dr. Noor Hadid Does

Noor produces two types of deliverables for Syndicate:

### Trade Attribution Reports
- Break down trade performance by regime, conviction, exit reason, asset tier, holding period, and side (long/short)
- Identify patterns in wins and losses that reveal systematic edges or weaknesses
- Quantify the impact of each variable on P&L
- Surface actionable parameter adjustments backed by data

### Hypothesis Testing
- Evaluate proposed strategy changes using backtested data
- Apply statistical significance tests (minimum p < 0.05, preferred p < 0.01)
- Issue clear deploy/reject/needs-more-data recommendations
- Quantify expected impact of proposed changes

## 1.2 Core Principles

1. **Numbers over narratives.** Every claim must have a number attached. "Performance improved" is unacceptable. "Win rate increased from 42% to 51% (n=214, p=0.03)" is the standard.

2. **Regime-aware analysis.** Never evaluate a strategy or parameter in aggregate when regime-specific analysis is possible. A strategy that works in bull markets and fails in bears has a fundamentally different profile than one that works in all regimes.

3. **Practical significance over statistical significance.** A statistically significant improvement of 0.1% in win rate is not worth implementation risk. Minimum threshold for recommending a change: Sharpe improvement >= 0.3.

4. **Calibration is king.** The fund's edge depends on well-calibrated conviction scores. If conviction 8 wins less than conviction 5, the entire signal aggregation pipeline is compromised.

5. **Survivorship bias awareness.** Always ask: "Are we only seeing the trades that happened? What about the trades we filtered out that would have been winners?"

---

# 2. Syndicate Trading Architecture Reference

## 2.1 Risk Parameters by Regime

### BULL Regime
| Parameter | Value |
|---|---|
| Max position size | 8-10% of portfolio |
| Risk per trade | 1.5-2% |
| Open positions | 10-15 concurrent |
| Net exposure | +60% to +80% |
| Stop loss | 1.5-2x ATR |
| Max drawdown before cut | 5% |
| Daily loss limit | 3% |
| Confidence threshold | 0.55-0.60 |
| Consensus requirement | 60% (3/5 teams) |
| Kelly fraction | 25-50% |
| Long/Short ratio | 70:30 to 80:20 |
| Position size factor | 1.0x (base) |
| Cash allocation | 5-15% |

### BEAR Regime
| Parameter | Value |
|---|---|
| Max position size | 3-5% of portfolio |
| Risk per trade | 0.5-1% |
| Open positions | 5-8 concurrent |
| Net exposure | -10% to +20% |
| Stop loss | 3-4x ATR |
| Max drawdown before cut | 3% |
| Daily loss limit | 2% |
| Confidence threshold | 0.70-0.80 |
| Consensus requirement | 75-80% (4/5 teams) |
| Kelly fraction | 10-25% |
| Long/Short ratio | 30:70 to 40:60 |
| Position size factor | 0.5x |
| Cash allocation | 30-50% |

### RANGING Regime
| Parameter | Value |
|---|---|
| Max position size | 5-7% of portfolio |
| Risk per trade | 1-1.5% |
| Open positions | 8-12 concurrent |
| Net exposure | 0% to +30% |
| Stop loss | 1.5-2x ATR |
| Max drawdown before cut | 4% |
| Daily loss limit | 2.5% |
| Confidence threshold | 0.60-0.70 |
| Consensus requirement | 65-70% |
| Kelly fraction | 20-30% |
| Long/Short ratio | 55:45 to 60:40 |
| Position size factor | 0.7x |
| Cash allocation | 15-25% |

### CRISIS Regime
| Parameter | Value |
|---|---|
| Max position size | 1-2% of portfolio |
| Risk per trade | 0.25-0.5% |
| Open positions | 0-3 |
| Net exposure | -20% to 0% |
| Stop loss | 1x ATR or no trades |
| Max drawdown before cut | 2% |
| Daily loss limit | 1% |
| Confidence threshold | 0.85+ |
| Consensus requirement | 80-100% |
| Kelly fraction | 0-10% |
| Long/Short ratio | 0:100 to 40:60 |
| Position size factor | 0.25x |
| Cash allocation | 50-100% |

## 2.2 Trade Parameters by Asset Tier

| Tier | Stop ATR | Trail ATR | TP1 R-mult | TP2 R-mult | Risk/Trade | Max Pos% | Max Hours |
|------|----------|-----------|-----------|-----------|-----------|---------|-----------|
| BTC | 2.0x | 2.5x | 2.0x | 4.0x | 1.5% | 20% | 360 |
| Top5 | 2.5x | 3.0x | 1.5x | 3.0x | 1.2% | 12% | 240 |
| Large-cap | 3.0x | 3.5x | 1.5x | 2.5x | 1.0% | 8% | 168 |
| Mid-cap | 3.5x | 4.0x | 1.5x | 3.0x | 0.75% | 5% | 120 |
| Meme | 4.5x | 5.0x | 1.0x | 2.0x | 0.25% | 2% | 48 |

### Key Relationships in the Tier Table
- **Wider stops for lower tiers:** Meme coins get 4.5x ATR stops because their intraday noise is 2-3x that of BTC. A 2x ATR stop on a meme coin would trigger on normal volatility, not signal failure.
- **Lower TP multiples for lower tiers:** Meme coins target 1.0x/2.0x R-multiples because their trends are shorter-lived and more prone to sudden reversal.
- **Dramatically lower risk allocation for lower tiers:** Meme coins at 0.25% risk/trade vs BTC at 1.5% reflects the 6x difference in blow-up probability.
- **Time stops decrease with tier quality:** BTC can be held 360 hours (15 days) because it trends; meme coins get 48 hours (2 days) because alpha decays rapidly.

## 2.3 Exit Structure

The fund uses a three-tranche exit:

1. **TP1 (33% of position):** Sell at the first R-multiple target (varies by tier). This locks in partial profit and reduces risk exposure.

2. **TP2 (33% of position):** Sell at the higher R-multiple target. This captures the larger move if the trend continues.

3. **Trailing remainder (34%):** Chandelier trailing stop (ATR-based), activated at 1.5R profit. This allows the position to ride an extended trend while protecting accumulated gains.

4. **Time stop:** Maximum holding hours per tier. If neither TP nor SL has been hit, the position is closed. This prevents capital from being tied up in dead trades.

### Exit Priority Order
```
IF time_stop_hit → close entire remaining position
ELIF stop_loss_hit → close entire remaining position
ELIF tp1_hit AND not tp1_filled → sell 33%
ELIF tp2_hit AND not tp2_filled → sell 33%
ELIF trailing_stop_hit AND position_profit >= 1.5R → close remainder
```

## 2.4 Regime Adjustments to Trade Parameters

| Regime | stop_adj | tp_adj (TP1) | tp_adj (TP2) | time_adj |
|--------|----------|-------------|-------------|----------|
| BULL | 0.85 (tighter) | 1.25 | 1.40 | 1.25 |
| BEAR | 1.30 (wider) | 0.60 | 0.80 | 0.75 |
| RANGING | 1.00 (unchanged) | 1.00 | 1.00 | 1.00 |
| CRISIS | 1.30 (wider) | 0.60 | 0.60 | 0.50 |

### How Adjustments Apply (Example)

**BTC in BULL regime:**
- Base stop: 2.0x ATR -> Adjusted: 2.0 * 0.85 = 1.7x ATR (tighter, ride momentum)
- Base TP1: 2.0R -> Adjusted: 2.0 * 1.25 = 2.5R (let winners run further)
- Base TP2: 4.0R -> Adjusted: 4.0 * 1.40 = 5.6R (ambitious targets in strong trends)
- Base time: 360h -> Adjusted: 360 * 1.25 = 450h (hold longer in trending market)

**BTC in BEAR regime:**
- Base stop: 2.0x ATR -> Adjusted: 2.0 * 1.30 = 2.6x ATR (wider to avoid noise)
- Base TP1: 2.0R -> Adjusted: 2.0 * 0.60 = 1.2R (take profits quickly)
- Base TP2: 4.0R -> Adjusted: 4.0 * 0.80 = 3.2R (lower ceiling)
- Base time: 360h -> Adjusted: 360 * 0.75 = 270h (cut losers faster)

**Mid-cap in CRISIS:**
- Base stop: 3.5x ATR -> Adjusted: 3.5 * 1.30 = 4.55x ATR
- Base TP1: 1.5R -> Adjusted: 1.5 * 0.60 = 0.9R (barely above break-even)
- Base time: 120h -> Adjusted: 120 * 0.50 = 60h (extremely short leash)
- At this point, the question is whether to trade mid-caps at all in crisis. Usually the answer is no.

## 2.5 Signal Aggregation Architecture

### How Signals Flow

1. **5 analyst teams** each produce independent signals for each asset:
   - Technical Analysis team
   - Sentiment Analysis team
   - On-Chain / Fundamental team
   - Macro / Regime team
   - Quantitative / ML team

2. **Each team outputs:**
   - Direction: LONG, SHORT, or HOLD
   - Confidence: 0.0 to 1.0 (continuous)
   - Key factors driving the signal

3. **Aggregation method:** Bayesian log-odds aggregation
   - Each team's signal is converted to log-odds: `log_odds = log(confidence / (1 - confidence))`
   - Log-odds are summed: `combined_log_odds = sum(individual_log_odds)`
   - Combined log-odds are converted back to probability: `combined_confidence = 1 / (1 + exp(-combined_log_odds))`
   - This naturally weights higher-confidence signals more heavily

4. **Consensus calculation:**
   - Count of teams agreeing on direction / total teams
   - 3/5 = 60%, 4/5 = 80%, 5/5 = 100%

5. **Trade decision thresholds:**
   - Conviction score >= 4/10: TRADE (below = HOLD)
   - Conviction is mapped from combined confidence: `conviction = round(combined_confidence * 10)`
   - Must also meet regime-specific consensus threshold

6. **Decision quality ratings:**
   - HIGH_CONVICTION: conviction >= 8 AND consensus >= 80%
   - MODERATE: conviction 6-7 AND consensus >= 60%
   - CLOSE_CALL: conviction 4-5 AND consensus 60-70%
   - LOW: conviction < 4 OR consensus < 60% (results in HOLD)

### Why Bayesian Log-Odds Instead of Simple Average

Simple averaging treats confidence 0.55 and confidence 0.95 as nearly equivalent increments. Log-odds correctly captures that the difference between 0.50 and 0.55 is small, while the difference between 0.90 and 0.95 is enormous in information terms.

Example:
- Simple average of [0.60, 0.70, 0.80, 0.55, 0.65] = 0.66
- Bayesian log-odds aggregation of the same = 0.91 (because multiple independent signals at >0.5 compound multiplicatively in odds space)

This means the aggregator is properly Bayesian: when multiple independent analysts agree, even with moderate individual confidence, the combined signal is much stronger.

---

# 3. Trade Attribution Methodology

## 3.1 Attribution by Regime

### Why Regime-Specific Analysis is Mandatory

A strategy with 55% overall win rate might decompose as:
- Bull: 65% win rate (contributing 80% of profits)
- Bear: 30% win rate (consuming 60% of profits from bull)
- Ranging: 55% win rate (break-even after costs)
- Crisis: 20% win rate (catastrophic losses, small sample)

Evaluating only the aggregate 55% obscures that the strategy is profitable exclusively due to bull market performance and is a liability in all other regimes. Regime-specific attribution reveals this immediately.

### Expected Win Rates by Regime

#### BULL Regime
- **Trend following (long side):** 40-45% win rate, but large winners produce R-multiples of 2.0-3.0
  - This is the typical pattern: fewer than half of trades win, but winners are 2-3x the size of losers
  - Expected R:R ratio: 1:2 to 1:3
  - Expectancy per trade: (0.42 * 2.5R) - (0.58 * 1.0R) = 0.47R positive expectancy
  - This is a strong positive-expectancy system despite sub-50% win rate
- **Mean reversion (long side):** 55-65% win rate, but smaller R-multiples of 0.8-1.5
  - Higher hit rate but lower payoff ratio
  - Expectancy: (0.60 * 1.0R) - (0.40 * 1.0R) = 0.20R (weaker than trend following in bull)
- **Short side in bull:** 25-35% win rate regardless of methodology
  - Structural crypto long bias means shorts face a persistent headwind
  - Only take shorts with HIGH_CONVICTION (conviction >= 8)

#### BEAR Regime
- **Trend following (short side):** 45-55% win rate with R-multiples of 1.5-2.5
  - Bear trends cluster downward moves, creating strong short-side momentum
  - Expectancy: (0.50 * 2.0R) - (0.50 * 1.0R) = 0.50R
- **Mean reversion (long side, tactical bounces):** Produces low or negative returns in sustained bears
  - QuantPedia backtest result: mean reversion "yielded low or even negative returns" during 2022-2024 bear
  - Do NOT rely on mean reversion longs in bear markets except for very short-term scalps (< 4 hours)
- **Long side in bear:** 25-35% win rate
  - Only justified at extreme fear levels (F&G < 15) with whale accumulation confirmation
  - Position size should be 0.25x-0.50x of bull market sizing

#### RANGING Regime
- **Mean reversion dominates:** 60-80% win rate but smaller gains (R-multiples of 0.5-1.5)
  - QuantPedia: "Sideways markets provide the best mean reversion trading environments"
  - Mean reversion trades both directions, so the long/short distinction matters less
- **Trend following produces whipsaws:** Win rate drops to 25-35%
  - Trend-following signals in ranging markets are predominantly false
  - "Frequent small losses" pattern — the classic whipsaw
  - If attribution shows high trend-following activity in ranging markets, it is a signal to adjust the strategy mix

#### Combined Strategy Performance (50/50 Momentum + Mean Reversion)
- Sharpe ratio: 1.71
- Annualized return: 56%
- T-statistic: 4.07
- This combined approach produces the smoothest returns across ALL regimes

### Regime Identification Confirmation

Before attributing trade outcomes to regime, verify regime classification was correct using:

1. **ADX (Average Directional Index):**
   - ADX > 25: trending (bull or bear depending on direction)
   - ADX < 25: ranging
   - ADX > 40: strong trend

2. **200-Day Moving Average:**
   - Price above 200-day MA with positive slope: BULL
   - Price below 200-day MA with negative slope: BEAR
   - Price oscillating around 200-day MA: RANGING

3. **Quarterly Return Percentiles (academic standard):**
   - Above 84th percentile: BULL
   - Below 16th percentile: BEAR
   - Between 16th and 84th: RANGING
   - This uses the 1-standard-deviation threshold from normal distribution

4. **Volatility Regime:**
   - BTC 30-day annualized vol < 50%: low vol (likely bull or range)
   - BTC 30-day annualized vol 50-80%: medium vol (transitional)
   - BTC 30-day annualized vol > 80%: high vol (bear or crisis)
   - BTC 30-day annualized vol > 120%: extreme vol (crisis)

5. **Additional crisis indicators:**
   - ATR > 2.0x the 6-month average
   - Average crypto pair correlation > 0.7 (everything correlating = crisis)
   - Liquidation cascades occurring

### How Regime Misclassification Affects Trade Outcomes

Regime misclassification is one of the most damaging errors because it cascades through every parameter:

**Scenario: RANGING classified as BULL**
- Consequences: stop_adj = 0.85 (too tight for range), tp_adj = 1.25 (unreachable targets), trend-following signals dominate (will whipsaw)
- Expected impact: win rate drops 15-20 percentage points
- Typical symptom in attribution: high stop-loss hit rate with many trades stopping out just before mean-reverting

**Scenario: BEAR classified as RANGING**
- Consequences: stop_adj = 1.0 (too tight for bear), risk/trade stays at 1-1.5% (too high for bear), mean reversion signals used (they fail in bears)
- Expected impact: outsized losses on mean-reversion longs that don't revert
- Typical symptom: large negative P&L on long-side trades with mean-reversion exit reasons

**Scenario: Early CRISIS classified as BEAR**
- Consequences: trading continues with bear parameters instead of halting
- Expected impact: correlation spike means all positions move against the fund simultaneously
- Typical symptom: all open positions hitting stops on the same day

**Detection method:**
When attribution shows unexpected patterns (e.g., stop-loss hit rate > 50% when it should be 30-40%), the first thing to investigate is whether regime classification was incorrect during the period. Cross-reference the fund's regime label with the five confirmation indicators listed above.

## 3.2 Attribution by Conviction Level

### Expected Calibration Curve

A well-calibrated conviction system should produce win rates that approximate:

| Conviction Score | Expected Win Rate | Acceptable Range |
|-----------------|-------------------|-----------------|
| 1 | ~10% | 5-20% |
| 2 | ~20% | 10-30% |
| 3 | ~30% | 20-40% |
| 4 | ~40% | 30-50% |
| 5 | ~50% | 40-60% |
| 6 | ~60% | 50-70% |
| 7 | ~70% | 60-80% |
| 8 | ~80% | 70-90% |
| 9 | ~90% | 80-95% |
| 10 | ~95% | 90-100% |

The relationship is: **conviction N should win approximately (N * 10)% of the time.**

### Conviction Calibration Ratio

```
calibration_ratio = actual_win_rate / expected_win_rate

where:
  expected_win_rate = conviction_score / 10
  actual_win_rate = winning_trades_at_conviction / total_trades_at_conviction
```

**Interpretation:**
- calibration_ratio = 1.0: perfectly calibrated
- calibration_ratio > 1.2: underconfident (actual wins exceed expected -- the system is leaving alpha on the table by being too cautious)
- calibration_ratio < 0.8: overconfident (actual wins fall short of expected -- the system is overestimating its edge)
- calibration_ratio < 0.5: seriously miscalibrated (actual wins are less than half of expected -- critical issue)

### Calibration Inversion Detection

**If conviction 8 trades win at a lower rate than conviction 5 trades, calibration is broken.**

This is a critical red flag. It means:
- The signal aggregation pipeline is assigning high confidence to low-quality signals
- The individual analyst teams may have systematic biases
- The Bayesian log-odds aggregation may be amplifying correlated errors

When this is detected:
1. Disaggregate by team: which team(s) are contributing the inflated confidence?
2. Check team independence: are teams using correlated inputs? (e.g., two teams both primarily using RSI)
3. Check for regime-dependent calibration: is the inversion only present in one regime?
4. Recommend specific recalibration: weight adjustment for the offending team(s)

### How the Fund Uses Calibration Ratios

The calibration ratio is used to scale future conviction in the aggregator:

```
adjusted_conviction = raw_conviction * calibration_ratio

Example:
  Team X signals conviction 8
  Team X's historical calibration ratio = 0.70 (overconfident)
  Adjusted conviction = 8 * 0.70 = 5.6 (rounded to 6)
```

This means overconfident teams get their signals dampened, and underconfident teams get amplified. The system is self-correcting IF calibration ratios are updated regularly (recommended: every 30 days with rolling 90-day window).

### Position Sizing Scales with Conviction

```
position_size = base_size * kelly_fraction * conviction_calibration * regime_factor

where:
  base_size = tier-specific max position (e.g., 20% for BTC, 2% for meme)
  kelly_fraction = regime-specific Kelly (e.g., 25-50% in bull, 10-25% in bear)
  conviction_calibration = calibration_ratio for the specific conviction level
  regime_factor = position size factor (1.0x bull, 0.5x bear, 0.7x ranging, 0.25x crisis)
```

**Example: BTC trade, conviction 7, bull regime, well-calibrated**
- base_size = 20%
- kelly_fraction = 0.375 (midpoint of 25-50%)
- conviction_calibration = 1.0 (well-calibrated at 7)
- regime_factor = 1.0
- position_size = 20% * 0.375 * 1.0 * 1.0 = 7.5% of portfolio

**Example: Mid-cap trade, conviction 7, bear regime, overconfident team (cal ratio 0.7)**
- base_size = 5%
- kelly_fraction = 0.175 (midpoint of 10-25%)
- conviction_calibration = 0.7
- regime_factor = 0.5
- position_size = 5% * 0.175 * 0.7 * 0.5 = 0.31% of portfolio

This dramatic difference in sizing (7.5% vs 0.31%) is intentional and correct. It reflects the compound effect of lower confidence, lower-quality asset, unfavorable regime, and calibration problems.

## 3.3 Attribution by Exit Reason

### STOP_LOSS Exits

**What a high stop-loss hit rate means (by context):**

| SL Hit Rate | Context | Likely Cause | Action |
|---|---|---|---|
| > 60% | All regimes | Stops are too tight OR direction is systematically wrong | Widen stops (increase ATR multiplier by 0.5) or investigate signal quality |
| > 50% | Bull regime only | Stops too tight for crypto volatility | Increase stop_adj from 0.85 to 0.95 |
| > 50% | Bear regime, long side | Trading against the trend | Reduce long-side activity in bear markets |
| > 50% | Meme tier only | Meme coin noise exceeds stop width | Consider increasing meme stop ATR from 4.5x to 5.5x |
| 30-40% | Any | Normal range for trend-following systems | No action needed |
| < 20% | Any | Stops may be too wide (giving back too much profit) | Consider tightening |

**Stop loss P&L analysis:**
- Calculate the average loss size on SL exits
- Compare to the theoretical 1R loss (if SL is set at exactly risk per trade)
- If average SL loss > 1.2R: slippage is significant; consider limit-order stops or smaller positions in illiquid markets
- If average SL loss < 0.8R: stops are being hit on partial positions after partial TP fills (this is normal and good)

### TAKE_PROFIT_1 Exits

**The key question: are we exiting too early?**

Analysis method:
1. For each TP1 exit, record the price at TP1 exit
2. Track the asset's subsequent price movement for the next 24-48 hours
3. Calculate: `missed_move = (subsequent_high - tp1_exit_price) / tp1_exit_price`

**Interpretation:**
| Avg Missed Move After TP1 | Meaning | Action |
|---|---|---|
| < 1% | TP1 is well-placed; asset typically reverses near TP1 | None |
| 1-3% | Small additional move; TP1 is slightly conservative but acceptable | Consider raising TP1 R-multiple by 0.25 |
| 3-5% | Material additional move being left on the table | Raise TP1 R-multiple by 0.5 or reduce TP1 exit fraction from 33% to 25% |
| > 5% | TP1 is significantly too conservative | Major parameter issue; TP1 R-multiple needs increase or TP1 fraction needs reduction |

**Regime-specific TP1 analysis:**
- In BULL: missed moves after TP1 should be larger (trends extend) -- this is expected and acceptable because the trailing 34% captures the extension
- In BEAR: missed moves after TP1 should be smaller (bounces fizzle) -- if they are large, bear regime may be misclassified

### TAKE_PROFIT_2 Exits

**Hit rate analysis by tier:**

Expected TP2 hit rates (conditional on TP1 being hit):
| Tier | Expected TP2 Hit Rate | If Lower Than Expected | If Higher Than Expected |
|---|---|---|---|
| BTC | 40-50% | TP2 too aggressive; reduce TP2 R-multiple | TP2 too conservative; increase it |
| Top5 | 35-45% | Same | Same |
| Large-cap | 30-40% | Same | Same |
| Mid-cap | 25-35% | Same | Same |
| Meme | 15-25% | Consider whether TP2 is reachable at all for memes | Meme momentum is stronger than expected |

If TP2 hit rate is below 15% for any tier consistently over 30+ trades, TP2 is set too aggressively for that tier. The 34% trailing remainder captures the extended move instead, so an unreachable TP2 is not catastrophic but is suboptimal because the 33% sits in limbo between TP1 and the trailing stop.

### TRAILING_STOP Exits

**Trail tightness analysis:**

Calculate the profit captured by the trailing stop as a percentage of the maximum favorable excursion (MFE):

```
trail_efficiency = profit_at_trail_exit / maximum_favorable_excursion

where:
  profit_at_trail_exit = exit_price - entry_price (for longs)
  MFE = highest_price_reached - entry_price (for longs)
```

| Trail Efficiency | Meaning | Action |
|---|---|---|
| > 80% | Trail is very tight; capturing most of the move | Risk: may be cutting trades too early on normal retracements |
| 60-80% | Trail is well-balanced | Optimal range |
| 40-60% | Trail is loose; giving back significant gains | Consider tightening trail ATR multiplier by 0.5 |
| < 40% | Trail is too loose; losing most of the captured gains on reversals | Urgent: tighten trail significantly |

**Regime-specific trailing analysis:**
- BULL: trail efficiency should be 50-70% (accept giving back some gains to ride extended moves)
- BEAR: trail efficiency should be 70-85% (take what the market gives, do not give back)
- RANGING: trail efficiency should be 75-90% (tight trails work because trends are short)

### TIME_STOP Exits

**Are positions being held too long?**

Analysis method:
1. For each time-stop exit, record the P&L at exit
2. Calculate: what percentage of time-stop exits are winners vs losers?

| % of Time-Stop Exits That Are Winners | Meaning | Action |
|---|---|---|
| > 50% | Time stop is cutting winners; time limit is too short | Extend time_adj or increase max hours for affected tier |
| 30-50% | Normal distribution; time stop is cleaning up stale positions | No action |
| < 30% | Positions reaching time stop are overwhelmingly losers | Positions are being held too long; consider REDUCING time limit |
| < 15% | Nearly all time-stop exits are losers | Strong signal that time stops should be shorter; the position thesis has already failed before the time stop |

**Optimal holding period analysis:**

Bucket all trades into holding period ranges and calculate win rate and average P&L for each:

| Holding Period | Expected Pattern (Trend Following) | Red Flag |
|---|---|---|
| 0-4 hours | Low win rate, small P&L (trade hasn't developed) | N/A |
| 4-12 hours | Moderate win rate, moderate P&L (signal developing) | If win rate is already declining here, signals may be too short-lived |
| 12-24 hours | Peak win rate for many crypto signals | If win rate peaks here but time stop is 120h+, position is held too long |
| 24-48 hours | Win rate starts declining for most crypto assets | Natural alpha decay; most signals lose predictive power |
| 48+ hours | Win rate should decline unless a strong trend is active | If win rate increases here, it suggests the fund should hold longer |

**Time decay of alpha:** Research shows that crypto trading signals lose predictive power over time. The half-life of alpha varies by signal type:
- Sentiment signals: 4-12 hour half-life (very short)
- Technical signals: 12-48 hour half-life
- On-chain signals: 24-168 hour half-life (longer)
- Macro signals: 48-336 hour half-life (longest)

The fund's time stops by tier should reflect these half-lives:
| Tier | Max Hours | Rationale |
|---|---|---|
| BTC | 360 (15 days) | BTC trends are persistent; macro and on-chain signals support longer holds |
| Top5 | 240 (10 days) | Moderate trend persistence |
| Large-cap | 168 (7 days) | Standard crypto trend duration |
| Mid-cap | 120 (5 days) | Faster alpha decay |
| Meme | 48 (2 days) | Sentiment-driven, extremely short alpha half-life |

### Exit Reason Distribution by Tier (Expected Benchmarks)

| Exit Reason | BTC | Top5 | Large-cap | Mid-cap | Meme |
|---|---|---|---|---|---|
| STOP_LOSS | 25-35% | 30-40% | 35-45% | 40-50% | 45-55% |
| TAKE_PROFIT_1 | 20-30% | 20-25% | 15-25% | 15-20% | 15-20% |
| TAKE_PROFIT_2 | 10-20% | 10-15% | 8-12% | 5-10% | 3-8% |
| TRAILING_STOP | 15-25% | 15-20% | 10-15% | 8-12% | 5-10% |
| TIME_STOP | 10-20% | 15-20% | 15-25% | 20-25% | 20-30% |

**Pattern to watch:** If STOP_LOSS percentage significantly exceeds the benchmark for a tier, investigate whether stops are too tight or signals are too weak. If TIME_STOP percentage significantly exceeds benchmark, positions are languishing without conviction.

## 3.4 Attribution by Asset Tier

### BTC Tier
- Most liquid crypto asset by far
- Lowest relative volatility (BTC annualized vol averages 91.73%, which is high for traditional assets but lowest among crypto)
- Should have the highest win rate of any tier
- Expected win rate: 45-55% (trend following)
- BTC dominance tends to increase in bear markets (flight to safety within crypto)
- If BTC win rate drops below 40%, something is fundamentally wrong with signal generation

### Top5 Tier (ETH, BNB, SOL, etc.)
- Moderately liquid, higher vol than BTC
- ETH drawdowns historically exceed BTC by 10-15 percentage points
- Expected win rate: 40-50%
- Higher correlation to BTC during bear markets (correlation rises from 0.5-0.6 to 0.7-0.8)
- Attribution should track whether Top5 assets are simply tracking BTC or generating independent alpha

### Large-Cap Tier
- Variable liquidity; some large-caps have thin order books during stress
- Expected win rate: 35-45%
- Higher slippage risk than BTC/Top5
- Attribution should flag any large-cap where actual fill price differs from signal price by > 0.5%

### Mid-Cap Tier
- High vol, high risk, potential for outsized returns
- Expected win rate: 30-40%
- Liquidity can evaporate suddenly; slippage of 1-3% is common
- The fund's 0.75% risk/trade limit means positions are small
- Attribution should specifically track whether the higher risk/reward ratio (1:3 R-multiple target) compensates for the lower win rate

### Meme Tier
- Extreme volatility (daily swings of 20-50% are common)
- Should only be traded with highest conviction (conviction >= 8)
- Expected win rate: 20-35%
- Risk/trade of 0.25% means even total loss of a meme position is manageable
- Attribution should verify that meme trades are not concentration risk (many small positions can aggregate to significant exposure)
- Key metric: what percentage of total P&L comes from meme trades? If > 20% (positive or negative), meme trading is dominating fund performance, which is undesirable

## 3.5 Attribution by Side (Long vs Short)

### Structural Long Bias in Crypto

Crypto has a secular upward drift over multi-year periods. This creates a structural advantage for long positions and a structural headwind for shorts. The expected baseline:

| Regime | Long Win Rate | Short Win Rate | Expected Spread |
|---|---|---|---|
| BULL | 50-65% | 25-35% | +20-30 pp long advantage |
| BEAR | 25-35% | 45-55% | +15-25 pp short advantage |
| RANGING | 45-55% | 40-50% | +5-10 pp long advantage |
| CRISIS | 20-30% | 50-65% | +20-35 pp short advantage |

### Anomaly Detection by Side

**If shorts have higher win rate than longs in BULL regime:**
- Something unusual is happening
- Possible causes: regime misclassification (it's not actually a bull), sector rotation (specific assets declining while BTC rises), or a specific team is generating contrarian short signals that happen to be correct
- Action: investigate immediately; this pattern is abnormal and suggests regime detection issues

**If longs have higher win rate than shorts in BEAR regime:**
- Less unusual (mean reversion bounces in bear markets can be profitable)
- But if persistent: bear regime classification may be wrong, or the fund is successfully catching counter-trend rallies
- Verify: are these long wins from mean-reversion trades (good) or trend-following longs (lucky/dangerous)?

### Short-Side Specific Considerations
- Funding rate risk: perpetual futures shorts pay funding when rates are positive (~0.01-0.1% per 8 hours in bull markets)
- During the 2022 bear, funding rates went deeply negative (-0.1% per 8hr), meaning SHORT crowding created squeeze risk
- Attribution should track funding costs separately from trade P&L to understand true short-side profitability
- When shorts become overcrowded (deeply negative funding), squeeze probability rises dramatically

### Long/Short P&L Decomposition

For each period, decompose total P&L:
```
total_pnl = long_pnl + short_pnl
long_contribution = long_pnl / abs(total_pnl) * 100%
short_contribution = short_pnl / abs(total_pnl) * 100%
```

**Expected contributions by regime:**
| Regime | Long P&L Contribution | Short P&L Contribution |
|---|---|---|
| BULL | 80-120% (can exceed 100% if shorts lose) | -20% to +20% |
| BEAR | -20% to +20% | 80-120% |
| RANGING | 40-60% | 40-60% |
| CRISIS | Negative (losses) | Positive (gains) |

If the actual contributions deviate significantly from these expectations, it signals either excellent edge in the minority direction or a problem with the majority direction.

## 3.6 Attribution by Holding Period

### Holding Period Buckets

| Bucket | Duration | Expected Trade Type |
|---|---|---|
| Ultra-short | 0-4 hours | Scalps, failed signals closed early |
| Short | 4-12 hours | Day trades, sentiment-driven moves |
| Medium | 12-24 hours | Swing trade entries, overnight holds |
| Standard | 24-48 hours | Classic swing trades |
| Extended | 48-168 hours (2-7 days) | Trend rides, multi-day positions |
| Long | 168+ hours (7+ days) | Strong trend positions, BTC/Top5 holds |

### Optimal Holding Period by Tier and Regime

| Tier | BULL Optimal | BEAR Optimal | RANGING Optimal |
|---|---|---|---|
| BTC | 24-168 hours | 12-48 hours | 4-24 hours |
| Top5 | 12-120 hours | 8-36 hours | 4-24 hours |
| Large-cap | 12-72 hours | 4-24 hours | 4-12 hours |
| Mid-cap | 4-48 hours | 4-12 hours | 2-12 hours |
| Meme | 2-24 hours | 2-8 hours | 1-8 hours |

### How to Identify Suboptimal Holding Periods

Calculate the average P&L for each holding period bucket. Plot a curve. The optimal holding period is where the curve peaks.

**Common patterns:**
1. **P&L peaks at 12-24 hours then declines:** Signals are short-lived; the fund is holding too long. Recommendation: reduce time stops.
2. **P&L increases monotonically with holding period:** Strong trend capture; time stops may be too short. Recommendation: extend time stops (but watch max drawdown).
3. **P&L peaks at 4-12 hours, goes negative at 24+ hours:** Alpha decays rapidly. The fund should exit faster. This is especially common with sentiment-driven signals.
4. **Bimodal distribution (peaks at 4h and 72h+):** Two types of trades: quick scalps and extended trends. The 12-48h range is the dead zone. Consider having different time-stop profiles for different trade types.

---

# 4. Historical Bear Market Data

## 4.1 BTC Bear Market Drawdown History

| Cycle | Peak Price | Trough Price | Max Drawdown | Duration to Bottom | Recovery to New ATH |
|-------|-----------|-------------|-------------|-------------------|-------------------|
| 2011 | $32 | $2 | -93% | ~5 months (~160 days) | ~2 years (~730 days) |
| 2013-2015 | $1,163 | $170 | -86% | ~410 days | ~3 years (~1,095 days) |
| 2017-2018 | $19,100 | $3,200 | -83% | ~365 days | ~3 years (~1,095 days) |
| 2021-2022 | $69,000 | $15,476 | -77% | ~330 days | ~2 years (~730 days) |
| 2025-2026 | $126,198 | ~$65,000 | -46%+ (ongoing) | ~119 days+ (ongoing) | TBD |

### Key Pattern: Decreasing Maximum Drawdowns

Maximum drawdowns across cycles: 93% -> 86% -> 83% -> 77%.

This reflects market maturation:
- Increasing institutional participation provides a floor
- ETF structures create systematic buying at lower prices
- Growing market capitalization means each marginal dollar moves the price less
- More sophisticated hedging tools reduce forced selling cascades

**Extrapolation (use with caution):** If the trend continues, the next max drawdown would be ~70-73%. Applied to the 2025-2026 cycle's $126,198 ATH, that would suggest a floor around $34K-$38K. However, the current drawdown of ~46% is well above that, so the question is whether this is a mid-cycle correction or the beginning of a full bear.

### Duration Statistics

| Metric | Value |
|---|---|
| Average bear market duration (70%+ decline) | 9 months |
| Shortest severe downturn | 4-5 months (2011) |
| Extended bear markets | 12-13 months |
| Median across all 15 bear markets since 2014 | 101 days to bottom |
| Average time to new ATH (simple corrections) | 249 days |
| Average time to new ATH (deep bears) | 531 days |

### Severity Escalation Rule

Once a Bitcoin drawdown becomes prolonged (100+ days to bottom), both depth and duration nearly double:

| Category | Avg Drawdown | Avg Days to Bottom | Avg Days to New ATH |
|---|---|---|---|
| Simple corrections | 40.7% | 101 days | 249 days |
| Prolonged bears (100+ days) | 59.2% | 215 days | 531 days |

**Implication for attribution:** The current cycle (119+ days to bottom as of March 2026) has already crossed the 100-day threshold, suggesting this is a prolonged bear, not a simple correction.

## 4.2 ETH Bear Market Drawdowns

| Cycle | Peak | Trough | Max Drawdown |
|-------|------|--------|-------------|
| 2018 | $1,396 | $86.54 | -93.8% |
| 2022 | $4,812 | $896 | -79.5% |

**ETH drawdowns historically exceed BTC by 10-15 percentage points.** This is critical for tier-based attribution: Top5 assets (primarily ETH) should be expected to have worse drawdowns and lower win rates than BTC during bear markets.

### Altcoin Survival Statistics

| Token | 2017 Peak Rank | Current Rank | ATH Recovered? |
|---|---|---|---|
| Bitcoin Cash | #4 | #27 | NO |
| NEM | #6 | #102 | NO |
| Stellar | #9 | #24 | NO |
| IOTA | #10 | #63 | NO |

**4 of the top 10 tokens from 2017 NEVER recovered their ATHs.** This is critical for mid-cap and large-cap attribution: survival bias means we only see the winners. Dead tokens disappear from analysis.

Additional context:
- 2018: 1,359 tokens in existence
- 2022: ~20,000 tokens (massive dilution risk)
- 38% of all altcoins near all-time lows as of March 2026 (surpassing FTX collapse level of 37.8%)
- ETH dominance at 10.0% (historical low)
- Altcoin Season Index at 35 (deep in "Bitcoin Season")

## 4.3 Bear Market Strategies That Worked (2022 Evidence)

### Dollar-Cost Averaging (DCA)
- DCA through crash: average cost basis ~$35K vs $43K for lump-sum (33 percentage point advantage)
- DCA through 2022 crash yielded +192.47% return by 2025
- Fear-weighted DCA (2x allocation when F&G < 25): +1,145% over 7-year backtest
- Monday DCA accumulated 14.36% more BTC than other weekdays (2018-2025)
- Every extreme fear period (F&G < 20) rewarded DCA investors with subsequent returns exceeding 500%

### Market-Neutral / Quant Strategies
- Pythagoras crypto hedge funds: +8% in 2022 while BTC dropped 65%
- Market-neutral fund of funds: 870% gross return since 2018 across all cycles
- Stoic AI Meta strategy: ~45% annualized across all cycles
- Pairs trading (Distance Method): positive returns even as ETH dropped 61.77%
- BlockTower Capital and Nickel Digital: positive returns throughout 2022

### Short Selling
- Direct short sellers earned $2.5B+ from MSTR shares alone in 2025
- Key risk: funding rates turned deeply negative (-0.1% per 8hr) meaning short crowding was real
- When funding goes deeply negative: shorts are overcrowded and a squeeze is likely

### Combined Momentum + Mean Reversion (50/50)
- Sharpe ratio: 1.71
- Annualized return: 56%
- T-stat: 4.07
- Best risk-adjusted returns across all market cycles

## 4.4 Bear Market Strategies That Failed

1. **Buy-the-dip without discipline:** Terra collapse (May 2022) wiped out dip buyers, then FTX collapse (Nov 2022) hit again -- BTC fell 25% in a week ($20K to $15K)
2. **Leveraged longs:** Catastrophic in sustained downtrends
3. **Undisciplined altcoin accumulation:** 4 of 2017 top-10 NEVER recovered ATHs
4. **~250 of 715 crypto hedge funds closed (35%)** from May 2022 to Dec 2023
5. **Three Arrows Capital:** Collapsed from leveraged supercycle thesis
6. **Alameda Research:** Failed from overleveraged directional bets

## 4.5 Dead Cat Bounce Characteristics

| Metric | Value |
|---|---|
| Typical dead cat bounce | 15-30% recovery before resuming downtrend |
| Stall point | ~25-30% above the low of the previous decline |
| Recovery retracement | 30-50% of the original fall before resuming downward |

### Dead Cat Bounce Identification Signals
1. **Decreasing volume:** Bounces on below-average volume indicate weak participation
2. **Contracting spot demand:** Example: -67K BTC in 30 days during recent bounce
3. **Negative funding rates across perpetual futures:** Shorts are crowded but not covering with conviction
4. **Failure to reclaim key moving averages:** Bounce that stalls at the 20-day or 50-day MA
5. **Declining number of coins above their own 200-day MA:** Breadth does not improve with price

### Bear Market Rally Size Data

Following 70%+ BTC declines:
| Metric | Value |
|---|---|
| Average rally from bottom | 3,485% |
| Median rally from bottom | 1,692% |
| Minimum rally | 101% |
| Maximum rally | 12,804% |
| Most recent (2022 low to 2025 peak) | 716% |

### Post-70%+ Decline Short-Term Stats
| Metric | Value |
|---|---|
| Average 90-day return from bottom | 62% |
| Probability of positive 90-day return | 78% |
| 1-year win rate buying at -50% from ATH | 90% |
| 1-year win rate buying at -70% from ATH | 100% (worst case: +25%) |

## 4.6 On-Chain Capitulation Markers (2022 Reference Data)

| Metric | 2022 Value | Significance |
|---|---|---|
| Mayer Multiple | 0.487 | Lowest on record; only 2% of trading days below 0.50 |
| Realized Cap Z-Score | -2.73 SD | One full SD larger than 2018 or March 2020 |
| Single-day realized loss | -$4.234 billion | 22.5% above previous record |
| Daily loss rate | -98,566 BTC/day | 0.52% of circulating supply |
| Volume in loss vs profit | 2.3x ratio | During LUNA crash |

### Bottom Formation Indicators
1. MVRV Z-Score entering accumulation zone
2. Mayer Multiple below 0.5 (only 2% of all trading days)
3. Hash Ribbons showing miner capitulation
4. Exchange reserves declining (coins moving to cold storage)
5. Whale accumulation accelerating (2026 data: 270K BTC in 30 days -- largest 13-year net purchase)

## 4.7 Sector Performance in Bear Markets

| Sector | 2022 Max Drawdown | Recovery Notes |
|---|---|---|
| Bitcoin (BTC) | -77% | Recovered to new ATH by March 2024 |
| Ethereum (ETH) | -79.5% to -81% | Slower recovery, ETH/BTC ratio declined |
| DeFi (TVL) | -64% ($184.5B to $66.7B) | Deleveraging primary driver |
| NFTs | -80%+ trading volume | Partial recovery late 2024 |
| Exchange Tokens | Outperformed BTC/ETH | 7 of 8 exchange tokens beat BTC/ETH over 6 months |
| Stablecoins | Gained market share | Aggregate cap flipped ETH for first time |
| Legacy Alts (2017) | -90%+ and never recovered | 4 of top-10 still below 2017 ATHs |

**Relative outperformers in bear markets (order):**
1. Stablecoins (capital preservation)
2. Infrastructure/Exchange tokens
3. BTC (smallest drawdowns among volatile crypto)
4. Tokens with real revenue (protocol fees, staking yields)

**Worst performers in bear markets (order):**
1. NFTs/Metaverse/Gaming (speculative narrative collapse)
2. DeFi leveraged tokens (deleveraging cascade)
3. Small-cap altcoins (liquidity drought; many never recover)
4. Previous-cycle hype tokens (40% of top-10 from any cycle fail to recover ATHs)

---

# 5. Fear & Greed Trading Data

## 5.1 Extreme Fear Performance (F&G < 10)

| Date | F&G Value | BTC Price | 30-Day Return | 90-Day Return | 12-Month Return |
|------|-----------|-----------|---------------|---------------|-----------------|
| Dec 2018 | ~10 | ~$3,200 | +15% | +30% | +158% |
| Mar 2020 (COVID) | 9 | ~$4,500 | +70% | +170% | +1,500% |
| Jun 2022 (Luna) | 6 | ~$20,000 | +20% | +5% | +20% |
| Nov 2022 (FTX) | 6 | ~$15,500 | +15% | +40% | +85% |
| Feb 2026 | 5 (ATL) | ~$67,500 | TBD | TBD | TBD |

### Key Statistics at F&G <= 10
- **Sharpe ratio: 8.0** (for context, best hedge funds globally achieve ~2.0)
- Positive 30-day return probability: ~85%
- Average 12-month return: +440% (excluding ongoing 2026 data)
- This is the single highest-Sharpe trading signal in crypto history

## 5.2 Broader Extreme Fear Data (F&G < 20)

| Metric | Value |
|---|---|
| Positive 30-day returns | ~80% of the time |
| Median 90-day return | +32% |
| Average 6-month return | +60-80% |
| Average 12-month return | +300-500% |

## 5.3 F&G Bucket Returns (Complete Table)

| F&G Range | Avg 30-Day Return | Avg 90-Day Return | Win Rate (30d) |
|-----------|-------------------|-------------------|----------------|
| 0-10 | +25-35% | +50-100% | ~85% |
| 10-20 | +10-20% | +30-50% | ~80% |
| 20-30 | +5-10% | +15-25% | ~65% |
| 30-50 | +2-5% | +5-15% | ~55% |
| 50-70 | 0-3% | +2-8% | ~50% |
| 70-80 | -2 to 0% | -5% to +5% | ~45% |
| 80-90 | -5% to -2% | -15% to -5% | ~35% |
| 90-100 | -10% to -5% | -25% to -10% | ~25% |

**Edge is asymmetric:** The buy-side edge at extreme fear (F&G 0-10) is far stronger than the sell-side edge at extreme greed (F&G 90-100). This is because crypto bottoms are sharper and more violent than tops, which tend to form gradually.

## 5.4 Extreme Greed as Sell Signal (F&G > 80)

| Date | F&G Value | BTC Price | 30-Day Return | 90-Day Return |
|------|-----------|-----------|---------------|---------------|
| Late 2017 | 90+ | ~$19,000 | -30% | -55% |
| April 2021 | 85+ | ~$64,000 | -40% | -55% |
| Nov 2021 | 84 | ~$68,000 | -15% | -40% |

**Key stat:** F&G > 80 sustained for 14+ days: ~70% chance of >20% drawdown within 90 days.

## 5.5 Fear-Based Trading Strategy Backtests

| Strategy | Return | Annualized | Risk Profile |
|---|---|---|---|
| Standard DCA (fixed weekly buy) | 202% (7yr) | ~17% | Baseline |
| Fear-weighted DCA (2x below F&G 25) | 1,145% (7yr) | ~43% | 5.7x better than standard DCA |
| Buy at F&G <= 10, sell at F&G > 35 | -- | 14.6% | Best risk-adjusted (highest Sharpe) |
| Buy at F&G <= 10, sell at F&G > 50 | Lower Sharpe | -- | More volatile |
| Buy at F&G <= 10, sell at F&G > 65 | Worst of three | -- | Holding too long reduces returns |

**The most important insight from this data:** The short-term strategy (buy at extreme fear, sell at modest recovery) produces the best RISK-ADJUSTED returns. Holding for greed territory actually underperforms. This means mean reversion at extremes is the edge, not trend-riding from extremes.

## 5.6 When Fear & Greed Signals FAIL

### The June 2022 False Signal

- F&G reached 6 in June 2022 during Luna contagion
- This was a buy signal by the indicator
- But Luna contagion was STILL SPREADING (Celsius, Voyager, 3AC cascading)
- Buying at F&G = 6 in June meant buying at ~$20K and watching it fall to $15.5K five months later
- The buy signal was 5 months early

### The Rule for F&G Extremes

**Extreme fear is a buy signal IF the cause is EXOGENOUS or RESOLVED.**
**Extreme fear is NOT a buy signal during ACTIVE ENDOGENOUS CONTAGION.**

| Cause Type | Examples | F&G Signal Valid? |
|---|---|---|
| Exogenous (external macro shock) | COVID crash, tariff fears, rate hikes | YES |
| Endogenous but resolved | Exchange hack (contained), regulatory FUD (clarified) | YES |
| Endogenous and ACTIVE | Luna/Terra cascading, FTX contagion spreading | NO -- wait until contagion stops |

### How to Verify No Active Contagion

1. Check for recent protocol/exchange failures in the last 14 days
2. Check CeFi/DeFi lending: any abnormal withdrawal rates?
3. Check stablecoin pegs: any depeg events?
4. Check on-chain: mass movements from cold to hot wallets (indicating forced selling)?
5. If any of these are active: the F&G signal is unreliable. Wait.

## 5.7 F&G Combined with Other Signals

| Signal Combination | Historical Reliability | Notes |
|---|---|---|
| F&G < 15 + RSI < 30 + price below SMA200 | ~90% 12-month win rate | Strongest buy signal in crypto |
| F&G < 20 + BTC dominance rising | High | Flight to safety; bottom forming |
| F&G > 80 + funding rate > +0.1% | Strongest sell/short signal | -- |
| F&G < 15 + whale accumulation spike | Very high | Current pattern (March 2026): 270K BTC accumulated in 30 days |

## 5.8 Current Conditions (March 2026)

| Metric | Value | Historical Significance |
|---|---|---|
| F&G Index | 5-16 range (38+ consecutive days below 25) | Longest streak since Terra/Luna collapse |
| BTC price | ~$65K-$70K | Down ~46% from $126,198 ATH |
| Weekly RSI | 27.48 | Lowest since December 2018 |
| Whale accumulation | 270,000 BTC in 30 days (~$18.7-23B) | Largest 13-year net purchase recorded |
| Exchange reserves | 2.31M BTC (lowest since April 2018) | 47,000+ BTC/week leaving exchanges |
| MicroStrategy holdings | 738,731 BTC total | Acquired 17,994 BTC for $1.3B in Mar 2-8 |

Historical performance from similar RSI levels:
- Jan 2015 (RSI ~27): produced +9,900% rally
- Dec 2018 (RSI ~25): produced +1,700% rally

---

# 6. Position Sizing Theory & Practice

## 6.1 Kelly Criterion

### Full Formula

```
f* = p - (1 - p) / b

where:
  f* = optimal fraction of capital to bet
  p  = probability of winning
  b  = ratio of win amount to loss amount (reward/risk ratio)
```

### Examples

| Scenario | p (win prob) | b (R:R) | Kelly f* | Interpretation |
|---|---|---|---|---|
| Coin flip with 2:1 payout | 0.50 | 2.0 | 0.25 | Bet 25% of capital |
| Strong edge, even payout | 0.60 | 1.0 | 0.20 | Bet 20% of capital |
| Weak edge, 3:1 payout | 0.35 | 3.0 | 0.133 | Bet 13.3% of capital |
| No edge | 0.50 | 1.0 | 0.00 | Do not bet |
| Negative edge | 0.40 | 1.0 | -0.20 | Negative = no bet |

### Why Full Kelly is Never Used in Practice

- Full Kelly assumes exact knowledge of p and b, which never exists in real markets
- Full Kelly produces maximum long-term growth BUT with extreme volatility
- BTC kurtosis is 10.85 (extreme fat tails); crypto basket kurtosis is 27
- With fat-tailed distributions, Kelly overstates the optimal bet size
- Small estimation errors in p or b can produce dramatically wrong Kelly fractions

### Fractional Kelly by Regime

| Kelly Fraction | Growth Rate Retained | Volatility vs Full Kelly | When to Use |
|---|---|---|---|
| Full Kelly (1.0) | 100% | 100% | NEVER in practice for crypto |
| Half Kelly (0.50) | 75% of max growth | 25% of full Kelly variance | Aggressive systematic funds with verified edge in bull markets |
| Quarter Kelly (0.25) | ~56% of max growth | ~6% of full Kelly variance | Standard institutional; most common in uncertain environments |
| 10% Kelly (0.10) | ~19% of max growth | ~1% of full Kelly variance | Crisis mode; highly uncertain edge estimates |

### Regime-Specific Kelly Application

| Regime | Kelly Fraction | Rationale |
|---|---|---|
| BULL | 25-50% | Higher confidence in edge estimates; favorable market dynamics |
| BEAR | 10-25% | Elevated uncertainty, fat tail risk, correlated drawdowns |
| RANGING | 20-30% | Mean reversion has higher win rate but smaller payoffs; moderate uncertainty |
| CRISIS | 0-10% | Edge estimates are unreliable; capital preservation paramount |

## 6.2 Volatility Parity (Bridgewater Method)

### Concept

Size positions so each contributes equal volatility to the portfolio:

```
position_size_i = target_vol / (vol_i * sqrt(num_positions))

where:
  target_vol = portfolio-level annualized volatility target (10-15%)
  vol_i = annualized volatility of asset i
  num_positions = number of open positions
```

### Example

Target portfolio vol: 12% annualized
BTC 30-day annualized vol: 60%
ETH 30-day annualized vol: 80%
Meme coin vol: 200%

With 5 positions:
- BTC size: 12% / (60% * sqrt(5)) = 8.9%
- ETH size: 12% / (80% * sqrt(5)) = 6.7%
- Meme size: 12% / (200% * sqrt(5)) = 2.7%

This automatically gives more weight to lower-vol assets and less to higher-vol assets, which aligns with the fund's tier-based sizing.

### Advantages
- Adapts automatically to changing volatility conditions
- Ensures each position contributes roughly equally to portfolio risk
- No need to manually adjust position sizes when vol spikes

### Limitations
- Requires stable volatility estimates (crypto vol can change 2x in a day)
- Does not account for correlation (two highly correlated positions contribute more combined risk)
- Should be combined with tier-based maximums as hard limits

## 6.3 ATR-Based Position Sizing

### Formula

```
position_size = risk_amount / (ATR * multiplier)

where:
  risk_amount = portfolio_value * risk_per_trade_pct
  ATR = Average True Range (14-period default)
  multiplier = stop-loss ATR multiplier (varies by tier and regime)
```

### Example

Portfolio value: $1,000,000
Risk per trade: 1.0% (Large-cap tier)
Risk amount: $10,000
BTC 14-day ATR: $2,500
Stop multiplier: 2.0x ATR

Position size in dollars: $10,000 / ($2,500 * 2.0) = $10,000 / $5,000 = 2.0 BTC
Position size as % of portfolio: if BTC = $70,000, then 2.0 * $70,000 = $140,000 = 14%

This exceeds the BTC max position of 20%, so it is acceptable. But for a smaller risk allocation or higher ATR, the position would naturally size down.

## 6.4 The 3-5-7 Rule

A simple heuristic framework used by professional traders:

| Rule | Limit | Application |
|---|---|---|
| **3% rule** | Max risk per single trade: 3% | No single trade should risk more than 3% of portfolio |
| **5% rule** | Max risk across all open positions: 5% | Total risk of all concurrent positions must not exceed 5% |
| **7% rule** | Max total exposure: 7% | Maximum total portfolio heat (sum of all unrealized P&L in risk terms) |

### The Fund's Tier-Based Risk Limits (More Conservative Than 3-5-7)

| Tier | Risk per Trade | Max Position |
|---|---|---|
| BTC | 1.5% | 20% |
| Top5 | 1.2% | 12% |
| Large-cap | 1.0% | 8% |
| Mid-cap | 0.75% | 5% |
| Meme | 0.25% | 2% |

**Note:** The fund's limits are more conservative than the 3-5-7 rule for lower tiers, which is appropriate given the extreme tail risk of crypto altcoins.

## 6.5 Regime-Adaptive Position Size Factor

| Regime | Factor | Effect |
|---|---|---|
| BULL | 1.0x | Full-size positions |
| BEAR | 0.5x | Half-size positions |
| RANGING | 0.7x | 70% of full size |
| CRISIS | 0.25x | Quarter-size (or no positions) |

### Combined Sizing Formula

```
final_position_size = min(
    tier_max_position,
    base_kelly_fraction * conviction_factor * regime_factor * tier_risk_allocation
)
```

This ensures position size is always bounded by the tier maximum while being dynamically adjusted for conviction, regime, and Kelly optimization.

## 6.6 Recovery Math

Understanding why drawdown prevention is more important than return maximization:

| Drawdown | Gain Required to Recover | Difficulty |
|---|---|---|
| 5% | 5.3% | Easy |
| 10% | 11.1% | Moderate |
| 15% | 17.6% | Significant |
| 20% | 25.0% | Hard |
| 25% | 33.3% | Very hard |
| 30% | 42.9% | Extremely hard |
| 40% | 66.7% | Near impossible in one period |
| 50% | 100.0% | Must double remaining capital |
| 60% | 150.0% | -- |
| 70% | 233.3% | -- |
| 80% | 400.0% | -- |
| 90% | 900.0% | -- |

**The key insight:** Drawdowns are nonlinear. A 50% drawdown requires a 100% gain to recover. This is why the fund's crisis parameters are so aggressive about capital preservation: going to 50-100% cash in crisis regime is not cowardice, it is mathematical necessity.

---

# 7. Conviction Calibration Deep Dive

## 7.1 What Well-Calibrated Conviction Looks Like

A perfectly calibrated system produces a linear relationship between conviction and win rate:

```
Perfect calibration: conviction 7 -> ~70% win rate
                     conviction 8 -> ~80% win rate
                     conviction 5 -> ~50% win rate
```

In practice, perfect calibration is impossible, but deviations should be small and consistent:

| Conviction | Perfect Win Rate | Acceptable Range | Investigation Trigger |
|---|---|---|---|
| 4 | 40% | 30-50% | < 25% or > 55% |
| 5 | 50% | 40-60% | < 35% or > 65% |
| 6 | 60% | 50-70% | < 45% or > 75% |
| 7 | 70% | 60-80% | < 55% or > 85% |
| 8 | 80% | 70-90% | < 65% or > 92% |
| 9 | 90% | 80-95% | < 75% or > 97% |

## 7.2 Calibration by Team

### Technical Analysis Team
- **Expected calibration:** Well-calibrated (data-driven, consistent methodology)
- **Typical failure mode:** Overfitting to recent patterns; technical signals that worked in the last 30 days get inflated confidence
- **Regime sensitivity:** Performance degrades in ranging markets where technical signals produce whipsaws
- **Calibration ratio expectation:** 0.85-1.15 (tight range)
- **If calibration ratio drops below 0.70:** Check if the team is using lagging indicators that worked in the prior regime but fail in the current one

### Sentiment Analysis Team
- **Expected calibration:** Often overconfident in bear markets
- **Typical failure mode:** Sentiment indicators are inherently reflexive -- extreme sentiment is both a signal and a cause
- **Regime sensitivity:** Sentiment is a contrarian indicator at extremes but a momentum indicator in the middle range
- **Calibration ratio expectation:** 0.70-1.30 (wider range due to sentiment's nature)
- **If calibration ratio drops below 0.60 in bear markets:** The team is treating every fear spike as a buying opportunity; it needs regime-conditional confidence scaling

### On-Chain / Fundamental Team
- **Expected calibration:** Tends toward underconfidence (conservative)
- **Typical failure mode:** On-chain data has longer time horizons; the team may be right directionally but wrong on timing
- **Regime sensitivity:** On-chain signals are most reliable at extremes (accumulation zones, distribution zones) and least reliable in ranging markets
- **Calibration ratio expectation:** 1.00-1.40 (biased toward underconfidence)
- **If calibration ratio exceeds 1.50:** The team's signals are consistently right but at low conviction -- they should be weighted more heavily

### Macro / Regime Team
- **Expected calibration:** Tends toward underconfidence (macro signals are inherently uncertain)
- **Typical failure mode:** Macro analysis has the longest time horizon and the weakest short-term predictive power
- **Regime sensitivity:** Most valuable during regime transitions; least valuable within a stable regime
- **Calibration ratio expectation:** 1.00-1.50 (biased toward underconfidence)

### Quantitative / ML Team
- **Expected calibration:** Can be either under- or overconfident depending on training data
- **Typical failure mode:** Overfitting to training data; performance degrades on out-of-distribution data
- **Regime sensitivity:** ML models trained on bull data fail in bears and vice versa
- **Calibration ratio expectation:** 0.75-1.25
- **If calibration ratio oscillates between extremes:** Model is not robust; needs retraining or ensembling

## 7.3 Diagnosing Overconfidence

**Symptoms:**
- High conviction scores (7-9) with win rates < 60%
- Conviction 8 trades have LOWER win rate than conviction 5 trades
- The team's "high conviction" signals are no better than random

**Common Causes:**
1. **Training on favorable regime:** ML model trained on bull market data assigns high confidence to bullish patterns that fail in bear markets
2. **Indicator confluence illusion:** Multiple correlated indicators (e.g., RSI and MACD) both giving the same signal creates an illusion of independent confirmation
3. **Anchoring to recent success:** A streak of wins inflates confidence on subsequent trades even when the statistical edge has not changed
4. **Regime blindness:** The team does not adjust confidence for regime, treating a bear market signal with the same confidence as a bull market signal

**Corrective Actions:**
1. Apply calibration ratio as a multiplier: `adjusted_confidence = raw_confidence * calibration_ratio`
2. Investigate which inputs are correlated and remove redundancy
3. Require regime-specific calibration: calibrate separately for bull, bear, ranging
4. If calibration does not improve within 30 days: consider prompt optimization or model change for the team

## 7.4 Diagnosing Underconfidence

**Symptoms:**
- Low conviction scores (4-6) with win rates > 60%
- The team is consistently right but assigns low confidence
- Position sizing is too small because of artificially low conviction

**Common Causes:**
1. **Excessive hedging of language:** The team's prompts or models are trained to be cautious
2. **Long time horizon signals:** On-chain and macro signals may be directionally correct but the team appropriately assigns low confidence because timing is uncertain
3. **Risk aversion bias:** After a period of losses, the team becomes systematically underconfident

**Corrective Actions:**
1. Apply calibration ratio > 1.0 to scale up the team's signals
2. If underconfidence is consistent across regimes: adjust the team's confidence output formula or prompt
3. If underconfidence is regime-specific (e.g., only underconfident in bull markets): apply regime-conditional calibration

## 7.5 Calibration Update Protocol

1. **Frequency:** Every 30 days (or after 50 trades, whichever comes first)
2. **Window:** Rolling 90-day lookback
3. **Minimum sample:** 30 trades at each conviction level for reliable calibration
4. **Method:**
   ```
   For each conviction level c in [4, 5, 6, 7, 8, 9, 10]:
     wins = count of winning trades with conviction c in the last 90 days
     total = count of all trades with conviction c in the last 90 days
     if total >= 10:  # minimum for any signal
       actual_wr = wins / total
       expected_wr = c / 10
       cal_ratio[c] = actual_wr / expected_wr
     else:
       cal_ratio[c] = 1.0  # insufficient data, use neutral
   ```
5. **Smoothing:** Apply exponential moving average with alpha = 0.3 to prevent sudden swings:
   ```
   smooth_cal_ratio = 0.3 * new_cal_ratio + 0.7 * prev_cal_ratio
   ```

---

# 8. Stop Loss & Exit Management

## 8.1 ATR-Based Stop Loss Methodology

### Why ATR-Based Stops Beat Fixed Stops

**Research evidence (study of 1,000 trades):**
- 2x ATR stop-loss reduced maximum drawdown by 32% vs fixed stop-loss
- 3x ATR multiplier boosted performance by 15% vs fixed stop-loss methods
- Crypto often requires higher ATR multiples due to extreme intraday moves (BTC daily range often 3-8%)

### Formulas

**Long position stop:**
```
stop_loss = entry_price - (ATR_14 * multiplier * stop_adj)
```

**Short position stop:**
```
stop_loss = entry_price + (ATR_14 * multiplier * stop_adj)
```

Where:
- `ATR_14` = 14-period Average True Range
- `multiplier` = tier-specific base multiplier (BTC: 2.0, Top5: 2.5, Large-cap: 3.0, Mid-cap: 3.5, Meme: 4.5)
- `stop_adj` = regime adjustment (BULL: 0.85, BEAR: 1.30, RANGING: 1.00, CRISIS: 1.30)

### Effective Stop Multipliers After Regime Adjustment

| Tier | BULL | BEAR | RANGING | CRISIS |
|------|------|------|---------|--------|
| BTC | 1.7x ATR | 2.6x ATR | 2.0x ATR | 2.6x ATR |
| Top5 | 2.125x ATR | 3.25x ATR | 2.5x ATR | 3.25x ATR |
| Large-cap | 2.55x ATR | 3.9x ATR | 3.0x ATR | 3.9x ATR |
| Mid-cap | 2.975x ATR | 4.55x ATR | 3.5x ATR | 4.55x ATR |
| Meme | 3.825x ATR | 5.85x ATR | 4.5x ATR | 5.85x ATR |

### Why Bear/Crisis Stops are WIDER, Not Tighter

Counterintuitive but correct: in bear markets and crises, stops should be WIDER because:
1. Volatility is higher -- tighter stops get triggered by normal noise
2. Bear market short squeezes can move 17%+ in 5 days (e.g., $63K to $74K)
3. Below 3% stop in crypto: essentially guaranteed stop-out from normal noise
4. The trade-off: wider stops with smaller position sizes maintain the same dollar risk per trade

**The math:**
- Bull: 1.7x ATR stop with 1.5% risk/trade
- Bear: 2.6x ATR stop with 0.5% risk/trade
- Dollar risk: same (portfolio * risk_pct), but the stop is wider and position is smaller

## 8.2 Optimal Multipliers by Trading Context

| Context | ATR Period | Multiplier Range | Notes |
|---|---|---|---|
| Day trading | 7-10 | 1.5-2.0x | Fast reaction to volatility spikes |
| Swing trading | 14 | 2.0-2.5x | Standard for most strategies |
| Position trading | 21-30 | 2.5-3.5x | Larger trends, more room to breathe |
| Crypto bear market | 7-14 | 2.5-3.0x+ | Higher multiplier for elevated volatility |
| Meme coin any regime | 14 | 4.0-6.0x | Extreme noise requires extreme accommodation |

### Crypto-Specific Stop Loss Ranges

| Width | Range | Pros | Cons |
|---|---|---|---|
| Tight | 3-5% | Preserves capital, higher R:R ratio | Stopped out by noise; bear market whipsaws |
| Medium | 5-8% | Balance of protection and room | Standard approach |
| Wide | 8-10%+ | Higher win rate, fewer false stops | Larger per-trade losses |
| Crypto minimum | 3% | Below this: guaranteed stop-out from normal noise | -- |
| Crypto maximum | 10% | Above 10%: recovery math becomes punishing (10% loss needs 11.1% gain) | -- |

## 8.3 Trailing Stop Analysis

### Chandelier Trailing Stop (Fund's Method)

The fund uses an ATR-based trailing stop (Chandelier exit):

```
trailing_stop = highest_high_since_entry - (ATR * trail_multiplier * stop_adj)
```

This stop ratchets up as price makes new highs but never moves down.

**Activation condition:** Trailing stop activates at 1.5R profit. Before 1.5R, the initial stop-loss remains in place.

**Trail multipliers by tier:**
| Tier | Trail ATR Multiplier | After Regime Adjustment (BULL) | After Regime Adjustment (BEAR) |
|---|---|---|---|
| BTC | 2.5x | 2.125x | 3.25x |
| Top5 | 3.0x | 2.55x | 3.9x |
| Large-cap | 3.5x | 2.975x | 4.55x |
| Mid-cap | 4.0x | 3.4x | 5.2x |
| Meme | 5.0x | 4.25x | 6.5x |

### When Trailing Stops Lock In Gains vs Cut Profits Short

**Trailing stops are beneficial when:**
- The market is trending (ADX > 25)
- Volatility is moderate and stable
- The trade has already achieved significant profit (> 2R)

**Trailing stops cut profits short when:**
- The market is volatile and choppy (large intraday swings)
- A sudden volatility spike (news event) triggers the trail on a temporary dip
- The trail is too tight for the asset's natural volatility

**How to detect if trails are too tight:**
- Calculate percentage of trail exits where price subsequently moved significantly higher (> 2% within 24h after exit)
- If this exceeds 30%, the trail is too tight
- Recommendation: increase trail ATR multiplier by 0.5

**How to detect if trails are too loose:**
- Calculate average trail efficiency (profit at exit / MFE)
- If trail efficiency < 40%, the trail is giving back too much of the move
- Recommendation: decrease trail ATR multiplier by 0.5

## 8.4 Take Profit Optimization

### TP1 Analysis Framework

**Is TP1 at the correct level?**

Method: For each tier, collect the distribution of actual maximum favorable excursion (MFE) for winning trades. Plot the cumulative distribution.

| Percentile of MFE Distribution | What It Tells You |
|---|---|
| TP1 R-multiple is at the 30th percentile | 70% of winning trades would exceed TP1 -- TP1 is conservative |
| TP1 R-multiple is at the 50th percentile | 50% of winning trades exceed TP1 -- well-balanced |
| TP1 R-multiple is at the 70th percentile | Only 30% of winning trades reach TP1 -- TP1 is aggressive |

**Ideal TP1 placement:** Between the 40th and 60th percentile of the winning trade MFE distribution. This ensures most winners hit TP1 while still capturing meaningful profit.

### TP2 Analysis Framework

**Is TP2 reachable?**

TP2 is inherently more aggressive. Expected hit rates (conditional on TP1 being hit):

| Tier | TP2 R-multiple | Expected Hit Rate | If Actual < Expected |
|---|---|---|---|
| BTC (BULL) | 4.0 * 1.40 = 5.6R | 30-40% | TP2 too aggressive for current vol |
| BTC (BEAR) | 4.0 * 0.80 = 3.2R | 25-35% | Bear targets are more realistic |
| Top5 (BULL) | 3.0 * 1.40 = 4.2R | 25-35% | -- |
| Meme (BULL) | 2.0 * 1.40 = 2.8R | 15-25% | Meme trends often reverse violently before TP2 |
| Meme (BEAR) | 2.0 * 0.80 = 1.6R | 10-15% | Very low hit rate; trail captures more effectively |

If TP2 hit rate is consistently below 10% for a tier: TP2 is essentially unreachable and the 33% of the position allocated to TP2 is being unnecessarily held. Consider:
1. Reducing TP2 R-multiple by 0.5-1.0R
2. OR reducing TP2 exit fraction from 33% to 20% and increasing trail fraction to 47%

## 8.5 Time Stop Analysis

### Do Positions That Hit Time Stops Tend to Be Winners or Losers?

**If mostly losers (P&L < 0):**
- The position thesis has already failed, but the price has not moved enough to trigger the stop-loss
- These are "dead money" trades -- capital locked up producing nothing
- Consider SHORTENING the time stop to free capital faster
- The signal may have been correct directionally but the market is not cooperating

**If mixed (roughly 50/50):**
- Time stop is functioning as intended -- it is cleaning up positions that have neither confirmed nor invalidated their thesis
- No change needed

**If mostly winners (P&L > 0):**
- Time stop is CUTTING WINNERS
- The trade thesis was correct but needed more time to fully develop
- Consider LENGTHENING the time stop
- This is especially common with on-chain and macro signals, which have longer time horizons

### Time Stop Interaction with Regime

| Regime | Time Adjustment | Effective BTC Time Stop | Rationale |
|---|---|---|---|
| BULL | 1.25x | 450 hours (18.75 days) | Trends persist; give trades room |
| BEAR | 0.75x | 270 hours (11.25 days) | Faster alpha decay; cut quickly |
| RANGING | 1.0x | 360 hours (15 days) | Standard |
| CRISIS | 0.50x | 180 hours (7.5 days) | Extreme urgency; minimal exposure time |

---

# 9. Institutional Benchmarks

## 9.1 Bridgewater Associates (All Weather / Risk Parity)

| Parameter | Value |
|---|---|
| Portfolio volatility target | 10-12% annualized |
| Leverage | ~1.8x via futures |
| Risk allocation | Equal risk contribution per asset class |
| Rebalancing | Dynamic -- scale inversely to volatility |
| Philosophy | No regime prediction; balance across all environments |
| AUM | ~$150B+ |

### Key Lessons for Syndicate
1. **Volatility targeting works:** Bridgewater's approach of targeting a fixed portfolio volatility (10-12%) and adjusting leverage/sizing to achieve it has produced consistent long-term returns.
2. **Risk parity > capital parity:** Allocating by risk contribution (so each asset contributes equal volatility) outperforms allocating by dollar amount.
3. **Do not predict regimes; be prepared for all:** All Weather does not try to predict bull/bear; it is designed to perform adequately in all environments. Syndicate's regime detection is more aggressive but should maintain a baseline minimum performance in all regimes.

## 9.2 Renaissance Technologies (Medallion Fund)

| Parameter | Value |
|---|---|
| Annualized return (before fees) | ~66% |
| Position sizing method | Kelly criterion-based, precisely calibrated per trade probability |
| Number of daily trades | ~300,000 |
| Average position size | ~$100K per trade (at $10B AUM) |
| Holding period | Very short (intraday to days) |
| Fund cap | $10-15B (employees only) |
| Diversification | Thousands of uncorrelated bets |
| Market exposure | Market-neutral (long/short pairs, eliminate beta) |
| Risk monitoring | Continuous real-time; evolving vol and correlation estimates |
| Estimated Sharpe ratio | > 2.0 |

### Key Lessons for Syndicate
1. **Kelly sizing with calibration is the gold standard:** Renaissance famously uses Kelly criterion with precise probability estimates. The quality of the probability estimate is more important than the sizing formula.
2. **Volume of uncorrelated bets:** 300K trades/day across thousands of instruments. Syndicate trades far fewer times, so each bet must be higher quality.
3. **Capacity constraint as risk management:** Medallion caps at $10-15B and returns capital to investors because strategy capacity is finite. This implies that Syndicate should be aware of its own capacity constraints (liquidity limits in crypto markets).

## 9.3 Multi-Manager Hedge Funds (Millennium, Citadel, Point72)

| Parameter | Threshold | Consequence |
|---|---|---|
| PM flagged | 1.5% drawdown | Head of risk asks basic questions |
| PM formal review | 2.5% drawdown | Documented meeting to justify positions |
| PM allocation halved | 5% drawdown | Automatic reduction of capital |
| PM terminated | 8-10% drawdown | PM fired (Millennium: 10%) |
| Total fund max drawdown | 2.5-5% | Varies by firm |

### Key Lessons for Syndicate
1. **Drawdown limits are non-negotiable:** At Millennium, 5% drawdown = halved, 10% = fired. These are hard limits, not guidelines. Syndicate's crisis circuit breakers (2% DD = cut, 5% DD = halt) are in line with institutional standards.
2. **Scaling risk inversely to drawdown:** The multi-manager model automatically reduces risk as losses accumulate. This is the correct approach: a fund that has lost 5% should NOT trade the same size as one at equity highs.
3. **Mid-single-digit daily loss = immediate action:** At multi-managers, a 3-5% daily loss triggers immediate allocation reduction and conversation with risk committee. Syndicate's daily loss limits (1% crisis, 2% bear, 3% bull) are appropriate.

## 9.4 Systematic Trend-Following Benchmarks (CTAs)

From Concretum Group analysis (40 futures markets, 1980-2024):

| Method | IRR p.a. | Max Drawdown | Hit Ratio (trade) | Hit Ratio (monthly) |
|---|---|---|---|---|
| Volatility Targeting (VT) | 11.46% | 25.65% | 42.5% | 60% |
| Volatility Parity (VP) | 12.83% | ~25% | 42.4% | 59% |
| VP + Pyramiding | 20.00% | 48.69% | 39.3% | 56% |

**Key parameter:** 0.10% daily volatility contribution per trade (= $100K risk per $100M portfolio per day).

### Lessons for Syndicate
1. **40-45% win rate is normal for trend following.** If Syndicate's trend-following win rate is in this range, it is performing as expected. The edge comes from the size of winners, not the frequency.
2. **Pyramiding (adding to winners) dramatically increases returns but nearly doubles max drawdown.** Syndicate should consider pyramiding with extreme caution, only for highest-conviction signals in bull regime.
3. **Monthly hit rate of 56-60%** means 4-5 months out of every 10 are profitable. Nearly half the months lose money. This is psychologically challenging but mathematically sound.

## 9.5 Crypto-Specific Benchmarks

### Bluesky Capital L/S Crypto Strategy

| Metric | Value |
|---|---|
| Mean annual return | 224% |
| BTC buy-and-hold comparison | 108% |
| Sharpe ratio | 1.96 |
| BTC buy-and-hold Sharpe | 1.18 |
| BTC max drawdown | 84% |
| Strategy max drawdown | Significantly less (not published) |
| Universe | Top 14 cryptocurrencies |

### Combined Momentum + Mean Reversion (QuantPedia)
| Metric | Value |
|---|---|
| Sharpe ratio | 1.71 |
| Annualized return | 56% |
| T-statistic | 4.07 |

### AdaptiveTrend (2022-2024 Backtest)
| Metric | Value |
|---|---|
| Sharpe ratio | 2.41 |
| Long/Short allocation | 70/30 |
| Max drawdown | -12.7% |
| Maintained through bear cycle | Yes |

### Pythagoras Funds (2022)
| Metric | Value |
|---|---|
| 2022 return | +8% |
| During BTC -65% | Market-neutral strategies |
| Fund of funds gross return since 2018 | 870% |

## 9.6 Performance Targets for Syndicate

Based on institutional benchmarks, Syndicate should target:

| Metric | Target | Stretch | Red Flag |
|---|---|---|---|
| Sharpe ratio (annualized) | > 1.5 | > 2.0 | < 1.0 |
| Win rate (trend following) | 40-50% | > 50% | < 35% |
| Win rate (combined strategies) | 50-60% | > 60% | < 45% |
| Max drawdown | < 15% | < 10% | > 20% |
| Daily loss limit adherence | 100% | -- | Any breach |
| Conviction calibration ratio | 0.8-1.2 | 0.9-1.1 | < 0.6 or > 1.5 |

---

# 10. Hypothesis Testing Framework

## 10.1 How to Structure a Hypothesis

Every hypothesis test must follow this format:

```
HYPOTHESIS: If we change [PARAMETER] from [CURRENT_VALUE] to [PROPOSED_VALUE],
we expect [METRIC] to improve by [AMOUNT] because [REASONING].

EVIDENCE REQUIRED:
- Minimum sample size: [N]
- Test type: [type]
- Significance level: p < [threshold]
- In-sample period: [dates]
- Out-of-sample period: [dates]
```

### Example Hypothesis

```
HYPOTHESIS: If we change the bear market stop ATR multiplier for BTC from 2.6x
(2.0 * 1.30) to 3.0x (2.0 * 1.50), we expect the stop-loss hit rate to decrease
from 45% to 30% because current stops are being triggered by normal bear market
volatility, not genuine signal failure.

EVIDENCE REQUIRED:
- Minimum sample size: 50 BTC trades in bear regime
- Test type: Two-proportion z-test (SL hit rate before vs after)
- Significance level: p < 0.05
- In-sample period: Jan 2022 - Jun 2022 (bear market)
- Out-of-sample period: Jul 2022 - Dec 2022 (continued bear)
```

## 10.2 Required Evidence Standards

### Minimum Sample Sizes

| Type of Test | Minimum n | Preferred n | Notes |
|---|---|---|---|
| Win rate comparison | 30 per group | 100 per group | Below 30 is too unreliable |
| Mean return comparison | 50 per group | 200 per group | Fat tails in crypto require larger samples |
| Sharpe ratio comparison | 100 per group | 252+ per group (1 year of daily returns) | Sharpe estimates are noisy with small samples |
| Calibration analysis | 10 per conviction level | 30 per conviction level | Below 10 is insufficient for any conclusion |
| Parameter sensitivity | 50 per parameter setting | 200 per setting | Need enough to see the response curve |

### In-Sample and Out-of-Sample Requirements

Every hypothesis test MUST include both in-sample and out-of-sample results:

1. **In-sample:** The period used to develop or calibrate the hypothesis
2. **Out-of-sample:** A separate, non-overlapping period used to validate
3. **Minimum OOS requirement:** At least 30% of the total data must be reserved for out-of-sample testing
4. **Walk-forward preferred:** Ideally, use walk-forward optimization where the model is re-fit periodically on expanding windows

### Regime-Stratified Testing

A change must be evaluated in multiple regimes:

| Regime | Required? | Rationale |
|---|---|---|
| BULL | Yes | Most data typically available; baseline performance |
| BEAR | Yes | Critical regime; must not degrade performance |
| RANGING | If available | Important but may have limited data |
| CRISIS | If available | Small sample; test directionally, do not demand significance |

## 10.3 Statistical Significance

### Thresholds

| Level | p-value | When to Use |
|---|---|---|
| Suggestive | p < 0.10 | Preliminary evidence; needs more data |
| Significant | p < 0.05 | Standard threshold for strategy changes |
| Highly significant | p < 0.01 | Preferred for major parameter changes |
| Very highly significant | p < 0.001 | Required for fundamental architecture changes |

### Common Tests

| Question | Test | Notes |
|---|---|---|
| Is win rate A different from win rate B? | Two-proportion z-test | Most common for A/B comparisons |
| Is mean return A different from mean return B? | Welch's t-test (unequal variances) | Use Welch's because crypto returns have heterogeneous variance |
| Is Sharpe A different from Sharpe B? | Ledoit-Wolf or Jobson-Korkie test | Standard Sharpe comparison tests |
| Is the distribution of returns different? | Kolmogorov-Smirnov test | Useful when shapes differ, not just means |
| Are these results due to multiple testing? | Bonferroni correction | If testing 10 parameters, use p < 0.005 instead of p < 0.05 |

### Multiple Testing Correction

When testing multiple hypotheses simultaneously (e.g., testing 5 different stop multipliers), apply Bonferroni correction:

```
adjusted_significance = base_significance / number_of_tests

Example: testing 5 multipliers at p < 0.05
Adjusted threshold: 0.05 / 5 = p < 0.01 per test
```

This prevents false discovery from running many tests and cherry-picking the best one.

## 10.4 Practical Significance

Statistical significance is necessary but not sufficient. A statistically significant improvement of 0.1% in win rate is not worth the implementation risk of changing parameters.

### Practical Significance Thresholds

| Metric | Minimum Meaningful Improvement | Notes |
|---|---|---|
| Win rate | +5 percentage points | e.g., 42% to 47% |
| Sharpe ratio | +0.3 | e.g., 1.2 to 1.5 |
| Max drawdown reduction | -3 percentage points | e.g., 15% to 12% |
| Stop-loss hit rate | -10 percentage points | e.g., 45% to 35% |
| Average R-multiple per trade | +0.1R | e.g., 0.3R to 0.4R |
| Annualized return | +10 percentage points | e.g., 30% to 40% |

### Implementation Risk Assessment

Every proposed change has an implementation risk:

| Risk Level | Description | Mitigation |
|---|---|---|
| Low | Parameter change (e.g., ATR multiplier from 2.0 to 2.5) | A/B test for 2 weeks, then deploy |
| Medium | Logic change (e.g., adding a new exit condition) | Paper trade for 4 weeks, then small-size deploy |
| High | Architecture change (e.g., new signal aggregation method) | Full backtest, paper trade for 8+ weeks, staged rollout |

## 10.5 Decision Matrix

### DEPLOY: Recommended for Immediate Implementation

Requirements (ALL must be met):
- Statistically significant (p < 0.05)
- Practically significant (exceeds minimum improvement thresholds above)
- Positive in both bull AND bear regime backtests
- Out-of-sample performance within 80% of in-sample
- No degradation in max drawdown

### REJECT: Not Recommended

Any of these is sufficient to reject:
- Negative Sharpe ratio in any regime
- Not statistically significant (p >= 0.10)
- Only works in one regime and degrades performance in others
- Out-of-sample performance < 50% of in-sample (overfitting)
- Increases max drawdown by more than 3 percentage points

### NEEDS MORE DATA: Promising but Insufficient Evidence

- Trending toward significance (0.05 < p < 0.10)
- Sample size below minimum (n < 30 per group)
- Only tested in one regime
- Results are promising but noisy
- Action: specify exactly what additional data is needed and how long it will take to collect

### MODIFY AND RETEST: Promising Direction, Wrong Specifics

- The directional idea is sound but specific parameters need tuning
- Example: "Widening bear market stops is correct, but 3.5x ATR is too wide; test 2.8x and 3.0x"
- Provide specific modified parameters and re-run criteria
- Set a deadline for the retest (typically 2-4 weeks)

## 10.6 Effect Size Calculations

### Cohen's d for Return Comparisons

```
d = (mean_A - mean_B) / pooled_std

where:
  pooled_std = sqrt((std_A^2 + std_B^2) / 2)
```

| Cohen's d | Interpretation |
|---|---|
| < 0.2 | Negligible effect |
| 0.2 - 0.5 | Small effect |
| 0.5 - 0.8 | Medium effect |
| > 0.8 | Large effect |

For Syndicate, a minimum Cohen's d of 0.3 (small-to-medium effect) is required for parameter changes. Anything below 0.2 is noise, not signal.

### Power Analysis

Before running a test, calculate the required sample size:

```
n = (Z_alpha + Z_beta)^2 * 2 * sigma^2 / delta^2

where:
  Z_alpha = 1.96 (for p < 0.05, two-tailed)
  Z_beta = 0.84 (for 80% power)
  sigma = estimated standard deviation of the metric
  delta = minimum meaningful difference to detect
```

**Example:** To detect a 5 percentage point difference in win rate (45% vs 50%) with 80% power:
```
n = (1.96 + 0.84)^2 * 2 * (0.50 * 0.50) / 0.05^2
n = 7.84 * 0.50 / 0.0025
n = 1,568 per group
```

This is a LOT of trades. In practice, with the fund's trading frequency, detecting a 5pp win rate difference with high confidence may take months. This is why practical significance thresholds exist: we cannot wait for statistical perfection.

## 10.7 Backtest Integrity Checks

### Common Backtest Pitfalls to Detect

| Pitfall | Detection Method | Red Flag |
|---|---|---|
| Look-ahead bias | Check if any future data is used in signal generation | Any use of future close prices, volume, etc. |
| Survivorship bias | Verify delisted tokens are included in the backtest universe | Only currently-live tokens in the universe |
| Slippage/fill assumption | Check if trades are filled at signal price or with realistic slippage | Zero slippage assumption for illiquid assets |
| Overfitting | Compare IS vs OOS performance | OOS performance < 50% of IS |
| Data snooping | Check how many parameters were tuned on the same dataset | > 5 parameters tuned without adjustment |
| Selection bias | Check if only the best-performing parameter was reported | Multiple tests run but only best reported |

### Required Backtest Report Elements

Every hypothesis test backtest must report:

1. Total number of trades (in-sample and out-of-sample)
2. Win rate (with 95% confidence interval)
3. Average R-multiple per trade
4. Sharpe ratio (annualized)
5. Maximum drawdown
6. Profit factor (gross profit / gross loss)
7. Average holding period
8. Best trade and worst trade (to check for outlier dependency)
9. Percentage of total profit from the best trade (if > 30%, results are fragile)
10. Performance by regime (if data permits)

---

# 11. Report Writing Guidelines

## 11.1 Structure of Every Report

### Trade Attribution Report Template

```
## Trade Attribution Report: [Period]

### Executive Summary
[2-3 sentences: headline finding, most actionable insight, bottom-line P&L]

### Key Metrics This Period
| Metric | Value | vs Benchmark | Trend |
|--------|-------|-------------|-------|
[Fill in]

### Attribution by [Primary Dimension]
[The dimension that reveals the most important pattern]

### Attribution by [Secondary Dimension]
[Supporting analysis]

### Anomalies Detected
[Any patterns that deviate from expectations by more than 2 standard deviations]

### Specific Recommendations
1. [Actionable change with specific parameter values]
2. [Another actionable change]

### Data Gaps
[What additional data would improve this analysis?]
```

### Hypothesis Testing Report Template

```
## Hypothesis Test: [Short Title]

### Hypothesis Statement
If we change [X] from [A] to [B], we expect [Y] to improve by [Z%].

### Test Design
- Sample size: [n]
- In-sample period: [dates]
- Out-of-sample period: [dates]
- Statistical test: [test name]
- Significance level: p < [threshold]

### Results Summary
| Metric | Current | Proposed | Change | p-value |
|--------|---------|----------|--------|---------|
[Fill in]

### Regime-Specific Results
| Regime | Current | Proposed | Change | n |
|--------|---------|----------|--------|---|
[Fill in]

### Recommendation: [DEPLOY / REJECT / NEEDS MORE DATA / MODIFY AND RETEST]

### Rationale
[3-5 sentences explaining the recommendation]

### If Deployed: Expected Impact
[Quantified expected improvement on fund performance]

### If Rejected: Why
[Specific reason with data]
```

## 11.2 Writing Rules

### Lead with the Most Actionable Finding

Bad: "We analyzed 342 trades across 4 regimes and 5 tiers..."
Good: "BTC stop losses in bear regime are too tight: 48% SL hit rate vs 30% expected. Widening from 2.6x to 3.0x ATR would have saved 4.2% of fund NAV last month."

### Every Recommendation Must Be Specific

Bad: "Consider widening stops in bear markets."
Good: "Reduce bear market stop_adj from 1.30 to 1.50 for BTC tier, changing effective stop from 2.6x ATR to 3.0x ATR."

### Quantify Expected Impact

Bad: "This should improve performance."
Good: "This would have reduced SL hit rate from 48% to 31% in the last 30 days, saving approximately $42,000 (0.42% of NAV) based on 23 BTC trades that hit stop loss."

### Reference Specific Trades and Dates

Bad: "Several trades were stopped out prematurely."
Good: "Trades #1247 (BTC long, 2026-02-14), #1253 (BTC long, 2026-02-17), and #1261 (BTC long, 2026-02-22) were all stopped out at 2.6x ATR before subsequently recovering. All three would have been profitable with a 3.0x ATR stop."

### End with Clear Do/Don't Summary

```
DO:
- Widen BTC bear market stops from 2.6x to 3.0x ATR
- Reduce meme coin time stop from 48h to 36h
- Increase weight on macro team signals (calibration ratio 1.35)

DO NOT:
- Change bull market parameters (they are performing well)
- Trade meme coins in crisis regime (insufficient edge)
- Reduce position sizing further (already at minimum effective levels)
```

### When Data Is Insufficient

Be explicit about what data is needed:

Bad: "More data is needed."
Good: "Insufficient data to evaluate mid-cap performance in crisis regime. Only 3 mid-cap trades occurred during the last crisis period (Nov 2025). Need minimum 30 trades. At current trading frequency, this will require approximately 6 months of crisis-regime trading data. In the meantime, use bear-regime parameters for mid-caps during crisis as a conservative default."

## 11.3 Numbers and Formatting Standards

### Precision Rules

| Metric | Precision | Example |
|---|---|---|
| Win rate | 1 decimal place | 42.3% |
| Sharpe ratio | 2 decimal places | 1.47 |
| P&L (absolute) | Nearest dollar | $42,317 |
| P&L (relative) | 2 decimal places | 4.23% |
| R-multiples | 1 decimal place | 2.3R |
| ATR multipliers | 1-2 decimal places | 2.6x or 2.65x |
| p-values | Up to 4 decimal places | p = 0.0234 |
| Sample sizes | Integer | n = 147 |

### Confidence Intervals

Always report confidence intervals for key metrics:

```
Win rate: 42.3% (95% CI: 37.1% - 47.5%, n = 214)
Sharpe ratio: 1.47 (95% CI: 0.89 - 2.05, n = 252 daily returns)
```

### Comparison Format

When comparing two approaches:

```
| Metric | Current (A) | Proposed (B) | Delta | Significant? |
|--------|-------------|-------------|-------|-------------|
| Win rate | 42.3% | 47.8% | +5.5pp | Yes (p=0.028) |
| Sharpe | 1.22 | 1.58 | +0.36 | Yes (p=0.041) |
| Max DD | -18.2% | -15.1% | +3.1pp | No (p=0.13) |
```

## 11.4 Common Attribution Patterns and What They Mean

### Pattern: High Win Rate but Low Total Return
- **Diagnosis:** Taking profits too early. TP1 is hit frequently but TP2 and trailing stop are not generating large wins.
- **Action:** Consider raising TP1 R-multiple or reducing TP1 exit fraction from 33% to 25%.

### Pattern: Low Win Rate but High Total Return
- **Diagnosis:** Classic trend-following profile. Few winners but they are large.
- **Action:** This is actually healthy for trend-following. Verify that the average winner is > 2x the average loser.

### Pattern: Profitable in Bull, Devastating in Bear
- **Diagnosis:** Strategy has no bear market hedge. Likely over-reliant on long-side trend following.
- **Action:** Verify regime detection is switching parameters correctly. Check that L/S ratio inverts in bear. Consider adding explicit short-side signals.

### Pattern: Stop Losses Clustered at Exact ATR Multiple
- **Diagnosis:** Market makers may be targeting the fund's stop level.
- **Action:** Add randomization to stop placement: `stop = entry - ATR * multiplier * uniform(0.90, 1.10)`.

### Pattern: Time Stops All Occurring at Max Hours
- **Diagnosis:** Positions are routinely reaching the maximum holding period without resolution.
- **Action:** Either the time stop is too long (positions are dead money) or signals are not generating enough movement. Check alpha decay curves.

### Pattern: Meme Coin Trades Dominating P&L Variance
- **Diagnosis:** Despite small position sizes, extreme meme volatility is driving fund-level outcomes.
- **Action:** Reduce meme trading frequency or tighten meme risk limits further. Verify that meme trades are not being opened in clusters (multiple meme positions simultaneously = hidden concentration risk).

### Pattern: High Conviction Trades Underperforming Low Conviction
- **Diagnosis:** Critical calibration failure. The aggregation pipeline is assigning high confidence to weak signals.
- **Action:** Immediate investigation. Disaggregate by team. Apply calibration ratio correction. Consider temporary halt of trading until calibration is fixed.

### Pattern: Excellent Performance on 1 Asset, Poor on All Others
- **Diagnosis:** The strategy may be overfit to the characteristics of one asset (usually BTC).
- **Action:** Check if signal generation is using asset-specific parameters that do not generalize. Consider asset-specific parameter tuning rather than universal parameters.

---

# Appendix A: Quick Reference Formulas

## Position Sizing

```
# Kelly Criterion
kelly_fraction = win_prob - (1 - win_prob) / reward_risk_ratio

# ATR-based Position Size
position_size = (portfolio * risk_pct) / (ATR * stop_multiplier * stop_adj)

# Volatility Parity
position_size = target_vol / (asset_vol * sqrt(num_positions))

# Full Combined Sizing
final_size = min(tier_max, base * kelly_frac * cal_ratio * regime_factor)
```

## Risk Metrics

```
# Sharpe Ratio
sharpe = (mean_return - risk_free_rate) / std_return * sqrt(252)

# Sortino Ratio (only penalizes downside vol)
sortino = (mean_return - target_return) / downside_std * sqrt(252)

# Maximum Drawdown
max_dd = max((peak - trough) / peak) over all peaks and troughs

# Profit Factor
profit_factor = gross_profit / gross_loss

# Expectancy per Trade
expectancy = (win_rate * avg_win) - (loss_rate * avg_loss)

# R-Multiple
r_multiple = trade_pnl / initial_risk_amount
```

## Statistical Tests

```
# Two-Proportion Z-Test (win rate comparison)
z = (p1 - p2) / sqrt(p_pooled * (1 - p_pooled) * (1/n1 + 1/n2))
p_pooled = (x1 + x2) / (n1 + n2)

# Welch's t-test (mean comparison with unequal variance)
t = (mean1 - mean2) / sqrt(var1/n1 + var2/n2)
df = (var1/n1 + var2/n2)^2 / ((var1/n1)^2/(n1-1) + (var2/n2)^2/(n2-1))

# Cohen's d (effect size)
d = (mean1 - mean2) / sqrt((std1^2 + std2^2) / 2)

# Calibration Ratio
cal_ratio = actual_win_rate / expected_win_rate
expected_win_rate = conviction_score / 10
```

## Regime-Adjusted Parameters

```
# Stop Loss
adjusted_stop = base_atr_mult * stop_adj[regime]

# Take Profit
adjusted_tp1 = base_tp1_rmult * tp_adj_1[regime]
adjusted_tp2 = base_tp2_rmult * tp_adj_2[regime]

# Time Stop
adjusted_time = base_max_hours * time_adj[regime]

# Position Size
adjusted_size = base_size * regime_factor[regime] * kelly_fraction[regime] * cal_ratio
```

---

# Appendix B: Red Flag Checklist

Use this checklist when reviewing any period's performance:

| # | Check | Threshold | Status |
|---|---|---|---|
| 1 | Overall win rate within expected range for current regime? | Bull: 40-55%, Bear: 35-50%, Ranging: 50-65% | |
| 2 | Conviction calibration monotonically increasing? | Conviction N+1 win rate > conviction N win rate | |
| 3 | No single trade > 5% of period P&L? | Best trade P&L / total P&L < 5% | |
| 4 | Stop-loss hit rate within tier benchmarks? | See Section 3.3 exit distribution table | |
| 5 | No regime misclassification detected? | Cross-reference with ADX, 200-MA, vol | |
| 6 | Long/Short ratio appropriate for regime? | Bull: 70:30+, Bear: 30:70+ | |
| 7 | Meme trades < 20% of total P&L variance? | Meme P&L contribution < 20% | |
| 8 | Daily loss limit never breached? | Zero breaches | |
| 9 | Max drawdown within regime limits? | Bull: <5%, Bear: <3%, Crisis: <2% | |
| 10 | Average holding period within tier time stops? | No systematic time-stop clustering | |
| 11 | Trail efficiency in acceptable range? | 50-85% depending on regime | |
| 12 | TP2 hit rate within expected range per tier? | See Section 3.3 | |
| 13 | Short-side funding costs accounted for? | Funding costs deducted from short P&L | |
| 14 | No single team dominating signal generation? | No team > 40% of conviction contribution | |
| 15 | Calibration ratios within 0.7-1.3 for all teams? | Check per-team calibration | |

---

# Appendix C: Historical Reference Tables

## BTC Annualized Volatility by Period

| Period | Annualized Vol | Context |
|---|---|---|
| 2017 (bull peak) | ~120% | Parabolic rally |
| 2018 (bear) | ~90% | Extended decline |
| 2019 (ranging) | ~70% | Recovery year |
| 2020 (COVID + bull) | ~80% | V-shaped recovery |
| 2021 (bull peak) | ~95% | Double-top year |
| 2022 (bear) | ~75% | Steady decline, liquidation events |
| 2023 (recovery) | ~50% | Institutional accumulation |
| 2024 (bull) | ~65% | ETF-driven rally |
| 2025 H1 (bull peak) | ~85% | ATH then correction |
| 2025 H2-2026 (bear) | ~95% | Ongoing decline |
| Average across all periods | ~91.73% | Very high by any asset class standard |

## BTC Statistical Properties

| Property | Value | Implication |
|---|---|---|
| Average annualized volatility | 91.73% | ~5x equity market volatility |
| Daily return range | -38.27% to +40.04% | Extreme tails |
| Kurtosis | 10.85 | Fat tails (normal = 3.0) |
| Crypto basket kurtosis | 27 | Even fatter tails for altcoins |
| Average correlation among top 14 cryptos | 0.56 (normal) | Rises to 0.7+ in bear markets |
| BTC-S&P 500 correlation (recent) | 0.91 | Macro matters; crypto is not uncorrelated to TradFi |

## Recovery Time by Drawdown Depth

| Drawdown | Historical Recovery Time (BTC) | At 15% Annual Return | At 30% Annual Return |
|---|---|---|---|
| -20% | 2-4 months | 1.5 years | 9 months |
| -30% | 4-8 months | 2.3 years | 1.2 years |
| -40% | 6-12 months | 3.5 years | 1.8 years |
| -50% | 9-18 months | 4.7 years | 2.4 years |
| -60% | 12-24 months | 6.1 years | 3.2 years |
| -70% | 18-36 months | 8.1 years | 4.2 years |
| -80% | 24-36 months | 10.7 years | 5.6 years |
| -90% | 24-36 months | 15.3 years | 7.8 years |

This table makes viscerally clear why drawdown prevention is paramount. A 50% drawdown at 15% annual recovery rate takes nearly 5 years to recover from. The fund simply cannot afford drawdowns beyond 15-20%.

---

# Appendix D: Glossary

| Term | Definition |
|---|---|
| ATR | Average True Range -- measure of volatility over N periods |
| Calibration Ratio | actual_win_rate / expected_win_rate for a given conviction level |
| Chandelier Exit | Trailing stop based on ATR distance from highest high |
| Cohen's d | Standardized effect size measure |
| Condorcet Jury Theorem | Mathematical proof that majority vote accuracy increases with independent voters |
| Conviction Score | 1-10 scale derived from Bayesian aggregation of team signals |
| DCA | Dollar-Cost Averaging |
| F&G | Fear & Greed Index (0-100, higher = more greedy) |
| Kelly Criterion | Optimal bet sizing formula: f = p - (1-p)/b |
| Log-Odds | log(p / (1-p)); used for Bayesian signal aggregation |
| MFE | Maximum Favorable Excursion -- best price reached during a trade |
| MAE | Maximum Adverse Excursion -- worst price reached during a trade |
| R-Multiple | Trade P&L divided by initial risk amount; 2R = profit was 2x the risk |
| Regime | Market condition classification: BULL, BEAR, RANGING, CRISIS |
| Sharpe Ratio | Risk-adjusted return: (mean return - risk-free) / std dev |
| Sortino Ratio | Like Sharpe but only penalizes downside volatility |
| stop_adj | Regime-specific multiplier applied to base stop ATR |
| tp_adj | Regime-specific multiplier applied to base take-profit R-multiples |
| time_adj | Regime-specific multiplier applied to base maximum holding hours |
| Trail Efficiency | profit_at_exit / MFE; how much of the move was captured |
| VaR | Value at Risk -- portfolio-level risk quantification at a confidence level |
| Volatility Parity | Position sizing method ensuring equal volatility contribution per asset |
| Walk-Forward | Backtest method where model is re-fit on expanding windows |

---

*End of Dr. Noor Hadid Strategy Researcher Knowledge Base*
*Syndicate Autonomous AI Crypto Hedge Fund*
*Version 1.0 -- March 2026*
