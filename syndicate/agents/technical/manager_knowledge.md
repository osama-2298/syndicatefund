# Technical Manager Knowledge Base
# Rules for synthesizing multi-timeframe technical signals into actionable output.

---

## 1. Elder's Triple Screen Method — Adapted for Crypto

### Core Principle
Higher timeframes set the bias. Lower timeframes provide entry timing. Never reverse this hierarchy.

### Override Rules
- **Daily (1D) overrides 4H**: If the daily is in a confirmed downtrend (lower highs, lower lows, price below 20 EMA), a 4H buy signal is a counter-trend bounce, NOT a reversal. Reduce its weight by 60%.
- **4H overrides 1H**: A 1H breakout against the 4H trend fails 70%+ of the time in crypto. Treat it as noise unless volume is 3x average AND the move reclaims a key 4H level.
- **Exception — climactic reversal**: If the daily shows a climactic volume spike (>5x 20-day average) with a long wick rejection at a major support/resistance, the daily trend may be reversing. In this case, allow the 4H to lead for the next 2-3 candles as confirmation.

### Screen Sequence
1. **Screen 1 (Daily)**: Determine trend direction and strength. Use 13/21 EMA slope + ADX > 25 for trend confirmation.
2. **Screen 2 (4H)**: Identify pullbacks within the daily trend. RSI 40-50 in uptrend or 50-60 in downtrend = healthy pullback zone.
3. **Screen 3 (1H)**: Time the entry. Use momentum oscillator crosses (MACD histogram flip, stochastic cross) in the direction of the daily trend.

---

## 2. Timeframe Alignment Scoring

### 3/3 Aligned (All Timeframes Agree)
- **Action**: Amplify conviction by 1.5x. This is the highest-probability setup.
- **Position sizing**: Full allocation warranted.
- **Stop placement**: Can use wider stops (below the 4H structure) since trend support is strong.
- **Example**: Daily uptrend + 4H pullback completing + 1H bullish engulfing = high-conviction long.

### 2/3 Aligned (Two Agree, One Disagrees)
- **Action**: Moderate conviction. Use standard allocation.
- **Which 2 matter more**: Daily + 4H agreement > Daily + 1H agreement > 4H + 1H agreement.
- **If the daily is the dissenter**: Reduce conviction to 0.5x. The daily being against you is a major headwind.
- **If the 1H is the dissenter**: Proceed with caution. The 1H may simply be lagging. Wait for the 1H to align before entry.

### Conflicting (All Disagree or No Clear Trend)
- **Action**: Reduce conviction to 0.25x or abstain entirely.
- **This is a no-trade zone** unless there is an extremely clear structural level being tested.
- **Chop detection**: If ATR is declining on the daily while the 1H ATR is expanding, the market is in a range. Fade the edges, do not chase breakouts.

---

## 3. Lower Timeframe Divergence: Noise vs Warning

### It Is Noise When:
- The divergence occurs in the middle of a strong daily trend (ADX > 30).
- Volume on the divergent move is below average.
- The divergence is on a single candle (1H) without follow-through in the next 2 candles.
- RSI divergence on the 1H while the 4H RSI is not yet overbought/oversold.

### It Is a Warning Signal When:
- The divergence appears on BOTH the 1H and 4H simultaneously.
- Volume confirms the divergence (declining volume on higher highs = bearish divergence).
- The divergence forms at a key daily level (prior support/resistance, round number, VWAP).
- Multiple oscillators diverge together (RSI + MACD + OBV all diverging).
- The divergence persists for 3+ candles on the 4H.

### Response Protocol
- **Noise**: Ignore. Maintain position. Do not adjust stops.
- **Warning**: Tighten stops to the 4H structure. Reduce position by 25%. Set an alert for daily confirmation.

---

## 4. Dow Theory Application to Crypto

### Primary Trend (Daily Chart)
- Defined by the sequence of higher highs/higher lows (bull) or lower highs/lower lows (bear).
- A primary trend change requires a daily close breaking the last significant swing. A wick does not count.
- In crypto, primary trends typically last 3-8 months (shorter than equities due to higher volatility).

### Secondary Trend (4H Chart)
- Corrections within the primary trend. Typically retrace 33-66% of the prior primary move.
- In crypto, secondary corrections are sharper and faster: expect 30-50% retracements in altcoins, 15-30% in BTC.
- A secondary trend becomes a primary trend change ONLY when the daily swing structure breaks.

### Short-Term Trend (1H Chart)
- Used exclusively for entry/exit timing, never for directional bias.
- Short-term trends in crypto last 6-48 hours. Beyond 48 hours, they are reclassified as secondary.

---

## 5. Volume-Price Relationships Across Timeframes

### Daily Volume Rules
- **Rising price + rising volume**: Trend is healthy. Maintain or add to position.
- **Rising price + declining volume**: Trend is weakening. Do not add. Tighten stops.
- **Falling price + rising volume**: Selling pressure is real. Respect the move. This is not "shaking out weak hands" — it is distribution.
- **Falling price + declining volume**: Selling exhaustion. Watch for a reversal setup on the 4H.

### 4H Volume Context
- Volume spikes on the 4H that are 3x+ average often mark intraday tops/bottoms. Use them as entry/exit timing signals.
- If 4H volume is consistently declining over 3+ days while price trends, expect a reversal within 24-48 hours.

### Crypto-Specific Volume Notes
- Exchange volume can be manipulated. Cross-reference spot volume with derivatives OI changes.
- Weekend volume is 30-50% lower. Breakouts on weekends are 40% more likely to fail. Require Monday confirmation.

---

## 6. Common False Signals by Timeframe

### Daily False Signals
- **Bear trap at round numbers**: BTC drops below a round number ($60K, $50K) on a Sunday/Monday, then reclaims it within 48 hours. Wait for a daily close below + retest as resistance.
- **Golden/Death cross lag**: Moving average crosses on the daily are lagging indicators. By the time the cross confirms, 60-70% of the move has already occurred. Use them for trend confirmation, not entry.

### 4H False Signals
- **Head-and-shoulders in an uptrend**: In a strong daily uptrend, 4H H&S patterns fail 55% of the time. Do not short them unless the daily trend is also weakening.
- **RSI overbought in a trend**: RSI can stay above 70 for days in crypto. Overbought is not a sell signal in a strong trend. Wait for bearish divergence.

### 1H False Signals
- **Breakout fakeouts**: 1H breakouts fail at a very high rate (60%+). Always require a retest of the breakout level. No retest, no entry.
- **MACD crosses in a range**: In a ranging market, 1H MACD crosses generate 5-10 false signals per day. Filter with the 4H trend.

---

## 7. Entry Timing Rules

### Never Enter Against the Daily Trend Unless:
1. A climactic reversal candle prints (>3x ATR, long wick, extreme volume).
2. The 4H shows structural change (break of the last swing high/low in the daily trend direction).
3. A major fundamental catalyst has occurred (exchange hack, regulatory event, protocol failure).
4. Price has reached a historically significant level (prior cycle high/low, 200-week MA).

If fewer than 2 of these conditions are met, do NOT counter-trend trade. Wait for the daily trend to shift.

### Entry Checklist (Trend-Following)
1. Daily trend confirmed (EMA slope + swing structure).
2. 4H pullback to a key level (EMA, Fibonacci, prior breakout).
3. 1H trigger candle in the trend direction (engulfing, pin bar, inside bar breakout).
4. Volume on the trigger candle is above average.
5. Risk/reward is at least 2:1 to the next 4H target.

---

## 8. Order Book and Derivatives in Multi-Timeframe Context

### Order Book Interpretation
- **Large bid walls in a daily uptrend**: Supportive. Smart money defending a level. Use as a stop-loss anchor.
- **Large bid walls in a daily downtrend**: Likely to be pulled (spoofing). Do not rely on them as support.
- **Ask walls being absorbed**: Bullish if the daily is trending up. Neutral if the daily is ranging.

### Derivatives Context
- **Funding rates > 0.1%**: Market is overleveraged long. A 1H dip is likely to cascade into a 4H correction. Reduce long exposure.
- **Funding rates < -0.05%**: Market is overleveraged short. Squeeze potential is high. Look for 1H bullish triggers.
- **Open Interest rising + price rising**: New money entering longs. Trend is supported. Bullish.
- **Open Interest rising + price falling**: New shorts entering. If this aligns with a daily downtrend, the move has legs. If it is against a daily uptrend, it is squeeze fuel.
- **Open Interest falling + price falling**: Long liquidation cascade. Watch for OI to stabilize as a reversal signal.

### Synthesis Rule
Order book and derivatives data are the highest-frequency inputs. They should confirm or warn about setups identified on the 1H and 4H. They should NEVER override a daily trend signal on their own. Weight them as 20% of the synthesis unless they show extreme readings (funding > 0.15% or < -0.1%), in which case increase to 35%.

---

## 9. Confidence Calibration Table

| Condition | Confidence Modifier |
|---|---|
| 3/3 timeframes aligned | +50% |
| 2/3 timeframes aligned (daily included) | +20% |
| 2/3 timeframes aligned (daily excluded) | -10% |
| All timeframes conflicting | -50% |
| Volume confirms across all timeframes | +30% |
| Volume diverges from price on daily | -40% |
| Funding rate extreme (>0.1% or <-0.05%) | Flag as risk, do not adjust conviction directionally |
| Weekend/low-liquidity period | -20% |
| Climactic volume reversal on daily | Override lower timeframes, reset analysis |

---

## 10. Synthesis Output Protocol

When producing the final technical signal:
1. State the daily bias first. Always.
2. State the 4H context (trending with daily, pulling back, or diverging).
3. State the 1H trigger status (triggered, pending, or invalid).
4. Assign alignment score (3/3, 2/3, conflicting).
5. Note any volume or derivatives anomalies.
6. Produce a single direction (LONG, SHORT, NEUTRAL) with conviction (0.0 to 1.0).
7. Include invalidation level — the price at which this signal is wrong.
