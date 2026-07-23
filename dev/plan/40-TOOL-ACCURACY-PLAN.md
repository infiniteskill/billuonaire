# 40 — TOOL-ACCURACY PLAN (EXHAUSTIVE): validate EVERY tool on EVERY feature on EVERY chart, then enhance (2026-07-23)

User directive (refined): MISS NOTHING. Every STOCK × every TOOL × every FEATURE × every CHART must be
tool-checked, validated, studied → then a per-tool ENHANCEMENT plan. Only after every tool's conclusions +
plans are ready do we build final code. This phase = exhaustive study + validation + plan. NO build now.
Prior version sampled 3-6 instances/tool — REJECTED. This version covers the FULL coverage matrix.

## The corpus (nothing excluded)
- **139 charts total** = 87 trade images (`/home/doom/Pictures/Screenshots/trades/*` — all 34 folders,
  t1..T31 + WYCKOFF) + 52 dev feature-images (`dev/IMG/*.png`).
- **~10 stocks**: HAVELLS, VOLTAS, DLF, TITAN, DABUR, SBICARD, SBILIFE + dev-only HEROMOTOCO, HDFCBANK,
  UNITY, … (exact set confirmed during CATALOG from each chart's Kite URL/title).
- **~16 feature/tool columns**: extreme/swing, liquidity-pool, sweep, order_block, fvg, ifvg, propulsion,
  breaker, mitigation, structure(BOS/CHoCH), compression, wyckoff-phase, spring/utad, premium_discount,
  htf_ltf_nesting, volume/time.

## THE COVERAGE MATRIX (the "miss nothing" contract)
Rows = 139 charts. Cols = 16 features. Cell = every MARKED INSTANCE of that feature on that chart. Every
cell is either VALIDATED against its detector or explicitly marked UNCHECKABLE-with-reason. A final audit
proves every chart and every mark is accounted for — no silent drops.

Registry row (one per marked instance):
`{instance_id, chart_path, stock, tf, date_approx, feature, sub_type, geometry(box_hi/box_lo | line_level |
pivot_price), label_text, birth_candle, entry, sl, target, direction, notes}`

Validation record (one per instance):
`{instance_id, tool, data_avail(5m/1h/daily/none), fires(y/n/uncheckable), box_match_tol, birth_match,
entry_match, sl_match, verdict(hit/partial/miss/uncheckable), numeric_gap, root_cause}`

## WORKFLOW DESIGN — 5 phases (chained; I review between)

**Phase 1 — CATALOG (exhaustive, per chart).** ~12 agents, ~12 charts each, cover all 139. Each reads its
charts and extracts EVERY marked feature instance (all fields above) → appends rows to
`runs/validate/tools/registry.jsonl`. Output: complete ground-truth registry of every mark on every chart.
This is the miss-nothing foundation. (Also captures stock + date + TF per chart.)

**Phase 2 — INDEX + RESOLVE (barrier).** Consolidate registry; resolve each chart's stock+date to real
candles (tools/yvalidate); tag data-availability per instance. Emit the COVERAGE MATRIX
`runs/validate/tools/MATRIX.md` (stock×feature counts + chart×feature present/absent) so completeness is
auditable. Instance counts per tool drive Phase-3 batching.

**Phase 3 — VALIDATE EVERY INSTANCE (per tool, exhaustive, NOT sampled).** For each of the 16 tools, take
ALL its registry instances and validate the detector against EACH: read the detector code once, then per
instance check fires?/box-tol/birth/entry/sl vs the mark, NUMERICALLY where data exists (read
data/yahoo|long5m CSV for the window), analytically + 'uncheckable' where not. Batch per (tool × stock) to
keep every instance covered. Writes `runs/validate/tools/val_<tool>.jsonl` (one record per instance).

**Phase 4 — PER-TOOL ENHANCEMENT PLAN.** Per tool, aggregate ALL its validation records → accuracy verdict
(%hit over ALL instances, not a sample) + gap taxonomy + prioritized tweak plan with NUMERIC targets derived
from the full instance distribution (e.g. "OB box should extend to outer wick: median miss = X ATR; birth
gate needs sweep+BOS: Y% of marks were post-sweep"). Write `dev/plan/41-TOOLS/<tool>.md`.

**Phase 5 — CROSS + AUDIT.** (a) CONFLUENCE map (`41-TOOLS/_CONFLUENCE.md`): co-fire sets, firing order,
anchor vs confirmer, weakest link. (b) COMPLETENESS AUDIT (`41-TOOLS/_GAPS.md`): verify every chart in the
registry and every mark got a validation verdict or a reasoned uncheckable; flag missing data, the
premium_discount tool that must be built new, the HTF-nesting scoring spec, any two-doc contradiction, and
any re-introduced optimism (recognition claimed as edge).

## Guardrails (from RETHINK.md — do not repeat the drift)
Distinguish RECOGNITION (fires on the right candle) from EDGE (never claim profitability here). Honor data
limits (native 5m only <60d; only t31's year is firm — dates approximate). Verify the doc35 known gaps
(outer-wick box + inner-body block; CE entry; outer-wick SL; born-after-sweep+BOS; liquidity from EXT). The
measured null tested a MIS-BUILT proxy — validate the USER's geometry, not shipped defaults. No silent
truncation: every skipped/uncheckable instance is logged with a reason.

## Deliverables (this phase)
`runs/validate/tools/{registry.jsonl, MATRIX.md, val_*.jsonl}` + `dev/plan/41-TOOLS/{<16 tools>.md,
_CONFLUENCE.md, _GAPS.md}`. Build gate: when all 16 tool docs + confluence + gaps are done & reviewed →
final-code build (doc 33, corrected geometry) begins. NOT before.

## Est. scale (ultracode): ~12 catalog + 1 index + ~16-30 validate (per tool×stock) + 16 synth + 2 cross ≈
50-70 agents, all coverage-complete. Chained as CATALOG → (review) → VALIDATE+ENHANCE → (review) → CROSS.
