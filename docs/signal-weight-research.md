# Signal Weight Learning: Research Compendium

Comprehensive research on optimal methods for learning signal weights in multi-signal trading systems. Covers IC-based weighting, Bayesian combination, online learning, ensemble methods, regime dependence, diversification, and practical considerations for crypto markets with small sample sizes.

---

## 1. Information Coefficient (IC) Based Weighting

### What Is IC?

The **Information Coefficient** is the rank correlation (Spearman) between predicted and realized returns. It measures how good a signal is at forecasting future returns.

```
IC = corr_rank(predicted_returns, actual_returns)
```

IC ranges from -1 to +1.

### IC Thresholds

| IC Value | Interpretation |
|----------|---------------|
| 0.02 | Barely detectable edge |
| 0.05 | Good — most PMs would consider this valuable |
| 0.10 | Very good — top-tier signal quality |
| 0.15+ | Exceptional — rarely sustained |

An IC of 0.05 means your predictions are slightly better than random. An IC of 0.10 is considered excellent by industry standards.

### ICIR (IC Information Ratio)

Stability matters as much as magnitude:

```
ICIR = mean(IC) / std(IC)
```

An ICIR > 0.5 indicates a reliable signal. This measures whether the IC is consistently positive rather than just positive on average.

### Grinold's Fundamental Law of Active Management

The foundational framework for signal weighting:

**Basic Law (unconstrained):**
```
IR* = IC × sqrt(BR)
```

**Full Law (with constraints):**
```
E(R_A) = TC × IC × sqrt(BR) × sigma_A
```

Where:
- **IR** = Information Ratio (risk-adjusted active return)
- **IC** = Information Coefficient (signal quality)
- **BR** = Breadth (number of independent bets per year)
- **TC** = Transfer Coefficient (how well signals translate to positions; 1.0 = unconstrained)
- **sigma_A** = Active risk (tracking error)

### Alpha From IC (Grinold's Rule)

Converting a signal score into an alpha forecast:

```
alpha_i = IC × volatility_i × z_score_i
```

Where `z_score_i` is the cross-sectionally standardized signal score for asset i.

### IC-Based Signal Combination

For M signals with individual ICs, the **IC-squared weighted combination** is:

```
w_j = IC_j^2 / sum(IC_k^2)       # Weight proportional to IC-squared
```

For uncorrelated signals, the combined IC:

```
IC_combined = sqrt(sum(w_j^2 × IC_j^2))
```

With equal weights (w_j = 1/M):

```
IC_combined = (1/sqrt(M)) × sqrt(sum(IC_j^2))
```

### Practical Implication

Breadth scales as sqrt(BR), meaning:
- Going from 1 to 100 independent bets: **10x improvement**
- Going from 100 to 10,000 bets: **10x more improvement**
- Doubling IC from 0.05 to 0.10: only **2x improvement**

It is often easier to improve performance by adding more independent signals (breadth) than by improving any single signal's IC.

---

## 2. Bayesian Signal Combination

### Black-Litterman Model for Signal Weighting

The BL model provides a principled Bayesian framework for combining multiple signal "views" with a prior.

**Posterior expected returns:**
```
E(R) = [(tau * Sigma)^(-1) + P^T * Omega^(-1) * P]^(-1)
        × [(tau * Sigma)^(-1) * Pi + P^T * Omega^(-1) * Q]
```

**Posterior covariance:**
```
Sigma_hat = Sigma + [(tau * Sigma)^(-1) + P^T * Omega^(-1) * P]^(-1)
```

Where:
- **Pi** (Nx1): Prior expected returns (e.g., market equilibrium returns)
- **Q** (Kx1): Signal views (each signal's prediction)
- **P** (KxN): Picking matrix mapping signals to assets
- **Omega** (KxK): Signal uncertainty matrix (diagonal = independent signals)
- **Sigma** (NxN): Asset covariance matrix
- **tau**: Scalar (typically 0.025-0.05), controls prior tightness

### Computing Prior Returns from Market Caps

```
delta = (R_market - R_f) / sigma_market^2    # Risk aversion coefficient
Pi = delta × Sigma × w_mkt                    # Equilibrium returns
```

### Default Omega (view uncertainty)

When no confidence is specified:
```
Omega = tau × P × Sigma × P^T
```

This makes uncertainty proportional to asset variance (volatile assets are harder to forecast).

### Idzorek Method for Confidence

Convert percentage confidence (0-100%) into the Omega matrix:
- 100% confidence: view dominates completely
- 0% confidence: view is ignored, prior dominates
- 50% confidence: equal blend of prior and view

### Bayesian Model Averaging (BMA)

A more general framework for combining multiple forecasting models:

```
p(theta | X) = sum_k p(theta | M_k, X) × p(M_k | X)
```

Where:
- `p(theta | M_k, X)` = posterior under model k
- `p(M_k | X)` = posterior model probability (the "weight")

**Key property:** BMA point estimators minimize mean squared error weighted by the prior (Raftery & Zheng, 2003).

**Posterior model probability:**
```
p(M_k | X) ∝ p(X | M_k) × p(M_k)
```

Where `p(X | M_k)` is the marginal likelihood (evidence) for model k.

### When to Use BMA vs. BL

- **BL**: When you have multiple signals about the same set of assets and want to combine them with a market-equilibrium prior
- **BMA**: When you have multiple competing models and want to weight by posterior probability of each being correct

---

## 3. Online Learning for Signal Weights

### EXP3 (Exponential-weight for Exploration and Exploitation)

Designed for adversarial bandits where rewards can be arbitrary (non-stochastic).

**Algorithm:**
```
Initialize: w_i(1) = 1 for all arms i = 1..K

For each round t:
  1. Compute probabilities:
     p_i(t) = (1 - gamma) × w_i(t) / sum(w_j(t)) + gamma/K

  2. Draw action i_t from distribution p(t)

  3. Observe reward x_{i_t}(t)

  4. Compute estimated reward (importance-weighted):
     x_hat_{i_t}(t) = x_{i_t}(t) / p_{i_t}(t)

  5. Update weight:
     w_{i_t}(t+1) = w_{i_t}(t) × exp(gamma × x_hat_{i_t}(t) / K)
```

**Regret bound:**
```
G_max(T) - E[G_EXP3(T)] <= (e-1) × gamma × G_max(T) + (K × log(K)) / gamma
```

**Optimal gamma:**
```
gamma = min(1, sqrt(K × log(K) / ((e-1) × g)))
```
where g bounds the best action's cumulative reward.

**Weak regret bound:** approximately `2.63 × sqrt(g × K × log(K))`

**Key properties:**
- Never stops exploring (gamma > 0 ensures continuous exploration)
- Handles truly adversarial payoffs
- Adapts if the environment changes over time
- Regret grows as O(sqrt(T × K × log(K)))

### Multiplicative Weights Update (MWU / Hedge)

A meta-algorithm for the "expert problem":

**Algorithm:**
```
Initialize: w_i(1) = 1 for all experts i = 1..N

For each round t:
  1. Select expert proportional to weights:
     p_i(t) = w_i(t) / sum(w_j(t))

  2. Observe losses/rewards for all experts

  3. Update weights multiplicatively:
     w_i(t+1) = w_i(t) × (1 - epsilon × loss_i(t))
     OR (Hedge variant):
     w_i(t+1) = w_i(t) × exp(-epsilon × loss_i(t))
```

**Regret bound (after T rounds):**
```
Total_Loss_MWU <= (1 + epsilon) × L_best + (ln N) / epsilon
```

Where L_best is the loss of the best expert in hindsight.

**Optimal learning rate:**
```
epsilon = sqrt(ln(N) / T)
```

**Resulting regret:** `O(sqrt(T × ln(N)))`

**Key guarantee:** The cumulative reward of MWU is, up to constant multiplicative factors, at least the cumulative reward of the best expert minus O(sqrt(T × ln(N))).

### Non-Stationary Variants

For crypto markets (non-stationary), standard algorithms need modification:

#### Discounted UCB (D-UCB)
- Applies discount factor gamma (~0.95) to past observations
- Recent observations weighted more heavily
- Regret: O(sqrt(T × B_T × log(T))) where B_T = number of breakpoints

#### Sliding Window UCB (SW-UCB)
- Only considers last tau observations
- Window size formula: `tau = 2 × sqrt(T × log(T) / (1 + Upsilon_T))`
  where Upsilon_T = number of change points
- Regret: O(sqrt(T × B_T × log(T)))

#### Discounted Thompson Sampling
- Discount factor gamma (~0.95) on posterior parameters
- More robust than UCB when feedback is delayed
- Thompson sampling alleviates delayed feedback influence through randomization

#### EXP3.S (for switching environments)
- Regret: O~(sqrt(T × B_T)) where B_T = breakpoints
- Theoretical bound comparable to D-UCB and SW-UCB

#### GLR-UCB (Generalized Likelihood Ratio)
- Actively detects change points without knowing number of breakpoints
- Best empirical performance in recent comparisons but higher computational cost

### Practical Comparison for Non-Stationary Environments

| Algorithm | Regret Bound | Breakpoint Detection | Computational Cost | Best For |
|-----------|-------------|---------------------|-------------------|----------|
| EXP3.S | O~(sqrt(T×B_T)) | Slow | Low | Adversarial |
| D-UCB | O(sqrt(T×B_T×log T)) | Fast | Low | Abrupt changes |
| SW-UCB | O(sqrt(T×B_T×log T)) | Fast | Low | Abrupt changes |
| D-Thompson | Similar to D-UCB | Moderate | Low | Delayed feedback |
| GLR-UCB | Best empirical | Very fast | High | Unknown breakpoints |

**Key finding:** D-UCB and SW-UCB "waste significantly less time than EXP3.S to detect breakpoints and quickly concentrate pulls on the optimal arm." They are "significantly more reactive to changes in practice" despite similar theoretical bounds.

---

## 4. Ensemble Learning for Trading

### Gradient Boosted Signal Combination

GBM trains base learners on the negative gradient of the ensemble's loss:

```
F_m(x) = F_{m-1}(x) + eta × h_m(x)
```

Where h_m is fitted to the pseudo-residuals of the current ensemble.

**Key advantage:** Each new signal directly reduces the ensemble's error.

**Crypto results:** Ensemble methods (XGBoost, Gradient Boosting) outperform deep learning models across multiple cryptocurrencies. Stacked ensembles improve prediction accuracy by ~5.2% over standalone models.

### Multi-Factor Quant Trading Framework

Standard hedge fund signal combination pipeline:

1. **Signal generation**: Compute raw signals (momentum, value, sentiment, etc.)
2. **Signal scoring**: Cross-sectionally rank signals into z-scores
3. **Neutralization**: Industry/size neutralize to isolate pure alpha
4. **IC-based weighting**: Weight signals by IC or ICIR
5. **Portfolio construction**: Convert weighted signal to positions via optimization

### Signal Neutralization

Before combining, signals should be neutralized for common factors:

```
alpha_neutral = alpha_raw - beta_sector × sector_factor - beta_size × size_factor
```

This transforms biased signals into pure alpha factors. Cross-sectional construction naturally hedges market risk.

### Stacking Architecture

```
Level 0: Individual signals (momentum, sentiment, on-chain, etc.)
Level 1: Meta-learner combining Level 0 outputs
         (often ridge regression or gradient boosting)
Level 2: Final portfolio weights
```

**Critical:** Use out-of-fold predictions at Level 0 to prevent information leakage.

---

## 5. Signal Decay and Regime Dependence

### Regime Detection Methods

#### Hidden Markov Models (HMM)
- Fit 2-state Gaussian HMM on daily log returns
- Training window: ~3000 days
- Identifies regimes primarily through conditional volatilities
- Problem: "numerous short-lived regimes that are unintuitive" — many flip within days
- Detection latency: ~25 calendar days average

#### Statistical Jump Models (JM)
- Optimization: `min sum(l(x_t, theta_{s_t})) + lambda × sum(1{s_{t-1} != s_t})`
- Lambda (jump penalty) controls regime persistence
- Uses features: EWMA downside deviation (10-day), Sortino ratios (20 and 60-day)
- Much better persistence than HMM

### Regime Persistence Comparison (S&P 500, 1982-2023)

| Model | Parameter | Regime Shifts/Year |
|-------|-----------|-------------------|
| HMM | k=0 | 8.5 |
| HMM | k=20 | 2.0 |
| JM | lambda=50 | 0.8 |
| JM | lambda=150 | 0.4 |

### Performance by Regime Strategy (1990-2023)

**S&P 500:**

| Strategy | Return | Vol | Sharpe | Max DD |
|----------|--------|-----|--------|--------|
| Buy-Hold | 10.2% | 18.2% | 0.48 | -55.2% |
| HMM 0/1 | 8.5% | 11.3% | 0.54 | -28.9% |
| JM 0/1 | 11.2% | 13.1% | 0.68 | -26.6% |

**Nikkei 225:**

| Strategy | Return | Vol | Sharpe | Max DD |
|----------|--------|-----|--------|--------|
| Buy-Hold | 0.8% | 23.4% | 0.12 | -79.1% |
| JM 0/1 | 4.7% | 17.1% | 0.31 | -45.3% |

### Signal Quality by Regime

- **Bull regimes**: Low risk, high returns — trend-following signals work well
- **Bear regimes**: Elevated risk, negative returns — defensive/reversal signals work well
- **Transitions**: Signal reliability significantly decreases during regime changes
- **Alpha decay rates accelerate during unstable periods**
- Factor exposures' statistical significance fluctuates markedly across regimes

### Regime-Dependent Signal Weighting Approach

```
For each regime r in {bull, bear, transition}:
  1. Detect current regime using JM or HMM
  2. Load regime-specific signal weights: w(r) = {w_1(r), ..., w_M(r)}
  3. Compute blended signal: S = sum(w_i(r) × signal_i)
  4. During transitions, blend weights between regimes
```

### Signal Robustness Under Delays

With 10-day trading delay (realistic for crypto):
- JM strategies maintain Sharpe ~0.70 (S&P 500)
- HMM strategies degrade to Sharpe ~0.51
- JM annual turnover: 44% vs HMM: 141%

---

## 6. Equal Weighting vs. Learned Weighting

### The DeMiguel-Garlappi-Uppal (2009) Result

Landmark finding: None of 14 optimization models consistently beat equal weighting (1/N) across 7 datasets.

**Required estimation window for optimization to beat 1/N:**
- **25 assets: ~3,000 months (250 years)**
- **50 assets: ~6,000 months (500 years)**

This devastating result is calibrated to US equity parameters.

### The Forecast Combination Puzzle

Equal-weight forecast combinations often outperform optimally-weighted combinations because:

1. **Estimation error in weights**: Optimal weights must be estimated, introducing variance
2. **Random vs. fixed weights**: Properties derived assuming fixed weights don't hold when weights are random
3. **Bias-variance tradeoff**: Equal weights trade small bias for much larger variance reduction
4. **Covariance estimation difficulty**: Ignoring cross-signal correlations (as Bates-Granger recommended) often helps

### When Optimization DOES Beat Equal Weighting

1. **High asset heterogeneity**: When signals have very different volatilities, risk-based weighting dominates
2. **Strong cross-signal correlations**: When some signals are redundant, optimization can de-weight them
3. **Proper shrinkage**: Bayesian/shrinkage methods reduce estimation error enough for optimization to work
4. **Sufficient sample size**: Empirical rule: need T >> N (observations >> number of signals)
5. **Factor-based screening**: Simply removing weak signals from equal-weighted portfolio improves Sharpe by 19-51%

### Practical Rules

| # Signals | # Observations | Recommendation |
|-----------|---------------|----------------|
| 3-5 | < 50 | Equal weight |
| 3-5 | 50-200 | Shrunk IC-weighted |
| 3-5 | 200+ | Full optimization |
| 10+ | < 200 | Equal weight |
| 10+ | 200-1000 | Risk parity or shrinkage |
| 10+ | 1000+ | Full optimization with regularization |

### Inverse-MSE Weighting (Simple Alternative)

The Bates-Granger (1969) approach — weight by inverse forecast error, ignoring cross-correlations:

```
w_i = (1/MSE_i) / sum(1/MSE_k)
```

This often outperforms the "optimal" formula that accounts for correlations, because the covariance matrix is too hard to estimate accurately.

---

## 7. Anti-Correlation and Signal Diversification

### Portfolio Variance with Correlated Signals

For two signals with correlation rho:
```
Var(portfolio) = w1^2 × sigma1^2 + w2^2 × sigma2^2 + 2 × w1 × w2 × sigma1 × sigma2 × rho
```

When rho < 0, the cross-term **reduces** portfolio variance below individual variances.

General N-signal case:
```
sigma_p^2 = w^T × Sigma × w
```

### Combined Sharpe Ratio for Uncorrelated Signals

**Critical formula:** For N uncorrelated (independent) strategies:

```
SR_combined = sqrt(SR_1^2 + SR_2^2 + ... + SR_N^2)
```

This is the "Sharpe ratio adds in quadrature" rule.

**Example:**
- Signal A: Sharpe 0.5
- Signal B: Sharpe 0.4
- Signal C: Sharpe 0.3
- Combined (uncorrelated): sqrt(0.25 + 0.16 + 0.09) = sqrt(0.50) = **0.71**

If all N signals have equal Sharpe ratio S:
```
SR_combined = S × sqrt(N)
```

### Correlation's Effect on Combined Sharpe

For N signals with average pairwise correlation rho_bar and equal Sharpe S:
```
SR_combined ≈ S × sqrt(N) / sqrt(1 + (N-1) × rho_bar)
```

- rho_bar = 0: Full diversification benefit, SR scales as sqrt(N)
- rho_bar = 1: No benefit, SR = S (all signals are the same)
- rho_bar = -1/(N-1): Maximum diversification, variance can reach zero

### Mean-Variance Optimization for Signal Weights

```
min_w  w^T × Sigma_signals × w
s.t.   w^T × mu_signals = target_return
        sum(w) = 1
```

Where Sigma_signals is the covariance matrix of signal returns and mu_signals is the expected alpha from each signal.

### Key Insight on Anti-Correlated Signals

It is **efficient to use signals with low or even negative Sharpe ratios** as long as their correlation to other signals is sufficiently low. A negative-Sharpe signal that is anti-correlated with your main signals can improve portfolio Sharpe ratio.

### Caveat

Correlations between signals tend to increase during market stress. The objective is to find signals with minimal correlation **over full market cycles**, not just in calm periods.

---

## 8. Crypto Quant Fund Approaches

### Academic Crypto Factor Models

Research identifies persistent market inefficiencies across three primary categories:

1. **Cross-exchange arbitrage**: Price discrepancies across exchanges
2. **Factor-based investing**: Size, momentum, liquidity factors show statistical significance
3. **On-chain metric signaling**: Exchange flows, active addresses, NVT ratio

### The Crypto Three-Factor Model (Liu et al., 2022)

```
R_i - R_f = alpha + beta_MKT × MKT + beta_SIZE × SIZE + beta_MOM × MOM + epsilon
```

A three-factor model (market, size, momentum) captures a large fraction of cross-sectional crypto returns. Adding a value factor further strengthens explanatory power.

### Crypto-Specific Signals

| Signal Type | Examples | Typical IC | Decay |
|------------|---------|-----------|-------|
| Momentum | 7d, 30d returns | 0.03-0.08 | Fast (days) |
| Funding rates | Perp vs spot premium | 0.02-0.05 | Medium (hours-days) |
| On-chain flows | Exchange inflow/outflow | 0.01-0.04 | Slow (days-weeks) |
| Social sentiment | Reddit, Twitter volume | 0.01-0.03 | Very fast (hours) |
| Volume/liquidity | Volume changes, spread | 0.02-0.05 | Medium |

### Multi-Factor Crypto Strategy Construction

Best performing crypto strategies are **blends of multiple individual factor strategies**:

1. Non-price strategies occupied top positions in 2021 when price action was ranging
2. Momentum dominated during strong trending periods
3. Factor scoring used to rank securities, with high scores getting higher weight

### Practical Signal Combination for Crypto

```
1. Compute z-scores for each signal across crypto universe
2. Apply IC-weighted (or equal-weighted) combination
3. Use rolling IC (e.g., 90-day) to adapt weights
4. Apply regime filter: reduce momentum weight in ranging markets,
   reduce mean-reversion weight in trending markets
5. Construct portfolio via risk-parity or minimum-variance optimization
```

### About Specific Firms

- **Wintermute**: Algorithmic liquidity provider using HFT practices from traditional finance. Focus on market-making and arbitrage rather than directional signal combination.
- **Jump Crypto**: Proprietary strategies not publicly disclosed. Known for infrastructure, MEV, and latency-sensitive strategies.
- **Academic crypto trading**: Publicly available research focuses on factor models, momentum, and on-chain metrics with standard quant factor combination methods.

---

## 9. Thompson Sampling vs UCB vs EXP3

### Algorithm Comparison

#### Thompson Sampling (Bernoulli Bandit)
```
Initialize: For each arm k, set alpha_k = 1, beta_k = 1  (uniform prior)

For each round t:
  1. Sample theta_k ~ Beta(alpha_k, beta_k) for each arm k
  2. Play arm k* = argmax_k(theta_k)
  3. Observe reward r_t in {0, 1}
  4. Update: if r_t = 1: alpha_{k*} += 1
             if r_t = 0: beta_{k*} += 1
```

**Regret bounds:**
- Instance-dependent: O(sum_{k: Delta_k > 0} log(T) / Delta_k) — matches UCB
- Instance-independent: O(sqrt(K × T × log(T)))
- Bayesian regret: O(sqrt(K × T)) — optimal up to constants

#### UCB1
```
Play arm k* = argmax_k(mu_hat_k + sqrt(2 × log(t) / n_k))
```

**Regret:** O(sqrt(K × T × log(T)))

#### EXP3
(See Section 3 above)

**Regret:** O(sqrt(K × T × log(K)))

### Head-to-Head Comparison

| Property | Thompson Sampling | UCB1 | EXP3 |
|----------|------------------|------|------|
| Environment | Stochastic | Stochastic | Adversarial |
| Regret (instance-dep) | O(K log T / Delta) | O(K log T / Delta) | N/A |
| Regret (worst-case) | O(sqrt(KT log T)) | O(sqrt(KT log T)) | O(sqrt(KT log K)) |
| Exploration | Randomized (posterior) | Deterministic (UCB) | Randomized (mixture) |
| Delayed feedback | Robust | Sensitive | Moderate |
| Non-stationary | Needs modification | Needs modification | Naturally adaptive |
| Convergence speed | Fast empirically | Moderate | Slow |
| Implementation | Easy (Beta posteriors) | Easy (counters) | Easy (weights) |

### For Non-Stationary Environments (Crypto)

**Discounted Thompson Sampling** is recommended because:
1. Robust to delayed feedback (crypto exchange latency)
2. Randomized exploration naturally handles regime changes
3. Simple to implement: just decay alpha and beta parameters

```
At each step:
  alpha_k *= gamma    # gamma ≈ 0.95-0.99
  beta_k *= gamma
  Then update with new observation
```

**Discounted UCB** is the runner-up:
- Faster breakpoint detection than EXP3.S
- D-UCB and SW-UCB "significantly more reactive to changes in practice"
- But deterministic nature makes it sensitive to delayed feedback

**EXP3** is theoretically safest for truly adversarial environments but:
- Slowest convergence in practice
- "Wastes significantly more time" detecting breakpoints
- Best reserved for scenarios where you suspect adversarial behavior (e.g., MEV)

### Convergence Speed Comparison

In simulation with large reward gap (0.1 vs 0.9):
- Thompson Sampling reaches 95% optimal arm selection within ~40 trials
- With small gap (0.8 vs 0.9): best arm selection ~68%
- Thompson Sampling consistently outperforms UCB1 and Epsilon-Greedy in cumulative regret

---

## 10. The Cold-Start Problem (50-100 Trades)

### The Core Challenge

With only 50-100 observations:
- Sample mean has enormous variance
- Covariance matrix may be singular (N > T)
- IC estimates are noisy (confidence intervals are wide)
- MLE weights will massively overfit

### Solution 1: Bayesian Shrinkage (James-Stein Estimator)

Shrink signal weight estimates toward a common value (e.g., equal weights):

```
mu_JS = b + (1 - alpha) × (mu_sample - b)
```

**Shrinkage coefficient:**
```
alpha = (1/T) × (N_tilde - 2) / ((mu_sample - b)^T × Sigma^(-1) × (mu_sample - b))
```

Where:
- N_tilde = Tr(Sigma) / lambda_max(Sigma) (effective dimension)
- b = target (e.g., grand mean of all signal means)
- Improves on sample mean when N_tilde > 2

**Jorion's portfolio-specific variant:**
```
b = (1^T × Sigma^(-1) × mu_sample) / (1^T × Sigma^(-1) × 1)
alpha = (N + 2) / (N + 2 + T × (mu_sample - b×1)^T × Sigma^(-1) × (mu_sample - b×1))
```

### Solution 2: Ledoit-Wolf Covariance Shrinkage

```
Sigma_LW = (1 - delta) × Sigma_sample + delta × B
```

**Optimal shrinkage intensity:**
```
delta_hat = max(0, min(kappa_hat / T, 1))
kappa_hat = (pi_hat - rho_hat) / gamma_hat
```

**Constant correlation target:**
```
B_ij = r_bar × sqrt(s_ii × s_jj)    for i != j
B_ii = s_ii                            for diagonal
```

Where r_bar = average sample correlation.

**Key finding:** Optimal shrinkage intensity is typically ~80%, meaning "there is four times as much estimation error in the sample covariance matrix as bias in the structured target."

### Solution 3: Hierarchical Bayesian Priors

For the cold start, place informative priors on signal weights:

```
Prior: w_i ~ Normal(1/N, sigma_prior^2)    # Centered on equal weight
Likelihood: returns | w ~ Normal(sum(w_i × signal_i), sigma_noise^2)
Posterior: w_i | data ∝ Likelihood × Prior
```

With few observations, the posterior stays close to equal weights (the prior). As data accumulates, the posterior moves toward the data-driven optimum.

### Solution 4: Online Learning with Warm Start

Start with equal weights and slowly adapt:

```
Initialize: w_i = 1/N for all signals

For each new trade t:
  1. Observe signal predictions and actual outcome
  2. Update with small learning rate:
     w_i(t+1) = w_i(t) × exp(epsilon × reward_i(t))
     Normalize: w_i(t+1) /= sum(w_j(t+1))

  epsilon = sqrt(ln(N) / t)    # Decreasing learning rate
```

With 50-100 trades, use a larger epsilon (more exploration). As trades accumulate, decrease epsilon.

### Solution 5: Covariance De-noising (Random Matrix Theory)

When N/T is close to 1, use Marchenko-Pastur to separate signal from noise:

```
1. Compute sample correlation matrix C
2. Eigendecompose: C = V × Lambda × V^T
3. Compute Marchenko-Pastur bounds:
   lambda_+ = (1 + sqrt(N/T))^2
   lambda_- = (1 - sqrt(N/T))^2
4. Set all eigenvalues below lambda_+ to their average
5. Reconstruct: C_clean = V × Lambda_clean × V^T
```

This preserves signal-associated eigenvalues while shrinking noise.

### Sample Size Rules of Thumb

| N (signals) | Min observations for IC estimation | Min for weight optimization | Min for full covariance |
|-------------|-----------------------------------|-----------------------------|------------------------|
| 3 | 30 | 50 | 100 |
| 5 | 50 | 100 | 250 |
| 10 | 100 | 300 | 1000 |
| 25 | 250 | 1000 | 3000+ |

General rule: **T >> N** (observations should be an order of magnitude greater than number of signals).

### Recommended Cold-Start Protocol for Syndicate

Given 3-7 agent teams and 50-100 initial trades:

```
Phase 1 (0-30 trades): Equal weights
  - All teams get equal allocation
  - Focus on collecting IC data

Phase 2 (30-100 trades): Shrunk IC-weighted
  - Compute rolling IC for each team
  - Apply James-Stein shrinkage toward equal weights
  - Weight: w_i = (1-alpha) × IC_i^2/sum(IC_k^2) + alpha × 1/N
  - alpha starts high (~0.8) and decreases as data accumulates

Phase 3 (100-500 trades): Bayesian Black-Litterman
  - Use Phase 2 weights as prior
  - Update with new trade outcomes
  - Incorporate signal covariance estimation

Phase 4 (500+ trades): Full optimization
  - Sufficient data for covariance estimation with shrinkage
  - Can use online learning (MWU/Thompson Sampling) for adaptive weights
  - Monitor for regime changes and adjust accordingly
```

---

## Key Formulas Summary

### Signal Quality
```
IC = rank_corr(predicted, actual)
ICIR = mean(IC) / std(IC)
IR = TC × IC × sqrt(BR)
```

### Signal Combination
```
alpha_i = IC × vol_i × score_i                    # Single signal to alpha
SR_combined = sqrt(sum(SR_k^2))                     # N uncorrelated signals
IC_combined = sqrt(sum(w_k^2 × IC_k^2))            # Weighted IC combination
```

### Bayesian Combination (Black-Litterman)
```
E(R) = [(tau×Sigma)^(-1) + P^T×Omega^(-1)×P]^(-1) × [(tau×Sigma)^(-1)×Pi + P^T×Omega^(-1)×Q]
```

### Online Learning
```
MWU regret:   O(sqrt(T × ln(N)))
EXP3 regret:  O(sqrt(T × K × ln(K)))
TS regret:    O(sqrt(K × T × ln(T)))    [instance-independent]
              O(K × ln(T) / Delta)       [instance-dependent]
```

### Shrinkage
```
mu_JS = b + (1-alpha)(mu_sample - b)
Sigma_LW = (1-delta)×Sigma_sample + delta×B
```

### Diversification
```
sigma_p^2 = w^T × Sigma × w
Benefit: 2×w1×w2×sigma1×sigma2×rho    (negative when rho < 0)
```

---

## Sources

### IC and Fundamental Law
- [PyQuant News: Information Coefficient](https://www.pyquantnews.com/the-pyquant-newsletter/information-coefficient-measure-your-alpha)
- [CFA Analyst Prep: Fundamental Law of Active Management](https://analystprep.com/study-notes/cfa-level-2/state-and-interpret-the-fundamental-law-of-active-portfolio-management-including-its-component-terms-transfer-coefficient-information-coefficient-breadth-and-active-risk-aggressiveness/)
- [Corporate Finance Institute: Fundamental Law](https://corporatefinanceinstitute.com/resources/career-map/sell-side/capital-markets/fundamental-law-of-active-management/)
- [MSCI Barra: Converting Scores Into Alphas](https://app2.msci.com/products/analytics/aegis/PI_Converting_Scores_Into_Alphas.pdf)

### Bayesian Combination
- [PyPortfolioOpt: Black-Litterman](https://pyportfolioopt.readthedocs.io/en/latest/BlackLitterman.html)
- [Black-Litterman in Algo Trading](https://reasonabledeviations.com/2020/01/04/black-litterman-algotrading/)
- [Hudson & Thames: Bayesian Portfolio Optimisation](https://hudsonthames.org/bayesian-portfolio-optimisation-the-black-litterman-model/)
- [Bayesian Model Averaging Tutorial (Hoeting et al.)](https://www.stat.colostate.edu/~jah/papers/statsci.pdf)

### Online Learning
- [Jeremy Kun: EXP3 Algorithm](https://www.jeremykun.com/2013/11/08/adversarial-bandits-and-the-exp3-algorithm/)
- [Jeremy Kun: Multiplicative Weights Update](https://www.jeremykun.com/2017/02/27/the-reasonable-effectiveness-of-the-multiplicative-weights-update-algorithm/)
- [Arora, Hazan, Kale: MWU Survey](https://www.cs.princeton.edu/~arora/pubs/MWsurvey.pdf)
- [SMPyBandits: Non-Stationary Bandits](https://smpybandits.github.io/NonStationaryBandits.html)
- [Garivier & Moulines: Non-Stationary Bandit UCB Policies](https://arxiv.org/abs/0805.3415)

### Ensemble Methods
- [Stefan Jansen: ML for Trading — Gradient Boosting](https://stefan-jansen.github.io/machine-learning-for-trading/12_gradient_boosting_machines/)
- [Springer: Ensemble Learning for Crypto](https://link.springer.com/article/10.1007/s44163-025-00519-y)

### Regime Switching
- [Regime-Switching Signals (arxiv)](https://arxiv.org/html/2402.05272v2)
- [MicroAlphas: Market Regimes and Signal Stability](https://microalphas.com/market-regimes-signals/)
- [MDPI: Regime-Switching Factor Investing with HMMs](https://www.mdpi.com/1911-8074/13/12/311)

### Equal Weighting vs Optimization
- [DeMiguel, Garlappi, Uppal (2009): 1/N Portfolio](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1376199)
- [ReSolve: Simple vs Optimal Portfolio Methods](https://investresolve.com/portfolio-optimization-simple-optimal-methods/)
- [QuantPedia: Outperforming Equal Weighting](https://quantpedia.com/outperforming-equal-weighting/)
- [Forecast Combination Puzzle](https://www.sciencedirect.com/science/article/abs/pii/S0169207016000327)

### Diversification
- [Gregory Gundersen: Portfolio Theory](https://gregorygundersen.com/blog/2021/05/04/portfolio-theory/)
- [AQR: Uncorrelated Assets](https://www.aqr.com/Insights/Perspectives/Uncorrelated-Assets-An-Important-Dimension-of-an-Optimal-Portfolio-1_12)
- [Sharpe Ratio (Stanford)](https://web.stanford.edu/~wfsharpe/art/sr/sr.htm)

### Estimation Error and Shrinkage
- [MOSEK: Dealing with Estimation Error](https://docs.mosek.com/portfolio-cookbook/estimationerror.html)
- [Ledoit & Wolf: Honey, I Shrunk the Sample Covariance Matrix](http://www.ledoit.net/honey.pdf)
- [Ledoit & Wolf: Covariance Review](http://www.ledoit.net/Review_Paper_2020_JFEc.pdf)

### Thompson Sampling
- [Stanford: Tutorial on Thompson Sampling](https://web.stanford.edu/~bvr/pubs/TS_Tutorial.pdf)
- [Agrawal & Goyal: Analysis of Thompson Sampling](http://proceedings.mlr.press/v23/agrawal12/agrawal12.pdf)
- [MDPI: Thompson Sampling for Non-Stationary Bandits](https://www.mdpi.com/1099-4300/27/1/51)

### Crypto Trading
- [SSRN: Quantitative Alpha in Crypto Markets](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5225612)
- [Liu et al.: Trend Factor for Crypto](https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/trend-factor-for-the-cross-section-of-cryptocurrency-returns/4C1509ACBA33D5DCAF0AC24379148178)
- [QuantPedia: Crypto Trading Research](https://quantpedia.com/cryptocurrency-trading-research/)
