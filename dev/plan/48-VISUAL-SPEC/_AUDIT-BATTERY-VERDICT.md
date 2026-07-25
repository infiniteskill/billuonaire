# AUDIT BATTERY — 4-agent detector audits → 5-variant 40-stock gate (2026-07-25, stage2)

## Audit findings (dev/plan/48-VISUAL-SPEC/audit_{anchors,liquidity,regime,zones}.md)
- anchors: extremes 9/10 HIT ±0.03%; **structure DISABLED in prod** (trend_swings:2 impossible → bos
  grade term dead in every trade); master=all-history extreme skews p/d.
- liquidity: taught lines all HIT; multi-day sweeps DEAD-confirm early (no session-scale pass);
  min_touches=3 strangles 69% EQ sweeps (86% pools carry fake TF-echo touches); G3 poke verified live.
- regime: wyckoff 12x scale mismatch (1h/W70/RA12 fires spring@1141 + UTAD@1234 exactly; vol gate
  untaught + vetoes both); **p/d lookback bug FIXED** (filtered singleton master pair = silence-only;
  local-recompute = 5/5 mark directions, taught boxes verbatim).
- zones: OB recognition 3/7 frozen → 6/7 min_disp=0 (gate kills post-sweep basing OBs); sweep-candle-
  as-run-breaker mints wrong box; **propulsion2 parent universe 8.2x** (no min_disp) → param added.

## Gate battery (deduped eod hi>=5 +minRR3; frozen +7.34R n153)
| variant | net | Δ | verdict |
|---|---|---|---|
| prp (propulsion2 min_disp=1.0) | +7.34, quads IDENTICAL | 0.00 | **SHIP — free consistency fix** |
| ts4 (structure trend_swings=4) | +7.34 hi-tier identical | 0.00 | **KEEP stage2** — revives designed bos term; g4 late/A −0.73 noted |
| pd20 (local dealing range) | +6.86 | −0.48 | REJECT as grade input → direction-fidelity layer |
| wyk1h (taught-scale wyckoff) | +7.06 | −0.28 | REJECT as grade input → recognition layer |
| combo | +6.71 | −0.63 | REJECT |

## Meta (confirmations 7-8)
Fidelity ≠ edge, again: perfect direction accuracy (pd20) and exact taught-event recognition (wyk1h)
both PRICE WORSE than the frozen conjunction. The frozen grade is the edge; the visual/fidelity layer
is for faithfulness, diagnostics, selection metadata, and the future live UI — never a grade input
without passing this gate.

## Standing open (edge-neutral fidelity work, no gate needed)
liquidity S-set (wick-keyed EQ lines, kind-aware touch gate, session-scale sweep pass, EXT carry,
recency floor) — improves the DIAGNOSTIC map; ob_taught include_break_bar/mono_run variants; 5 user
questions (_SPEC.md §D).

## Battery-2 (2026-07-25 late): keepers cross-regime + s12/obi
| variant | eod hi>=5 +minRR | ref | verdict |
|---|---|---|---|
| keepers BULL | +8.53 n333 | +8.63 | HOLDS → merge-blocker cleared |
| keepers BEAR | +6.70 n465 | +6.75 | HOLDS |
| **s12** (S1 wick-line EQ + S2 distinct-touch + EQ-gate 2) | **+7.62 n158** | +7.34 | **+0.28 — FIRST fidelity fix to IMPROVE the money gate** (C3 selective-error fix); cross-regime confirm in battery-3 |
| obi (I3 break-bar) | +7.29 n151 | +7.34 | neutral → param off |
Battery-3 running: s12×bull/bear + wide2026 (7-month, 40-stock) frozen anchor + s12-wide2026.
Gate tape upgraded: data/wide2026 (Jan-Jul, 137 sessions) replaces the 17-day tape as anchor.

## Battery-3 FINAL (2026-07-25): s12 cross-regime + wide2026 anchor
| leg | s12 | frozen ref | delta |
|---|---|---|---|
| 2026 17-day | +7.62 | +7.34 | +0.28 |
| bull | +8.93 | +8.63 | +0.30 |
| bear | +6.68 | +6.75 | −0.07 |
| **wide2026 7-month (n1233)** | **+5.89** | **+6.02** | **−0.13** |
n-weighted ≈ 0.00 → **s12 = edge-NEUTRAL** (battery-2's +0.28 was small-tape flattery). SHIPPED to
stage2 profile on FIDELITY grounds (wick-line EQ, honest touch counts, EQ sweeps emitting; zero edge cost).

## NEW GATE ANCHOR: data/wide2026 (frozen config, 40 stk, Jan-Jul, 137 sess, deduped eod hi>=5+minRR)
**+6.02R n=1215 win 66%** — the honest production number (Jan-May untouched by tuning; the 17-day
+7.34 carried in-sample flattery). All future gates reference THIS. Perf fix made the 7-month derive
~15min (was ~hours).

## S3 gate (wide2026): FIRST RECALL-EXPANDER SHIPPED
n 1239->1313 (+74 multi-day-sweep killshots), per-trade +5.86 (holds, -0.03 noise), hit 64.7%,
**TOTAL R +7298->+7701 (+5.5%)**. Recall fixes = more killshots at same quality = more total money.

## I1 gate (wide2026): SECOND RECALL-EXPANDER SHIPPED
n 1313->1479 (+166 sub-displacement OB killshots), hit holds 64.5%, per-trade +5.65 (-0.21 documented
tradeoff), quads all + (0.87..4.06), **TOTAL R +7701->+8359 (+8.5%)**. Cumulative recall arc vs main:
n 1215->1479 (+22%), TOTAL R +7314->+8359 (+14.3%).

## Deepest-tier entry gate: NEUTRAL reject (n1477/+8320 vs n1479/+8359 identical — zone choice never
binds at tick level; deeper zones fire later as their own trades). Param off.
## sl_floor PARITY: closed — 9% of killshots below floor, widened 1.3x, net impact bounded ±4% total R.
Sim ≈ production. (Those 127 sub-floor trades = the best cohort: +9.83R, 68% win.)
