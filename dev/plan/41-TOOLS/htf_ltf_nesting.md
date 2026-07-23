# htf_ltf_nesting

Multi-timeframe nesting: draw the trade zone on a HIGHER timeframe (the
context / demand-supply base), then drill DOWN through successive lower
timeframes and refine the SAME zone until the entry sits on a low-TF origin
nested inside every parent. The teaching statement (reference schematic
`b8d2_c11`, "HTF Demand + LTF Demand") is: *nest the LTF entry inside the HTF
zone for a refined multi-timeframe entry*.

There is **no dedicated `htf_ltf_nesting` detector** in the codebase. The
concept is realised only in fragments, none of which reproduces a hand-drawn
nest. See "Accuracy verdict" for what each fragment does and misses.

## Feature notes (structure & validity)

**Candle / price geometry.** The user's marks are two shapes:

- **HTF context circles / boxes** (t28a 1D `570-660`; t28b 2H `560-700`;
  t28e/g 5m ellipse `560-720`; t28h 10m; t28i/j 15m ellipse `560-720`). These
  are loose highlights framing a range, drawn with TradingView's ellipse tool
  (its readout `158.80 / -25% / 2863 bars` is just the ellipse *size*, not a
  precise edge). Numerically the SBICARD 2026 daily base is real: after a
  ~-28% decline from Feb ~800, price consolidated May-Jul 2026 at low
  565-612 / high 638-660 -- the `570-660` box (t28a) frames it almost exactly.
  The 5m ellipse `560-720` is loose: 5m visible range is 566.9-657.8, so the
  ellipse top over-draws by +9.5%.
- **A concrete nested demand OB** (t29f 1m). Same demand refined across
  TFs: `15m 843-828 > 30m 845-830 > 5m 838-832 > 1m 837-835`, entry `835`,
  SL `828`. Each inner box is a tighter slice of the outer; the entry is the
  1m origin; the SL sits BELOW the outer wick of the base.

**HOW / WHEN it fires (as the user draws it).** The HTF zone is a
demand/supply base or a decisional zone. You mark it on the high TF, then step
down (1D -> 2H -> 15m -> 10m -> 5m -> 1m for t28; 15m -> 30m -> 5m -> 1m for
t29) confirming at each step that a same-direction zone (OB/FVG/demand) still
holds and gets tighter. The entry is armed only when the innermost LTF origin
is reached; the stop is anchored to the OUTER WICK of the base, not any inner
tier.

**CONFLUENCE.** Nesting is itself a confluence multiplier -- the more parent
TFs a zone is nested inside, the stronger. In this codebase that maps to
three existing knobs: (a) `wyckoff.htf_phase` D1 regime, (b) confluence
`_align` D1+M15 agreement multiplier, (c) ladder rung-2 `+H1 nested`. A fully
nested long is: D1 MARKUP + M15 up + M5 OB overlapping a live H1 OB/FVG +
1m origin entry.

## How the user draws it

1. Open the HTF (Daily / 2H). Circle the accumulation/distribution base or
   decisional zone that price has reacted from (t28a: the -28%-decline base).
2. Drop one TF at a time (2H -> 15m -> 10m -> 5m). At each, redraw the SAME
   zone tighter -- an FVG or OB inside the parent (t28j co-shows 2H FVG + 2H
   OB with the 5m entry OB inside).
3. On the lowest TF (1m/5m) mark the entry OB origin (t29f entry 835 = 1m
   origin) nested inside all parents.
4. SL goes beyond the OUTER WICK of the base (t29f SL 828, below the 830 wick),
   never at an inner-tier body edge. Target is the opposing HTF liquidity.

## Accuracy verdict

**pct_match = 0% (0 hit / 8 scored).** Denominator excludes the 1 uncheckable
reference. Counts: **hit 0, partial 2, miss 6, uncheckable 1** over **9**
instances.

| verdict | instances |
|---|---|
| hit | (none) |
| partial | t28j, t29f |
| miss | t28a, t28b, t28e, t28g, t28h, t28i |
| uncheckable | b8d2_c11 |

**Per-stock breakdown.** All 9 are SBICARD except the reference schematic
`b8d2_c11` (no symbol). SBICARD tape: 8 instances -> 0 hit / 2 partial / 6
miss.

**What the code actually has (the three fragments):**

- `engine/ladder.py` rung 2 `+H1 nested` (`_rung`, lines 199-206): the M5
  OB/FVG zone band must overlap a LIVE same-direction H1 zone (H1 FVG =
  3-candle wick gap; H1 OB = simplified LuxAlgo pivot). This IS a 2-tier
  LTF-in-HTF nest and is the closest thing to the feature -- but it is
  **binary** (yields a +1 rung, not a drawn zone), **H1<->M5 ONLY**, and
  fires only when other detectors already scored a zone.
- `detectors/wyckoff.py::htf_phase` (lines 140-147): net D1 close change over
  the last 10 D1 candles; MARKUP/MARKDOWN when `|pct| > 2%`. A directional
  REGIME scalar, not a zone.
- `engine/confluence.py::_align` (lines 143-147): D1 regime veto (0.0 against)
  + M15 trend agreement (1.0 agree / 0.8 neutral / 0.0 oppose). The "M15
  nested in D1" alignment multiplier.

**Structural gaps (why 6 misses):**

1. **No HTF context-zone detector.** Nothing emits a Daily accumulation-base
   box as a `Level`. t28a's `570-660` box matches the data (base lo 565 / hi
   660) but the engine produces zero D1 zones -- `extremes.py` defaults to
   `timeframes=("1h",)` (line 43) so it never even anchors D1 pivots, and
   `wyckoff.phase` classifies without emitting a box.
2. **Unsupported timeframes.** `Timeframe` enum = M1/M5/M15/H1/D1
   (`models/candle.py:14`); store derives only M5/M15/H1/D1
   (`store/candles.py:45`). The user's **2H (t28b), 30m (t29f tier), 10m
   (t28h)** are unrepresentable -- the engine can never form those series.
   3 of 9 instances sit on TFs that do not exist.
3. **No recursive drilldown.** The ladder is a single H1<->M5 overlap. The
   user nests up to 4 tiers (1D>2H>15m>10m>5m>1m). There is no mechanism that
   refines the same zone across >=3 TFs down to a 1m origin.
4. **Context ellipses are annotations, not zones.** t28e/g/i are HTF-range
   highlights, not tradeable boxes; nothing in the engine emits or consumes a
   "context range" object, so these can never be reproduced as-drawn.

**Numeric gaps (values seen in data):**

- t28a box `570-660` vs 1D May-Jul-2026 base **lo 565-612 / hi 638-660** ->
  box is VALID; detector output = 0 zones. Miss is recognition, not geometry.
- t28e/g/i ellipse top `720` vs 5m data high **657.8** -> **+9.5% over-draw**
  (loose context circle); on 2026-07-07 5m traded 601.0-607.5, inside it.
- t29f (only checkable on 1h -- 5m/1m native absent for Dec-2025): Dec-30-2025
  demand base **outer wick low 830.0**, consolidation 831-838, rally to 846
  (15:15) then 862 (Dec-31, **+3.9%**). Entry `835` sits in the 833-837 origin
  band; SL `828` is just below the 830.0 outer wick -> **outer-wick SL
  confirmed**. BUT the 1h demand legs (in -4.1% / out +3.9%) are **below the
  extremes 6.0% `leg_pct` floor**, so `extremes.py` anchors no pivot; and the
  30m/1m nesting tiers are unsupported/absent.

**Data limits.** SBICARD has 1d (full), 1h (since 2024-07), 5m (since
2026-05-04). t28 July-2026 marks are 5m/1h-checkable; t29 (Dec-2025) is
1h-ONLY -- the multi-TF refinement it teaches (15m/30m/5m/1m) is intrinsically
unverifiable at 1h resolution. Only trade t31 has a firm year; t28/t29 dates
are price-era guesses. `b8d2_c11` is a foreign reference graphic (no tape).

## Enhancement plan

Prioritized. Recognition only -- none of this claims profitability.

**A. Structural -- add a first-class nesting detector (biggest gap).**

1. New `detectors/htf_nest.py` emitting a `NEST` composite `Level` when a
   same-direction zone overlaps live parent zones across a TF ladder, not just
   H1<->M5. Generalise `ladder.Ladder._rung` (lines 199-206): replace the
   single H1-overlap test with a loop over an ordered TF list
   `[D1, H1, M15, M5]`, counting how many parents the child zone nests inside;
   store `nest_depth` on the level meta and let confluence read it as a
   multiplier. This directly reproduces t28j (5m OB in a 2H/H1 zone) and
   t29f (1m origin in 5m/15m parents).
2. Add an **HTF context-zone** emitter so t28a-style Daily bases become
   `Level`s: reuse `wyckoff._event`/`phase` range logic (band height <
   `range_atr * ATR` -> `lo/hi = min low / max high`) but on D1 and *emit* the
   band as a `RANGE`/`CONTEXT` level (today `phase` only returns a scalar).
   Target: on SBICARD 1D May-Jul-2026 this must emit a box ~=`565-660`
   (matches the drawn `570-660`).

**B. Numeric-threshold tweaks (with TARGET values).**

3. **Timeframe coverage.** Extend `Timeframe` enum + `store/candles.py
   _DERIVED` to add `M30`/`H2`/`M10`, OR add an explicit "nearest supported
   TF" mapping (2H->H1, 30m->M15, 10m->M15) and record the substitution on the
   nest level. Without this, 3 of 9 instances (t28b, t28h, t29f-30m tier) stay
   permanently unrepresentable.
4. **Extremes `leg_pct` for intraday demand.** t29f's 1h demand legs are
   ~4.1% / 3.9%, below the frozen `_DEFAULT_LEG_PCT = 6.0`
   (`extremes.py:42`). Add a per-TF override so intraday anchors form: TARGET
   `leg_pct ~= 3.5` on H1/M15 (the taught fallback is 4.7). This lets an
   `EXT_L` / `OB_BULL` anchor the 830 base.
5. **Nest box tolerance.** When matching a child zone to a parent, use an
   overlap tolerance rather than strict edge equality -- the drawn ellipses
   over-draw by up to +9.5% (t28e). TARGET: accept nesting when child/parent
   overlap >= 50% of the child band OR within `0.25 * ATR` of the parent edge
   (mirrors `ladder.EQ_ATR = 0.25`).

**C. Birth-gate / entry / SL geometry (doc35 gaps).**

6. **Entry = innermost LTF origin, not the parent zone.** For a NEST level,
   arm at the CE (midpoint) of the *innermost* child tier (t29f entry 835 =
   1m origin), not the HTF band. Wire this into `pipeline._entry_flow`
   (lines 304+) where `top.zone` currently feeds the gate.
7. **SL beyond the OUTER WICK of the base**, not ATR/body. t29f SL 828 sits
   below the 830.0 outer wick; the shipped default is an ATR/body-edge stop.
   Add an `sl = outer_wick(base) -/+ 1 tick` path for nest entries.
8. **Birth gate.** Keep the nest born only after the child zone is confirmed
   inside a LIVE parent (extends the existing `ladder` "born on an earlier
   session, first touch" gate). The user's nest is a *refined demand*, so a
   sweep is NOT required at every tier -- do not force the ladder rung-3
   sweep+BOS gate onto nest births; make it an optional confluence bonus.

**Reference the exact params/functions when implementing:**
`ladder.Ladder._rung` / `.grade` (H1<->M5 overlap, `_BULL`/`_BEAR`,
`SWEEP_BARS`, `EQ_ATR`), `wyckoff.htf_phase` / `.phase` / `_event`
(`range_atr`, `window`), `confluence._align` (D1+M15 multiplier),
`extremes._DEFAULT_LEG_PCT=6.0` / `_DEFAULT_TIMEFRAMES=("1h",)`,
`models/candle.Timeframe`, `store/candles._DERIVED`.
