# 40-STOCK REGIME LABELS — 2026 window (study40_2026)

Coarse RANGE / UPTREND / DOWNTREND label per symbol, from **D1 bars resampled from 1m** (`data/wide/<SYM>.csv`), for the 40 symbols in the distinct `symbol` column of `runs/validate/study40_2026/evidence.parquet`.

## CAVEAT — thin tape (READ FIRST)
`data/wide` is a **single 17-day tape**: **35 symbols have 16 D1 bars (2026-06-25..07-17)**, 5 have 19 bars (from 2026-06-19). With only ~16 daily bars, **D1 drift / close-position / ADX are STATISTICALLY THIN** and these labels are **COARSE — one regime snapshot, not a validated trend classification**. In particular **ADX(14) cannot seat** on 16 bars (needs ~2x14=28 for the double Wilder smoothing), so the `adx` column is a **coarse fallback = mean of the available DX values** (thin proxy, not a true 14-period ADX). Treat every label as provisional.

## Thresholds used
- **UPTREND**: `drift% > +3` AND `close_pos > 65`
- **DOWNTREND**: `drift% < -3` AND `close_pos < 35`
- **RANGE**: everything else
- **Intraday tie-break** (robustness): a *D1 tie* = drift meets its trend bar but close_pos is ambiguous (up-tie: drift>+3 & close_pos in [50,65]; down-tie: drift<-3 & close_pos in (35,50]). Break it toward the drift-direction trend **iff** intraday confirms: `samedir >= 0.70` AND `itrend >= 0.45`; else keep RANGE. Thresholds tuned to yield a non-degenerate 3-way split.

## Column definitions
- **drift%** = (last D1 close - first D1 close) / first close x 100
- **close_pos** = (last close - min low) / (max high - min low) x 100  (stochastic-style position of the final close in the window range)
- **adx** = coarse ADX(14) proxy (mean available DX; see caveat — thin)
- **inband%** = fraction of D1 closes sitting inside the 20-80 band of the window range (range-boundedness; high => coils in the middle)
- **intraday_trend** = `itrend` (mean over sessions of |close-open|/(high-low); high => trending days)  **/ sd** = fraction of sessions whose direction matches net drift (persistence; used for tie-break)

## Table
| SYM | drift% | close_pos | adx~ | inband% | intraday_trend | REGIME |
|---|---|---|---|---|---|---|
| BAJFINANCE | +7.52 | 84.5 | 53.2 | 73.7 | 0.46 / sd 0.68 | **UPTREND** |
| DLF | +7.36 | 70.9 | 10.5 | 62.5 | 0.52 / sd 0.50 | **UPTREND** |
| ABB | +7.35 | 65.3 | 46.7 | 50.0 | 0.51 / sd 0.44 | **UPTREND** |
| AARTIIND | +5.95 | 70.0 | 39.2 | 75.0 | 0.41 / sd 0.69 | **UPTREND** |
| BAJAJ-AUTO | +5.73 | 86.4 | 43.8 | 75.0 | 0.49 / sd 0.50 | **UPTREND** |
| BIOCON | +5.24 | 82.3 | 34.5 | 68.8 | 0.44 / sd 0.38 | **UPTREND** |
| TITAN | +4.87 | 88.1 | 42.6 | 68.4 | 0.41 / sd 0.53 | **UPTREND** |
| APOLLOHOSP | +3.63 | 78.3 | 45.5 | 87.5 | 0.36 / sd 0.56 | **UPTREND** |
| COLPAL | +2.76 | 63.3 | 4.1 | 75.0 | 0.52 / sd 0.38 | **RANGE** |
| ADANIENT | +2.72 | 67.7 | 14.8 | 75.0 | 0.53 / sd 0.56 | **RANGE** |
| VOLTAS | +2.66 | 59.5 | 29.7 | 68.8 | 0.49 / sd 0.44 | **RANGE** |
| BAJAJFINSV | +2.56 | 49.2 | 21.4 | 50.0 | 0.52 / sd 0.62 | **RANGE** |
| ALKEM | +2.54 | 49.0 | 21.8 | 75.0 | 0.37 / sd 0.44 | **RANGE** |
| BHARATFORG | +2.12 | 74.7 | 13.0 | 100.0 | 0.45 / sd 0.50 | **RANGE** |
| COFORGE | +1.03 | 70.7 | 16.1 | 68.8 | 0.49 / sd 0.50 | **RANGE** |
| ADANIPORTS | +0.92 | 46.6 | 19.8 | 75.0 | 0.43 / sd 0.50 | **RANGE** |
| DABUR | +0.81 | 15.7 | 6.7 | 68.8 | 0.44 / sd 0.38 | **RANGE** |
| BHARTIARTL | +0.78 | 67.0 | 20.3 | 84.2 | 0.46 / sd 0.53 | **RANGE** |
| BOSCHLTD | +0.78 | 44.9 | 17.5 | 75.0 | 0.42 / sd 0.44 | **RANGE** |
| HAVELLS | +0.62 | 50.1 | 6.7 | 81.2 | 0.51 / sd 0.31 | **RANGE** |
| BRITANNIA | +0.57 | 55.0 | 4.2 | 75.0 | 0.44 / sd 0.50 | **RANGE** |
| CHOLAFIN | +0.27 | 46.7 | 8.1 | 81.2 | 0.44 / sd 0.56 | **RANGE** |
| BEL | +0.04 | 18.7 | 10.1 | 62.5 | 0.46 / sd 0.44 | **RANGE** |
| APOLLOTYRE | +0.03 | 26.6 | 10.6 | 62.5 | 0.47 / sd 0.50 | **RANGE** |
| CIPLA | -0.55 | 14.1 | 18.7 | 81.2 | 0.45 / sd 0.62 | **RANGE** |
| AUBANK | -0.65 | 22.0 | 3.3 | 93.8 | 0.35 / sd 0.56 | **RANGE** |
| BPCL | -0.87 | 61.9 | 15.5 | 81.2 | 0.53 / sd 0.38 | **RANGE** |
| AUROPHARMA | -1.23 | 12.0 | 25.8 | 87.5 | 0.40 / sd 0.62 | **RANGE** |
| ASIANPAINT | -2.65 | 43.4 | 31.5 | 73.7 | 0.44 / sd 0.53 | **RANGE** |
| COALINDIA | -3.15 | 12.7 | 24.2 | 81.2 | 0.43 / sd 0.69 | **DOWNTREND** |
| CANBK | -3.17 | 42.5 | 20.4 | 93.8 | 0.49 / sd 0.75 | **DOWNTREND**  <!--tie->DOWN (samedir/itrend confirm)--> |
| ABFRL | -3.50 | 2.4 | 4.8 | 56.2 | 0.49 / sd 0.56 | **DOWNTREND** |
| ASHOKLEY | -3.63 | 13.1 | 0.6 | 68.8 | 0.46 / sd 0.56 | **DOWNTREND** |
| AXISBANK | -3.86 | 14.3 | 29.2 | 73.7 | 0.44 / sd 0.58 | **DOWNTREND** |
| CGPOWER | -3.92 | 19.2 | 8.1 | 75.0 | 0.44 / sd 0.56 | **DOWNTREND** |
| ADANIPOWER | -6.35 | 6.0 | 17.9 | 68.8 | 0.50 / sd 0.81 | **DOWNTREND** |
| CROMPTON | -6.61 | 2.5 | 50.9 | 68.8 | 0.47 / sd 0.75 | **DOWNTREND** |
| BALKRISIND | -7.43 | 5.1 | 25.4 | 81.2 | 0.42 / sd 0.56 | **DOWNTREND** |
| BERGEPAINT | -8.29 | 11.5 | 39.4 | 62.5 | 0.47 / sd 0.50 | **DOWNTREND** |
| BANKBARODA | -11.78 | 18.0 | 65.9 | 68.8 | 0.56 / sd 0.75 | **DOWNTREND** |

## Counts
- **RANGE: 21**
- **UPTREND: 8**
- **DOWNTREND: 11**
- Total: 40

## Per-bucket symbol lists
- **UPTREND (8)**: AARTIIND, ABB, APOLLOHOSP, BAJAJ-AUTO, BAJFINANCE, BIOCON, DLF, TITAN
- **RANGE (21)**: ADANIENT, ADANIPORTS, ALKEM, APOLLOTYRE, ASIANPAINT, AUBANK, AUROPHARMA, BAJAJFINSV, BEL, BHARATFORG, BHARTIARTL, BOSCHLTD, BPCL, BRITANNIA, CHOLAFIN, CIPLA, COFORGE, COLPAL, DABUR, HAVELLS, VOLTAS
- **DOWNTREND (11)**: ABFRL, ADANIPOWER, ASHOKLEY, AXISBANK, BALKRISIND, BANKBARODA, BERGEPAINT, CANBK, CGPOWER, COALINDIA, CROMPTON

## Tie-break audit
Exactly **1** symbol was a genuine trend-qualifying D1 tie: **CANBK** (drift -3.17% clears the -3 bar, but close_pos 42.5 is mid-range). Intraday confirmed weakness (samedir 0.75, itrend 0.49) -> flipped **RANGE -> DOWNTREND**. No up-side ties arose (every drift>+3 name also had close_pos>65). All other RANGE names have flat drift (|drift| within the +/-3 band) regardless of close_pos, so they are not trend-qualified.
