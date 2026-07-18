# DIAG5 -- FINAL FULL-SYSTEM DIAGNOSTIC (5 stocks x 8 detectors)

**Data**: `data/long5m/` native 5m, 57 sessions (2026-04-27 .. 2026-07-17), 75 bars/day.
**Stocks**: RELIANCE, HDFCBANK, INFY, TATASTEEL, HINDUNILVR (index heavyweight / bank / IT / metal cyclical / FMCG defensive).
**Detectors** (all 8 registered v2-family on main, production default params, tick-by-tick
drive with real CandleStore+StockContext+LevelEngine, session hooks, OB/FVG carry <5
weekday sessions): ob_lux, compression_fade, fvg_cb, mitigation, bpr, inducement,
propulsion_block (ob_lux runs first as its OB-level writer), turtle_soup.
`breaker_msb` does **not** exist in `app/trader/detectors/` (only `breaker`, a different
INVERTED-level retest detector outside the v2 family) -- excluded.

**Method (leak-free)**: signal at closed-M5 bar; entry = next 5m bar open; all outcome
windows EOD-truncated. hit = MFE>=1ATR before MAE>=1ATR (24-bar window, both-in-one-bar
= loss, undecided counts against). baseline = 20 seeded same-session same-30-min-bucket
random bars, same scoring (study.baseline). Net exp = step2_engine realistic fills+costs
(limit entry -half-spread, stop gap-through + slip, Rs20x2 + STT + exch, 1% of 10L risk,
5x leverage cap), stop k=1.5xATR, schemes fixed_t1 / fixed_t3.
**Taxonomy** (stop = 1.5 ATR, R = 1.5 ATR): WIN = fav >=3R strictly before the stop bar;
WRONG = stopped then adverse continues >=2R beyond the stop; SHAKEOUT = stopped then
fav >=3R (first-touch ordering, tie -> WRONG); CHOP = everything else.
Temporal halves: H1 = sessions 1-29, H2 = sessions 30-57.

Signals: 11128 total (RELIANCE 2079, HDFCBANK 2220, INFY 2260, TATASTEEL 2365, HINDUNILVR 2204).

---

## RELIANCE

### Per-tool

| tool | n | hit% | undec% | base% | edge pp | net_t1 R | net_t3 R |
|---|---|---|---|---|---|---|---|
| ob_lux | 502 | 52.2 | 2.2 | 46.6 | +5.6 | -0.349 | -0.227 |
| compression_fade | 872 | 50.1 | 4.1 | 40.9 | +9.2 | -0.333 | -0.333 |
| fvg_cb | 214 | 48.6 | 7.0 | 40.5 | +8.1 | -0.289 | -0.236 |
| mitigation | 299 | 48.2 | 5.4 | 37.5 | +10.7 | -0.397 | -0.409 |
| bpr | 39 | 48.7 | 10.3 | 42.4 | +6.3 | -0.629 | -0.384 |
| inducement | 68 | 52.9 | 0.0 | 34.2 | +18.7 | -0.308 | -0.207 |
| propulsion_block | 43 | 41.9 | 11.6 | 33.6 | +8.3 | -0.390 | -0.504 |
| turtle_soup | 42 | 40.5 | 2.4 | 39.6 | +0.8 | -0.597 | -0.416 |
| ALL | 2079 | 49.9 | 4.2 | 41.4 | +8.5 | -0.353 | -0.311 |

### Autopsy (all trades classified; stop k=1.5 ATR)

| tool | n | WIN% | WRONG% | SHAKEOUT% | CHOP% | stopped% | med need-k (ATR) |
|---|---|---|---|---|---|---|---|
| ob_lux | 502 | 22.3 | 22.5 | 7.6 | 47.6 | 62.9 | 2.00 (=1.3x) |
| compression_fade | 872 | 17.8 | 22.7 | 6.9 | 52.6 | 62.5 | 2.41 (=1.6x) |
| fvg_cb | 214 | 17.8 | 19.6 | 6.5 | 56.1 | 62.1 | 1.67 (=1.1x) |
| mitigation | 299 | 14.0 | 27.8 | 4.7 | 53.5 | 63.9 | 2.74 (=1.8x) |
| bpr | 39 | 20.5 | 35.9 | 7.7 | 35.9 | 69.2 | 2.63 (=1.8x) |
| inducement | 68 | 22.1 | 23.5 | 5.9 | 48.5 | 63.2 | 2.52 (=1.7x) |
| propulsion_block | 43 | 11.6 | 20.9 | 16.3 | 51.2 | 53.5 | 2.84 (=1.9x) |
| turtle_soup | 42 | 19.0 | 31.0 | 2.4 | 47.6 | 71.4 | 2.09 (=1.4x) |
| ALL | 2079 | 18.4 | 23.5 | 6.8 | 51.3 | 62.9 | 2.29 (=1.5x) |

### Co-fire pairs (same dir, <=3 bars, zone mids <=0.5 ATR; entry at later signal)

| pair (+) | n | hit% | net_t1 | solo A | solo B | beats both | H1 | H2 |
|---|---|---|---|---|---|---|---|---|
| compression_fade+ob_lux | 116 | 50.9 | -0.420 | -0.333 | -0.349 | no | -0.53 | -0.28 |
| compression_fade+mitigation | 83 | 50.6 | -0.220 | -0.333 | -0.397 | **YES** | -0.15 | -0.28 |
| mitigation+ob_lux | 79 | 45.6 | -0.314 | -0.397 | -0.349 | **YES** | -0.34 | -0.30 |
| compression_fade+fvg_cb | 44 | 52.3 | -0.162 | -0.333 | -0.289 | **YES** | -0.14 | -0.21 |
| compression_fade+inducement | 26 | 65.4 | -0.005 | -0.333 | -0.308 | **YES** | -0.72 | +0.52 |
| bpr+compression_fade | 20 | 45.0 | -0.291 | -0.629 | -0.333 | **YES** | -0.28 | -0.30 |
| mitigation+propulsion_block | 13 | 76.9 | +0.020 | -0.397 | -0.390 | **YES** | +0.02 | +0.02 |
| compression_fade+propulsion_block | 12 | 50.0 | -0.458 | -0.333 | -0.390 | no | -0.58 | -0.29 |
| compression_fade+turtle_soup | 10 | 50.0 | -0.453 | -0.333 | -0.597 | no | -0.57 | -0.28 |
| inducement+ob_lux | 9 | 55.6 | -0.585 | -0.308 | -0.349 | no | -1.21 | -0.41 |
| bpr+fvg_cb | 8 | 50.0 | -1.024 | -0.629 | -0.289 | no | -0.76 | -1.29 |
| mitigation+turtle_soup | 7 | 57.1 | -0.209 | -0.397 | -0.597 | **YES** | -0.22 | -0.20 |
| inducement+mitigation | 7 | 42.9 | -0.078 | -0.308 | -0.397 | **YES** | +0.15 | -0.25 |
| fvg_cb+ob_lux | 6 | 100.0 | -0.181 | -0.289 | -0.349 | **YES** | -0.69 | +0.84 |
| ob_lux+propulsion_block | 6 | 0.0 | -1.004 | -0.349 | -0.390 | no | -1.13 | -0.74 |
| fvg_cb+mitigation | 5 | 20.0 | -0.519 | -0.289 | -0.397 | no | -1.27 | -0.02 |

### Sequence chains A->B (1..6 bars, same dir, zone <=0.5 ATR; entry at B)

| pair (->) | n | hit% | net_t1 | solo A | solo B | beats both | H1 | H2 |
|---|---|---|---|---|---|---|---|---|
| compression_fade->ob_lux | 111 | 46.8 | -0.536 | -0.333 | -0.349 | no | -0.65 | -0.39 |
| mitigation->compression_fade | 66 | 51.5 | -0.270 | -0.397 | -0.333 | **YES** | -0.21 | -0.31 |
| mitigation->ob_lux | 65 | 52.3 | -0.177 | -0.397 | -0.349 | **YES** | -0.19 | -0.17 |
| fvg_cb->compression_fade | 39 | 59.0 | -0.234 | -0.289 | -0.333 | **YES** | -0.46 | +0.03 |
| ob_lux->compression_fade | 35 | 48.6 | -0.290 | -0.349 | -0.333 | **YES** | -0.12 | -0.45 |
| compression_fade->mitigation | 34 | 52.9 | -0.264 | -0.333 | -0.397 | **YES** | -0.23 | -0.30 |
| inducement->compression_fade | 14 | 71.4 | -0.098 | -0.308 | -0.333 | **YES** | -0.86 | +0.32 |
| compression_fade->inducement | 13 | 53.8 | -0.289 | -0.333 | -0.308 | **YES** | -0.53 | -0.08 |
| bpr->compression_fade | 12 | 66.7 | -0.261 | -0.629 | -0.333 | **YES** | -0.41 | -0.05 |
| turtle_soup->compression_fade | 12 | 58.3 | -0.256 | -0.597 | -0.333 | **YES** | -0.89 | +0.20 |
| ob_lux->mitigation | 11 | 54.5 | -0.083 | -0.349 | -0.397 | **YES** | +0.01 | -0.14 |
| propulsion_block->compression_fade | 9 | 44.4 | -0.291 | -0.390 | -0.333 | **YES** | -0.06 | -0.58 |
| inducement->ob_lux | 8 | 37.5 | -0.784 | -0.308 | -0.349 | no | - | -0.78 |
| compression_fade->bpr | 7 | 42.9 | -0.489 | -0.333 | -0.629 | no | +0.76 | -0.70 |
| mitigation->fvg_cb | 6 | 66.7 | -0.381 | -0.397 | -0.289 | no | -0.77 | +0.01 |
| fvg_cb->inducement | 5 | 40.0 | -0.358 | -0.289 | -0.308 | no | -1.19 | -0.15 |
| compression_fade->fvg_cb | 5 | 0.0 | -1.234 | -0.333 | -0.289 | no | -1.25 | -1.17 |
| fvg_cb->ob_lux | 5 | 100.0 | -0.802 | -0.289 | -0.349 | no | -1.21 | +0.84 |

### Loss decomposition

**RELIANCE** (n=2079 trades, k=1.5 fixed_t1). All figures R/trade; ledger sums exactly to observed net.

| item | R/trade | note |
|---|---|---|
| target hits (+1R x 47.2%) | +0.472 | favorable capture actually banked |
| stop-outs (-1R x 46.6%) | -0.466 | split below |
| &nbsp;&nbsp;... of which WRONG-direction stops | -0.188 | (a) direction wrongness |
| &nbsp;&nbsp;... of which SHAKEOUT stops | -0.056 | (b) stop tax: move was there, stop died first |
| &nbsp;&nbsp;... of which CHOP/WIN-class stops | -0.222 | noise stops |
| EOD flat exits (6.3% of trades) | +0.002 | neither side reached |
| = idealized pre-cost expectancy E0 | +0.008 | (d) the symmetric-payoff ceiling: mean MFE 3.31 ATR vs MAE 3.26 ATR (ratio 1.01); capture ceiling min(MFE,1R) = +0.808 R |
| + stop overshoot (gap-through fills) | -0.000 | (b) stop tax, part 2 |
| + costs & frictions (fees+STT+spread+slip+rounding+size-cap) | -0.360 | (c) |
| **= observed net** | **-0.353** | |

---

## HDFCBANK

### Per-tool

| tool | n | hit% | undec% | base% | edge pp | net_t1 R | net_t3 R |
|---|---|---|---|---|---|---|---|
| ob_lux | 561 | 51.2 | 2.0 | 39.7 | +11.5 | -0.301 | -0.315 |
| compression_fade | 886 | 47.0 | 4.2 | 37.8 | +9.1 | -0.327 | -0.303 |
| fvg_cb | 248 | 53.6 | 2.0 | 41.8 | +11.8 | -0.246 | -0.319 |
| mitigation | 319 | 45.8 | 2.5 | 36.0 | +9.8 | -0.405 | -0.414 |
| bpr | 68 | 50.0 | 4.4 | 42.3 | +7.7 | -0.342 | -0.320 |
| inducement | 71 | 47.9 | 1.4 | 35.0 | +12.9 | -0.438 | -0.450 |
| propulsion_block | 42 | 47.6 | 4.8 | 34.5 | +13.1 | -0.205 | -0.402 |
| turtle_soup | 25 | 40.0 | 8.0 | 40.0 | +0.0 | -0.467 | -0.694 |
| ALL | 2220 | 48.6 | 3.1 | 38.5 | +10.2 | -0.326 | -0.335 |

### Autopsy (all trades classified; stop k=1.5 ATR)

| tool | n | WIN% | WRONG% | SHAKEOUT% | CHOP% | stopped% | med need-k (ATR) |
|---|---|---|---|---|---|---|---|
| ob_lux | 561 | 17.3 | 27.1 | 4.8 | 50.8 | 63.6 | 2.18 (=1.5x) |
| compression_fade | 886 | 15.6 | 18.8 | 5.9 | 59.7 | 60.9 | 2.20 (=1.5x) |
| fvg_cb | 248 | 15.3 | 18.5 | 4.4 | 61.7 | 67.7 | 2.28 (=1.5x) |
| mitigation | 319 | 13.8 | 22.9 | 6.3 | 57.1 | 64.9 | 1.86 (=1.2x) |
| bpr | 68 | 14.7 | 16.2 | 4.4 | 64.7 | 63.2 | 3.18 (=2.1x) |
| inducement | 71 | 15.5 | 25.4 | 2.8 | 56.3 | 66.2 | 2.05 (=1.4x) |
| propulsion_block | 42 | 14.3 | 19.0 | 4.8 | 61.9 | 64.3 | 2.62 (=1.7x) |
| turtle_soup | 25 | 8.0 | 20.0 | 8.0 | 64.0 | 68.0 | 2.11 (=1.4x) |
| ALL | 2220 | 15.6 | 21.6 | 5.4 | 57.4 | 63.3 | 2.16 (=1.4x) |

### Co-fire pairs (same dir, <=3 bars, zone mids <=0.5 ATR; entry at later signal)

| pair (+) | n | hit% | net_t1 | solo A | solo B | beats both | H1 | H2 |
|---|---|---|---|---|---|---|---|---|
| compression_fade+ob_lux | 143 | 51.0 | -0.306 | -0.327 | -0.301 | no | +0.02 | -0.57 |
| mitigation+ob_lux | 126 | 40.5 | -0.523 | -0.405 | -0.301 | no | -0.13 | -0.82 |
| compression_fade+mitigation | 87 | 46.0 | -0.453 | -0.327 | -0.405 | no | -0.34 | -0.55 |
| compression_fade+fvg_cb | 44 | 40.9 | -0.354 | -0.327 | -0.246 | no | -0.31 | -0.40 |
| compression_fade+inducement | 33 | 54.5 | -0.296 | -0.327 | -0.438 | **YES** | -0.31 | -0.28 |
| bpr+compression_fade | 29 | 58.6 | -0.001 | -0.342 | -0.327 | **YES** | +0.06 | -0.04 |
| inducement+ob_lux | 21 | 33.3 | -0.539 | -0.438 | -0.301 | no | -0.80 | +0.12 |
| compression_fade+propulsion_block | 15 | 40.0 | -0.537 | -0.327 | -0.205 | no | -0.57 | -0.51 |
| mitigation+propulsion_block | 15 | 40.0 | -0.224 | -0.405 | -0.205 | no | -0.21 | -0.24 |
| bpr+fvg_cb | 13 | 53.8 | -0.136 | -0.342 | -0.246 | **YES** | +0.15 | -0.39 |
| fvg_cb+ob_lux | 13 | 30.8 | +0.023 | -0.246 | -0.301 | **YES** | -1.38 | +0.65 |
| inducement+mitigation | 11 | 45.5 | -0.733 | -0.438 | -0.405 | no | -0.77 | -0.69 |
| ob_lux+propulsion_block | 7 | 57.1 | +0.509 | -0.301 | -0.205 | **YES** | +0.45 | +0.85 |
| compression_fade+turtle_soup | 6 | 50.0 | -0.007 | -0.327 | -0.467 | **YES** | -0.17 | +0.82 |
| bpr+mitigation | 6 | 16.7 | -0.601 | -0.342 | -0.405 | no | +0.58 | -0.84 |

### Sequence chains A->B (1..6 bars, same dir, zone <=0.5 ATR; entry at B)

| pair (->) | n | hit% | net_t1 | solo A | solo B | beats both | H1 | H2 |
|---|---|---|---|---|---|---|---|---|
| compression_fade->ob_lux | 129 | 51.9 | -0.231 | -0.327 | -0.301 | **YES** | +0.20 | -0.59 |
| mitigation->ob_lux | 98 | 36.7 | -0.556 | -0.405 | -0.301 | no | -0.09 | -0.95 |
| mitigation->compression_fade | 61 | 34.4 | -0.581 | -0.405 | -0.327 | no | -0.50 | -0.65 |
| ob_lux->compression_fade | 49 | 42.9 | -0.499 | -0.301 | -0.327 | no | -0.57 | -0.44 |
| compression_fade->mitigation | 43 | 53.5 | -0.408 | -0.327 | -0.405 | no | -0.37 | -0.44 |
| fvg_cb->compression_fade | 32 | 34.4 | -0.552 | -0.246 | -0.327 | no | -0.68 | -0.40 |
| compression_fade->inducement | 18 | 55.6 | -0.380 | -0.327 | -0.438 | no | -0.47 | -0.29 |
| ob_lux->mitigation | 17 | 47.1 | -0.399 | -0.301 | -0.405 | no | -0.48 | -0.31 |
| bpr->compression_fade | 16 | 62.5 | +0.041 | -0.342 | -0.327 | **YES** | +0.15 | -0.01 |
| inducement->compression_fade | 15 | 53.3 | -0.236 | -0.438 | -0.327 | **YES** | +0.31 | -0.51 |
| inducement->ob_lux | 12 | 16.7 | -0.972 | -0.438 | -0.301 | no | -0.97 | - |
| propulsion_block->ob_lux | 9 | 77.8 | +0.298 | -0.205 | -0.301 | **YES** | +0.80 | -0.10 |
| compression_fade->bpr | 8 | 37.5 | -0.520 | -0.327 | -0.342 | no | -0.75 | -0.29 |
| propulsion_block->compression_fade | 7 | 14.3 | -0.948 | -0.205 | -0.327 | no | -1.30 | -0.81 |
| ob_lux->inducement | 7 | 42.9 | -0.203 | -0.301 | -0.438 | **YES** | -0.14 | -0.25 |
| mitigation->propulsion_block | 7 | 28.6 | -0.042 | -0.405 | -0.205 | **YES** | -0.53 | +0.33 |
| compression_fade->fvg_cb | 7 | 42.9 | -0.226 | -0.327 | -0.246 | **YES** | +0.04 | -0.57 |
| mitigation->inducement | 6 | 50.0 | -0.800 | -0.405 | -0.438 | no | -0.88 | -0.40 |
| compression_fade->turtle_soup | 5 | 60.0 | +0.252 | -0.327 | -0.467 | **YES** | +0.11 | +0.82 |
| fvg_cb->ob_lux | 5 | 20.0 | -0.930 | -0.246 | -0.301 | no | -1.38 | +0.87 |
| ob_lux->fvg_cb | 5 | 40.0 | +0.469 | -0.301 | -0.246 | **YES** | - | +0.47 |

### Loss decomposition

**HDFCBANK** (n=2220 trades, k=1.5 fixed_t1). All figures R/trade; ledger sums exactly to observed net.

| item | R/trade | note |
|---|---|---|
| target hits (+1R x 45.8%) | +0.458 | favorable capture actually banked |
| stop-outs (-1R x 48.6%) | -0.486 | split below |
| &nbsp;&nbsp;... of which WRONG-direction stops | -0.173 | (a) direction wrongness |
| &nbsp;&nbsp;... of which SHAKEOUT stops | -0.049 | (b) stop tax: move was there, stop died first |
| &nbsp;&nbsp;... of which CHOP/WIN-class stops | -0.264 | noise stops |
| EOD flat exits (5.6% of trades) | +0.004 | neither side reached |
| = idealized pre-cost expectancy E0 | -0.025 | (d) the symmetric-payoff ceiling: mean MFE 2.99 ATR vs MAE 3.17 ATR (ratio 0.94); capture ceiling min(MFE,1R) = +0.787 R |
| + stop overshoot (gap-through fills) | -0.000 | (b) stop tax, part 2 |
| + costs & frictions (fees+STT+spread+slip+rounding+size-cap) | -0.301 | (c) |
| **= observed net** | **-0.326** | |

---

## INFY

### Per-tool

| tool | n | hit% | undec% | base% | edge pp | net_t1 R | net_t3 R |
|---|---|---|---|---|---|---|---|
| ob_lux | 539 | 44.5 | 3.0 | 39.1 | +5.4 | -0.418 | -0.504 |
| compression_fade | 907 | 48.1 | 4.4 | 39.6 | +8.4 | -0.272 | -0.336 |
| fvg_cb | 248 | 42.7 | 7.7 | 37.1 | +5.6 | -0.143 | -0.323 |
| mitigation | 318 | 44.3 | 4.4 | 40.8 | +3.5 | -0.239 | -0.199 |
| bpr | 106 | 40.6 | 4.7 | 34.8 | +5.8 | -0.292 | -0.302 |
| inducement | 67 | 59.7 | 1.5 | 40.1 | +19.6 | -0.037 | +0.019 |
| propulsion_block | 30 | 46.7 | 3.3 | 37.2 | +9.5 | -0.453 | -0.628 |
| turtle_soup | 45 | 33.3 | 4.4 | 40.3 | -7.0 | -0.616 | -0.612 |
| ALL | 2260 | 45.8 | 4.3 | 39.2 | +6.6 | -0.291 | -0.353 |

### Autopsy (all trades classified; stop k=1.5 ATR)

| tool | n | WIN% | WRONG% | SHAKEOUT% | CHOP% | stopped% | med need-k (ATR) |
|---|---|---|---|---|---|---|---|
| ob_lux | 539 | 11.5 | 21.5 | 2.0 | 64.9 | 67.7 | 1.78 (=1.2x) |
| compression_fade | 907 | 13.3 | 17.0 | 4.0 | 65.7 | 59.6 | 2.04 (=1.4x) |
| fvg_cb | 248 | 12.9 | 13.3 | 2.0 | 71.8 | 59.7 | 1.95 (=1.3x) |
| mitigation | 318 | 15.1 | 12.9 | 5.0 | 67.0 | 54.1 | 2.21 (=1.5x) |
| bpr | 106 | 15.1 | 11.3 | 6.6 | 67.0 | 57.5 | 1.62 (=1.1x) |
| inducement | 67 | 25.4 | 14.9 | 1.5 | 58.2 | 53.7 | 2.95 (=2.0x) |
| propulsion_block | 30 | 3.3 | 23.3 | 6.7 | 66.7 | 66.7 | 1.62 (=1.1x) |
| turtle_soup | 45 | 8.9 | 31.1 | 13.3 | 46.7 | 71.1 | 2.38 (=1.6x) |
| ALL | 2260 | 13.3 | 17.1 | 3.7 | 65.8 | 60.8 | 2.05 (=1.4x) |

### Co-fire pairs (same dir, <=3 bars, zone mids <=0.5 ATR; entry at later signal)

| pair (+) | n | hit% | net_t1 | solo A | solo B | beats both | H1 | H2 |
|---|---|---|---|---|---|---|---|---|
| compression_fade+ob_lux | 116 | 39.7 | -0.474 | -0.272 | -0.418 | no | -0.15 | -0.86 |
| mitigation+ob_lux | 115 | 46.1 | -0.246 | -0.239 | -0.418 | no | -0.07 | -0.47 |
| compression_fade+mitigation | 85 | 41.2 | -0.326 | -0.272 | -0.239 | no | -0.07 | -0.53 |
| bpr+fvg_cb | 53 | 35.8 | -0.229 | -0.292 | -0.143 | no | -0.13 | -0.24 |
| bpr+compression_fade | 51 | 37.3 | -0.184 | -0.292 | -0.272 | **YES** | +0.23 | -0.39 |
| compression_fade+fvg_cb | 46 | 41.3 | -0.142 | -0.272 | -0.143 | **YES** | -0.57 | +0.06 |
| compression_fade+inducement | 24 | 66.7 | +0.236 | -0.272 | -0.037 | **YES** | +0.34 | +0.14 |
| compression_fade+turtle_soup | 19 | 42.1 | -0.418 | -0.272 | -0.616 | no | -0.83 | +0.15 |
| ob_lux+propulsion_block | 13 | 30.8 | -0.302 | -0.418 | -0.453 | **YES** | -0.21 | -0.80 |
| inducement+ob_lux | 12 | 8.3 | -0.504 | -0.037 | -0.418 | no | -0.43 | -0.85 |
| mitigation+propulsion_block | 10 | 60.0 | -0.276 | -0.239 | -0.453 | no | -0.17 | -0.52 |
| mitigation+turtle_soup | 10 | 30.0 | -0.971 | -0.239 | -0.616 | no | -1.10 | -0.78 |
| bpr+ob_lux | 9 | 77.8 | -0.157 | -0.292 | -0.418 | **YES** | +0.75 | -1.29 |
| fvg_cb+mitigation | 8 | 37.5 | -0.409 | -0.143 | -0.239 | no | -0.41 | - |
| fvg_cb+ob_lux | 6 | 83.3 | +0.108 | -0.143 | -0.418 | **YES** | -0.27 | +0.86 |
| bpr+mitigation | 6 | 33.3 | -0.541 | -0.292 | -0.239 | no | -0.58 | -0.50 |
| inducement+mitigation | 5 | 40.0 | -0.206 | -0.037 | -0.239 | no | -0.50 | +0.23 |

### Sequence chains A->B (1..6 bars, same dir, zone <=0.5 ATR; entry at B)

| pair (->) | n | hit% | net_t1 | solo A | solo B | beats both | H1 | H2 |
|---|---|---|---|---|---|---|---|---|
| compression_fade->ob_lux | 109 | 44.0 | -0.521 | -0.272 | -0.418 | no | -0.26 | -0.89 |
| mitigation->ob_lux | 94 | 41.5 | -0.344 | -0.239 | -0.418 | no | -0.08 | -0.72 |
| mitigation->compression_fade | 66 | 43.9 | -0.341 | -0.239 | -0.272 | no | -0.35 | -0.33 |
| ob_lux->compression_fade | 43 | 37.2 | -0.308 | -0.418 | -0.272 | no | -0.05 | -0.67 |
| compression_fade->mitigation | 36 | 41.7 | -0.303 | -0.272 | -0.239 | no | -0.25 | -0.38 |
| bpr->compression_fade | 30 | 43.3 | -0.318 | -0.292 | -0.272 | no | -0.01 | -0.45 |
| fvg_cb->compression_fade | 29 | 44.8 | -0.213 | -0.143 | -0.272 | no | -0.24 | -0.21 |
| compression_fade->inducement | 20 | 65.0 | -0.007 | -0.272 | -0.037 | **YES** | +0.02 | -0.03 |
| compression_fade->fvg_cb | 16 | 43.8 | +0.314 | -0.272 | -0.143 | **YES** | +0.42 | +0.26 |
| inducement->compression_fade | 14 | 64.3 | +0.003 | -0.037 | -0.272 | **YES** | -0.09 | +0.18 |
| compression_fade->bpr | 11 | 45.5 | -0.143 | -0.272 | -0.292 | **YES** | +0.11 | -0.24 |
| ob_lux->mitigation | 9 | 22.2 | -0.841 | -0.418 | -0.239 | no | -0.70 | -1.32 |
| mitigation->fvg_cb | 9 | 22.2 | -0.086 | -0.239 | -0.143 | **YES** | -0.11 | +0.13 |
| inducement->ob_lux | 9 | 44.4 | -0.091 | -0.037 | -0.418 | no | -0.07 | -0.15 |
| turtle_soup->compression_fade | 9 | 66.7 | +0.094 | -0.616 | -0.272 | **YES** | -0.79 | +0.80 |
| fvg_cb->bpr | 9 | 44.4 | -0.486 | -0.143 | -0.292 | no | -0.16 | -0.58 |
| propulsion_block->ob_lux | 8 | 50.0 | -0.119 | -0.453 | -0.418 | **YES** | -0.08 | -0.40 |
| bpr->mitigation | 8 | 25.0 | -0.730 | -0.292 | -0.239 | no | -0.57 | -0.82 |
| bpr->fvg_cb | 8 | 37.5 | -0.184 | -0.292 | -0.143 | no | -1.10 | -0.05 |
| fvg_cb->ob_lux | 7 | 57.1 | -0.677 | -0.143 | -0.418 | no | -0.60 | -1.13 |
| ob_lux->inducement | 6 | 0.0 | -0.787 | -0.418 | -0.037 | no | -0.76 | -0.85 |
| mitigation->inducement | 6 | 66.7 | +0.272 | -0.239 | -0.037 | **YES** | +0.81 | +0.00 |
| fvg_cb->mitigation | 5 | 60.0 | +0.159 | -0.143 | -0.239 | **YES** | +0.50 | -1.20 |
| bpr->ob_lux | 5 | 60.0 | -0.468 | -0.292 | -0.418 | no | +0.75 | -1.28 |
| turtle_soup->ob_lux | 5 | 0.0 | -1.311 | -0.616 | -0.418 | no | -1.31 | - |

### Loss decomposition

**INFY** (n=2260 trades, k=1.5 fixed_t1). All figures R/trade; ledger sums exactly to observed net.

| item | R/trade | note |
|---|---|---|
| target hits (+1R x 47.7%) | +0.477 | favorable capture actually banked |
| stop-outs (-1R x 46.0%) | -0.460 | split below |
| &nbsp;&nbsp;... of which WRONG-direction stops | -0.140 | (a) direction wrongness |
| &nbsp;&nbsp;... of which SHAKEOUT stops | -0.031 | (b) stop tax: move was there, stop died first |
| &nbsp;&nbsp;... of which CHOP/WIN-class stops | -0.290 | noise stops |
| EOD flat exits (6.2% of trades) | +0.001 | neither side reached |
| = idealized pre-cost expectancy E0 | +0.019 | (d) the symmetric-payoff ceiling: mean MFE 2.64 ATR vs MAE 2.73 ATR (ratio 0.97); capture ceiling min(MFE,1R) = +0.791 R |
| + stop overshoot (gap-through fills) | -0.000 | (b) stop tax, part 2 |
| + costs & frictions (fees+STT+spread+slip+rounding+size-cap) | -0.310 | (c) |
| **= observed net** | **-0.291** | |

---

## TATASTEEL

### Per-tool

| tool | n | hit% | undec% | base% | edge pp | net_t1 R | net_t3 R |
|---|---|---|---|---|---|---|---|
| ob_lux | 603 | 49.8 | 5.6 | 38.9 | +10.9 | -0.287 | -0.339 |
| compression_fade | 969 | 48.2 | 3.1 | 38.6 | +9.6 | -0.356 | -0.366 |
| fvg_cb | 278 | 46.8 | 4.3 | 39.2 | +7.5 | -0.320 | -0.447 |
| mitigation | 315 | 46.3 | 3.5 | 39.6 | +6.8 | -0.340 | -0.474 |
| bpr | 63 | 55.6 | 0.0 | 44.2 | +11.3 | -0.327 | -0.433 |
| inducement | 68 | 48.5 | 1.5 | 32.5 | +16.0 | -0.438 | -0.350 |
| propulsion_block | 39 | 64.1 | 0.0 | 43.7 | +20.4 | -0.155 | +0.046 |
| turtle_soup | 30 | 63.3 | 0.0 | 47.2 | +16.2 | -0.235 | -0.642 |
| ALL | 2365 | 48.8 | 3.7 | 39.0 | +9.8 | -0.329 | -0.381 |

### Autopsy (all trades classified; stop k=1.5 ATR)

| tool | n | WIN% | WRONG% | SHAKEOUT% | CHOP% | stopped% | med need-k (ATR) |
|---|---|---|---|---|---|---|---|
| ob_lux | 603 | 10.1 | 17.4 | 2.2 | 70.3 | 51.9 | 1.68 (=1.1x) |
| compression_fade | 969 | 13.2 | 18.9 | 4.4 | 63.5 | 60.2 | 2.13 (=1.4x) |
| fvg_cb | 278 | 12.9 | 12.6 | 6.1 | 68.3 | 65.5 | 2.12 (=1.4x) |
| mitigation | 315 | 11.7 | 21.0 | 2.5 | 64.8 | 62.5 | 2.08 (=1.4x) |
| bpr | 63 | 14.3 | 22.2 | 7.9 | 55.6 | 69.8 | 1.93 (=1.3x) |
| inducement | 68 | 13.2 | 17.6 | 1.5 | 67.6 | 61.8 | 2.89 (=1.9x) |
| propulsion_block | 39 | 28.2 | 17.9 | 5.1 | 48.7 | 64.1 | 1.64 (=1.1x) |
| turtle_soup | 30 | 13.3 | 26.7 | 3.3 | 56.7 | 80.0 | 2.89 (=1.9x) |
| ALL | 2365 | 12.5 | 18.2 | 3.8 | 65.5 | 59.6 | 1.98 (=1.3x) |

### Co-fire pairs (same dir, <=3 bars, zone mids <=0.5 ATR; entry at later signal)

| pair (+) | n | hit% | net_t1 | solo A | solo B | beats both | H1 | H2 |
|---|---|---|---|---|---|---|---|---|
| compression_fade+ob_lux | 137 | 54.0 | -0.233 | -0.356 | -0.287 | **YES** | -0.08 | -0.41 |
| mitigation+ob_lux | 118 | 53.4 | -0.232 | -0.340 | -0.287 | **YES** | -0.32 | -0.14 |
| compression_fade+mitigation | 98 | 59.2 | -0.244 | -0.356 | -0.340 | **YES** | -0.23 | -0.25 |
| compression_fade+fvg_cb | 61 | 67.2 | -0.167 | -0.356 | -0.320 | **YES** | -0.41 | +0.02 |
| compression_fade+inducement | 33 | 45.5 | -0.389 | -0.356 | -0.438 | no | -0.45 | -0.34 |
| bpr+compression_fade | 25 | 56.0 | -0.329 | -0.327 | -0.356 | no | -0.09 | -0.52 |
| bpr+fvg_cb | 21 | 71.4 | -0.743 | -0.327 | -0.320 | no | -0.69 | -0.78 |
| fvg_cb+ob_lux | 14 | 42.9 | -0.208 | -0.320 | -0.287 | **YES** | +0.81 | -0.38 |
| ob_lux+propulsion_block | 11 | 54.5 | -0.322 | -0.287 | -0.155 | no | -1.32 | -0.10 |
| inducement+ob_lux | 10 | 30.0 | -0.615 | -0.438 | -0.287 | no | -0.89 | -0.20 |
| compression_fade+propulsion_block | 10 | 70.0 | -0.022 | -0.356 | -0.155 | **YES** | -0.30 | +0.05 |
| bpr+mitigation | 9 | 66.7 | -0.149 | -0.327 | -0.340 | **YES** | -0.03 | -0.30 |
| ob_lux+turtle_soup | 7 | 14.3 | -1.245 | -0.287 | -0.235 | no | -1.21 | -1.30 |
| mitigation+propulsion_block | 7 | 57.1 | -0.066 | -0.340 | -0.155 | **YES** | +0.19 | -0.26 |
| fvg_cb+mitigation | 6 | 66.7 | -0.571 | -0.320 | -0.340 | no | -1.26 | -0.22 |
| compression_fade+turtle_soup | 5 | 60.0 | -0.865 | -0.356 | -0.235 | no | -0.57 | -1.30 |

### Sequence chains A->B (1..6 bars, same dir, zone <=0.5 ATR; entry at B)

| pair (->) | n | hit% | net_t1 | solo A | solo B | beats both | H1 | H2 |
|---|---|---|---|---|---|---|---|---|
| compression_fade->ob_lux | 132 | 50.0 | -0.287 | -0.356 | -0.287 | no | -0.13 | -0.50 |
| mitigation->ob_lux | 108 | 52.8 | -0.250 | -0.340 | -0.287 | **YES** | -0.34 | -0.14 |
| mitigation->compression_fade | 57 | 63.2 | -0.388 | -0.340 | -0.356 | no | -0.58 | -0.27 |
| ob_lux->compression_fade | 48 | 45.8 | -0.225 | -0.287 | -0.356 | **YES** | -0.07 | -0.46 |
| fvg_cb->compression_fade | 34 | 70.6 | +0.192 | -0.320 | -0.356 | **YES** | -0.10 | +0.42 |
| compression_fade->mitigation | 33 | 51.5 | -0.176 | -0.356 | -0.340 | **YES** | -0.01 | -0.34 |
| compression_fade->inducement | 20 | 50.0 | -0.346 | -0.356 | -0.438 | **YES** | -0.55 | -0.10 |
| ob_lux->mitigation | 18 | 38.9 | -0.371 | -0.287 | -0.340 | no | -0.23 | -0.46 |
| inducement->compression_fade | 17 | 23.5 | -0.396 | -0.438 | -0.356 | no | -0.20 | -0.68 |
| bpr->compression_fade | 13 | 76.9 | +0.092 | -0.327 | -0.356 | **YES** | -0.04 | +0.20 |
| inducement->ob_lux | 10 | 40.0 | -0.424 | -0.438 | -0.287 | no | -0.66 | +0.13 |
| fvg_cb->ob_lux | 10 | 50.0 | +0.001 | -0.320 | -0.287 | **YES** | - | +0.00 |
| propulsion_block->compression_fade | 8 | 62.5 | +0.050 | -0.155 | -0.356 | **YES** | -0.55 | +0.41 |
| turtle_soup->ob_lux | 8 | 0.0 | -1.083 | -0.235 | -0.287 | no | -1.01 | -1.30 |
| compression_fade->fvg_cb | 8 | 100.0 | +0.434 | -0.356 | -0.320 | **YES** | +0.51 | +0.36 |
| propulsion_block->ob_lux | 6 | 50.0 | -0.217 | -0.155 | -0.287 | no | -1.30 | +0.00 |
| mitigation->bpr | 5 | 80.0 | -0.087 | -0.340 | -0.327 | **YES** | -0.62 | +0.71 |
| compression_fade->bpr | 5 | 80.0 | -0.442 | -0.356 | -0.327 | no | -0.60 | -0.21 |
| bpr->mitigation | 5 | 80.0 | +0.369 | -0.327 | -0.340 | **YES** | +0.80 | -0.28 |
| mitigation->fvg_cb | 5 | 100.0 | +0.012 | -0.340 | -0.320 | **YES** | -1.21 | +0.32 |
| compression_fade->propulsion_block | 5 | 40.0 | -0.461 | -0.356 | -0.155 | no | -1.35 | -0.24 |
| mitigation->propulsion_block | 5 | 60.0 | +0.022 | -0.340 | -0.155 | **YES** | +0.22 | -0.28 |

### Loss decomposition

**TATASTEEL** (n=2365 trades, k=1.5 fixed_t1). All figures R/trade; ledger sums exactly to observed net.

| item | R/trade | note |
|---|---|---|
| target hits (+1R x 46.1%) | +0.461 | favorable capture actually banked |
| stop-outs (-1R x 45.5%) | -0.455 | split below |
| &nbsp;&nbsp;... of which WRONG-direction stops | -0.142 | (a) direction wrongness |
| &nbsp;&nbsp;... of which SHAKEOUT stops | -0.035 | (b) stop tax: move was there, stop died first |
| &nbsp;&nbsp;... of which CHOP/WIN-class stops | -0.278 | noise stops |
| EOD flat exits (8.4% of trades) | +0.000 | neither side reached |
| = idealized pre-cost expectancy E0 | +0.007 | (d) the symmetric-payoff ceiling: mean MFE 2.69 ATR vs MAE 2.67 ATR (ratio 1.00); capture ceiling min(MFE,1R) = +0.798 R |
| + stop overshoot (gap-through fills) | -0.003 | (b) stop tax, part 2 |
| + costs & frictions (fees+STT+spread+slip+rounding+size-cap) | -0.333 | (c) |
| **= observed net** | **-0.329** | |

---

## HINDUNILVR

### Per-tool

| tool | n | hit% | undec% | base% | edge pp | net_t1 R | net_t3 R |
|---|---|---|---|---|---|---|---|
| ob_lux | 576 | 52.8 | 2.1 | 45.0 | +7.8 | -0.227 | -0.239 |
| compression_fade | 847 | 51.5 | 1.9 | 40.1 | +11.4 | -0.299 | -0.269 |
| fvg_cb | 255 | 48.2 | 3.1 | 39.1 | +9.2 | -0.293 | -0.408 |
| mitigation | 287 | 47.0 | 1.0 | 38.0 | +9.0 | -0.354 | -0.386 |
| bpr | 89 | 56.2 | 4.5 | 42.3 | +13.9 | -0.235 | -0.152 |
| inducement | 62 | 41.9 | 0.0 | 36.0 | +5.9 | -0.450 | -0.363 |
| propulsion_block | 46 | 50.0 | 2.2 | 37.5 | +12.5 | -0.404 | -0.218 |
| turtle_soup | 42 | 50.0 | 0.0 | 38.9 | +11.1 | -0.113 | -0.604 |
| ALL | 2204 | 50.7 | 2.0 | 40.9 | +9.8 | -0.287 | -0.296 |

### Autopsy (all trades classified; stop k=1.5 ATR)

| tool | n | WIN% | WRONG% | SHAKEOUT% | CHOP% | stopped% | med need-k (ATR) |
|---|---|---|---|---|---|---|---|
| ob_lux | 576 | 18.4 | 24.0 | 5.6 | 52.1 | 58.5 | 2.04 (=1.4x) |
| compression_fade | 847 | 16.8 | 21.7 | 3.5 | 58.0 | 61.0 | 1.97 (=1.3x) |
| fvg_cb | 255 | 12.2 | 18.4 | 4.7 | 64.7 | 65.9 | 1.80 (=1.2x) |
| mitigation | 287 | 16.4 | 27.2 | 5.2 | 51.2 | 64.1 | 2.13 (=1.4x) |
| bpr | 89 | 20.2 | 22.5 | 2.2 | 55.1 | 55.1 | 2.38 (=1.6x) |
| inducement | 62 | 19.4 | 22.6 | 3.2 | 54.8 | 61.3 | 2.04 (=1.4x) |
| propulsion_block | 46 | 15.2 | 19.6 | 2.2 | 63.0 | 52.2 | 1.71 (=1.1x) |
| turtle_soup | 42 | 4.8 | 19.0 | 7.1 | 69.0 | 61.9 | 2.92 (=1.9x) |
| ALL | 2204 | 16.6 | 22.6 | 4.4 | 56.4 | 60.9 | 1.96 (=1.3x) |

### Co-fire pairs (same dir, <=3 bars, zone mids <=0.5 ATR; entry at later signal)

| pair (+) | n | hit% | net_t1 | solo A | solo B | beats both | H1 | H2 |
|---|---|---|---|---|---|---|---|---|
| compression_fade+ob_lux | 117 | 54.7 | -0.157 | -0.299 | -0.227 | **YES** | +0.06 | -0.43 |
| mitigation+ob_lux | 92 | 41.3 | -0.544 | -0.354 | -0.227 | no | -0.36 | -0.78 |
| compression_fade+mitigation | 73 | 50.7 | -0.323 | -0.299 | -0.354 | no | -0.32 | -0.33 |
| compression_fade+fvg_cb | 38 | 44.7 | -0.204 | -0.299 | -0.293 | **YES** | +0.02 | -0.51 |
| bpr+compression_fade | 30 | 63.3 | -0.211 | -0.235 | -0.299 | **YES** | -0.26 | -0.19 |
| inducement+ob_lux | 18 | 50.0 | -0.551 | -0.450 | -0.227 | no | -0.79 | -0.31 |
| compression_fade+inducement | 17 | 52.9 | -0.124 | -0.299 | -0.450 | **YES** | -0.25 | -0.05 |
| compression_fade+propulsion_block | 16 | 37.5 | -0.439 | -0.299 | -0.404 | no | -0.34 | -0.50 |
| bpr+fvg_cb | 16 | 56.2 | -0.013 | -0.235 | -0.293 | **YES** | +0.13 | -0.25 |
| fvg_cb+ob_lux | 16 | 68.8 | -0.211 | -0.293 | -0.227 | **YES** | -0.40 | +0.35 |
| ob_lux+propulsion_block | 15 | 40.0 | -0.457 | -0.227 | -0.404 | no | -0.24 | -0.90 |
| fvg_cb+mitigation | 11 | 45.5 | -0.704 | -0.293 | -0.354 | no | -0.98 | -0.23 |
| mitigation+propulsion_block | 9 | 55.6 | -0.896 | -0.354 | -0.404 | no | -0.78 | -0.99 |
| bpr+mitigation | 8 | 75.0 | +0.365 | -0.235 | -0.354 | **YES** | +0.47 | +0.26 |
| inducement+mitigation | 7 | 28.6 | -0.372 | -0.450 | -0.354 | no | -0.48 | -0.29 |
| bpr+ob_lux | 7 | 100.0 | +0.638 | -0.235 | -0.227 | **YES** | +0.79 | +0.52 |
| compression_fade+turtle_soup | 6 | 66.7 | +0.227 | -0.299 | -0.113 | **YES** | +0.70 | -0.01 |
| fvg_cb+propulsion_block | 5 | 20.0 | -0.372 | -0.293 | -0.404 | no | -0.67 | +0.84 |

### Sequence chains A->B (1..6 bars, same dir, zone <=0.5 ATR; entry at B)

| pair (->) | n | hit% | net_t1 | solo A | solo B | beats both | H1 | H2 |
|---|---|---|---|---|---|---|---|---|
| compression_fade->ob_lux | 119 | 48.7 | -0.275 | -0.299 | -0.227 | no | -0.13 | -0.46 |
| mitigation->ob_lux | 98 | 42.9 | -0.598 | -0.354 | -0.227 | no | -0.47 | -0.76 |
| mitigation->compression_fade | 55 | 49.1 | -0.324 | -0.354 | -0.299 | no | -0.29 | -0.35 |
| ob_lux->compression_fade | 41 | 56.1 | -0.212 | -0.227 | -0.299 | **YES** | -0.09 | -0.37 |
| fvg_cb->compression_fade | 29 | 51.7 | -0.154 | -0.293 | -0.299 | **YES** | +0.08 | -0.40 |
| compression_fade->mitigation | 29 | 51.7 | -0.219 | -0.299 | -0.354 | **YES** | +0.07 | -0.42 |
| propulsion_block->ob_lux | 21 | 23.8 | -0.701 | -0.404 | -0.227 | no | -0.44 | -1.35 |
| ob_lux->mitigation | 18 | 33.3 | -0.623 | -0.227 | -0.354 | no | -0.64 | -0.60 |
| bpr->compression_fade | 18 | 33.3 | -0.476 | -0.235 | -0.299 | no | -0.54 | -0.43 |
| inducement->ob_lux | 18 | 44.4 | -0.677 | -0.450 | -0.227 | no | -0.90 | -0.33 |
| compression_fade->inducement | 17 | 47.1 | -0.245 | -0.299 | -0.450 | **YES** | -0.09 | -0.35 |
| propulsion_block->compression_fade | 12 | 25.0 | -0.450 | -0.404 | -0.299 | no | -0.16 | -0.74 |
| compression_fade->fvg_cb | 11 | 45.5 | -0.447 | -0.299 | -0.293 | no | -0.27 | -1.26 |
| fvg_cb->ob_lux | 9 | 77.8 | +0.119 | -0.293 | -0.227 | **YES** | -0.79 | +0.85 |
| compression_fade->propulsion_block | 7 | 71.4 | -0.481 | -0.299 | -0.404 | no | -1.30 | -0.15 |
| fvg_cb->mitigation | 6 | 50.0 | -0.636 | -0.293 | -0.354 | no | -0.56 | -0.79 |
| bpr->mitigation | 6 | 33.3 | -0.436 | -0.235 | -0.354 | no | -0.00 | -1.31 |
| bpr->ob_lux | 6 | 83.3 | +0.289 | -0.235 | -0.227 | **YES** | +0.29 | +0.28 |
| compression_fade->bpr | 6 | 83.3 | +0.194 | -0.299 | -0.235 | **YES** | +0.83 | +0.07 |
| mitigation->bpr | 5 | 80.0 | +0.457 | -0.354 | -0.235 | **YES** | +0.89 | +0.17 |
| fvg_cb->bpr | 5 | 80.0 | -0.082 | -0.293 | -0.235 | **YES** | -0.01 | -0.20 |
| bpr->fvg_cb | 5 | 40.0 | -0.413 | -0.235 | -0.293 | no | +0.15 | -1.25 |
| mitigation->fvg_cb | 5 | 60.0 | -0.435 | -0.354 | -0.293 | no | -1.26 | -0.23 |
| inducement->compression_fade | 5 | 40.0 | -0.098 | -0.450 | -0.299 | **YES** | -0.32 | +0.05 |
| mitigation->propulsion_block | 5 | 80.0 | -0.550 | -0.354 | -0.404 | no | - | -0.55 |

### Loss decomposition

**HINDUNILVR** (n=2204 trades, k=1.5 fixed_t1). All figures R/trade; ledger sums exactly to observed net.

| item | R/trade | note |
|---|---|---|
| target hits (+1R x 50.0%) | +0.500 | favorable capture actually banked |
| stop-outs (-1R x 44.8%) | -0.448 | split below |
| &nbsp;&nbsp;... of which WRONG-direction stops | -0.184 | (a) direction wrongness |
| &nbsp;&nbsp;... of which SHAKEOUT stops | -0.035 | (b) stop tax: move was there, stop died first |
| &nbsp;&nbsp;... of which CHOP/WIN-class stops | -0.229 | noise stops |
| EOD flat exits (5.2% of trades) | +0.000 | neither side reached |
| = idealized pre-cost expectancy E0 | +0.053 | (d) the symmetric-payoff ceiling: mean MFE 3.03 ATR vs MAE 2.97 ATR (ratio 1.02); capture ceiling min(MFE,1R) = +0.819 R |
| + stop overshoot (gap-through fills) | -0.006 | (b) stop tax, part 2 |
| + costs & frictions (fees+STT+spread+slip+rounding+size-cap) | -0.334 | (c) |
| **= observed net** | **-0.287** | |

---

# POOLED SYNTHESIS (5 stocks)

## Per-tool (pooled)

| tool | n | hit% | undec% | base% | edge pp | net_t1 R | net_t3 R |
|---|---|---|---|---|---|---|---|
| ob_lux | 2781 | 50.1 | 3.0 | 41.7 | +8.3 | -0.314 | -0.325 |
| compression_fade | 4481 | 48.9 | 3.5 | 39.4 | +9.5 | -0.318 | -0.323 |
| fvg_cb | 1243 | 47.9 | 4.7 | 39.5 | +8.4 | -0.259 | -0.352 |
| mitigation | 1538 | 46.3 | 3.4 | 38.4 | +7.9 | -0.346 | -0.376 |
| bpr | 365 | 49.6 | 4.4 | 40.5 | +9.1 | -0.329 | -0.300 |
| inducement | 336 | 50.3 | 0.9 | 35.5 | +14.8 | -0.334 | -0.271 |
| propulsion_block | 200 | 50.0 | 4.5 | 37.2 | +12.8 | -0.318 | -0.328 |
| turtle_soup | 184 | 44.6 | 2.7 | 40.9 | +3.6 | -0.415 | -0.582 |
| ALL | 11128 | 48.8 | 3.5 | 39.8 | +9.0 | -0.317 | -0.336 |

### Temporal halves

| tool | H1 net_t1 (n) | H2 net_t1 (n) |
|---|---|---|
| ob_lux | -0.233 (1414) | -0.398 (1367) |
| compression_fade | -0.290 (2223) | -0.345 (2258) |
| fvg_cb | -0.240 (589) | -0.276 (654) |
| mitigation | -0.319 (774) | -0.374 (764) |
| bpr | -0.309 (139) | -0.342 (226) |
| inducement | -0.400 (165) | -0.270 (171) |
| propulsion_block | -0.339 (99) | -0.298 (101) |
| turtle_soup | -0.387 (95) | -0.444 (89) |
| ALL | -0.281 (5498) | -0.352 (5630) |

## Autopsy (pooled)

| tool | n | WIN% | WRONG% | SHAKEOUT% | CHOP% | stopped% | med need-k (ATR) |
|---|---|---|---|---|---|---|---|
| ob_lux | 2781 | 15.7 | 22.4 | 4.4 | 57.5 | 60.7 | 2.00 (=1.3x) |
| compression_fade | 4481 | 15.3 | 19.8 | 4.9 | 60.0 | 60.8 | 2.20 (=1.5x) |
| fvg_cb | 1243 | 14.1 | 16.3 | 4.7 | 64.8 | 64.3 | 1.95 (=1.3x) |
| mitigation | 1538 | 14.2 | 22.2 | 4.7 | 58.9 | 61.8 | 2.12 (=1.4x) |
| bpr | 365 | 16.7 | 19.5 | 5.5 | 58.4 | 61.4 | 2.06 (=1.4x) |
| inducement | 336 | 19.0 | 20.8 | 3.0 | 57.1 | 61.3 | 2.38 (=1.6x) |
| propulsion_block | 200 | 15.0 | 20.0 | 7.0 | 58.0 | 59.5 | 1.96 (=1.3x) |
| turtle_soup | 184 | 10.9 | 26.1 | 7.1 | 56.0 | 70.1 | 2.28 (=1.5x) |
| ALL | 11128 | 15.2 | 20.5 | 4.8 | 59.5 | 61.5 | 2.10 (=1.4x) |

## Failure fingerprints (per tool, WRONG trades)

**ob_lux** (n=2781, WRONG=624 = 22.4% of all its trades). P(WRONG | stratum):

  - time-of-day: 09:15 25% (n=361)  10:15 18% (n=359)  11:15 35% (n=586)  12:15 25% (n=518)  13:15 25% (n=439)  14:15+ 6% (n=518)  
  - vs prev-day drift: WITH 21% (n=1485) | AGAINST 24% (n=1249)
  - at day-extreme (<=0.25 ATR in signal dir): AT 31% (n=13) | AWAY 22% (n=2768)

**compression_fade** (n=4481, WRONG=886 = 19.8% of all its trades). P(WRONG | stratum):

  - time-of-day: 09:15 18% (n=628)  10:15 22% (n=657)  11:15 30% (n=742)  12:15 25% (n=748)  13:15 20% (n=789)  14:15+ 7% (n=917)  
  - vs prev-day drift: WITH 21% (n=2209) | AGAINST 18% (n=2213)
  - at day-extreme (<=0.25 ATR in signal dir): AT 22% (n=41) | AWAY 20% (n=4440)

**fvg_cb** (n=1243, WRONG=203 = 16.3% of all its trades). P(WRONG | stratum):

  - time-of-day: 09:15 17% (n=642)  10:15 14% (n=166)  11:15 30% (n=114)  12:15 16% (n=92)  13:15 18% (n=99)  14:15+ 1% (n=130)  
  - vs prev-day drift: WITH 19% (n=691) | AGAINST 13% (n=542)
  - at day-extreme (<=0.25 ATR in signal dir): AT 29% (n=34) | AWAY 16% (n=1209)

**mitigation** (n=1538, WRONG=341 = 22.2% of all its trades). P(WRONG | stratum):

  - time-of-day: 09:15 27% (n=357)  10:15 20% (n=171)  11:15 33% (n=213)  12:15 30% (n=228)  13:15 20% (n=242)  14:15+ 7% (n=327)  
  - vs prev-day drift: WITH 23% (n=807) | AGAINST 21% (n=715)
  - at day-extreme (<=0.25 ATR in signal dir): AT 17% (n=36) | AWAY 22% (n=1502)

**bpr** (n=365, WRONG=71 = 19.5% of all its trades). P(WRONG | stratum):

  - time-of-day: 09:15 24% (n=80)  10:15 20% (n=49)  11:15 33% (n=67)  12:15 18% (n=61)  13:15 14% (n=49)  14:15+ 3% (n=59)  
  - vs prev-day drift: WITH 22% (n=175) | AGAINST 17% (n=190)
  - at day-extreme (<=0.25 ATR in signal dir): AT 33% (n=3) | AWAY 19% (n=362)

**inducement** (n=336, WRONG=70 = 20.8% of all its trades). P(WRONG | stratum):

  - time-of-day: 09:15 23% (n=70)  10:15 18% (n=82)  11:15 27% (n=59)  12:15 27% (n=37)  13:15 29% (n=35)  14:15+ 6% (n=53)  
  - vs prev-day drift: WITH 24% (n=199) | AGAINST 16% (n=134)
  - at day-extreme (<=0.25 ATR in signal dir): AT 14% (n=7) | AWAY 21% (n=329)

**propulsion_block** (n=200, WRONG=40 = 20.0% of all its trades). P(WRONG | stratum):

  - time-of-day: 09:15 26% (n=47)  10:15 14% (n=21)  11:15 36% (n=25)  12:15 24% (n=34)  13:15 29% (n=21)  14:15+ 4% (n=52)  
  - vs prev-day drift: WITH 22% (n=110) | AGAINST 19% (n=86)
  - at day-extreme (<=0.25 ATR in signal dir): AT 0% (n=4) | AWAY 20% (n=196)

**turtle_soup** (n=184, WRONG=48 = 26.1% of all its trades). P(WRONG | stratum):

  - time-of-day: 09:15 29% (n=59)  10:15 50% (n=8)  11:15 37% (n=27)  12:15 38% (n=13)  13:15 29% (n=28)  14:15+ 8% (n=49)  
  - vs prev-day drift: WITH 24% (n=94) | AGAINST 28% (n=88)
  - at day-extreme (<=0.25 ATR in signal dir): AT 20% (n=15) | AWAY 27% (n=169)

## Co-fire pairs (pooled, n>=10)

| pair (+) | n | hit% | net_t1 | solo A | solo B | beats both | H1 | H2 |
|---|---|---|---|---|---|---|---|---|
| compression_fade+ob_lux | 629 | 50.2 | -0.314 | -0.318 | -0.314 | no | -0.13 | -0.51 |
| mitigation+ob_lux | 530 | 45.5 | -0.371 | -0.346 | -0.314 | no | -0.23 | -0.51 |
| compression_fade+mitigation | 426 | 49.8 | -0.312 | -0.318 | -0.346 | **YES** | -0.22 | -0.38 |
| compression_fade+fvg_cb | 233 | 50.6 | -0.203 | -0.318 | -0.259 | **YES** | -0.26 | -0.14 |
| bpr+compression_fade | 155 | 50.3 | -0.192 | -0.329 | -0.318 | **YES** | -0.03 | -0.29 |
| compression_fade+inducement | 133 | 56.4 | -0.144 | -0.318 | -0.334 | **YES** | -0.29 | -0.02 |
| bpr+fvg_cb | 111 | 48.6 | -0.341 | -0.329 | -0.259 | no | -0.21 | -0.39 |
| inducement+ob_lux | 70 | 35.7 | -0.553 | -0.334 | -0.314 | no | -0.74 | -0.27 |
| compression_fade+propulsion_block | 56 | 46.4 | -0.406 | -0.318 | -0.318 | no | -0.50 | -0.33 |
| fvg_cb+ob_lux | 55 | 58.2 | -0.117 | -0.259 | -0.314 | **YES** | -0.48 | +0.21 |
| mitigation+propulsion_block | 54 | 57.4 | -0.266 | -0.346 | -0.318 | **YES** | -0.18 | -0.39 |
| ob_lux+propulsion_block | 52 | 38.5 | -0.323 | -0.314 | -0.318 | no | -0.28 | -0.40 |
| compression_fade+turtle_soup | 46 | 50.0 | -0.336 | -0.318 | -0.415 | no | -0.51 | -0.09 |
| fvg_cb+mitigation | 34 | 47.1 | -0.462 | -0.259 | -0.346 | no | -0.64 | -0.17 |
| inducement+mitigation | 32 | 37.5 | -0.459 | -0.334 | -0.346 | no | -0.52 | -0.40 |
| bpr+mitigation | 30 | 50.0 | -0.219 | -0.329 | -0.346 | **YES** | -0.05 | -0.36 |
| mitigation+turtle_soup | 25 | 48.0 | -0.355 | -0.346 | -0.415 | no | -0.48 | -0.24 |
| ob_lux+turtle_soup | 17 | 29.4 | -0.710 | -0.314 | -0.415 | no | -0.71 | -0.71 |
| bpr+ob_lux | 17 | 88.2 | +0.226 | -0.329 | -0.314 | **YES** | +0.76 | -0.25 |
| inducement+turtle_soup | 10 | 30.0 | -0.627 | -0.334 | -0.415 | no | -0.21 | -1.25 |

## Sequence chains (pooled, n>=10)

| pair (->) | n | hit% | net_t1 | solo A | solo B | beats both | H1 | H2 |
|---|---|---|---|---|---|---|---|---|
| compression_fade->ob_lux | 600 | 48.5 | -0.361 | -0.318 | -0.314 | no | -0.19 | -0.56 |
| mitigation->ob_lux | 463 | 44.9 | -0.397 | -0.346 | -0.314 | no | -0.25 | -0.54 |
| mitigation->compression_fade | 305 | 48.2 | -0.379 | -0.346 | -0.318 | no | -0.38 | -0.38 |
| ob_lux->compression_fade | 216 | 45.8 | -0.312 | -0.314 | -0.318 | **YES** | -0.17 | -0.47 |
| compression_fade->mitigation | 175 | 50.3 | -0.284 | -0.318 | -0.346 | **YES** | -0.18 | -0.38 |
| fvg_cb->compression_fade | 163 | 52.8 | -0.190 | -0.259 | -0.318 | **YES** | -0.31 | -0.09 |
| bpr->compression_fade | 89 | 52.8 | -0.218 | -0.329 | -0.318 | **YES** | -0.19 | -0.24 |
| compression_fade->inducement | 88 | 54.5 | -0.248 | -0.318 | -0.334 | **YES** | -0.34 | -0.17 |
| ob_lux->mitigation | 73 | 39.7 | -0.454 | -0.314 | -0.346 | no | -0.46 | -0.44 |
| inducement->compression_fade | 65 | 50.8 | -0.186 | -0.334 | -0.318 | **YES** | -0.20 | -0.17 |
| inducement->ob_lux | 57 | 36.8 | -0.617 | -0.334 | -0.314 | no | -0.72 | -0.43 |
| propulsion_block->ob_lux | 48 | 39.6 | -0.391 | -0.318 | -0.314 | no | -0.28 | -0.57 |
| compression_fade->fvg_cb | 47 | 48.9 | -0.089 | -0.318 | -0.259 | **YES** | -0.12 | -0.05 |
| propulsion_block->compression_fade | 39 | 35.9 | -0.381 | -0.318 | -0.318 | no | -0.39 | -0.38 |
| compression_fade->bpr | 37 | 54.1 | -0.276 | -0.318 | -0.329 | **YES** | -0.24 | -0.29 |
| fvg_cb->ob_lux | 36 | 61.1 | -0.342 | -0.259 | -0.314 | no | -0.95 | +0.27 |
| turtle_soup->compression_fade | 28 | 57.1 | -0.117 | -0.415 | -0.318 | **YES** | -0.59 | +0.29 |
| mitigation->fvg_cb | 26 | 53.8 | -0.248 | -0.346 | -0.259 | **YES** | -0.44 | -0.06 |
| bpr->mitigation | 24 | 41.7 | -0.280 | -0.329 | -0.346 | **YES** | -0.16 | -0.41 |
| mitigation->propulsion_block | 23 | 47.8 | -0.284 | -0.346 | -0.318 | **YES** | -0.41 | -0.20 |
| ob_lux->inducement | 21 | 28.6 | -0.561 | -0.314 | -0.334 | no | -0.74 | -0.36 |
| mitigation->inducement | 20 | 45.0 | -0.463 | -0.346 | -0.334 | no | -0.41 | -0.55 |
| fvg_cb->mitigation | 20 | 70.0 | -0.087 | -0.259 | -0.346 | **YES** | -0.26 | +0.17 |
| fvg_cb->bpr | 20 | 60.0 | -0.368 | -0.259 | -0.329 | no | -0.26 | -0.41 |
| compression_fade->propulsion_block | 19 | 52.6 | -0.566 | -0.318 | -0.318 | no | -0.81 | -0.39 |
| compression_fade->turtle_soup | 17 | 64.7 | -0.041 | -0.318 | -0.415 | **YES** | -0.11 | +0.03 |
| bpr->fvg_cb | 17 | 41.2 | -0.248 | -0.329 | -0.259 | **YES** | +0.18 | -0.48 |
| propulsion_block->mitigation | 16 | 50.0 | -0.440 | -0.318 | -0.346 | no | -0.14 | -0.74 |
| turtle_soup->ob_lux | 16 | 18.8 | -0.921 | -0.415 | -0.314 | no | -1.00 | -0.58 |
| mitigation->bpr | 15 | 73.3 | -0.014 | -0.346 | -0.329 | **YES** | -0.07 | +0.04 |
| fvg_cb->inducement | 14 | 28.6 | -0.461 | -0.259 | -0.334 | no | -0.77 | -0.29 |
| ob_lux->fvg_cb | 13 | 46.2 | +0.194 | -0.314 | -0.259 | **YES** | +0.13 | +0.21 |
| inducement->mitigation | 12 | 58.3 | -0.480 | -0.334 | -0.346 | no | -0.92 | -0.16 |
| bpr->ob_lux | 12 | 75.0 | -0.168 | -0.329 | -0.314 | **YES** | +0.18 | -0.65 |
| ob_lux->bpr | 10 | 90.0 | +0.246 | -0.314 | -0.329 | **YES** | +0.76 | -0.09 |

## Loss decomposition (pooled)

**POOLED** (n=11128 trades, k=1.5 fixed_t1). All figures R/trade; ledger sums exactly to observed net.

| item | R/trade | note |
|---|---|---|
| target hits (+1R x 47.3%) | +0.473 | favorable capture actually banked |
| stop-outs (-1R x 46.3%) | -0.463 | split below |
| &nbsp;&nbsp;... of which WRONG-direction stops | -0.165 | (a) direction wrongness |
| &nbsp;&nbsp;... of which SHAKEOUT stops | -0.041 | (b) stop tax: move was there, stop died first |
| &nbsp;&nbsp;... of which CHOP/WIN-class stops | -0.257 | noise stops |
| EOD flat exits (6.4% of trades) | +0.001 | neither side reached |
| = idealized pre-cost expectancy E0 | +0.012 | (d) the symmetric-payoff ceiling: mean MFE 2.92 ATR vs MAE 2.95 ATR (ratio 0.99); capture ceiling min(MFE,1R) = +0.800 R |
| + stop overshoot (gap-through fills) | -0.002 | (b) stop tax, part 2 |
| + costs & frictions (fees+STT+spread+slip+rounding+size-cap) | -0.327 | (c) |
| **= observed net** | **-0.317** | |


### Per-stock ledger summary

| stock | n | E0 | wrong-stops | shakeout-stops | overshoot | costs | net | MFE/MAE |
|---|---|---|---|---|---|---|---|---|
| RELIANCE | 2079 | +0.008 | -0.188 | -0.056 | -0.000 | -0.360 | **-0.353** | 1.01 |
| HDFCBANK | 2220 | -0.025 | -0.173 | -0.049 | -0.000 | -0.301 | **-0.326** | 0.94 |
| INFY | 2260 | +0.019 | -0.140 | -0.031 | -0.000 | -0.310 | **-0.291** | 0.97 |
| TATASTEEL | 2365 | +0.007 | -0.142 | -0.035 | -0.003 | -0.333 | **-0.329** | 1.00 |
| HINDUNILVR | 2204 | +0.053 | -0.184 | -0.035 | -0.006 | -0.334 | **-0.287** | 1.02 |


---

# FINAL VERDICT

### Cell scan (n>=100, ranked by worse half; top 20)

| cell | n | H1 net_t1 | H2 net_t1 | positive both halves? |
|---|---|---|---|---|
| fvg_cb @ HDFCBANK | 248 | -0.242 | -0.249 | no |
| pair compression_fade+fvg_cb @ POOLED | 233 | -0.259 | -0.144 | no |
| fvg_cb @ INFY | 248 | -0.265 | -0.067 | no |
| fvg_cb @ POOLED | 1243 | -0.240 | -0.276 | no |
| pair compression_fade+inducement @ POOLED | 133 | -0.285 | -0.021 | no |
| ob_lux @ HINDUNILVR | 576 | -0.169 | -0.286 | no |
| pair bpr+compression_fade @ POOLED | 155 | -0.029 | -0.292 | no |
| mitigation @ INFY | 318 | -0.180 | -0.312 | no |
| pair fvg_cb->compression_fade @ POOLED | 163 | -0.313 | -0.092 | no |
| compression_fade @ INFY | 907 | -0.227 | -0.315 | no |
| fvg_cb @ RELIANCE | 214 | -0.250 | -0.323 | no |
| ob_lux @ TATASTEEL | 603 | -0.249 | -0.324 | no |
| bpr @ INFY | 106 | -0.207 | -0.325 | no |
| propulsion_block @ POOLED | 200 | -0.339 | -0.298 | no |
| bpr @ POOLED | 365 | -0.309 | -0.342 | no |
| compression_fade @ POOLED | 4481 | -0.290 | -0.345 | no |
| compression_fade @ HINDUNILVR | 847 | -0.248 | -0.351 | no |
| compression_fade @ RELIANCE | 872 | -0.372 | -0.290 | no |
| mitigation @ POOLED | 1538 | -0.319 | -0.374 | no |
| mitigation @ TATASTEEL | 315 | -0.375 | -0.309 | no |


**Qualifying cells (n>=100, net_t1 > 0 in BOTH halves): 0** -- NONE.


### The one-page answer: where exactly does each rupee die?

Per trade, pooled, k=1.5 fixed_t1 (all figures R = Rs10,000):

1. **The move is real but symmetric.** Every tool beats its seeded same-bucket
   baseline on the hit metric (+3.6 to +14.8 pp, pooled +9.0 pp) -- the detectors DO
   mark spots where a >=1-ATR favorable excursion is likelier than random. But the
   full-path excursions are symmetric (mean MFE 2.92 ATR vs MAE
   2.95 ATR, ratio 0.99), so with a
   symmetric 1R/1R bracket the targets (47.3%) and stops
   (46.3%) nearly cancel: **idealized pre-cost expectancy E0 =
   +0.012 R/trade** -- statistically zero. This is the (d)
   symmetric-payoff ceiling: the hit-metric edge does not convert into asymmetric
   excursions, and no exit scheme can mine expectancy from a symmetric distribution.

2. **Direction wrongness (the WRONG class)** = 20.5% of all
   trades = 33.4% of stopped trades (the prior "44%-class" shrinks
   to ~33% at this scale). Its ledger mass is -0.165 R/trade -- but it is
   almost fully offset inside E0 by the target mass; it caps the ceiling rather than
   being the marginal rupee-killer.

3. **Stop tax**: shakeouts are only 4.8% of trades
   (-0.041 R/trade); the median shakeout needed a
   2.1-ATR stop
   (~1.4x the current 1.5 ATR) to survive -- widening stops buys little because the
   pool is tiny. Stop overshoot (gap-through) is negligible: -0.002
   R/trade.

4. **Costs are the actual killer: -0.327 R/trade** (measured
   net - frictionless; analytic reconstruction 0.32 R agrees). Anatomy: a 1.5x-5m-ATR
   stop is ~0.27% of price, so risking
   Rs10,000 forces a median notional of ~Rs36L
   (364x the risk); at ~9 bp round-trip (spread 4bp + STT
   2.5bp one leg + exch + slip + Rs40 flat) that is ~0.33 R **every trade**. Breakeven
   would need E0 >= 0.33 R, i.e. a 33-pp target-vs-stop gap -- vs the observed
   1 pp.

**Waterfall (sums exactly): +0.012 (E0) -0.002
(overshoot) -0.327 (costs) = -0.317 R/trade
observed.** Gross capture ceiling min(MFE,1R) = +0.800 R/trade; stops +
symmetry eat +0.788 of it before costs even start.

### Does any stock behave differently enough to matter?

No. Net spans -0.287 (HINDUNILVR) to -0.353 (RELIANCE); every stock's E0 sits in
[-0.03, +0.05] and every stock's cost drag in [-0.30, -0.36]. HINDUNILVR has the best
E0 (+0.05) and INFY the least direction-wrongness, but nothing flips sign, in either
temporal half, in any cell with n>=100. The five profiles (index heavyweight, bank,
IT, metal, FMCG) fail identically: same symmetric excursions, same cost anatomy.

### Pairing

Co-fire and sequence confluence consistently *improves* expectancy (e.g. pooled
compression_fade+inducement -0.144 vs solos ~-0.32/-0.33;
27 pair/chain cells beat both
solos) -- confluence is real signal -- but not one pooled pair with n>=100 is positive
in even ONE half. Small-n positives
(ob_lux->fvg_cb n=13 +0.194; ob_lux->bpr n=10 +0.246) are noise-sized.

### Caveats (honesty)

- Late-day (14:15+) WRONG rates of 1-8% are an EOD-truncation artifact (no room left
  for a 2R continuation to prove wrongness), not late-day skill.
- The at-day-extreme stratum is tiny for every tool (these are retrace-entry tools;
  they rarely fire within 0.25 ATR of the day extreme) -- descriptive only.
- breaker_msb does not exist on main; the existing `breaker` detector is a different
  (non-v2) tool and was excluded per scope.
- hit%/baseline use the identical scoring convention (undecided counts against both),
  so the +9 pp edge is not a metric artifact.

### VERDICT

**Still a failure, and now fully itemized: NO tool, stock, pair, or chain cell with
n>=100 is net-positive in both temporal halves (0 of 42 candidate cells >=100 n).
The detectors have genuine hit-metric edge (+9 pp over baseline) and confluence adds
more, but the underlying excursions are symmetric (MFE/MAE = 0.99),
so pre-cost expectancy is ~0.01 R; intraday 5m-ATR sizing then pays ~0.33 R/trade in
costs. The system loses ~0.32 R/trade almost entirely to friction, not to being
"wrong". Nothing in this 8-tool family, on any of 5 diverse stocks, at k=1.5 with t1
or t3 exits, survives realistic NSE costs at the 5m timeframe.**
