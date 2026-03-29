# Sentiment Manager Knowledge Base
# Rules for synthesizing multi-source sentiment signals into actionable output.

---

## 1. Source Reliability Hierarchy

### Tier 1: Smart Money Signals (Weight: 40-50%)
- Whale wallet movements (on-chain verified, not self-reported).
- Institutional fund flow data (Grayscale, ETF inflows/outflows).
- OTC desk activity indicators.
- Exchange reserve changes for top 100 wallets.
- **Rule**: Smart money data is the only sentiment source that can independently justify a trade signal. All other sources require corroboration.

### Tier 2: Market-Derived Sentiment (Weight: 30-35%)
- Funding rates across major exchanges.
- Options put/call ratio and skew.
- Liquidation heatmaps and cascades.
- Basis spread between spot and futures.
- **Rule**: Market-derived sentiment reflects actual capital at risk. It is more reliable than opinion-based sources but can be distorted by market-maker positioning.

### Tier 3: Social Media and Crowd Sentiment (Weight: 15-25%)
- Reddit engagement metrics (post volume, upvote velocity, comment sentiment).
- Crypto Twitter/X trending topics and influencer positioning.
- CoinGecko/CoinMarketCap trending and search volume.
- Fear & Greed Index.
- **Rule**: Social sentiment is a lagging and often contrarian indicator. Never use it as a primary signal. It confirms or warns — it does not lead.

### Weighting Adjustment Rules
- In low-volatility regimes, increase smart money weight to 50%. Crowd sentiment is meaningless in a range.
- In high-volatility regimes (daily ATR > 2x average), increase market-derived weight to 40%. Liquidation cascades drive price more than fundamentals.
- During major news events, temporarily elevate social media to 30% for the first 4-6 hours (it captures narrative velocity), then decay back to 15%.

---

## 2. Narrative Deduplication

### The Problem
Multiple sources often reflect the same underlying event. Counting them independently inflates sentiment artificially.

### Deduplication Rules
- **Reddit trending + CoinGecko trending + Twitter trending for the same token**: This is ONE signal, not three. The underlying event is the same (price move or news catalyst). Count it once with amplified conviction, not as three separate bullish/bearish signals.
- **News article spawns Reddit discussion spawns Twitter threads**: Trace to the origin. The news article is the signal. Reddit and Twitter are echoes. Weight the news, discard the echoes.
- **Multiple influencers posting about the same topic within 2 hours**: This is a coordinated narrative push or organic viral spread. Count as one signal. Check if it originated from a single source.
- **Exchange listing rumor on Reddit + exchange listing confirmation on Twitter**: These are two stages of ONE event. The confirmation supersedes the rumor. Replace, do not add.

### Amplification vs Duplication
- Deduplication removes false signal multiplication.
- AFTER deduplication, if a single event is reflected across all three tiers (smart money acting on it + market positioning shifting + social media discussing it), that IS meaningful amplification. The breadth of response matters, not the count of sources.

---

## 3. Contrarian Signal Rules

### When Extreme Fear IS a Buy Signal
- Fear & Greed Index below 15 AND smart money wallets are accumulating (net inflows to cold storage).
- Social media is overwhelmingly bearish AND funding rates are deeply negative (shorts overleveraged).
- Reddit daily discussion threads have <50% of normal engagement (capitulation — people stopped caring).
- **Key requirement**: Smart money MUST be accumulating. Fear without accumulation is justified fear.

### When Extreme Fear IS NOT a Buy Signal
- Smart money is distributing (moving to exchanges, not away from them).
- The fear is driven by a fundamental change (protocol hack, regulatory ban, stablecoin depeg) rather than price action.
- Institutional outflows are accelerating, not stabilizing.
- Leverage has not been flushed yet (open interest still elevated despite the drop).
- **Rule**: Fear is only contrarian when the smart money disagrees with the crowd. When smart money agrees with the fear, the fear is rational.

### When Extreme Greed IS a Sell Signal
- Fear & Greed Index above 85 for 3+ consecutive days.
- Funding rates above 0.1% sustained for 48+ hours.
- Reddit posts about "generational wealth" and "never selling" reach front page of crypto subreddits.
- Google Trends for "buy [token]" hits local maximum.
- **Key requirement**: Market-derived data must confirm euphoria. Social-only euphoria can persist for weeks before reversing.

### When Extreme Greed IS NOT a Sell Signal
- Early-to-mid bull market where smart money is still accumulating (cycle position matters enormously).
- Greed driven by genuine adoption metrics (new addresses, transaction volume, protocol revenue).
- Institutional inflows are accelerating alongside retail greed (wall of money still incoming).

---

## 4. Social Media Lag Rules

### Reddit Lag Profile
- Reddit sentiment trails price action by **12-24 hours** for major moves.
- For slow grinds (multi-day trends), Reddit sentiment aligns with a 1-2 day delay.
- **Implication**: If Reddit turns bearish today, the price move that caused it happened yesterday. Do NOT treat it as a leading indicator.
- **Exception**: Reddit is occasionally early on regulatory news and protocol-specific developments where community insiders post first.

### Twitter/X Lag Profile
- Crypto Twitter trails price by **2-6 hours** for well-known influencers.
- Breaking news accounts (e.g., whale alert bots, on-chain trackers) are near real-time.
- Influencer positioning posts often come AFTER the influencer has already entered the trade. Lag: 4-12 hours.

### CoinGecko/CoinMarketCap Trending
- Trailing indicator, 6-12 hours behind the initial price move that caused interest.
- By the time a token trends on CoinGecko, the first major move is typically 60-80% complete.
- **Rule**: Trending tokens on aggregator sites are useful for identifying WHAT is moving, not for timing entries.

### Using Lag Constructively
- If price drops 10% and Reddit has not turned bearish yet, expect the negative sentiment wave in 12-24 hours. This can cause a secondary dip. Plan accordingly.
- If price pumps 15% and Twitter is already euphoric within 2 hours, the move is well-known and likely crowded. Reduce entry size.

---

## 5. Sentiment-Price Divergence

### Bearish Divergence (Price Up, Sentiment Flat/Down)
- Price making new highs but social engagement is declining = distribution phase.
- Smart money selling into the rally while retail is not excited enough to buy = top forming.
- **Action**: This is one of the most reliable sentiment signals. Begin reducing exposure. Set trailing stops.
- **Timeline**: Bearish divergence typically resolves within 1-3 weeks with a sharp correction.

### Bullish Divergence (Price Down, Sentiment Improving)
- Price making new lows but smart money accumulating and social fear diminishing = accumulation phase.
- Funding rates normalizing during a downtrend = leverage flush complete.
- **Action**: Begin building a watchlist. Enter when technical triggers confirm on the 4H.
- **Timeline**: Bullish divergence can persist for weeks. Do not front-run it. Wait for price confirmation.

### False Divergence Identification
- Sentiment improving because of a single viral post (not organic) = false bullish divergence.
- Sentiment declining because of general market fatigue (not specific to the asset) = false bearish divergence.
- **Rule**: Divergence must be confirmed by at least TWO source tiers to be actionable.

---

## 6. Fear & Greed Index — Historical Patterns

### Key Thresholds (Historically Validated)
- **0-10 (Extreme Fear)**: Occurred during COVID crash, Luna/FTX collapse. Historically, buying here with a 6-month horizon has yielded 100%+ returns. But timing the exact bottom is impossible. Dollar-cost average in, do not lump sum.
- **10-25 (Fear)**: Common during bear market rallies. Not extreme enough for high-conviction contrarian trades. Watch, do not act on this alone.
- **25-45 (Moderate Fear/Neutral)**: No actionable signal. This is the "noise zone." Ignore the index entirely.
- **45-75 (Moderate Greed/Neutral)**: Also noise. Normal bull market readings.
- **75-90 (Greed)**: Begin monitoring for reversal signals. Not actionable alone — bull markets live here.
- **90-100 (Extreme Greed)**: Historically precedes corrections of 15-40% within 2-4 weeks. Only actionable when combined with smart money distribution and elevated funding rates.

### Cycle Context Matters
- In a bear market, F&G of 50 (neutral) is actually bullish — sentiment is recovering.
- In a bull market, F&G of 50 is actually bearish — sentiment is deteriorating.
- Always interpret the index relative to the current cycle phase, never in absolute terms.

---

## 7. Reddit Engagement as Reliability Indicator

### High Engagement (Reliable Signal)
- Daily discussion thread comments > 2x 30-day average.
- Post upvote velocity in the first hour > 90th percentile.
- Multiple unique users (not bots) making substantive comments.
- **When engagement is high**: The signal is representative of broad retail sentiment. It can be used for contrarian analysis.

### Low Engagement (Unreliable Signal)
- Daily discussion thread comments < 50% of 30-day average.
- Top posts are memes or recycled content.
- Few unique commenters.
- **When engagement is low**: The signal represents only the most active users (often biased, often wrong). Discount Reddit sentiment by 50%+.

### Bot and Manipulation Detection
- Sudden spike in new accounts pushing one narrative = coordinated campaign. Discard entirely.
- Identical or near-identical comments across subreddits = bot activity. Discard.
- A single post driving 80%+ of the day's sentiment shift = outlier, not signal. Discard.

---

## 8. Smart Money Divergence Interpretation

### Smart Money Buying While Crowd Is Fearful
- **Strongest possible buy signal** in the sentiment framework.
- Historically has preceded recoveries in 78% of cases (based on on-chain data analysis).
- **Action**: Issue a bullish sentiment signal with high conviction, even if technical and fundamental signals are neutral.
- **Caveat**: Verify smart money is accumulating the SAME asset being analyzed, not a different one. Whale BTC accumulation does not make altcoin X a buy.

### Smart Money Selling While Crowd Is Greedy
- **Strongest possible sell signal** in the sentiment framework.
- Distribution phases last 2-6 weeks. The crowd does not notice until the final sharp drop.
- **Action**: Issue a bearish sentiment signal. Emphasize urgency — the window to exit is closing.

### Smart Money and Crowd Agree
- **Both bullish**: Trend continuation likely. This is the "middle of the move" where everyone is right. Do not fight it. But watch for the divergence that signals the end.
- **Both bearish**: Capitulation or early bear. If price is near a major support, this may be the bottom. If price is in open air (no nearby support), more downside is likely.

### Smart Money Inactive While Crowd Is Active
- **Crowd bullish, smart money flat**: The rally is retail-driven and unlikely to sustain. Discount the bullish signal by 40%.
- **Crowd bearish, smart money flat**: The fear is likely overdone but there is no catalyst for reversal. Wait for smart money to act before issuing a signal.

---

## 9. Cross-Source Synthesis Protocol

### Step 1: Collect and Categorize
- Assign each incoming signal to its tier (Smart Money, Market-Derived, Social).
- Tag each signal with the asset, timestamp, and directional bias.

### Step 2: Deduplicate
- Apply narrative deduplication rules from Section 2.
- Merge overlapping signals into single events with amplified weight.

### Step 3: Check for Divergence
- Compare the directional bias across tiers.
- If all tiers agree: Strong signal. Proceed with high conviction.
- If Tier 1 disagrees with Tiers 2+3: Trust Tier 1. Smart money is usually right.
- If Tier 2 disagrees with Tiers 1+3: Flag as ambiguous. Market positioning may be distorted by market-makers.
- If Tier 3 disagrees with Tiers 1+2: Ignore Tier 3. Crowd is lagging.

### Step 4: Apply Contrarian Filters
- Check if the signal is at a sentiment extreme (F&G < 15 or > 85).
- If at an extreme, apply the contrarian rules from Section 3.

### Step 5: Produce Output
- Single direction: BULLISH, BEARISH, or NEUTRAL.
- Conviction: 0.0 to 1.0.
- Key driver: Which tier/source is driving the signal.
- Risk flag: Any divergence or manipulation concern.
- Time horizon: How long this sentiment signal is expected to persist.

---

## 10. Confidence Calibration Table

| Condition | Confidence Modifier |
|---|---|
| Smart money accumulating in fear | +50% |
| Smart money distributing in greed | +50% (for bearish signal) |
| All three tiers agree | +40% |
| Social-only signal (no smart money or market confirmation) | -50% |
| Signal at sentiment extreme (F&G < 15 or > 85) | +30% (contrarian direction) |
| Signal during low Reddit engagement | -30% |
| Narrative duplication detected (before dedup) | -40% |
| Smart money inactive, crowd-only signal | -40% |
| Market-derived confirms smart money | +35% |
| Breaking news event (first 4 hours) | Elevate social media temporarily, reassess after |
