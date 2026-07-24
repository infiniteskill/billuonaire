# STATE OF THE PROJECT — the taught edge, validated (2026-07-24)

The single-page truth after the full build → measure → scrutinize → validate arc. Supersedes the
optimistic intermediate claims; every number here is deduped/honest + gate-checked.

## THE EDGE (one line)
A grade-conjunction × RR-asymmetry system on the taught SMC method: enter a nested decisional zone at a
D1 premium/discount extreme, tight structural stop, far-liquidity target. **hi-tier (grade≥5) ≈ +6-7R/trade
eod, win ~56-72%, deduped/executable.** Not accuracy — RR asymmetry on a coin-flip hit-rate, in the
right direction per regime (which the grade+far-target auto-select).

## VALIDATION STACK — what is PROVEN
| dimension | result | evidence |
|---|---|---|
| Regime-agnostic | 3 regimes (mixed/bull/bear), **12/12 quad-regime cells +** | triptych, frozen config |
| Window-robust | far-RR edge lookback-INVARIANT; min-RR removes the tinyRR haircut | +6.05R local ≈ +7.21R 6mo |
| Temporally stable | **19/19 sequential windows +** (incl OOS-earlier 2026), ~14 months | walk-forward |
| Honest/deduped | raw was ~40% clustering-inflated → +6-7R is the executable number | dedup by (sym,e,sl,tgt) |
| Tuning-resistant | 3 deep-study fixes REJECTED by the gate → robust local optimum | B1, warm-up, mode-switch |
| Faithful (shorts) | user's marked shorts fire as winners in local context (1221 → +27.6R) | temporal co-location |
| Cost-honest | 1m gap-aware fill-through + rupee costs; survives M5-close & EOD-squareoff | derive_tradebook |

## WHAT SHIPPED (production config)
- **min-RR≥3** gate in `decide()` (`taught_profile decision.min_rr=3`, pipeline wired) — the ONE tune that
  passed every gate: proven 4 contexts, window-robustifier, verified implementation==A/B. 46 tests green.
- Everything else FROZEN (grade formula, min_grade=4, detectors). Deliberately — it resists improvement.

## WHAT WAS REJECTED (the gate did its job)
- **B1 anchor fix** (emit_live): net-R +6.94→+4.78R, didn't promote the target. Reverted.
- **Regime mode-switch** (suppress counter-trend): hurts bull (+8.63→+7.51R). Rejected.
- **b_hit>0 / local-window p/d**: coverage/selectivity, no clean edge lift. Held/unproven.
- Root: all derived from the UNGATED SYMMETRIC frame; the GRADED+RR edge already encodes them implicitly.

## HONEST CEILING — what history+sim CANNOT answer
1. **Tick fills** — the 1m gap-aware model is optimistic vs real fills/slippage/partials.
2. **Live execution** — routing, per-stock liquidity/capacity, squareoff mechanics, latency.
3. **Future regime** — 14 months of history ≠ the future; the edge could decay.
4. **Faithfulness (full)** — only shorts, only local context, only 2026-dated marks proven; 12 prior-year
   (Aug-Dec) marks + the LONG side unproven.
These are the boundary where historical-1m research ENDS.

## THE NEXT REAL STEP — a small PAPER PILOT (build spec)
Not more historical tuning (contraindicated). The pipeline is already wired for `engine=taught` + min-RR;
what's missing for a paper pilot:
1. **Live data feed** — Kite streaming (websocket) into the M1 CandleStore (currently FileFeed only).
2. **Paper execution** — a broker-sim that logs decide()-takes as paper orders + tracks fills/P&L on
   live ticks (NO real orders — paper only; live trade execution is out of scope / user-only).
3. **Live regime/window guard** — cap the extremes/p-d lookback to a LOCAL window (the window finding)
   so live direction matches the tested local context; min-RR already handles the R-magnitude.
4. **Guardrails** — daily loss cap, per-stock size cap, EOD squareoff (already the best sim mode).
Run it small, log every decide() vs the paper fill, compare live hit-rate/net-R to the +6-7R sim
expectation. That comparison is the ONLY thing that turns "validated candidate" into "proven live".

## VERDICT
A **VALIDATED CANDIDATE** — real, regime-agnostic, window-robust, temporally-stable, honest ~+6-7R,
at its historical-1m-research ceiling. The disciplined move is a paper pilot, not more tuning.
Artifacts: derive_tradebook.py (honest sim), ab_tradebook.py (gate A/B), derive_parallel.py (sharded),
runs/validate/tradebook_*.csv (the tradebooks), dev/plan/47-40STOCK/*.md (this study).
