# Detector Specs

Every detector: implements `Detector`, reads only `StockContext`, returns `list[Evidence]`,
never raises out (registry catches), never vetoes. Params live in config under
`detectors.params.<name>` (defaults below). All thresholds are the docs' values
where they existed; contradictions resolved here — this file is authoritative.

## swings — Swing Points
- Swing high: N candles each side with strictly lower highs (N = `strength`, default 3; `>=` disqualifies). Mirror for lows.
- Emits no Evidence itself (infrastructure detector): writes SWING_H/SWING_L Levels to LevelStore.
- Marks Level SWEPT when wick exceeds, RECLAIMED when close returns within same/next candle.

## structure — BOS / CHoCH
- Trend from swing sequence: HH+HL → bullish, LH+LL → bearish, else ranging.
- BOS = close beyond swing in trend direction (continuation). Evidence strength 0.6,
  direction = trend, ttl 12.
- CHoCH = close beyond opposite swing (potential reversal). Strength 0.8 when it follows
  a SWEPT level within 6 candles (trap chain), else 0.5. Direction = new direction, ttl 24.
- Fake-BOS memory: BOS that reverses within `fake_within=5` candles logs to meta and
  feeds timestats (inducement statistics).

## orderblock — Order Blocks
- Bullish OB: last bearish candle before displacement ≥ `displacement_atr=1.5` × ATR(14)
  within ≤3 candles. Mirror bearish.
- Quality: displacement/ATR (cap 0.4) + body/ATR (0.3) + body% cleanliness (0.3).
- **Mitigation rule (resolves docs conflict): first touch = TESTED, second touch = MITIGATED/dead.**
- Evidence when price inside unmitigated OB zone aligned with structure: strength = quality, ttl 6.
- Writes OB Levels; overlapping OBs keep highest quality.

## breaker — Breaker Blocks + inversion logic
- OB whose level transitions SWEPT (price traded through, closed beyond) then price
  reclaims → Level INVERTED → breaker: old support acts resistance and vice versa.
- Evidence on retest of inverted zone: strength 0.85 (highest single-concept weight —
  breaker after sweep is the trap-reversal signature), direction = post-inversion, ttl 12.

## fvg — FVG / iFVG / BPR / Consequent Encroachment
- FVG: 3-candle gap. Bullish: c3.low > c1.high, min size `min_gap_atr=0.3` × ATR.
- Fill tracking: CE = 50% of gap. Hold at CE = strength 0.7; full fill → Level DEAD.
- iFVG: FVG traded fully through then respected from opposite side → INVERTED, strength 0.75.
- BPR: overlap of opposing FVGs → single zone Evidence, strength 0.8, ttl 12.

## liquidity — Pools & Key Levels
- EQH/EQL: ≥2 touches within `tolerance=0.1%`. Strength = min(touches/5,1)×0.7 + recency×0.3 (48h decay).
- PDH/PDL/PWH/PWL from prev sessions; OPEN_RANGE from 09:15–09:30; ROUND nearest 50/100/500 within 2%.
- Emits proximity Evidence: untapped pool above/below within 1 ATR = draw-on-liquidity
  direction hint, strength = pool strength × 0.5, ttl 12. Writes all Levels.

## sweep — Liquidity Sweeps (trap trigger)
- Bullish sweep: wick below low-kind Level + close back above. Mirror bearish.
- Quality: +0.4 close correct side, +0.25 × pool strength, +0.2 ≥3 touches,
  +0.15 PDH/PDL/PWH/PWL kind. Speed bonus: reversal within ≤3 candles +0.1 (cap 1.0).
- Evidence direction = reversal direction, strength = quality, ttl 18.
- Transitions the swept Level → SWEPT, on reclaim → RECLAIMED (feeds breaker/template).

## wyckoff — Phase Classifier (pure data, no boxes)
- Range detect: last `window=40` M5 candles, (max-min) < `range_atr=3.0` × ATR ⇒ in-range.
- Events inside range, volume-based:
  - Climax: candle range > 2×ATR AND volume > 2× vol-SMA(20) at range extreme.
  - Absorption/Spring: sweep of range low + volume > 1.5× avg + close in upper half ⇒ spring (accumulation sign). Mirror upthrust (distribution).
  - Effort-vs-result: volume z-score > 1.5 with |close-open| < 0.3×ATR ⇒ absorption bar.
- Phase output: ACCUMULATION / DISTRIBUTION / MARKUP / MARKDOWN / UNCLEAR + confidence.
- Evidence: spring→LONG strength 0.8; upthrust→SHORT 0.8; phase-aligned continuation 0.5. ttl 24.
- Also exposes `htf_phase(D1)` used by RegimeVetoGate (weekly/daily markdown blocks longs).

## volume — VSA stats (support detector)
- Maintains vol-SMA(20), vol z-score, per-candle classification: no_demand (up candle,
  low vol), stopping_volume (down candle, huge vol, long lower wick), climax.
- Emits low-strength confirming Evidence (0.3) only when co-located with another
  detector's zone (checks evidence_history) — pure confluence booster.

## cage — Options Cage (requires options_chain; inert without)
- Inputs: OI per strike (CE/PE), ATM straddle price, max pain, futures basis + OI delta.
- Ceiling = max CE-OI strike above spot; floor = max PE-OI strike below; magnet = max pain.
- Evidence:
  - Price within 0.3% of wall + rejection candle ⇒ reversal Evidence strength 0.7.
  - OI-change matrix (15-min snapshots): price↑+OI↓ = short covering ⇒ fade Evidence 0.6.
  - Straddle-implied range consumed >90% ⇒ exhaustion Evidence 0.5.
- Writes OI_WALL Levels so sweep/breaker detectors compose with them automatically.

## compression — Compression Boxes / Coiled Energy (spec: 06 §5)
- Range contraction <0.6, body overlap, negative volume slope, NR7/inside clusters ⇒ box.
- Box registers as PO3 ACCUMULATION (06 §3). Never trade its breakout directly — trade
  failure (sweep-reclaim) or post-BOS retrace. Energy = box_height × 2.5 caps targets.
- Location on hunt-born OB/HTF FVG ⇒ Evidence 0.75 post-DISTRIBUTION, else 0.3 context.

## index — Index Context (spec: 05 axiom 11)
- Runs full structure/wyckoff stack on NIFTY (+BANKNIFTY for financials).
- Emits per-stock context Evidence: index phase + direction; confluence applies ×0.5
  haircut on entries against strong index move. D1 index markdown reinforces RegimeVetoGate.

## timestats — Learned Time Probabilities
- 5-min buckets (75/day). Counts per bucket: sweeps, reversals, fake-BOS, trap outcomes.
- Cold start priors from docs: 09:15–10:30 danger 0.8; 11:00–13:00 safe 0.3; 13:30–14:00 0.6; 14:45+ 0.8.
- Evidence: current bucket favorable for entry ⇒ strength = 1 - danger, NEUTRAL direction
  (confluence uses it as multiplier-style contribution).
- Persisted per stock; recalibrated by learn/calibrate.py. Docs' fixed-vs-learned conflict
  resolved: **priors fixed, data overrides as samples accumulate (Laplace smoothing).**

## Template Classifier (engine/template.py — not a detector, consumes Levels+Evidence)
- At each candle until locked (≤11:30): checks cage/PDH/PDL sweep states + reclaim + CHoCH
  presence + drive character (pullback depth, vol trend) → TRAP_REVERSAL / TREND /
  RANGE_PIN / DOUBLE_TRAP / UNCLASSIFIED.
- UNCLASSIFIED ⇒ TemplateGate blocks entries all day. Locked template + stats → journal.

## Scenario Ground-Truth Matrix (MockFeed must generate; tests assert)

| Scenario | Ground truth | Detectors that must fire | Must NOT fire |
|---|---|---|---|
| judas_reversal | morning dump, PDL sweep, V-up, afternoon rally | sweep, structure(CHoCH), breaker, wyckoff(spring) | trend-join |
| trend_day | gap-go, shallow pullbacks | structure(BOS), orderblock | sweep-reversal |
| range_pin | narrow chop, no edge sweep | liquidity(EQH/EQL) | breaker, sweep |
| double_trap | both edges swept, late breakdown | sweep×2, template DOUBLE_TRAP | early entry (gate) |
| stop_hunt_survive | entry, wick through stop, reclaim, target | manager wick-tolerance path | EXIT_STOP on wick |
| grind_markdown (HTF) | daily markdown context | RegimeVetoGate blocks longs | any long entry |
