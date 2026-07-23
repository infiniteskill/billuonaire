# compression

Validation of the `compression` feature against EVERY hand-marked instance in
`runs/validate/tools/registry.jsonl` (feature == "compression"). Two instances,
both the **same** HDFCBANK 30m consolidation box re-shown
(`h4242_compression_1`, `h4256_compression_1`). Detectors read:
`app/trader/detectors/compression.py` (coil→PO3 FSM) and
`compression_fade.py` (single-candle doji fade). Numeric checks run on the
native 5m tape `data/long5m/HDFCBANK.csv` (covers 2026-04-27..07-17, so the
14-18 May 2026 window is fully in-window).

Guardrail (RETHINK.md): RECOGNITION (fires on the right candle) != EDGE. The
already-measured record is NEGATIVE for this bundle — `compression BOX_ON_LEVEL
-2.3pp (n=956)`, `PO3_DIST -26.7pp`, `compression_fade` win@3R 31% / exp +0.26R
was later superseded as a mis-built proxy. Nothing below claims profitability;
this is a geometry/recognition audit only.

## Feature notes (structure & validity)

**What the user drew (the mark).** A large square ("range-box" sub_type),
`~760` (bottom) to `~772` (top), spanning ~4 sessions (14/05→18/05) of 30m
chop, sitting just BELOW the 15/05 swing high (~782). Unlabeled: no
entry/SL/target/direction. It is a **macro consolidation RANGE** — accumulation
value area where price overlaps within a band before the next leg. Registry
note: "could alternatively be read as an order-block zone."

**What `compression.py` targets (candle/price geometry).** A *coiled-energy
cluster* over the last `window=12` closed `tf=5m` candles, scored 0..1:
- `contraction` (0.30): mean(range last 4) / mean(range first 4) < 0.6
- `overlap` (0.25): the last 6 candle **bodies** share a common price
  (max(min(o,c)) <= min(max(o,c)))
- `vol_slope` (0.25): linear-regression slope of volume < 0 (drying up)
- `nr_cluster` (0.20): >=2 of last 4 candles are narrowest-of-7 or inside bars

Score >= **0.7** ⇒ `box = (min low, max high) of the LAST 6 candles`, pushed to
`ctx.day.po3["leg"].set_box(...)` only while that FSM is IDLE/DISTRIBUTION.
Every tick also `fsm.step(...)`. **Evidence:** `PO3_DIST` (strength 0.85, dir =
fsm.true_direction, energy = box_height × `expansion_factor` 2.5) when the FSM
reaches DISTRIBUTION; `BOX_ON_LEVEL` (0.75) when the box overlaps an
ACTIVE/TESTED OB/FVG level. Defaults: `{tf:5m, window:12, expansion_factor:2.5}`.
Lifecycle: dedupe per (event, box_ts); `on_session_end` clears (box_ts is
intraday). **No retest rule, no SL, no explicit death** beyond the FSM.

**What `compression_fade.py` targets.** A *single* compression candle: `body <=
0.35*range` AND `upper_wick >= 0.2*range` AND `lower_wick >= 0.2*range` (a
symmetric doji). If it breaks within the next `break_window=3` closed candles,
FADE the break: break-of-high ⇒ SHORT (sl=break high), break-of-low ⇒ LONG
(sl=break low). Entry = break-candle close; `zone=(min(sl,entry),max)`; ttl 2;
strength = coil quality (tighter body + bigger min-wick). SL floor annotated
`0.15*ATR` (executor applies; the literal `sl` stays the break extreme).
Continuum window (never session-scoped); first bar of the whole series is never
a candidate (`bar0` guard). Defaults `{tf:5m, break_window:3, body_frac:0.35,
wick_frac:0.2, sl_atr_floor:0.15}`.

**HOW/WHEN each fires vs the mark.** Both fire *abundantly inside* the marked
window, but on a **different-scale object**: `compression.py` = a 30-min coil
(6-candle box) armed for expansion; `compression_fade.py` = a per-candle doji
break-fade. Neither is a multi-session RANGE rectangle.

**CONFLUENCE.** The mark's real relatives in the codebase are the RANGE / value-
area concept and `orderblock`/`ob_taught` (the registry itself flags "could be
an OB zone"). `compression.py`'s only confluence hook is `BOX_ON_LEVEL` (box
overlapping an OB/FVG level) — the closest thing to "this consolidation sits on
a zone", but gated to a 6-bar box, so it never fires for the macro range.

## How the user draws it

Rectangle tool (Zerodha "RECTANGLE"), 30m HDFCBANK. Left edge at the start of
the sideways chop (~14/05 midday, after the 14/05 11:15 impulse candle that ran
752→775), right edge where the range resolves (~18/05). Top of the box at the
overlap **resistance** (~772, where 14/05 & 18/05 candles topped 773-774),
bottom at the overlap **support** (~760). Drawn *below* the immediate swing high
(15/05 ~782) — i.e. the box is the value/accumulation band, not the spike. No
entry/SL/target annotated: a context zone, "compression building", read
alongside the OB/liquidity story, not a standalone trade ticket.

## Accuracy verdict

**pct_match = 0%** (hit / (hit+partial+miss), uncheckable excluded).
Counts over ALL instances: **hit 0 · partial 2 · miss 0 · uncheckable 0** (n=2).

Per-stock: **HDFCBANK 0/2 hit, 2/2 partial** — both records are the SAME
760-772 box (h4256 is h4242 re-shown; both logged, no silent drop).

Why **partial** (not miss, not hit): the detectors ARE recognition-positive —
they fire repeatedly *inside* the exact 14-18 May window and one micro-box
aligns to the box's TOP edge — but they never reproduce the mark's actual object
(one macro range rectangle), its birth, its scale.

**Structural + NUMERIC gaps (values seen in real 5m tape):**
- **Scale.** User box = **12.0pt** (760→772) = **1.57%** of ~766 = **6.7×** mean
  5m range. `compression.py` emitted **17** boxes in the same window, each the
  last-6-candle extremes, height **1.45–5.25pt (mean 3.77pt = 0.49% = 2.1×
  ATR5m)** — only **~31%** of the user height. `compression_fade` drew **no**
  box (40 doji-fade signals instead).
- **Box edges.** Top ~772 **matched within ~1pt / 0.13%** (05-14 12:15 micro-box
  hi 773.00; several ~771.45 — a real coil cluster at resistance). Bottom **760
  never appears as a box edge** (nearest micro-box lo **764.00** on 05-18, **+4pt
  off**; the 18/05 session low actually pierced to 751). So the detector captures
  the resistance rail but not the support rail as one object.
- **Fragmentation.** 1 hand-drawn zone ⇒ **17 compression.py micro-boxes + 40
  compression_fade coil-fades** across the window. No aggregation to a single
  range.
- **Birth.** User birth = multi-session overlapping chop below a swing high.
  Detector birth = score>=0.7 30-min coil (compression.py) / single doji
  (compression_fade). No sweep+BOS gate, no "range under swing high" concept.
- **Object type.** compression.py = coil→expansion FSM (emits directional
  PO3_DIST energy = breakout thesis). compression_fade = mean-reversion doji
  fade. The mark = a neutral consolidation container. All three disagree on what
  "compression" even *is* here.

**Data limits.** Rare good case: the box window is native-5m in-window, so every
number above is measured on real HDFCBANK tape, not inferred. The mark's YEAR is
the 2026 label on the chart itself (dev-unvalidated, not in ytrades/results) —
but the price era (~750-782) uniquely matches May-2026 HDFCBANK, so the window is
firm. 30m marks were validated by resampling 5m→30m (NSE 09:15-anchored bins).

## Enhancement plan

Priority ordered. The headline gap is **there is no range/consolidation-box
detector at all** — `compression.py` is a coil FSM, `compression_fade.py` is a
doji fader; both are correct-but-different objects. The user's "compression" ⇒
CONSOLIDATION RANGE needs its own detector.

1. **[STRUCTURAL — new detector] `range_box` / consolidation aggregator.** Add a
   detector that, instead of `set_box(min(last6.low), max(last6.high))`, walks a
   variable-length window and closes a box when: N>=`min_bars` consecutive
   candles overlap within a band whose height <= `range_atr_mult`×ATR and whose
   extremes are re-tested >=`min_touches` times. Emit `zone=(range_low,
   range_high)` spanning the WHOLE cluster (not 6 bars). TARGET params tuned to
   THIS mark: `min_bars≈12` (the 760-772 box was ~40 30m bars ⇒ still >=12 on
   any tf), `range_atr_mult≈4–7` (measured 6.7×ATR5m; set ceiling ~8×),
   `min_touches>=2` per edge. This is the object the user actually draws.

2. **[NUMERIC-THRESHOLD] widen `compression.py` box beyond 6 candles.** The
   single line `fsm.set_box(min(c.low for c in last6), max(c.high for c in
   last6), ...)` caps every box at 30 min. Replace `last6` with a
   contraction-run lookback (grow the box backward while `overlap` still holds
   over the last-6 bodies test). TARGET: box height should reach ~1.5% / ~6×ATR
   (the measured user scale), not the current 0.49% / 2.1×ATR.

3. **[BIRTH-GATE / CONFLUENCE] "range under a swing high".** Gate the range_box
   birth on structure: the band's top must sit at/under a recent swing high
   (from `extremes.py`) and the band must follow an impulse leg (the 14/05 11:15
   +23pt candle). Reuse `compression.py::_box_on_level` logic but for the macro
   box — a consolidation ON an OB/FVG level (BOX_ON_LEVEL) is the confluence the
   registry itself names ("could be an OB zone"). This distinguishes an
   accumulation range from random chop.

4. **[EDGE — do NOT ship as-is] direction.** `compression.py` emits directional
   `PO3_DIST` (breakout) energy; `compression_fade.py` fades. The user's box is
   NEUTRAL until it resolves. Measured record kills both directional priors
   (BOX_ON_LEVEL -2.3pp, PO3_DIST -26.7pp). Enhancement: the range_box should
   emit a **zone only** (no direction) and let downstream sweep/BOS logic pick
   the break side — never bake in the coil's expansion bias.

5. **[SL geometry — carry doc35 forward] outer-wick, not body.** If the range
   ever feeds a trade, the SL belongs beyond the OUTER WICK of the range edge
   (e.g. 18/05 wick to 751 below the 760 rail), not the body edge.
   `compression_fade` already uses the break EXTREME (good, wick-inclusive);
   `compression.py` emits no SL. A range_box detector should expose
   `edge_low_wick / edge_high_wick` for the executor, matching the doc35
   outer-wick rule rather than the shipped body-edge SL.

**Reference points:** `compression.py` L59 (`set_box` 6-candle cap — widen),
L66-74 (`_score` — reuse contraction/overlap for range detection), L88-101
(`_box_on_level` — confluence template); `compression_fade.py` L90-102
(`_is_compress` doji test — orthogonal, keep for micro-fade), L75-78 (break
extreme as SL — the right SL object). New detector should register as e.g.
`range_box` (base.py `@register`).
