# On-Chain Trading Knowledge

## Smart Money On-Chain Tracking Methodology
- **Address classification**: Tier 1 = wallets with >60% win rate over 100+ trades and >$1M AUM. Tier 2 = 50-60% win rate, >$100K. Tier 3 = <50% (noise, ignore)
- **Signal types**: ADD HOLDINGS (accumulation — bullish), REDUCE HOLDINGS (distribution — bearish), NEW POSITION (fresh conviction), FULL EXIT (lost conviction entirely)
- **Signal timing**: On-chain moves are visible 1-24h BEFORE price impact. Large transfers to DEX = about to sell. Large transfers from exchange to cold wallet = accumulation
- **Chain-specific patterns**:
  - Ethereum mainnet: Largest whale activity, gas spikes signal urgency (whales willing to pay high gas = high conviction)
  - Solana: Faster cycles, DEX volume spikes precede price moves by minutes, not hours
  - BSC: Meme token concentration, watch PancakeSwap new pair listings
- **Volume-weighted signals**: One whale moving $5M > 100 addresses moving $50K each. Weight signals by notional value

## Exchange Flow Analysis (Capital Movement)
- **Net exchange flow**: OUTFLOW (negative) = accumulation, whales pulling to cold storage (bullish). INFLOW (positive) = distribution, preparing to sell (bearish). STABLE = no signal, neutral
- **Flow magnitude thresholds**:
  - BTC: >10K BTC daily net outflow = significant accumulation. >10K inflow = significant selling pressure
  - ETH: >100K ETH daily net flow = significant
  - Stablecoins: USDT/USDC inflow to exchanges = dry powder ready to buy (bullish for all crypto). Outflow = capital leaving system (bearish)
- **Exchange reserve ratio**: Current reserves / 30-day avg reserves. <0.95 = meaningful outflow. >1.05 = meaningful inflow
- **Post-crash context**: Outflows after -20% crash = bottom forming (smart money buying the dip). Outflows during rally = still accumulating (trend continuation)

## Whale Behavior Patterns
- **Accumulation patterns**: Slow, consistent outflows over 5-15 days (not one big move). Multiple wallets receiving from same exchange = coordinated accumulation. OTC desk activity rising = institutional buying (not visible on-chain but inferred from exchange balance drops without large on-chain sells)
- **Distribution patterns**: Large deposits to multiple exchanges simultaneously. Increasing exchange inflow while price rising = selling into strength. Whale wallets splitting into smaller amounts before selling = trying to minimize market impact
- **Dormant wallet activation**: Wallets inactive >1 year suddenly moving = CRITICAL signal. If moving to exchange = massive sell pressure incoming. If moving to new cold wallet = just custody reorganization (neutral)
- **Miner behavior**: Miner outflow to exchanges = selling pressure. Miner accumulation (not selling block rewards) = extreme bullish conviction

## Network Health Metrics for Trading
- **Hash rate / Network power**: New ATH = miners investing (6-12 month bullish horizon). Declining >10% = miners capitulating (short-term bearish, medium-term bullish if price holds)
- **Active addresses**: Rising active addresses + rising price = healthy bull. Rising addresses + falling price = panic activity (bearish). Declining addresses in bear = capitulation (bullish contrarian)
- **Transaction count**: Sustained >300K daily BTC transactions = healthy network usage. <200K = reduced activity (bearish for momentum)
- **Mempool size**: Rising mempool = increasing demand for block space (bullish activity). Empty mempool for extended period = low interest (bearish)
- **NVT ratio** (Network Value to Transactions): NVT > 90 = overvalued (price exceeds usage). NVT < 50 = undervalued. Use 28-day smoothed NVT, not raw

## DeFi Protocol Health Signals
- **TVL trends**: Rising TVL + rising price = fundamental support for rally. Rising TVL + falling price = accumulation in protocols despite bearish sentiment (bullish divergence). Falling TVL rapidly = capital flight (bearish)
- **Protocol revenue**: Protocols generating >$1M monthly revenue with P/S < 20 = fundamentally strong. Revenue declining quarter-over-quarter = competitive threat or narrative death
- **DEX volume**: DEX/CEX volume ratio rising = DeFi adoption (structurally bullish for DeFi tokens). Ratio falling = capital returning to centralized (neutral for L1s)
- **Stablecoin market cap**: Total stablecoin MCap rising = new capital entering crypto ecosystem (macro bullish). Declining = capital exiting (macro bearish)
- **Bridge flows**: Capital flowing from Ethereum → L2s/alt-L1s = rotation into higher-yield opportunities. Capital flowing back to Ethereum = risk-off within DeFi

## UTXO Analysis (Bitcoin-Specific)
- **HODL Waves**: >60% of supply unmoved for 1+ year = strong holder base (bullish macro). When long-term holders start moving = distribution phase beginning
- **SOPR (Spent Output Profit Ratio)**: <1.0 = holders selling at a loss (capitulation if sustained). >1.0 = holders selling at profit. Reset to 1.0 after bear = breakeven sellers exhausted (bullish)
- **Realized Price**: Average acquisition cost of all BTC. Price below realized price = market-wide loss (historically strong buy). Price 2x+ above realized price = frothy (caution)
- **Supply in profit**: <50% of supply in profit = deep bear, historically strong accumulation zone. >90% in profit = everyone profitable, distribution risk elevated
