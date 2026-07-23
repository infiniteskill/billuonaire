# sweep — precision audit

Detector `app/trader/detectors/sweep.py` (`SweepDetector`, `name="sweep"`, event
`SWEEP`). Scope: **PRECISION / recognition only** — of all firings, how many are
the REAL taught object (a poke-through-reject of a *resting-liquidity pool*).
Recall is already ~100% (41-TOOLS: 15/18 marks reproduce to ±1 tick). No edge/
profit claim here. Data: `runs/validate/precision_study/evidence.parquet`
(8 marked stocks, 17 sessions, 1m/wide, 2026-06-25..2026-07-17).

## Firing picture (over-fire)

- **Total SWEEP fires: 2613** over 8 stocks × 17 sessions.
- **Density = 19.2 fires / stock / session** (median 19, max **47** in one
  stock-session). Mean 327 fires/stock.

| stock | fires | fires/session |
|---|---|---|
| HEROMOTOCO | 382 | 22.5 |
| HDFCBANK | 372 | 21.9 |
| TITAN | 357 | 21.0 |
| VOLTAS | 342 | 20.1 |
| HAVELLS | 322 | 18.9 |
| SBILIFE | 296 | 17.4 |
| DABUR | 276 | 16.2 |
| DLF | 266 | 15.7 |

A real chart shows **~1–3** taught liquidity-pool sweeps per session (the
poke-and-reject that precedes a reversal). 19.2/session is a **~6–10× over-fire**.

**Where the over-fire lives (measured):**
- **77%** of fires are on tick-thin levels (zone width <0.05% ≈ ±1 tick →
  PDH/PDL/PWH/PWL/OR **and raw SWING** pivots, all built as `(p±tick)`);
  22% are EQ clusters (0.05–0.3%).
- **48.6%** of fires sit at strength **0.525 or 0.625** — the decomposition
  `0.4 + 0.25·(pool=0.5) [+0.1 chain]` with **no** touches-≥3 bonus, no daily/
  weekly bonus: i.e. **lone-fractal / generic-pool grazes**, not resting liquidity.
- **63.4%** of fires are strength <0.725 → almost certainly **touches < 3**
  (never carry the +0.2 multi-touch term). Only **10%** reach ≥0.825.
- **32%** of firing *instants* fire on ≥2 overlapping levels at once (mean 1.67,
  **max 11** simultaneous). **67%** of fires land within 5 min of the previous
  fire (40% within 1 min) — bursty repeat-pokes of the same region.

## In-window precision (honest limits)

Registry `sweep` marks: **20**, but **18** are dated outside the window (HAVELLS
1863/1368/1320/1240/1220 = Jan–Jun price-era guesses; VOLTAS 18/05; TITAN 03-07/01;
DABUR 512 Oct; SBILIFE 24/09; 1 schematic with null stock). Only the two **DABUR
~450** marks (`~07/07` @450.3, `~02-06/07` @450.5) fall in the window by both date
**and** price-era (DABUR trades 421.8–454.5 in-window). So **in-window n = 2 marks
= 1 distinct pool, 1 stock.** Ground truth is far too thin for a real precision
number — density is the honest proxy.

- **Recall (in-window): 2/2** — both marks have matching fires (DABUR 09:xx
  2026-07-06..08 near 450, tol 0.5 ATR ≈ 1.35). ✓
- **Precision (in-window, DABUR only): 10 / 276 = 3.6%** of DABUR fires land on
  the ~450 mark. And the matched fires split **6 LONG / 4 SHORT** — a HIGH pool
  (EQH ~450) swept should be **SHORT**-only; the LONG fires are a *second, low-
  kind* level colliding at ~450 (the multi-level clutter). Worse, 41-TOOLS graded
  DABUR 450 as **"break, not reject" (level went DEAD, sl inside the excursion)** —
  so even the 10 "matched" fires are likely the non-taught break case. Treat 3.6%
  as an **upper bound**; the true clean-sweep rate on this level is ~0.
- **Overall in-window precision is not estimable** (10 matched / 2613 = 0.38% is
  meaningless — the marks cover 1 level on 1 stock). Use **density = 19.2 fires/
  stock/session vs ~1–3 taught = ~6–10× over-fire** as the precision proxy.

## Over-fire root cause (code)

`detect()` (`sweep.py:43-83`) loops over **every** `Level` in `ctx.levels`
whose kind has a side in `_SIDE_BY_KIND` — that is PDH/PDL, PWH/PWL, EQH/EQL,
OR_H/OR_L, EXT_H/EXT_L **and raw SWING_H/SWING_L** (`levels.py:80-89`) — and emits
the instant the level flips to `SWEPT` (`levels.py` wick-through-close-back).
There is **no birth gate**:

1. **No pool-quality gate.** `touches>=3` is only a soft **+0.2 quality nudge**
   (`sweep.py:73`), never a filter. A resting-liquidity pool = *stacked stops* =
   a level tested **multiple** times (equal highs/lows, a repeatedly-defended
   PDH). The detector sweeps a level poked **once**, which is a lone-fractal graze,
   not the taught stop-run. → the 63.4% of fires with touches<3.
2. **Raw SWING pivots are in the sweep surface.** `SWING_H/SWING_L` (built
   `(extreme±tick)` in `swings.py:76`) are "fractal furniture" — commit 8dc7cc8
   made **extremes** the taught anchor precisely because raw swings are noise.
   Every minor 1m fractal high/low becomes an independently sweepable level.
3. **No poke-depth floor.** Any wick that pokes beyond a tick-thin edge and
   closes back fires; a 1-tick graze is indistinguishable from a real 0.1–0.6 ATR
   poke. (41-TOOLS gap #4.)
4. **No per-pool session refractory.** `_seen` dedups only `(level_id, swept_ts,
   is_reclaim)` (`sweep.py:55`). The **same** pool re-poked at a *new* swept_ts
   fires again, and every **adjacent** clustered level fires independently at the
   same instant → 32% of instants fire ≥2 levels (max 11), 67% within 5 min.

Net: the sweep leg that feeds the high-grade conjunction is **~1-in-8 real** — a
dilute stack of lone-fractal grazes and repeat-pokes drowning the true resting-
liquidity sweep.

## The precision tune + expected effect

**THE single highest-leverage change — promote `touches` to a HARD birth gate.**
In `detect()` add a `min_touches` param (default **3**) and, before emitting the
base SWEEP (`sweep.py:70`, right after the `is_reclaim` block), skip lone-fractal
pools:

```python
# resting liquidity = stacked stops = multiply-tested pool; lone pokes are noise
if lv.touches < self.params["min_touches"] and lv.kind not in _DAILY_WEEKLY:
    continue
```

Gate on **touches ≥ 3** (the accumulated-liquidity threshold the taught "equal
highs/lows / SL stacked" object requires), **exempting only PDH/PDL/PWH/PWL**
(single-reference daily/weekly pools that hold stops on first touch — this
protects the validated HAVELLS/TITAN/SBILIFE daily-level recall).

- **Numeric target:** fires **2613 → ~950–1150**, i.e. **−55% to −63%**
  (strength≥0.725 = the touches≥3 slice = 957 fires; +the daily/weekly exemption
  adds back the PDH/PDL first-touch band). Density **19.2 → ~7 fires/stock/session**.
- **Why it raises the real-fraction (not just the count):** it removes
  *preferentially* the 48.6% modal 0.525/0.625 lone-fractal grazes and the 63.4%
  touches<3 pokes — exactly the fires that are **not** resting liquidity — while
  keeping every multiply-tested pool. Unlike a de-dup, it filters by conviction,
  so the surviving sweep leg is dominated by genuine stacked-stop pools. The
  high-grade tier's sweep contribution goes from ~1-in-8 real toward ~1-in-3,
  making more of each firing's grade-stack the real taught object.
- **Recall guard:** the daily/weekly exemption keeps the canonical PDH/PWH sweeps
  (the 8 validated distinct sweeps are daily/1h/30m pool sweeps); EQH/EQL by
  construction already carry ≥2–3 touches, so equal-highs/lows sweeps survive.
  Expected recall cost on the validated marks: ~0.

**Runner-up levers (lower leverage / secondary):**
- **Per-pool session refractory** — collapse overlapping-zone levels (within
  0.5 ATR) and suppress re-fires on a cluster for the session unless price fully
  re-crosses to origin. *Measured* −58% to −64% (2613 → ~942 distinct pool-
  clusters). Recall-safe, but it **de-duplicates** rather than filters, so it
  raises conviction-density more than the real-fraction — pair it *after* the
  touches gate, not instead of it.
- **`min_poke_atr ≈ 0.05` floor** (41-TOOLS P3) — kills 1-tick grazes; recall-safe
  (real sweeps poked 0.09–0.60 ATR) but small, and not measurable from this
  parquet (poke depth isn't a column).

*Data caveat:* in-window ground truth is 2 marks / 1 pool / 1 stock (DABUR ~450,
itself a graded "break not reject"). The reduction targets are anchored on the
firing-density and strength-decomposition of the 2613 fires, not on matched marks.
