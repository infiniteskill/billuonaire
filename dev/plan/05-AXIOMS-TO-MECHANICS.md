# 31 Axioms → Mechanics

User's trading axioms (2026-07-15). Each mapped to enforcement point. This file is the
philosophy→code traceability matrix; if an axiom has no mechanism, that's a bug in the plan.

| # | Axiom | Mechanism | Where |
|---|---|---|---|
| 1 | Every move is trap, has countermove | Default suspicion: no move trusted without sweep→reclaim proof; Level state machine | sweep, structure |
| 2 | Every countermove is trap too, recursive | **TrapChain tracker**: reversal leg's own extremes become next liquidity; chain depth on Evidence.meta; 2nd-order sweep strength +0.1 | sweep (chain_depth) |
| 3 | Moves/countermoves co-exist per TF | Detectors run per TF (M5/M15/H1/D1); Evidence tagged tf; spatial clustering cross-TF | engine/confluence |
| 4 | Use for reversal trades with BOS+OB | RELEASE entry = post-CHoCH retrace into OB/breaker | engine/pipeline |
| 5 | Most liquidity in morning 1 HR | timestats priors: 09:15–10:30 danger 0.8; liquidity detector weights opening range pools high | timestats, liquidity |
| 6 | Operator hunts stops in morning | TRAP window = observation only; morning sweeps expected, scored as signal-for-later | template, sweep |
| 7 | **OBs designed during morning hunt** | OB gets `birth_time`; hunt-born (09:15–10:45) + displacement = premium flag, quality +0.15 | orderblock |
| 8 | Trade those OBs near/after 11 | `observe_until: "11:00"` default (was 10:45); hunt-born OB retest = top entry pattern | gates.TimeWindowGate |
| 9 | Morning trades lose (hunting) | Hard: no entries before observe_until. No exceptions, not even 99 confluence | gates |
| 10 | Panic/early entry, wrong timing = failures | **ChaseGate**: entry only inside zone, never beyond zone edge + 0.1×ATR; trigger-confirmed entries only (3-stage entry FSM, see 06) | gates, pipeline |
| 11 | Market moves per index; options sold+decayed purposely | **index detector**: NIFTY/BANKNIFTY structure+phase as context Evidence on every stock; strong index counter-move = score haircut ×0.5 | detectors/index |
| 12 | Gaps, breakouts, big moves, results, news preplanned | **EventCooldownGate**: gap open or candle >3×ATR ⇒ mandatory `cooldown_candles: 6` (M5) wait; earnings-day skip via stocks.json `events` field | gates |
| 14 | Volatile days > trending days | Template priors: TREND base rate low (~40%); UNCLASSIFIED default | template |
| 15 | Options sold trending days, decayed volatile days | cage detector OI-change matrix (writers add = pin day expected) | cage (Phase 6) |
| 16 | Volatile days take back trend-day profits | **Inter-day context**: day-after-TREND ⇒ size ×0.75 + give-back prior in template classifier; learned per stock | template, risk |
| 17 | Waiting > losing | Patience core: default verdict NO; skips journaled + scored | engine, journal |
| 18 | Gap down traps sellers, gap up traps buyers | Gap fade-bias: gap direction = suspected trap direction until BOS confirms; feeds template | template, structure |
| 19 | Small SL via waiting + refining | `max_stop_atr: 1.2` — stop distance > 1.2×ATR ⇒ SKIP (don't widen, don't take) | risk/sizing |
| 20 | Morning push down + induce trailers = up-trap | judas_reversal template LONG release | template |
| 21 | Morning push up + induce trailers = down-trap | judas_reversal mirror SHORT release | template |
| 22 | S/R, trends, patterns all fakeable | Nothing trusted standalone: min 3 distinct detectors in a ConfluenceZone to arm | confluence |
| 23 | Prices designed, not buyer/seller driven | Volume read as operator intent (VSA absorption/no-demand), not demand/supply | volume |
| 24 | Psychological design; setups sustain sometimes | Probabilistic scoring end-to-end; per-detector precision tracked; no certainty language in output | learn/calibrate |
| 25 | Precise execution ⇒ small SL | 3-stage entry FSM: ARMED→TRIGGER→FILL; entry at zone, SL beyond trap extreme; see 06 §4 | pipeline, execution |
| 26 | Market designed to lose; few outsmart | System refuses more than it takes: gates ALL must pass; expected 0–3 trades/day, most days 0–1 | gates |
| 27 | After 11 AM good OB trades, small SL | = axioms 7+8: hunt-born OB + post-11 window + max_stop_atr | combined |
| 28 | Valid OBs are not broken | OB validity = hunt-born/displacement/unmitigated; break while ARMED ⇒ instant disarm + Level→breaker candidate | orderblock, pipeline |
| 29 | Decide RANGING or TRENDING | Template classifier mandatory; UNCLASSIFIED ⇒ TemplateGate blocks all day | template |
| 30 | 10 successful trades enough | Optional `daily_profit_lock_R: 2.0` (stop after +2R day) + monthly trade-quality report over volume | risk/limits |
| 31 | Look for clean chart | **cleanliness** in fit score: spread tightness, gap frequency, swing regularity (stddev of swing sizes), ATR stability; dirty stocks sink in `trader list` | scanner (06 §7) |

(13 absent in user list — numbering preserved as given.)

## Config additions (extends 01-ARCHITECTURE-CONTRACTS shape)

```json
{
  "time": {"observe_until": "11:00"},
  "entry": {"max_stop_atr": 1.2, "chase_tolerance_atr": 0.1, "min_zone_detectors": 3},
  "events": {"cooldown_candles": 6, "big_candle_atr": 3.0},
  "risk": {"daily_profit_lock_R": 2.0, "day_after_trend_mult": 0.75,
           "portfolio_heat_pct": 1.0, "max_correlated_positions": 2}
}
```

New detectors: `index`, `compression` (see 06). New gates: `ChaseGate`, `EventCooldownGate`.
Roadmap placement: index+compression detectors → Phase 3; new gates → Phase 4; scanner → Phase 4.
