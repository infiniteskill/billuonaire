# HINDUNILVR — full SMC inventory (5m / 15m / 30m / H1 / D1)

Data: `data/long5m/HINDUNILVR.csv`, native 5m, **2026-04-27 → 2026-07-17, 57 sessions**
(4275 five-minute bars). 15m/30m/H1 resampled 09:15-anchored (30m & H1 bins offset
+15min so the first bar opens 09:15); D1 = one bar per session.
Script: scratchpad `hulinv_run.py` (zone construction = the chartpar standalone
replications of `ob_lux` / `fvg_cb` / fractal swings; breaker = EmreKb MSB core
ported from `app/trader/detectors/breaker_msb.py`, zz=9 fib=0.33 warm=25).

## Master table — total counts over 57 sessions

| Category | 5m | 15m | 30m | H1 | D1 |
|---|---:|---:|---:|---:|---:|
| Bars | 4275 | 1425 | 741 | 399 | 57 |
| Swings (fractal 5/5) | 463 | 162 | 84 | 55 | 4 |
| — highs / lows | 237/226 | 84/78 | 42/42 | 30/25 | 2/2 |
| **Extremes** (move-to-violation ≥ 2×ATR14) | 377 | 132 | 77 | 49 | 4 |
| — strict alt: flank prominence ≥ 2×ATR | 221 | 83 | 48 | 33 | 2 |
| FVG (fvg_cb rule) | 103 | 37 | 23 | 14 | 0 |
| — bull / bear | 59/44 | 20/17 | 13/10 | 8/6 | 0/0 |
| OB (ob_lux rule) | 332 | 108 | 58 | 33 | 5 |
| — bull / bear | 162/170 | 55/53 | 29/29 | 16/17 | 2/3 |
| FVG invalidated (close through far edge) | 94 | 30 | 18 | 11 | 0 |
| **iFVG** (invalidated + retested from other side) | 92 | 29 | 17 | 11 | 0 |
| **Breaker (BB)** zones formed | 34 | 6 | 2 | 2 | 1 |
| — of which retested (close back inside) | 18 | 3 | 1 | 1 | 1 |
| EQ-high pools (2+ swings ≤ 0.25×ATR) | 74 | 29 | 13 | 8 | 0 |
| EQ-low pools | 69 | 22 | 8 | 4 | 0 |
| **Sweep events** (wick through pool, close back; 1/pool) | 55+63=118 | 18+17=35 | 6+5=11 | 3+3=6 | 0 |

### Per-session averages (count ÷ 57)

| Category | 5m | 15m | 30m | H1 |
|---|---:|---:|---:|---:|
| Swings | 8.1 | 2.8 | 1.5 | 0.96 |
| Extremes (task defn / strict flank) | 6.6 / 3.9 | 2.3 / 1.5 | 1.4 / 0.84 | 0.86 / 0.58 |
| FVG | 1.8 | 0.65 | 0.40 | 0.25 |
| OB | 5.8 | 1.9 | 1.0 | 0.58 |
| iFVG | 1.6 | 0.51 | 0.30 | 0.19 |
| Breaker | 0.60 | 0.11 | 0.04 | 0.04 |
| Liquidity pools (EQH+EQL) | 2.5 | 0.89 | 0.37 | 0.21 |
| Sweep events | 2.1 | 0.61 | 0.19 | 0.11 |

D1 is structurally empty at 57 bars: 4 swings, 5 OB, 1 breaker, 0 FVG, 0 pools —
the fractal + ATR-warmup rules need more history than one quarter of days.

## HTF → LTF refinement map

5m zone universe = OB + FVG = 435 zones. A 5m zone "nests" in an HTF zone when its
band overlaps the HTF band AND it was born within ±2 trading sessions of the HTF
zone's birth. Full = 5m band entirely inside HTF band; partial = overlap only.

| Map | HTF zones | avg 5m zones/HTF zone | avg full | avg partial | min | max |
|---|---:|---:|---:|---:|---:|---:|
| H1 → 5m | 47 | **13.6** | 8.0 | 5.6 | 3 | 34 |
| 30m → 5m | 81 | **10.7** | 5.6 | 5.1 | 2 | 34 |

Distribution ("1 H1 zone contains N 5m zones", N = full+partial):

| N | ≤5 | 6–10 | 11–15 | 16–20 | 21+ |
|---|---:|---:|---:|---:|---:|
| H1 zones | 6 | 9 | 16 | 10 | 6 |
| 30m zones | 14 | 30 | 22 | 9 | 6 |

Every H1 zone contains at least 3 nested 5m zones — the "find on HTF, refine on
LTF" join never comes up empty on this symbol.

**H1 extremes → 5m "OB near swing" join**: of 49 H1 extremes, **47 (96%)** have a
5m OB/FVG within 1×ATR(5m) of the swing price born within ±2 sessions of the
swing; relaxing the time window to anytime gives 49/49 (100%).

## 5 example H1 zones (verify on Zerodha, HINDUNILVR 60-minute chart)

| # | Kind | Band (₹) | Origin candle | Confirmed | Note |
|---|---|---|---|---|---|
| 1 | FVG bull | 2102.60 – 2126.30 | 2026-07-17 09:15 (c2) | 2026-07-17 10:15 | overnight gap: c1 = 16-Jul 15:15 high 2102.60, c3 = 17-Jul 10:15 low 2126.30 |
| 2 | OB bull | 2096.20 – 2105.00 | 2026-07-16 14:15 | 2026-07-17 09:15 | last down-anchor before the close that broke the swing high |
| 3 | OB bear | 2148.80 – 2178.00 | 2026-07-10 09:15 | 2026-07-13 09:15 | supply block above the mid-July slide |
| 4 | FVG bear | 2179.80 – 2203.10 | 2026-07-08 09:15 (c2) | 2026-07-08 10:15 | displacement gap on the 8-Jul open drive down |
| 5 | Breaker bull | 2162.70 – 2200.00 | 2026-06-25 09:15 | MSB 2026-07-03 14:15 | swing low swept → up-candle range becomes breaker; later retested (close back inside) |

## Rule definitions used (exact)

- **Swings**: fractal 2N+1 window, N=5; middle bar strictly highest/lowest.
- **Extremes**: prominence = the subsequent adverse move from the swing until the
  swing price is first violated (or to end of data); extreme if ≥ 2×ATR(14, TF)
  at the swing bar. Note this definition is permissive (81% of 5m swings qualify —
  a fractal swing survives ≥5 bars each side by construction, so the
  move-to-violation is usually large). The strict alternative row uses chartpar's
  flank prominence: min(left-drop, right-drop) over the 5-bar flanks ≥ 2×ATR.
- **FVG** (`fvg_cb`): bull c3.low > c1.high with c2 close > c1.high (bear mirrored),
  gap% above the running mean bar-range% threshold, no creation before ATR14 exists.
- **OB** (`ob_lux`): pivot(5) swing, first close crossing it confirms; anchor = the
  extreme parsed low/high over [pivot..confirm] with high-volatility bars
  (range ≥ 2×ATR) high/low-swapped; zone = anchor candle's sorted band.
- **iFVG**: FVG whose far edge is closed through (bull: close < zone low), then the
  band is re-touched from the other side. Near-total conversion: 92 of 94
  invalidated 5m FVGs were later retested — an invalidated FVG on this symbol is
  almost always a future iFVG event.
- **Breaker** (`breaker_msb` core): zigzag(9) alternating swings; fib-0.33 MSB with
  both extremes fresh; box only when the older swing was swept; box = full range of
  the last opposite-color candle in [older-swing-bar−9 .. other-swing-bar]; dies on
  close beyond far edge; retest = first later close back inside.
- **Pools**: same-side fractal swing points clustered within 0.25×ATR(14, TF)
  (anchor-chained, sorted by price), pool needs ≥2 points. **Sweep** = wick takes
  the pool's extreme price and the same candle closes back inside (turtle-soup
  shape), scanned only after the pool's second point is confirmed (+5 bars),
  counted once per pool.
