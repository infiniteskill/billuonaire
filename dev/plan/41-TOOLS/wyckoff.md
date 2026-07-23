# wyckoff

Detector: `app/trader/detectors/wyckoff.py` (`WyckoffDetector`, `name="wyckoff"`).
Features validated: `wyckoff_phase` (12 marks) + `spring_utad` (1 mark) = **13 instances, ALL covered** (no silent drops).

## Feature notes (structure & validity)

**Candle / price geometry the code targets.** Two objects, both scoped to the
intraday `tf=5m` surface:

1. **Spring / Upthrust events** (`_event`, emitted by `detect`). Takes the last
   `window+1` (=41) candles. The prior 40 form a band `lo=min low, hi=max high`;
   the band must be *tight*: `hi-lo < range_atr*ATR` (=`3.0*ATR`) or nothing
   fires. On the latest candle, with `volume > 1.5 * mean(vol of prior 20)`:
   - **SPRING** = `low < lo` (wick pierces band floor) AND `close > low+range/2`
     (closes in upper half) -> LONG, strength 0.8, ttl 24, zone `= (lo-tick, lo+tick)`.
   - **UPTHRUST** = `high > hi` AND `close < mid` -> SHORT, strength 0.8, ttl 24,
     zone `= (hi-tick, hi+tick)`. Deduped per `(ts,event)`; the last event is
     kept in `_last_event` for `phase()`.

2. **Phase classifier** (`phase` -> `(name, conf)`, NOT Evidence). On the last
   `window` (=40) candles: `<window` or no ATR -> `UNCLEAR 0.0`.
   - band `hi-lo < 3*ATR` (in-range): if a spring/upthrust fired within the last
     10 candles -> `ACCUMULATION/DISTRIBUTION 0.7`, else `UNCLEAR 0.4`.
   - out-of-range: `|net close change| > ATR` -> `MARKUP/MARKDOWN`, conf
     `min(1, |net|/(3*ATR))`; else `UNCLEAR 0.0`.
   `MARKUP/MARKDOWN` with conf >= 0.5 also emits ONE continuation Evidence 0.5
   ttl 12, zone = latest ACTIVE/TESTED same-direction M5 swing within `1.5*ATR`
   of the M5 close (`_continuation_zone`); none qualifying -> no emission.
   `htf_phase` is a separate D1 read: net close % over last 10 D1 candles,
   `>+2% MARKUP / <-2% MARKDOWN`, conf `min(1,|pct|/5)`.

**HOW / WHEN it fires.** ONLY on 5m tape, ONLY inside a band `< 3*ATR(5m)` wide
(~a 3.3-hour micro-consolidation), and a phase label needs a recent 5m spring/
upthrust. **No Accumulation/Distribution Evidence is ever emitted** — `detect`
appends evidence only for `MARKUP/MARKDOWN`; the phase() ACCUM/DIST labels are
internal state consumed elsewhere, never a drawable box.

**CONFLUENCE.** The continuation Evidence deliberately anchors to a stable M5
swing level (`ctx.levels`, `SWING_L`/`SWING_H`, ACTIVE/TESTED only, trap extremes
excluded) so it clusters with other detectors at that swing instead of drifting
per candle. Spring/upthrust zones are `edge +/- 1 tick` — pinned to the band
edge, designed to co-locate with sweep / liquidity-pool marks at the same level.

**Params / defaults:** `tf=5m, window=40, range_atr=3.0, vol_sma=20`.

## How the user draws it

Every one of the 13 marks is at a scale the detector does not operate on:

- **Macro HTF context boxes** (t32b_1/2, SBILIFE 4h): a rectangle spanning
  *months to years* — a multi-month base at a discount (ACCUMULATION, long) or a
  premium topping range after markup (DISTRIBUTION, short). Box drawn on the
  swing extremes of the whole range; `entry/sl/target = null` (pure context, not
  a trade). Birth = the range simply *existing* on the HTF tape, not a
  sweep+event trigger.
- **Textbook schematics** (wyk1/2/3/5/6, c37, c38, c39_1/2, c29): reference
  diagrams (Alchemy/StockCharts/WyckoffAnalytics/ICT). Full Phase A-E event
  vocabulary — PS/SC/AR/ST/Spring/Test/SOS/LPS on the accumulation side,
  PSY/BC/AR/UT/UTAD/SOW/LPSY on distribution — plus the ICT re-labelling
  (AMD = Accumulation/Manipulation/Distribution, PO3 = Power-of-3 candle OHLC).
  The `spring_utad` mark (c29) is a pair of faint liquidity-grab arcs at the two
  range extremes.
- **Foreign real-tape example** (wyk4, TSLA 4h): a distribution box on Tesla used
  as a teaching example — same macro-4h scale, no NSE tape in the repo.

The through-line: the user draws **macro HTF ranges and full event schematics**;
the detector codes **one intraday 5m event pair + a 40-bar micro-phase label**.

## Accuracy verdict

**pct_match = 0.0%** (hit / (hit+partial+miss) = 0/2). Only 2 of 13 marks sit on
real NSE tape; both are macro frames the detector cannot reproduce.

| verdict | count |
|---|---|
| hit | 0 |
| partial | 1 |
| miss | 1 |
| **uncheckable** | **11** |
| total | 13 |

**Per-stock breakdown.**
- **SBILIFE** (2 marks, only checkable stock):
  - *Accumulation, 2024, box 1300-1500* (t32b_1) -> **MISS**. Box is REAL and the
    mark is accurate: 2024 H1 base ran lo **1307.7** (Jun) / hi **1569.3** (Mar),
    so LO is within **0.6%** and HI within **4.4%** of the true extremes. But the
    detector emits no box, and even reconfigured to D1 the in-range gate fails
    (below).
  - *Distribution, Jan-Feb 2026, box 1980-2080* (t32b_2) -> **PARTIAL**. Box is
    REAL and accurate: Jan-Feb top hi **2132.0** (Feb-23), base **1951-1955**, so
    HI within **2.4%**, LO within **1.5%**. Detector at the top returns UNCLEAR;
    only after markdown starts does it (on D1) return **MARKDOWN conf 1.00** — the
    correct SHORT direction but the WRONG phase label and no premium box. That
    directional overlap is the only reason it is partial, not miss.
- **11 uncheckable**: 9 pure schematics (no symbol/tf/axis), 1 foreign (TSLA), 1
  faint-arc schematic (the sole `spring_utad`). All logged with reasons; none
  dropped.

**Structural gaps.**
1. **Scope/timeframe mismatch (root cause of both misses).** wyckoff.py is an
   intraday 5m detector (`window=40` = ~3.3h). Every hand mark is a macro 4h /
   multi-month / multi-year frame. The detector has **no HTF/macro
   accumulation-distribution box concept** and never emits a phase Evidence at
   all.
2. **No event vocabulary beyond spring/upthrust.** The schematics teach
   SC/AR/ST/SOS/LPS/PSY/BC/UT/UTAD/SOW/LPSY; the code models exactly 1 of ~7
   accumulation and ~7 distribution events.
3. **The coded spring/upthrust firing surface has ZERO real-tape marks.** The one
   `spring_utad` instance (c29) is a schematic; no hand-marked 5m spring/upthrust
   exists in the whole registry to validate the event geometry against.

**NUMERIC gaps (values seen in data).**
- **In-range band gate rejects macro ranges.** `range_atr=3.0` requires
  `band < 3*ATR`. Measured on D1:
  - Accumulation window (end Jun-2024): band **191.1pt = 5.84x ATR14 (32.7)**;
    needs `<3xATR = 98pt`. Gate REJECTS -> falls to net-change: net **+31 < ATR**
    -> **UNCLEAR 0.0** (never ACCUMULATION).
  - Distribution window (end Feb-2026): band **180.5pt = 4.96x ATR14 (36.4)**;
    needs `<109.2pt`. Gate REJECTS -> net **-30.2 < ATR** -> **UNCLEAR 0.0** at the
    top; by end-Apr net **-218 -> MARKDOWN conf 1.00** (label flips, one leg late).
  A macro Wyckoff range is naturally **~5-6x ATR** wide; the 3.0 threshold is
  calibrated for a 3.3h micro-coil.
- **Volume gate misses the macro UTAD.** The true Feb-23-2026 top candle
  (H2132 > prior range hi 2110, closes below its mid) fails the event because
  `vol 998,892 < 1.5*SMA20 (1,688,060)` — the macro upthrust simply is not a
  relative-volume spike vs a lookback that already contains spikes. An earlier
  minor poke (2026-01-07) *does* register as an upthrust, i.e. the gate fires on
  noise and skips the real event.

**Data limits.** Only SBILIFE has NSE tape for these marks: daily 2017-2026 (full)
plus 5m native from **2026-04-27** — which starts **56 days AFTER** the Jan-Feb
2026 distribution top, so the top is uncheckable on native 5m. No 1h/4h file for
SBILIFE exists despite the registry's `data_avail` note claiming 1h. Per RETHINK,
only trade t31 has a firm year; the t32b context spans are label-year guesses, so
exact dates are approximate (I used 2024 H1 for accumulation, Jan-Feb 2026 for the
distribution top per the daily tape). RECOGNITION of the boxes is confirmed
(they exist, accurately drawn); this says NOTHING about edge/profitability.

## Enhancement plan

Prioritized. Note: RETHINK.md already measured `wyckoff PHASE +4.6pp (n=4376,
sub-toll)`, `SPRING +38pp on n=8 (unreliable)`, and `UPTHRUST -9.2pp (NEGATIVE)`
— so treat the SHORT/upthrust path as unproven-to-negative and do NOT claim edge
from any change below. These are RECOGNITION fixes only.

**1. Structural — add an HTF macro-phase surface (highest impact; fixes both
misses).** The single reason pct_match=0 is that the detector has no macro object.
Add an HTF box classifier alongside the 5m one:
   - Run `phase()` geometry on `D1` (and/or a synthesized 4h) with a *macro*
     window (`window~=40 D1` for the ~2-month distribution top; a longer
     `~=120 D1` for multi-month/year bases). Emit an actual Evidence carrying the
     macro band `(lo,hi)` = `min low / max high` of the range so it is a drawable
     box, not just internal state.
   - Reference: generalise `_DEFAULTS` to a per-instance `tf`/`window`, and make
     `detect()` emit a phase-box Evidence for `ACCUMULATION/DISTRIBUTION` (today
     it only emits for `MARKUP/MARKDOWN` at L69-81).

**2. Numeric-threshold — raise / decouple the in-range band gate.** With
`range_atr=3.0`, both real macro ranges (5.84x and 4.96x ATR) are rejected.
   - TARGET: for the HTF phase surface use **`range_atr ~= 6.0`** (admits the
     measured 5.84x accumulation and 4.96x distribution bands; `_band_max` at
     L56-57). Keep the intraday 5m instance at 3.0. Validate against the two
     SBILIFE windows: band 191.1 < 6*32.7=196.2 (passes) and 180.5 < 6*36.4=218
     (passes).
   - The out-of-range `MARKUP/MARKDOWN` `|net|>ATR` test (L136) is fine for
     trend, but on the macro surface a *ranging* top nets near-zero (measured
     net -30.2, +31) — which is exactly why in-range must be widened, not the
     net test.

**3. Numeric-threshold — relative-to-range volume for the macro UTAD/spring.**
The `vol > 1.5*mean(prior 20)` gate (L104-106) skips the real Feb-23 top
(998,892 vs 1.5xSMA 1,688,060). For HTF events, gate on volume **relative to the
range's own average** or drop the hard vol gate to a soft strength multiplier so
a low-relative-volume-but-structurally-valid UTAD still marks (structure first,
volume as a booster, mirroring how `volume` VSA is a colocated strength boost).
TARGET: replace the binary `1.5x` with `strength *= clamp(vol/SMA, 0.6..1.0)`.

**4. Birth-gate / confluence — anchor phase to the sweep, not just tightness.**
doc35's taught geometry says a Wyckoff turn is born from a **sweep + BOS**, not
mid-air tightness. The current birth = "band < 3*ATR + a spring in last 10". Add:
require the spring/upthrust wick to actually sweep a `ctx.levels` liquidity
extreme (EXT, not fractal furniture) before the phase upgrades to
ACCUM/DIST 0.7 — reuse the `_continuation_zone` pattern (ACTIVE/TESTED,
trap-extremes-excluded) at L94-96 to pull the swept level. This raises specificity
of the ONE event surface the detector has, ahead of trying to code the full A-E
schematic vocabulary (deferred; schematics are unverifiable anyway).

**5. Data — backfill 4h/1h SBILIFE and pre-Apr-2026 5m** so the distribution top
(Jan-Feb 2026) and any real spring/upthrust events become checkable on the
detector's native surface. Until then the coded event geometry has zero
real-tape validation.
