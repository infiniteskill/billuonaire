# compression — precision audit

Detector `compression` (`app/trader/detectors/compression.py`). Events
`BOX_ON_LEVEL` (0.75, box overlaps an ACTIVE/TESTED OB/FVG level) and
`PO3_DIST` (0.85, coil→PO3 FSM reaches DISTRIBUTION). RECOGNITION/PRECISION
audit only — never edge/profit. Precision = of all firings, how many are the
REAL taught object (a multi-session consolidation RANGE sitting on a zone).
Recall is already ~100% (41-TOOLS doc: both marks partial-match, detector fires
abundantly inside the window). Data: `runs/validate/precision_study/evidence.parquet`
(8 stocks × ~17d 1m). Marks: `runs/validate/tools/registry.jsonl`.

## Firing picture (over-fire)

- **460 total fires, 100% `BOX_ON_LEVEL`.** `PO3_DIST` fires **0×** — the leg
  PO3 FSM never reaches DISTRIBUTION on any of the 8 stocks over the window. So
  every compression firing in this study is the box-on-level spring, none the
  distribution-expansion thesis.
- **All 8 stocks fire.** VOLTAS 72 · HAVELLS 70 · HEROMOTOCO 62 · HDFCBANK 56 ·
  SBILIFE 54 · DABUR 54 · TITAN 54 · DLF 38.
- **DENSITY = 3.38 fires / stock / session** (460 / (8×17)); per-stock range
  **2.24–4.24 fires/session**. For an object the user draws roughly **once per
  multi-session chop** (~once every several sessions per stock), this is
  ~10–20× over-fired.
- Strength is **constant 0.75** (no conviction spread — nothing separates a
  graze from a real containment). Direction is inherited from the level:
  259 LONG / 201 SHORT.
- **Box scale is wrong.** Median box width **2.0× ATR / 0.47% of price**; only
  **1.5%** of boxes reach ≥4× ATR and only **5.2%** reach ≥1.0% width. The
  taught object (registry `h4242`) is a **6.7× ATR / 1.57%** multi-session
  range. So **~98.5% of fires are the wrong-scale 6-candle micro-coil**, not the
  drawn macro range.

Two mechanical multipliers sit on top of the loose birth gate:

- **Level fan-out (×1.93).** 460 fires come from only **238 distinct
  box-candles**; **133 of 238** box-candles emit >1 copy (up to 5). The
  emission is one Evidence *per overlapping level* → the same box at the same
  instant is counted once per OB/FVG it grazes.
- **Candle fragmentation.** Those 238 box-candles collapse to **175 distinct
  physical coils** / **122 (stock,session) episodes**; **48% of fires land
  within 5 min of a prior fire** — a persisting coil re-fires every candle it
  holds because the dedup key is the ever-changing `box_ts`.

Net: **~62% of the 460 fires are redundant copies** of ~175 physical coil
episodes, which are themselves ~98% the wrong scale.

## In-window precision

**In-window marks = 0.** Both `compression` marks (`h4242`, `h4256`) are the
**same** HDFCBANK 30m box 760–772 dated **14/05–18/05 2026**, outside the
1m study window **2026-06-25 … 2026-07-17**. Precision-by-match is therefore
**uncheckable (n=0)** — no honest matched-fire / recall number can be computed
on this dataset.

- **Recall:** ~100% by construction (41-TOOLS doc: detector fires repeatedly
  inside the exact 14–18 May window; both marks graded *partial*, not *miss*).
- **Precision proxy = DENSITY:** 3.38 fires/stock/session vs a taught object
  that appears ≪1×/session ⇒ heavy over-fire. With strength pinned at 0.75 and
  98.5% of boxes at the wrong 2× ATR scale, the fraction of firings that are the
  REAL taught object is low; the redundant-copy fraction (~62%) is definitively
  **not** separate taught objects.

## Over-fire root cause (code)

1. **Loose birth gate — `_score >= 0.7` (L56-57, 79-87).** 0.7 is satisfiable
   by **any 3 of 4** booleans (contraction 0.30, overlap 0.25, vol_slope<0 0.25,
   nr_cluster 0.20 → e.g. contraction+vol+nr = 0.75). Overlapping bodies +
   drying volume + a narrow bar is *ordinary intraday chop*, so the gate opens
   constantly.
2. **Geometry caps the box at 6 candles — `min/max of last6` (L59).** Every box
   is the last-6-candle extremes ⇒ ~2.0× ATR / 30 min, structurally unable to
   reach the taught 6.7× ATR multi-session range. 98.5% of fires are the wrong
   object *by scale*.
3. **Level fan-out — list comprehension emits one Evidence per level (L105-112).**
   `_seen` is keyed `(event, box_ts)` and added only *after* the whole list
   (L113-114), so a box overlapping N levels emits N copies before dedup. ×1.93.
4. **Fragmentation — fresh `box_ts` every candle (L59, dedup L102).**
   `set_box(..., candles[-1].ts)` stamps a new `box_ts` each qualifying candle;
   dedup is by exact `box_ts`, so the *same persisting coil* re-fires every
   candle. 48% of fires are within 5 min of the prior.
5. **Any-overlap containment — `lv.zone[0] <= hi and lo <= lv.zone[1]` (L112).**
   A 1-tick edge graze counts as "box on level"; there is no requirement that
   the box actually *sits inside* the zone.

## The precision tune + expected effect

**THE single highest-leverage precision tune — collapse the emission unit to
one contained coil-on-level episode.** Rewrite the `_box_on_level` emission
(L101-115) so a physical coil that sits on a level produces **exactly one**
`BOX_ON_LEVEL`, gated on real containment:

- **Dedup by spatial box identity, not `box_ts`.** While a coil box overlaps
  its own previously-emitted box in the session, do **not** re-fire (extend the
  live box instead). Kills the 48%-within-5-min fragmentation.
- **Emit one evidence per box, not per level.** Pick the single strongest /
  nearest overlapping ACTIVE/TESTED level (highest state, smallest centre
  distance) and emit once. Kills the ×1.93 fan-out.
- **Containment floor — require box∩level ≥ 0.5 × box height** (replace the
  any-overlap test L112). The box must *sit on* the zone, not graze its edge —
  this is the taught "consolidation ON an OB/FVG zone" confluence and directly
  raises object-fidelity.

**Numeric target:** 460 → **~150–175 fires (−62% to −67%)** from the two dedups
alone (measured: 238 distinct box-candles → 175 distinct physical coils), with
the containment floor trimming the edge-graze subset further. **Zero recall
loss** — every collapsed fire is a duplicate of a coil already emitted, and the
121 remaining episodes still cover every window the marks fall in.

**Why this and not a width gate:** raising the box to the taught 6.7× ATR scale
requires *widening the 6-candle lookback* (41-TOOLS enhancement items 1–2) — a
recognition **rebuild**, and a bare `width ≥ 4× ATR` gate on the current
6-candle geometry would nuke recall (only 1.5% of boxes qualify). That is out
of the precision lane. The dedup+containment tune stays in-lane: **fewer,
higher-conviction firings** — one distinct contained coil-on-level event per
episode instead of ~2.6 redundant copies — so each firing's grade-stack that
feeds the high-grade tier (REFINE iter-6: high-grade +4.57R) is real rather than
inflated by double-counting.

**Deeper follow-up (recognition lane, not this tune):** widen the box lookback
to span the whole contraction run and add a "range under a recent swing high"
birth gate (extremes.py) so the emitted object is the multi-session range the
user actually draws (41-TOOLS items 1–3).
