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
