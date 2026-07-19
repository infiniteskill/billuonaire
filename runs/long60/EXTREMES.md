# EXTREMES — ATR-zigzag extreme-swing detector vs hand-circled swings

Prototype: `scratchpad/ext_zigzag.py` + `ext_run.py` (session scratchpad). HEROMOTOCO, continuous tape, no session logic.

## Algorithm (as taught)

- ATR(14, TF), Wilder smoothing (warm-up backfilled over first 14 bars).
- Causal state machine. After a confirmed pivot, track the running opposite extreme (pending pivot).
- **Confirm**: pending pivot becomes a valid pivot once the reversal leg from its extreme reaches `K x ATR(confirm bar)`. `leg_in >= K x ATR` holds by construction (previous pivot needed the same reversal).
- **Alternation**: while seeking a low, a bar exceeding the last confirmed high *replaces* it (pivot moves to the new extreme, re-confirms on the next K x ATR drop); mirror for lows. Never two same-side pivots in a row.
- **Cluster band**: contiguous bars around the pivot whose relevant extreme is within `0.5 x ATR(pivot bar)` of the pivot price -> zone `[band_lo, band_hi]` + a time span. (Reported band uses the full window; causally the band right edge grows as retests print.)
- **Rank**: `min(leg_in, leg_out) / ATR(pivot bar)`. Master = window max-high / min-low pivot. `leg_out` of the final confirmed pivot measured to the running extreme at window end.
- Flags: `b` = boundary (leg_in truncated by window start), `?` = pending (leg_out not yet K x ATR at window end).

Matching vs circles: price = distance from circled price to pivot band <= 1.2%; date = cluster span padded +-3 days overlaps circled range. Greedy, same side only, one pivot per circle.

## Data

- **Chart A**: `data/long5m/HEROMOTOCO.csv` resampled 5m -> 30m (offset 15min => Zerodha-aligned 09:15 bars). 741 bars, 2026-04-27..2026-07-17. Median ATR 28.7 (~0.58% of price). ATR warm-up eats the window start (no lead-in data exists) — first pivot flagged `b`.
- **Chart B**: `runs/artifacts-data/l4_h1.parquet`, HEROMOTOCO H1, window 2025-11-04..2026-03-16 (623 bars, 89 days), ATR lead-in from 2025-10-01. Median ATR 44.4 (~0.79%).

## K sweep (strict tolerances)

| K | A pivots | A match/8 | A extras | A F1 | B pivots | B match/8 | B extras | B F1 | combined F1 |
|---|---|---|---|---|---|---|---|---|---|
| 4 | 27 | **8** | 19 | .457 | 20 | 6 | 14 | .429 | .444 |
| 5* | 22 | 6 | 16 | .400 | 12 | 5 | 7 | .500 | .440 |
| 6 | 17 | 6 | 11 | .480 | 11 | 5 | 6 | .526 | .500 |
| 8 | 8 | 6 | 2 | **.750** | 9 | 4 | 5 | .471 | **.606** |
| 10 | 6 | 5 | 1 | .714 | 7 | 2 | 5 | .267 | .483 |

*K=5 added as a bonus point (not in the brief's sweep).

**K\* = 8** by combined F1 (also wins after crediting the structural matches below: .788 vs .636 for K=6). Per-chart optimum differs: **A -> K=8, B -> K=6**. Not noise — in percent terms both equal the same threshold: `8 x ATR30m = 4.64%` of price, `6 x ATR_H1 = 4.72%`. The eye's cutoff is **a ~4.7% minimum leg**, TF-invariant; K must be recalibrated per TF (or the detector should use a percent-of-price leg floor directly).

## Chart A parity @ K=8 (30m) — 8 pivots vs 8 circles: 6 strict match, 2 extras, 2 missed

| # | date | H/L | price | band | rank(xATR) | lag(bars) | flag | circle |
|---|---|---|---|---|---|---|---|---|
| 1 | 06 May 10:45 | L | 4953.0 | 4953–4965 | 8.1 | 29 | b | **A1** (0.7%) |
| 2 | 07 May 12:45 | H | 5458.0 | 5442–5458 | 7.7 | 38 | **MASTER** | **A2** (0.4%) |
| 3 | 14 May 11:15 | L | 4880.5 | 4880–4896 | 6.8 | 125 | | **A3** (0.1%) |
| 4 | 15 May 09:15 | H | 5138.5 | 5122–5138 | 7.1 | 128 | | extra |
| 5 | 02 Jun 09:15 | L | 4747.1 | 4747–4765 | 9.0 | 79 | | **A5** (0.3%) |
| 6 | 15 Jun 09:45 | H | 5073.0 | 5073 | 10.8 | 97 | | extra |
| 7 | 30 Jun 09:15 | L | 4672.5 | 4672 | 8.8 | 38 | **MASTER low** | **A7** (0.6%) |
| 8 | 07 Jul 14:15 | H | 5022.4 | 5015–5022 | 14.7 | ? | pending | **A8** (0.5%) |

- **A4 missed** (H ~5060, 26–27 May): real bar = 25 May H 5062 (price exact), but its down-leg is only ~113 pts ≈ **4.9 x ATR** -> absorbed for K>=5; caught at K=4. The phase's true extreme is 29 May 5134.5 (algo keeps that at K=6).
- **A6 missed** (H ~5010, 26–27 Jun): 25 Jun H 5043.9, leg_in ~159 pts ≈ **5.0 x ATR** -> caught only at K=4.
- Both misses are genuine ~5x swings, consistent with the ~4.7% eye threshold sitting right at their size.
- Extras #4/#6 are real uncircled lower-highs (rank 7–11x) — structure, not noise.

## Chart B parity @ K=6 (H1, per-chart best) — 11 pivots: 5 strict + 3 structural, 1 honest insert

| # | date | H/L | price | band | rank(xATR) | lag(bars) | flag | circle |
|---|---|---|---|---|---|---|---|---|
| 1 | 07 Nov 10:15 | L | 5258.0 | 5258–5276 | 28.0 | 20 | b | extra (window edge) |
| 2 | 05 Dec 10:15 | H | 6388.0 | 6378–6388 | 22.6 | 11 | **MASTER** | **B1**† |
| 3 | 29 Dec 13:15 | L | 5551.0 | 5551–5559 | 17.5 | 13 | | **B2** (0.9%) |
| 4 | 07 Jan 12:15 | H | 6049.0 | 6049 | 13.4 | 12 | | **B3** (0.5%) |
| 5 | 27 Jan 12:15 | L | 5298.5 | 5298–5323 | 11.6 | 25 | | **B4**† |
| 6 | 05 Feb 09:15 | H | 5888.0 | 5860–5888 | 9.0 | 47 | | **B5**† |
| 7 | 20 Feb 10:15 | L | 5375.0 | 5375–5389 | 11.2 | 20 | | **B6** (0.8%) |
| 8 | 25 Feb 11:15 | H | 5840.0 | 5815–5840 | 8.8 | 23 | | **B7** (0.3%) |
| 9 | 09 Mar 09:15 | L | 5340.0 | 5340–5355 | 7.3 | 12 | | insert between B7/B8 |
| 10 | 11 Mar 09:15 | H | 5763.5 | 5763 | 6.7 | 12 | | **B8** (0.2%) |
| 11 | 16 Mar 10:15 | L | 5125.0 | 5125 | 9.7 | ? | MASTER low, pending | extra (crash into window end) |

†Structural matches, outside strict tolerance for data-vs-eyeball reasons:
- **B1** (~6300, 5–8 Dec): master top found at the **exact date**; actual data high is **6388** (circled ~6300 => 1.4% > 1.2%). Chart-scale eyeball, not a detector miss.
- **B4** (~5370, 19–20 Jan): the circled price is the **23 Jan first-touch low 5369 (0.02% off)**; the alternation-replace correctly kept the deeper final extreme 5298.5 on 27 Jan. Same low complex.
- **B5** (~5930, 9–10 Feb): no 5930 print exists; the rounded top 04–10 Feb peaks at **5888 on 05 Feb** (price within 0.7%). The 10 Feb retest (5845) sits 0.7 x ATR below the peak, so the 0.5 x ATR cluster ends 05 Feb and the date misses the +-3d window by 1 day.
- The **9 Mar low insert** between B7 and B8 is the predicted honest structural insert (alternation demands it).
- At combined **K\*=8**, B drops B8 (leg_in 6.7x < 8) and keeps 9 pivots, 4 strict + 3 structural.

## Confirmation lag (causality cost — honest numbers)

Pivot known only after the full K x ATR reversal prints:

| chart | K | lag median | lag max |
|---|---|---|---|
| A 30m | 6 | 18 bars (~1.4 d) | 69 bars (~5.3 d) |
| A 30m | **8** | **79 bars (~6.1 d)** | 128 bars (~9.8 d) |
| B H1 | **6** | **16 bars (~2.3 d)** | 47 bars (~6.7 d) |
| B H1 | 8 | 22 bars (~3.1 d) | 51 bars (~7.3 d) |

Median lag at A/K=8 is ~6 trading days — the pivot label is far too late to *enter* on; it is a regime/structure label. Trading use needs the anticipatory form (pending extreme + partial reversal), not the confirmed pivot.

## Before/after noise

Current `swings.py` fractal 3/3 rule on the same Chart A window: **135 swings** (67 H + 68 L). ATR-zigzag @ K=8: **8**. ~17x reduction; every survivor is a hand-circle-grade extreme.

## Verdict

The user's 16 circles are reproducible as ATR-zigzag majors: **A 8/8 @ K=4, 6/8 @ K\*=8** (misses are ~5x swings, price-exact bars exist), **B 8/8 structural @ K=6** (5 strict; 3 misses are data-vs-eyeball artifacts, each within 0.7–1.4% or 1 day). K\*=8 by F1, but the real invariant is a **~4.7% minimum leg**; calibrate K per TF from median ATR%.
