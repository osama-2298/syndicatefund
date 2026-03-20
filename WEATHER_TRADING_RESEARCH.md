# Weather Bot Trading on Polymarket & Kalshi — Deep Research

## Executive Summary

Weather prediction markets are one of the fastest-growing segments on both Polymarket and Kalshi. Daily temperature markets across 49+ cities generate significant volume. The edge comes from **NWP model ensembles** vs. market prices, **data release timing** exploitation, and **market making** around fair value. This document covers everything needed to build a profitable weather trading bot.

---

## 1. Platform Comparison

### Polymarket (Crypto, Unregulated)

| Feature | Details |
|---------|---------|
| **Market Type** | Binary outcomes on CLOB (Central Limit Order Book) |
| **Resolution Source** | **Weather Underground (NOT NWS)** — e.g., wunderground.com/history/daily/us/ny/new-york-city/KLGA |
| **Cities** | 29 US + 20 international = **49 cities** (NYC, Chicago, London, Tokyo, Shanghai, Hong Kong, etc.) |
| **Market Structure** | Negative-risk multi-outcome: 7-11 temp buckets per city per day (e.g., "43F or below", "44-45F", ..., "62F or higher") |
| **Active Markets** | ~421 weather markets, 317 are daily temperature, **$2M+ daily volume** |
| **Tick Size** | $0.001 (0.1 cent) |
| **Settlement** | On-chain (Polygon), off-chain matching |
| **Fees** | **ZERO fees on weather markets** (only crypto/sports have fees) |
| **Liquidity** | NYC ($197K/day, $146K depth), London ($240K), Tokyo ($330K), Shanghai ($381K) |
| **API** | REST + WebSocket CLOB API |
| **SDKs** | Python (`py-clob-client`), Rust (`rs-clob-client`, `polyfill-rs`) |
| **Infrastructure** | AWS eu-west-2 (London). Best latency from Dublin (~0.83ms) |
| **Batch Orders** | Up to 15 orders per batch call |
| **Geo Restrictions** | US persons prohibited (Terms of Service) |

### Kalshi (US-Regulated, CFTC)

| Feature | Details |
|---------|---------|
| **Market Type** | Event contracts (binary options) on central exchange |
| **Resolution Source** | **NWS Daily Climate Report (CLI)** — released morning after, Local Standard Time |
| **Cities** | NYC, Chicago, Miami, LA, Denver, Austin (6 primary cities) |
| **Market Structure** | KXHIGH series: 6 brackets per city per day (4 middle at 2°F wide, 2 unbounded edges) |
| **Fees** | Taker: `ceil(0.07 * P * (1-P))` per contract, **max 1.75¢ at 50¢**. Maker: 1/4 of taker. |
| **Median Stake** | ~$9K per contract — **thin liquidity** |
| **Interest** | **~4% APY** on cash + open positions (min $250 balance) |
| **Regulation** | CFTC-regulated DCM (Designated Contract Market) |
| **API** | REST + WebSocket, RSA-PSS authentication |
| **SDKs** | Official: Python (sync + async), TypeScript. Community: Rust, Go |
| **Order Types** | Limit, market, FOK, GTC, IOC, post-only, reduce-only |
| **Batch Orders** | Up to 20 orders per batch |
| **Legal Risk** | Arizona filed criminal charges (March 2026) — ongoing legal battle |
| **Order Groups** | Built-in risk controls with rolling 15-second cancel limits |

### Platform Verdict

- **Polymarket**: Higher liquidity on weather ($2M/day), more cities (49), zero fees, but US-restricted. Crypto-native (need USDC on Polygon).
- **Kalshi**: US-legal (for now), 4% APY on capital, but **much thinner** weather liquidity (~$9K median). Better for US-based operations.
- **Cross-platform arbitrage**: **CRITICAL EXPLOIT** — Polymarket resolves via Weather Underground, Kalshi resolves via NWS CLI. These sometimes disagree by 1°F (e.g., LaGuardia 29°F on Wunderground vs 30°F on NWS). Same weather event, different resolution = structural arbitrage.

### CRITICAL: Resolution Source Discrepancy (Exploitable)

**Polymarket** resolves from Weather Underground hourly observations at specific airport stations (KLGA for NYC, KORD for Chicago, etc.). **Kalshi** resolves from NWS Daily Climate Report (CLI). These are different data products that occasionally disagree:

- Wunderground shows hourly maxima; NWS CLI is the official daily max
- Celsius-to-Fahrenheit rounding can cause ±1°F discrepancy
- Temperature measurement timing (Local Standard Time for Kalshi vs. calendar day for Polymarket)
- Equipment calibration differences

**This means the same temperature can resolve differently on each platform**, creating risk-free arbitrage when you can identify the discrepancy before resolution.

---

## 2. Proven Profitable Weather Bots (Real Data)

### Verified Wallet Performance on Polymarket

| Wallet | Profit | Method | Capital | Notes |
|--------|--------|--------|---------|-------|
| **"meropi"** | ~$30K | Automated $1-$3 micro bets | Unknown | High-frequency, many small trades |
| **"1pixel"** | $18.5K | NYC + London only | $2.3K deposited | 8x return |
| **Anonymous** | $24K | London weather since Apr 2025 | ~$1K | GFS ensemble model |
| **Anonymous** | $65K | Multi-city | Unknown | Most profitable known weather trader |

### Microstructure Data (Becker 2025 — 72.1M trades analyzed)
- Weather **makers** earn **+1.29% per trade** on average
- Weather **takers** lose **-1.29% per trade** on average
- The "Optimism Tax": takers systematically overpay for YES shares
- **Implication**: Market making is the structural edge, not directional betting

### Key Trading Parameters from Successful Bots
- **Minimum edge threshold**: 8% for <24h horizon, 12% for 1-2 days, 15% for 3+ days
- **Position sizing**: Quarter-Kelly (0.25× Kelly criterion)
- **Max per trade**: $75-$100
- **Data source**: 31-member GFS ensemble via Open-Meteo (free, no API key)

---

## 3. Market Mechanics Deep Dive

### How Weather Markets Work

1. **Market Creation**: Each day, negative-risk multi-outcome markets with 7-11 temperature buckets per city
2. **Trading**: Shares trade $0.001-$0.999 (Polymarket) or $0.01-$0.99 (Kalshi)
3. **Resolution**: Polymarket: Weather Underground data. Kalshi: NWS CLI report (morning after)
4. **Settlement**: Winning bucket pays $1.00, all others pay $0.00
5. **Negative Risk**: Buying NO on one bucket = buying YES on all others (capital efficient)

### Key Timing (All UTC)

| Event | Time (UTC) | Significance |
|-------|-----------|--------------|
| **HRRR update** | Every hour | Freshest short-range forecast |
| **GFS update** | 00Z, 06Z, 12Z, 18Z | Major forecast shift events |
| **ECMWF update** | 00Z, 12Z | Highest-skill global model |
| **METAR observations** | :51-:58 past each hour | Real-time airport weather |
| **DSM release** | Varies by city (e.g., NYC ~20:21, 21:21, 05:17Z) | Intraday high temp updates |
| **6-hour max temps** | 23:51, 05:51, 11:51, 17:51Z | Captures highs missed by 5-min data |
| **CLI release** | 05:25-08:40Z (varies by city) | **Official resolution** — market settles |
| **24hr high report** | 04:51-07:56Z | Near-final high confirmation |

### Resolution Source Details

- **CLI (Climatological Report)**: Issued by NWS for each ASOS station. Contains the official max/min temperature for the day.
- Markets resolve based on this official number, NOT real-time observations.
- Rounding: Celsius-to-Fahrenheit conversion can create ±1°F ambiguity.

---

## 3. Known Bot Types in Weather Markets

Based on research from wethr.net (the primary weather trading community):

### DSM Bot (Data Release Sniper)
- **Strategy**: Monitors NWS Daily Summary Message releases
- **Edge**: Reacts to new high temperature readings before manual traders
- **Timing**: City-specific DSM release schedules (e.g., NYC ~20:21Z, 21:21Z, 05:17Z)
- **Defense**: Don't leave unprotected limit orders near expected highs during DSM windows

### OMO Bot (One-Minute Observation)
- **Strategy**: Accesses 1-minute ASOS observation data between public 5-minute updates
- **Edge**: 1-4 minute head start on temperature readings
- **Limitation**: Celsius rounding ambiguity
- **Risk Level**: Medium — data advantage is narrow

### 6-Hour Bot
- **Strategy**: Monitors 6-hourly maximum temperature fields in NWS hourly obs
- **Timing**: ~23:51Z, ~05:51Z, ~11:51Z, ~17:51Z
- **Edge**: Captures highs that may not appear in standard 5-minute timeseries

### "240" Market Maker Bot
- **Strategy**: Provides liquidity with large orders (e.g., 240 contracts) on both sides
- **Spread**: Maintains ~2 cent spreads
- **Behavior**: Adjusts pricing based on internal forecast model and inventory
- **Key Insight**: This is the bot to emulate — consistent profit from spread capture

### UI Bot & "1-Up" Bot
- **UI Bot**: Rapid order placement/cancellation causing visual noise — mostly harmless
- **1-Up Bot**: Places orders 1 cent better than current best — queue positioning strategy

---

## 4. Weather Prediction Models — Your Edge

### Tier 1: Numerical Weather Prediction (NWP) Models

| Model | Provider | Resolution | Update Freq | Forecast Range | Access |
|-------|----------|-----------|-------------|----------------|--------|
| **HRRR** | NOAA | 3km | Hourly | 18-48 hours | Free (NOMADS, AWS) |
| **GFS** | NOAA | 25km | Every 6 hours | 16 days | Free (NOMADS, AWS) |
| **NAM** | NOAA | 12km | Every 6 hours | 3.5 days | Free (NOMADS) |
| **ECMWF IFS** | ECMWF | 9km | Every 12 hours | 15 days | Paid (some open data) |
| **ECMWF AIFS** | ECMWF | ~25km | Every 12 hours | 15 days | Open data (operational since Feb 2025) |
| **GEM** | Canada CMC | 25km | Every 12 hours | 16 days | Free |
| **ICON** | DWD Germany | 13km | Every 6 hours | 7.5 days | Free |
| **NBM** | NOAA | 2.5km | Hourly | 10 days | Free — **THIS IS THE GOLD STANDARD FOR US TEMPS** |

**Key Insight**: The **National Blend of Models (NBM)** is NOAA's official multi-model blend. It already combines GFS, NAM, ECMWF, HRRR, and applies MOS corrections. For US temperature markets, NBM is your strongest single-model baseline.

### Tier 2: AI/ML Weather Models (The New Edge)

| Model | Provider | Status | Key Advantage |
|-------|----------|--------|---------------|
| **ECMWF AIFS** | ECMWF | Operational (Feb 2025) | Graph neural network, 1000x less compute, outperforms IFS on many metrics |
| **GenCast** | Google DeepMind | Published (Nature, Dec 2024) | Diffusion model, beats ECMWF ENS on 97.2% of targets, probabilistic |
| **GraphCast** | Google DeepMind | Open source | 10-day forecasts in under 60 seconds |
| **Pangu-Weather** | Huawei | Open source | Competitive with ECMWF at much lower cost |
| **FourCastNet** | NVIDIA | Open source | Vision transformer architecture |
| **Aurora** | Microsoft | Research | Foundation model approach |

**GenCast is the most relevant for trading**: It's a probabilistic ensemble model that directly outputs probability distributions. Beats ECMWF ENS on 99.8% of targets beyond 36 hours. Published in Nature.

### Tier 3: Ensemble Methods (The Real Edge)

The proven profitable approach (used by Polyforecast and others):

1. Run **5+ independent models**: GFS, ECMWF, ECMWF-AI (AIFS), ICON, GEM
2. For each model, extract the **forecast high temperature** for each city
3. Convert forecasts to **probability distributions** across temperature buckets
4. **Ensemble the probabilities** (weighted average, or Bayesian combination)
5. Compare ensemble probability to **market price**
6. Trade when ensemble shows **significant edge** (e.g., >10% deviation)

### Accessing Model Data

**Best tool**: [Herbie](https://herbie.readthedocs.io/) — Python library for downloading NWP data

```python
from herbie import Herbie

# Get latest HRRR 2m temperature forecast
H = Herbie("2026-03-20 12:00", model="hrrr", fxx=6)
ds = H.xarray("TMP:2 m")

# Get GFS forecast
H = Herbie("2026-03-20 12:00", model="gfs", fxx=24)
ds = H.xarray("TMP:2 m")
```

Supports: HRRR, GFS, RAP, NAM, ECMWF, NBM, GEFS, ICON, GEM, and 15+ models. Downloads from NOMADS, AWS, Google Cloud automatically.

**Other data APIs**:
- **Open-Meteo Ensemble API**: Free, no key needed. 16 models, 200+ ensemble members. `https://ensemble-api.open-meteo.com/v1/ensemble`
- **Open-Meteo Previous Runs API**: Shows what past model runs predicted — **critical for backtesting**. Available since Jan 2024.
- **Open-Meteo Historical Forecast API**: 2-5 years of concatenated first-hour forecasts — backtest calibration.
- **ECMWF Open Data**: Became **free (CC BY-4.0)** on October 1, 2025. Python: `pip install ecmwf-opendata`. 2-hour delay vs real-time.
- **weather.gov**: Official NWS API (free, 5 req/sec)
- **Iowa Environmental Mesonet (IEM)**: Gold mine for historical ASOS station data — **1-minute observations going back to 2000+** for all US airports. Free.
- **Visual Crossing**: $35/month, historical + forecast, good for backtesting
- **Tomorrow.io**: 500 free calls/day, 80+ weather variables

**Key model update note**: HRRR and NAM are being replaced by **RRFS (Rapid Refresh Forecast System)** in early 2026 — same 3km resolution, extends to 84 hours.

---

## 5. Optimal Bot Strategies (Ranked by Expected Edge)

### Strategy 1: Ensemble Fair Value Market Maker (HIGHEST EXPECTED RETURN)

**Concept**: Quote bid/ask around your model's fair value, capture spread.

**Architecture**:
```
┌─────────────────────────────────────────────┐
│                Data Pipeline                 │
│  HRRR (hourly) + GFS (6h) + ECMWF (12h)   │
│  + NBM (hourly) + ICON (6h) + GEM (12h)    │
│  + AIFS (12h) + GenCast (if available)      │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│           Probability Engine                 │
│  For each city × each temp bucket:          │
│  1. Each model → forecast high temp         │
│  2. Convert to PDF (normal dist, σ from     │
│     model historical error)                 │
│  3. Integrate PDF over bucket range         │
│  4. Weighted ensemble of all model probs    │
│  5. Calibrate against historical accuracy   │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│          Market Making Engine                │
│  For each market:                           │
│    fair_value = ensemble_probability        │
│    spread = f(volatility, time_to_resolve,  │
│              inventory, liquidity)           │
│    bid = fair_value - spread/2              │
│    ask = fair_value + spread/2              │
│    size = kelly_fraction(edge, bankroll)    │
│  Post limit orders, cancel/replace on       │
│  model updates                              │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│            Risk Management                   │
│  - Max position per market: 5% of bankroll  │
│  - Max correlated exposure: 15% of bankroll │
│  - Pull quotes if spread narrows below edge │
│  - Inventory skew: shift quotes to flatten  │
│  - Widen spread near DSM release times      │
└─────────────────────────────────────────────┘
```

**Expected Edge**: 3-8% per market cycle (daily). Polyforecast reports consistent positive returns using this approach with 5 models.

**Key Parameters**:
- Minimum edge to trade: 5-10 cents (5-10% probability deviation)
- Spread: 2-4 cents for liquid markets (NYC, Chicago), 4-8 cents for thin markets
- Inventory limit: ±500 contracts per bucket per city
- Rebalance frequency: Every model update (hourly for HRRR, 6h for GFS)

### Strategy 2: Data Release Sniper (MEDIUM EDGE, LOW CAPITAL)

**Concept**: React to NWS data releases faster than the market.

**Architecture**:
```
┌─────────────────────────────────────────────┐
│         Real-Time Data Monitor               │
│  Poll NWS ASOS data every 60 seconds        │
│  Monitor DSM feeds at city-specific times    │
│  Watch METAR updates at :51-:58 past hour   │
│  Parse 6-hour max temps at known times      │
└────────────────┬────────────────────────────┘
                 │ New high temp detected!
┌────────────────▼────────────────────────────┐
│         Signal Generator                     │
│  IF new_observed_high > market_expected_high │
│    → BUY higher bucket, SELL lower bucket   │
│  IF new_observed_high confirms bucket        │
│    → BUY that bucket to ~95-99¢             │
│  IF new_observed_high eliminates bucket      │
│    → SELL that bucket immediately            │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│         Execution Engine                     │
│  Market order or aggressive limit (±1¢)     │
│  Latency target: <500ms from data to order  │
│  Use WebSocket for order book monitoring     │
│  Cancel stale orders immediately             │
└─────────────────────────────────────────────┘
```

**Expected Edge**: 5-15% per successful snipe, but opportunities are intermittent. Works best when observed temp is near a bucket boundary.

**Critical Timing Table** (city-specific DSM release times are THE key data):

| City | DSM Times (UTC) | METAR | CLI |
|------|-----------------|-------|-----|
| NYC (KNYC) | ~20:21, 21:21, 05:17 | :51 | ~06:00 |
| Chicago (KORD) | varies | :51 | ~06:30 |
| London (EGLL) | varies | :50 | varies |
| (29 US + 20 intl cities — full table at wethr.net) | | | |

### Strategy 3: Forecast Convergence Trader (MEDIUM EDGE, HIGHER CAPITAL)

**Concept**: Trade when multiple models agree but the market hasn't caught up.

**When to trade**:
- Model update comes in (e.g., 12Z GFS) showing significant shift
- Your ensemble probability moves >5% from market price
- Multiple models are converging on same temperature range
- Market is still priced at the old consensus

**Position sizing**: Kelly criterion adapted for binary outcomes:
```
f* = (p * b - q) / b
where:
  p = your ensemble probability
  q = 1 - p
  b = (1/market_price) - 1  (the odds)
  f* = fraction of bankroll to wager
Use 0.25× Kelly for safety.
```

### Strategy 4: NWS Rounding Exploitation (NICHE, HIGH SKILL)

**Concept**: ASOS temperature observations undergo lossy rounding that creates predictable ambiguity near bucket boundaries.

**The Rounding Chain**:
1. Measured in °F (rounded to whole number)
2. Converted to °C (rounded to whole number)
3. Converted back to °F (rounded again)
4. A displayed 70°F could originate from actual measurements spanning several tenths of a degree

**Edge**: When temperature is near a settlement threshold, understanding the rounding chain helps predict which side the CLI will land on. **Hourly METAR** observations (:51-:54) have higher precision than 5-minute ASOS data. **SPECI reports** (triggered by significant weather changes) have exact readings. The final **CLI report** incorporates OMO (1-minute observation) data which may capture peaks missed by rounded 5-minute data.

### Strategy 5: Asymmetric Tail Bets (HIGH VARIANCE, HUGE PAYOFF)

**Concept**: When ensemble spread is large (high uncertainty), extreme outcome buckets are systematically underpriced.

**Real Example**: Trader "Hans323" made **$1.11M from a $92K bet** on a London weather outcome priced at 8% implied probability. When ensemble members widely disagree, tail outcomes happen more often than the market expects.

**When to use**:
- Large ensemble spread (members don't agree)
- Sea-breeze fronts, passing cold fronts, or unexpected clearing can cause dramatic intraday swings
- 15% fractional Kelly on tail bets to manage variance

### Strategy 6: Known Model Bias Exploitation (SYSTEMATIC EDGE)

**Concept**: Trade against known systematic biases in NWP models.

| Model | Known Bias | Trading Implication |
|-------|------------|---------------------|
| **GFS** | Persistent cold bias in 2m temperature | If GFS says 75°F, actual likely higher → buy higher bucket |
| **ECMWF** | Underestimates diurnal cycle by 1-2K in summer (cold bias day, warm bias night) | Summer daytime highs likely higher than ECMWF forecast |
| **ECMWF** | Cold bias 0.5-1K at night in winter (Europe) | Winter lows in Europe likely warmer |
| **All models** | Miss urban heat island effects | Airport stations near concrete/tarmac may read higher |
| **Coastal models** | Often miss sea breeze timing | Coastal cities (Boston, SF) can drop 10-15°F when sea breeze develops |

### Strategy 7: Cross-Platform Arbitrage (LOW EDGE, HIGH COMPLEXITY)

**Concept**: Buy on Polymarket, sell on Kalshi (or vice versa) when same weather event is priced differently.

**Challenges**:
- Different resolution sources (Wunderground vs NWS CLI)
- Capital locked on two platforms
- Polymarket = crypto (USDC), Kalshi = USD
- Execution risk: prices move before both legs fill
- US restrictions on Polymarket

**When it works**: Markets with very different participant bases. Polymarket weather markets tend to be more efficient (more bot activity), Kalshi may lag.

### Strategy 8: Climatological Baseline Fade (LOWEST EDGE, SIMPLEST)

**Concept**: Compare market prices against climatological probabilities. Bet against markets that deviate significantly from historical norms, especially at longer time horizons (2+ days out).

**Data source**: NOAA Climate Normals (30-year averages by date and station).

**When it works**: Markets 3+ days before resolution where prices reflect recent weather bias rather than climatological reality.

---

## 6. Technical Implementation Guide

### Polymarket Bot Setup

```python
# Authentication & Setup
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs

client = ClobClient(
    host="https://clob.polymarket.com",
    key=PRIVATE_KEY,
    chain_id=137,  # Polygon
    signature_type=2,  # POLY_GNOSIS_SAFE
)

# Get API credentials
client.set_api_creds(client.create_or_derive_api_creds())

# Fetch weather markets
markets = client.get_markets(
    next_cursor="",
    tag="weather"  # or search by slug
)

# Place a limit order
order = client.create_order(
    OrderArgs(
        token_id="<YES_TOKEN_ID>",
        price=0.45,  # 45 cents = 45% probability
        size=100,    # 100 contracts
        side="BUY",
        fee_rate_bps=200,  # 2% fee
    )
)
resp = client.post_order(order)

# WebSocket for real-time order book
# Connect to: wss://ws-subscriptions-clob.polymarket.com/ws/
# Subscribe to market channels for live updates
# Send PING every 10 seconds
```

### Kalshi Bot Setup

```python
from kalshi_python_sync import KalshiClient
from cryptography.hazmat.primitives import serialization

# Load RSA key
with open("kalshi_private_key.pem", "rb") as f:
    private_key = serialization.load_pem_private_key(f.read(), password=None)

client = KalshiClient(
    api_key_id="YOUR_API_KEY_ID",
    private_key=private_key,
    host="https://api.elections.kalshi.com"
)

# Get weather markets
events = client.get_events(series_ticker="TEMP")  # Temperature markets

# Place order
order = client.create_order(
    ticker="TEMP-NYC-26MAR20-H54",  # NYC high temp 54°F on March 20
    side="yes",
    action="buy",
    yes_price=45,  # 45 cents
    count=100,
    time_in_force="good_till_canceled"
)

# Batch orders (up to 20)
orders = client.batch_create_orders([
    {"ticker": "TEMP-NYC-...", "side": "yes", "action": "buy", "yes_price": 42, "count": 50},
    {"ticker": "TEMP-NYC-...", "side": "no", "action": "buy", "no_price": 55, "count": 50},
])
```

### Weather Data Pipeline

```python
import openmeteo_requests
from herbie import Herbie
import numpy as np
from scipy.stats import norm

class WeatherFairValueEngine:
    """Calculate fair value probabilities for temperature buckets."""

    MODELS = {
        "hrrr": {"weight": 0.25, "sigma": 1.5},   # °F typical error
        "gfs": {"weight": 0.20, "sigma": 2.5},
        "ecmwf": {"weight": 0.25, "sigma": 2.0},
        "nbm": {"weight": 0.20, "sigma": 1.2},     # Best US model
        "icon": {"weight": 0.10, "sigma": 2.8},
    }

    def get_forecasts(self, city_lat, city_lon, target_date):
        """Pull forecasts from all models for a city."""
        forecasts = {}
        for model, params in self.MODELS.items():
            try:
                H = Herbie(target_date, model=model)
                ds = H.xarray("TMP:2 m")
                # Extract nearest gridpoint to city
                temp_k = ds.sel(latitude=city_lat, longitude=city_lon, method="nearest")
                temp_f = (temp_k - 273.15) * 9/5 + 32  # Convert K → °F
                forecasts[model] = float(temp_f)
            except Exception:
                continue
        return forecasts

    def calculate_bucket_probabilities(self, forecasts, buckets):
        """
        Convert model forecasts to probability distribution across buckets.

        buckets: list of (low, high) tuples, e.g., [(50, 51), (52, 53), ...]
        """
        ensemble_probs = np.zeros(len(buckets))
        total_weight = 0

        for model, temp_forecast in forecasts.items():
            if model not in self.MODELS:
                continue
            params = self.MODELS[model]
            weight = params["weight"]
            sigma = params["sigma"]
            total_weight += weight

            for i, (low, high) in enumerate(buckets):
                # Probability that true temp falls in [low, high]
                p = norm.cdf(high + 0.5, loc=temp_forecast, scale=sigma) - \
                    norm.cdf(low - 0.5, loc=temp_forecast, scale=sigma)
                ensemble_probs[i] += weight * p

        if total_weight > 0:
            ensemble_probs /= total_weight

        # Normalize to sum to 1
        ensemble_probs /= ensemble_probs.sum()

        return ensemble_probs

    def find_edges(self, ensemble_probs, market_prices, min_edge=0.05):
        """Find markets where ensemble disagrees with market by > min_edge."""
        edges = []
        for i, (prob, price) in enumerate(zip(ensemble_probs, market_prices)):
            edge = prob - price
            if abs(edge) >= min_edge:
                edges.append({
                    "bucket_idx": i,
                    "fair_value": prob,
                    "market_price": price,
                    "edge": edge,
                    "direction": "BUY" if edge > 0 else "SELL",
                    "kelly_fraction": self._kelly(prob, price),
                })
        return edges

    def _kelly(self, p, market_price):
        """Half-Kelly for binary outcome."""
        if market_price <= 0 or market_price >= 1:
            return 0
        b = (1 / market_price) - 1  # odds
        q = 1 - p
        f = (p * b - q) / b
        return max(0, f * 0.25)  # Quarter Kelly for safety
```

---

## 7. Backtesting & Validation

### Data Sources for Backtesting

1. **Historical NWP forecasts**: NOAA NOMADS archives (GFS, HRRR, NAM back to 2014+)
2. **Historical observations**: IEM ASOS (Iowa Environmental Mesonet) — free, comprehensive
3. **Historical market prices**: Polymarket API historical data, Kalshi historical trades
4. **ERA5 reanalysis**: ECMWF's gold-standard historical weather dataset (1940-present)

### Key Metrics

| Metric | Target | Description |
|--------|--------|-------------|
| **Brier Score** | < 0.15 | Calibration of probability forecasts (lower = better) |
| **Log Loss** | < 0.40 | Information-theoretic accuracy |
| **Calibration** | Within 5% | Predicted 40% should happen ~40% of the time |
| **Edge per Trade** | > 3% | Average deviation between fair value and fill price |
| **Win Rate** | > 55% | Percentage of profitable trades |
| **Sharpe Ratio** | > 1.5 | Risk-adjusted return |
| **Max Drawdown** | < 20% | Worst peak-to-trough loss |

### Backtesting Approach

```python
# Pseudo-code for weather strategy backtest
for date in historical_dates:
    for city in cities:
        # 1. Get historical NWP forecasts for that date
        forecasts = get_archived_forecasts(city, date)

        # 2. Calculate ensemble probabilities
        probs = engine.calculate_bucket_probabilities(forecasts, buckets)

        # 3. Get historical market prices (if available) or use as reference
        market_prices = get_historical_market_prices(city, date)

        # 4. Simulate trades
        edges = engine.find_edges(probs, market_prices)
        for edge in edges:
            execute_paper_trade(edge)

        # 5. Get actual outcome
        actual_high = get_historical_observation(city, date)

        # 6. Calculate P&L
        settle_trades(actual_high)
```

---

## 8. Risk Factors & Pitfalls

### Market Structure Risks
- **Cheap contract trap**: Contracts under 10¢ lose 60%+ of invested money on average (Kalshi analysis by Chris Dodds). The fee structure destroys edge on low-probability bets.
- **Liquidity risk**: Many cities have thin order books. Moving $100+ can shift the market 5-10%.
- **Adverse selection**: Bots with faster data access fill your limit orders when data changes (DSM bot, OMO bot).
- **Resolution edge cases**: Celsius/Fahrenheit rounding, station equipment failures, missing data.

### Model Risks
- **Model error correlation**: All NWP models share similar physics — they fail together in extreme weather.
- **Regime changes**: Models perform differently in different seasons and weather patterns.
- **Overfitting**: Backtested edge may not persist out-of-sample.
- **Stale data**: Using old model runs when fresh data is available = trading against yourself.

### Operational Risks
- **API downtime**: Both Polymarket and Kalshi CLOB can go down.
- **Rate limits**: Kalshi rate-limits API calls; Polymarket WebSocket requires heartbeats.
- **Key management**: Polymarket requires crypto private keys; Kalshi requires RSA keys.
- **Regulatory**: Arizona criminal charges against Kalshi (March 2026). Polymarket bans US users.

### Capital Efficiency
- **Chris Dodds' real results**: "A few bucks a week on a $50 bankroll" with a weather bot on Kalshi.
- **Polyforecast**: Profitable with 5-model ensemble approach, but modest returns relative to capital.
- **Scaling issue**: Weather markets are inherently low-liquidity. Can't deploy $1M+ into weather alone.
- **Best use of capital**: Kalshi 4% APY on idle capital means you earn yield while waiting for trades.

---

## 9. Competitive Landscape

### Known Weather Trading Operations

1. **Polyforecast** (polyforecast.io)
   - 5-model ensemble: GFS, ECMWF, ECMWF-AI, ICON, GEM
   - Trades on Polymarket, shares picks via email
   - Full transparency with on-chain verified trade history
   - Free service (seems to be marketing/community building)

2. **Degen Doppler**
   - Weather trading signal service
   - Less transparent than Polyforecast

3. **"240" Market Maker**
   - Unnamed entity providing consistent liquidity
   - 240-contract orders, ~2¢ spreads
   - Likely the most profitable weather participant

4. **wethr.net Community**
   - Educational resource for weather trading
   - City-specific data release schedules
   - Bot identification and defense strategies

### Open Source Weather Trading Bots (GitHub)

| Repository | Description | Results |
|------------|-------------|---------|
| [suislanchez/polymarket-kalshi-weather-bot](https://github.com/suislanchez/polymarket-kalshi-weather-bot) | GFS ensemble weather bot | $1.8K reported profit |
| [solship/Polymarket-Weather-Trading-Bot](https://github.com/solship/Polymarket-Weather-Trading-Bot) | NWS forecast weather bot | — |
| [ryanfrigo/kalshi-ai-trading-bot](https://github.com/ryanfrigo/kalshi-ai-trading-bot) | AI-powered Kalshi bot (Grok integration) | Educational |
| [OctagonAI/kalshi-deep-trading-bot](https://github.com/OctagonAI/kalshi-deep-trading-bot) | Deep Research + OpenAI for Kalshi | — |
| [IntelIP/Neural](https://github.com/IntelIP/Neural) | Algo trading platform for Kalshi | — |
| [taetaehoho/poly-kalshi-arb](https://github.com/taetaehoho/poly-kalshi-arb) | Cross-platform arbitrage bot | — |
| [dylanpersonguy/Fully-Autonomous-Polymarket-AI-Trading-Bot](https://github.com/dylanpersonguy/Fully-Autonomous-Polymarket-AI-Trading-Bot) | Multi-LLM ensemble bot | 17 stars |

### Platform SDKs & Tools

| Tool | Platform | Language | Link |
|------|----------|----------|------|
| py-clob-client | Polymarket | Python | PyPI (official) |
| @polymarket/clob-client | Polymarket | TypeScript | npm (official) |
| polyfill-rs | Polymarket | Rust | github.com/floor-licker/polyfill-rs (fastest) |
| rs-clob-client | Polymarket | Rust | github.com/Polymarket/rs-clob-client (official) |
| Polymarket Agents | Polymarket | Python | github.com/Polymarket/agents (AI framework) |
| kalshi-python-sync | Kalshi | Python | PyPI (official) |
| kalshi-python-async | Kalshi | Python | PyPI (official) |
| kalshi-typescript | Kalshi | TypeScript | npm (official) |
| kalshi-rs | Kalshi | Rust | crates.io (community) |
| NautilusTrader | Polymarket | Python | nautilustrader.io (institutional) |
| Herbie | NWP Data | Python | herbie.readthedocs.io |
| Open-Meteo | Weather API | REST | open-meteo.com |

### Weather Trading Community & Signal Services

| Service | Description | Cost |
|---------|-------------|------|
| [wethr.net](https://wethr.net) | Education, city schedules, bot identification, analytics | $0-99/mo |
| [Polyforecast](https://polyforecast.io) | 5-model ensemble daily signals | Free |
| [Degen Doppler](https://degendoppler.com) | 14-model ensemble, confidence tiers (LOCK/STRONG/SAFE) | — |
| [BettingOnWeather.com](https://bettingonweather.com) | Beginner guides for Polymarket/Kalshi weather | Free |

### Key Blog Posts & Research

- ["People Are Making Millions on Polymarket Betting on the Weather" (Medium, Jan 2026)](https://ezzekielnjuguna.medium.com/) — meropi and 1pixel wallet analysis
- ["Found the Weather Trading Bots Quietly Making $24,000" (Dev Genius, Feb 2026)](https://blog.devgenius.io/) — Step-by-step bot build
- "The Microstructure of Wealth Transfer in Prediction Markets" (Becker 2025) — 72.1M trades, makers +1.29%
- "Unravelling the Probabilistic Forest" (AFT 2025) — $40M arbitrage extracted from Polymarket
- [Chris Dodds — Kalshi Casino Analysis](https://chrisdodds.net/blog/2026-02-19-kalshi-prediction-markets-casino/) — Real bot results, fee analysis
- [Financial Markets Value Skillful Forecasts (Nature Comms)](https://link.springer.com/article/10.1038/s41467-024-48420-z)

---

## 10. What You Already Have (Existing Codebase)

**You already have a mature 4,911-line Polymarket weather trading system** in `syndicate/polymarket/`:

| Component | Files | Status |
|-----------|-------|--------|
| **Oracle** (`oracle.py`) | Orchestrator: discover → forecast → analyze → trade → resolve | Built, paper trading |
| **Market Discovery** (`data/gamma_client.py`) | Polymarket Gamma API integration | Built |
| **Ensemble Forecasts** (`data/open_meteo.py`) | GFS + ECMWF IFS + ECMWF AIFS + ICON = **173 ensemble members** | Built |
| **Resolution Verification** (`data/wunderground.py`) | Weather Underground scraper | Built |
| **EMOS Calibration** (`forecast/emos.py`) | Gneiting et al. 2005, CRPS-optimized bias/spread correction | Built |
| **Bias Correction** (`forecast/bias_correction.py`) | Per-city per-model bias tracking | Built |
| **Model Weighting** (`forecast/model_weighting.py`) | Per-model accuracy-based dynamic weights | Built |
| **Probability Engine** (`forecast/probability.py`) | Member counting → bin probability distribution (1% floor) | Built |
| **WU Alignment** (`forecast/wunderground_alignment.py`) | Alignment testing between forecasts & resolution source | Built |
| **Edge Detection** (`markets/edge.py`) | model_prob > market_price + threshold | Built |
| **Position Sizing** (`markets/sizing.py`) | Quarter-Kelly, 25% max per city, 30% daily cap | Built |
| **Scan Timing** (`markets/timing.py`) | Follows NWP model release schedule | Built |
| **Laddering** (`markets/laddering.py`) | Spreads bets across adjacent bins | Built |
| **Paper Trader** (`execution/paper_trader.py`) | Virtual USDC portfolio, daily loss limits, loss streak tracking | Built |
| **Resolution Tracker** (`resolution/tracker.py`) | Forecast-vs-actual Brier score, MAE, calibration | Built |
| **26 Cities** (`constants.py`) | ICAO station mappings, edge thresholds, Kelly limits | Built |
| **API Routes** (`routes.py`) | /status, /markets endpoints | Built |

**Edge thresholds already tuned**: 8% (<24h), 12% (25-48h), 15% (49-72h), skip >72h
**Kelly limits already set**: 0.25 fractional, $10K default bankroll, $5 min / $2.5K max bet

### What's Missing (To Go Live)

1. **Live CLOB Execution** — paper trader only, no actual `py-clob-client` order placement
2. **Wallet/Key Management** — no private key handling, no USDC.e approvals, no gas estimation
3. **Market Making** — no bid/ask quoting, no cancel/replace cycles, no inventory management
4. **WebSocket Integration** — no real-time order book streaming (currently polls)
5. **Kalshi Integration** — no Kalshi API at all (only Polymarket)
6. **Cross-Platform Arb** — no Wunderground-vs-NWS resolution discrepancy exploitation
7. **Real-Time Dashboard** — API routes exist but no frontend page

### Recommended Next Steps (Minimal Path to Live)

**Phase 1: Live Execution on Polymarket (1-2 weeks)**
1. Add `py-clob-client` integration to paper_trader.py → real_trader.py
2. Implement wallet management (private key, USDC.e approvals for neg-risk contracts)
3. Add WebSocket subscription for real-time order book updates
4. Start with $500 on NYC + London only (highest liquidity)

**Phase 2: Market Making Mode (2-3 weeks)**
1. Add bid/ask quoting around ensemble fair value
2. Implement cancel/replace cycles (target <200ms)
3. Add inventory skew (shift quotes to flatten exposure)
4. Widen spreads during DSM release windows

**Phase 3: Cross-Platform & Kalshi (3-4 weeks)**
1. Add Kalshi API integration (RSA-PSS auth, order placement)
2. Build Wunderground-vs-NWS resolution discrepancy detector
3. Implement cross-platform arbitrage when same event is mispriced

**Phase 4: Scale & Optimize**
1. Expand to all 26 cities
2. Add HRRR (hourly updates) for same-day accuracy boost
3. Add DSM/OMO data release sniping
4. Target $5K-$25K deployed capital

### Estimated Capital Requirements
- **Minimum viable**: $500 (enough for 5-10 simultaneous positions)
- **Comfortable**: $5,000 (can market-make across 5 cities)
- **Serious operation**: $25,000+ (all cities, both platforms)
- **Expected return**: 15-40% annualized (based on Polyforecast-style approach)
- **Plus**: 4% risk-free yield on Kalshi idle capital

---

## 11. Advanced Market Making: Avellaneda-Stoikov Adaptation for Weather Markets

### The Core Model

The Avellaneda-Stoikov (AS) model is the gold standard for automated market making. It derives optimal bid and ask quotes by balancing expected profit against inventory risk. The key insight: your reservation price (where you'd be indifferent to trading) shifts based on your inventory position.

**Optimal Reservation Price:**
```
r(s, q, t) = s - q * gamma * sigma^2 * (T - t)
where:
  s = current fair value (from your ensemble model)
  q = current inventory (positive = long, negative = short)
  gamma = risk aversion parameter (higher = wider quotes when inventory builds)
  sigma = price volatility
  T = time to settlement
  t = current time
```

**Optimal Spread:**
```
delta = gamma * sigma^2 * (T - t) + (2/gamma) * ln(1 + gamma/kappa)
where:
  kappa = order arrival rate parameter (higher kappa = denser order book = tighter spreads)
```

**Bid and Ask:**
```
bid = reservation_price - delta/2
ask = reservation_price + delta/2
```

### Weather Market Adaptations

Standard AS assumes continuous price movement. Weather markets have critical differences:

1. **Binary settlement**: Price converges to 0 or 1. As settlement approaches, gamma explodes. The model must reduce position size by `sqrt(T_remaining / T_initial)` -- cut exposure ~65% in the final settlement week.

2. **Event-driven jumps**: When DSM/METAR data releases occur, prices can gap 20-40 cents. Widen spreads by 3-5x during known data release windows. Pull quotes entirely 30 seconds before and after DSM release times.

3. **Discrete price levels**: Polymarket tick size is $0.001, Kalshi is $0.01. Spread cannot be narrower than 2 ticks. At the minimum spread, your entire edge is the fair value advantage of your model.

4. **Correlated inventory**: Temperature buckets within a city are perfectly negatively correlated (they sum to 100%). Buying YES on "52-53F" is equivalent to selling NO on all other buckets. Track net directional exposure, not per-bucket inventory.

5. **Multi-bucket quoting**: For 7-11 temperature buckets per city, you're effectively market-making a portfolio. Focus liquidity on the 2-3 buckets where your model has highest edge and the market has deepest liquidity. Don't quote buckets below $0.05 or above $0.95 (insufficient spread opportunity).

### Practical Parameters for Weather Market Making

| Parameter | Liquid Market (NYC, London) | Thin Market (Denver, Austin) |
|-----------|---------------------------|------------------------------|
| **Min Spread** | 2-3 cents | 5-8 cents |
| **Max Inventory** | 500 contracts/bucket | 100 contracts/bucket |
| **Risk Aversion (gamma)** | 0.1 | 0.3 |
| **Quote Refresh** | Every model update + every 5 min | Every model update + every 15 min |
| **DSM Blackout Window** | Pull quotes +/-60 seconds | Pull quotes +/-120 seconds |
| **Terminal Reduction** | Start at T-6 hours | Start at T-3 hours |

### Cancel/Replace Cycle

Professional market makers on Polymarket target sub-200ms cancel/replace latency:

1. Detect model update or order fill (WebSocket event)
2. Recalculate fair value and optimal quotes (<50ms)
3. Cancel all existing orders (batch cancel via API)
4. Post new orders (batch of up to 15 orders)
5. Total loop target: <200ms

The 500ms stale order buffer removal means if your loop takes >200ms, you face adverse selection from faster bots filling your stale quotes.

---

## 12. CME Weather Derivatives and Prediction Market Arbitrage

### The CME Weather Market

CME Group lists weather derivative contracts for 24 US cities, 11 in Europe, 6 in Canada, 3 in Australia, and 3 in Japan. These are primarily:

- **HDD Futures**: Heating Degree Days = max(65F - T_avg, 0). Monthly and seasonal contracts.
- **CDD Futures**: Cooling Degree Days = max(T_avg - 65F, 0). Monthly and seasonal contracts.
- **Tick Value**: $20 per degree day (US cities), $2,500-$5,000 per degree day (standard)

CME weather derivative volume surged from ~11,500 contracts/month average (2021-2022) to 42,052/month in 2023, settling around 20,660/month in 2024.

### Pricing Weather Derivatives

The standard approach uses an **Ornstein-Uhlenbeck mean-reverting process**:
```
dT_t = [dT_bar_t/dt + kappa * (T_bar_t - T_t)] * dt + sigma_t * dW_t
where:
  T_t = daily average temperature
  T_bar_t = seasonal trend (Fourier series: T_trend + alpha * sin(omega*t + theta))
  kappa = mean-reversion speed (~0.44 for typical US cities)
  sigma_t = time-varying volatility (B-spline interpolation across seasons)
```

Derivative prices are computed via Monte Carlo simulation of the temperature process, then summing degree-day accumulations and discounting.

### Cross-Market Arbitrage Opportunity

A structural arbitrage exists between CME weather derivatives and Kalshi/Polymarket daily temperature contracts:

**The logic**: If you know the daily high temperature distribution for a month, you can calculate expected HDD/CDD. If the CME monthly HDD/CDD futures are mispriced relative to your daily temperature model, you can:

1. Trade the daily temperature contracts on Kalshi/Polymarket (take the "correct" side)
2. Hedge with CME HDD/CDD futures (offset the temperature exposure)
3. Pocket the pricing discrepancy

**Practical challenges**:
- CME weather contracts have very thin liquidity (few market makers)
- Kalshi/Polymarket resolve daily; CME resolves monthly -- basis risk
- Different temperature metrics (daily high vs. daily average)
- Margin requirements on CME are substantial

### Interactive Brokers ForecastEx

Interactive Brokers launched ForecastEx, offering daily high temperature markets alongside CME-style weather contracts. This creates another potential arbitrage surface, as IB's ForecastEx may price events differently than Kalshi or Polymarket due to different participant bases.

ForecastEx also pays ~4% APY on contract value (similar to Kalshi), making it capital-efficient for longer-dated weather positions.

---

## 13. Advanced Risk Management for Weather Binary Portfolios

### Portfolio-Level Risk Framework

Weather prediction market portfolios face unique risk characteristics because binary contracts have discontinuous payoff functions.

#### Position Sizing: Kelly Criterion Deep Dive

**Full Kelly:**
```
f* = (p * b - q) / b
where:
  p = your estimated true probability
  q = 1 - p
  b = (1 - market_price) / market_price  (net odds)
```

**Worked example**: Market prices a bucket at $0.30. Your model says 42% probability.
- b = (1 - 0.30) / 0.30 = 2.333
- f* = (0.42 * 2.333 - 0.58) / 2.333 = (0.98 - 0.58) / 2.333 = 0.171

Full Kelly recommends 17.1% of bankroll. But **NEVER use full Kelly** in practice:

| Kelly Fraction | Expected Growth | Bankruptcy Risk |
|---------------|-----------------|-----------------|
| Full (1.0x) | Maximum | ~33% ruin risk |
| Half (0.5x) | 75% of max | ~10% ruin risk |
| Quarter (0.25x) | 50% of max | <3% ruin risk |

**Use quarter-Kelly (0.25x)** for weather trading. Your probability estimates are uncertain, and model errors are correlated across similar weather events.

#### Correlation Structure

Weather contracts exhibit complex correlation patterns:

1. **Intra-city, same-day**: Perfectly negatively correlated (buckets sum to 100%). Buying YES on one bucket implicitly sells all others.

2. **Cross-city, same-day**: Positively correlated when cities share weather systems. NYC and Philadelphia temperatures are highly correlated. NYC and LA are nearly independent.

3. **Same-city, cross-day**: Positively correlated (weather persistence). Tomorrow's high is correlated with today's.

4. **Cross-event type**: Temperature and precipitation can be correlated (rain often reduces high temperatures).

**Risk implication**: Don't treat each city as independent when sizing positions. If you're long "high temperature" across NYC, Philadelphia, and Boston on the same day, your effective exposure is ~1.5-2x what a single-city position would suggest, not 3x.

#### Max Exposure Rules

```
Per-market (single bucket):  max(5% of bankroll)
Per-city (all buckets):      max(25% of bankroll)
Per-day (all cities):        max(50% of bankroll)
Correlated city cluster:     max(35% of bankroll)
Daily loss limit:            max(10% of bankroll) -> stop all trading
```

#### Terminal Risk Management

As settlement approaches, binary option gamma increases toward infinity. The position's P&L becomes extremely sensitive to small price changes. Professional traders follow this scaling:

```
hours_to_settle = (settlement_time - current_time).hours
if hours_to_settle < 6:
    max_position *= 0.5
if hours_to_settle < 2:
    max_position *= 0.25
if hours_to_settle < 0.5:
    close_all_positions()  # or set very tight stop losses
```

#### Binary Option Greeks for Weather Contracts

Unlike traditional options, prediction market Greeks behave differently:

- **Delta**: Probability sensitivity. For a contract at 50 cents, delta = 1 (maximum sensitivity). At 10 cents or 90 cents, delta approaches 0.
- **Gamma**: Always negative for the market maker. Increases dramatically near settlement. This is why market makers MUST reduce positions as resolution approaches.
- **Theta**: Time decay is non-linear. Contracts far from 50 cents decay slowly; contracts near 50 cents can experience rapid value changes.
- **Vega (belief volatility)**: Sensitivity to changes in information uncertainty. High before data releases, low afterward.

The paper "Toward Black-Scholes for Prediction Markets" (arXiv 2510.15205) develops a formal framework with logit jump-diffusion model where belief-volatility, jump intensity, correlation across events, and co-jump structure are tradable risk factors.

#### Hedging Strategies

1. **Cross-bucket hedge**: If you're long the "52-53F" bucket, buy small positions in adjacent buckets ("50-51F", "54-55F") to reduce binary risk. This turns a binary bet into a wider distribution bet.

2. **Cross-city hedge**: If long high-temp in NYC, consider shorting high-temp in a correlated city where your model is less confident. Reduces weather system exposure.

3. **Cross-platform hedge**: Buy YES on Polymarket, buy NO on Kalshi for the same event when combined cost < $1.00 (structural arbitrage). Even when not pure arbitrage, it reduces single-platform risk.

4. **Time-based hedge**: If long a 3-day-out contract, you can partially hedge with same-city next-day contracts once that forecast firms up.

---

## 14. Extended Backtesting Framework

### Historical Data Sources (Detailed)

| Source | Data Type | Coverage | Access | Cost |
|--------|-----------|----------|--------|------|
| **Open-Meteo Historical Forecast API** | Archived NWP forecasts | 2021+ (model dependent) | REST API | Free (non-commercial) |
| **Open-Meteo Previous Runs API** | Forecast vs. actual comparison | 2024+ | REST API | Free |
| **Open-Meteo Ensemble API** | Multi-model ensemble data (18 models, 200+ members) | Current + recent | REST API | Free |
| **NOAA NOMADS** | GFS/HRRR/NAM archives | 2014+ (2 years online) | THREDDS/GRIB | Free |
| **IEM ASOS** | 1-minute airport observations | 2000+ | Download portal | Free |
| **IEM ASOS 5-minute** | Standard METAR observations | 1940s+ | Download portal | Free |
| **ECMWF ERA5** | Reanalysis (gold standard history) | 1940-present | CDS API | Free |
| **NOAA Climate Normals** | 30-year average temperatures | 1991-2020 | Download | Free |
| **GribStream** | Historical NWP with fast API | Multi-year archive | REST API | Paid |
| **Polymarket API** | Historical trade/price data | 2021+ | REST API | Free |
| **Kalshi Historical** | Trade and settlement data | 2021+ | REST/Download | Free |

### Open-Meteo Ensemble API: Complete Model Coverage

| Model | Region | Resolution | Members | Forecast Range | Update Freq |
|-------|--------|-----------|---------|----------------|-------------|
| GFS 0.25 | Global | 25 km | 31 | 10 days | Every 6h |
| GFS 0.5 | Global | 50 km | 31 | 35 days | Every 6h |
| ECMWF IFS | Global | 25 km | 51 | 15 days | Every 6h |
| ECMWF AIFS | Global | 25 km | 51 | 15 days | Every 6h |
| DWD ICON-EPS | Global | 26 km | 40 | 7.5 days | Every 12h |
| DWD ICON-EU-EPS | Europe | 13 km | 40 | 5 days | Every 6h |
| DWD ICON-D2-EPS | Central Europe | 2 km | 20 | 2 days | Every 3h |
| GEM | Global | 25 km | 21 | 16-39 days | Every 12h |
| BOM ACCESS-GE | Global | 40 km | 18 | 10 days | Every 6h |
| UK MOGREPS-G | Global | 20 km | 18 | 8 days | Every 6h |
| UK MOGREPS-UK | UK | 2 km | 3 | 5 days | Every hour |

Total accessible ensemble members: **300+** from 18 models across 7 national weather services.

### Backtesting Methodology

**Phase 1: Forecast Accuracy Validation**
Before backtesting any trading strategy, validate that your probability model beats climatology:

```python
# For each historical day, for each city:
# 1. Pull archived NWP forecasts from Open-Meteo Historical Forecast API
# 2. Generate bucket probabilities using your ensemble engine
# 3. Compare against actual outcomes (IEM ASOS observations)
# 4. Calculate metrics:

brier_score = mean((forecast_prob - actual_outcome)**2)  # lower = better
log_loss = -mean(actual * log(forecast) + (1-actual) * log(1-forecast))
calibration = plot(predicted_prob_bins vs actual_frequency)

# Target: Brier score < 0.15, calibration within 5%
# Benchmark: Kalshi markets achieve BSS of 0.37-0.51
# State of the art 12-hour rain forecast: Brier 0.05-0.12
```

**Phase 2: Signal Quality Assessment**
```python
# For each historical day where you would have traded:
# 1. Calculate edge = model_prob - market_price
# 2. Track: did the "edge" side actually win?

edge_accuracy = wins / total_trades_with_edge
avg_edge_when_correct = mean(edge | correct)
avg_edge_when_wrong = mean(edge | wrong)

# A good model: edge_accuracy > 55%, avg_edge_correct > avg_edge_wrong
```

**Phase 3: Order Book Simulation**

Simulating order book dynamics is the hardest part of backtesting prediction markets:

1. **Naive approach**: Assume you can always fill at the current mid-price. Overestimates returns by 30-50%.

2. **Better approach**: Use historical bid-ask spreads. Fill at bid when selling, at ask when buying. Account for your own market impact.

3. **Best approach**: Replay actual order book snapshots (if available from Polymarket WebSocket recordings or NautilusTrader's PolymarketDataLoader). Use pessimistic fill assumptions -- assume you're always the last to fill.

4. **Market impact model**: For prediction markets, linear slippage approximation works:
   ```
   slippage = order_size / (2 * book_depth_at_level)
   effective_price = mid_price + slippage * direction
   ```

5. **hftbacktest framework**: The open-source hftbacktest library supports market making backtests with order book replay and pessimistic exchange matching rules via its SimBook implementation.

**Phase 4: Strategy P&L Simulation**
```python
for date in backtest_period:
    for city in cities:
        # Morning: generate forecasts, calculate fair values
        forecasts = get_archived_forecasts(city, date)
        fair_values = ensemble_engine.calculate_probabilities(forecasts, buckets)

        # Throughout day: simulate trading at each model update
        for update_time in model_update_schedule:
            new_forecasts = get_archived_forecasts(city, date, run_time=update_time)
            new_fair_values = ensemble_engine.calculate_probabilities(new_forecasts, buckets)

            edges = find_edges(new_fair_values, simulated_market_prices)
            for edge in edges:
                size = kelly_size(edge, bankroll, existing_positions)
                fill_price = simulate_fill(edge.direction, simulated_orderbook)
                execute_trade(edge, size, fill_price)

        # Settlement: resolve all positions
        actual_temp = get_historical_observation(city, date)
        winning_bucket = determine_bucket(actual_temp, bucket_ranges)
        daily_pnl = settle_all_positions(winning_bucket)

        # Track metrics
        update_brier_scores(fair_values, winning_bucket)
        update_pnl_curve(daily_pnl)
        update_drawdown_tracker(daily_pnl)
```

### Performance Evaluation Metrics

| Metric | Good | Excellent | Description |
|--------|------|-----------|-------------|
| **Brier Score** | < 0.15 | < 0.10 | Probability calibration quality |
| **Log Loss** | < 0.40 | < 0.25 | Information-theoretic forecast accuracy |
| **Win Rate** | > 52% | > 58% | Fraction of profitable trades |
| **Average Edge** | > 3% | > 7% | Mean model_prob - market_price on trades taken |
| **Sharpe Ratio** | > 1.5 | > 2.5 | Risk-adjusted return (daily) |
| **Max Drawdown** | < 20% | < 10% | Worst peak-to-trough |
| **Recovery Time** | < 14 days | < 7 days | Time to recover from max drawdown |
| **Profit Factor** | > 1.3 | > 1.8 | Gross profit / gross loss |
| **Trade Frequency** | > 5/day | > 20/day | Enough trades for statistical significance |

---

## 15. Extended Open Source Ecosystem

### Additional Tools & Infrastructure

| Tool | Type | Description | URL |
|------|------|-------------|-----|
| **NautilusTrader** | Framework | Production-grade Rust-native trading engine with Polymarket integration. Supports backtesting with historical order book replay via PolymarketDataLoader. | [nautilustrader.io](https://nautilustrader.io) |
| **PredictOS** | Framework | Open-source AI-powered prediction market OS. MIT License. Includes Polymarket 15-min arb bot. | [github.com/PredictionXBT/PredictOS](https://github.com/PredictionXBT/PredictOS) |
| **OctoBot Prediction Market** | Bot | Open-source copy trading + arbitrage bot for Polymarket. | [github.com/Drakkar-Software/OctoBot-Prediction-Market](https://github.com/Drakkar-Software/OctoBot-Prediction-Market) |
| **Poly-Maker** | Market Making | Automated market maker for Polymarket. Google Sheets config. Warning: "not profitable in today's market." | [github.com/warproxxx/poly-maker](https://github.com/warproxxx/poly-maker) |
| **EventArb** | Arbitrage | Real-time cross-platform arbitrage scanner (Kalshi, Polymarket, Robinhood, IB). | [eventarb.com](https://www.eventarb.com) |
| **Oddpool** | Analytics | "Bloomberg for prediction markets." Cross-venue aggregation, arbitrage detection. | [oddpool.com](https://oddpool.com) |
| **PolyRouter** | API | Normalized API across Kalshi, Polymarket, Limitless. | github |
| **Dome** | API | Unified SDKs for prediction market data. | github |
| **PMXT** | API | Open-source prediction market API. | [github.com/qoery-com/pmxt](https://github.com/qoery-com/pmxt) |
| **pykalshi** | SDK | Unofficial Python client with WebSocket streaming, auto-retry, domain objects. | [github.com/ArshKA/kalshi-client](https://github.com/ArshKA/kalshi-client) |
| **openmeteo-requests** | SDK | Official Open-Meteo Python SDK using FlatBuffers for efficient data transfer. | [PyPI](https://pypi.org/project/openmeteo-requests/) |
| **hftbacktest** | Backtesting | High-frequency trading backtest framework with order book simulation and replay. | [hftbacktest.readthedocs.io](https://hftbacktest.readthedocs.io) |
| **Awesome-Prediction-Market-Tools** | Directory | 150+ tools curated list: bots, analytics, agents, arbitrage, APIs, alerts. | [github.com/aarora4/Awesome-Prediction-Market-Tools](https://github.com/aarora4/Awesome-Prediction-Market-Tools) |

### Prediction Market Ecosystem Scale (2025-2026)

- **Total notional volume**: >$44 billion across major platforms in 2025
- **Kalshi**: Captured >60% of total prediction market trading volume during peak 2025 periods
- **Bot dominance**: 14 of 20 most profitable Polymarket wallets are bots (Financial Magnates 2026)
- **AI agent penetration**: >30% of Polymarket wallets use AI agents (LayerHub analytics)
- **Arbitrage extraction**: ~$40 million extracted from Polymarket April 2024 - April 2025 ("Unravelling the Probabilistic Forest," AFT 2025)
- **Weather market microstructure**: Makers earn +1.29% per trade, takers lose -1.29% (Becker 2025, 72.1M trades)

---

## 16. Delta-Neutral and Correlated Weather Contract Strategies

### Cross-City Temperature Correlation

US cities cluster into correlated weather systems:

**Northeast Cluster** (high correlation): NYC, Philadelphia, Boston, Washington DC
- Share weather fronts, similar temperature movements
- Correlation coefficient: 0.85-0.95 for same-day highs

**Midwest Cluster**: Chicago, Detroit, Minneapolis
- Continental weather patterns
- Correlation: 0.80-0.90

**Southeast Cluster**: Miami, Tampa, Jacksonville, Atlanta
- Subtropical, but Atlanta diverges in winter
- Correlation: 0.70-0.85

**West Coast** (LOW cross-city correlation): LA, San Francisco, Seattle
- Microclimates dominate. LA and SF can differ by 20F+
- Correlation: 0.30-0.60

### Delta-Neutral Strategies

True delta-neutral trading in weather prediction markets is possible through:

1. **Intra-city bracket neutral**: Market-make across all buckets for a single city. Your net position should be near zero (sum of YES positions across all buckets approximates 100%). Profit comes from spread capture.

2. **Cross-city pair trading**: If NYC is priced at 70% for "above 55F" and Philadelphia at 60% for "above 54F", but your model says the correlation implies both should be ~65%, you can:
   - Buy Philadelphia "above 54F" at 60%
   - Sell NYC "above 55F" at 70%
   - Net temperature-direction exposure is reduced

3. **Temporal spread**: Buy today's resolution (high confidence), sell tomorrow's (uncertain). As your model firms up for tomorrow, the spread narrows. This is analogous to a calendar spread in options.

### Practical Limitation

Unlike traditional options, binary contracts cannot be continuously delta-hedged because there is no underlying asset with continuous price movement. "Hedging" is achieved through portfolio construction and diversification across loosely correlated events, not through dynamic position adjustment.

---

## 17. Key Takeaways

1. **The edge is real but modest**: Weather markets are inefficient because most participants use a single model or gut feel. A proper 5+ model ensemble with calibrated probabilities consistently finds 5-10% edges.

2. **Speed matters but isn't everything**: DSM/OMO sniping is competitive (other bots exist). Market making around fair value is more sustainable.

3. **NBM is your secret weapon for US markets**: NOAA's National Blend of Models already combines multiple NWP models with MOS corrections. Most market participants don't use it.

4. **AI weather models are the next frontier**: ECMWF AIFS (operational), Google GenCast (open source), and others are matching or beating traditional NWP. Incorporating these gives you an edge over traders using only traditional models.

5. **Cheap contracts are a trap**: Avoid buying sub-10¢ contracts. The math doesn't work after fees and adverse selection.

6. **Start with Kalshi for US, Polymarket for international**: Better regulatory footing + 4% yield on Kalshi. Better liquidity + more cities on Polymarket.

7. **The "240 bot" model is the winner**: Consistent market making with wide enough spreads to absorb adverse selection, tight enough to capture flow. This is the strategy to build toward.

---

## References & Resources

### Platform Documentation
- [Polymarket CLOB Documentation](https://docs.polymarket.com)
- [Polymarket WebSocket API (WSS Overview)](https://docs.polymarket.com/developers/CLOB/websocket/wss-overview)
- [Kalshi API Documentation](https://docs.kalshi.com)
- [Kalshi Weather Markets Help](https://help.kalshi.com/markets/popular-markets/weather-markets)
- [ForecastEx — Interactive Brokers Weather Markets](https://forecastex.com/insights/the-value-of-climate-prediction-markets)

### Weather Trading Education & Community
- [wethr.net Weather Trading Education](https://wethr.net)
- [wethr.net — NWS Data Guide](https://wethr.net/edu/nws-data-guide)
- [wethr.net — Market Bots Guide](https://wethr.net/edu/market-bots)
- [wethr.net — City Data Release Schedules](https://wethr.net/edu/city-resources)
- [Polyforecast](https://polyforecast.io) — Live weather trading signals
- [BettingOnWeather.com](https://www.bettingonweather.com) — Beginner guides
- [Chris Dodds — Kalshi Casino Analysis](https://chrisdodds.net/blog/2026-02-19-kalshi-prediction-markets-casino/)

### Weather Data APIs
- [Open-Meteo Ensemble API](https://open-meteo.com/en/docs/ensemble-api) — 18 models, 300+ ensemble members, free
- [Open-Meteo Historical Forecast API](https://open-meteo.com/en/docs/historical-forecast-api) — Archived forecasts for backtesting
- [Open-Meteo Previous Runs API](https://open-meteo.com/en/docs/previous-runs-api) — Forecast accuracy tracking
- [Open-Meteo GFS & HRRR API](https://open-meteo.com/en/docs/gfs-api)
- [Herbie Documentation](https://herbie.readthedocs.io) — Python NWP data access (15+ models)
- [Herbie GitHub](https://github.com/blaylockbk/Herbie)
- [IEM ASOS Data Download](https://mesonet.agron.iastate.edu/request/download.phtml)
- [IEM ASOS 1-Minute Data](https://mesonet.agron.iastate.edu/request/asos/1min.phtml)
- [NOAA NBM Dashboard](https://blend.mdl.nws.noaa.gov/nbm-dashboard)
- [NOAA HRRR](https://rapidrefresh.noaa.gov/hrrr/)
- [GribStream](https://gribstream.com/) — Fast historical NWP API (paid)

### SDKs & Libraries
- [py-clob-client (PyPI)](https://pypi.org/project/py-clob-client/) — Official Polymarket Python SDK
- [rs-clob-client (GitHub)](https://github.com/Polymarket/rs-clob-client) — Official Polymarket Rust SDK
- [kalshi-python (PyPI)](https://pypi.org/project/kalshi-python/) — Official Kalshi Python SDK
- [pykalshi (GitHub)](https://github.com/ArshKA/kalshi-client) — Unofficial Kalshi Python with WebSocket
- [openmeteo-requests (PyPI)](https://pypi.org/project/openmeteo-requests/) — Official Open-Meteo Python SDK
- [NautilusTrader — Polymarket Integration](https://nautilustrader.io/docs/latest/integrations/polymarket/)

### Open Source Bots
- [suislanchez/polymarket-kalshi-weather-bot](https://github.com/suislanchez/polymarket-kalshi-weather-bot) — GFS ensemble weather bot ($1.8K profit)
- [warproxxx/poly-maker](https://github.com/warproxxx/poly-maker) — Polymarket market maker (Google Sheets config)
- [Polymarket/agents](https://github.com/Polymarket/agents) — Official AI agent framework
- [PredictionXBT/PredictOS](https://github.com/PredictionXBT/PredictOS) — Open-source prediction market OS
- [Drakkar-Software/OctoBot-Prediction-Market](https://github.com/Drakkar-Software/OctoBot-Prediction-Market) — Copy trading + arbitrage
- [akshatgurbuxani/Kalshi-Weather-Forecasting-Financial-Trading](https://github.com/akshatgurbuxani/Kalshi-Weather-Forecasting-Financial-Trading) — XGBoost weather model for Kalshi
- [aarora4/Awesome-Prediction-Market-Tools](https://github.com/aarora4/Awesome-Prediction-Market-Tools) — Curated 150+ tool directory

### Arbitrage & Analytics Tools
- [EventArb](https://www.eventarb.com/) — Cross-platform arbitrage calculator
- [Oddpool](https://oddpool.com) — "Bloomberg for prediction markets"
- [Dune Analytics — Prediction Market Scanners](https://dune.com/the_liolik/99c)

### Academic Papers & Research
- [Toward Black-Scholes for Prediction Markets (arXiv 2510.15205)](https://arxiv.org/pdf/2510.15205) — Unified kernel pricing model
- [Google GenCast — Probabilistic Weather Forecasting (Nature)](https://www.nature.com/articles/s41586-024-08252-9)
- [Financial Markets Value Skillful Forecasts (Nature Comms)](https://link.springer.com/article/10.1038/s41467-024-48420-z)
- [Global Weather-Based Trading Strategies (J. Banking & Finance)](https://www.sciencedirect.com/science/article/abs/pii/S0378426622001546) — 15.2% annual return, Sharpe 0.46
- [A Practical Guide to Pricing Weather Derivatives (BSIC)](https://bsic.it/a-practical-guide-to-pricing-weather-derivatives/) — OU process, Monte Carlo
- [The Math of Prediction Markets (Substack)](https://navnoorbawa.substack.com/p/the-math-of-prediction-markets-binary) — Kelly, CLOB, pricing
- [Mathematical Execution Behind Prediction Market Alpha (Substack)](https://navnoorbawa.substack.com/p/the-mathematical-execution-behind) — Greeks, risk, microstructure
- [Calibration and Skill of Kalshi Prediction Markets](https://www.cwdatasolutions.com/post/calibration-and-skill-of-the-kalshi-prediction-markets) — BSS 0.37-0.51
- [ECMWF AIFS (Operational Feb 2025)](https://www.ecmwf.int/en/about/media-centre/news/2025/ecmwfs-ai-forecasts-become-operational)
- [Avellaneda-Stoikov Market Making (Hummingbot Guide)](https://hummingbot.org/blog/guide-to-the-avellaneda--stoikov-strategy/)
- [CME Weather Products](https://www.cmegroup.com/markets/weather.html)
- [How Weather Derivatives Hedge Against Nature (GARP)](https://www.garp.org/risk-intelligence/sustainability-climate/how-weather-derivatives-250220)

### News & Analysis
- [Prediction Markets Are Turning Into a Bot Playground (Financial Magnates)](https://www.financemagnates.com/trending/prediction-markets-are-turning-into-a-bot-playground/)
- [AI Agents Are Quietly Rewriting Prediction Market Trading (CoinDesk)](https://www.coindesk.com/tech/2026/03/15/ai-agents-are-quietly-rewriting-prediction-market-trading)
- [How Prediction Market Arbitrage Works (Trevor Lasn)](https://www.trevorlasn.com/blog/how-prediction-market-polymarket-kalshi-arbitrage-works)
- [Market Making in Prediction Markets (QuantVPS)](https://www.quantvps.com/blog/market-making-in-prediction-markets)
- [Prediction Market Making: Complete 2026 Guide](https://newyorkcityservers.com/blog/prediction-market-making-guide)
- [Advanced Prediction Market Trading Strategies (MetaMask)](https://metamask.io/news/advanced-prediction-market-trading-strategies)
- [NWS Climate Prediction Center](https://www.cpc.ncep.noaa.gov/)
- [QuantVPS Polymarket Latency Guide](https://www.quantvps.com/blog/polymarket-servers-location)
- [Interactive Brokers — Weather Prediction Markets](https://www.interactivebrokers.com/campus/traders-insight/ibkr-climate-energy/prediction-markets-might-already-be-the-best-source-for-todays-weather-forecast/)
