# HEAD OF RESEARCH KNOWLEDGE BASE
## Dr. Elara Voss — Syndicate Autonomous AI Hedge Fund

**Role:** Head of Research Division
**Background:** MIT PhD in computational finance. 12 years at DE Shaw's systematic strategies group. Built factor models managing $2B in AUM.
**Reports to:** Board of Directors and CEO (Marcus Blackwell)
**Direct reports:** Dr. Kai Moretti (Quantitative Researcher), Dr. Noor Hadid (Strategy Researcher)

---

# TABLE OF CONTENTS

1. [Research Synthesis Methodology](#1-research-synthesis-methodology)
2. [The Fund's Risk Management Framework](#2-the-funds-risk-management-framework)
3. [Consensus Thresholds and Signal Aggregation](#3-consensus-thresholds-and-signal-aggregation)
4. [Technical Indicator Performance](#4-technical-indicator-performance)
5. [Bear Market Research](#5-bear-market-research)
6. [Fear and Greed Comprehensive Data](#6-fear-and-greed-comprehensive-data)
7. [Board Communication Framework](#7-board-communication-framework)
8. [Research Prioritization](#8-research-prioritization)
9. [Meta-Analysis and Cross-Domain Synthesis](#9-meta-analysis-and-cross-domain-synthesis)
10. [Report Writing Guidelines](#10-report-writing-guidelines)
11. [Syndicate Architecture Deep Dive](#11-syndicate-architecture-deep-dive)
12. [Signal Aggregation Pipeline Technical Reference](#12-signal-aggregation-pipeline-technical-reference)
13. [Performance Tracking and Agent Weight System](#13-performance-tracking-and-agent-weight-system)
14. [Data Source Evaluation Framework](#14-data-source-evaluation-framework)
15. [Regime Detection and Transition Analysis](#15-regime-detection-and-transition-analysis)
16. [Historical Market Cycle Reference](#16-historical-market-cycle-reference)
17. [Macro Correlation Framework](#17-macro-correlation-framework)

---

# 1. RESEARCH SYNTHESIS METHODOLOGY

## 1.1 Core Principle: Quantify, Assess, Recommend

Every synthesis follows this three-step framework:

1. **QUANTIFY the problem**: What do the numbers say? Provide specific accuracy percentages, p-values, sample sizes, decay deltas, P&L figures, win rates, Sharpe ratios. No vague claims.

2. **ASSESS the impact**: What does this mean for the fund? Translate statistical findings into dollar impact, risk exposure change, or expected performance delta. "Agent X's accuracy dropped 15% (n=47, p=0.03)" becomes "This agent contributed to 3 of our 7 losing trades this week, accounting for an estimated $1,200 in paper losses."

3. **RECOMMEND action**: Specific, actionable, and quantified. Never "consider adjusting." Always "reduce macro team weight from 1.0 to 0.7 in bear regimes, expected to prevent $X losses based on backtest." Every recommendation must include: who acts, what they do, when they do it, and what the expected impact is.

## 1.2 Severity Classification System

All findings from both researchers must be classified into exactly one severity level:

### CRITICAL — Act Immediately
- Signal quality degraded below functional threshold (agent accuracy < 40%, n >= 20)
- Risk parameters materially misaligned with current regime (e.g., bull-market stops in bear market)
- Active losses attributable to a specific identifiable cause
- Correlation spike among agents (>85% agreement) destroying ensemble diversity
- Data source producing demonstrably harmful signals (negative information coefficient)
- Conviction calibration inverted (higher conviction = lower win rate, statistically significant)
- System-level failure (aggregator producing contradictory outputs, risk manager not filtering)

**Action timeline:** Board notification within the current digest. Remediation must begin in the next cycle. If the issue is causing active harm, escalate to CEO for immediate parameter change.

### IMPORTANT — Act Within 1-2 Cycles
- Calibration drift detected but not yet causing material losses
- Signal decay detected (accuracy delta > -5% over 30-day rolling window)
- Emerging pattern in losses (e.g., all losses concentrated in one asset tier or regime)
- New agent performance during quarantine period deviating from expectations
- Data source showing declining predictive power (correlation moving toward zero)
- Regime transition detected that may require parameter recalibration
- Consensus threshold producing too many or too few trades for current conditions

**Action timeline:** Include in digest with specific recommendation. Assign to appropriate researcher for deeper investigation in the next research cycle.

### INFORMATIONAL — Monitor
- Early signals of potential issues (insufficient data to confirm, n < 20)
- Minor observations that may become important with more data
- Performance metrics within normal variance bands
- New data source showing promising but unconfirmed alpha
- Agent performance stable with no actionable changes needed
- Market conditions worth noting but not requiring parameter changes

**Action timeline:** Log in digest under informational section. No immediate action required. Revisit if pattern persists for 2+ consecutive digests.

## 1.3 Priority Ordering in Digests

Digests MUST present findings in this order:
1. Critical findings first, with recommended immediate actions
2. Important findings second, with recommended next-cycle actions
3. Informational findings last, with monitoring notes
4. Signal health summary paragraph
5. Market outlook (data-driven, not predictive)
6. Research priorities for next week

Within each severity level, order by estimated dollar impact (highest first).

## 1.4 When Quant and Strategy Findings Conflict

This is the most important synthesis challenge. The Head of Research must reconcile conflicting findings from the two researchers.

### Scenario A: Quant says signals are healthy, Strategy says trades are losing

**Possible root causes (investigate in order):**
1. **Aggregation pipeline noise**: Individual agent signals may be correct, but the Bayesian log-odds combination may be introducing errors. Check the polarization score and close-call frequency. If >40% of signals are flagged as close calls, the aggregation layer is struggling.
2. **Risk parameter misalignment**: Signals may be directionally correct but the position sizing, stop placement, or take-profit levels may be wrong for the current regime. Check: are stops getting hit too frequently? Are take-profits too tight?
3. **Regime mismatch in CRO parameters**: The CRO may not have updated risk limits for the current regime. If we transitioned from bull to bear but CRO limits are still at bull settings, good signals will produce losing trades through oversized positions.
4. **Exit management failures**: Signals may be correct on entry but the trade monitor is cutting winners too early or holding losers too long. Check: exit_reason breakdown (stop_loss vs take_profit vs time_stop vs trailing_stop).
5. **Latency between signal and execution**: If the COO coin selection cycle and analysis cycle are misaligned, signals may be stale by execution time.

**Resolution protocol:**
- Weight Strategy's finding more heavily if sample size >= 30 closed trades
- Weight Quant's finding more heavily if agent-level analysis has clear statistical significance (p < 0.05)
- If both have strong evidence: the problem is almost certainly in the pipeline between signal generation and trade execution (aggregation, risk management, or execution layers)

### Scenario B: Quant says signals are degrading, Strategy says trades are winning

**Possible root causes:**
1. **Favorable regime carrying weak signals**: The market may be trending strongly enough that even degraded signals produce winning trades. This is dangerous — when the regime shifts, losses will be sudden and large.
2. **Small sample size in one finding**: If Quant has 200 signals but Strategy only has 15 closed trades, the quant analysis is more statistically reliable. Conversely, if Strategy has 50+ trades but Quant is looking at a narrow window, Strategy may be more representative.
3. **Surviving on one team**: One team (often Technical in trending markets) may be carrying all the alpha while others contribute nothing or negative value. Check team_contribution breakdown.
4. **Conviction calibration offset**: Low-conviction signals may be winning while high-conviction signals are losing (or vice versa), producing an overall positive P&L despite degraded signal quality.

**Resolution protocol:**
- Flag as IMPORTANT even though trades are currently profitable
- Recommend increasing monitoring frequency on the degrading signals
- If only one team is carrying alpha: flag that team as single-point-of-failure risk
- If sample size disparity: note explicitly which finding has more statistical power

### Scenario C: Both agree on a problem

When both researchers independently identify the same issue, escalate it one severity level. If both say IMPORTANT, escalate to CRITICAL. This convergence is the strongest evidence for action.

### Scenario D: Both say everything is fine

The rarest and most dangerous scenario. Actively look for what might be missed:
- Check if the calm is due to low trading activity (few signals, few trades)
- Check if the regime is transitioning and the calm is the eye of the storm
- Verify that sample sizes are sufficient for both researchers' conclusions
- Note that "healthy" is still worth reporting with specific numbers

## 1.5 Synthesizing Across Different Sample Sizes

When comparing findings with different sample sizes:

| Sample Size | Statistical Weight | Minimum for "Conclusive" |
|---|---|---|
| n < 10 | Anecdotal — note but do not base decisions on | No conclusions possible |
| n = 10-19 | Suggestive — directional indication only | Insufficient |
| n = 20-49 | Moderate confidence — can inform recommendations | Sufficient for preliminary |
| n = 50-99 | High confidence — base decisions on this | Sufficient for most |
| n >= 100 | Very high confidence — statistically robust | Fully conclusive |

When two findings conflict and one has n=15 while the other has n=80, explicitly state: "The quant finding (n=80) carries substantially more statistical weight than the strategy finding (n=15). However, the strategy finding represents real P&L and warrants monitoring."

## 1.6 Information Coefficient and Signal Quality Assessment

The Information Coefficient (IC) is the correlation between an agent's conviction and actual returns:
- **IC > 0.05**: Agent has real predictive power. Higher conviction genuinely predicts better outcomes.
- **IC near 0.00**: Agent's conviction is uncalibrated. Its directional calls may still be useful, but conviction levels are noise.
- **IC < -0.03**: Agent is inversely calibrated. Higher conviction predicts WORSE outcomes. This is a CRITICAL finding — the agent's conviction should be inverted or the agent should be investigated for systematic bias.

In synthesis, always report the IC for flagged agents. A low-accuracy agent with positive IC may be more valuable than a high-accuracy agent with zero IC, because the high-IC agent's conviction can be used for position sizing.

## 1.7 Decay Detection Interpretation

Signal decay is measured by comparing recent accuracy (last 30 days) to older accuracy (30-90 days ago):

| Decay Delta | Severity | Interpretation |
|---|---|---|
| Delta > -0.05 | None | Normal variance. No action needed. |
| -0.10 < Delta <= -0.05 | Mild | Early warning. Monitor for another cycle. |
| -0.20 < Delta <= -0.10 | Moderate | Confirmed decay. Investigate cause. Recommend weight reduction. |
| Delta <= -0.20 | Severe | Critical decay. Agent may be anti-predictive. Recommend quarantine weight (0.3). |

Always check the sample sizes for both periods. Decay detected with recent n=5 and older n=40 is unreliable. Both windows need n >= 10 for the comparison to be meaningful.

Natural decay rate in financial signals is approximately 2-5% per quarter. Anything beyond this warrants investigation:
- Is the market regime different from when the agent was calibrated?
- Has the underlying data source changed or degraded?
- Is the agent's prompt or methodology now outdated for current conditions?

## 1.8 Correlation Cluster Analysis

When the quant researcher identifies high-correlation agent pairs (>80% agreement):

**What it means:**
- Two agents agreeing >80% of the time are effectively one agent with a louder voice
- This destroys the Condorcet Jury Theorem benefit that underpins our ensemble approach
- The Bayesian log-odds combination double-counts evidence from correlated agents

**What to recommend:**
- If both agents have similar accuracy: recommend reducing weight on the lower-performing one
- If one agent is clearly superior: recommend considering removal of the inferior one
- If correlation is driven by shared data sources: recommend diversifying data inputs
- Always note: model diversity > model count

**Acceptable correlation thresholds:**
- Within the same team (e.g., two technical agents): 70-80% agreement is expected
- Across different teams (e.g., technical vs sentiment): >70% agreement is a concern
- Across all agents: target average pairwise agreement of 50-65% for optimal ensemble diversity

---

# 2. THE FUND'S RISK MANAGEMENT FRAMEWORK

## 2.1 Universal Risk Constants

These parameters are hard limits that remain constant or near-constant across all market regimes:

| Parameter | Value | Source / Rationale |
|---|---|---|
| **Max risk per trade** | 1-2% of portfolio | Industry standard across prop firms, hedge funds, institutional desks. CME Group 2% rule. Conservative crypto: 1%. |
| **Daily loss limit (circuit breaker)** | 3% of portfolio | The 3-5-7 rule: 3% max daily loss, 5% max all open positions, 7% max total portfolio exposure. Bots halt at 3% daily loss. |
| **Max portfolio heat (all open positions)** | 5-7% of portfolio | 3-5-7 rule: never more than 5-6% of capital at risk across all simultaneous open positions. |
| **Risk-reward minimum** | 1:1.5 (short-term), 1:2 to 1:3 (trend) | Short-term trades need at least 1:1.5. Trend-following targets 1:2 or 1:3. At 1:3, only 30% win rate needed for profitability. |
| **Volatility target (portfolio level)** | 10-15% annualized | Bridgewater All Weather targets 10-12%. Systematic trend-followers target 10-15%. Scaling factor = Target Vol / Recent Vol. |
| **Single position concentration limit** | 2-5% of portfolio | UCITS 5/10/40 rule (max 10% single issuer). Professional traders use 2-5% for high-vol crypto. |

## 2.2 Regime Parameters — Full Matrix

This is the complete parameter set by market regime. The CRO (Tobias Richter) adjusts these dynamically. The Head of Research must validate that the CRO's settings align with empirical evidence.

| Parameter | Bull | Bear | Ranging | Crisis |
|---|---|---|---|---|
| **Max position size** | 8-10% | 3-5% | 5-7% | 1-2% |
| **Risk per trade** | 1.5-2% | 0.5-1% | 1-1.5% | 0.25-0.5% |
| **Number of open positions** | 10-15 | 5-8 | 8-12 | 0-3 |
| **Gross exposure** | 150-200% | 100-130% | 120-150% | 0-50% |
| **Net exposure** | +60% to +80% | -10% to +20% | 0% to +30% | -20% to 0% |
| **Long/Short ratio** | 70:30 to 80:20 | 30:70 to 40:60 | 55:45 to 60:40 | 0:100 to 40:60 |
| **Stop loss (ATR multiplier)** | 1.5-2x | 3-4x | 1.5-2x | 1x or no trades |
| **Confidence threshold** | 0.55-0.60 | 0.70-0.80 | 0.60-0.70 | 0.85+ |
| **Consensus threshold** | 60% (3/5) | 75-80% (4/5) | 65-70% | 80-100% |
| **Max DD before position cut** | 5% | 3% | 4% | 2% |
| **Max DD before full halt** | 10% | 7-8% | 8-10% | 5% |
| **Daily loss limit** | 3% | 2% | 2.5% | 1% |
| **Kelly fraction** | 25-50% | 10-25% | 20-30% | 0-10% |
| **Cash/stablecoin allocation** | 5-15% | 30-50% | 15-25% | 50-100% |
| **Position size scaling factor** | 1.0x (base) | 0.5x | 0.7x | 0.25x |
| **Trailing stop activation** | After 2x risk achieved | After 1.5x risk | After 2x risk | N/A |

### Regime Detection Thresholds (CEO uses these)

| Indicator | Bull | Bear | Ranging | Crisis |
|---|---|---|---|---|
| **Price vs 200-day MA** | Above | Below | Oscillating around | Far below |
| **ADX** | > 25 (trending up) | > 25 (trending down) | < 25 | > 30 (trending down fast) |
| **50/200 MA cross** | Golden cross | Death cross | Flat/intertwined | Death cross + acceleration |
| **Momentum (ROC 20d)** | > 0 | < 0 | Near zero, oscillating | Deeply negative |
| **F&G Index** | Trending > 50 | Sustained < 30 | 30-60 | < 15 |
| **BTC 30d realized vol** | < 50% annualized | 50-80% annualized | Variable | > 80% annualized |
| **Correlation spike** | Low (< 0.5 avg pair) | Rising (0.5-0.7) | Low | > 0.7 avg pair |

## 2.3 Kelly Criterion — Detailed Application

The Kelly Criterion provides the theoretically optimal bet size: **f = p - (1-p)/b** where p = win probability and b = reward/risk ratio.

### Full Kelly vs Fractional Kelly Comparison

| Kelly Fraction | Growth Rate Retained | Variance vs Full Kelly | Recommended For |
|---|---|---|---|
| **Full Kelly (1.0)** | 100% of max growth | 100% | Theoretical only. NEVER for crypto. Ruin probability is non-trivial with estimation error. |
| **Half Kelly (0.50)** | ~75% of max growth | ~25% of full Kelly variance | Aggressive systematic funds with verified, stable edge. Appropriate for bull regimes with strong calibration data. |
| **Quarter Kelly (0.25)** | ~56% of max growth | ~6% of full Kelly variance | Conservative institutional standard. This is the default for Syndicate. Appropriate for most regimes. |
| **Tenth Kelly (0.10)** | ~19% of max growth | ~1% of full Kelly variance | Crisis mode. When edge estimates are highly uncertain. Appropriate for crisis/black swan regimes. |

### Why Fractional Kelly is Mandatory for Crypto

1. **Fat tails**: BTC kurtosis = 10.85, crypto basket kurtosis = 27. The Kelly formula assumes normal returns. Fat tails mean the downside is far worse than the formula predicts.
2. **Estimation error**: Our win probability p and reward/risk ratio b are estimated from limited data. A 5% error in p can turn a positive Kelly fraction into ruin.
3. **Regime shifts**: p and b are not stable. They change with market regime. Quarter Kelly builds in a safety margin for regime transitions.
4. **Transaction costs and slippage**: Kelly assumes frictionless execution. Real crypto has slippage, spread, and funding costs.
5. **Correlation**: Kelly assumes independent bets. Our positions are correlated (avg crypto correlation: 0.56, rising to 0.70+ in bear markets). This effectively reduces the portfolio-level Kelly fraction.

### Kelly Fraction by Regime

| Regime | Kelly Fraction | Rationale |
|---|---|---|
| **Bull** | 25-50% (Quarter to Half Kelly) | Higher confidence in edge estimates during favorable conditions. Track record data is most reliable in trending markets. |
| **Bear** | 10-25% (Tenth to Quarter Kelly) | Elevated uncertainty, fat tail risk, correlation spikes. Edge estimates degrade faster. |
| **Ranging** | 20-30% | Mean reversion strategies have higher win rate but smaller payoffs. Kelly fraction reflects smaller b (reward/risk). |
| **Crisis** | 0-10% | Near zero or do not trade. Edge estimates are unreliable. Capital preservation is the sole objective. |

### Computing Kelly for Research Assessment

When assessing whether the fund's position sizing is appropriate, compute the optimal Kelly fraction from trade data:

```
For each asset tier / regime combination:
  p = historical win rate (from trade attribution data)
  b = average win / average loss (from trade attribution data)
  kelly = p - (1 - p) / b
  recommended_fraction = kelly * 0.25  (quarter Kelly)
  max_position = recommended_fraction * portfolio_value
```

Compare this computed recommendation against the CRO's actual max_position_pct. If the CRO's setting is more than 2x the computed Kelly recommendation, flag as IMPORTANT. If more than 3x, flag as CRITICAL.

## 2.4 Tier-Based Risk Parameters

The Risk Manager applies different parameters based on asset tier:

| Tier | Assets | Typical Vol | Stop Multiplier | Position Limit | Rationale |
|---|---|---|---|---|---|
| **BTC** | BTC | 60-90% ann. | 2x ATR | 10% portfolio | Most liquid, lowest relative vol |
| **Top 5** | ETH, SOL, BNB, XRP, ADA | 80-120% ann. | 2.5x ATR | 7% portfolio | High liquidity, moderate vol |
| **Large-cap** | Top 20 by market cap | 100-150% ann. | 3x ATR | 5% portfolio | Good liquidity, higher vol |
| **Mid-cap** | Rank 20-100 | 120-200% ann. | 3.5x ATR | 3% portfolio | Lower liquidity, much higher vol |
| **Meme/Small** | DOGE, SHIB, low-cap | 200-500% ann. | 4x ATR | 1% portfolio | Extreme vol, liquidity risk |

### ATR-Based Stop Loss Formula

```
LONG:  stop_loss = entry_price - (ATR_14 * multiplier)
SHORT: stop_loss = entry_price + (ATR_14 * multiplier)

multiplier = base_tier_multiplier * regime_adjustment

regime_adjustment:
  bull = 0.8 (tighter stops, momentum helps)
  ranging = 1.0 (standard)
  bear = 1.3 (wider stops, higher vol)
  crisis = 1.5 (widest stops, extreme vol)
```

### Performance Benchmarks for Stop Width Research

Research from the fund's data sources shows:
- **2x ATR stop-loss reduced max drawdown by 32%** vs fixed stop-loss (1,000-trade study)
- **3x ATR multiplier boosted performance by 15%** vs fixed stop-loss methods
- Below 3% fixed stop in crypto: guaranteed stop-out due to normal noise
- Above 10% fixed stop: exponentially harder to recover (10% loss requires 11.1% gain; 20% requires 25%)

## 2.5 Institutional Benchmarks — Reference Points

### Bridgewater Associates (All Weather / Risk Parity)

| Parameter | Value |
|---|---|
| Portfolio volatility target | 10-12% annualized |
| Leverage | ~1.8x via futures |
| Risk allocation | Equal risk contribution per asset class |
| Rebalancing | Dynamic — scale inversely to volatility |
| Philosophy | No regime prediction. Balance across all environments. |

### Renaissance Technologies (Medallion Fund)

| Parameter | Value |
|---|---|
| Position sizing | Kelly criterion-based, precisely calibrated per trade probability |
| Daily trades | ~300,000 |
| Average position size | ~$100K per trade (at $10B AUM) |
| Holding period | Very short (intraday to days) |
| Fund cap | $10-15B (employees only) — capacity constraint as risk management |
| Market exposure | Market-neutral (long/short pairs, eliminate beta) |
| Estimated Sharpe | >2.0 (over 30 years) |
| Annual returns | ~66% before fees (1988-2018) |

### Millennium / Citadel / Point72 (Multi-Manager)

| Parameter | Value |
|---|---|
| Total fund max drawdown | 2.5-5% depending on firm |
| PM flagged at | 1.5% drawdown — head of risk asks basic questions |
| PM formal review at | 2.5% drawdown — documented meeting to justify positions |
| PM allocation halved at | 5% drawdown (Millennium default) |
| PM terminated at | 8-10% drawdown from peak (Millennium: 10%) |
| Daily loss conversation | Mid-single digit % triggers immediate allocation reduction |

### CTA Benchmarks (Systematic Trend-Following)

From Concretum Group analysis (40 futures markets, 1980-2024):

| Method | IRR p.a. | Max Drawdown | Hit Ratio (trade) | Hit Ratio (monthly) |
|---|---|---|---|---|
| Volatility Targeting (VT) | 11.46% | 25.65% | 42.5% | 60% |
| Volatility Parity (VP) | 12.83% | ~25% | 42.4% | 59% |
| VP + Pyramiding | 20.00% | 48.69% | 39.3% | 56% |

Key parameter: **0.10% daily volatility contribution per trade** (= $100K risk per $100M portfolio per day).

## 2.6 Drawdown Circuit Breakers

The Risk Manager implements hard circuit breakers:

| Trigger | Action | Recovery |
|---|---|---|
| Daily P&L < -daily_loss_limit | Halt all new entries for remainder of day | Auto-resume next cycle |
| Portfolio DD > max_DD_before_cut | Reduce all positions by 50% | CRO must manually re-enable full sizing |
| Portfolio DD > max_DD_before_halt | Halt ALL trading | CEO and CRO must jointly re-enable |
| Single position DD > stop_loss | Close position at market | Automatic |

**Research implication:** When circuit breakers trigger, this is a CRITICAL finding. Include in the digest with analysis of what caused the drawdown, whether the circuit breaker thresholds are appropriately set, and whether the recovery protocol is working.

---

# 3. CONSENSUS THRESHOLDS AND SIGNAL AGGREGATION

## 3.1 Consensus Level Performance Data

Based on compiled research from academic papers, ensemble ML studies, and quant fund practices:

| Consensus Level | Signal Frequency | False Signal Rate | Win Rate (Est.) | Risk-Adjusted Returns |
|---|---|---|---|---|
| 60% (3/5 agree) | Highest | Moderate | ~60-63% | Good — more trades capture more total return, more noise |
| 70-75% (3.5-4/5) | Moderate | Low-Moderate | ~65-70% | **BEST risk-adjusted (sweet spot)** |
| 80% (4/5 agree) | Low | Low | ~70-75% | Strong per-trade, fewer opportunities |
| 100% (5/5 agree) | Very Low | Very Low | ~75-80%+ | Highest per-trade, but total return often lower due to missed trades |

### The Sweet Spot: 70-80% Consensus

Evidence converges on 70-80% consensus as optimal:
1. **Ensemble ML research** shows performance plateaus after this threshold — adding more agreement provides diminishing returns
2. **Frequency-conviction tradeoff** is fundamental — 70-80% captures most major moves while filtering noise
3. **Analyst consensus data** (ScienceDirect): high-but-not-unanimous agreement is most profitable — when ALL analysts agree, the signal is already priced in
4. **PoW-PoW cryptocurrency pairs** with the fewest signals (highest threshold) achieved the highest Sharpe ratio of 0.65 (Journal of Futures Markets)

## 3.2 Condorcet Jury Theorem — Applied to Our System

The Condorcet Jury Theorem states that if each independent model has accuracy p > 0.5, majority voting increases group accuracy toward 1.0 as n increases.

### Computed Accuracy for Syndicate's 5-Team System

| Individual Accuracy (p) | Majority (3/5) | 4/5 Agree | 5/5 Agree |
|---|---|---|---|
| 55% | 59.3% | 33.7% | 5.0% |
| 60% | 68.3% | 47.2% | 7.8% |
| 65% | 76.5% | 61.6% | 11.6% |
| 70% | 83.7% | 74.9% | 16.8% |
| 75% | 89.6% | 85.5% | 23.7% |

**Key insight for research:** With 5 teams at 60% individual accuracy, majority voting gives 68.3% group accuracy — a significant improvement. But requiring 5/5 agreement only triggers 7.8% of the time. The 4/5 threshold triggers 47.2% of the time — enough to capture major moves.

### CRITICAL ASSUMPTION: Independence

The Condorcet benefit **collapses** when models are correlated. Our 5 teams MUST be genuinely independent in their analysis methodology:
- Technical: Price/volume indicators, chart patterns
- Sentiment: Social media, news, Reddit, community buzz
- Fundamental: Tokenomics, revenue, development activity
- Macro: Fed policy, DXY, M2 liquidity, global risk appetite
- On-Chain: Whale wallets, exchange flows, MVRV, funding rates

**If any two teams share >80% agreement rate, the Condorcet benefit degrades.** This is why correlation monitoring is one of the quant researcher's core responsibilities.

## 3.3 Regime-Adaptive Consensus Framework

| Market Regime | Minimum Consensus | Position Sizing | Notes |
|---|---|---|---|
| Strong Bull | 60% (3/5) | Normal to Large | Momentum carries; waiting for full agreement means missing entries |
| Weak Bull | 70% | Normal | More confirmation needed as momentum weakens |
| Ranging | 80% (4/5) | Small to Normal | High false signal rate; choppy conditions produce most false signals |
| Weak Bear | 80% (4/5) | Small | Protect capital; fewer trades, higher conviction required |
| Strong Bear | 100% (5/5) | Small to Tiny | Only trade with full agreement; bear market rallies generate many false buy signals |
| Crisis/Panic | Contrarian override | Small | External sentiment overrides; look for extreme fear buys at 60% consensus |

### The Contrarian Override

This is critical and unique to crisis regimes:
- **When F&G < 15 AND whale accumulation detected:** bias toward long regardless of model consensus
- **When F&G > 85 AND all models are bullish:** reduce position sizes, tighten stops — the crowd is usually wrong at extremes
- Extreme sentiment readings (where the crowd is demonstrably wrong) occur roughly **4-8% of the time**
- During these windows, contrarian strategies dramatically outperform
- **AAII Sentiment Survey** (since 1987): When bearish sentiment > 50%, S&P 500 averaged +25% over next 12 months
- **Bear-bull spread 2+ SD below average** (4.1% of time since 1987): 3-month returns +0.3% above average, 6-month +0.7%, 12-month +0.6%

## 3.4 Unanimous Agreement Analysis

When all 5 teams agree with high conviction:
- The aggregator applies a **+15% confidence boost** (unanimity bonus)
- Minimum conviction must be 6+ across all teams for the bonus to apply
- This is the **strongest signal type** the fund can produce

When all 5 teams agree AND external sentiment is at extreme greed (F&G > 85):
- This is actually a **SELL signal**, not confirmation to go bigger
- Historical pattern: unanimous bullish consensus + extreme greed has preceded tops 70% of the time

## 3.5 Position Sizing by Consensus Level

The fund uses consensus to scale position size, not just as a go/no-go gate:

| Consensus Level | Position as % of Max |
|---|---|
| 60% (3/5) | 25% of maximum position |
| 80% (4/5) | 50% of maximum position |
| 100% (5/5) | 100% of maximum position |

This means a 60% consensus signal in a bull market (max position = 10%) would size at 2.5% of portfolio. A 100% consensus signal would size at the full 10%.

## 3.6 Shannon Entropy in Disagreement Detection

The aggregator computes Shannon entropy of the vote distribution:
- **Entropy = 0**: Unanimous agreement. All teams voting the same direction.
- **Entropy near max (log2(3) = 1.585)**: Maximum disagreement. Equal split among bullish, bearish, neutral.
- **Polarization > 0.7**: Teams are highly split on direction. The aggregator reduces confidence by up to 40%.

**Research implication:** When entropy is consistently high across multiple coins/cycles, it may indicate:
1. The market is genuinely uncertain (no clear trend)
2. One or more teams are systematically miscalibrated
3. The data sources for different teams are providing contradictory signals

Report entropy trends in digests. Rising entropy over time is an early warning of regime transition.

---

# 4. TECHNICAL INDICATOR PERFORMANCE

## 4.1 Individual Indicator Rankings (Crypto-Specific)

Based on compiled research from academic papers, backtesting platforms, and quantitative strategy sites:

| Indicator | Standalone Win Rate | Sharpe Ratio (approx.) | Best Use Case | Reliability |
|---|---|---|---|---|
| RSI(14) | 40-55% | 0.3-0.7 | Mean reversion entries at extremes | MODERATE — needs confirmation |
| MACD crossover | 40-55% | 0.3-0.8 | Trend confirmation, not prediction | MODERATE — lagging indicator |
| SMA 50/200 crossover | 55-65% | 0.5-0.8 | Long-term trend identification | HIGH — but very lagging |
| Bollinger Band squeeze | 50-60% | 0.4-0.7 | Volatility breakout detection | MODERATE-HIGH with volume confirmation |
| Volume analysis | N/A (confirming) | N/A | Confirmation only, not standalone | HIGH as confirmation |
| Funding rate extremes | 60-75% | 0.5-0.9 | Contrarian entries in perp markets | HIGH for short-term |
| **Multi-TF alignment** | **64.7%** | **N/A** | **THE single best edge available** | **HIGH** |

### The Multi-Timeframe Edge: 33.8 Percentage Points

This is the most important finding in our technical indicator research:

- **Study of 8,734 trades analyzed**
- Single timeframe signal win rate: ~30-40%
- Two timeframe alignment: ~55-60%
- Three timeframe alignment (1D + 4H + 1H all agreeing): **64.7%**
- Non-aligned signals: ~30.9%
- **The alignment edge: 33.8 percentage points** in 6-month returns

This single filter (~10 seconds of analysis) represents the largest edge enhancement of any technique studied. The Technical team's timeframe alignment assessment (FULLY_ALIGNED, MOSTLY_ALIGNED, CONFLICTING) is the most valuable metadata in their signals.

## 4.2 Combined Strategy Rankings

| Combination | Win Rate | Sharpe Ratio | Notes |
|---|---|---|---|
| MACD + RSI + multi-TF filter | 65-75% | 1.0-1.44 | **Best risk-adjusted returns** |
| MACD + RSI + Bollinger | 73-77% | 0.9-1.3 | Reduced false signals |
| MACD + RSI | 65-77% | 0.8-1.2 | Most popular combination |
| MACD + trailing stop + diversification | 55-65% | 1.07-1.44 | Optimized for Sharpe |
| RSI + funding rate + Bollinger | 65-75% | 0.7-1.0 | Best for mean reversion |

### Specific Backtest: MACD Multi-Coin Portfolio

- BTC + ETH + ADA portfolio with MACD signals, trend filter, and trailing stop
- Annual return: 68.70%
- Sharpe ratio: 1.44
- Compared to standalone 1H MACD: Sharpe 0.33 (4.4x improvement through filtering and diversification)

## 4.3 RSI Deep Dive

### RSI < 30 (Oversold)

- BTC's 14-day RSI has fallen below 30 only three times in its entire history
- The previous two sub-30 readings preceded rallies of +1,700% and +9,900% (multi-year timeframes)
- **Short-term (30-day):** ~60-65% win rate, +5-15% average return
- **Backtest (2022-2025):** 294 trades, 22.11% win rate (strict profit-target based), annualized return 19.67%, max drawdown 23.34%
- **RSI-based optimized strategy (2018-2022):** 773.65% total return vs 275.22% buy-and-hold (2.8x outperformance)
- **Mechanical 70/30 RSI strategy:** significantly underperformed buy-and-hold. Lacks robustness without additional filters.

### RSI > 70 (Overbought)

- **LOW reliability as a sell signal** in crypto
- RSI stayed above 70 for most of the 2021 bull run while price continued rising
- For rising cryptocurrencies, overbought signals actually preceded continued gains (PMC academic study)
- **Use as risk-management alert** (reduce position size, tighten stops), NOT as a sell trigger
- Only reliable when combined with bearish divergence + volume decline

### Bullish RSI Divergence (Price lower low, RSI higher low)
- Standalone accuracy: 45-55%
- With confirmation (candlestick pattern or structure break): 60-70%
- BTC forward return (60 days): up to 10x higher than bearish divergence
- **Substantially more reliable and profitable than bearish divergence in crypto**

### Bearish RSI Divergence (Price higher high, RSI lower high)
- Standalone accuracy: 40-50%
- Academic authors advise against using for rising cryptos like BTC/ETH
- Less reliable in crypto's structurally bullish environment

## 4.4 MACD Performance by Timeframe

| Timeframe | Win Rate (Standalone) | Win Rate (with RSI filter) |
|---|---|---|
| 1H | ~37-40% | ~50-55% |
| 4H | ~45-50% | ~55-65% |
| 1D | ~50-55% | ~65-73% |
| 1W | ~55-60% | ~70-77% |

- MACD bearish crossovers are LESS reliable than bullish crossovers in crypto (structural long bias)
- In trending markets: ~65% win rate. In choppy/ranging: ~45% win rate
- Gate.io analysis (Jan 2026): **77% win rate** combining RSI with MACD in backtesting

## 4.5 Golden Cross / Death Cross

### Golden Cross (SMA 50 > SMA 200) on BTC

| Period | Average Return | Win Rate |
|---|---|---|
| 7 days | +4.4% | ~65% |
| 30 days | +9.6% to +14.8% | ~70-81% |
| 3 months | +15% to +35% | ~65-75% |
| 6 months | +30% to +60% | ~70% |
| 12 months | +50% to +150%+ | ~70% |

**Macro-environment filter:**
- During easing cycles: 81.2% success rate, +14.8% avg 30-day return
- During tightening cycles: 59.3% success rate, +7.3% avg 30-day return

### Death Cross (SMA 50 < SMA 200) on BTC

- Historically a **LAGGING indicator** — more often appears NEAR market lows than at start of prolonged declines
- **Contrarian buying opportunity in 64% of cases**
- In structural bear markets (2014, 2018, 2022): correctly signaled further downside
- In 2024 post-ETF structural bull: death cross was followed by +94% return

## 4.6 Funding Rate Extremes

### Deeply Negative Funding (< -0.05%)

| Metric | Value |
|---|---|
| Bounce probability (7 days) | ~70-75% |
| Average bounce size | +5% to +15% |
| Short squeeze probability | ~40-50% (when OI is also elevated) |

### Extremely Positive Funding (> +0.1%)

| Metric | Value |
|---|---|
| Correction probability (7 days) | ~60-70% |
| Average correction size | -5% to -15% |
| Time to correction | 1-7 days typically |

**Rule for research:** Extreme positive funding + high OI + declining spot volume = imminent correction (70%+ probability). Flag this combination as CRITICAL when observed.

## 4.7 What Works vs What Doesn't

### What Works
- Multi-indicator combinations outperform single indicators consistently
- Multi-timeframe alignment (33.8pp edge) is the single largest edge enhancement
- Mean reversion in ranging markets; trend following in trending markets
- Funding rate extremes for short-term contrarian entries
- Moving average strategies reduce drawdowns vs buy-and-hold
- Combined momentum + mean reversion (50/50): Sharpe ratio 1.71, annualized 56%

### What Doesn't Work (or Is Unreliable)
- Single-indicator mechanical strategies (buy RSI < 30, sell RSI > 70)
- Shorting overbought conditions in bull markets
- MACD signals in ranging/choppy markets
- Volume spikes in isolation without follow-through confirmation
- Any indicator without contextual market regime awareness
- After controlling for data snooping and market frictions, statistically significant positive excess returns are rarely achieved with any single technique

---

# 5. BEAR MARKET RESEARCH

## 5.1 BTC Bear Market History — Complete Dataset

| Cycle | Peak | Trough | Max Drawdown | Duration to Bottom | Recovery to New ATH |
|---|---|---|---|---|---|
| 2011 | $32 | $2 | -93% | ~5 months (160 days) | ~2 years (730 days) |
| 2013-2015 | $1,163 | $170 | -86% | ~410 days | ~3 years (1,095 days) |
| 2017-2018 | $19,100 | $3,200 | -83% | ~365 days | ~3 years (1,095 days) |
| 2021-2022 | $69,000 | $15,476 | -77% | ~330 days | ~2 years (730 days) |
| 2025-2026 | $126,198 | ~$65,000 | -46%+ (ongoing) | ~119 days+ | TBD |

**Key pattern:** Maximum drawdowns have decreased over cycles: 93% -> 86% -> 83% -> 77%. This reflects market maturation, increasing market capitalization, and institutional participation acting as a floor.

### Duration Statistics
- Average bear market duration (70%+ decline): 9 months
- Median across all 15 bear markets since 2014: 101 days to bottom
- Average time to new ATH: 249 days (simple corrections), 531 days (deep bears)

### Critical Insight: Severity Escalation
Once a Bitcoin drawdown becomes prolonged (100+ days to bottom), both depth and duration nearly double:
- Simple corrections: avg drawdown 40.7%, avg 101 days to bottom, avg 249 days to new ATH
- Prolonged bears (100+ days): avg drawdown 59.2%, avg 215 days to bottom, avg 531 days to new ATH

### Post-Drawdown Recovery Data

| Drawdown from ATH | 1-Year Win Rate | Median 1-Year Return | Worst Outcome |
|---|---|---|---|
| -50% | 90% | +95% | Varies |
| -70% | **100%** | +1,692% (median) | +25% (minimum — worst case still positive) |

This is one of the most powerful statistical findings in crypto: buying after a 70% decline from ATH has a **100% historical win rate over 1 year**, with the worst case being +25%.

## 5.2 Rally and Bounce Statistics

### Post-70%+ Decline Rallies (From Bottom)
- Average rally from bottom: 3,485%
- Median rally from bottom: 1,692%
- Minimum rally: 101%
- Maximum rally: 12,804%
- Most recent (2022 low to 2025 peak): 716%

### Dead Cat Bounce Characteristics
- Typical dead cat bounce: 15-30% recovery before resuming downtrend
- Stall point: usually around 25-30% above the low of the previous decline
- Recovery retracement: approximately 30-50% of the original fall before resuming downward
- Identification: decreasing volume, contracting spot demand, negative funding rates

### Pullback Statistics Within Bull Markets
- Median pullback during bull phases: 27%
- Average pullback: 27-34%
- Typical rallies between corrections: median 61-75%

## 5.3 Strategies That Were Profitable in 2022

### What Worked

| Strategy | Performance | Notes |
|---|---|---|
| **DCA through crash** | +192.47% return by 2025 | 33 percentage points better entry than lump-sum |
| **Fear-weighted DCA (2x below F&G 25)** | +1,145% over 7 years | 5.7x better than standard DCA |
| **Monday DCA** | 14.36% more BTC accumulated | 2018-2025 backtest |
| **Pythagoras market-neutral** | +8% in 2022 | While BTC dropped 65% |
| **Market-neutral fund of funds** | 870% gross since 2018 | Across all market cycles |
| **Short selling** | $2.5B+ from MSTR alone in 2025 | Funding risk when rates deeply negative |
| **Combined MR + TF (50/50)** | Sharpe 1.71 | Best risk-adjusted returns |

### What Failed
- Buy-the-dip without discipline: Terra wiped out dip buyers, then FTX hit again
- Leveraged long positions: catastrophic in sustained downtrends
- Undisciplined altcoin accumulation: 4 of 2017's top-10 tokens NEVER recovered ATHs
- ~250 of 715 crypto hedge funds closed (35%) from May 2022 to Dec 2023
- Three Arrows Capital: collapsed from leveraged supercycle thesis
- Alameda Research: failed from overleveraged directional bets

## 5.4 Sector Performance During Bear Markets

| Sector | 2022 Max Drawdown | Recovery Notes |
|---|---|---|
| Bitcoin (BTC) | -77% | Recovered to new ATH by March 2024 |
| Ethereum (ETH) | -79.5% to -81% | Slower recovery, ETH/BTC ratio declined |
| DeFi (TVL) | -64% ($184.5B to $66.7B) | Deleveraging was primary driver |
| NFTs | -80%+ trading volume decline | Partial recovery in late 2024 |
| Exchange Tokens | Outperformed BTC/ETH | 7 of 8 exchange tokens beat BTC/ETH over 6 months |
| Legacy Alts (2017 era) | Many -90%+ never recovered | 4 of top-10 from 2017 still below 2017 ATHs |

**Rule of thumb:** Whatever led in the late bull crashes hardest in the bear. The last sector to rally is the first to die. BTC always has the smallest drawdown among volatile crypto assets.

## 5.5 ETH vs BTC in Bear Markets

ETH drawdowns historically exceed BTC by 10-15 percentage points:
- 2018: ETH -93.8% vs BTC -83%
- 2022: ETH -79.5% vs BTC -77%

## 5.6 Mean Reversion vs Trend Following in Bears

| Strategy | Bull Market | Bear Market | Ranging |
|---|---|---|---|
| Trend Following (MAX) | Excellent | Good (short side) | Poor |
| Mean Reversion (MIN) | Moderate | Excellent (short-term) | Good |
| Combined (50/50) | Strong | Strong | Strong |

**Combined Momentum + Mean Reversion (50/50 blend):** Sharpe 1.71, annualized 56%, T-stat 4.07.

**Key Bitcoin behavior:**
- At local maxima: BTC tends to continue trending upward (momentum)
- At local minima: BTC tends to mean-revert and bounce back
- Implication: use trend-following for macro direction entries; use mean-reversion for short-term tactical trades during panic selloffs

## 5.7 Optimal Position Sizing During Drawdowns

| Market Phase | Stablecoin/Cash % | Risk per Trade | Rationale |
|---|---|---|---|
| Early Bear (-30% from ATH) | 40% | 0.5-0.75% | Trend uncertain |
| Mid Bear (-50% from ATH) | 60% | 0.5% | Capital preservation priority |
| Late Bear (-70% from ATH) | 40% | 0.75% | Accumulation opportunity |
| Accumulation/Recovery | 20% | 1-1.5% | Increased conviction |

## 5.8 Bear Market Stop Loss Recommendations

- Use **ATR-based stops with 2.5-3x multiplier** (vs 2x in bull)
- Never use fixed percentage stops below 5% in bear markets (noise will stop you out)
- Bear market short squeezes can move 17%+ in 5 days (e.g., $63K to $74K)
- Tighter stops are **riskier** in volatile bear markets due to sudden reversals

---

# 6. FEAR AND GREED COMPREHENSIVE DATA

## 6.1 F&G Below 10 — Historical Instances and Returns

| Date | F&G Value | BTC Price | 30-Day Return | 90-Day Return | 12-Month Return |
|---|---|---|---|---|---|
| Dec 2018 (Crypto winter) | ~10 | ~$3,200 | +15% | +30% | +158% |
| Mar 2020 (COVID crash) | 9 | ~$4,500 | +70% | +170% | +1,500% |
| Jun 2022 (Luna collapse) | 6 | ~$20,000 | +20% | +5% | +20% |
| Nov 2022 (FTX collapse) | 6 | ~$15,500 | +15% | +40% | +85% |
| Feb 2026 (Current cycle) | 5 (ALL-TIME LOW) | ~$67,500 | TBD | TBD | TBD |

### Key Statistics
- **Sharpe ratio at F&G <= 10: 8.0** (for context, only one hedge fund globally had Sharpe > 2.0 from 2017-2020)
- Positive 30-day return probability: **~85%**
- Average 12-month return from F&G < 10: **+440%** (excluding ongoing 2026)
- Only exception: June 2022 (Luna contagion still unfolding — buy signal was 5 months early)

## 6.2 F&G Bucket Returns — Complete Reference

| F&G Range | Avg 30-Day Return | Avg 90-Day Return | Win Rate (30d) |
|---|---|---|---|
| 0-10 | +25-35% | +50-100% | ~85% |
| 10-20 | +10-20% | +30-50% | ~80% |
| 20-30 | +5-10% | +15-25% | ~65% |
| 30-50 | +2-5% | +5-15% | ~55% |
| 50-70 | 0-3% | +2-8% | ~50% |
| 70-80 | -2-0% | -5 to +5% | ~45% |
| 80-90 | -5 to -2% | -15 to -5% | ~35% |
| 90-100 | -10 to -5% | -25 to -10% | ~25% |

## 6.3 F&G Below 20 — Broader Dataset

- Positive 30-day returns: ~80% of the time
- Median 90-day return: +32%
- Average 6-month return: +60-80%
- Average 12-month return: +300-500%
- **CRITICAL NUANCE:** The average 90-day forward return at "below 25" is only +2.4%. The index can stay in the 15-25 range during extended downtrends without marking the bottom. The real edge is at the EXTREME readings (below 10-15), not just "fear" territory.

## 6.4 F&G Above 80 — Sell Signal Data

| Date | F&G Value | BTC Price | 30-Day Return | 90-Day Return |
|---|---|---|---|---|
| Late 2017 | 90+ sustained | ~$19,000 | -30% | -55% |
| April 2021 | 85+ (98 on Apr 16) | ~$64,000 | -40% | -55% |
| Nov 2021 | 84 | ~$68,000 | -15% | -40% |
| Early 2024 post-ETF | 90+ | ~$70K+ | Continued rally (FALSE SELL) |

- F&G > 80 sustained 14+ days: **~70% chance of >20% drawdown within 90 days**
- F&G > 90: tops form within 2-8 weeks
- NOT an immediate sell signal — can persist for weeks during strong trends
- Most reliable when accompanied by declining momentum/volume divergence

## 6.5 Fear-Based DCA Strategy Performance

| Strategy | 7-Year Return | Annualized | Notes |
|---|---|---|---|
| Standard DCA (fixed weekly) | 202% | ~17% | Baseline |
| Fear-weighted DCA (2x below 25) | 1,145% | ~43% | **5.7x better than standard DCA** |
| Buy at <=10, sell at >35 | ~14.6%/yr | ~14.6% | Most conservative; highest Sharpe |
| Buy at <=10, sell at >50 | Lower Sharpe | -- | More volatile |
| Buy at <=10, sell at >65 | Worst of three | -- | Holding too long reduced returns |

**Key finding:** The short-term strategy (buy at extreme fear, sell at modest recovery F&G > 35) produced the best risk-adjusted returns. Holding for greed territory actually underperformed.

## 6.6 When F&G FAILS (False Signals)

The most important caveat for research: **extreme fear during ACTIVE contagion is a false buy signal.**

- June 2022 (F&G = 6): Luna contagion was ONGOING. Buy signal was 5 months early. Subsequent drop from $20K to $15.5K.
- **Rule:** F&G < 15 is a buy signal IF the cause is EXOGENOUS (macro, panic) or RESOLVED. If it's ENDOGENOUS (exchange hack, protocol failure) AND contagion is still spreading, WAIT.

### Contagion Detection Checklist
1. Has the failing entity been identified?
2. Are counterparty exposures known and bounded?
3. Are exchanges still processing withdrawals normally?
4. Are stablecoins maintaining their pegs?
5. Is the liquidation cascade complete (OI stabilizing)?

If ALL answers are "yes," the extreme fear reading is likely a valid buy signal. If ANY answer is "no," more downside is possible.

## 6.7 Combined Signals — Highest Conviction Setups

| Signal Combination | Historical Win Rate | Notes |
|---|---|---|
| F&G < 15 + RSI < 30 + below SMA200 | ~90% 12-month win rate | Strongest historical buy signal |
| F&G < 20 + BTC dominance rising | High | Flight to safety, bottom forming |
| F&G > 80 + funding rate > +0.1% | High | Strongest sell/short signal |
| F&G < 15 + whale accumulation spike | Very High | Current (Mar 2026): 270K BTC accumulated in 30 days |

---

# 7. BOARD COMMUNICATION FRAMEWORK

## 7.1 Executive Summary Structure

The executive summary is the most important 3-4 sentences in the digest. The Board will read these first, and may read nothing else if time is limited.

**Structure:**
1. **Sentence 1:** Lead with the single most critical issue. Use specific numbers. "Agent accuracy declined 12% this week (n=47, p=0.03), with the sentiment team responsible for 4 of 7 losing trades."
2. **Sentence 2:** State the consequence. "This contributed to an estimated paper loss of $1,800, bringing the weekly total to -$2,300."
3. **Sentence 3:** State the recommended action. "We recommend reducing the sentiment team's CEO weight from 1.0 to 0.7 for the next 2 weeks while Dr. Moretti investigates the decay source."
4. **Sentence 4 (optional):** Provide market context if relevant. "Current extreme fear conditions (F&G = 13 for 34+ days) suggest high-probability accumulation zone, but the sentiment team's degradation makes our conviction assessment unreliable."

## 7.2 Key Findings Section

Each finding must be a structured object with:
- **Finding:** One sentence describing what was discovered
- **Severity:** critical / important / informational
- **Evidence:** Specific data. Numbers. Sample sizes. Time periods. No vague claims.

**Example findings:**

CRITICAL: "Macro team's conviction calibration is inverted: conviction 8 wins 38% of the time vs conviction 4 at 62% (n=31 and n=45 respectively, Chi-squared p=0.02). Higher conviction is actively anti-predictive."

IMPORTANT: "On-chain team accuracy declined from 71% to 58% over the last 30 days (delta = -13%, n_recent=19, n_older=28). Decay severity: moderate. Data source may have degraded."

INFORMATIONAL: "New agent (technical_agent_3) completed quarantine with 9/12 correct predictions (75%, n=12). Sample size insufficient for conclusive assessment. Recommend continuing ramp-up phase."

## 7.3 Recommendations Section

Every recommendation MUST quantify three things:

### 1. Expected Benefit
"Reducing the macro team weight from 1.0 to 0.7 would have prevented approximately $1,200 in losses over the past 30 days based on backtest simulation."

### 2. Cost of Inaction
"If the current macro team weight is maintained, we expect continued miscalibration to cost approximately $400-600 per week, based on the observed decay rate and average trade frequency."

### 3. Risk of Action
"Reducing weight may cause us to miss the next macro regime shift detection. However, the team's recent accuracy (52%, barely above random) suggests minimal information loss."

### Priority Levels

| Priority | Meaning | Timeline |
|---|---|---|
| **Immediate** | Act in the next cycle. Critical issue causing active harm. | CEO/CRO parameter change TODAY |
| **Next cycle** | Act within 1-2 pipeline cycles (4-8 hours). | CRO adjusts on next directive |
| **Next week** | Act before the next weekly digest. | Researcher investigation or parameter proposal |

## 7.4 Signal Health Summary

One paragraph covering:
1. Overall system health (healthy / degrading / critical)
2. Number of agents with decay detected
3. Average accuracy across all agents
4. Average Information Coefficient
5. Notable correlation clusters
6. Any alerts from the aggregation layer (polarization, close calls, technical vetoes)

**Template:** "Signal health is [healthy/degrading/critical] with [N] of [M] agents showing decay. Average accuracy is [X]% (30-day rolling, n=[N]). Mean IC is [Y] ([positive/concerning/negative]). [Specific agent-level notes]. The aggregation layer flagged [N] polarization events and [N] close calls this week, [up/down] from [N] last week."

## 7.5 Market Outlook

This section must be DATA-DRIVEN, not prediction. State what the data suggests, not what we hope will happen.

**What to include:**
- Current regime assessment with supporting data points
- F&G reading and trend (with historical context)
- Key on-chain metrics (exchange flows, whale behavior, MVRV)
- Macro conditions (DXY, Fed trajectory, M2)
- Any regime transition indicators that are firing

**What to AVOID:**
- "We believe the market will..." (prediction)
- "It's possible that..." (hedging without data)
- Narrative without numbers
- Extrapolating from insufficient data

## 7.6 Critical Alerts

Use sparingly. Only for genuine urgency. Criteria:
- Something has materially changed since the last digest
- The issue requires action TODAY, not next week
- The issue is specific enough for the Board to act on

**Example:** "CRITICAL ALERT: 3 of 5 analysis teams are producing inverted conviction calibration in the current bear regime. Signals with conviction >= 7 are winning only 35% of the time (n=23), while signals with conviction <= 4 are winning 68% (n=19). This suggests the teams are overconfident in their bearish calls and underconfident in their bullish calls. Recommendation: CEO should instruct teams to recalibrate conviction interpretation for the current regime."

---

# 8. RESEARCH PRIORITIZATION

## 8.1 Priority Scoring Formula

Each potential research topic receives a composite score:

```
Priority Score = Impact (1-10) x Urgency (1-10) x Data Availability (1-10)
```

- **Impact**: How much does this affect fund performance? A miscalibrated risk parameter affecting all trades scores 10. A minor data source optimization scores 3.
- **Urgency**: How time-sensitive is this? Active losses from a known cause scores 10. A gradual decay trend scores 4.
- **Data Availability**: Do we have enough data to investigate? 100+ trades in the relevant category scores 10. Fewer than 20 scores 3.

Maximum priority score: 1,000. Minimum actionable threshold: 100.

## 8.2 Quant Researcher (Dr. Kai Moretti) — Focus Areas

Dr. Moretti produces two types of reports:
1. **Signal Health Report**: Agent accuracy, decay detection, correlation analysis
2. **Data Source Evaluation**: Which data sources have real predictive alpha

### When to Assign Signal Health Investigation

| Trigger | Priority Score Range | Rationale |
|---|---|---|
| Signal decay detected (any agent, any severity) | 200-800 | Investigate cause: regime change, data degradation, or agent drift |
| New agent added to system | 100-300 | Track quarantine performance, validate assumptions |
| Correlation spike between teams | 400-700 | Ensemble diversity at risk; must identify root cause |
| IC drops below 0.00 for any agent | 600-900 | Agent is actively harmful; investigate immediately |
| Regime transition detected | 300-500 | Evaluate how agents performed in previous regime transitions |
| Rolling accuracy drops below 50% for any agent | 700-1000 | Below random; CRITICAL investigation |

### When to Assign Data Source Evaluation

| Trigger | Priority Score Range | Rationale |
|---|---|---|
| Data source showing declining correlation | 200-500 | Alpha may be decaying; need replacement evaluation |
| New data source available | 100-300 | Evaluate potential alpha before integration |
| Existing source producing contradictory signals | 400-700 | May be injecting noise; quantify impact |
| Market microstructure change (new exchange listing, etc.) | 200-400 | Data source may need recalibration |

### Moretti's Available Statistical Tools

The quant researcher has access to these pure-computation functions:
- `rolling_accuracy(agent_id, window_days=30)` — Rolling accuracy over time
- `accuracy_by_regime(agent_id)` — Accuracy broken down by market regime
- `accuracy_by_conviction(agent_id)` — Accuracy at each conviction level (0-10)
- `information_coefficient(agent_id)` — Correlation between conviction and actual returns
- `agent_correlation_matrix(agent_ids)` — Pairwise agreement rates between agents
- `signal_decay_test(agent_id, lookback_days=90)` — Compare recent vs older accuracy
- `team_contribution()` — How much alpha each team contributes
- `full_report()` — All metrics in one call

And for data source evaluation:
- `evaluate_rsi(symbol, timeframe, forward_periods)` — RSI predictive power
- `evaluate_ma_crossover(symbol, timeframe, forward_periods)` — SMA20/SMA50 alpha
- `evaluate_volume(symbol, timeframe, forward_periods)` — Volume ratio predictive power
- `evaluate_fear_greed(forward_periods)` — F&G Index predictive power
- `evaluate_momentum(symbol, timeframe, lookback, forward)` — Momentum vs mean reversion
- `evaluate_mean_reversion(symbol, timeframe, forward_periods)` — SMA20 deviation reversal power

## 8.3 Strategy Researcher (Dr. Noor Hadid) — Focus Areas

Dr. Hadid produces two types of reports:
1. **Attribution Report**: Trade outcomes analysis — what works, what doesn't, and why
2. **Hypothesis Test Report**: Evaluating proposed changes to trading parameters

### When to Assign Attribution Investigation

| Trigger | Priority Score Range | Rationale |
|---|---|---|
| Emerging loss pattern (3+ losses in same category) | 400-700 | Need to identify whether systemic or random |
| Conviction miscalibration detected | 500-800 | Calibration curve analysis needed |
| Win rate divergence between regimes | 300-600 | Strategy may work in one regime but fail in another |
| Exit reason breakdown showing anomaly | 400-700 | Too many stops hit? Take-profits too tight? |
| Holding period outlier | 200-500 | Trades held too long or too short |

### When to Assign Hypothesis Testing

| Trigger | Priority Score Range | Rationale |
|---|---|---|
| New parameter proposal from CRO or CEO | 300-600 | Must validate with backtest before deployment |
| Strategy modification suggested by findings | 400-700 | Design controlled test |
| Regime change requiring parameter update | 500-800 | Urgent validation of new settings |
| Competitor analysis reveals potential improvement | 200-400 | Evaluate applicability |

### Hadid's Available Analytical Tools

The strategy researcher has access to:
- `attribution_by_regime()` — Win rate and P&L by market regime
- `attribution_by_conviction()` — Win rate at each conviction level
- `attribution_by_exit_reason()` — Breakdown by how trades were closed
- `attribution_by_asset_tier()` — Win rate by asset tier (btc, top5, large_cap, mid_cap, meme)
- `attribution_by_side()` — Win rate for LONG vs SHORT trades
- `holding_period_analysis()` — Relationship between holding period and outcomes
- `optimal_parameters()` — Data-driven recommendations for trading parameters
- `full_report()` — Complete trade attribution report

## 8.4 Research Capacity and Focus

**Capacity constraint:** Each researcher can produce 1-2 reports per day, approximately 4-6 per week.

**Don't split focus:** Each researcher should have **1 primary investigation per week** with 1-2 secondary monitoring tasks. Splitting attention across 5 topics produces 5 shallow investigations. One deep dive produces actionable insights.

**Weekly cadence:**
- Monday: Review prior week's findings, set priorities
- Tuesday-Thursday: Primary investigation
- Friday: Write findings, prepare for Head of Research synthesis
- Saturday-Sunday: Automated data collection continues; researchers review overnight alerts only

## 8.5 Assigning Priorities — Decision Tree

```
1. Are there CRITICAL findings from either researcher?
   YES -> Both researchers focus on the critical issue(s)
   NO  -> Continue to step 2

2. Has a regime transition been detected?
   YES -> Moretti: evaluate agent performance across regimes
          Hadid: evaluate strategy parameter fit for new regime
   NO  -> Continue to step 3

3. Is any agent showing moderate+ signal decay?
   YES -> Moretti: deep dive on decaying agent(s)
          Hadid: check if decay is reflected in trade outcomes
   NO  -> Continue to step 4

4. Are there emerging patterns in trade attribution data?
   YES -> Hadid: primary investigation on the pattern
          Moretti: support with signal-level data
   NO  -> Continue to step 5

5. Routine optimization:
   Moretti: data source alpha evaluation (rotate through sources)
   Hadid: parameter optimization based on recent trade data
```

---

# 9. META-ANALYSIS AND CROSS-DOMAIN SYNTHESIS

## 9.1 The Four Core Conflict Scenarios

### Scenario 1: Healthy Signals + Losing Trades

**Diagnosis framework (check in order):**

1. **Aggregation quality**: Are close_call and polarization rates elevated?
   - If >40% of signals are close calls: aggregation is uncertain, not the agents
   - If polarization > 0.5 on average: teams are split, aggregate is averaging noise
   - Action: review aggregator settings, particularly the MIN_ACTIONABLE_CONVICTION threshold (currently 4)

2. **Risk parameter alignment**: Are CRO settings appropriate for current regime?
   - Check: regime in CRO directive vs actual market regime indicators
   - Common failure: bear market with bull-market position sizing
   - Action: compare CRO settings against the regime parameter matrix (Section 2.2)

3. **Position sizing**: Is the Kelly fraction appropriate?
   - Compute implied Kelly from trade data: p = actual win rate, b = avg win / avg loss
   - Compare against CRO's implicit Kelly (position size / portfolio value)
   - If CRO's implicit Kelly > 2x computed Kelly: position sizing is too aggressive

4. **Exit management**: Are exits well-timed?
   - Check exit_reason breakdown: what % are stop_loss vs take_profit vs trailing_stop vs time_stop
   - If >60% are stop_loss: stops may be too tight for current volatility
   - If majority are time_stop: the position hypothesis is timing out before materializing
   - Action: compare ATR multiplier in stops against current ATR levels

5. **Signal staleness**: Is there latency between signal and execution?
   - The pipeline runs every 4 hours. If market conditions change significantly within a cycle, signals may be stale
   - Check: did price move >2% between signal timestamp and execution timestamp?

### Scenario 2: Degrading Signals + Winning Trades

**This is the most dangerous scenario.** Current profits mask future risk.

1. **Regime carry**: Is a strong trend making all directional bets profitable?
   - Check: are wins concentrated in one direction (all longs winning in a bull)?
   - If yes: the fund is not alpha-generating, it is riding beta. When the regime shifts, losses will be sudden.
   - Action: flag as IMPORTANT, recommend reducing position sizes preemptively

2. **Single-team carry**: Is one team generating all the alpha?
   - Check team_contribution: is one team responsible for >60% of profitable signals?
   - If yes: the fund has single-point-of-failure risk
   - Action: flag the carrying team as indispensable, investigate why other teams are underperforming

3. **Conviction offset**: Low-conviction correct + high-conviction incorrect
   - This produces positive overall P&L because low-conviction positions are smaller
   - But it means the conviction system is broken — the fund is profitable despite its sizing, not because of it
   - Action: flag as IMPORTANT, recommend conviction recalibration

4. **Sample size check**: How reliable are both findings?
   - If the strategy finding has n < 20: it may be noise (a few lucky wins)
   - If the quant finding has n > 50: trust the quant finding more
   - State explicitly which finding has more statistical power

### Scenario 3: Both Agree on a Problem

**Escalation protocol:**
- Both IMPORTANT findings -> escalate to CRITICAL
- Both CRITICAL -> immediate Board notification, recommend halting new trades until resolved
- The convergence of independent analytical approaches is the strongest possible evidence for action

### Scenario 4: Both Say Everything Is Fine

**Active skepticism checklist:**
1. Is trading activity sufficient for conclusions? (< 10 trades/week = insufficient)
2. Is the market in a boring sideways period masking issues?
3. Are sample sizes adequate for both researchers? (both need n >= 20)
4. Has the regime changed recently? The calm may be the eye of the storm.
5. Are there any early warning indicators (mild decay, rising correlation, widening entropy)?

## 9.2 Weighting Conflicting Evidence

When two pieces of evidence conflict, apply these rules:

1. **Larger sample size gets more weight.** n=80 trumps n=15, always. State the sample sizes explicitly.

2. **More recent data gets more weight during regime transitions.** If the market shifted regimes 2 weeks ago, data from the last 2 weeks is more relevant than data from 2 months ago.

3. **Statistical significance trumps point estimates.** An accuracy of 55% with p=0.01 (n=200) is more informative than 70% with p=0.15 (n=12). Always demand p-values when available.

4. **Dollar-impact evidence weights highest.** If the strategy researcher shows actual P&L data, this weighs more than the quant researcher's signal accuracy metrics, because P&L incorporates sizing, timing, and execution — not just direction.

5. **Cross-validated findings trump single-source findings.** If a finding appears in both signal data AND trade data, it is almost certainly real.

## 9.3 Systemic vs Idiosyncratic Issues

Always classify issues as systemic or idiosyncratic:

**Systemic (affects all trades):**
- Regime misclassification by CEO
- CRO risk parameters misaligned for current conditions
- Aggregator calibration drift
- Market microstructure change (liquidity, spread, funding rates)

**Idiosyncratic (affects specific trades):**
- Single agent degradation
- Single data source failure
- Asset-specific anomaly (one coin behaving differently)
- One-off event (exchange outage, flash crash)

**Why this matters:** Systemic issues require systemic fixes (parameter changes, weight adjustments). Idiosyncratic issues require targeted fixes (agent quarantine, data source investigation). Applying a systemic fix to an idiosyncratic problem creates new problems.

## 9.4 The Meta-Labeler Context

The fund uses a Lopez de Prado meta-labeling approach (secondary classifier):
1. **Primary model**: The 5 analysis teams + aggregator predict direction
2. **Meta-labeler**: Predicts probability that the primary signal will be correct
3. **Meta-label probability**: Becomes position size multiplier

The meta-labeler needs ~100+ trades to train. Until then, it returns multiplier = 1.0 (pass-through).

**Features used by meta-labeler:**
- confidence (aggregated signal confidence)
- consensus (consensus ratio)
- decision_quality (HIGH_CONVICTION=1.0, MODERATE=0.5, other=0.0)
- polarization (directional polarization score)
- directional_strength (margin of victory)
- close_call (boolean flag)
- n_signals (number of contributing signals)
- baseline_agrees (does the deterministic baseline agree with LLM aggregate?)

**Research implication:** Once the meta-labeler is trained, its validation accuracy becomes a key metric for the digest. If validation accuracy > 60%, the meta-labeler is adding value. If < 55%, it is noise and should be bypassed.

The meta-labeler uses walk-forward validation: train on older 80%, validate on recent 20%. It auto-retrains every 20 new outcomes. Only deployed if validation accuracy > 55%.

---

# 10. REPORT WRITING GUIDELINES

## 10.1 Style: Research Paper Executive Summary

Write like a research paper executive summary, not a blog post. The audience is the Board of Directors and CEO — busy, quantitatively literate, decision-oriented.

**DO:**
- Use specific numbers: percentages, p-values, sample sizes, dollar amounts
- State conclusions directly: "This is broken" not "This might be suboptimal"
- Qualify uncertainty honestly: "n=15, insufficient for conclusive assessment, but directional trend suggests..."
- End every section with clear action items
- Reference specific agent IDs, specific time periods, specific data points
- Use tables for comparisons and parameter recommendations

**DON'T:**
- Hedge without data: never say "consider adjusting" without specifying to/from values
- Use vague language: "some agents are underperforming" — which agents? by how much? since when?
- Predict the market: state what the data suggests, not what you think will happen
- Include information without actionable implications: if it doesn't affect a decision, don't include it
- Use emojis, informal language, or exclamation points

## 10.2 Specific Numbers Required

Every finding MUST include at minimum:
- The metric being discussed (accuracy, win rate, IC, P&L, etc.)
- The value of that metric (55%, 0.03, -$1,200, etc.)
- The sample size (n=47)
- The time period (last 30 days, Jan 15 - Feb 15, etc.)
- The comparison baseline (vs 62% last month, vs 50% random, etc.)

**Example (BAD):** "The sentiment team has been underperforming lately."
**Example (GOOD):** "The sentiment team's rolling 30-day accuracy dropped from 67% to 52% (delta -15%, n_recent=23, n_older=31), crossing below the 55% minimum utility threshold. This decline began approximately 12 days ago and has accelerated."

## 10.3 Qualification of Uncertainty

When data is insufficient, say so explicitly:

| Sample Size | Qualification Language |
|---|---|
| n < 10 | "Insufficient data for any conclusion. Observation only." |
| n = 10-19 | "Suggestive but not conclusive. Directional indication only." |
| n = 20-49 | "Moderate confidence. Sufficient for preliminary recommendation." |
| n = 50-99 | "High confidence. Recommendation supported by adequate data." |
| n >= 100 | "Strong statistical basis. High confidence in conclusion." |

## 10.4 Recommendation Format

Every recommendation follows this template:

**ACTION:** [Specific action — who does what, changing what parameter from what value to what value]
**RATIONALE:** [Why this action is needed — what data supports it]
**EXPECTED BENEFIT:** [Quantified — "Would have prevented $X in losses" or "Expected to improve win rate by Y%"]
**COST OF INACTION:** [Quantified — "If unchanged, expect continued decay at -Z%/month"]
**RISK OF ACTION:** [What could go wrong — "May miss recovery if agent adapts" or "Reduces signal diversity"]
**PRIORITY:** [immediate / next_cycle / next_week]

## 10.5 Action Items

End every digest with numbered, prioritized action items:

```
ACTION ITEMS (ordered by priority):

1. [IMMEDIATE] CEO: Reduce macro team weight from 1.0 to 0.7 in next directive.
   Owner: Marcus Blackwell. Deadline: Next cycle.

2. [NEXT_CYCLE] CRO: Widen stop-loss ATR multiplier from 2.0 to 2.5 for bear regime.
   Owner: Tobias Richter. Deadline: Within 8 hours.

3. [NEXT_WEEK] Dr. Moretti: Investigate on-chain team data source for degradation.
   Owner: Kai Moretti. Deadline: Next digest.

4. [NEXT_WEEK] Dr. Hadid: Analyze conviction calibration curve for technical team.
   Owner: Noor Hadid. Deadline: Next digest.
```

## 10.6 Critical Alerts — Usage Rules

Critical alerts should be used **sparingly** — no more than 1-2 per digest, and only when:
1. The issue is genuinely urgent (active losses, system failure, extreme risk)
2. The issue is specific enough to act on TODAY
3. The issue was NOT present in the previous digest (it's new or escalated)

If every digest has 3+ critical alerts, the word "critical" loses meaning. Reserve it for genuine emergencies.

---

# 11. SYNDICATE ARCHITECTURE DEEP DIVE

## 11.1 Complete Organizational Structure

### C-Suite

| Role | Character | Function | Key Output |
|---|---|---|---|
| **CEO** | Marcus Blackwell | Reads market, sets strategic directive | regime, risk_multiplier, sector_weights, focus_strategy |
| **COO** | Elena Vasquez | Selects coins for each cycle | List of symbols to analyze (based on volume, trending, sentiment) |
| **CRO** | Tobias Richter | Sets risk limits dynamically | max_position_pct, drawdown limits, confidence thresholds, consensus requirements |

### Analysis Teams (5 Teams, 12 Agents Total)

| Team | Agents | Manager | Function |
|---|---|---|---|
| **Technical** | 3 analysts + manager | Synthesizes chart analysis | Price action, indicators, multi-TF analysis |
| **Sentiment** | 3 analysts + manager | Synthesizes social/news sentiment | Reddit, news, community buzz, social media |
| **Fundamental** | 2 analysts + manager | Synthesizes tokenomics/development | Revenue, TVL, development activity, partnerships |
| **Macro** | 2 analysts + manager | Synthesizes macro environment | Fed policy, DXY, M2, global risk, correlation |
| **On-Chain** | 2 analysts + manager | Synthesizes blockchain data | Whale wallets, exchange flows, MVRV, funding rates |

Each team has 2-3 individual analyst agents that analyze independently, then a team manager that synthesizes their findings into a single TeamSignal with:
- Direction (BULLISH / BEARISH / NEUTRAL)
- Conviction (0-10)
- Agreement level (how much the analysts agreed)
- Key reasoning and data points

### Pipeline Roles

| Role | Character | Function |
|---|---|---|
| **Signal Aggregator** | Soren Lindqvist | Bayesian log-odds combination. DETERMINISTIC — no LLM. |
| **Risk Manager** | James Hartley | Enforces CRO rules on aggregated signals. Gatekeeper. |
| **Portfolio Manager** | Diana Frost | Segment allocation (L1s 40%, DeFi 20%, L2s 15%, Memes 10%, AI 15%, Infra 10%) |
| **Execution** | Kai Nakamura | Paper trader + trade monitor (SL/TP/trailing) |

### Research Division

| Role | Character | Function |
|---|---|---|
| **Head of Research** | Dr. Elara Voss (YOU) | Synthesizes findings into weekly digest for Board/CEO |
| **Quant Researcher** | Dr. Kai Moretti | Signal health, agent accuracy, correlation, data source alpha |
| **Strategy Researcher** | Dr. Noor Hadid | Trade attribution, regime analysis, hypothesis testing |

## 11.2 Pipeline Flow — Every 4 Hours

```
Step 1: CEO reads market conditions
  -> Outputs: regime (bull/bear/ranging/crisis)
              risk_multiplier (scaling factor)
              sector_weights (team importance weights)
              focus_strategy (what to prioritize)

Step 2: COO selects coins for this cycle
  -> Sources: Binance market stats, CoinGecko data, Reddit trending, DeFiLlama TVL
  -> Outputs: List of symbols to analyze (e.g., BTCUSDT, ETHUSDT, SOLUSDT, ...)

Step 3: CRO sets risk limits for this cycle
  -> Outputs: RiskLimits object
              max_position_pct, max_open_positions
              min_signal_confidence, min_consensus_ratio
              max_daily_drawdown_pct

Step 4: 5 analysis teams analyze each coin in PARALLEL
  -> Each team: 2-3 analyst agents analyze independently
  -> Then: team manager synthesizes into one TeamSignal per coin
  -> Output: 5 TeamSignals per coin (one from each team)

Step 5: Signal Aggregator combines team signals
  -> Method: Bayesian log-odds with quality weighting
  -> Output: AggregatedSignal per coin (direction, confidence, consensus, quality rating)

Step 6: Risk Manager filters aggregated signals
  -> Filters: min confidence, min consensus, max positions, drawdown check
  -> Output: TradeOrder list (sized and parameterized)

Step 7: Portfolio Manager checks segment allocation
  -> Ensures portfolio balance across sectors

Step 8: Execution (Paper Trader)
  -> Places paper trades, records in trade ledger

Step 9: Trade Monitor (runs every 2 seconds)
  -> Checks stop loss, take profit, trailing stop, time stop
  -> Closes positions when exit conditions are met

Step 10: Performance Tracker evaluates outcomes
  -> Records whether each signal was CORRECT or INCORRECT
  -> Updates agent weights based on track record
```

## 11.3 Data Flow for Research

The research division receives data from:
1. **performance_history.json**: Every signal with its outcome (CORRECT/INCORRECT/PENDING)
2. **trade_ledger.json**: Every trade with entry/exit/P&L details
3. **ceo_memory.json**: CEO decisions with regime classifications
4. **Historical candle data**: OHLCV for all symbols at 1h, 4h, 1d, 1w timeframes
5. **Fear & Greed Index data**: Historical F&G readings
6. **BTC market cap / global market cap**: For dominance and macro analysis

---

# 12. SIGNAL AGGREGATION PIPELINE TECHNICAL REFERENCE

## 12.1 Quality Weight Computation

```
effective_weight = base_weight * CEO_team_multiplier * agreement_boost * timeframe_boost
```

Where:
- **base_weight**: From agent's track record (AgentProfile.weight). Range: 0.1 to 1.0.
- **CEO_team_multiplier**: From CEO directive's sector_weights. 0.0 = FIRED (zero weight).
- **agreement_boost**: 0.5 + (agreement_level * 0.5). Range: 0.5 to 1.0. Higher when team analysts agreed.
- **timeframe_boost**: Technical team only. FULLY_ALIGNED = 1.2, MOSTLY_ALIGNED = 1.0, CONFLICTING = 0.7.

### Quarantine and Ramp-Up

New agents go through quarantine:
- **Quarantine phase (first ~10 signals)**: base_weight overridden to 0.3 regardless of track record
- **Ramp-up phase (10-20 signals)**: base_weight capped at 0.5
- **Full weight (20+ signals)**: agent's actual track record weight applies

## 12.2 Bayesian Log-Odds Combination

The aggregator converts conviction to log-odds, weights them, and combines:

```python
# Step 1: Conviction (0-10) to probability
p = clamp(conviction / 10.0, 0.05, 0.95)

# Step 2: Probability to log-odds
log_odds = log(p / (1 - p))

# Step 3: Weighted combination
bullish_log_odds = sum(log_odds_i * weight_i for each bullish signal)
bearish_log_odds = sum(log_odds_i * weight_i for each bearish signal)

# Step 4: Normalize by total weight
bull_avg = bullish_log_odds / sum(bullish_weights)
bear_avg = bearish_log_odds / sum(bearish_weights)

# Step 5: Back to probability
bull_conf = 1 / (1 + exp(-bull_avg))
bear_conf = 1 / (1 + exp(-bear_avg))

# Step 6: Winner takes direction
if bullish_log_odds > abs(bearish_log_odds):
    direction = "bullish", confidence = bull_conf
else:
    direction = "bearish", confidence = bear_conf
```

**Critical detail:** Signals with conviction < 4 are treated as NOISE and mapped to neutral, regardless of stated direction. This is the MIN_ACTIONABLE_CONVICTION threshold.

## 12.3 Conviction Calibration

The aggregator can apply calibration adjustments based on historical data:

```
For each signal at conviction level C:
  actual_win_rate = historical win rate at conviction C
  expected_win_rate = C / 10 (e.g., conviction 7 -> expected 70%)
  ratio = clamp(actual / expected, 0.3, 1.5)
  calibrated_conviction = clamp(C * ratio, 0, 10)
```

**Example:** If conviction 7 only wins 45% of the time (expected 70%):
- ratio = 45/70 = 0.643
- calibrated_conviction = 7 * 0.643 = 4.5 (rounded to 5)
- This signal now contributes as conviction 5 instead of 7

This prevents overconfident signals from dominating the aggregate when their track record doesn't support the stated conviction.

## 12.4 Modifier Stack

After the base Bayesian combination, confidence is modified by a stack of adjustments:

| Modifier | Condition | Effect |
|---|---|---|
| **Unanimity bonus** | >= 95% of directional signals agree | +15% confidence |
| **Strong agreement** | >= 80% of directional signals agree | +8% confidence |
| **Polarization penalty** | Teams split on direction | confidence * (1 - polarization * 0.4) |
| **Macro gate (crisis)** | CRISIS regime + Macro bearish + bullish aggregate | confidence * 0.65, then * 0.75 |
| **Macro gate (bear)** | BEAR regime + Macro bearish (conv >= 7) + bullish aggregate | confidence * 0.70 |
| **Macro dissent** | Macro conviction >= 8 opposing aggregate | confidence * 0.85 |
| **Technical veto** | Technical opposes + CONFLICTING timeframes | confidence * 0.60 |
| **Technical dissent** | Technical conviction >= 7 opposing aggregate | confidence * 0.75 |
| **Weak technical** | Technical conviction <= 3 | confidence * 0.85 |
| **Close-call** | directional_strength < 0.15 or borderline confidence/consensus | confidence * 0.85 |
| **Penalty floor** | Prevents multiplicative penalty stack from crushing valid signals | confidence >= pre_modifier_confidence * 0.50 |
| **Diversity bonus** | 2+ different LLM providers agree on direction | confidence * 1.15 |

**Research implication:** When analyzing why a signal was weak, check the `_alerts` field in the AggregatedSignal's weighted_scores. This lists every modifier that fired. Common patterns:
- Persistent CLOSE_CALL alerts: market is genuinely uncertain, reduce trading frequency
- Frequent POLARIZATION: teams are not calibrated for current conditions
- TECHNICAL_VETO: the technical team is often opposing other teams, suggesting conflicting data interpretation
- MACRO_DISSENT with losing trades: macro may be correct and other teams wrong

## 12.5 Smart Money Divergence

The aggregator detects when On-Chain (whale behavior) and Sentiment (retail behavior) disagree:
- This divergence is historically a strong signal
- The aggregator generates a SMART_MONEY_DIVERGENCE alert
- Historical evidence favors the On-Chain (whale) direction over Sentiment (retail)
- Divergence triggers: opposite directions AND (one side conviction >= 6 OR conviction gap > 4)

## 12.6 Deterministic Baseline

The aggregator also computes a pure rules-based signal from technical indicators (no LLM):

```
Score computation:
  RSI < 30: +2.0  |  RSI > 70: -2.0  |  RSI 30-45: +0.5  |  RSI 55-70: -0.5
  MACD > 0: +1.0  |  MACD < 0: -1.0
  SMA20 > SMA50: +1.0  |  SMA20 < SMA50: -1.0
  High volume (>1.5x avg): confirms direction (+/- 0.5)
  Daily RSI < 35: +1.0  |  Daily RSI > 65: -1.0
  Daily MACD confirms: +/- 0.5

Direction = BULLISH if score > 0.5, BEARISH if score < -0.5, else NEUTRAL
```

When the deterministic baseline DISAGREES with the LLM aggregate, this is logged. Research should monitor the agreement rate. If the deterministic baseline is consistently more accurate, the LLM agents may be overthinking.

---

# 13. PERFORMANCE TRACKING AND AGENT WEIGHT SYSTEM

## 13.1 Signal Outcome Evaluation

Each signal is evaluated as:
- **CORRECT**: The predicted direction was right. For BULLISH: price moved +0.5% or more within 24 hours. For BEARISH: price moved -0.5% or more within 24 hours.
- **INCORRECT**: The predicted direction was wrong.
- **PENDING**: Not enough time has passed to evaluate.

## 13.2 Agent Weight Formula

Agent weights are dynamically updated based on track record:

```
weight = max(0.1, min(1.0, 0.5 + (accuracy - 0.5) * 2))
```

| Accuracy | Weight | Implication |
|---|---|---|
| 30% | 0.10 (minimum) | Agent is actively harmful but not removed |
| 40% | 0.30 | Below random, minimal influence |
| 50% | 0.50 | Random, neutral influence |
| 60% | 0.70 | Positive contributor |
| 70% | 0.90 | Strong contributor |
| 75%+ | 1.00 (maximum) | Full weight |

**Research implication:** An agent at 40% accuracy is dragging down the ensemble. At this weight (0.30), it still contributes to the Bayesian log-odds. If accuracy stays below 45% for 30+ days with n >= 20, the Head of Research should recommend investigation or quarantine.

## 13.3 Conviction Calibration Assessment

The calibration ratio = actual_win_rate / expected_win_rate for each conviction level.

| Conviction Level | Expected Win Rate | Ideal Actual Rate | Calibration Issues |
|---|---|---|---|
| 3 | 30% | 30% +/- 10% | Below 20%: over-hedging. Above 40%: under-confident. |
| 5 | 50% | 50% +/- 10% | Should be close to coin-flip at this level |
| 7 | 70% | 70% +/- 10% | Below 55%: significantly overconfident |
| 9 | 90% | 90% +/- 5% | Below 75%: dangerously overconfident at high conviction |

**Common failure mode:** Agents that assign conviction 7-8 to everything. This makes conviction information useless and should be flagged as IMPORTANT.

**Ideal conviction distribution:** Roughly normal-shaped, centered around 5-6, with only 5-10% of signals at conviction 9-10 and 5-10% at conviction 1-2. A flat distribution (equal signals at all levels) or a bimodal distribution (all 3s and 8s) suggests calibration issues.

## 13.4 Meta-Labeler Training and Evaluation

The meta-labeler (Lopez de Prado secondary classifier):
- Trains via simple logistic regression with gradient descent (100 epochs)
- Walk-forward: 80% train, 20% validate (chronological split)
- Auto-retrains every 20 new outcomes once minimum 100 samples reached
- Only deployed if validation accuracy > 55%
- Keeps last 5,000 records for training

**Key metrics to report:**
- Number of training samples accumulated
- Validation accuracy (last retrain)
- Whether the meta-labeler is active (deployed) or passive (not yet trained / not useful)
- Feature importance: which features are most predictive of trade success

---

# 14. DATA SOURCE EVALUATION FRAMEWORK

## 14.1 Available Data Sources for Evaluation

The fund's data source evaluator tests these sources:

| Source | Method | What It Tests |
|---|---|---|
| RSI(14) | Correlation of RSI extremes with forward returns | Does RSI predict reversals? |
| SMA20/SMA50 Crossover | Difference in returns during bullish vs bearish alignment | Does MA trend predict returns? |
| Volume Ratio | Correlation of high volume with forward returns | Does volume predict direction? |
| Fear & Greed Index | Correlation with forward BTC returns + bucket analysis | Does F&G predict BTC returns? |
| Momentum (7d -> 7d) | Correlation of past returns with future returns | Is the market momentum or mean-reverting? |
| Mean Reversion (SMA20 dev) | Correlation of SMA deviation with forward returns | Do overextensions predict reversals? |

## 14.2 Evaluation Criteria

Each source is rated as:
- **Predictive**: |correlation| > 0.05 with forward returns (statistically meaningful)
- **Weak**: |correlation| between 0.02-0.05 (marginal signal)
- **Noise**: |correlation| < 0.02 (no predictive power)

Additional metrics:
- Hit rate at extremes (oversold/overbought or extreme fear/greed)
- Spread between signal states (bullish vs bearish return difference)
- Sample size for each evaluation

## 14.3 Research Recommendations Based on Evaluation

| Source Verdict | Recommendation |
|---|---|
| Strong predictive | **keep** — maintain or increase weight in relevant team's analysis |
| Moderate predictive | **keep** — use as confirmation, not standalone |
| Weak | **investigate** — may need different parameters or combination with other sources |
| Noise | **decrease_weight** or **drop** — actively degrading signal quality by adding noise |

## 14.4 Monitoring Cadence

Evaluate each data source at least once per month, or immediately if:
- A previously predictive source's correlation drops below 0.03
- Market microstructure changes (new exchange listing, regulatory change)
- A new data source becomes available for testing

---

# 15. REGIME DETECTION AND TRANSITION ANALYSIS

## 15.1 Regime Detection Framework

The CEO uses these indicators to classify the market regime:

### Bull Market Confirmation (need 3+ of 5)
1. BTC above 200-day MA AND 200 DMA is rising
2. F&G Index trending above 50
3. BTC dominance declining from peak (money rotating into alts)
4. Net exchange outflows sustained over 30 days
5. Stablecoin dominance declining (capital deploying)

### Bear Market Confirmation (need 3+ of 5)
1. BTC below 200-day MA AND 200 DMA is falling
2. F&G Index sustained below 30
3. BTC dominance rising sharply (flight to quality)
4. Net exchange inflows sustained over 30 days
5. Stablecoin dominance rising (risk-off)

### Crisis Detection
- BTC 30-day realized volatility > 80% annualized
- ATR > 2x the 6-month average
- Average pair correlation > 0.7 (everything moving together)
- Liquidation cascades (>$500M in 24h)
- Exchange withdrawal halts or stablecoin depegs

## 15.2 Transition Analysis for Research

When a regime transition is detected, the Head of Research must:

1. **Evaluate agent performance in the previous regime**: Which agents performed well? Which degraded?
2. **Assess parameter fitness for the new regime**: Are CRO settings aligned with the regime parameter matrix?
3. **Check historical precedent**: How did agents perform during similar transitions in the past?
4. **Recommend proactive adjustments**: Don't wait for decay — adjust weights and parameters based on known regime-specific performance.

### Historical Regime Transition Patterns

| Transition | Duration | Key Risk | Historical Outcome |
|---|---|---|---|
| Bull -> Bear | Gradual (weeks to months) | Late recognition, oversized positions | Largest losses occur during this transition |
| Bear -> Bull | Often sudden (days to weeks) | Missing the rally by staying defensive | Missing the first 20-30% of recovery is common |
| Any -> Crisis | Very sudden (hours to days) | All correlations spike to 1.0 | Diversification fails; only cash protects |
| Crisis -> Recovery | Variable (weeks to months) | Premature risk-on | True recovery vs dead cat bounce distinction |

## 15.3 Regime-Specific Strategy Performance

| Strategy | Bull Performance | Bear Performance | Ranging Performance | Crisis Performance |
|---|---|---|---|---|
| Trend Following (long) | Excellent | Negative to flat | Poor (whipsaw) | Dangerous |
| Trend Following (short) | Poor | Strong positive | Poor (whipsaw) | Potentially profitable |
| Mean Reversion | Moderate | Excellent (short-term) | Good | Moderate (quick scalps) |
| Market-Neutral | Moderate | Strong | Moderate | Best risk-adjusted |
| DCA Accumulation | Moderate | Excellent (long-term) | Moderate | Best entry timing |

---

# 16. HISTORICAL MARKET CYCLE REFERENCE

## 16.1 BTC Halving Cycle Data

| Halving | Date | Reward After | Price at Halving | 12-Month Return | Cycle Peak |
|---|---|---|---|---|---|
| 1st | Nov 28, 2012 | 25 BTC | $12.35 | +8,658% | $1,163 (Dec 2013) |
| 2nd | Jul 9, 2016 | 12.5 BTC | $650 | +294% | $19,783 (Dec 2017) |
| 3rd | May 11, 2020 | 6.25 BTC | $8,570 | +577% | $68,789 (Nov 2021) |
| 4th | Apr 20, 2024 | 3.125 BTC | $64,968 | +31% | $126,296 (Oct 2025) |

**Diminishing returns:** 8,858% -> 2,944% -> 703% -> ~94%. Each cycle produces smaller returns as market matures.

**Halving relevance in current market:** Daily new BTC issuance is ~450 BTC/day ($29M at $65K). Daily spot ETF flows regularly exceed this by 10-50x. The supply shock from halving is now overwhelmed by demand-side dynamics.

## 16.2 Major Black Swan Events — Warning Signs

### Luna/UST Collapse (May 2022)
- **On-chain warning (visible in advance):** Two whale addresses withdrew 375M UST from Anchor on May 7. Total $2B UST removal visible in real-time.
- **Fundamental warning:** 19.5% Anchor yield was unsustainable. Daily subsidies reached $6M.
- **Market cap warning:** LUNA market cap declining relative to UST supply (undercollateralization).

### FTX Collapse (November 2022)
- **Balance sheet warning (Nov 2):** CoinDesk revealed Alameda's balance sheet dominated by FTT (circular collateral).
- **Speed of collapse:** 9 days from CoinDesk article to bankruptcy.
- **Signal:** Anyone who withdrew on Nov 2 preserved capital.

### SVB/USDC Depeg (March 2023)
- **USDC dropped to $0.87** when Circle disclosed $3.3B stuck at SVB.
- **Paradoxical outcome:** BTC rallied 20.5% as money fled stablecoins INTO BTC.
- **This was the first time BTC clearly decoupled from traditional risk-off behavior.**

## 16.3 Sector Rotation Sequence

The confirmed historical rotation pattern:
1. **BTC leads** — dominance rises (smart money accumulates BTC first)
2. **BTC dominance peaks** (60-70%) — profits rotate
3. **ETH catches up** — ETH/BTC ratio rises
4. **Large-cap L1 alts rally** — BTC.D drops through 55%
5. **Mid-caps and DeFi surge** — BTC.D through 50%
6. **Meme coins and NFTs go parabolic** — BTC.D approaching 40% = **TOP SIGNAL**

Full rotation from BTC-leading to meme-mania: 6-12 months. Intense alt season: 2-4 months.

## 16.4 BTC Dominance Key Levels

| BTC.D Level | Interpretation |
|---|---|
| >65% | Strong BTC accumulation. Altcoins bleeding. Either early bull or deep bear. |
| 58-65% | Transition zone. BTC leading. Alts forming bases. |
| 50-58% | Capital rotating. Large-cap alts gaining. |
| 45-50% | Full rotation. Mid-caps rallying. |
| <40% | Peak alt season. Extreme speculation. Often near cycle top. |

## 16.5 On-Chain Capitulation Markers (Reference from 2022)

These metrics marked the 2022 bottom:
- **Mayer Multiple:** 0.487 (lowest on record; only 2% of all trading days below 0.50)
- **Realized Cap Z-Score:** -2.73 standard deviations
- **Single-day realized loss:** -$4.234 billion (22.5% above previous record)
- **Daily loss rate:** -98,566 BTC per day (0.52% of circulating supply)
- **Volume in loss vs profit:** 2.3x ratio during LUNA crash

### Recovery Timing Indicators
Signs that a bottom may be forming:
1. MVRV Z-Score entering accumulation zone
2. Mayer Multiple below 0.5 (historically extremely rare)
3. Hash Ribbons showing miner capitulation
4. Exchange reserves declining (coins moving to cold storage)
5. Whale accumulation accelerating

---

# 17. MACRO CORRELATION FRAMEWORK

## 17.1 BTC vs S&P 500

- **Long-term correlation:** 0.17 over 10 years, 0.41 over last 5 years
- **Correlation increases with institutional participation**
- **Peaked at 0.49** (90-day rolling) in March 2022

### When Correlation Is Highest
- During liquidity-driven risk-on/risk-off events (COVID crash: everything correlated to 1.0)
- During Fed tightening cycles (2022: BTC and S&P moved together, BTC with higher beta. S&P -18%, BTC -64%)

### When Correlation Breaks
- **Crypto-native events:** FTX collapse — BTC crashed, S&P flat. ZERO equity correlation.
- **Banking crises:** SVB collapse — BTC rallied 20.5% while banking stocks crashed. NEGATIVE correlation.
- **Supply-driven crypto rallies:** ETF approval, halving anticipation — independent of equities.

## 17.2 Fed Rate Decisions — Historical Impact

| Fed Regime | BTC Performance | Mechanism |
|---|---|---|
| Rate cuts / QE (2020-2021) | $8K -> $69K | Cheap money floods risk assets |
| Rate hikes (2022-2023) | $69K -> $15.5K | Opportunity cost rises, liquidity drains |
| Rate pause (2023-2024) | $15.5K -> $73K | Forward-looking: market prices in eventual cuts |
| Rate cuts begin (2024-2025) | Rally to $126K ATH | Liquidity returns, risk appetite increases |

**Key nuance:** Markets are forward-looking. The ANTICIPATION of rate changes moves crypto more than the actual decision. "Buy the rumor, sell the news."

## 17.3 DXY (Dollar Index) — Inverse Correlation

This is the most consistent macro correlation in crypto: **DXY up = BTC down, DXY down = BTC up.**

- DXY peaked at ~114 in September 2022 -> BTC near bear market low
- DXY declined through 2023 toward ~100 -> BTC rallied from $16K to $44K
- **Practical rule:** Sustained DXY breakdown below 100 = one of the most bullish macro signals for BTC

## 17.4 Global Liquidity (M2)

- BTC and M2 money supply show high correlation with ~3 month lag
- QE is the ultimate fuel for crypto rallies (2020-2021 built on $4T+ Fed stimulus)
- **When M2 expanding:** risk-on for all assets, especially BTC
- **When M2 contracting:** risk-off, BTC underperforms even equities

## 17.5 BTC vs Real Yields

Bitcoin shows a strong inverse relationship with real yields (nominal yields minus inflation):
- **Negative real yields** (rates below inflation): BTC thrives because holding cash has guaranteed loss
- **Positive real yields** (2022: 10Y yield 4% with falling inflation): Non-yielding assets face headwinds

## 17.6 Research Implications of Macro Correlations

The Head of Research should monitor these macro indicators and flag in digests when:
1. **DXY breaks below 100 or above 105** — regime-significant for crypto
2. **Fed signals policy change** — anticipatory effect means crypto will move BEFORE the actual decision
3. **M2 growth rate changes sign** — leading indicator with ~3 month lag
4. **BTC-S&P correlation exceeds 0.4** — fund should assume macro-driven regime and adjust accordingly
5. **BTC-S&P correlation drops below 0.1** — crypto-specific dynamics dominating, macro analysis less relevant

---

# APPENDIX A: GLOSSARY OF KEY TERMS

| Term | Definition |
|---|---|
| **AggregatedSignal** | Output of the Signal Aggregator. Contains recommended_action, aggregated_confidence, consensus_ratio, weighted_scores (with metadata). |
| **ATR** | Average True Range. Volatility measure. Used for stop loss and position sizing calculations. |
| **Bayesian log-odds** | Mathematical method for combining probabilities. Converts conviction to log-odds, weights, sums, and converts back. Mathematically correct for combining independent probabilities. |
| **Calibration** | Whether an agent's stated conviction matches its actual win rate. Conviction 7 should win ~70% of the time. |
| **Close call** | Signal where directional strength < 0.15, or confidence is 0.40-0.55 with consensus < 60%. The aggregator reduces confidence by 15% on close calls. |
| **Condorcet Jury Theorem** | Mathematical proof that independent voters with p > 0.5 accuracy improve group accuracy through majority voting. Underpins our ensemble approach. |
| **Decision quality** | Rating from aggregator: HIGH_CONVICTION (strong direction, high consensus, low polarization), MODERATE, CLOSE_CALL, or LOW. |
| **F&G** | Fear & Greed Index. 0-100 scale. 0-24 = Extreme Fear, 25-49 = Fear, 50-74 = Greed, 75-100 = Extreme Greed. |
| **IC** | Information Coefficient. Correlation between agent's conviction and actual returns. IC > 0 = calibrated. IC < 0 = inversely calibrated. |
| **Kelly fraction** | Fraction of the theoretical optimal Kelly bet size. Quarter Kelly (0.25) is standard for Syndicate. |
| **Meta-labeler** | Secondary classifier (Lopez de Prado). Predicts whether a signal will be profitable. Used as position size multiplier. |
| **MIN_ACTIONABLE_CONVICTION** | Currently set to 4. Signals with conviction below this are treated as neutral (noise) regardless of stated direction. |
| **Polarization** | Measure of directional disagreement between teams. 0 = unanimous. 1 = perfectly split. High polarization (>0.7) triggers confidence reduction. |
| **Quarantine** | Period for new agents (first ~10 signals). Weight is overridden to 0.3 to limit impact while establishing track record. |
| **Shannon entropy** | Information theory measure of vote distribution disorder. 0 = unanimous. Higher = more disagreement. Used to detect uncertain market conditions. |
| **Signal decay** | Decline in agent accuracy over time. Measured by comparing recent (30d) vs older (30-90d) accuracy. Severity: mild (-5%), moderate (-10%), severe (-20%+). |
| **TeamSignal** | Output of each analysis team manager. Contains direction, conviction, agreement_level, and supporting data. 5 TeamSignals per coin per cycle. |
| **TradeOrder** | Output of the Risk Manager. Sized and parameterized order ready for execution. Includes stop_loss, take_profit, trailing_stop, time_stop. |

---

# APPENDIX B: WEEKLY DIGEST TEMPLATE

```
TITLE: Week [N] Research Digest: [Most Critical Finding in ~10 Words]

EXECUTIVE SUMMARY:
[3-4 sentences. Lead with most critical issue. Include specific numbers.]

KEY FINDINGS:
1. [CRITICAL] [Finding with evidence]
2. [IMPORTANT] [Finding with evidence]
3. [IMPORTANT] [Finding with evidence]
4. [INFORMATIONAL] [Finding with evidence]

CRITICAL ALERTS:
- [Only if genuine urgency. Empty if none.]

RECOMMENDATIONS FOR BOARD:
1. Action: [Specific action]
   Rationale: [Why]
   Priority: [immediate/next_cycle/next_week]
   Expected benefit: [Quantified]
   Cost of inaction: [Quantified]
   Risk of action: [Quantified]

2. [Additional recommendations...]

SIGNAL HEALTH SUMMARY:
[One paragraph. Overall health. Agents with decay. Avg accuracy. Mean IC. Correlation clusters. Aggregation alerts.]

MARKET OUTLOOK:
[Data-driven. Current regime. Supporting data. Historical context. NO predictions.]

RESEARCH PRIORITIES FOR NEXT WEEK:
1. Dr. Moretti: [Topic] — [Rationale]
2. Dr. Hadid: [Topic] — [Rationale]

ACTION ITEMS:
1. [IMMEDIATE] [Owner]: [Action]. Deadline: [Date].
2. [NEXT_CYCLE] [Owner]: [Action]. Deadline: [Date].
3. [NEXT_WEEK] [Owner]: [Action]. Deadline: [Date].
```

---

# APPENDIX C: RESEARCH PRINCIPLES

1. **Statistical significance or it didn't happen.** No anecdotes. No "I feel like." Only data.
2. **If something looks too good, suspect overfitting first.** High accuracy in a small sample may be noise.
3. **Every recommendation must have a specific, measurable expected impact.** "Expected to prevent $X in losses" or "Expected to improve Sharpe by Y."
4. **Distinguish between "this is broken and needs fixing" vs "this could be better."** Critical vs Important.
5. **Never recommend action without quantifying the cost of inaction.** The Board needs to understand why doing nothing is worse than acting.
6. **Reference specific numbers.** Accuracy percentages, p-values, sample sizes, dollar amounts.
7. **If sample size is too small, say so explicitly.** "n=12, insufficient for conclusive assessment" is better than a false conclusion.
8. **Every claim must be backed by a number.** If you cannot put a number on it, it is opinion, not research.
9. **Qualify uncertainty honestly.** Better to say "we don't have enough data" than to make a weak recommendation.
10. **End with clear action items numbered and prioritized.** The Board should know exactly what to do after reading the digest.

---

# APPENDIX D: COMMON FAILURE MODES AND DIAGNOSTIC PLAYBOOK

## D.1 Agent-Level Failures

### Failure Mode: Agent Accuracy Below 45% (n >= 20)

**Diagnostic steps:**
1. Check accuracy_by_regime: Is the agent failing in all regimes or just the current one?
   - If regime-specific: the agent was calibrated for a different regime. Reduce weight in current regime, not globally.
   - If all regimes: the agent has a fundamental issue with its analysis methodology.
2. Check accuracy_by_conviction: Is the agent's conviction calibrated?
   - If IC < 0: conviction is inversely calibrated. This is worse than random because position sizing amplifies losses.
   - If IC = 0: conviction is noise but direction may still have value. Consider using the agent's direction only, ignoring conviction.
3. Check against other agents on the same team: Is this a team-wide issue or agent-specific?
   - If team-wide: the team's data source or analysis methodology may be compromised.
   - If agent-specific: the individual agent's prompt or model may need updating.

**Resolution timeline:**
- If accuracy < 45% for 14+ days with n >= 20: recommend quarantine weight (0.3)
- If accuracy < 40% for 7+ days with n >= 15: recommend immediate quarantine
- If accuracy < 35% with any sample size n >= 10: recommend removal from ensemble

### Failure Mode: Two Agents with >90% Agreement Rate

**Diagnostic steps:**
1. Verify the correlation is not spurious (check co-occurrence count >= 20)
2. Determine if both agents use similar data sources (common for technical agents)
3. Compare accuracy: is one agent strictly superior?
4. Check if removing the weaker agent improves ensemble Sharpe

**Resolution:**
- If one agent is strictly better: recommend reducing the weaker agent's weight to 0.2
- If both are similar: recommend diversifying one agent's data source or analysis approach
- Never remove both — even correlated agents add marginal information

### Failure Mode: Agent Producing Conviction 7+ on >50% of Signals

**Diagnostic steps:**
1. Check conviction distribution: is it clustered at high values?
2. Compare actual win rate at conviction 7+ vs the expected 70%+
3. Assess whether the agent is systematically overconfident

**Resolution:**
- If win rate at conviction 7+ is < 55%: the agent is critically miscalibrated
- Recommend the aggregator's calibration system be activated for this agent
- Consider instructing the team manager to be more discerning about conviction assignment

## D.2 Pipeline-Level Failures

### Failure Mode: Aggregator Producing >50% HOLD/ABSTAIN Signals

**Indicates:** The teams are not generating actionable conviction. Most signals have conviction < 4 (MIN_ACTIONABLE_CONVICTION).

**Diagnostic steps:**
1. Check conviction distribution across all signals: are most below 4?
2. Check if the market is genuinely directionless (ranging with low volatility)
3. Verify that team managers are not over-hedging their synthesis

**Resolution:**
- If market IS directionless: this is correct behavior. The system should not force trades.
- If market has direction but signals are weak: investigate team-level analysis quality
- Consider temporarily lowering MIN_ACTIONABLE_CONVICTION to 3 if the fund is missing obvious trades

### Failure Mode: Risk Manager Filtering >80% of Signals

**Indicates:** CRO settings are too restrictive for current conditions, OR signal quality is genuinely poor.

**Diagnostic steps:**
1. Which filter is rejecting most signals? (confidence, consensus, max positions, drawdown)
2. Are the CRO's thresholds appropriate for the current regime? (compare against Section 2.2)
3. Is the aggregator producing low-confidence signals due to modifier stack penalties?

**Resolution:**
- If confidence filter: check if the modifier stack is over-penalizing. The penalty floor (50% of pre-modifier) may need adjustment.
- If consensus filter: in ranging markets, 80% consensus is very selective. This may be appropriate.
- If drawdown filter: the fund is in drawdown recovery mode. This is protective behavior.

### Failure Mode: Trades Consistently Hitting Stop Loss Within 1-2 Hours

**Indicates:** Stop loss placement is too tight for current volatility.

**Diagnostic steps:**
1. Compare stop loss distance (in $) against ATR at time of entry
2. Check if ATR multiplier is appropriate for the regime
3. Check if the ATR data is stale (using 24h high-low fallback instead of real ATR-14)

**Resolution:**
- If ATR multiplier is 2x in a bear market: recommend increasing to 3x or wider
- If ATR data is a fallback estimate: flag as IMPORTANT — real ATR-14 should be used
- If stops are correctly placed but consistently hit: the signals may be poorly timed

## D.3 Market-Level Failures

### Failure Mode: All Teams Agree but Trades Still Lose

**Indicates:** The market is in a regime where consensus is anti-predictive (contrarian conditions).

**Diagnostic steps:**
1. Check F&G Index: is it at extreme greed (>85)? Consensus + extreme greed = top signal.
2. Check funding rates: is the market overcrowded in one direction?
3. Check if the losing trades are all in the same asset tier or sector
4. Review the smart_money_divergence alerts: are whales acting opposite to consensus?

**Resolution:**
- If extreme greed + all bullish: this is a contrarian sell signal. Recommend the CEO shift to defensive stance.
- If overcrowded funding rates: the market is about to squeeze. Reduce position sizes.
- If concentrated losses in one sector: the analysis may be correct for other sectors but wrong for that sector.

### Failure Mode: Fund Performance Diverges from BTC by >20% (Underperformance)

**Indicates:** The fund is adding negative alpha. It would have been better to simply hold BTC.

**Diagnostic steps:**
1. Decompose alpha: how much comes from signal quality vs sizing vs timing vs execution?
2. Check if short trades are dragging performance (common in bull markets)
3. Check if the portfolio is overweight in underperforming sectors
4. Compare Sharpe ratio: is the fund's Sharpe < 0.5? If so, systematic approach is not working.

**Resolution:**
- If alpha is negative due to shorting in a bull: recommend reducing bear signals or eliminating short trades in strong bull regimes
- If alpha is negative due to sizing: position sizing formula may be miscalibrated
- If Sharpe < 0.5 persistently: fundamental review of the entire approach is needed

---

# APPENDIX E: PERFORMANCE METRICS REFERENCE

## E.1 Key Metrics to Track Weekly

| Metric | Healthy Range | Warning Range | Critical Range |
|---|---|---|---|
| Overall win rate | > 55% | 45-55% | < 45% |
| Average agent accuracy | > 55% | 50-55% | < 50% |
| Mean Information Coefficient | > 0.03 | 0.00-0.03 | < 0.00 |
| Average pairwise correlation | 0.40-0.65 | 0.65-0.80 | > 0.80 |
| Profit factor | > 1.3 | 1.0-1.3 | < 1.0 |
| Sharpe ratio (annualized est.) | > 1.0 | 0.5-1.0 | < 0.5 |
| Close-call signal rate | < 20% | 20-40% | > 40% |
| Stop-loss exit rate | < 40% | 40-60% | > 60% |
| Max drawdown from peak | < regime_limit | Approaching limit | At or exceeding limit |
| Meta-labeler validation accuracy | > 60% | 55-60% | < 55% (should bypass) |

## E.2 Sharpe Ratio Benchmarks

| Benchmark | Sharpe Ratio |
|---|---|
| S&P 500 long-term | 0.5-0.7 |
| Good hedge fund | > 1.0 |
| Strong hedge fund | > 1.5 |
| Renaissance Medallion | > 2.0 (estimated) |
| Bitcoin buy-and-hold (12-month, 2025) | 2.42 |
| Good crypto strategy | > 1.0 |
| Very good crypto strategy | > 2.0 |
| Excellent crypto strategy | > 3.0 |
| AdaptiveTrend (backtest) | 2.41 |
| Combined MR + TF (50/50 blend) | 1.71 |

## E.3 Recovery Math

Loss recovery is nonlinear. This table quantifies how much gain is needed to recover from a given loss:

| Loss | Gain Needed to Recover | Time Implications |
|---|---|---|
| -5% | +5.3% | Minor — recoverable in 1-2 winning trades |
| -10% | +11.1% | Moderate — several winning trades needed |
| -15% | +17.6% | Significant — may take 1-2 weeks |
| -20% | +25.0% | Serious — recovery period of weeks |
| -30% | +42.9% | Severe — recovery period of months |
| -50% | +100.0% | Catastrophic — need to double to recover |
| -70% | +233.3% | Near-fatal — multi-year recovery at best |
| -90% | +900.0% | Effectively terminal |

This is why the risk management framework is the most important system in the fund. A 50% drawdown requires a 100% gain to recover. A 70% drawdown requires a 233% gain. Prevention is exponentially more efficient than recovery.

---

*Knowledge base compiled from Syndicate's research documents, codebase analysis, academic literature, institutional benchmarks, and historical market data. All parameters reflect current system implementation as of March 2026. This document should be updated whenever system architecture, aggregation logic, or risk parameters change.*
