# Macro Trading Knowledge

## Full Derivatives Data Framework
- **Funding rate interpretation**: Aggregated funding across exchanges is more reliable than single-exchange. When all exchanges show negative funding = system-wide short crowding (squeeze risk). All positive = system-wide long crowding (liquidation risk)
- **Open Interest as leverage gauge**: Total OI / Total MCap = system leverage ratio. >3% = dangerously leveraged. <1% = deleveraged (bottoming signal). OI change rate matters more than absolute level
- **Liquidation mapping**: $100M+ liquidation events in 4h = forced selling complete, bottom likely within 24h. $50M+ cascading liquidations across 3+ exchanges = systemic deleveraging
- **Basis (futures vs spot premium)**: Positive basis (contango) = bullish market structure. Negative basis (backwardation) = bearish, hedging demand exceeds speculation. Basis > 15% annualized = overheated

## Regime Detection (HMM-Based)
- **3-state model**: Bull (high return, low vol), Bear (negative return, high vol), Transition (near-zero return, rising vol)
- **Regime identification signals**:
  - Bull → Bear transition: VIX spike >25, BTC weekly close below 20-week SMA, F&G drops >30 points in 2 weeks
  - Bear → Bull transition: Declining volatility for 30+ days, funding rates normalizing from extreme negative, BTC reclaims 20-week SMA
- **Regime persistence**: Average bull regime lasts 400-600 days, bear 200-400 days. Don't call regime change until at least 3 weeks of evidence
- **Regime-specific strategies**: Bull = momentum + breakout. Bear = mean reversion + short. Transition = reduce size, widen stops

## Correlation & Factor Decomposition
- **BTC correlation**: In crisis (correlation >0.9), all crypto moves together. Diversification is an illusion. Only hedge is cash or BTC puts
- **Cross-asset correlations**: BTC-SPX correlation: 0.4-0.6 in normal times, >0.8 in crisis. BTC-DXY: -0.3 to -0.5 (dollar strength bearish for crypto). BTC-Gold: 0.1-0.3 (weak, not a reliable hedge)
- **Decorrelation events**: Fed rate decisions (BTC decorrelates from equities for 24-48h). Halving (crypto-specific, zero equity correlation). Exchange hacks/failures (crypto-specific risk event)
- **Factor rotation**: In early bull, small-cap + high-beta outperforms. In late bull, quality + large-cap outperforms. In bear, cash + BTC dominance outperforms

## Federal Reserve & Monetary Policy Impact
- **Rate decisions**: Markets price in expectations. Surprise hawkish = -5 to -15% BTC within 48h. Surprise dovish = +5 to +10%. As expected = minimal impact (already priced in)
- **Transmission timeline**: 0-1 month = minimal crypto impact. 1-3 months = risk assets adjust. 3-6 months = full transmission to crypto. 6-12 months = second-order effects (M2, lending)
- **QE/QT**: QE (money printing) = strongest bullish macro signal for crypto. QT (balance sheet reduction) = persistent headwind. Track M2 money supply with 10-12 week lead
- **Real rates**: Negative real rates (inflation > Fed funds rate) = bullish for crypto as inflation hedge. Positive real rates = bearish (yield competition)

## Prediction Market Intelligence
- **Polymarket interpretation**: Volume >$1M per market = real money conviction, highly reliable. $100K-$1M = directional but noisy. <$100K = ignore (low liquidity, easily manipulated)
- **Key markets to track**: Federal funds rate probability, recession probability, regulatory outcomes (ETF approval, enforcement actions)
- **Probability thresholds**: Recession prob <25% = crypto tailwind. 25-40% = headwind, reduce risk. >40% = strong headwind, defensive positioning
- **Leading indicator quality**: Polymarket leads traditional polls by 1-7 days. Sharp probability moves (>10 points in 24h) = significant new information

## Macro Risk-On / Risk-Off Framework
- **Risk-on signals (need 3+ for confirmation)**: VIX <20, DXY declining, yield curve normalizing, M2 growing, positive PMI trend, crypto funding rates mildly positive
- **Risk-off signals (need 3+ for confirmation)**: VIX >25, DXY rising, yield curve inverting, M2 contracting, negative PMI, crypto funding deeply negative
- **BTC dominance as risk gauge**: >60% = extreme risk-off (capital fleeing to BTC safety). 50-60% = cautious. 40-50% = risk-on (alt season forming). <40% = euphoria (peak risk)
- **Macro trumps micro**: In risk-off regimes, even fundamentally strong altcoins fall 60-80%. Position sizing > coin selection in macro regimes

## Transaction Cost Reality
- **Crypto**: 80 bps round-trip (0.1% maker + 0.1% taker + 0.05% slippage x2 + funding). For derivatives: add 0.03-0.05% per 8h funding period
- **Market impact**: Orders >$1M face 10-50 bps additional slippage depending on liquidity. $10M+ orders = 100-500 bps impact
- **The Sharpe tax**: Transaction costs reduce raw Sharpe by 0.3-0.5 for active strategies. A strategy with gross Sharpe 1.5 may have net Sharpe 1.0 after costs
