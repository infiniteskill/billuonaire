# FINDER COVERAGE RE-MEASURE (RECALL2) — after `drift_continuation`

Follow-up to `RECALL.md`: that audit proved all 7 v2 tools are pullback/
reversion-shaped and 58% of trend-continuation run-starts were invisible
(missed-set profile: +0.24-ATR 6-bar pre-drift, −1.35 ATR below the 6-bar
extreme, 2.75× fresh 12-bar breakouts, volume-neutral). The missing class was
built as **`drift_continuation`** (`app/trader/detectors/drift_continuation.py`,
auto-registers, **NOT enabled in any config**): 6-bar drift ≥ 0.5×ATR in `d`,
close within 0.65×ATR of the prior 12-bar extreme, no cross-bar adverse leg
≥ 0.75×ATR in the last 6 bars, strength by drift magnitude +0.25 fresh-breakout
bonus, ttl 3, sl = 6-bar adverse extreme (compression_fade meta contract).

**Method**: identical to RECALL.md Table B. The new detector driven tick-by-tick
(real CandleStore + StockContext, default params, session-end hooks;
`drive_drift.py`) on the same top-10 + mid-10 × 57 sessions, merged with the
7-tool `merged_signals.parquet`; coverage = same-direction fire within ±3 bars
of an opp start (@2.5 ATR); random control = per-session uniform re-timing of
the (enlarged) signal budget, 20 draws (`recall2.py`). Budget added:
3,486 fires / 20 symbols = **3.1/symbol/session** (7-tool budget: ~38.6).

## Table 1 — union coverage before → after vs random budget (@2.5)

| group | union(7) | union(8) | Δ | random 7-budget | random 8-budget | corrected before | corrected after |
|---|---|---|---|---|---|---|---|
| top10 | 72.5% | **75.5%** | +3.0 | 80.9% | **83.6%** | −8.4 | **−8.1** |
| mid10 | 72.9% | **75.7%** | +2.9 | 81.0% | **84.1%** | −8.1 | **−8.4** |

Sweeps: @2.0 top10 72.1→75.4%, mid10 71.6→74.6%; @3.0 top10 73.1→76.3%,
mid10 74.0→76.8% (threshold-insensitive, as before). (7-budget controls 80.9/
81.0 vs RECALL.md's 81.1/81.2 = draw noise.)

**TARGET NOT MET**: union coverage was supposed to exceed the random-budget
control for the first time. It does not — the union gained +3.0 pts but the
control gained +2.7 pts from the same added budget; chance-corrected run-start
selectivity stays **negative** (top10 −8.4→−8.1, mid10 −8.1→−8.4 — unchanged
within draw noise).

## Table 2 — per-tool @2.5, top10 (8 tools; mid10 in parentheses for the new row)

| tool | n signals | coverage | med lag | med captured | % fires near an opp start |
|---|---|---|---|---|---|
| ob_lux | 5394 | 16.8% | −2 | 1.00 | 17.9% |
| fvg_cb | 2346 | 16.9% | 0 | 0.98 | 26.7% |
| compression_fade | 8836 | 46.8% | −1 | 1.00 | 16.7% |
| inducement | 700 | 5.2% | −1 | 1.00 | 17.1% |
| bpr | 924 | 5.3% | −1 | 1.00 | 19.7% |
| mitigation | 3193 | 23.5% | −1 | 1.00 | 19.8% |
| turtle_soup | 419 | 4.1% | −1 | 0.96 | 22.9% |
| **drift_continuation** | **1626** (1860) | **7.7%** (8.0%) | **−2** (−3) | **0.80** (0.83) | **15.9%** (14.3%) |
| **UNION(8)** | 23438 | **75.5%** | — | — | 18.6% |

Solo control: a random emitter with drift_continuation's own budget covers
13.6% (top10) / 15.7% (mid10) — the new tool's own chance-corrected
selectivity is **−5.8 / −7.7**. Same pathology as the incumbents, mechanically
inevitable for this shape: once a leg qualifies, consecutive bars keep
qualifying, so fires cluster inside the same ±3-bar neighborhoods instead of
marking new run starts; per-fire precision (15.9%) lands *below* the 7-tool
average (18.8%). When it IS present it is punctual and early (lag −2, ~80% of
the run still ahead — slightly less than the pullback tools' ~100% because it
fires after drift is established).

## Table 3 — the intended class IS being hit

| pattern (top10) | n | missed before | missed after |
|---|---|---|---|
| **trend-continuation** | 140 | **57.9%** | **44.3%** |
| coil-break | 10 | 40.0% | 20.0% (tiny n) |
| gap-open | 328 | 21.3% | 16.8% |
| reversal-after-sweep | 318 | 27.0% | 25.8% |
| other | 1547 | 26.1% | 24.1% |

Mid10 trend-continuation: 50.3% → 40.6%. drift_continuation covers 11.0%
(top10) / 10.5% (mid10) of the previously-missed sets (71 + 71 opps newly
covered) — the largest per-class reduction, exactly the shape it was built
from. The audit's descriptive spec was correct; it just doesn't change the
selectivity verdict.

## Table 4 — RESIDUAL missed profile (what's STILL invisible)

574/2343 = **24.5%** (top10; was 27.5%), 605/2491 = **24.3%** (mid10; was 27.1%).

| dimension (top10) | residual missed | covered | RECALL.md missed |
|---|---|---|---|
| pre-drift 6-bar (med) | **+0.05 ATR** | −0.22 | +0.24 |
| pre-drift ≥0.5 ATR | 41% | 30% | 46% |
| dist below 6-bar extreme (med) | −1.44 ATR | −1.91 | −1.35 |
| fresh 12-bar breakout | 8% | 6% | 11% |
| ignition bar (med) | 1.03 ATR | 1.08 | ~1.0 |
| volume spike ≥2× | 17% | 17% | 16% |
| magnitude (med) | 3.03 | 3.04 | 3.06 |
| missed% by tod | 23.3/25.6/23.4 | — | timing-flat |

The continuation tilt is now largely drained: the residual set's median
pre-drift is +0.05 ATR (below any workable gate — lowering `drift_min_atr`
toward 0 just converges the detector to the random control), breakout rate
8% vs 6% (was 2.75×), still slightly high-in-range (−1.44 vs −1.91), volume-
neutral, timing-flat, full-size runs. What remains is the featureless
drift/rotation start: no preamble signature at the M5 granularity this
enumeration measures.

## VERDICT

1. **The missed class is real and the new detector sees it**: trend-
   continuation misses drop 57.9→44.3% (top10) / 50.3→40.6% (mid10); union
   +3.0 pts on a +7.5% budget increase; punctual when present (lag −2, 80% of
   run captured).
2. **But the accuracy gate FAILS, honestly**: union(8) 75.5% still trails the
   same-budget random control 83.6%; chance-corrected selectivity is still
   ~−8 pts and the new tool's own corrected selectivity is −5.8. Coverage was
   never the binding failure — per-fire discrimination is, and a
   trend-following emitter clusters fires along the leg just like the
   pullback tools cluster at zones.
3. **Residual 24.5% is profile-flat** (median drift +0.05 ATR, breakout 8%,
   volume-neutral, all hours): no further shape-detector is implied by this
   data at M5.
4. Consistent with RECALL.md verdict 4: the finder's fix is not more
   coverage; it is fire-level selectivity (and post-cost extraction).
   `drift_continuation` stays registered-but-disabled: a coverage instrument,
   not a validated edge.

*Artifacts (scratchpad): `drift_{SYM}.parquet` ×20, `merged_signals2.parquet`,
`recall2_opps_25_{top10,mid10}.parquet`, `recall2.out`; scripts
`drive_drift.py`, `recall2.py` (reuses `recall_analysis.py` with TOOLS
patched to 8, `opportunities.parquet`, 20-draw seed-7 random control).*
