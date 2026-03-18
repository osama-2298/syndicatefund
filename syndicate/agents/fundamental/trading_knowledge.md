# Fundamental Analysis Trading Knowledge

## Quantitative Valuation Framework
- **FDV/MCap ratio**: <1.3 = low dilution risk (bullish). 1.3-2.5 = moderate. >2.5 = significant unlock pressure. >5 = extreme (avoid or short)
- **Supply dynamics**: <50% circulating = major unlock risk ahead. Check vesting schedules. Large unlock within 30 days = sell pressure catalyst
- **ATH distance**: -50% from ATH = historically 90% 1-year win rate, median +95% return. -70% = 100% historical win rate. But context matters — dead projects also fall 90%
- **Revenue multiples**: For DeFi protocols with revenue: P/S < 10 = undervalued in crypto context. P/S > 100 = pure speculation
- **TVL/MCap ratio**: >1.0 = TVL exceeds market cap (undervalued by usage). <0.1 = pure speculation, no protocol backing

## Factor Model Construction (Fama-French adapted for crypto)
- **Market Factor (MKT)**: Beta to BTC. Coins with beta > 1.5 amplify BTC moves (high-beta plays)
- **Size Factor (SMB)**: Small caps outperform in bull regimes, massively underperform in bears
- **Value Factor (HML)**: In crypto, "value" = ATH distance + FDV/MCap + revenue. Deep value wins in recovery phases
- **Momentum Factor (UMD)**: 3-month momentum is the strongest crypto factor. Top quintile = +15% monthly alpha historically. BUT crashes hard in regime transitions
- **Liquidity Factor**: Illiquid tokens carry a premium but gap down violently. Volume/MCap ratio < 0.01 = illiquidity risk
- **Alpha decomposition**: If a token's return is fully explained by BTC beta + momentum, there is NO alpha. Seek idiosyncratic returns

## Statistical Rigor Requirements
- **Information Coefficient**: Signal must show IC > 0.02 (correlation between prediction and outcome). Most "fundamental" signals fail this test
- **t-statistic**: Signal significance requires t-stat > 2.0 (p < 0.05). With multiple testing, use Bonferroni correction
- **Information Ratio**: IR > 0.5 indicates genuine alpha. IR < 0.2 = noise
- **Degrees of freedom**: Minimum 20 observations per parameter tested. With 5 factors, need 100+ data points
- **Walk-forward validation**: NEVER backtest on full dataset. Split 60/20/20 (train/validate/test). Out-of-sample results only
- **Parameter sensitivity**: Strategy must be stable within +/-20% parameter changes. If Sharpe drops 50% with 10% parameter change = overfit

## Token Economics & Unlock Analysis
- **Cliff unlocks**: 10%+ supply unlock in single event = -15 to -30% avg price impact. Trade BEFORE the event (sell 3-7 days prior)
- **Linear vesting**: Gradual unlocks (1-2% monthly) have minimal price impact if absorbed by demand
- **Insider behavior**: If insiders are staking/locking rather than selling post-unlock = bullish. If moving to exchanges immediately = bearish
- **Staking ratio**: >60% staked = reduced sell pressure. <30% staked = liquid supply can dump. Rising staking ratio = accumulation signal

## Financial Calculation Methods
- **Discounted Cash Flow** (for revenue protocols): NPV = Sum of (Cash Flow / (1+r)^n). Use 30-50% discount rate for crypto (reflects risk)
- **Relative valuation**: Compare P/S, P/E ratios within same sector (L1 vs L1, DeFi vs DeFi). Cross-sector comparison is meaningless
- **Network value models**: Metcalfe's Law: Value proportional to n^2 (active addresses squared). NVT ratio = Market Cap / Transaction Volume. High NVT = overvalued
- **Terminal value**: For infrastructure (L1s), assume perpetual growth. For application tokens, assume limited lifespan

## When Fundamentals vs Price Disagree
- **Cheap + Price falling**: Value trap. Need catalyst (product launch, partnership, upgrade) to reverse. Don't catch falling knives on fundamentals alone
- **Expensive + Price rising**: Momentum play. Fundamentals will matter eventually, but can persist for months. Ride with trailing stop
- **Cheap + Price rising**: Best setup. Fundamental value being recognized. Highest conviction long
- **Expensive + Price falling**: Avoid entirely. Market is pricing in something you might not see (insider selling, competitor, regulatory risk)
