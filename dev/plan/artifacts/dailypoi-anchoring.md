# DAILY-POI ANCHORING — top-down SMC test (60d, 300,153 signals)

**Hypothesis tested:** textbook top-down SMC — intraday entries only inside DAILY points of
interest (daily OB / daily FVG / daily swing S/R). Last untested version of "enter only at the
REAL institutional zones"; the 300k intraday signals had previously only been conditioned on
M15/wyckoff context (which failed).

**Verdict: DEAD FILTER for profitability. Daily-POI anchoring gives a real but tiny hit-rate
lift (+1.1pp pooled, +2.4pp best detector) and improves net_R by ~+0.03R, but every single
(detector x condition x cfg) cell with n>=200 stays net-NEGATIVE — best cell anywhere is
-0.21R. Zero cells go net-positive even before requiring holdout stability. The strictest
textbook cell (fresh daily OB, entry deep inside) is -0.24R at its best cfg. Not a power
problem: 117,539 in-POI signals (39.2%).**

## Method (leak-free)

- Daily bars: yfinance 2y daily (`{sym}.NS`), all 138 signals60 symbols fetched, 0 failures
  (499 bars each, 2024-07-18..2026-07-17), cached to scratchpad `daily2y.parquet`.
- CAUSAL: for a signal on session D, only daily bars with date < D are used — both for POI
  formation (form_idx <= j) and invalidation (kill_idx > j), where j = last daily bar before D.
  Swing fractals only count after their 2-bar confirmation.
- Daily OB: displacement bar with body >= 1.5xATR14(prev); zone = range of last opposite-color
  candle within 5 bars back; live until a daily close beyond its far edge.
- Daily FVG: 3-candle gap >= 0.3xATR14(prev); zone = the gap; live until filled (daily close
  beyond far edge).
- Daily swing S/R: 2-2 fractal high (bear/resistance) / low (bull/support); live until a daily
  close beyond the level.
- In-POI: signal entry inside a live, direction-consistent zone +/- 0.25xdaily-ATR14
  (bull zone -> LONG only, bear zone -> SHORT only).
- Holdout: temporal first/second-half sessions (29/28 of 57) x crc32(symbol)%2.

## Sample accounting

- in-POI: **39.2%** (117,539 / 300,153) — high power, no low-sample caveat.
- Primary type: FVG 89,566 / OB 17,474 / swing 10,499 (overlapping: in_fvg 95,975,
  in_swing 26,249, in_ob 17,474).
- fresh (age<=10 trading days) 68,049; old 49,490; deep-inside raw zone 74,672; edge-band only 42,867.

| detector | n | n in-POI | % in-POI |
|---|---|---|---|
| bpr | 12,970 | 4,690 | 36.2% |
| compression_fade | 113,445 | 44,707 | 39.4% |
| fvg_cb | 37,009 | 12,379 | 33.4% |
| inducement | 9,177 | 2,208 | 24.1% |
| mitigation | 43,095 | 17,980 | 41.7% |
| ob_lux | 79,028 | 33,623 | 42.5% |
| turtle_soup | 5,429 | 1,952 | 36.0% |
| ALL | 300,153 | 117,539 | 39.2% |

## 1. Hit-edge (hit% − b_hit baseline; decided signals only)

| detector | n in | hit% in | edge in | n out | hit% out | edge out | d(edge) |
|---|---|---|---|---|---|---|---|
| bpr | 4,582 | 52.6% | +7.7% | 8,005 | 50.1% | +5.3% | +2.4% |
| compression_fade | 43,476 | 51.2% | +10.9% | 66,860 | 49.1% | +9.4% | +1.4% |
| fvg_cb | 12,049 | 50.5% | +11.0% | 23,822 | 49.1% | +9.1% | +1.9% |
| inducement | 2,156 | 50.3% | +16.2% | 6,803 | 49.2% | +15.4% | +0.8% |
| mitigation | 17,524 | 50.1% | +10.8% | 24,486 | 49.2% | +9.9% | +0.9% |
| ob_lux | 32,781 | 51.2% | +9.9% | 44,260 | 50.3% | +9.4% | +0.5% |
| turtle_soup | 1,913 | 48.2% | +9.0% | 3,390 | 47.2% | +9.1% | -0.1% |
| **ALL** | **114,481** | **50.9%** | **+10.5%** | **177,626** | **49.4%** | **+9.5%** | **+1.1%** |

Direction is right in 6/7 detectors — the zones carry *some* information — but the lift is
~1pp, an order of magnitude too small to matter after costs.

By POI sub-condition (pooled):

| condition | n | hit% | b_hit | edge |
|---|---|---|---|---|
| out-of-POI | 177,626 | 49.4% | 39.9% | +9.5% |
| in-POI (any) | 114,481 | 50.9% | 40.4% | +10.5% |
| in OB | 17,030 | 51.2% | 40.3% | +10.9% |
| in FVG | 93,484 | 50.8% | 40.2% | +10.5% |
| in SWING | 25,543 | 51.7% | 40.7% | +11.1% |
| fresh (<=10d) | 66,291 | 50.3% | 40.0% | +10.3% |
| old (>10d) | 48,190 | 51.8% | 40.9% | +10.9% |
| deep-inside | 72,724 | 50.8% | 40.2% | +10.7% |
| edge-band only | 41,757 | 51.1% | 40.8% | +10.3% |

Notably anti-textbook: OLD zones slightly beat FRESH ones; OB is not better than FVG; swing
levels are marginally the best sub-type. Deep vs edge: no meaningful difference.

## 2. Net expectancy (mean net_R, realistic costs) at k=1.5 fixed_t1 / fixed_t3

| detector | cfg | n in | net_R in | n out | net_R out | d |
|---|---|---|---|---|---|---|
| bpr | k1.5 fixed_t1 | 4,690 | -0.2442 | 8,280 | -0.2950 | +0.0508 |
| compression_fade | k1.5 fixed_t1 | 44,707 | -0.2663 | 68,738 | -0.3086 | +0.0422 |
| fvg_cb | k1.5 fixed_t1 | 12,379 | -0.2206 | 24,630 | -0.2552 | +0.0345 |
| inducement | k1.5 fixed_t1 | 2,208 | -0.2658 | 6,969 | -0.2885 | +0.0227 |
| mitigation | k1.5 fixed_t1 | 17,980 | -0.2548 | 25,115 | -0.2910 | +0.0362 |
| ob_lux | k1.5 fixed_t1 | 33,623 | -0.2869 | 45,405 | -0.3130 | +0.0261 |
| turtle_soup | k1.5 fixed_t1 | 1,952 | -0.3012 | 3,477 | -0.3105 | +0.0093 |
| **ALL** | **k1.5 fixed_t1** | **117,539** | **-0.2653** | **182,614** | **-0.2987** | **+0.0334** |
| bpr | k1.5 fixed_t3 | 4,690 | -0.2207 | 8,280 | -0.2804 | +0.0598 |
| compression_fade | k1.5 fixed_t3 | 44,707 | -0.2588 | 68,738 | -0.3212 | +0.0624 |
| fvg_cb | k1.5 fixed_t3 | 12,379 | -0.2328 | 24,630 | -0.2713 | +0.0384 |
| inducement | k1.5 fixed_t3 | 2,208 | -0.3167 | 6,969 | -0.3162 | -0.0004 |
| mitigation | k1.5 fixed_t3 | 17,980 | -0.2763 | 25,115 | -0.3100 | +0.0337 |
| ob_lux | k1.5 fixed_t3 | 33,623 | -0.3194 | 45,405 | -0.3267 | +0.0073 |
| turtle_soup | k1.5 fixed_t3 | 1,952 | -0.3635 | 3,477 | -0.3748 | +0.0113 |
| **ALL** | **k1.5 fixed_t3** | **117,539** | **-0.2774** | **182,614** | **-0.3133** | **+0.0359** |

Sub-conditions (pooled): best is in-SWING at fixed_t3 (-0.2273); old > fresh again
(-0.2298 vs -0.3120 at t3); nothing within 0.2R of breakeven.

## 3. The money question: holdout-stable net-positive cells

Scan: all 28 cfgs x 7 detectors + pooled x 8 conditions (in_poi / OB / FVG / SWING / fresh /
old / deep / edge-only), n>=200, requiring mean net_R > 0 overall AND in both temporal halves
AND both symbol halves.

**Result: ZERO holdout-stable net-positive cells. Stronger: ZERO cells are net-positive even
overall, before any stability requirement — the "near-miss" list is empty.** Control scan of
out-of-POI cells likewise has zero net-positive cells.

Best cells found anywhere (all still firmly negative):

| detector | condition | cfg | n | net_R |
|---|---|---|---|---|
| fvg_cb | in-POI | k1.5 fixed_t2 | 12,379 | -0.2146 |
| bpr | in-POI | k1.5 fixed_t3 | 4,690 | -0.2207 |
| fvg_cb | deep-inside | k1.5 fixed_t2 | 7,944 | -0.2265 |

Strictest textbook cell — fresh (<=10d) daily OB, entry deep inside the raw zone
(n=7,094): hit-edge +11.1% (no lift over pooled in-POI +10.5%), best cfg k1.5 fixed_t1.5 =
**-0.2437 net_R**. The "purest institutional zone" entry is exactly as unprofitable as
everything else.

## Verdict

Daily-POI anchoring is **another dead filter**. It is directionally real — being inside a live,
direction-consistent daily zone adds ~+1pp win rate and ~+0.03R expectancy, consistently across
6/7 detectors — but the effect size is ~10x too small to overcome the ~-0.27R cost-laden
baseline. The textbook refinements (fresh > old, OB > FVG, deep > edge) are either absent or
inverted in this data. With 117k in-POI signals and zero net-positive cells across 1,700+
scanned cells, this is not a power issue and not a cfg-selection issue. The top-down
"institutional zone" hypothesis, in its last untested form, does not rescue the intraday
signal set.

Caveats: 60 trading days (one regime); simplified parity POI rules (single-bar displacement,
5-bar OB lookback, simple-mean ATR14); multiple-testing across the scan would demand even
stronger evidence than "any positive cell" — none appeared anyway.

Artifacts (scratchpad): `daily2y.parquet` (cached daily bars), `dailypoi_tags.parquet`
(per-signal tags), `dailypoi_fetch.py`, `dailypoi_build.py`, `dailypoi_measure.py`.
