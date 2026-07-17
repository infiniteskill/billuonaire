# Real-Month Study — 20 NIFTY Stocks × 19 Sessions (Jun 19 – Jul 16, 2026)

Data: free yfinance M1, 20 liquid NIFTY-50 names + NIFTY index, 143k minute bars, zero gaps.
Three replays: baseline (13 trades), sized (0 — costs_dominate), cost-corrected (pending).
Full evidence: autopsy tables in `.superpowers/sdd/` reports. This doc = conclusions for discussion.

## What the month actually was
- Day templates: 9 UNCLASSIFIED / 8 RANGE_PIN / 2 DOUBLE_TRAP / 0 TREND / 0 TRAP_REVERSAL.
  Axiom 14 confirmed live: volatile/range days dominate; clean trend days are rare.
- Detector clusters DO form on real ticks: 326 zones with 4+ detectors agreeing (max 7).
  The concept stack survives contact with reality — co-location is real, not a mock artifact.

## The five findings (evidence-ranked)

### 1. Execution chase destroys correct signals — the single biggest flip
Fill = market at confirmation-candle close ⇒ median 39-tick chase = 3× planned risk.
Counterfactual (limit fill at planned entry, same signals, same stops): 5/13 trades become
winners (+8.6R, +6.8R, +4.3R, +2.2R, +1.5R) ⇒ ≈ +15R net vs realized 0/13.
Also self-contradictory: ChaseGate forbids 0.1×ATR chases while the fill rule chases 3× risk.
**Fix direction: resting limit at traded-zone CE after trigger, expire if unfilled in N candles.**

### 2. NSE cost floor makes tight-stop M5 scalping mathematically unviable
Stops averaged 0.27×ATR ≈ 0.02–0.08% of price. Percentage costs (~0.04–0.08% round trip)
exceed the risk itself regardless of quantity (both scale with notional). The cost-viability
guard (correctly) blocked 172/230 arms. Choices (not mutually exclusive):
  a. corrected cost model (STT sell-only — was double-charged; fix in flight)
  b. wider stops: risk_pts ≥ ~0.2-0.3% of price ⇒ stop ≈ 1.5–2×ATR(M5) — but max_stop_atr
     caps 1.2×ATR: the stop budget and cost viability currently DON'T INTERSECT
  c. M15 decision timeframe (ATR doubles ⇒ same ATR-multiple = cost-viable rupee stops)
  d. judge viability vs expected profit (R:R≥1.5 ⇒ compare costs to reward, not risk)
**This is the fork to discuss — it sets the system's character (scalper vs intraday swing).**

### 3. Stops sit exactly where hunts happen
Median stop 0.27×ATR beyond swept edges; 7 of 11 stop-outs later traded through T1 the same
day; 5 wick-throughs survived only via close-confirm; one death by 1 tick. Wider stop floor
(≥0.5×ATR, likely ≥1×ATR post-cost-math) + the axiom-25 "small SL via waiting" needs
re-reading: small RELATIVE to target, not absolute-tiny — 0.27×ATR is hunt food.

### 4. RANGE_PIN sweep-fade monoculture fought the tape
12/13 trades = same setup (sweep+VSA+FVG fade at range edge), 9/13 against the day's drift,
7/8 stop-first trades counter-trend, all crammed into 11:00–12:55 (observe-gate erases
mornings, day-locks erase afternoons). The single align=1.0 trade hit T1 in one minute;
the other 12 carried a knowing 0.8 misalignment penalty and still traded.
Candidates (need >19 days of data to decide): require align=1.0 for counter-drift fades;
per-template entry windows; drift-day kill-switch for fades after NIFTY moves >X points.

### 5. R denomination and locks cascade
R booked vs planned risk while true risk = fill→stop + costs ⇒ single trades booked −7…−52R,
tripping daily-loss/consecutive-loss locks on cost noise, freezing afternoons where the
system's own stopped setups later won. Fix: R on effective (fill) risk everywhere.

## What is PROVEN good
- Patience architecture: 3,105 verdicts → 13 entries. Gates/locks all functioned as designed.
- Jul-13 DOUBLE_TRAP: system's one genuinely-armed A-setup was real (post entry-zone fix it
  arms with 0.65 risk vs 1.48 budget, then correctly refuses on failed confirmation).
- Infra: fetch→replay→report→calibrate loop, byte-reproducible journals, no-lookahead proven,
  detector detachability, index context live. The lab works; now it's calibration science.

## M2/M4 candle question (user asked)
M5 is hardcoded in ~21 sites; M2/M4 = refactor. Evidence so far says granularity is NOT the
binding constraint — execution rule + cost floor + stop width are. Finer candles would make
stops TIGHTER, worsening finding 2. Recommend: fix 1/2/3 first; revisit M2/M4 only if
trigger latency shows up as a measured leak afterward.

## Proposed next wave (pending discussion)
1. Limit-fill execution (finding 1) + R on effective risk (finding 5) — mechanical, high-confidence.
2. Cost model correction (in flight) + stop floor raised to cost-viable band; resolve the
   max_stop_atr intersection (likely 1.5-2.0 + M15-stop experiment as a config study).
3. Rerun month → if trades appear, judge finding-4 filters on the larger sample.
4. Only then: more history (M1 monthly accrual + 5m backfill for context), more symbols.
