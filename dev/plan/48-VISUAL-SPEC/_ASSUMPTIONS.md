# ASSUMPTION INVENTORY — what every number here rests on (2026-07-26)

Process fix after the phantom-fill disaster: **twelve downstream batteries shared one
upstream fiction and none could see it.** Every result from here on must be published
with this table, each row marked VERIFIED / BOUNDED / UNVERIFIED.

| # | assumption | status | evidence / risk |
|---|---|---|---|
| A1 | entry actually fills at our price | **VERIFIED (bounded)** | honest race: limit must be TOUCHED same session; 57% of old "trades" were phantom (91% of old profit). Fill-bar judged SL-first = pessimistic bound. Intra-minute sequence unknowable at 1m. |
| A2 | entry price = ZONE MID | **VERIFIED vs marks** | 36 measured hand-entries, medians 0.48/0.54/0.56/0.57 |
| A3 | SL = 0.7 x zone height | **VERIFIED vs marks** | measured 0.67-0.75H; every observed zone wicked its far edge -> at-edge stop dies |
| A4 | zone reported == zone entered | **FIXED 2026-07-26** | decide() picked the globally-deepest nest, not the nest OF the chosen zone -> entry/zone split by 27-43 rupees. All pre-fix zone-relative stats void. |
| A5 | signal DIRECTION matches the method | **FIXED (config)** | p/d dealing range is lookback-sensitive; 6-month history inverted direction vs the user's local range (measured on his own marks). Measurement profile now p/d range_lookback_days=20. |
| A6 | BE-move to entry+cost once profitable | **TAUGHT, param** | user rule; zero chart annotations -> be_mult swept |
| A7 | trail distance | **TAUGHT, param** | "2-3rs on a 2000rs stock" ~ 0.15% px ~ 1/6 daily range -> swept as frac x per-stock daily range |
| A8 | costs | **VERIFIED (exact)** | Zerodha intraday equity: brokerage min(20, 0.03%) x2, STT 0.025% sell, exch 0.00297%, SEBI 10/cr, stamp 0.003% buy, GST 18% |
| A9 | targets | **UNVERIFIED** | `_runway` nearest far opposite EXT. User has NOT taught targets ("decide later"). Exit-mode sweep (target/trail/hybrid) is the stand-in. |
| A10 | holding period | **UNVERIFIED** | production squares off 15:10; the user's own examples held DAYS (t29/t30). Both modelled (intraday / 5-day). |
| A11 | one trade per signal, no capacity limit | **FIXED (portfolio_sim)** | sum-of-all-signals is untradeable (226/month, account holds 1-2). Capacity sim ranks ex-ante and obeys risk rules. |
| A12 | slippage beyond the limit price | **UNVERIFIED** | limit assumed to fill AT price when touched; real books can trade through without filling size. Only a live/paper pilot resolves. |
| A13 | 1m bar granularity | **BOUNDED** | intra-bar ordering unknown -> SL-first everywhere (pessimistic). Tick data would narrow. |
| A14 | data quality | **SPOT-CHECKED** | 1/40 stocks had a >12% gap (ADANIPOWER); no systemic split/adjust errors found |
| A15 | the marks are ground truth | **PARTIAL** | 32 hand-marks, year inferred (month<=7 = 2026); 20 testable, 19 in-universe |

## THE ADMISSIBILITY RULE
No aggregate statistic is reported unless `tools/ground_truth.py` shows the pipeline
reproduces >=50% of the user's testable marks with the CORRECT DIRECTION on the same
tape. Old tape scored 21% -> every number computed on it is inadmissible.

## TOOLS THAT ENFORCE THIS
- `tools/ground_truth.py` — the admissibility gate (marks vs tape)
- `tools/trace_audit.py`   — per-trade independent re-race (catches phantom/lookahead)
- `tools/grammar_audit.py` — FORM/DEPART/RETURN/RESPOND classification + taught race
- `tools/trail_opt.py`     — taught management sim: costs, BE-at-cost, per-stock trail, exit modes
- `tools/portfolio_sim.py` — capacity-real account curve (ranking + risk rules)
