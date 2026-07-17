# v2 Build Plan — build the measured winners (2026-07-17)

Build ON the existing framework (detachable detectors + config-weighted confluence + replay
+ 592 green tests). Each v2 detector = a new plugin porting the VALIDATED scratchpad logic
(the measurement code IS the reference). Enable a v2 config profile; A/B replay vs baseline.
Build only KEEP rows (`23-CHECKLIST-RESULTS.md`). COMPACT. Suite green after each task.

## Wave 1 — core grab-signal detectors (parallel, disjoint files)
- **ob_lux** — LuxAlgo vol-adj leg-extreme OB (port scratchpad/luxob.py `lux_ob_events`).
- **fvg_cb** — FVG close-beyond + auto mean-range% threshold (port scratchpad/fvg2.py `gaps(...,"luxded")` + CE-hold).
- **compression_fade** — fade the coil breakout, SL beyond the break (port scratchpad/compress.py + rr EOD logic). The base signal.
- **inducement** — HTF CHoCH dir + LTF inducement grab (port a013584c scratchpad/ind_sweeps.py IDM_entry len20).

## Wave 2 — secondary zones + level map
- **bpr** — opposing-FVG overlap (from ict_pieces.py). **mitigation** (body-only zone). **turtle_soup** (range-extreme sweep+reclaim).
- **sl_cluster_map** — level fatness map with INVERTED strength (fresh>obvious); feeds zone-freshness weighting + targets.

## Wave 3 — direction + decision
- **htf_dir_h60 + smt** — H60 (≈12× entry TF) leak-free structure bias + SMT-divergence (stock vs NIFTY) as context/gate.
- **decision_tf** — make decision TF config (M10 primary); MarketSpec `decision_tf`, thread through pipeline (M5 hardcoded ~21 sites → param).
- **structure→direction-only** — keep structure detector but weight 0 (context/bias), drop breaker/iFVG/PO3/rejection/heavy-level-bonus/VSA-booster from the v2 confluence weights.
- **reweight confluence** — weights ∝ measured marginal edge (OB/FVG/compression/inducement/BPR up; structure/sweep/pool down/out). NOT by count (density doesn't lift).

## Wave 4 — prove it (the forensic gate)
- **v2 config profile** (config.v2.json) enabling the v2 detector set + weights + M10.
- **A/B replay** — replay(baseline) vs replay(v2) on the real month, cross-sectional holdout stocks;
  rich journal (every decision + the real candles) so we can autopsy each trade: why it won/lost.
- Ship v2 only if net-R beats baseline AND survives costs at the tiny-SL rupee risk.

## Notes
- Losers stay OUT of v2 weights but detectors remain in the registry (baseline A/B needs them).
- Detectors TF-parameterized (read ctx.candles.last(n, tf)); decision-TF change is Wave 3.
- SL semantics: v2 entries set SL beyond the destroyed extreme (tiny) — port the SL from each
  scratchpad signal so RR matches what we measured.
- Keep the pipeline deterministic + no-lookahead; every task re-runs the suite.
