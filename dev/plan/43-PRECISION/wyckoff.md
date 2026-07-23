# wyckoff — precision audit

Detector `wyckoff` (`app/trader/detectors/wyckoff.py`), events `PHASE / SPRING /
UPTHRUST`, features `wyckoff_phase + spring_utad`. RECOGNITION/PRECISION only —
no edge/profit claims. Data: `runs/validate/precision_study/evidence.parquet`
(8 stocks, sessions 2026-06-19..2026-07-17). Recall is already ~100%; this doc is
only about how many of the firings are the REAL taught object.

## Firing picture (the over-fire)

Total wyckoff fires: **1430**. Composition:

| event | fires | share | strength |
|---|---|---|---|
| PHASE (continuation) | **1424** | 99.6% | 0.5 |
| UPTHRUST | 4 | 0.3% | 0.8 |
| SPRING | 2 | 0.1% | 0.8 |

Per-stock fires + density (fires / session):

| stock | fires | sess | density/sess |
|---|---|---|---|
| HDFCBANK | 239 | 19 | 12.6 |
| TITAN | 213 | 19 | 11.2 |
| HEROMOTOCO | 188 | 16 | 11.8 |
| DABUR | 174 | 16 | 10.9 |
| VOLTAS | 165 | 16 | 10.3 |
| SBILIFE | 162 | 16 | 10.1 |
| DLF | 146 | 16 | 9.1 |
| HAVELLS | 143 | 16 | 8.9 |

Overall **~10.7 fires per stock-session**. The over-fire is entirely the PHASE
continuation Evidence — it fires on a mean of 10.9 (max 26) 5m candles per
stock-session. It **flip-flops direction**: 741 LONG / 683 SHORT overall, and in
**46% of stock-sessions BOTH a LONG and a SHORT PHASE fired on the same day**.
That both-ways cadence is the signature of a per-candle trend follower tracking
noise, not a Wyckoff phase recognizer. The real SPRING/UPTHRUST event surface is
6 fires total (0.4% of all firings).

Taught cadence for reference: the user marks ~1 macro accumulation/distribution
phase per stock across a whole multi-year chart. 160–240 fires per stock over 17
days is a **~1000x over-fire** vs the taught object's natural rate.

## In-window precision (honest limits)

**Checkable in-window marks = 0.** Of the 13 registry marks (12 `wyckoff_phase` +
1 `spring_utad`), only 2 are attached to one of the 8 study stocks; the other 11
are schematics (`stock=None`) or foreign (TSLA) with no date/axis. Both stock
marks are macro **SBILIFE 4h boxes**:

- `box HI 1500 - LO 1300`, date_approx *Jun-2024 – Oct-2026* — a multi-year
  accumulation base. The span brackets the window, but SBILIFE trades **1738–1878**
  in-window, nowhere near 1300–1500.
- `box HI 2080 - LO 1980`, date_approx *Feb-Apr 2026* — before the 17d window, and
  again above/below the in-window price band.

So neither mark is a discrete, price-reachable object inside 2026-06-25..07-17.
**Matched fires against either box geom = 0** (no PHASE fire lands in 1300–1500 or
1980–2080; price never visits those bands). Precision must fall back to the
**density proxy**.

Density-proxy verdict: the PHASE object emitted is an *out-of-range 5m trend
continuation* — the **opposite market state** from the taught object (an *in-range*
accumulation/distribution consolidation box). The code even computes the
ACCUM/DISTR label internally (L131-133) but **never emits it as Evidence**. So the
real-taught-object fraction of the 1424 PHASE fires is **≈ 0%**, and the 6
spring/upthrust events have **zero hand-marked real-tape counterpart** to match
against (the sole `spring_utad` is a schematic). Recall of the taught macro box is
also ~0 on this surface — but that is the structural scope gap documented in
41-TOOLS, not the precision lever here.

## Over-fire root cause

`detect()` L69–81 appends a continuation Evidence on **every** 5m candle where
`phase() ∈ {MARKUP, MARKDOWN}` with `conf ≥ 0.5` AND a nearby ACTIVE/TESTED M5
swing exists. Two defects:

1. **Wrong object emitted.** The emitted PHASE is the *out-of-range trend* branch
   (`|net over 40×5m closes| > ATR`, `conf = min(1,|net|/3ATR)`). The taught
   `wyckoff_phase` is the *in-range* accumulation/distribution range/box. The
   detector emits Evidence ONLY for MARKUP/MARKDOWN and discards the ACCUM/DIST
   label — so no firing can ever be the taught object by construction.

2. **No event anchor / no episode dedup — a bare 5m trend gate.** The birth
   condition is just `conf ≥ 0.5` (= `|net| > 1.5·ATR` over ~3.3h of 5m tape) plus
   a swing-within-1.5·ATR. **Direction is set by the raw 5m net sign**, not by any
   preceding Wyckoff event — a "MARKUP/LONG continuation" fires with **no spring at
   all**. Because a trend persists across consecutive candles and dedup is only
   per-candle (`self._seen` cleared only at session end), it **re-fires bar after
   bar** through the whole leg; and because each stock both rises and falls in
   different 3.3h windows over 17d, it emits **both directions** (46% of
   stock-sessions fire both). That is the whole ~10.7/session over-fire.

The `conf ≥ 0.5` gate (L69) is the loose birth gate; `_continuation_zone`
availability is the only thing capping it below one-per-candle.

## The precision tune + expected effect

**Single highest-leverage tune — anchor the PHASE continuation to a recent,
direction-consistent spring/upthrust event (a real Wyckoff birth), replacing the
bare 5m-trend gate.**

Concrete change at `detect()` L69 — add to the emit condition:

```
self._last_event is not None
and self._last_event[1] >= candles[-window].ts          # event within last 40×5m bars
and ((name == "MARKUP"   and self._last_event[0] == "SPRING")
  or (name == "MARKDOWN" and self._last_event[0] == "UPTHRUST"))
```

i.e. a MARKUP/LONG continuation may fire **only if a SPRING swept the band floor in
the last 40 bars** (accumulation confirmed → genuine markup leg out of it), and
MARKDOWN/SHORT only after an UPTHRUST. This is doc-35's "phase is born from a
sweep+BOS, not mid-air tightness" made into one gate, reusing the `_last_event`
memory the code already maintains.

**Numeric target / expected firing reduction.** Only **6** spring/upthrust events
fired across all 8 stocks in 17d; each now licenses continuation for at most the
≤40 candles after it AND only while price is out-of-range trending the matching
direction. PHASE fires collapse **1424 → order of ≤30 total (≥98% reduction)**,
density **10.7 → <0.25 fires/session**, and the both-direction-same-session rate
(46%) drops to near zero since direction is pinned to the event, not the noise
sign.

**Expected effect on the high-grade tier.** Today the conjunction stack is flooded
with ~1400 both-way 0.5-strength PHASE votes that add near-zero-precision mass to
almost every grade window (diluting the +4.57R high-grade tier from iter-6). After
the gate, every surviving wyckoff vote is anchored to a real detected
liquidity-grab, so the **real-taught-object fraction of wyckoff's (now tiny)
emissions rises from ~0% toward ~100%**. When wyckoff then co-occurs in a
high-grade conjunction it genuinely means "a swept-then-continued Wyckoff leg,"
sharpening the tier instead of padding it — fewer, higher-conviction firings, more
of each firing's grade-stack real. (Recall unmeasurable in-window: n=0 checkable
marks; the change trades unverifiable trend-continuation breadth for event-anchored
precision, consistent with recall already ~100% on the recognizable surface.)
