# htf_nest — precision audit

Detector `htf_nest` / event `NEST` / feature `htf_ltf_nesting`.
Recognition/precision only (never edge/profit). Precision = of all firings,
how many are the REAL taught object (a genuine multi-TF nest). Recall is
already ~100%; the goal is fewer, higher-conviction births so more of a
firing's grade-stack is real.

## Firing picture (over-fire)

Source: `runs/validate/precision_study/evidence.parquet`, `detector==htf_nest &
event==NEST`, 8 marked stocks, ~17d 1m (sessions 16–19 per stock).

- **382 total NEST fires** over 8 stocks.
- Overall **density = 2.81 fires / stock / session** (382 / (8×17)).

| stock | fires | sessions | density (fires/sess) |
|---|---|---|---|
| HEROMOTOCO | 102 | 16 | **6.38** |
| TITAN | 75 | 19 | 3.95 |
| DABUR | 52 | 16 | 3.25 |
| DLF | 41 | 16 | 2.56 |
| VOLTAS | 41 | 16 | 2.56 |
| HAVELLS | 37 | 16 | 2.31 |
| HDFCBANK | 18 | 19 | 0.95 |
| SBILIFE | 16 | 16 | 1.00 |

A genuine multi-TF nested demand/supply base is a rare, high-conviction event
(the user marked it at most a handful of times per name across months). ~3–6
fires *per session* is far too dense to all be the taught object — this is
over-firing.

**Depth is the tell.** `strength = min(1, nest_depth/3)`, so depth decodes
exactly from strength:

- depth 1 (strength 0.333): **231 fires (60.5%)** — child overlaps exactly ONE
  higher TF.
- depth 2 (strength 0.667): **151 fires (39.5%)**.
- depth 3 (strength 1.0): **0 fires** — the cap is never reached.

So a clear **60.5% of all fires are single-HTF-overlap "nests" of depth 1** —
i.e. one 5m zone that happens to touch one 15m/1h/1d zone. That is not a nest;
it is the shallow `ladder._rung` H1↔M5 overlap this detector was built to
*generalise past*.

## In-window precision (honest data limit)

Window (1m/wide): **2026-06-25 .. 2026-07-17** (17 trading days). Only marks
with `date_approx` inside it, ON one of the 8 firing stocks, are checkable
against firings.

**Registry `htf_ltf_nesting` marks: 9 total — and ALL 9 are SBICARD** (t28a/b/e/g/h/i/j,
t29f, plus reference schematic `b8d2_c11` with no symbol). **SBICARD is not in
the firing dataset** (firing stocks = DABUR, DLF, HAVELLS, HDFCBANK, HEROMOTOCO,
SBILIFE, TITAN, VOLTAS).

- **In-window checkable-against-firings n = 0.** Several t28 marks resolve to
  2026-07-07 (inside the window) but on SBICARD, which never fires here; the
  rest are era-approx (2025 / "May–Jul 2026"). No firing can be geometry-matched
  to any mark.
- Therefore **precision / recall against marks is not computable**; per task,
  **firing density is the precision proxy**. At 2.81 fires/stock/session the
  proxy says the current birth gate is far too permissive to be selecting the
  taught object.

Corroborating evidence from the feature doc (`41-TOOLS/htf_ltf_nesting.md`):
the taught nest is a **deep drilldown** — t28 nests 1D>2H>15m>10m>5m>1m (4+
tiers); t29f nests 15m>30m>5m>1m. A depth-1 firing cannot be that object.

## Over-fire root cause

The **birth gate is `min_depth = 1`** (`_DEFAULTS`, line 31; tested at
`len(tiers) < int(min_depth)` → continue, lines 73–74). One overlapping higher
TF is enough to emit. Two structural amplifiers make depth-1 trivially easy to
hit:

1. **`min_depth = 1` admits the shallow single-overlap case.** The whole point
   of `htf_nest` (docstring: *"Generalises ladder._rung … to a full TF ladder"*;
   feature doc: *"the more parent TFs a zone is nested inside, the stronger"*)
   is that conviction comes from **multiple** HTF tiers agreeing. At depth 1 the
   detector is just re-emitting the ordinary "5m zone under one HTF zone"
   overlap — indistinguishable from a plain OB/FVG retest. 60.5% of fires are
   this shallow case.

2. **Parent pool is wide, and the match is bare interval-overlap.** The parent
   set `_PAR` includes not just OB/FVG zones but **EXT_L / EXT_H swing bands**
   (lines 27–29) — wide swing-extreme furniture that a 5m zone easily grazes.
   And `_overlaps` (lines 39–42) is raw interval intersection
   (`alo <= bhi and blo <= ahi`): a **1-tick kiss of the parent's outer edge
   counts as "nested"**, with no containment and no tolerance. The taught nest
   requires the child to sit *inside* the parent. So even the depth count is
   inflated by grazes that are not true containment.

Zone-width evidence: firing `zone_hi−zone_lo` ranges 0.17–12.4 ATR (median
0.95 ATR) — the emitter is boxing everything from tiny 5m origins to 12-ATR
bands, consistent with a gate that fires on almost any overlap rather than a
selective nest.

Net: the gate that should encode "nested inside *every* parent" instead fires
on "touches *one* parent", so the majority of the grade-stack fed to the
high-grade tier is not the taught object.

## The precision tune + expected effect

**THE single highest-leverage change: raise the birth gate `min_depth` from 1 → 2.**

- Exact change: `_DEFAULTS["min_depth"]: 1 → 2` (htf_nest.py line 31). One
  parameter; the gate at lines 73–74 already enforces it.
- Rationale: it directly removes the shallow single-overlap case that is not a
  nest, and keeps only births where **≥2 distinct higher TFs** contain the child
  — genuine multi-TF confluence, which is exactly what the feature teaches and
  what the high-grade tier should be stacking.

**Numeric target & expected firing reduction** (measured from the depth
histogram, no re-run needed): 231 depth-1 fires drop, 151 depth≥2 survive.

- **382 → 151 fires, −60.5%.**
- **Density 2.81 → 1.11 fires/stock/session.**
- Worst offenders collapse most: HEROMOTOCO 6.38→1.56, TITAN 3.95→0.79,
  DABUR 3.25→1.12, DLF 2.56→1.12; low-density HDFCBANK/SBILIFE barely move
  (0.95→0.58, 1.00→0.75) — the cut lands where the over-fire is.

**Effect on the high-grade tier.** Every surviving firing now carries ≥2 HTF
tiers of agreement (strength ≥ 0.667), so the fraction of NEST evidence that is
the real taught multi-TF nest rises from ~39.5% to ~100% of what's emitted.
Recall is unaffected for the taught object (a true nest is depth ≥ 2 by
construction — t28/t29 are 3–4 tiers), so this is a pure precision gain: fewer,
higher-conviction firings feeding the conjunction + tiny-stop RR.

**Second-order tune (secondary, do not conflate with the top one).** Once
depth≥2 is in, tighten the overlap match so a depth tier must be real
containment, not a grazing kiss: replace bare `_overlaps` with an
overlap-fraction / edge-tolerance test — count a tier only when child∩parent ≥
50% of the child band OR child edge within 0.25·ATR of the parent (mirrors
`ladder.EQ_ATR = 0.25`, per feature-doc enhancement #5). This would further
prune inflated depth-2 counts (grazes on wide EXT bands), but its numeric effect
needs a re-run since parent geometry is not in the firing parquet — hence it is
secondary to the `min_depth` gate, which is fully quantified above.
