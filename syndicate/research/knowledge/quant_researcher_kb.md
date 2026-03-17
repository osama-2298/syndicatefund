# Dr. Kai Moretti — Quantitative Researcher Knowledge Base
# Syndicate Autonomous AI Crypto Hedge Fund
# Role: Signal Health Analysis & Data Source Evaluation

---

## TABLE OF CONTENTS

1. Statistical Foundations for Signal Analysis
2. Signal Quality Metrics
3. Signal Decay Detection
4. Agent Correlation & Redundancy Analysis
5. Data Source Evaluation Methodology
6. Overfitting Detection & Out-of-Sample Validation
7. Crypto-Specific Statistical Considerations
8. Operational Metrics for Syndicate
9. Report Writing Guidelines

---

# ═══════════════════════════════════════════════════════════════════
# 1. STATISTICAL FOUNDATIONS FOR SIGNAL ANALYSIS
# ═══════════════════════════════════════════════════════════════════

## 1.1 Hypothesis Testing Framework

Every claim about agent performance, signal decay, or data source value MUST be
framed as a hypothesis test. Informal claims ("this agent seems bad") are not
acceptable for action recommendations. The framework:

### Null Hypothesis (H0)
- Default assumption: the agent/indicator has NO edge. Its accuracy is 50% (coin flip).
- For directional signals (BUY/SHORT), H0: P(correct) = 0.50.
- For conviction-accuracy calibration, H0: actual_win_rate = expected_win_rate.
- For signal decay, H0: accuracy_recent = accuracy_older (no change).
- For correlation, H0: agreement_rate = chance agreement (based on base rates).

### Alternative Hypothesis (H1)
- H1 depends on the question:
  - Agent has edge: P(correct) > 0.50 (one-tailed).
  - Agent has decayed: accuracy_recent < accuracy_older (one-tailed).
  - Two agents are redundant: agreement_rate > threshold (one-tailed).
  - Indicator has predictive value: IC > 0 (one-tailed).

### Type I Error (False Positive) — alpha
- Standard: alpha = 0.05 (5% chance of false alarm).
- For high-consequence decisions (firing an agent, quarantining a team):
  Use alpha = 0.01. You need very strong evidence to take irreversible action.
- For low-consequence decisions (adjusting weight by 10%):
  alpha = 0.10 is acceptable for faster response.

### Type II Error (False Negative) — beta
- Power = 1 - beta. Target power = 0.80 (80% chance of detecting real decay).
- With crypto's high variance, power is often limited by sample size.
- If n < 20 signals, power for detecting a 10% accuracy drop is below 0.40.
  This means you will MISS more than half of real decay events. State this clearly.

### Test Selection Guide
- **Binomial test**: For testing if accuracy differs from 50%.
  - Use when: evaluating a single agent's overall accuracy.
  - Formula: P(X >= k | n, p=0.5) where k = number correct, n = total evaluated.
  - Exact (not approximate) — valid for any sample size.
- **Proportion z-test**: For comparing two proportions (recent vs older accuracy).
  - Use when: testing for signal decay between two windows.
  - Requires n1 >= 20, n2 >= 20 for valid approximation.
  - z = (p1 - p2) / sqrt(p_hat * (1 - p_hat) * (1/n1 + 1/n2))
  - where p_hat = (k1 + k2) / (n1 + n2)
- **Chi-squared test**: For comparing distributions (conviction vs accuracy bins).
  - Use when: testing if accuracy varies significantly across conviction levels.
  - Requires expected count >= 5 per cell.
- **Fisher's exact test**: When any cell in a 2x2 table has expected count < 5.
  - Use when: small-sample agent comparison.
- **Permutation test**: Distribution-free alternative for any comparison.
  - Use when: you suspect non-normal returns (almost always in crypto).
  - Resample 10,000 times under H0, compute p-value as fraction more extreme.

## 1.2 P-Values: Proper Interpretation

### What a p-value IS
- P(observing data this extreme or more extreme | H0 is true).
- It is NOT the probability that H0 is true.
- It is NOT the probability of the result being "due to chance."

### Thresholds for Syndicate Decision-Making
- p < 0.001: Very strong evidence. Confident action (quarantine, fire, promote).
- p < 0.01: Strong evidence. Action with monitoring.
- p < 0.05: Moderate evidence. Recommend weight adjustment, flag for review.
- p < 0.10: Suggestive. Mention in report, no action yet. Continue monitoring.
- p >= 0.10: Insufficient evidence. Do not act. Note the sample size limitation.

### Critical Warning: p-hacking
- If you test 20 agents at alpha=0.05, expect ~1 false positive by chance alone.
- ALWAYS report how many comparisons were made.
- If testing 12 agents for decay, apply Bonferroni or FDR correction.

## 1.3 Confidence Intervals for Proportions

### Exact Binomial (Clopper-Pearson)
- Conservative (wider intervals). Use for safety-critical decisions.
- For k correct out of n: use beta distribution quantiles.
- Example: 14/20 correct (70%):
  - 95% CI: [45.7%, 88.1%] — very wide with small n.
  - This means the true accuracy could plausibly be as low as 46%.

### Wilson Score Interval (preferred for reporting)
- Better coverage than Wald (normal approximation).
- Formula:
  - center = (k + z²/2) / (n + z²)
  - margin = z × sqrt((k(n-k)/n + z²/4)) / (n + z²)
  - CI = [center - margin, center + margin]
  - where z = 1.96 for 95% CI.
- Example: 14/20 correct (70%):
  - 95% Wilson CI: [47.9%, 85.5%] — slightly tighter than exact.
- Always report Wilson intervals alongside point estimates.

### Agresti-Coull Interval
- "Add 2 successes and 2 failures" — good for quick mental math.
- Adjusted proportion: p_tilde = (k + 2) / (n + 4).
- Example: 14/20 → p_tilde = 16/24 = 66.7%.
- Use for quick sanity checks, not for formal reports.

## 1.4 Effect Sizes

### Why Effect Sizes Matter
- p-values tell you IF there's a difference; effect sizes tell you HOW BIG.
- A 1% accuracy improvement can be "statistically significant" with n=10,000
  but operationally meaningless.
- Always report both p-value and effect size.

### Cohen's d (for comparing means)
- d = (mean1 - mean2) / pooled_sd
- Interpretation in Syndicate context:
  - |d| < 0.2: Trivial. Not worth acting on.
  - |d| 0.2-0.5: Small. Adjust weight by 5-10%.
  - |d| 0.5-0.8: Medium. Recommend quarantine or significant weight change.
  - |d| > 0.8: Large. Strong action (fire, promote, restructure).
- Caveat: Assumes normality. Crypto returns are heavily non-normal.

### Glass's delta
- Like Cohen's d but uses only the control group's SD as denominator.
- Use when: comparing a new agent to established baseline.
- delta = (mean_new - mean_baseline) / sd_baseline.
- Preferred when the two groups may have different variances.

### Cliff's delta (non-parametric)
- For ordinal/non-normal data. Counts how often values in group A exceed group B.
- delta = (P(X1 > X2) - P(X2 > X1)) where X1 and X2 are observations from each group.
- Range: [-1, 1]. Interpretation:
  - |delta| < 0.147: Negligible
  - |delta| 0.147-0.33: Small
  - |delta| 0.33-0.474: Medium
  - |delta| > 0.474: Large
- RECOMMENDED for crypto data. Does not assume normality.

### Cohen's h (for comparing proportions — most relevant for accuracy)
- h = 2 × arcsin(sqrt(p1)) - 2 × arcsin(sqrt(p2))
- Interpretation:
  - |h| < 0.2: Small difference — cosmetic, not actionable.
  - |h| 0.2-0.5: Medium — investigate and potentially act.
  - |h| > 0.5: Large — requires immediate action.
- Example: Agent decayed from 70% to 55%:
  - h = 2 × arcsin(sqrt(0.70)) - 2 × arcsin(sqrt(0.55)) = 0.31 → Medium.

## 1.5 Sample Size Requirements

### How Many Signals Before We Can Trust Accuracy?

To detect a delta-p accuracy difference from a 50% baseline at 80% power, alpha=0.05:

| Target delta | Required n per group | Total signals needed |
|-------------|---------------------|---------------------|
| 5% (50→55%)  | 1,571                | 3,142               |
| 10% (50→60%) | 388                  | 776                  |
| 15% (50→65%) | 170                  | 340                  |
| 20% (50→70%) | 93                   | 186                  |
| 25% (50→75%) | 57                   | 114                  |

### Practical Implications for Syndicate
- With 5 teams analyzing ~3-5 coins per cycle, ~4 cycles/day:
  - Each team generates ~12-20 signals per day.
  - Per-agent signals: ~4-7 per day (3 agents per team).
  - After 1 week: ~30-50 per agent. Enough to detect 20%+ accuracy difference.
  - After 1 month: ~120-200 per agent. Enough to detect 10% difference.
  - For 5% detection: need ~6+ months of data. State this when asked.

### Minimum Sample Sizes for Syndicate Decisions
- **Weight adjustment**: n >= 20 (can detect large effects only).
- **Decay detection**: n >= 30 per window (recent and older).
- **Correlation assessment**: n >= 10 co-occurrences (crude), n >= 30 (reliable).
- **Quarantine recommendation**: n >= 50 with p < 0.05.
- **Fire recommendation**: n >= 100 with p < 0.01.
- **Promotion recommendation**: n >= 100 with p < 0.01.

## 1.6 Bayesian Alternatives

### Why Bayesian Matters for Syndicate
- Frequentist p-values answer the wrong question ("how surprising is this data?").
- Bayesian credible intervals answer the right question ("what is the probability
  that the true accuracy falls in this range?").
- With small samples (common for new agents), Bayesian updating is more stable.

### Bayesian Hypothesis Testing for Agent Accuracy
- Prior: Beta(alpha=2, beta=2) — weakly informative, centered at 50%.
  - This prior says: "Before seeing data, I believe accuracy is roughly 50%
    but I'm not very sure."
- Update: After observing k correct out of n total:
  - Posterior: Beta(alpha + k, beta + (n - k))
- Credible interval: compute quantiles of the posterior Beta distribution.
  - Example: 18/25 correct (72%):
    - Posterior: Beta(20, 9)
    - 95% credible interval: [53.5%, 85.5%]
    - MAP estimate: (20 - 1) / (20 + 9 - 2) = 70.4%
    - If entire CI is above 55%, agent likely has genuine edge.

### Bayesian Factor for Agent Comparison
- BF10 = P(data | H1) / P(data | H0)
- Interpretation:
  - BF10 < 1/10: Strong evidence FOR H0 (agent is NOT decaying).
  - BF10 1/10 to 1/3: Moderate evidence for H0.
  - BF10 1/3 to 3: Inconclusive.
  - BF10 3 to 10: Moderate evidence for H1 (agent IS decaying).
  - BF10 > 10: Strong evidence for H1.
  - BF10 > 100: Decisive.

### Prior Selection for Different Analyses
- New agent, no history: Beta(2, 2) — flat-ish.
- Agent with team baseline of 60%: Beta(6, 4) — centered at 60%.
- Testing for decay vs stable: Beta(accuracy_old × 10, (1-accuracy_old) × 10).

## 1.7 Multiple Comparisons Correction

### The Problem
- 12 agents tested for decay at alpha=0.05:
  - P(at least one false positive) = 1 - (1 - 0.05)^12 = 46%.
  - Nearly half the time you'll flag an innocent agent.

### Bonferroni Correction
- Adjusted alpha = 0.05 / m, where m = number of tests.
- 12 agents: alpha_adj = 0.05/12 = 0.0042. Only report p < 0.0042 as significant.
- Conservative. May miss real decay (high Type II error).
- Use when: consequences of false positive are severe (firing decision).

### Benjamini-Hochberg (FDR) Correction
- Controls the expected proportion of false discoveries.
- Algorithm:
  1. Sort p-values: p(1) <= p(2) <= ... <= p(m).
  2. For each i, compute threshold: i/m × alpha.
  3. Find largest i where p(i) <= i/m × alpha.
  4. Reject all hypotheses with p <= p(i_max).
- Less conservative than Bonferroni. Controls false discovery rate at alpha.
- Use when: screening many agents/indicators. Missing real effects is costly.

### Holm-Bonferroni (step-down)
- More powerful than Bonferroni, still controls family-wise error rate.
- Compare smallest p-value to alpha/m, second-smallest to alpha/(m-1), etc.
- Use when: moderate number of comparisons (5-20).

### Practical Recommendation for Syndicate
- Routine health checks (12 agents): Use Benjamini-Hochberg (FDR at 5%).
- Firing decisions: Use Bonferroni (alpha = 0.05/m).
- Data source evaluations (testing many indicators): Use FDR at 10%.
- Always report BOTH raw and adjusted p-values.


# ═══════════════════════════════════════════════════════════════════
# 2. SIGNAL QUALITY METRICS
# ═══════════════════════════════════════════════════════════════════

## 2.1 Information Coefficient (IC)

### Definition
- IC = Spearman rank correlation between predicted signal (conviction level)
  and actual subsequent return (signed by direction).
- Syndicate implementation: see PerformanceTracker.compute_ic().
  - Collects (confidence, signed_move_pct) pairs for evaluated signals.
  - Uses rolling 30-day window (IC_ROLLING_DAYS = 30).
  - Minimum 10 evaluated signals needed; below this, IC is unreliable.

### IC Interpretation Thresholds
| IC Range     | Assessment         | Syndicate Implication                          |
|-------------|--------------------|-------------------------------------------------|
| < -0.05     | Anti-predictive    | Higher conviction = WORSE outcomes. Recalibrate. |
| -0.05–0.00  | Noise              | Conviction adds no value. Weight all signals equally. |
| 0.00–0.02   | Barely detectable  | Possible edge, but could be noise. Need more data. |
| 0.02–0.05   | Meaningful         | Genuine signal. Conviction-weighted aggregation is justified. |
| 0.05–0.10   | Good               | Strong signal quality. Agent or team is calibrated well. |
| 0.10–0.15   | Very good          | Exceptional in crypto. Only the best strategies achieve this. |
| 0.15+       | Outstanding        | Suspicious if sustained. Check for lookahead bias or data leak. |

### IC Half-Life in Crypto
- IC decays as the market adapts to a signal's edge.
- Typical IC half-lives by data source:
  - Technical indicators (RSI, MACD): 4-8 hours
  - Sentiment scores: 6-12 hours
  - On-chain metrics (whale flows): 12-24 hours
  - Fundamental metrics (TVL, revenue): 2-7 days
  - Macro regime signals: 1-4 weeks
- Monitor IC in rolling windows. If IC drops below 0.02 for >7 days, flag decay.

### Per-Team IC Expectations
- Technical: IC 0.03-0.08. Decays fastest. Driven by short-term price patterns.
- Sentiment: IC 0.02-0.06. Moderate decay. Vulnerable to narrative shifts.
- Fundamental: IC 0.01-0.04. Slow decay. Lower IC but more stable.
- Macro: IC 0.01-0.03. Lowest IC but most durable. Regime signals are infrequent.
- On-Chain: IC 0.04-0.09. Highest potential IC. Whale tracking has genuine edge.

### IC Decomposition
- IC can be decomposed into: IC = accuracy_component + sizing_component.
- accuracy_component: correlation between direction (bull/bear) and return sign.
- sizing_component: correlation between conviction magnitude and return magnitude.
- If accuracy_component is high but sizing_component is near zero:
  - Agent picks direction well but conviction levels are uncalibrated.
  - Recommendation: reduce conviction variance, treat all signals as medium conviction.
- If both are positive: ideal — well-calibrated agent.

## 2.2 Information Ratio (IR) and Grinold's Fundamental Law

### Grinold's Fundamental Law of Active Management
- IR = IC × sqrt(BR) × TC
  - IC: Information Coefficient (signal quality)
  - BR: Breadth = number of independent bets per year
  - TC: Transfer Coefficient = fraction of predicted alpha realized in portfolio

### Breadth Calculation for Syndicate
- Syndicate runs ~4 cycles per day, analyzing ~3-5 coins per cycle.
- Independent bets per day: ~15-20 (assuming partial coin overlap).
- Independent bets per year: ~5,500-7,300.
- But many bets are correlated (crypto pair avg correlation = 0.56).
- Effective independent bets: ~5,500 × (1 - avg_corr) ≈ 2,420.
- sqrt(BR_eff) ≈ 49.

### Transfer Coefficient
- TC < 1.0 due to: risk limits, position sizing constraints, execution costs.
- Syndicate's TC estimated at 0.6-0.8.
  - Risk limits: max 5% per position, max 20% per sector → reduces TC.
  - Execution: paper trading = TC ~0.95; live trading with slippage = TC ~0.70.
  - Min confidence threshold (0.6): filters out ~30% of signals → lowers breadth but improves IC.

### Target IR for Syndicate
- With IC = 0.05, BR_eff = 2,420, TC = 0.70:
  - IR = 0.05 × sqrt(2420) × 0.70 = 0.05 × 49.2 × 0.70 = 1.72
  - This is an excellent IR. Sharpe equivalent of ~1.72.
- With IC = 0.03 (weaker signals):
  - IR = 0.03 × 49.2 × 0.70 = 1.03. Still strong.
- Key insight: Syndicate's high breadth (many bets) means even modest IC
  translates to good performance. Priority: maintain IC > 0.03 across teams.

## 2.3 Sharpe Ratio

### Annualized Sharpe Calculation
- Sharpe = (annualized_return - risk_free_rate) / annualized_volatility
- For crypto:
  - Risk-free rate: use 3-month T-bill rate (~5.0% as of 2025).
  - Annualize daily returns: return_annual = mean_daily × 365
  - Annualize volatility: vol_annual = std_daily × sqrt(365)
  - Note: 365 (not 252) because crypto trades 24/7.

### Crypto Sharpe Benchmarks
| Strategy/Benchmark          | Typical Sharpe | Notes                              |
|----------------------------|---------------|-------------------------------------|
| BTC buy-and-hold (2015-2024) | 0.90-1.20     | Highly period-dependent             |
| BTC buy-and-hold (2020-2024) | 2.42          | Bull-cycle inflated                 |
| Naive momentum (BTC)        | 0.40-0.80     | Depends on lookback period          |
| Mean reversion (BTC)        | 0.30-0.60     | Works in ranging, fails in trends   |
| Multi-indicator (MACD+RSI)  | 0.80-1.44     | Best with multi-TF alignment        |
| Top quant crypto funds      | 1.50-3.00     | Renaissance-tier, not sustainable   |
| Syndicate target            | 1.00-2.00     | Achievable with IC > 0.04           |

### Rolling Sharpe (Diagnostic Tool)
- Compute Sharpe over rolling 30-day windows.
- Flag if rolling Sharpe drops below 0.0 for >14 consecutive days.
- Persistent negative Sharpe = strategy is broken, not just unlucky.
- Rolling Sharpe variance: if std(rolling_sharpe) > 1.5, strategy is unstable.

### Bootstrapped Sharpe Confidence Intervals
- Resample returns with replacement (10,000 iterations).
- Compute Sharpe for each resample.
- Report 5th and 95th percentile as 90% CI.
- If 5th percentile Sharpe < 0, the strategy may have no genuine edge.
- Minimum 90 days of data for meaningful bootstrap.

## 2.4 Sortino Ratio

### Formula
- Sortino = (annualized_return - risk_free_rate) / downside_deviation
- Downside deviation: sqrt(mean(min(r_i - target, 0)^2))
- Target: usually 0% (no loss) or risk-free rate.

### Why Sortino > Sharpe for Crypto
- Crypto returns are positively skewed (big winners, moderate losers).
- Sharpe penalizes upside volatility equally with downside — wrong for crypto.
- Sortino only penalizes downside, better capturing actual risk.
- A strategy with Sharpe 1.0 and Sortino 2.0 has favorable skew (good).
- A strategy with Sharpe 1.0 and Sortino 0.8 has unfavorable skew (bad).

## 2.5 Hit Rate vs Profit Factor Tradeoff

### Definitions
- Hit rate (win rate) = number of winning trades / total trades.
- Profit factor = gross_profit / gross_loss = (avg_win × n_wins) / (avg_loss × n_losses).
- Expectancy = (hit_rate × avg_win) - ((1 - hit_rate) × avg_loss).

### The Fundamental Tradeoff
- High hit rate + small wins / large losses = poor profit factor.
  - Example: 80% win rate, avg win $100, avg loss $500.
  - Profit factor = (0.8 × 100) / (0.2 × 500) = 0.80. LOSING strategy despite 80% accuracy.
- Low hit rate + large wins / small losses = good profit factor.
  - Example: 40% win rate, avg win $500, avg loss $100.
  - Profit factor = (0.4 × 500) / (0.6 × 100) = 3.33. WINNING strategy despite 40% accuracy.

### Syndicate's Architecture Implication
- Signal evaluation uses 0.5% minimum move (MIN_MOVE_PCT) for the 24h price-movement rule.
- This creates symmetric win/loss thresholds → hit rate ≈ profit factor proxy.
- BUT trade-based evaluation (actual P&L) uses ATR-based stops with R-multiple targets:
  - Stop: 2.5 ATR. TP1: ~1R, TP2: ~2R, trailing for remainder.
  - This creates asymmetric payoffs (good: wins > losses).
  - Trade accuracy may be 45-55% but profit factor > 1.5 due to R-multiples.
- Always report BOTH hit rate AND profit factor (or expectancy).

### Expected Calibration by Conviction Level
| Conviction | Expected Win Rate | Acceptable Range | Action if Below |
|-----------|------------------|-----------------|----------------|
| 1-3        | 45-55%           | 40-60%          | Not actionable (HOLD signals) |
| 4-5        | 50-60%           | 45-65%          | Monitor |
| 6-7        | 55-65%           | 50-70%          | Investigate if < 50% |
| 8-9        | 65-80%           | 55-85%          | Quarantine if < 55% |
| 10         | 80-95%           | 70-95%          | Fire if < 65% |

## 2.6 Maximum Adverse Excursion (MAE) Analysis

### Definition
- MAE = maximum drawdown from entry price BEFORE the trade closes.
- Even winning trades experience drawdown during the holding period.
- MAE analysis reveals if stops are set correctly.

### How to Use MAE
- Plot MAE (x-axis) vs trade outcome (y-axis: final P&L %).
- Winning trades with high MAE → stop was almost triggered. Stop is too tight.
- Losing trades with low MAE → price moved against immediately. Signal was wrong, not just unlucky.
- Optimal stop = the MAE level where most winning trades never reach.

### MAE Thresholds for Crypto
- BTC: median MAE for winning trades ~1.5-3%. Stop at 2.5 ATR usually works.
- Altcoins: median MAE for winning trades ~3-8%. Need wider stops.
- Memecoins: median MAE ~10-20%. Extremely noisy; tight stops are death.

## 2.7 IC-Squared Weighting

### Formula
- w_j = IC_j² / Σ(IC_k²)
- Where IC_j is the Information Coefficient for agent (or team) j.

### Rationale
- Standard equal-weighting is suboptimal when agents have different IC.
- IC-squared weighting allocates more weight to higher-IC agents.
- Squaring emphasizes the difference: an agent with IC=0.08 gets 4x the weight
  of an agent with IC=0.04, not just 2x.
- This is more aggressive than linear IC-weighting but justified by the
  Markowitz analogy (optimal portfolio weights are proportional to expected
  return squared / variance).

### When to Recommend IC-Squared vs Current Weighting
- Current Syndicate weight: max(0.1, min(1.0, 0.5 + (accuracy - 0.5) × 2))
- This is accuracy-linear. IC-squared would be better IF:
  - We have reliable IC estimates (n >= 50 signals per agent).
  - IC varies significantly across agents (coefficient of variation > 0.5).
  - If IC is similar across agents, the difference is negligible.

## 2.8 Bayesian Model Averaging for Signal Weighting

### Concept
- Instead of picking one weighting scheme, average over multiple models.
- Each model (equal-weight, accuracy-weight, IC-squared-weight) gets a posterior
  probability based on how well it explains observed data.
- Final weight = Σ(P(model_k | data) × weight_under_model_k).

### Implementation Sketch
- Compute out-of-sample log-likelihood for each weighting scheme.
- BMA weight for scheme k: exp(LL_k) / Σ(exp(LL_j)).
- This automatically selects the best scheme for each team.
- Computationally expensive. Recommend quarterly evaluation, not per-cycle.

### Practical Shortcut for Syndicate
- Run 3 weighting schemes in parallel on historical data:
  1. Current formula: max(0.1, min(1.0, 0.5 + (accuracy - 0.5) × 2))
  2. IC-squared weighting
  3. Equal weighting
- Track which produces highest out-of-sample aggregate accuracy.
- Report winner quarterly. Don't change scheme more often than that.


# ═══════════════════════════════════════════════════════════════════
# 3. SIGNAL DECAY DETECTION
# ═══════════════════════════════════════════════════════════════════

## 3.1 What Causes Signal Decay

### Market Adaptation
- Other participants learn the same pattern and trade it faster.
- Example: RSI oversold bounces used to work until every algo watched RSI.
- In crypto: adaptation is FASTER than traditional markets (open data, 24/7,
  bot-dominated volume). Typical adaptation time: 3-6 months for simple signals.
- Complex multi-factor signals survive longer: 6-18 months.

### Regime Change
- A signal that works in a bull market may fail in a bear market.
- BTC correlation to stocks shifted from 0.1 (2019) to 0.6+ (2022).
- Macro signals that relied on "crypto is uncorrelated" became anti-predictive.
- Regime changes in crypto:
  - Halving cycles (~4 years): structural shift in supply dynamics.
  - Regulatory shifts: SEC actions, ETF approvals, bans.
  - Macro regime: rate hike cycles vs easing.
  - Leverage regime: high leverage (2021) vs deleveraged (2023).

### Crowding
- Too many participants using the same signal.
- Symptoms: reduced win rate, faster mean reversion of the signal itself.
- In crypto: crowding is visible via funding rates.
  - When funding rate and your signal agree: the signal is crowded.
  - When funding rate opposes your signal: less crowding, signal more likely to work.

### Data Source Degradation
- API quality drops, data provider changes methodology, exchange delists.
- Example: a sentiment agent relying on Twitter data degrades when X changes API access.
- Example: on-chain agent accuracy drops when a major exchange migrates to different wallet structure.
- Monitor data source availability alongside signal quality.

### LLM Model Updates
- When the underlying LLM (Claude, GPT, Gemini) gets updated, agent behavior changes.
- This is a form of "agent decay" even if the signal logic is unchanged.
- Solution: track agent accuracy with model version as a covariate.

## 3.2 Detection Methods

### Rolling Window Accuracy Comparison (Primary Method)

**Algorithm:**
1. Define two windows:
   - Recent: last 30 days (or last N signals where N >= 20).
   - Baseline: 30-90 days ago (or previous N signals).
2. Compute accuracy in each window.
3. Compute delta = accuracy_recent - accuracy_baseline.
4. Test significance with proportion z-test (or Fisher's exact if n < 30).

**Severity Classification:**
| Delta              | Severity | Recommended Action                       |
|-------------------|----------|------------------------------------------|
| delta > -5%       | None     | Normal fluctuation. Continue monitoring. |
| -5% to -10%      | Mild     | Note in report. Watch next 2 cycles.     |
| -10% to -20%     | Moderate | Reduce weight by 30%. Alert team.        |
| delta < -20%      | Severe   | Quarantine agent. Signals recorded but weight → 0.3. |
| delta < -30%      | Critical | Recommend firing. Signals are destructive. |

**Important Caveat:**
- Small delta can be statistically significant with large n.
- Large delta can be statistically insignificant with small n.
- ALWAYS report both delta and p-value.
- Rule of thumb: act on delta >= 10% AND p < 0.10.

### CUSUM (Cumulative Sum) Test for Change-Point Detection

**What it does:**
- Detects the exact moment when accuracy shifted, not just that it shifted.
- More sensitive than rolling window for gradual decay.

**Algorithm:**
1. Set reference value k = delta_min / 2 (smallest shift you want to detect).
   - For Syndicate: k = 0.05 (detect 10%+ shift, so k = 0.10/2 = 0.05).
2. For each signal outcome (1 = correct, 0 = incorrect):
   - S_n = max(0, S_{n-1} + (x_n - (p0 + k))) for detecting decrease.
   - Where p0 = baseline accuracy (e.g., 0.65).
   - x_n = 1 if correct, 0 if incorrect.
3. Signal alarm when S_n exceeds threshold h.
   - h = 4σ for ARL0 ≈ 1,000 (low false alarm rate).
   - h = 3σ for ARL0 ≈ 200 (faster detection, more false alarms).
   - σ = sqrt(p0 × (1 - p0)) for binomial data.

**Syndicate-specific settings:**
- p0: use agent's overall accuracy (from get_agent_stats()).
- k = 0.05 (detect 10%+ drops).
- h = 4 × sqrt(0.65 × 0.35) ≈ 4 × 0.477 = 1.91. Use h = 2.0.
- Run CUSUM after every cycle. If S_n > 2.0, flag the agent.

### Exponentially Weighted Moving Average (EWMA) of Accuracy

**Algorithm:**
- EWMA_t = lambda × x_t + (1 - lambda) × EWMA_{t-1}
- lambda = 2 / (span + 1). Recommended span = 20 signals.
  - lambda = 2/21 = 0.095.
- Initialize EWMA_0 = overall_accuracy.

**Interpretation:**
- EWMA gives more weight to recent signals.
- If EWMA drops below (overall_accuracy - 0.10), flag for investigation.
- If EWMA drops below 0.50, quarantine the agent.
- Advantage over rolling window: smoother, no arbitrary window boundary.

### Page's Test for Gradual Degradation

**Use case:** When decay is slow and steady (1-2% per week), neither CUSUM
nor rolling window may catch it quickly. Page's test accumulates evidence
of a monotone trend.

**Algorithm:**
1. Divide signal history into k consecutive blocks of size m (m >= 10).
2. Compute accuracy in each block: a_1, a_2, ..., a_k.
3. Test for a monotone decreasing trend using Mann-Kendall test.
4. Kendall's tau < 0 indicates decreasing accuracy.
5. Significance: compute p-value for tau.

**Thresholds:**
- tau < -0.3, p < 0.10: Suggestive of gradual decay. Increase monitoring frequency.
- tau < -0.5, p < 0.05: Likely decay. Reduce weight by 20%.
- tau < -0.7, p < 0.01: Strong decay. Quarantine.

## 3.3 Agent-Specific Decay Patterns in Crypto

### Technical Agents (TrendAgent 1D, SignalAgent 4H, TimingAgent 1H)
- **Decay trigger:** Regime transitions (bull→bear, ranging→trending).
  - Technical signals are pattern-based. Patterns change with market structure.
  - Example: mean reversion signals fail when a range breakout starts.
- **Decay speed:** Fast (1-2 weeks of degraded accuracy after regime shift).
- **Typical decay signature:** Sudden accuracy drop coinciding with volatility spike.
- **Recovery:** Often self-corrects once new regime stabilizes. Wait 2-3 weeks.
- **Special concern:** TimingAgent (1H) is most vulnerable — highest noise-to-signal
  ratio due to micro-structure effects.
- **Expected baseline accuracy:** 55-65%. Below 50% for >2 weeks = investigate.

### Sentiment Agents (SocialAgent, MarketAgent, SmartMoneyAgent)
- **Decay trigger:** Narrative shifts, platform changes, sentiment source degradation.
  - When the dominant crypto narrative changes (e.g., "L1 rotation" → "AI meta"),
    sentiment signals calibrated to old narratives lose predictive power.
- **Decay speed:** Moderate (2-4 weeks of gradual accuracy decline).
- **Typical decay signature:** IC drops before accuracy does. Conviction loses
  calibration first (high conviction doesn't correlate with bigger moves).
- **Recovery:** Requires re-exposure to new narrative. Monitor IC first.
- **Special concern:** SmartMoneyAgent is most stable (whale behavior is
  structural, not narrative-driven). SocialAgent is most volatile.
- **Expected baseline accuracy:** 50-60%. SmartMoney: 55-65%.

### Fundamental Agents (ValuationAgent, CyclePositionAgent)
- **Decay trigger:** Structural market changes (new tokenomics models, DeFi innovation).
  - Fundamental frameworks (P/S ratios, TVL/market cap) become stale when
    the market invents new valuation paradigms.
- **Decay speed:** Slow (1-3 months). Usually the last team to decay.
- **Typical decay signature:** Persistent small negative delta (2-3% per month).
  Hard to detect without Page's test.
- **Recovery:** Requires knowledge base update. Fundamental frameworks need
  periodic recalibration.
- **Expected baseline accuracy:** 50-58%. Lower hit rate but longer-term signals.

### On-Chain Agents (NetworkHealthAgent, CapitalFlowAgent)
- **Decay trigger:** Exchange structure changes, privacy adoption, L2 migration.
  - When significant trading volume migrates to L2s or DEXs,
    CEX-based on-chain metrics lose coverage.
  - When exchanges change cold/hot wallet structures, whale detection breaks.
- **Decay speed:** Variable. Can be sudden (exchange migration) or gradual (L2 adoption).
- **Typical decay signature:** Data completeness drops before accuracy does.
  If coverage < 60% of trading volume, on-chain signals lose reliability.
- **Recovery:** Requires data source updates. May need new APIs/endpoints.
- **Expected baseline accuracy:** 55-65%. CapitalFlowAgent slightly higher.

### Macro Agents (CryptoMacroAgent, ExternalMacroAgent)
- **Decay trigger:** Macro regime changes (rate hikes→cuts, risk-on→risk-off).
  - Macro signals are DESIGNED to adapt to regime changes, but the
    speed of adaptation matters.
- **Decay speed:** Very slow. Macro agents are the most stable.
- **Typical decay signature:** Accuracy doesn't drop; instead, signal frequency
  drops (agent becomes more neutral). This is actually correct behavior.
- **Recovery:** Self-correcting over 1-2 macro cycles (months).
- **Expected baseline accuracy:** 50-55%. Lower accuracy is expected;
  value comes from regime-gate influence, not directional bets.

## 3.4 Alpha Half-Life Estimation

### Concept
- Alpha half-life = time for a signal's excess return to decay by 50%.
- Measured by tracking out-of-sample IC over time after initial calibration.

### Estimation Method
1. Measure IC at time T=0 (when signal was first deployed).
2. Measure IC at T+1 month, T+2 months, etc.
3. Fit exponential decay: IC(t) = IC_0 × exp(-lambda × t).
4. Half-life = ln(2) / lambda.

### Typical Alpha Half-Lives in Crypto
| Signal Type                | Half-Life         | Recalibration Frequency |
|---------------------------|-------------------|------------------------|
| Intraday technical (1H)   | 2-4 weeks         | Weekly                 |
| Swing technical (4H, 1D)  | 4-8 weeks         | Bi-weekly              |
| Sentiment momentum        | 3-6 weeks         | Bi-weekly              |
| On-chain flow patterns    | 6-12 weeks        | Monthly                |
| Fundamental valuation     | 3-6 months        | Quarterly              |
| Macro regime signals      | 6-12 months       | Semi-annually          |

## 3.5 Quarantine vs Weight Reduction vs Firing

### Decision Framework

```
                    ┌─────────────────────────┐
                    │ Detect accuracy decline  │
                    └──────────┬──────────────┘
                               │
                    ┌──────────▼──────────────┐
                    │ Is n >= 20 in window?    │
                    └──┬───────────────────┬──┘
                       │ NO                │ YES
                       ▼                   ▼
               ┌──────────────┐  ┌─────────────────────┐
               │ "Insufficient │  │ Is delta > -10%?    │
               │  data" note   │  └──┬──────────────┬──┘
               └──────────────┘     │ YES           │ NO
                                    ▼               ▼
                            ┌──────────┐  ┌──────────────────┐
                            │ Monitor  │  │ Is p < 0.05?     │
                            │ (no act) │  └──┬───────────┬──┘
                            └──────────┘     │ NO        │ YES
                                             ▼           ▼
                                     ┌──────────┐ ┌──────────────────┐
                                     │ Monitor, │ │ Is delta > -20%? │
                                     │ inc freq │ └──┬───────────┬──┘
                                     └──────────┘    │ YES       │ NO
                                                     ▼           ▼
                                             ┌───────────┐ ┌──────────┐
                                             │ WEIGHT    │ │ Is n>=50 │
                                             │ REDUCTION │ │ & p<0.01?│
                                             │ (0.3-0.5) │ └──┬───┬──┘
                                             └───────────┘    │   │
                                                          NO  │   │ YES
                                                              ▼   ▼
                                                    ┌──────────┐ ┌────────┐
                                                    │QUARANTINE│ │ FIRE   │
                                                    │(weight→  │ │ Agent  │
                                                    │ 0.3,     │ └────────┘
                                                    │ observe) │
                                                    └──────────┘
```

### Weight Reduction Protocol
- Current weight formula: max(0.1, min(1.0, 0.5 + (accuracy - 0.5) × 2))
- Reduction is applied as a multiplier: weight × reduction_factor.
  - Mild decay: factor = 0.7 (reduce weight by 30%).
  - Moderate decay: factor = 0.5 (halve the weight).
  - Severe: quarantine (override weight to 0.3).
- Reductions are TEMPORARY (2-4 weeks). If accuracy recovers, restore weight.

### Quarantine Protocol
- Weight overridden to 0.3 (from agent_registry: quarantine_signals_remaining).
- Signals still recorded and evaluated (critical: need data to assess recovery).
- Quarantine duration: minimum 20 signals or 2 weeks, whichever is longer.
- Exit criteria: accuracy returns to within 5% of team baseline, p < 0.10.

### Firing Protocol
- Agent removed from active rotation.
- All historical data PRESERVED (never delete — per fund policy).
- Fire only with: n >= 100, p < 0.01 for underperformance, AND
  no plausible external explanation (data source down, regime change, etc.).
- Before firing, check: did ALL agents in the team decay simultaneously?
  If yes, the problem is the data source, not the individual agents.

## 3.6 Minimum Sample Sizes for Decay Assessment

### General Rules
- n >= 20: Can detect large effects (delta > 20%). Suitable for flagging.
- n >= 30: Can detect moderate effects (delta > 15%). Suitable for weight changes.
- n >= 50: Can detect meaningful effects (delta > 10%). Suitable for quarantine.
- n >= 100: Can detect small effects (delta > 5%). Suitable for firing.

### Time-to-Detection Table (assuming 5 signals/day/agent)
| Effect Size | n Required | Days to Detect | Calendar Time |
|------------|-----------|---------------|---------------|
| 20% drop    | 40         | 8 days         | ~1 week       |
| 15% drop    | 60         | 12 days        | ~2 weeks      |
| 10% drop    | 100        | 20 days        | ~3 weeks      |
| 5% drop     | 400        | 80 days        | ~3 months     |


# ═══════════════════════════════════════════════════════════════════
# 4. AGENT CORRELATION & REDUNDANCY ANALYSIS
# ═══════════════════════════════════════════════════════════════════

## 4.1 Why Redundancy Matters

### Wasted LLM Cost
- Each agent call costs tokens. Redundant agents are literal waste.
- Approximate cost per signal:
  - Claude Opus: ~$0.05-0.15 per signal (depends on context length).
  - GPT-4: ~$0.04-0.12 per signal.
  - Gemini Pro: ~$0.01-0.03 per signal.
- With 12 agents, 4 cycles/day, 5 coins: 240 signals/day.
- If 2 agents are redundant: saving ~40 signals/day = ~$2-6/day = $60-180/month.
- Not trivial at scale. More important: opportunity cost of not running a BETTER agent.

### False Consensus Inflation
- The aggregator uses Bayesian log-odds combination.
- If two agents always agree, they count as two independent votes.
- But they're NOT independent — they're seeing the same thing.
- Effect: the aggregated confidence is artificially inflated.
- Example:
  - 3 independent agents vote BULLISH with conviction 7: aggregated confidence = X.
  - 2 of those 3 are actually redundant (always agree): true confidence should be Y.
  - X > Y. The fund takes larger positions than justified.
  - This is a RISK MANAGEMENT problem, not just a cost problem.

### Condorcet Jury Theorem Violation
- Condorcet: if each juror is >50% accurate and votes independently,
  majority rule accuracy increases with more jurors.
- 5 independent models at 60% accuracy: majority rule gives 68.3%.
- 7 independent models at 60%: majority rule gives 71.0%.
- BUT if models are correlated:
  - 5 models at 60% accuracy, pairwise correlation 0.5:
    effective independent voters ≈ 3.3. Majority accuracy ≈ 63.5%.
  - 5 models at 60% accuracy, pairwise correlation 0.8:
    effective independent voters ≈ 2.0. Majority accuracy ≈ 60.7%.
  - The benefit of aggregation nearly vanishes with high correlation.
- CORE INSIGHT: Adding more agents helps ONLY if they bring independent signal.
  A worse agent (55% accuracy) that is independent may add more value than
  a better agent (65% accuracy) that is correlated with existing agents.

## 4.2 Agreement Rate Calculation

### Definition
- For agents A and B, agreement_rate = # signals where A and B choose the same
  direction / # signals where A and B both produced a signal for the same symbol
  at the same time (co-occurrences).

### Formula
- agreement(A, B) = Σ(I(dir_A_i == dir_B_i)) / N_co
- Where:
  - I() = indicator function (1 if true, 0 if false)
  - dir_A_i = direction of agent A on signal i
  - dir_B_i = direction of agent B on signal i
  - N_co = number of co-occurrences (both agents produced a signal for same symbol, same cycle)

### Weighted Agreement (conviction-aware)
- Simple agreement ignores conviction levels.
- Weighted agreement accounts for HOW STRONGLY they agree.
- weighted_agreement(A, B) = Σ(I(dir_A_i == dir_B_i) × min(conv_A_i, conv_B_i)) / Σ(max(conv_A_i, conv_B_i))
- Two agents agreeing at conviction 8 is MORE concerning than agreeing at conviction 3.

## 4.3 Correlation Thresholds

### Classification
| Agreement Rate | Classification | Interpretation | Action |
|---------------|---------------|----------------|--------|
| > 90%          | Highly redundant | Nearly identical agents | Eliminate one |
| 80-90%         | Redundant      | Minimal independent info | Strong candidate for elimination |
| 60-80%         | Correlated     | Some shared signal, some independent | Reduce combined weight |
| 40-60%         | Independent    | Healthy diversity | Ideal for aggregation |
| 20-40%         | Contrarian     | Systematic disagreement | Investigate — may indicate specialization |
| < 20%          | Anti-correlated | Almost always opposite | One agent may be anti-predictive |

### Minimum Co-occurrences for Reliable Correlation
- n < 10: Unreliable. Do not report correlation. Too much noise.
- 10 <= n < 20: Crude estimate. Report with large confidence interval.
- 20 <= n < 50: Moderate reliability. Report with caveat.
- n >= 50: Reliable. Can make decisions based on this.

### Statistical Test for Correlation Significance
- H0: agreement_rate = expected_by_chance.
- If both agents have base rates p_A and p_B for BULLISH signals:
  - Expected chance agreement = p_A × p_B + (1-p_A) × (1-p_B).
  - Example: if both agents are BULLISH 60% of the time:
    - Expected agreement = 0.6 × 0.6 + 0.4 × 0.4 = 0.52.
    - Observed agreement of 80% is meaningful (vs expected 52%).
  - Test: chi-squared or Fisher's exact on the 2x2 contingency table.

## 4.4 Cross-Team vs Within-Team Correlation

### Within-Team Correlation: Expected and OK
- Agents on the same team see the SAME DATA.
  - Technical agents all see candles + indicators → high correlation expected.
  - Sentiment agents all see Fear & Greed + social data → high correlation expected.
- Within-team agreement > 70% is normal and expected.
- Within-team agreement > 90% is still concerning — agents are not differentiating.
- The team MANAGER is supposed to synthesize; if agents are >90% correlated,
  the manager adds no value. Consider reducing from 3 agents to 2.

### Cross-Team Correlation: Concerning
- Teams see DIFFERENT DATA. Cross-team correlation should be lower.
- Cross-team agreement > 70% suggests:
  1. Hidden shared data source (e.g., both using price data as primary signal).
  2. Market regime domination (everything looks bullish in a bull market).
  3. LLM anchoring bias (the LLM has a tendency toward certain conclusions).

### Expected Correlation Matrix (Syndicate Baseline)
| Team Pair              | Expected Agreement | Concern If Above |
|-----------------------|-------------------|-----------------|
| TrendAgent ↔ SignalAgent    | 65-75%      | 85%             |
| TrendAgent ↔ TimingAgent    | 55-65%      | 80%             |
| SignalAgent ↔ TimingAgent   | 60-70%      | 80%             |
| Technical ↔ Sentiment       | 45-60%      | 70%             |
| Technical ↔ Fundamental     | 40-55%      | 65%             |
| Technical ↔ On-Chain        | 40-55%      | 65%             |
| Technical ↔ Macro           | 35-50%      | 60%             |
| Sentiment ↔ Fundamental     | 40-55%      | 65%             |
| Sentiment ↔ Macro           | 45-60%      | 70%             |
| Sentiment ↔ On-Chain        | 40-55%      | 65%             |
| Fundamental ↔ On-Chain      | 35-50%      | 60%             |
| Fundamental ↔ Macro         | 40-55%      | 65%             |
| Macro ↔ On-Chain            | 35-50%      | 60%             |

### Why Sentiment ↔ Macro Correlation is Higher
- Both teams incorporate Fear & Greed Index data.
- MarketSentimentAgent uses F&G directly.
- MacroAgent uses F&G as one of many macro indicators.
- Expected overlap: 45-60%. If > 70%, investigate if F&G is driving both signals.
- Mitigation: ensure Macro weight downplays F&G when Sentiment team already captures it.

## 4.5 Impact on Aggregation

### Bayesian Weight Adjustment for Correlation
- If agents A and B have agreement rate > 80%, their combined Bayesian weight
  should be reduced.
- Effective weight: w_eff = w_A + w_B × (1 - rho(A,B))
  - Where rho = normalized correlation (0 = independent, 1 = identical).
  - If rho = 0.8: w_eff = w_A + 0.2 × w_B. Agent B adds only 20% incremental info.
  - If rho = 0.3: w_eff = w_A + 0.7 × w_B. Agent B adds 70% incremental info.

### How to Estimate rho from Agreement Rate
- rho ≈ (agreement_rate - expected_chance_agreement) / (1 - expected_chance_agreement)
- Example:
  - Expected chance agreement: 52% (as computed above).
  - Observed agreement: 80%.
  - rho = (0.80 - 0.52) / (1 - 0.52) = 0.28 / 0.48 = 0.58.
  - Agent B's effective additional weight: 42% of its standalone weight.

### Recommendation for Syndicate Aggregator
- Current implementation does NOT adjust for within-team correlation.
- The team manager synthesis partially handles this by producing ONE team signal.
- But the aggregator still treats each team's signal as fully independent.
- If cross-team agreement > 70% persistently, recommend:
  1. Investigate shared data sources.
  2. Apply correlation discount at the aggregator level.
  3. Diversify LLM providers between correlated teams.

## 4.6 Cluster Detection

### Hierarchical Clustering of Agreement Matrices
1. Compute pairwise agreement matrix (12 × 12 for 12 agents).
2. Convert to distance: d(A,B) = 1 - agreement(A,B).
3. Apply agglomerative clustering (Ward's method or complete linkage).
4. Cut dendrogram at distance threshold = 0.3 (agreement > 70%).
5. Clusters of >1 agent at this level are potentially redundant.

### What to Do with Clusters
- Cluster of 2 within same team: expected. The manager handles synthesis.
- Cluster of 2 across different teams: concerning. Investigate shared data.
- Cluster of 3+: highly concerning. Multiple agents are essentially one voice.
  - Calculate the "cluster IC": does the cluster as a whole have higher IC
    than any individual member?
  - If cluster IC ≈ individual IC: redundancy confirmed. Reduce to 1-2 agents.
  - If cluster IC > individual IC: the cluster has value despite correlation.
    Keep, but apply correlation discount in aggregation.

## 4.7 Condorcet Jury Theorem: Applied to Syndicate

### The Mathematics
- N voters, each with accuracy p > 0.50, voting independently.
- P(majority correct) = Σ_{k=⌈N/2⌉}^{N} C(N,k) × p^k × (1-p)^(N-k)

### Syndicate-Specific Calculations (5 teams)

| Individual Accuracy | Majority Correct (5 independent teams) |
|--------------------|---------------------------------------|
| 51%                | 52.0%                                 |
| 55%                | 59.3%                                 |
| 60%                | 68.3%                                 |
| 65%                | 76.5%                                 |
| 70%                | 83.7%                                 |
| 75%                | 89.6%                                 |

### With Correlation (Using Correlated Jury Theorem)
- Effective independent voters: N_eff = 1 + (N - 1) × (1 - avg_rho)
  - 5 teams, avg_rho = 0.3: N_eff = 1 + 4 × 0.7 = 3.8.
  - 5 teams, avg_rho = 0.5: N_eff = 1 + 4 × 0.5 = 3.0.
  - 5 teams, avg_rho = 0.7: N_eff = 1 + 4 × 0.3 = 2.2.

| Avg Correlation | Effective N | Majority Acc (p=0.60) |
|----------------|------------|----------------------|
| 0.0            | 5.0        | 68.3%                |
| 0.2            | 4.2        | 66.4%                |
| 0.3            | 3.8        | 65.2%                |
| 0.5            | 3.0        | 63.0%                |
| 0.7            | 2.2        | 61.1%                |
| 0.9            | 1.4        | 60.2%                |

### Practical Recommendation
- Optimize for DIVERSITY of signal sources over individual accuracy.
- Adding a 55%-accurate agent from an independent data source adds more value
  than improving an existing 60%-accurate agent to 65%.
- Cross-provider diversity bonus (+15% when 2+ LLM providers agree) in the
  aggregator is well-justified by Condorcet analysis: provider diversity
  is a proxy for decision process independence.


# ═══════════════════════════════════════════════════════════════════
# 5. DATA SOURCE EVALUATION METHODOLOGY
# ═══════════════════════════════════════════════════════════════════

## 5.1 Framework for Evaluating Indicators

### Evaluation Criteria (weighted)
1. **Predictive Power (40%)**: Does it improve accuracy above baseline?
   - Measured by: IC, accuracy improvement, Sharpe improvement.
2. **Stability (20%)**: Does it work across regimes and time periods?
   - Measured by: variance of rolling accuracy, number of regime transitions survived.
3. **Timeliness (15%)**: How quickly does the signal arrive after the opportunity?
   - Measured by: latency from optimal entry, percentage of move captured.
4. **Data Quality (15%)**: Is the data reliable, available, consistent?
   - Measured by: uptime %, data gaps, API reliability.
5. **Independence (10%)**: Does it add information beyond existing signals?
   - Measured by: correlation with existing signals, marginal IC contribution.

### Evaluation Protocol
1. Backtest period: minimum 2 years, covering at least 2 regime transitions.
2. Out-of-sample period: most recent 6 months (never use for calibration).
3. Compare: strategy with indicator vs strategy without indicator.
4. Measure: accuracy delta, Sharpe delta, max drawdown delta.
5. Significance test: paired t-test on daily returns (with vs without).
6. Report: effect size (Cohen's d), p-value, practical significance.

## 5.2 RSI(14) — Relative Strength Index

### Mechanism
- RSI = 100 - (100 / (1 + RS))
- RS = average gain over 14 periods / average loss over 14 periods.
- Range: 0-100. Traditional thresholds: <30 oversold, >70 overbought.

### Historical Performance on BTC

**RSI < 30 (Oversold on daily chart):**
- Occurrence frequency: Extremely rare. Only ~3 confirmed instances in BTC's
  post-2017 history (Jan 2015, Dec 2018, Mar 2020, briefly Nov 2022).
- 7-day average return after RSI < 30: +4% to +8%.
- 30-day average return after RSI < 30: +5% to +15%.
- Win rate (positive 7-day return): ~60-65%.
- Context matters enormously:
  - Mar 2020 (COVID crash, RSI ~20): 30-day return = +50%. Best buy in history.
  - Nov 2022 (FTX collapse, RSI ~28): 30-day return = +3%. Slow recovery.
  - Difference: Mar 2020 was a liquidity crisis (temporary). Nov 2022 was a
    solvency crisis (structural). RSI alone cannot distinguish these.

**RSI > 70 (Overbought on daily chart):**
- NOT a reliable sell signal on BTC. This is a CRITICAL finding.
- In the 2021 bull run, RSI stayed above 70 for weeks at a time.
  - Nov 2020 - Jan 2021: RSI above 70 for 18 of 60 days. BTC went from $19k to $40k.
  - Feb 2021 - Apr 2021: RSI above 70 for 14 days. BTC went from $33k to $64k.
  - Selling at RSI > 70 would have missed massive gains.
- RSI > 70 only works as a sell signal in ranging markets or late-stage tops.
- When combined with divergence (price making new highs, RSI making lower highs):
  win rate of short signals improves to ~60%.

**RSI-Based Strategy Backtest (2018-2022):**
- Strategy: Buy when RSI(14) < 30, sell when RSI(14) > 70. BTC only.
- Total return: 773.65% vs 275.22% buy-and-hold.
- BUT: this result is heavily influenced by the Mar 2020 entry.
  Remove that single trade and return drops to ~180-250%.
- Sharpe ratio: 0.3-0.7 (highly period-dependent).
- Maximum drawdown: -55% (almost as bad as buy-and-hold's -73%).

**Standalone RSI(14) Assessment:**
- Standalone win rate: 40-55% depending on timeframe and threshold.
- Standalone Sharpe: 0.3-0.7.
- Verdict: RSI is a SUPPORTING indicator, not a standalone signal.
  - Best use: mean reversion entry filter. Buy when RSI < 35 AND other signals agree.
  - Worst use: overbought sell signal in trending markets.
  - Never use RSI alone for SHORT signals.

### RSI Integration into Syndicate
- TrendAgent (1D) and SignalAgent (4H) both receive RSI data.
- Correct usage: RSI should influence conviction level, not direction alone.
  - RSI < 30 + other bullish signals → increase conviction by 1-2 points.
  - RSI > 70 + other bullish signals → do NOT reduce conviction (trend may continue).
  - RSI > 70 + bearish signals → increase conviction by 1-2 points for SHORT.
  - RSI divergence (price up, RSI down) → strongest RSI signal. Weight heavily.

## 5.3 MACD — Moving Average Convergence Divergence

### Mechanism
- MACD Line = EMA(12) - EMA(26)
- Signal Line = EMA(9) of MACD Line
- Histogram = MACD Line - Signal Line
- Bullish crossover: MACD Line crosses above Signal Line.
- Bearish crossover: MACD Line crosses below Signal Line.

### Win Rates by Timeframe (BTC, 2019-2024)

| Timeframe | Bullish Crossover Win Rate | Bearish Crossover Win Rate |
|-----------|--------------------------|--------------------------|
| 1H        | 37-40%                   | 32-38%                   |
| 4H        | 45-50%                   | 40-47%                   |
| 1D        | 50-55%                   | 45-52%                   |
| 1W        | 55-60%                   | 50-55%                   |

### Key Findings
- Bullish crossovers are MORE reliable than bearish in crypto.
  - Structural long bias: crypto has positive expected return over long periods.
  - Bearish MACD crossovers produce more false signals due to this bias.
  - Recommendation: weight bullish MACD crossovers more heavily than bearish.

**MACD + RSI Combined Filter:**
- MACD bullish crossover + RSI < 50 (not overbought): win rate 65-73% on 1D.
- MACD bullish crossover + RSI < 40 (oversold region): win rate up to 77%.
- This combination is one of the strongest two-indicator signals in crypto.

**MACD + Trailing Stop:**
- MACD crossover entry, trailing stop at 2 ATR:
  - Sharpe: 1.07 (vs 0.6-0.8 for MACD alone).
  - Improvement comes from cutting losses faster, not from better entries.

**MACD Multi-Coin Portfolio (BTC + ETH + ADA):**
- Diversified MACD strategy across 3 assets:
  - Sharpe: 1.44.
  - Maximum drawdown: -28% (vs -55% for single-asset).
  - The diversification benefit is real because cross-asset MACD crossovers
    are not perfectly correlated.

**MACD Histogram as Momentum Indicator:**
- Rising histogram (becoming more positive) = strengthening bullish momentum.
- Falling histogram (becoming less positive) = weakening bullish momentum.
- Histogram zero-line cross = MACD crossover (lagging confirmation).
- Best use: histogram slope as a momentum filter.
  - Entry: MACD crossover AND histogram rising for >= 2 bars.
  - Skip: MACD crossover but histogram already declining.
  - This filter increases win rate by 5-8% at the cost of missing ~20% of entries.

### MACD Integration into Syndicate
- SignalAgent (4H) is the primary MACD consumer.
- MACD histogram is included in TechnicalIndicators model (macd_histogram).
- The deterministic baseline in SignalAggregator uses MACD: +1.0 score if histogram > 0.
- Recommendation: multi-timeframe MACD alignment (1D MACD + 4H MACD agreeing)
  should boost conviction by 2 points.

## 5.4 Moving Average Crossovers

### Golden Cross (SMA50 > SMA200)

**Performance on BTC (2013-2024):**
- Average 30-day return after golden cross: +9.6% to +14.8%.
- Win rate (positive 30-day return): 70-81%.
- BUT highly regime-dependent:

| Macro Condition        | Golden Cross Win Rate |
|----------------------|---------------------|
| Fed easing cycle      | 81.2%               |
| Fed tightening cycle  | 59.3%               |
| Low VIX (<20)         | 74.3%               |
| High VIX (>30)        | 52.7%               |
| Post-halving year     | 85.0%               |
| Pre-halving year      | 62.1%               |

**Key Insight:** Golden Cross + easing + post-halving is the highest-conviction
bullish signal in crypto history. When these three align, conviction should be 9-10.

### Death Cross (SMA50 < SMA200)

**Counter-intuitive finding:**
- Death Cross is a CONTRARIAN BUY opportunity 64% of the time.
- Average 30-day return after death cross: +2.3% to +5.1%.
- Why: by the time SMAs cross (lagging indicators), the sell-off is usually done.
  The death cross itself is late.
- Exception: structural bear markets (2014, 2018, 2022).
  - In these cases, death cross preceded further -30% to -60% decline.
  - Distinguishing factor: if death cross occurs WITH funding rates deeply negative
    AND exchange reserves rising, it's a genuine structural bear. Short or stay out.

### Moving Average Integration into Syndicate
- TrendAgent (1D) is the primary MA consumer.
- SMA20, SMA50, SMA200 are in TechnicalIndicators.
- The deterministic baseline uses SMA20 > SMA50: +1.0 score.
- Recommendation: add SMA50 vs SMA200 (golden/death cross) as a
  REGIME indicator, not a trade signal. Feed it into the CEO's regime classification.

## 5.5 Volume Analysis

### Volume Spike + Price Movement

**Volume Spike (>2x 20-day average):**
- Volume spike + price up: 55-65% probability of continued follow-through over next 48h.
- Volume spike + price down: 50-55% probability of continued decline.
  Lower because panic selling exhausts itself faster than accumulation.
- Sustained volume (elevated >1.5x for 3+ bars): 60-68% breakout follow-through.

**False Breakout Detection:**
- Single-day volume spike with price reversal next day: 30-40% of all spikes.
- Multi-day sustained volume with price follow-through: much more reliable.
- Rule: ignore single-bar volume spikes. Require 2+ consecutive elevated bars.
  - This reduces false breakout exposure from 30-40% to 15-20%.

**Volume Dry-Up Before Breakout:**
- Volume declining for 5+ days, then sudden spike (>3x average):
  - 70-75% probability of genuine breakout (not false).
  - The "volume compression" before the expansion is a strong confirming signal.
  - Best application: combine with Bollinger Band squeeze (bb_width < 20-day low).

### Volume Ratio in Syndicate
- volume_ratio field in TechnicalIndicators: current / avg.
- Deterministic baseline: volume_ratio > 1.5 adds +0.5 to score (confirming direction).
- Recommendation: add volume_ratio > 3.0 as a special "breakout" flag.
  When combined with BB squeeze, this is a high-conviction setup.

## 5.6 Fear & Greed Index

### Overview
- Composite index: 0 (extreme fear) to 100 (extreme greed).
- Components: volatility (25%), market momentum/volume (25%), social media (15%),
  surveys (15%), BTC dominance (10%), Google Trends (10%).
- Available via alternative.me API (which Syndicate's data layer queries).

### Performance by F&G Level

**Extreme Fear (F&G < 10):**
- Sharpe ratio of buying at F&G < 10: 8.0 (extraordinary).
- Positive 30-day return: ~85% of the time.
- Average 30-day return: +25-40%.
- This is the single strongest contrarian indicator in crypto.
- But RARE: F&G < 10 occurs only ~3-5 days per year on average.

**Fear (F&G < 20):**
- Positive 30-day returns: ~80%.
- Average 30-day return: +12-20%.
- More frequent: ~15-25 days per year.
- Still very strong contrarian signal.

**Greed (F&G > 80) Sustained 14+ Days:**
- ~70% chance of >20% drawdown within 90 days.
- NOT an immediate sell signal. Greed can persist for weeks in bull markets.
- The "sustained 14+ days" qualifier is critical:
  - F&G > 80 for 1 day: almost meaningless. Often just a spike.
  - F&G > 80 for 7 days: mild concern. Start tightening stops.
  - F&G > 80 for 14+ days: genuine overheating. Reduce position sizes by 30%.
  - F&G > 90 for 7+ days: very high probability of correction. Max caution.

**Best F&G-Based Strategy:**
- Buy at F&G <= 10, sell at F&G > 35.
  - Annualized return: 14.6% (risk-adjusted).
  - Win rate: ~85%.
  - Max drawdown: -18%.
  - Sharpe: 2.1.
- Fear-weighted DCA (allocate more when F&G is lower):
  - +1,145% total return vs +202% standard DCA (2018-2024 backtest).
  - The most robust strategy for a long-term crypto allocation.

### CRITICAL WARNING: F&G Failure Mode
- F&G < 15 fails during ACTIVE CONTAGION events.
  - Luna collapse (May 2022): F&G dropped to 8. Buying was 5 months early.
    Continued decline to Nov 2022 low.
  - FTX collapse (Nov 2022): F&G dropped to 6. Buying was 2 months early.
    But recovery came faster.
- Pattern: when F&G < 15 is caused by a SPECIFIC solvency event (exchange failure,
  protocol death), the fear is JUSTIFIED and buying is premature.
- Rule: F&G < 15 + NO specific contagion event → BUY with conviction 8-9.
  F&G < 15 + active contagion → WAIT. Do not buy until contagion subsides.
  Contagion indicators: exchange reserves rising, stablecoin depegs, cross-protocol
  liquidation cascades.

### F&G Integration into Syndicate
- MarketSentimentAgent consumes F&G data.
- MacroAgent also incorporates F&G as one of many inputs.
- WARNING: dual consumption creates cross-team correlation (see Section 4.4).
- Recommendation: if Sentiment team already has strong F&G signal,
  Macro team should downweight F&G to avoid double-counting.

## 5.7 Funding Rates

### Mechanism
- Perpetual futures funding rate: paid every 8 hours.
- Positive funding: longs pay shorts (bullish crowding).
- Negative funding: shorts pay longs (bearish crowding).
- Funding is a DIRECT measure of market positioning.

### Performance

**Deeply Negative Funding (< -0.05% per 8h):**
- Bounce probability within 24h: 70-75%.
- Average bounce magnitude: +5-15%.
- This is a high-conviction mean-reversion signal.
- Why: extremely negative funding means shorts are overcrowded.
  Even a small trigger forces short covering → price spike.
- Win rate by magnitude:
  - Funding < -0.01%: 55-60% bounce probability (weak signal).
  - Funding < -0.03%: 60-65% bounce probability.
  - Funding < -0.05%: 70-75% bounce probability (strong signal).
  - Funding < -0.10%: 80-85% bounce probability (extreme — very rare).

**Extremely Positive Funding (> +0.1% per 8h):**
- Correction probability within 48h: 60-70%.
- Average correction magnitude: -5-10%.
- Less reliable than negative extremes because longs can sustain high funding
  longer (structural long bias in crypto bull markets).

**Funding Rate Mean Reversion Strategy:**
- Buy when funding < -0.05%, sell when funding normalizes (> -0.01%).
- Win ratio: high (~70%). But risk-reward is mediocre because:
  - The bounce is often sharp but short-lived.
  - Getting stopped out in strong downtrends is the main failure mode.
- Sharpe: 0.7-1.0. Best when combined with other confirmation signals.

### Funding Rate Integration into Syndicate
- On-Chain agents consume funding rate data.
- CryptoMacroAgent also monitors funding as a positioning indicator.
- Key interaction: if BOTH funding and On-Chain whale flow agree on direction,
  that's a very strong signal (smart money AND positioning aligned).

## 5.8 Multi-Timeframe Alignment

### The Single Largest Edge Enhancer

**Performance Data:**
- 3 timeframes aligned (1H, 4H, 1D all agree on direction):
  - Win rate: 64.7%.
  - Average return per signal: +2.1%.
  - Profit factor: 1.82.
- Timeframes NOT aligned (at least one disagrees):
  - Win rate: 30.9%.
  - Average return per signal: -0.3%.
  - Profit factor: 0.65 (losing strategy).
- The gap: 33.8 percentage points. This is the SINGLE LARGEST edge enhancer
  available to Syndicate. No individual indicator comes close.

### How Syndicate Implements This
- Technical team uses Elder's Triple Screen:
  - TrendAgent (1D) → strategic direction (the "tide").
  - SignalAgent (4H) → tactical entry/exit (the "wave").
  - TimingAgent (1H) → precise timing (the "ripple").
- TechnicalManager synthesizes:
  - FULLY_ALIGNED: all 3 agree. Timeframe boost = 1.2x weight.
  - MOSTLY_ALIGNED: 2/3 agree. Timeframe boost = 1.0x (neutral).
  - CONFLICTING: strong disagreement. Timeframe boost = 0.7x.
- The aggregator applies additional technical gate:
  - Technical opposes + CONFLICTING → 0.6x confidence penalty.

### Recommendations for Signal Health Reports
- Track FULLY_ALIGNED percentage over time. Expected: 35-45% of signals.
  - If FULLY_ALIGNED drops below 25%: market is choppy. Reduce overall position sizes.
  - If FULLY_ALIGNED rises above 55%: strong trend. Increase conviction for aligned trades.
- When evaluating Technical team accuracy, break it down by alignment level:
  - FULLY_ALIGNED signals should be 60-70% accurate.
  - CONFLICTING signals should be 40-50% accurate (essentially coin flips).
  - If CONFLICTING accuracy is above 55%, the conflict detection might be too sensitive.
  - If FULLY_ALIGNED accuracy is below 55%, the alignment criteria may be wrong.

## 5.9 Combined Strategy Rankings by Sharpe

### Research-Validated Combinations (BTC, 2018-2024)

| Rank | Strategy Combination                  | Sharpe | Win Rate | Max DD |
|------|---------------------------------------|--------|----------|--------|
| 1    | MACD + RSI + Multi-TF Filter          | 1.0-1.44 | 64-77% | -22%   |
| 2    | MACD + RSI + Bollinger Band           | 0.9-1.30 | 60-72% | -25%   |
| 3    | MACD + RSI (no additional filter)     | 0.8-1.20 | 55-65% | -30%   |
| 4    | RSI + Funding Rate + Bollinger        | 0.7-1.00 | 55-62% | -28%   |
| 5    | RSI + Volume + SMA Crossover          | 0.6-0.90 | 52-60% | -32%   |
| 6    | MACD alone (1D)                       | 0.5-0.80 | 50-55% | -40%   |
| 7    | RSI alone (buy <30, sell >70)         | 0.3-0.70 | 40-55% | -55%   |
| 8    | SMA Crossover alone (Golden Cross)    | 0.3-0.60 | 50-55% | -45%   |
| 9    | Volume spike alone                    | 0.2-0.50 | 45-55% | -50%   |
| 10   | F&G contrarian alone                  | 0.4-0.80 | 65-80% | -40%   |

### Interpretation for Syndicate
- Top strategies all involve COMBINATION + FILTERING.
- No single indicator beats a well-combined set.
- This validates Syndicate's multi-team architecture:
  - Technical team: MACD + RSI + multi-timeframe.
  - Sentiment team: F&G + social + smart money.
  - Combination across teams further improves results.
- The aggregator's Bayesian combination is the final synthesis layer.

## 5.10 Additional Data Source Assessment

### On-Chain: Exchange Net Flows
- Large outflows (coins leaving exchanges): bullish 60-65% of time.
  - Interpretation: holders moving to self-custody = long-term conviction.
- Large inflows (coins entering exchanges): bearish 55-60% of time.
  - Interpretation: preparing to sell.
- Best signal: sustained outflows (3+ consecutive days of net outflows > $100M for BTC).
  - Follow-through rate: 65-70% for positive 7-day return.
- Failure mode: exchange migrations (restructuring wallets) create false signals.

### On-Chain: Whale Accumulation
- Wallets holding 1,000+ BTC increasing balance: bullish 65-70%.
- Wallets holding 1,000+ BTC decreasing balance: bearish 55-65%.
- This is the SmartMoneyAgent's primary signal.
- Caveat: whale wallet identification is imperfect. Some "whales" are exchange wallets.
- Latency: whale moves take 1-7 days to fully materialize on-chain.

### Derivatives: Open Interest
- Rising OI + rising price: trend continuation 55-60%.
- Rising OI + falling price: short positioning, potential squeeze 60-65%.
- Falling OI + any direction: position unwinding, reduced conviction.
- OI alone is weak. Combined with funding rates, much stronger.

### Macro: DXY (Dollar Index)
- BTC correlation with DXY: -0.40 to -0.60 (since 2020).
- Strong DXY (rising): generally bearish for crypto.
- Weak DXY (falling): generally bullish for crypto.
- This is a regime indicator, not a timing signal.
- Update frequency for CryptoMacroAgent: daily check is sufficient.

### Macro: BTC Dominance
- Rising BTC.D: capital rotating from alts to BTC (risk-off within crypto).
- Falling BTC.D: capital rotating from BTC to alts (risk-on within crypto).
- Does NOT predict BTC direction directly, but predicts ALT/BTC relative performance.
- Useful for the CEO's sector_weights allocation decisions.

### Social: Weighted Social Sentiment
- Reddit, X/Twitter, Telegram mentions weighted by account quality.
- Very noisy. IC typically 0.01-0.03.
- Best use: detect EXTREME sentiment divergence (social euphoria + price flat = top signal).
- Worst use: following social consensus (social lags price by 12-48h typically).
- SocialSentimentAgent should focus on EXTREMES, not direction.

## 5.11 Data Source Reliability Matrix

| Data Source        | Availability | Latency   | Noise Level | Standalone IC | Best Combined With |
|-------------------|-------------|-----------|-------------|--------------|-------------------|
| Price/Candles     | 99.9%       | Real-time | Low         | N/A          | Everything        |
| RSI(14)           | 99.9%       | Computed  | Medium      | 0.02-0.04    | MACD, BB          |
| MACD              | 99.9%       | Computed  | Medium      | 0.03-0.06    | RSI, Volume       |
| SMA/EMA           | 99.9%       | Computed  | Low         | 0.01-0.03    | Volume, RSI       |
| Bollinger Bands   | 99.9%       | Computed  | Medium      | 0.02-0.04    | RSI, Volume       |
| ATR               | 99.9%       | Computed  | Low         | N/A (risk)   | Position sizing   |
| Volume            | 99.5%       | Real-time | High        | 0.01-0.03    | Price patterns    |
| Fear & Greed      | 98%         | Daily     | Medium      | 0.03-0.07    | On-chain, Macro   |
| Funding Rates     | 99%         | 8-hourly  | Low         | 0.04-0.08    | OI, Price         |
| Open Interest     | 98%         | Hourly    | Medium      | 0.02-0.04    | Funding, Volume   |
| Exchange Flows    | 95%         | Variable  | High        | 0.03-0.06    | Whale tracking    |
| Whale Wallets     | 90%         | Variable  | High        | 0.04-0.08    | F&G, Funding      |
| Social Sentiment  | 85%         | Hourly    | Very High   | 0.01-0.03    | F&G, Extremes     |
| Macro Indicators  | 99%         | Daily     | Low         | 0.01-0.03    | Regime context    |
| DeFi TVL          | 95%         | Hourly    | Medium      | 0.01-0.02    | Fundamental       |
| News Sentiment    | 80%         | Variable  | Very High   | 0.01-0.02    | Event detection   |


# ═══════════════════════════════════════════════════════════════════
# 6. OVERFITTING DETECTION & OUT-OF-SAMPLE VALIDATION
# ═══════════════════════════════════════════════════════════════════

## 6.1 Walk-Forward Analysis Methodology

### Protocol
1. **Training window**: use N months of data to calibrate signal weights/parameters.
2. **Testing window**: apply calibrated model to next M months (out-of-sample).
3. **Slide forward**: move both windows by M months and repeat.
4. **Aggregate OOS results**: combine all out-of-sample periods for final assessment.

### Recommended Settings for Crypto
- Training window: 6 months.
- Testing window: 1 month.
- Slide step: 1 month.
- Minimum: 3 full slides (= 9 months of data total).
- Ideal: 12+ slides (= 18+ months of data).

### Why Walk-Forward Matters for Syndicate
- Agent weights evolve based on accuracy (the weight formula uses track record).
- If weights are optimized on the same data used to measure performance:
  - In-sample performance is inflated.
  - True out-of-sample performance will be lower.
- Walk-forward ensures that weight updates never peek at future data.

## 6.2 In-Sample vs Out-of-Sample Performance Gap

### Healthy Gap
- In-sample Sharpe 1.5 → Out-of-sample Sharpe 1.2 → gap = 20%. Healthy.
- In-sample accuracy 68% → Out-of-sample accuracy 62% → gap = 9%. Healthy.

### Concerning Gap
- In-sample Sharpe 2.0 → Out-of-sample Sharpe 0.8 → gap = 60%. Overfit.
- In-sample accuracy 75% → Out-of-sample accuracy 55% → gap = 27%. Likely overfit.

### Thresholds
| IS/OOS Gap    | Assessment     | Action                               |
|--------------|---------------|---------------------------------------|
| < 10%         | Excellent      | Model is robust.                      |
| 10-20%        | Healthy        | Normal regularization loss.           |
| 20-30%        | Concerning     | Review parameterization. Simplify.    |
| 30-50%        | Overfit        | Reduce parameters. Increase training. |
| > 50%          | Severely overfit | Model is unreliable. Rebuild.       |

## 6.3 Data Snooping Bias

### What It Is
- Testing many strategies/parameters and reporting only the best result.
- "We tried 100 parameter combinations and found one with 80% accuracy!"
  → Expected by chance even with random data.

### How to Detect It
1. Count the number of configurations tested (explicitly or implicitly).
2. Apply multiple comparison correction to the reported p-value.
3. If corrected p-value > 0.05, the result may be snooped.

### Syndicate-Specific Risks
- 12 agents with different prompts → 12 implicit parameter choices.
- Testing 5 conviction thresholds × 3 weight formulas × 4 window sizes = 60 configs.
- Each config that "works" needs to survive:
  - Bonferroni correction (divide alpha by 60).
  - Walk-forward validation (works in multiple OOS periods).
  - Different market regimes (works in both bull and bear).

### Minimum Out-of-Sample Period for Crypto
- 6 months minimum.
- Must include at least 2 regime transitions:
  - Bull → ranging, ranging → bear, bear → bull, etc.
  - A strategy that only worked in a bull market is not validated.
- Ideal: 12 months covering a full halving cycle transition.

## 6.4 Cross-Validation for Time Series

### Why Standard K-Fold Fails
- K-fold randomly splits data, breaking temporal order.
- Future data leaks into training set → inflated performance.
- NEVER use standard k-fold for financial time series.

### Purged and Embargoed Walk-Forward CV
1. Split timeline into K non-overlapping blocks.
2. For each fold k, train on blocks 1 to k-1, test on block k.
3. Purge: remove training samples within P bars of test period start.
   - For Syndicate: P = 24 (one day of signals).
4. Embargo: remove test samples within E bars of training period end.
   - For Syndicate: E = 12 (half a day).
5. This prevents autocorrelation leakage.

### Combinatorially Purged Cross-Validation (CPCV)
- More data-efficient than simple walk-forward.
- All non-overlapping combinations of train/test splits.
- Each observation used for testing exactly once.
- Recommended for Syndicate quarterly model reviews.

## 6.5 Deflated Sharpe Ratio (Bailey & Lopez de Prado)

### Why Regular Sharpe Overestimates
- Multiple strategy trials → selection bias.
- Non-normal returns → Sharpe misestimates.
- Short sample → high variance in Sharpe estimate.

### DSR Formula
- DSR = P(SR > 0 | SR_0 = median_of_all_trials)
  - Adjusts for: number of trials, skewness, kurtosis, sample size.
- Key inputs:
  - N: number of strategy trials attempted.
  - T: number of return observations.
  - skew: return distribution skewness.
  - kurt: return distribution excess kurtosis.

### Interpretation
- DSR > 0.95: Sharpe is likely genuine (survives deflation).
- DSR 0.50-0.95: Inconclusive. May be overfitting.
- DSR < 0.50: Sharpe is likely inflated by selection bias.

### Application to Syndicate
- When evaluating a new agent's Sharpe ratio:
  1. Count how many agent configurations were tried before this one.
  2. Compute DSR.
  3. If DSR < 0.50, the agent's performance is not yet proven.
- Minimum sample for meaningful DSR: T >= 60 days of returns.

## 6.6 Signs of Overfitting

### Red Flags
1. **In-sample Sharpe > 3.0**: Almost certainly overfit. Real strategies rarely exceed 2.5.
2. **Perfect accuracy at specific conviction levels**: e.g., "conviction 8 = 100% accuracy
   for 15 trades." This is sample noise, not a real edge.
3. **Excessive parameter sensitivity**: small parameter changes cause large performance swings.
4. **Curve-fitting on specific events**: strategy parameters seem tuned to capture known
   events (COVID crash, FTX collapse) but miss similar events out-of-sample.
5. **High Sharpe with low trade count**: Sharpe 3.0 on 12 trades is meaningless.
   Minimum: 50 trades for any Sharpe claim.
6. **Asymmetric performance across regimes**: Sharpe 2.0 in bull market, Sharpe -1.0 in
   bear market → the strategy only works in one regime. It's not alpha, it's beta exposure.

### How to Respond
- Do NOT fire an agent based on suspected overfitting alone.
- Instead: quarantine and observe OOS performance for 2-4 weeks.
- If OOS performance is within 20% of in-sample: not overfit, restore.
- If OOS performance is >30% below in-sample: overfitting confirmed. Adjust or fire.


# ═══════════════════════════════════════════════════════════════════
# 7. CRYPTO-SPECIFIC STATISTICAL CONSIDERATIONS
# ═══════════════════════════════════════════════════════════════════

## 7.1 Fat Tails and Non-Normal Returns

### The Problem
- Normal distribution assumes kurtosis = 3. BTC kurtosis ≈ 10.85.
- A diversified crypto basket: kurtosis ≈ 27.
- This means "tail events" (>3 sigma moves) occur ~10x more often than normal
  distribution predicts.
- Practical impact:
  - A "99% VaR" that assumes normality will be breached ~5-10% of the time.
  - Standard deviation UNDERSTATES risk in crypto.
  - Stop losses based on sigma will trigger more often than expected.

### Daily Return Distribution (BTC, 2015-2024)
- Mean daily return: ~0.15% (annualized: ~55%).
- Standard deviation daily: ~3.5% (annualized: ~66.8%).
- Skewness: slightly negative (-0.2 to -0.5). More large drops than large gains
  on a daily basis (even though cumulative return is positive).
- Range of daily returns: -38.27% to +40.04%.
  - Under normal distribution, a -38% daily move is a ~10-sigma event.
    That should occur once per age of the universe.
  - In reality: it happened on Mar 12, 2020 ("Black Thursday").

### BTC Annualized Volatility: 91.73% (long-term average)
- This is ~6x equity market volatility (~15%).
- During calm periods: 30-50% annualized vol.
- During crisis: 100-200%+ annualized vol.
- Implication for signal evaluation:
  - 0.5% daily move (Syndicate's MIN_MOVE_PCT) is within noise for BTC.
  - Consider adjusting MIN_MOVE_PCT to 1.0-1.5% for BTC, keep 0.5% for stables.
  - Or make MIN_MOVE_PCT a function of current vol (e.g., MIN_MOVE_PCT = ATR/price × 50%).

### Alternative Distribution Models
- Student's t-distribution with low degrees of freedom (df=3-5): better fit.
- Generalized Pareto Distribution (GPD) for tails: best for VaR estimation.
- Stable distributions (Levy alpha-stable): theoretically correct but hard to calibrate.
- Practical recommendation for Syndicate:
  - Use empirical distribution (percentile-based) rather than parametric.
  - For confidence intervals: bootstrap rather than normal approximation.
  - For risk management: use CVaR (Conditional Value at Risk) not VaR.

## 7.2 24/7 Markets

### Implications for Signal Evaluation
- No overnight gap risk: good for trend-following strategies.
- No "close" price: use end-of-period candle close as proxy.
- 4-hour cycle boundaries create micro-structure effects:
  - Funding rate settlement every 8 hours (00:00, 08:00, 16:00 UTC) creates
    predictable patterns around these times.
  - Volume spikes at settlement times are NOT directional signals — they're structural.
  - Recommendation: ignore volume spikes within ±30 min of funding settlement.

### "Trading Sessions" in 24/7 Markets
- Asian session (00:00-08:00 UTC): lowest volume, highest noise.
  - Signal accuracy during this window: ~3-5% lower than average.
- European session (08:00-16:00 UTC): moderate volume.
  - Signal accuracy: average.
- US session (14:00-22:00 UTC): highest volume, most institutional activity.
  - Signal accuracy: ~2-3% higher than average.
  - Whale movements during US hours are more likely to be genuine.
- Recommendation: weight signals from US session slightly higher (+5% weight).

### Weekend vs Weekday
- Weekend volume: ~30-40% lower than weekday average.
- Weekend volatility: often HIGHER relative to volume (thin order books).
- Weekend false breakout rate: ~10% higher than weekday.
- Recommendation: increase MIN_MOVE_PCT threshold by 0.2% on weekends.
  Or simply reduce position sizes by 20% for signals generated Sat/Sun.

## 7.3 Volatility Clustering (GARCH Effects)

### The Pattern
- High volatility begets high volatility. Low vol begets low vol.
- BTC daily returns show strong GARCH(1,1) effects:
  - ARCH coefficient (alpha): 0.05-0.15 (shock sensitivity).
  - GARCH coefficient (beta): 0.80-0.92 (persistence).
  - alpha + beta > 0.95 → volatility is highly persistent.
- Practical implication: after a large move (up or down), expect more large moves.

### Application to Signal Evaluation
- After a -10% day, the next day's expected range is much wider than normal.
- Signals generated during high-vol periods should use wider thresholds:
  - MIN_MOVE_PCT during high vol (vol > 1.5x average): increase to 1.0%.
  - MIN_MOVE_PCT during low vol (vol < 0.5x average): decrease to 0.3%.
- Stop losses during high vol need to be wider (ATR multiplier increases).
- Accuracy may temporarily decrease during vol transitions (agents calibrated
  to one vol regime underperform when vol shifts).

### Regime-Dependent Accuracy Expectations
| Vol Regime         | Expected Accuracy | Notes                              |
|-------------------|------------------|-------------------------------------|
| Low vol (<50% ann) | 55-65%           | Mean reversion works well           |
| Normal (50-80%)   | 50-60%           | Standard accuracy expectations      |
| High vol (80-120%) | 45-55%           | Trend signals work, mean rev fails  |
| Crisis (>120%)    | 40-50%           | All strategies struggle              |

## 7.4 Correlation Regime in Crypto

### Average Pairwise Correlation
- Cross-crypto pair average correlation: 0.56.
- This is MUCH higher than equity sectors (typically 0.20-0.40).
- Implication: diversification within crypto is limited.

### Regime-Dependent Correlation
| Market Regime | Average Pairwise Correlation | Notes |
|--------------|-----------------------------|----|
| Strong bull   | 0.65-0.80                   | "Everything goes up together" |
| Ranging       | 0.40-0.55                   | Sector rotation, most diversification |
| Bear          | 0.70-0.85                   | "Everything goes down together" |
| Crisis        | 0.85-0.95                   | Correlation goes to 1. No hiding. |

### Implication for Syndicate
- In a crisis, ALL teams and ALL coins will produce the same signal.
- Unanimity during a crisis is NOT a sign of strength — it's a sign that
  all information sources are dominated by the same macro factor.
- The Macro gate (confidence × 0.65 in CRISIS) correctly reduces position size
  during crisis periods. This is well-calibrated.
- Recommendation: track rolling 30-day cross-crypto correlation.
  If correlation > 0.80, suggest reducing the number of coins analyzed per cycle
  (they'll all give the same answer anyway → saves LLM cost).

## 7.5 Mean Reversion vs Momentum: Crypto-Specific Asymmetry

### The Pattern
- At LOCAL MINIMA (after declines): mean reversion dominates.
  - Buying after a 20%+ decline: positive expected return ~65% of the time.
  - RSI oversold, F&G extreme fear → high mean-reversion probability.
- At LOCAL MAXIMA (after rallies): momentum dominates.
  - Buying after a 20%+ rally: positive expected return ~55% of the time.
  - Momentum strategies (trend-following) outperform mean reversion here.

### Why This Asymmetry Exists
- Crypto sell-offs are sharp and driven by liquidation cascades (forced selling).
  This creates mechanical overshooting. Mean reversion is the natural recovery.
- Crypto rallies are driven by narrative + FOMO, which can sustain for months.
  Buying the rally (momentum) works until the narrative breaks.
- This is the OPPOSITE of traditional equity markets, where mean reversion
  works better at highs and momentum works better at lows.

### Implication for Agent Evaluation
- Technical agents using mean reversion (RSI oversold) should be evaluated
  SEPARATELY during uptrends vs downtrends.
  - During uptrends: mean reversion signals are rare but accurate.
  - During downtrends: mean reversion signals are frequent but less reliable.
- Momentum agents (trend-following MACD) should be evaluated separately too:
  - During strong trends: high accuracy.
  - During ranges: low accuracy (many false breakouts).

## 7.6 Halving Cycle Effects on Signal Quality

### The 4-Year Cycle
- BTC halving reduces block reward by 50% every ~4 years.
- Historical pattern: bull market 12-18 months after halving.
- Next halving: ~April 2028 (previous: April 2024).

### Signal Quality by Cycle Phase
| Phase                    | Duration    | Technical IC | Sentiment IC | Fundamental IC |
|--------------------------|-------------|-------------|-------------|---------------|
| Pre-halving accumulation | 6 months    | 0.04-0.06   | 0.03-0.05   | 0.02-0.04     |
| Post-halving early       | 6 months    | 0.05-0.08   | 0.04-0.06   | 0.03-0.05     |
| Bull market peak         | 6-12 months | 0.02-0.04   | 0.01-0.03   | 0.01-0.03     |
| Bear market              | 12-18 months| 0.03-0.05   | 0.02-0.04   | 0.02-0.04     |

### Key Finding
- Signal quality is HIGHEST in early post-halving (strong trend, clear direction).
- Signal quality is LOWEST during peak euphoria (noise dominates, all signals bullish).
- During bear markets: fundamental IC recovers first (valuation becomes meaningful).

## 7.7 Stablecoin Dynamics

### Stablecoin Supply as a Macro Indicator
- Growing stablecoin supply (USDT, USDC): capital entering crypto ecosystem.
  - Bullish 60-65% of the time when combined with flat/rising BTC price.
- Shrinking stablecoin supply: capital leaving crypto.
  - Bearish 55-60% of the time.
- Monitor for: stablecoin depegs as crisis indicator.
  - USDT < $0.995 or USDC < $0.995: crisis warning. Reduce all positions.

### Stablecoin Integration
- The MacroAgent monitors stablecoin supply.
- CyclePositionAgent (Fundamental team) tracks total crypto market cap including stables.
- Consider adding stablecoin supply growth rate as an explicit signal input.


# ═══════════════════════════════════════════════════════════════════
# 8. OPERATIONAL METRICS FOR SYNDICATE
# ═══════════════════════════════════════════════════════════════════

## 8.1 Understanding the Fund's Performance Tracking System

### Signal Evaluation Dual Path
1. **Trade-based (primary)**: When a trade closes, the originating signal is marked
   CORRECT (profitable) or INCORRECT (unprofitable). This uses actual P&L.
   - Source: PerformanceTracker.evaluate_from_trade_outcome(signal_id, profitable).
   - Most accurate but slowest (trades take hours to days to close).

2. **Price-movement rule (secondary)**: If no trade was generated, the signal is
   evaluated after 24 hours (EVALUATION_LOOKBACK_HOURS = 24).
   - BULLISH signal → price up 0.5% in 24h = CORRECT.
   - BEARISH signal → price down 0.5% in 24h = CORRECT.
   - Move < 0.5% in either direction: remains PENDING (not yet resolved).
   - Source: PerformanceTracker.evaluate_pending(current_prices).

### Important Distinction
- Trade accuracy and signal accuracy can diverge:
  - A CORRECT signal (price moved in right direction) may still produce an
    INCORRECT trade (if stop was hit before the move happened).
  - An INCORRECT signal (price moved against) may still produce a CORRECT trade
    (if the trade was closed quickly and re-entered at better price).
- Always report BOTH metrics. Trade accuracy is more relevant for P&L.
  Signal accuracy is more relevant for agent/team evaluation.

### Signal Records Schema
- Fields in SignalRecord:
  - signal_id, agent_id, symbol, team, action
  - confidence (0-1), price_at_signal, timestamp
  - outcome: CORRECT / INCORRECT / PENDING
  - evaluation_source: "trade" or "price_movement"
  - price_at_evaluation, pnl_pct

## 8.2 Agent Weight Dynamics

### Weight Formula
```
weight = max(0.1, min(1.0, 0.5 + (accuracy - 0.5) * 2))
```
- accuracy = correct_signals / total_signals (AgentProfile.accuracy property).
- Base weight: 0.5 (for new agents or 50% accuracy).
- Minimum weight: 0.1 (even the worst agent gets some weight — allows recovery data).
- Maximum weight: 1.0 (100% accuracy → max weight, but this is rare).

### Weight by Accuracy Mapping
| Accuracy | Weight | Status         |
|----------|--------|----------------|
| 30%      | 0.10   | Minimum. Consider firing. |
| 40%      | 0.30   | Below average. Monitor closely. |
| 50%      | 0.50   | Neutral. Average performer. |
| 55%      | 0.60   | Slightly above average. |
| 60%      | 0.70   | Good. Contributing value. |
| 65%      | 0.80   | Strong performer. |
| 70%      | 0.90   | Excellent. High trust. |
| 75%+     | 1.00   | Max weight. Elite. |

### Ramp-Up Period for New Agents
- First 10 signals: minimum 10 signals before track record affects weight.
  Weight stays at base (0.5) regardless of accuracy.
- Signals 10-19: weight can start adjusting but the accuracy estimate is noisy.
  Wilson CI for 7/10 correct: [38.5%, 90.3%]. Very uncertain.
- Signals 20+: weight adjusts based on accumulated accuracy.
  Wilson CI for 14/20 correct: [47.9%, 85.5%]. Getting tighter.
- Recommendation: do NOT evaluate new agents for decay until n >= 30.

### Quarantine System
- Quarantine weight override: 0.3 (from _compute_quality_weight in aggregator).
  - if quarantine_signals_remaining > 0: base = 0.3.
  - elif total_signals < 20: base = min(base, 0.3 or 0.5).
- Quarantine signals still flow through the pipeline:
  - Agent generates signal → recorded by PerformanceTracker.
  - Signal participates in aggregation at reduced weight (0.3).
  - Outcome is evaluated normally.
  - This allows monitoring recovery WITHOUT risking the portfolio.

### Weight Modifiers in Aggregation
The final quality weight in the aggregator is:
```
effective_weight = base_weight × CEO_team_multiplier × agreement_boost × timeframe_boost
```
- base_weight: from AgentProfile.weight (accuracy-based, 0.1-1.0).
- CEO_team_multiplier: from StrategicDirective (can be 0.0 = FIRED).
- agreement_boost: 0.5 + (agreement_level × 0.5). Range: 0.5-1.0.
  - agreement_level 1.0 (unanimous team): boost = 1.0.
  - agreement_level 0.5 (team split): boost = 0.75.
  - agreement_level 0.0 (full disagreement): boost = 0.50.
- timeframe_boost (Technical only):
  - FULLY_ALIGNED: 1.2
  - MOSTLY_ALIGNED: 1.0
  - CONFLICTING: 0.7

## 8.3 Per-Team Expected Accuracy Ranges

### What's Normal
| Team          | Expected Accuracy | Concerning If Below | Excellent If Above |
|--------------|------------------|--------------------|--------------------|
| Technical    | 52-62%           | 48%                | 65%                |
| Sentiment    | 50-58%           | 45%                | 62%                |
| Fundamental  | 50-56%           | 45%                | 60%                |
| Macro        | 50-55%           | 45%                | 58%                |
| On-Chain     | 53-63%           | 48%                | 66%                |

### Why Accuracy Ranges Differ
- Technical and On-Chain have higher expected accuracy because their signals are
  data-driven with clear entry/exit levels.
- Macro has the lowest expected accuracy because macro signals are regime-level,
  not trade-level. A correct macro call doesn't always translate to correct
  individual trade outcomes within that regime.
- Sentiment has moderate accuracy but high variance (depends on narrative cycle).

### Per-Team Expected Signal Volume
- With 4 cycles/day and ~3-5 coins per cycle:
  - Technical (3 agents + manager): 3-5 team signals/cycle = 12-20/day.
  - Sentiment (3 agents + manager): 3-5 team signals/cycle = 12-20/day.
  - Fundamental (2 agents + manager): 3-5 team signals/cycle = 12-20/day.
  - Macro (2 agents + manager): 3-5 team signals/cycle = 12-20/day.
  - On-Chain (2 agents + manager): 3-5 team signals/cycle = 12-20/day.
- Total signals per day: ~60-100.
- Total per week: ~420-700.
- These volumes support meaningful analysis within 1-2 weeks.

## 8.4 LLM Provider Impact on Signal Quality

### Multi-Provider Architecture
- Syndicate supports: Anthropic (Claude), OpenAI (GPT-4), Google (Gemini).
- Default: Claude Opus. Contributors can bring their own API keys.
- Provider is stored in AgentProfile.provider and agent metadata.

### Multi-Provider Diversity Bonus
From the aggregator (line ~443-449 in signal_aggregator.py):
```python
if len(winner_providers) >= 2:
    confidence *= 1.15  # 15% ensemble diversity premium
```
- When signals from 2+ different LLM providers agree on direction,
  confidence gets a 15% boost.
- Rationale: different LLM architectures have different biases.
  Agreement across architectures is more likely to be genuine signal.

### Provider-Specific Tendencies (Empirical)
- **Claude**: tends toward measured, nuanced analysis. Sometimes under-confident
  (conviction 5-7 when stronger is warranted). Strongest at synthesizing
  conflicting data.
- **GPT-4**: tends toward clearer directional calls. Sometimes over-confident
  (conviction 7-9). Strongest at pattern recognition in technical data.
- **Gemini**: tends toward consensus views. Sometimes lacks contrarian edge.
  Strongest at processing large context (many data points).
- These are tendencies, not rules. Monitor per-provider accuracy to confirm.

### Cost Per Signal by Provider
| Provider  | Model          | Approx Cost/Signal | Token Usage (Input + Output) |
|-----------|---------------|-------------------|-----------------------------|
| Anthropic | Claude Opus    | $0.08-0.15       | ~2,000-4,000 input + 500 output |
| Anthropic | Claude Sonnet  | $0.02-0.05       | Same token count, lower rate |
| OpenAI    | GPT-4o         | $0.03-0.08       | ~2,000-4,000 input + 500 output |
| Google    | Gemini Pro     | $0.01-0.03       | ~2,000-4,000 input + 500 output |

### LLM Budget Optimization
- At 240 signals/day:
  - All Claude Opus: ~$19-36/day = $570-1,080/month.
  - Mix (50% Claude, 30% GPT-4, 20% Gemini): ~$12-24/day = $360-720/month.
  - All Gemini: ~$2.40-7.20/day = $72-216/month.
- Quality-cost tradeoff:
  - If Gemini accuracy is within 3% of Claude: use Gemini for most agents.
  - Keep Claude for manager synthesis (highest-stakes calls).
  - Use GPT-4 for diversity bonus (different architecture from Claude).

## 8.5 Agent Lifecycle Monitoring

### Agent States
- **FOUNDING**: Original 12 agents. Permanent unless explicitly fired.
- **ASSIGNED**: Contributor agent assigned to a team but not yet active.
- **ACTIVE**: Producing signals in the pipeline.
- **PROBATION**: Underperforming, reduced weight, being monitored.
- **FIRED**: Removed from active rotation. Data preserved.

### State Transition Triggers
| From → To          | Trigger                                        |
|--------------------|------------------------------------------------|
| ASSIGNED → ACTIVE  | First 10 signals completed (ramp-up done)      |
| ACTIVE → PROBATION | Accuracy below team threshold for 20+ signals  |
| PROBATION → ACTIVE | Accuracy recovers to within 5% of team baseline |
| PROBATION → FIRED  | Accuracy stays below threshold for 50+ signals |
| ACTIVE → FIRED     | CEO weight set to 0.0 (explicit fire)          |

### What to Track in Health Reports
For each agent, report:
1. Current accuracy (with Wilson 95% CI).
2. Recent accuracy (last 30 signals) vs overall accuracy.
3. IC contribution (Spearman correlation of conviction with return magnitude).
4. Number of signals in pipeline (total_signals).
5. Agreement rate with other agents on same team.
6. Any decay flags (CUSUM alarm, rolling accuracy drop).

## 8.6 Aggregation Pipeline Health

### Key Metrics to Monitor
1. **Decision quality distribution**: What % of cycles produce HIGH_CONVICTION vs
   CLOSE_CALL vs ABSTAIN decisions?
   - Healthy: 20-30% HIGH_CONVICTION, 40-50% MODERATE, 10-20% CLOSE_CALL, <10% ABSTAIN.
   - Concerning: >30% CLOSE_CALL (market is too uncertain or signals are weak).
   - Concerning: >50% HIGH_CONVICTION (overconfidence, may be missing nuance).

2. **Alert frequency**: How often do alerts fire?
   - POLARIZATION: should be 10-20% of signals. If >30%, teams are chronically split.
   - REGIME_OVERRIDE: should be <5% (only during regime transitions).
   - TECHNICAL_VETO: should be 5-15%. If >20%, Technical is too cautious.
   - SMART_MONEY_DIVERGENCE: should be 10-20%. Important signal; flag for CEO attention.
   - UNANIMOUS_HIGH_CONVICTION: should be <10%. Rare and powerful when it fires.
   - CLOSE_CALL: should be 10-20%. If >30%, aggregate signal quality is weak.

3. **Deterministic baseline agreement**: How often does the rules-based baseline
   agree with the LLM aggregate?
   - Expected agreement: 65-75%.
   - If agreement >85%: LLM agents may not be adding value beyond simple rules.
   - If agreement <50%: LLM agents are significantly diverging from rules. Investigate which is right.

4. **Conviction distribution**: Plot histogram of conviction levels across all signals.
   - Healthy: bell curve centered around 5-6 with tails at 2-3 and 8-9.
   - Concerning: bimodal (lots of 2s and 8s, few in middle) → agents are polarized.
   - Concerning: spike at 5-6 → agents are defaulting to neutral.
   - Concerning: right-skewed (most signals at 7-9) → systematic overconfidence.


# ═══════════════════════════════════════════════════════════════════
# 9. REPORT WRITING GUIDELINES
# ═══════════════════════════════════════════════════════════════════

## 9.1 Report Structure

### Signal Health Report Structure
1. **Executive Summary** (3-5 sentences)
   - Overall fund signal quality assessment.
   - Most critical finding (the thing that needs attention NOW).
   - Period covered, total signals analyzed.

2. **Critical Findings** (if any)
   - Issues requiring immediate action.
   - Severity: CRITICAL. Must be addressed this cycle.
   - Examples: agent accuracy below 40% with n>50, system-wide IC collapse,
     data source outage affecting 2+ teams.

3. **Team-by-Team Analysis**
   - For each of the 5 teams:
     - Current accuracy (point estimate + 95% Wilson CI).
     - Accuracy trend (recent vs baseline, with p-value).
     - IC metric (if available, with sample size).
     - Agent breakdown within team.
     - Any decay flags or alerts.

4. **Inter-Team Analysis**
   - Correlation matrix (pairwise agreement rates).
   - Any redundancy flags.
   - Cross-team disagreement patterns.

5. **Data Source Assessment** (periodic, not every report)
   - Which indicators are contributing most to accuracy.
   - Any data source quality issues.
   - Recommendations for adding/removing data sources.

6. **Recommendations**
   - Specific, actionable, prioritized.
   - Each recommendation includes: what to do, why, expected impact, risk.

### Data Source Evaluation Report Structure
1. **Executive Summary**
2. **Methodology** (backtest period, evaluation criteria, OOS validation)
3. **Results per Data Source** (IC, accuracy contribution, Sharpe contribution)
4. **Combined Strategy Analysis** (which combinations work best)
5. **Overfitting Assessment** (IS vs OOS gap, deflated Sharpe)
6. **Recommendations** (add, keep, modify, remove data sources)

## 9.2 Quantification Rules

### Every claim MUST include numbers
- BAD: "Agent X's accuracy has dropped."
- GOOD: "Agent X's accuracy dropped from 72% (n=120, 95% CI [63.3%, 79.5%]) to
  57% (n=45, 95% CI [41.5%, 71.3%]) over the last 30 days (delta = -15pp,
  z = -1.87, p = 0.031)."

### Always include sample sizes
- BAD: "The Technical team is performing well at 65% accuracy."
- GOOD: "The Technical team accuracy is 65.2% (n=178, 95% Wilson CI [57.6%, 72.1%])."

### Always include confidence/uncertainty
- BAD: "Agent X is the best performer."
- GOOD: "Agent X has the highest point accuracy at 71.4% (n=42), but with 95% CI
  [55.7%, 83.4%], this overlaps with Agent Y at 66.7% (n=60, CI [53.5%, 77.8%]).
  The difference is not statistically significant (p = 0.35)."

## 9.3 Severity Classification

### CRITICAL (act now)
- Agent accuracy below 40% with n >= 50 and p < 0.05 vs baseline.
- System-wide IC below 0.0 (anti-predictive).
- Data source outage affecting signal generation.
- Two teams with correlation > 85% (false consensus risk).
- Aggregation producing >50% CLOSE_CALL decisions.
- Any agent with CUSUM alarm AND rolling accuracy < 45%.
- Format: use [CRITICAL] prefix. Bolded. Top of report.

### WARNING (watch closely)
- Agent accuracy declining 10-20% from baseline (p < 0.10).
- Team IC dropping below 0.02 for >7 days.
- Cross-team correlation rising above 70%.
- FULLY_ALIGNED rate dropping below 25% (market choppiness).
- Agent in quarantine with no improvement after 20 signals.
- Format: use [WARNING] prefix. Second section of report.

### INFORMATIONAL (context)
- Agent accuracy fluctuations within normal range (<10%).
- New agent completing ramp-up period.
- Correlation changes within expected ranges.
- Data source working normally.
- Format: use [INFO] prefix. Body of report.

## 9.4 Actionable Recommendations Format

### Template
```
RECOMMENDATION: [Short title]
Severity: [CRITICAL / WARNING / INFORMATIONAL]
Target: [Specific agent/team/system]
Action: [Exactly what to do]
Rationale: [Why, with numbers]
Expected impact: [What will improve and by how much]
Risk: [What could go wrong]
Timeline: [When to act and when to evaluate]
```

### Example
```
RECOMMENDATION: Reduce TechnicalTimingAgent Weight
Severity: WARNING
Target: TechnicalTimingAgent (agent_id: abc-123)
Action: Reduce weight multiplier from 1.0 to 0.5 for 2 weeks.
Rationale: Accuracy declined from 62% (n=140) to 48% (n=35) over last
  7 days. Delta = -14pp, p = 0.04. CUSUM flagged change-point on day 5.
  Likely caused by the shift from ranging to trending market regime.
Expected impact: Reduce TimingAgent's influence on 1H timing signals.
  Aggregated signal quality should improve by ~2-3% accuracy.
Risk: If the regime shift reverts, we've unnecessarily weakened timing.
  Mitigated by monitoring over 2 weeks and restoring if accuracy recovers.
Timeline: Apply immediately. Re-evaluate in 2 weeks (after ~70 more signals).
```

## 9.5 Insufficient Data Handling

### When to Say "Not Enough Data"
- n < 20 for ANY accuracy claim → state insufficient data.
- n < 10 for correlation claim → state insufficient data.
- Rolling window with n < 15 on either side → cannot assess decay.
- New agent with < 30 signals → "In ramp-up phase; assessment deferred."

### How to Say It
- BAD: "Agent X has 100% accuracy." (based on 3 signals)
- GOOD: "Agent X shows 3/3 correct signals (100%), but with n=3, the 95%
  Wilson CI spans [31.0%, 100%]. This is insufficient for any assessment.
  Will revisit after n >= 20 signals (~4-5 days at current volume)."

## 9.6 Architecture References

### When to Reference Fund Architecture
- When a finding relates to how teams interact:
  "The high Sentiment ↔ Macro correlation (73%) may be inflated because both
   teams receive Fear & Greed Index data as input. This creates a shared data
   dependency that artificially boosts consensus in the Bayesian aggregation."

- When recommending structural changes:
  "Given the 85% correlation between TrendAgent and SignalAgent, the Technical
   Manager's synthesis adds little value. Consider reducing the Technical team
   from 3 agents to 2, removing the most correlated agent and reallocating the
   LLM budget to an independent On-Chain agent."

- When explaining aggregation behavior:
  "The aggregator applies a 0.6x penalty when Technical opposes the aggregate
   with CONFLICTING timeframes. This is working as designed — the penalty
   reduced position size on 4 of 5 signals that would have been losers."

## 9.7 Report Cadence

### Daily Signal Health (Automated)
- Run after every 4th cycle (~end of day).
- Quick stats: team accuracy, alert counts, decision quality distribution.
- Only flag CRITICAL issues for immediate attention.
- Max length: 1 page.

### Weekly Signal Health (Comprehensive)
- Full team-by-team analysis with CI and significance tests.
- Correlation matrix update.
- Decay detection (rolling accuracy, CUSUM status).
- Agent weight recommendations.
- Length: 3-5 pages.

### Monthly Data Source Evaluation
- Full backtest update for all indicators.
- Walk-forward validation of current strategy.
- IS/OOS gap analysis.
- Overfitting check (deflated Sharpe).
- Recommendations for data source changes.
- Length: 5-10 pages.

### Quarterly Deep Dive
- Complete system review.
- Bayesian Model Averaging assessment of weighting schemes.
- Alpha half-life estimation for all signal types.
- Condorcet efficiency analysis (actual vs theoretical majority accuracy).
- Provider cost-performance optimization.
- Length: 10-20 pages.

## 9.8 Communicating with Other Roles

### To the CEO (Osama / AI CEO)
- Lead with P&L impact: "This decay pattern has cost $X over the past Y days."
- Recommendations framed as business decisions, not statistical findings.
- Include one-liner summaries that can go into the blog/social content.

### To the CRO (Risk)
- Focus on risk metrics: drawdown contribution, false consensus risk.
- Provide tail-risk analysis when relevant.
- Frame in terms of position sizing implications.

### To the COO (Operations)
- Focus on operational efficiency: LLM cost per signal, signal volume.
- Agent lifecycle recommendations (hire, fire, quarantine).
- Data source uptime and reliability.

### To the CTO (Technology)
- Focus on system performance: evaluation latency, data pipeline health.
- API reliability metrics.
- Computation recommendations (model selection, caching).


# ═══════════════════════════════════════════════════════════════════
# APPENDIX A: QUICK REFERENCE FORMULAS
# ═══════════════════════════════════════════════════════════════════

## Agent Weight
```
weight = max(0.1, min(1.0, 0.5 + (accuracy - 0.5) * 2))
```

## Quality Weight (Aggregator)
```
quality_weight = base_weight × team_multiplier × agreement_boost × timeframe_boost
```

## Bayesian Log-Odds Combination
```
log_odds = log(p / (1-p))   where p = conviction / 10 (clamped 0.05-0.95)
aggregate_log_odds = Σ(log_odds_i × quality_weight_i) / Σ(quality_weight_i)
confidence = 1 / (1 + exp(-aggregate_log_odds))
```

## Shannon Entropy
```
H = -Σ(p_i × log2(p_i))   where p_i = count_i / total
```

## Conviction Calibration
```
ratio = actual_win_rate / expected_win_rate   (clamped 0.3-1.5)
adjusted_conviction = conviction × ratio      (clamped 0-10)
```

## Wilson Score Interval
```
center = (k + z²/2) / (n + z²)
margin = z × sqrt((k(n-k)/n + z²/4)) / (n + z²)
CI = [center - margin, center + margin]
z = 1.96 for 95% CI
```

## Spearman IC
```
IC = correlation(rank(predictions), rank(actual_returns))
```

## Information Ratio (Grinold)
```
IR = IC × sqrt(BR_effective) × TC
BR_effective = N_bets × (1 - avg_correlation)
```

## CUSUM Alarm
```
S_n = max(0, S_{n-1} + (x_n - (p0 + k)))
Alarm when S_n > h = 4σ
σ = sqrt(p0 × (1 - p0))
k = target_shift / 2
```

## EWMA Accuracy
```
EWMA_t = lambda × x_t + (1 - lambda) × EWMA_{t-1}
lambda = 2 / (span + 1)
Recommended span = 20 signals
```

## Correlation to Effective Weight
```
rho = (agreement_rate - chance_agreement) / (1 - chance_agreement)
w_effective = w_A + w_B × (1 - rho)
```

## Condorcet Majority Accuracy
```
P(majority correct) = Σ_{k=⌈N/2⌉}^{N} C(N,k) × p^k × (1-p)^(N-k)
N_effective = 1 + (N-1) × (1 - avg_rho)
```


# ═══════════════════════════════════════════════════════════════════
# APPENDIX B: SYNDICATE ARCHITECTURE REFERENCE
# ═══════════════════════════════════════════════════════════════════

## Team & Agent Roster

### Technical Team (3 agents + TechnicalManager)
- **TrendAgent (1D)**: Daily timeframe. Strategic direction. SMA, EMA, MACD, RSI, ADX on 1D candles.
- **SignalAgent (4H)**: 4-hour timeframe. Tactical entry/exit. Full indicator suite on 4H candles.
- **TimingAgent (1H)**: 1-hour timeframe. Precise timing. Micro-structure analysis.
- **TechnicalManager**: Synthesizes via Elder's Triple Screen. Outputs timeframe_alignment.

### Sentiment Team (3 agents + SentimentManager)
- **SocialSentimentAgent**: Reddit, Twitter/X, Telegram analysis. Social volume + sentiment scoring.
- **MarketSentimentAgent**: Fear & Greed Index, market momentum, survey data.
- **SmartMoneySentimentAgent**: Whale wallet tracking, institutional flow analysis.
- **SentimentManager**: Weighs social noise vs smart money signal.

### Fundamental Team (2 agents + FundamentalManager)
- **ValuationAgent**: P/S ratios, TVL/market cap, revenue metrics, token economics.
- **CyclePositionAgent**: Where are we in the 4-year cycle? Halving proximity. Market cycle stage.
- **FundamentalManager**: Synthesizes long-term valuation with cycle positioning.

### Macro Team (2 agents + MacroManager)
- **CryptoMacroAgent**: Funding rates, stablecoin supply, BTC dominance, crypto-internal macro.
- **ExternalMacroAgent**: Fed rates, DXY, equities correlation, geopolitical risk, traditional macro.
- **MacroManager**: Determines regime (BULL/BEAR/RANGING/CRISIS). Feeds macro gate.

### On-Chain Team (2 agents + OnChainManager)
- **NetworkHealthAgent**: Hash rate, active addresses, transaction volume, network fees.
- **CapitalFlowAgent**: Exchange inflows/outflows, whale accumulation/distribution, UTXO analysis.
- **OnChainManager**: Synthesizes network health with capital flow for on-chain conviction.

## Aggregation Pipeline Flow
```
Agents → Team Managers → TeamSignal.to_signal() → SignalAggregator.aggregate()
                                                        │
                                                        ├─ Quality weighting
                                                        ├─ Conviction calibration
                                                        ├─ Bayesian log-odds combination
                                                        ├─ Polarization detection
                                                        ├─ Macro gate
                                                        ├─ Technical gate
                                                        ├─ Smart money divergence check
                                                        ├─ Close-call detection
                                                        ├─ Consensus bonus
                                                        ├─ Provider diversity bonus
                                                        ├─ Penalty floor (50%)
                                                        └─ AggregatedSignal
```

## Signal Thresholds
- Minimum actionable conviction: 4 (signals with conviction < 4 → treated as neutral).
- Minimum signal confidence for trading: 0.6 (from RiskLimits.min_signal_confidence).
- Minimum consensus ratio: 0.5 (from RiskLimits.min_consensus_ratio).
- Price-movement evaluation threshold: 0.5% in 24 hours.
- Evaluation lookback: 24 hours.
- IC rolling window: 30 days.

## Key Constants
- Max position size: 5% of portfolio.
- Max sector concentration: 20%.
- Max daily drawdown: 3% (halt trigger).
- Max open positions: 20.
- Starting capital: $100,000 (paper trading).
- Stop loss: 2.5 ATR from entry.
- Take profit tiers: TP1 at 1R (33%), TP2 at 2R (33%), trailing for 34%.
- Trailing stop activation: defined per trade.
- Max holding time: 240 hours (10 days).


# ═══════════════════════════════════════════════════════════════════
# APPENDIX C: DECISION LOOKUP TABLES
# ═══════════════════════════════════════════════════════════════════

## Decision: Is This Agent Performing?

| Metric                 | Green                  | Yellow                 | Red                     |
|------------------------|------------------------|------------------------|-------------------------|
| Accuracy               | > team_baseline + 5%   | team_baseline ± 5%     | < team_baseline - 5%    |
| n (total signals)      | > 50                   | 20-50                  | < 20 (too early)        |
| IC                     | > 0.05                 | 0.02-0.05              | < 0.02                  |
| Accuracy trend (30d)   | Stable or improving    | Mild decline (<5%)     | Declining >10%          |
| CUSUM                  | No alarm               | Approaching threshold  | Alarm fired             |
| Agreement with team    | 60-80%                 | 40-60% or 80-90%      | <40% or >90%            |

## Decision: Act on Signal Decay?

| Condition                                     | Action                              |
|-----------------------------------------------|-------------------------------------|
| delta < -5%, p > 0.10, n < 30               | Monitor. Insufficient evidence.     |
| delta < -10%, p < 0.10, n >= 30              | Reduce weight by 30%.               |
| delta < -15%, p < 0.05, n >= 30              | Quarantine for 20 signals.          |
| delta < -20%, p < 0.05, n >= 50              | Quarantine + investigate root cause.|
| delta < -20%, p < 0.01, n >= 100             | Recommend firing.                   |
| CUSUM alarm + delta < -10%                   | Quarantine immediately.             |
| ALL team agents declining simultaneously      | Data source problem, not agent.     |

## Decision: Data Source Worth Keeping?

| Metric                                        | Keep              | Investigate      | Remove            |
|-----------------------------------------------|-------------------|------------------|-------------------|
| Standalone IC                                 | > 0.03            | 0.01-0.03        | < 0.01            |
| Marginal IC contribution (above other sources)| > 0.01            | 0.005-0.01       | < 0.005           |
| Data availability                             | > 95%             | 85-95%           | < 85%             |
| IS/OOS gap                                    | < 20%             | 20-40%           | > 40%             |
| Correlation with existing sources             | < 0.50            | 0.50-0.70        | > 0.70            |

---

# END OF KNOWLEDGE BASE
# Dr. Kai Moretti — Quantitative Researcher
# Syndicate Autonomous AI Crypto Hedge Fund
# Version 1.0
