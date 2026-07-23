# sweep

Validation of detector `app/trader/detectors/sweep.py` (class `SweepDetector`,
`name="sweep"`) against **every** hand-marked `sweep` instance in
`runs/validate/tools/registry.jsonl` (20 instances across 6 charts/stocks).
Per-instance records: `runs/validate/tools/val_sweep.jsonl`.

Guardrail honoured: this validates **RECOGNITION** (does it fire on the candle
the user drew, at the right price, right direction) — **not EDGE**. Nothing here
claims profitability. Per RETHINK.md, only t31 SBILIFE has a firm year; every
other date/year is a price-era guess, so several "gaps" below are registry
date/year mislabels, not detector faults.

## Feature notes (structure & validity)

**What the user's `sweep` mark is.** A single price line or pivot at a resting-
liquidity pool (equal highs/lows, a prior swing high/low, a prior-day high) that
price **spikes through then rejects** — a stop-run: wick pokes beyond the level,
candle closes back on the origin side. HIGH pool swept -> the move that follows
is DOWN (short); LOW pool swept -> UP (long). Labels seen: "LIQUIDITY SWEEP",
"ALL SL TAKEN BY BANK AS LIQUIDITY SWEEP", "liquidity sl taken", "UTAD upthrust".

**What the code detects.** `sweep.py` is **evidence-only** — it does not scan raw
candles. It reads `ctx.levels` and fires directional `Evidence` the instant a
`Level` flips to `LevelState.SWEPT` on the latest closed candle (`_episode`,
`sweep.py:85-99`). The SWEPT transition itself is produced by `LevelEngine._step`
(`engine/levels.py:201-204`):

> `wick_beyond AND close on origin side` — "wick trades beyond the far edge AND
> close is fully back on the origin side" (wick-through-close-back).

Plus a 2-candle break-then-reclaim path (`levels.py:190-198`): a close **beyond**
the far edge arms `PENDING_BREAK`; if the **next** close comes back on origin,
that also emits SWEPT. This is exactly the user's geometry, and the 2-candle path
is what catches intraday sweeps whose poke bar closes beyond and only the *next*
bar reclaims (observed live in TITAN t23 1h and DABUR t27 1h).

- **Direction** (`sweep.py:70`): `SHORT if side=="below" else LONG`. `side` comes
  from `_SIDE_BY_KIND` (`levels.py:80-89`): high-kinds (PDH/PWH/EQH/SWING_H/
  OPEN_RANGE_H/OB_BEAR/FVG_BEAR) = "below" -> SHORT; low-kinds = "above" -> LONG.
  **Correct for all 20 marks** where a signal direction is meaningful.
- **Quality** (`sweep.py:72-74`): `0.4 + 0.25*pool + 0.2*(touches>=3) +
  0.15*(daily/weekly kind) + 0.1*(chain_depth>=2)`, cap 1.0, `ttl=18`.
  `_pool_strength` (`sweep.py:108-115`) rewards EQ pools by touches+recency,
  OR/weekly pools 0.7, PD 0.6, else 0.5.
- **Reclaim upgrade** (`sweep.py:59-68`): SWEPT -> RECLAIMED within
  `reclaim_bonus_candles` (default 3) emits a second Evidence at `+0.1` strength,
  `meta.upgrade=True`. Encodes "sweep + reclaim = stronger".
- **Params/defaults** (`sweep.py:23`): `{tf:"5m", reclaim_bonus_candles:3,
  chain_window:20}`. Level zone widths that set the effective sweep tolerance live
  in `liquidity.py`: PDH/PDL/PWH/PWL/OR/ROUND = `(p - tick, p + tick)` (±1 tick,
  effectively exact); EQH/EQL = span of the clustered swing zones
  (`liquidity.py:147-151`); EQ clustering tol `eq_tolerance=0.001` (0.1%).

**CONFLUENCE.** The sweep signal is one leg of the taught chain
`sweep -> BOS -> OB/FVG entry`. `sweep.py` fires on the **sweep alone** (no BOS
gate) — which is *correct* for recognising the sweep itself (the sweep precedes
BOS). The BOS/entry gating belongs to `ob_taught`/`structure`, not here. Chain
context is captured softly via `_chain_depth` (opposite-direction sweep stacking,
`sweep.py:101-106`) feeding quality, not as a hard gate.

## How the user draws it

A horizontal line (or pivot dot) sitting on a liquidity pool, annotated
"LIQUIDITY SWEEP / SL TAKEN". The tradeable read is: the spike **through** the
line is the trap; the rejection candle's **outer wick** is where the stop goes
(a few points beyond the line); the pool becomes the SL anchor for the trade in
the opposite direction. In the marks the sweep line doubles as the SL location
(t24/t25 `sl=450`, t31b `sl=1932`) and sometimes as a target/exit pool for a
trade coming from the other side (t25: the ~450 sweep is the *long's* overhead
target-liquidity, not a short entry).

## Accuracy verdict

**pct_match = 15/18 = 83.3%** (hit / (hit+partial+miss); uncheckable excluded
from denominator).

| verdict | count | instances |
|---|---|---|
| hit | 15 | t10a, t10c, T11a, T11b, T12a, T12b, T13a, T13b, T13c, T18_1, T18_2, T18_4, t23_1, t23_2, t27 |
| partial | 2 | t24, t25 |
| miss | 1 | t31b |
| uncheckable | 2 | T5a, c33 |

**Per-stock breakdown**

| stock | hit | partial | miss | uncheck | note |
|---|---|---|---|---|---|
| HAVELLS | 9 | 0 | 0 | 1 | 4 distinct daily sweeps (1368/1320/1240/1220), each drawn twice/thrice; T5a era-mismatch |
| VOLTAS | 3 | 0 | 0 | 0 | one 5m spike-low, drawn 3x |
| TITAN | 2 | 0 | 0 | 0 | one 1h/daily sweep (3535), drawn 2x |
| DABUR | 1 | 2 | 0 | 0 | t27 hit (re-dated); t24/t25 partial (450 EQH broke, not rejected) |
| SBILIFE | 0 | 0 | 1 | 0 | firm-year MISS (1932 never reached) |
| (reference) | 0 | 0 | 0 | 1 | c33 schematic |

The 15 hits collapse to **8 distinct sweeps** once duplicate zoom-views are
merged (t10, T11, T12, T13, T18, t23, t27 + the schematic concept-match). On the
correct-era tape the wick-through-close-back geometry reproduces on the exact
drawn line to within ±1 tick, with the correct direction, every time.

**NUMERIC gaps seen in real data (values):**

- *Poke depths are tiny.* Daily HAVELLS sweeps poked only **0.09-0.22 ATR**
  beyond the line (1368: +5.70 = 0.22 ATR; 1320: +2.90 = 0.10; 1240: +3.30 =
  0.10; 1220: +3.90 = 0.09). TITAN 3535 poked 0.60 ATR (D1). VOLTAS spiked to
  1198.6 vs a drawn ~1198 (0.6 pt). These are **shallow structural pokes**, not
  1.5-2.5 ATR excursions — consistent with the user's tiny-stop thesis and with
  why an ATR-scaled stop model (the measured null) was the wrong object.
- *Registry date/year mislabels (not detector faults).* **T13** (all 3): the
  1220 sweep is clean on **2023-01-19** (H1223.90, C1205.45) — registry's **2022**
  has price at 1310-1380 with 1220 far below trend (no sweep). **t27**: 512 is
  swept-and-rejected on **2025-10-23** (D1 H515.0 C511.4; 1h 14:15 H514.45
  C511.00) then drops to 487 — registry's **2025-11-02** has price already
  *broken* above 512 to 524 (no sweep; the date was borrowed from the opposite-
  direction Da_nov_long). Detector reproduces both on the correct date.
- *DABUR 450 EQH (t24/t25) — break, not reject.* 5m wick-close-back pokes do
  exist early (07-07 09:30 H450.85 C449.90), but price then ran to **455.95
  (+5.65 pt = +0.70 ATR D1)** and the **daily bar closed 453.50 ABOVE 450.3** —
  a sustained close-beyond, which the level engine resolves to **DEAD**, not
  SWEPT. The mark's `sl=450.3` sits *inside* that excursion (would be run); the
  actual reversal came days later (target 07-15). Recognition partially fires but
  the clean same-session reject the user drew is absent.
- *SBILIFE 1932 (t31b) — the reliable MISS.* On firm-year 2024 daily the rally
  **topped at 1927.95 (2024-09-24), −4.05 pt short of the drawn 1932**; the
  prior high (1936, 2024-09-03) was also **not retaken**. Because daily high
  bounds every intraday high, no 30m candle reached 1932 either. This is a
  failure-swing / lower-high double-top rejection with **no poke-through**, so
  `LevelEngine` never emits SWEPT and `sweep.py` never fires. The wick-through
  rule is *correct* to reject it; the mark labels a reaction-at-level as a
  "sweep". (Note RETHINK: t31 was celebrated as a UTAD, and `wyckoff UPTHRUST`
  measured −9.2pp — a real over-labelling risk.)

**STRUCTURAL gaps:**

1. **EXT pivots are invisible.** `_SIDE_BY_KIND` has no `EXT_H`/`EXT_L`
   (`levels.py:80-89`), so `_SIDE_BY_KIND.get(lv.kind)` returns `None` and the
   loop `continue`s (`sweep.py:50-52`). Yet commit 8dc7cc8 made **extremes the
   taught liquidity anchor**, and `extremes.py` emits exactly `EXT_H/EXT_L`. So a
   sweep of the *taught* pivot cannot fire from an EXT level. Today the marks are
   still reachable via SWING_H/SWING_L and EQH/EQL (both handled), but the
   canonical anchor is not wired in. (T5a "doubles as extreme_swing low".)
2. **No SL / entry emitted.** `sweep.py` emits `zone=lv.zone` only. The taught
   object needs the **outer-wick SL** (a few pts beyond the spike) and a CE/edge
   entry. doc35 gap#3 (outer-wick vs body-edge) is *unaddressed here* — the sweep
   detector produces neither, so downstream must build the stop from the spike
   wick, which nothing currently does. This is the single untested lever in
   RETHINK §D2.
3. **Timeframe coupling.** Default `tf="5m"`; the HAVELLS/TITAN/SBILIFE marks are
   HTF (daily/1h/30m). With `tf=5m` and daily-only data `detect` returns `[]`
   (empty window). The geometry reproduces only when `tf` matches the chart TF.
4. **No reject-depth / speed gate.** A 0.10-ATR wick-and-reject and a full break
   that later reverses (DABUR 450) are indistinguishable until the close-beyond
   flips the level to DEAD one bar later. There is no "shallow poke + fast
   snapback within N bars/ticks" qualifier, so on noisy EQH clusters the detector
   fires repeatedly on every micro-poke.

**Data limits (per RETHINK / no silent drops):**
- 5m native only < 60 days (`data/long5m` + yahoo 5m since 2026-05-04); 1h from
  ~2024-07; daily full. So HAVELLS 2022-23, TITAN 2025, SBILIFE 2024, DABUR 2025
  sweeps were checked on **daily/1h**, not the 5m the user drew.
- Years are price-era guesses except t31 (firm 2024). T13 (2022->2023) and t27
  (Nov->Oct) are demonstrable mislabels found *by* this validation.
- T5a: 1863 is straddled by 25 HAVELLS 2024 daily candles (peak era ~1820-2106);
  its 2026 label contradicts the price era and no unique candle is locatable —
  logged uncheckable, not dropped.
- c33: educational schematic, no tape — concept-matches the SWEPT rule, logged
  uncheckable.

## Enhancement plan

Prioritised; references exact params/functions. RECOGNITION-scoped — none of
this claims edge.

**P1 — structural: wire EXT pivots into the sweep surface.**
Add `EXT_H:"below", EXT_L:"above"` to `_SIDE_BY_KIND` (`levels.py:80-89`) so
`LevelEngine` runs its transition machine on extreme pivots and `sweep.py:50`
stops skipping them. This makes the *taught anchor* (extremes.py) sweepable,
closing the "liquidity from EXT not fractal" guardrail. Verify EXT zone width is
tick-thin (like PD/PW) so shallow 0.1-ATR pokes still cross the far edge.

**P2 — structural: emit the outer-wick SL in the sweep Evidence.**
Extend the Evidence `meta` (`sweep.py:75-80`) with `sl` = the swept candle's
outer wick ± a tick buffer (the spike extreme past the level), and `entry` = the
level edge / CE, so downstream can build the tiny-stop / far-target RR that the
measured null never tested (RETHINK §D2). This is the highest-value structural
change: it produces the physically-different stop object the whole method rests
on. Keep it in `meta` (non-breaking) until a consumer reads it.

**P3 — numeric threshold: reject-depth + snapback gate.** TARGET values from the
data above. Add params, defaulting so the observed hits still pass:
- `min_poke_atr` ≈ **0.05** (all hits poked 0.09-0.60 ATR; keep it low, this is
  a floor to drop nuisance 1-tick grazes, not the shallow real sweeps).
- `max_reject_bars` ≈ **2** and require close back on origin within that window
  (already the reclaim path; expose it) — this is what separates the DABUR 450
  break (closed *beyond* for the whole session, went DEAD) from a true sweep.
- Optionally `max_poke_atr` (e.g. **1.5**) to distinguish a sweep-poke from a
  clean momentum break-through; DABUR ran +4.6 ATR(5m) above 450 — well past any
  sweep band — and should be classed break, not sweep.
  These would flip t24/t25 from noisy-partial toward a correct "not a clean
  sweep" and cost none of the 15 hits.

**P4 — birth-gate / confluence (optional, downstream): "reaction-at-level"
handling.** t31b shows the user sometimes labels a *lower-high double-top
rejection that never pokes through* as a "sweep". Do **not** loosen the
wick-through rule (it correctly rejected t31b, and UTAD measured negative).
Instead, if a "failure swing at pool" signal is ever wanted, add it as a
*separate, distinctly-named* Evidence (`event:"REACTION"`) so it is never
conflated with a true SWEPT stop-run — keeping the sweep signal honest.

**P5 — config hygiene: timeframe.** Make `tf` explicit per-run (or multi-TF) so
HTF marks (daily/1h/30m) are evaluated on their own TF; document that
`tf="5m"` + daily-only data yields no signal (empty `window`, `sweep.py:45-47`).
Not a code bug — a wiring/documentation fix.

*Cross-cut for the whole registry:* T13 (year 2022->2023) and t27 (date
Nov->Oct) are hard evidence that the circular year/price-era resolution
(RETHINK A2) put marks on wrong candles. Re-resolve dates against the actual
wick-through-close-back candle the detector finds, rather than the outcome-
maximising year, before any of these are used as ground truth for edge work.
