# H1GRID — combination × geometry sweep, H1 + 2H, 3 years (definitive)

Question: does ANY pure-SMC zone type × elimination-flag combination × stop/exit
geometry produce excess-over-drift at H1 or 2H? 192 cells, dual nulls, full
holdout gauntlet. Anchor: LADDER.md found excess≈0 at every TF.

## Data & method

- `runs/artifacts-data/l4_h1.parquet`: 138 NSE stocks × H1, 2023-08-04 →
  2026-07-17 (2.94y, 725 sessions, ~5052 bars/sym). 2H = session-aware pairing
  of H1 bars (4 buckets/day); D1 = daily resample of the same data.
- Splice guard: 6 symbols carry one unadjusted split/demerger jump (>20%
  close→open: ABFRL, BAJFINANCE, HAL, SIEMENS, TRENT, VEDL). No entry on a
  splice bar, no zone spanning one, any open position force-exits at the last
  pre-splice close — applied identically to real trades and nulls.
- Zones (verified ports from `dev/research/hulinv_run.py` / `chartpar_run.py`),
  constructed on native TF bars: **FVG** (fvg_cb 3-candle gap, displacement
  close, adaptive range threshold; wick-valid retest), **OB** (ob_lux: 5-bar
  pivot, close-cross structure break, hv-bar swap, anchor candle), **BREAKER**
  (EmreKb zz=9 MSB, fib 0.33, swept-swing origin box; retest = close back
  inside), **iFVG** (FVG close-invalidated through far edge, then wick-retested
  from the other side; direction flips).
- Trade: first retest (wick touch) → entry next-bar open, fade direction.
  Zone counts (zones with a retest): H1 104,189 (OB 52.8k, FVG 26.7k, iFVG
  22.9k, BRK 1.8k); 2H 66,220.
- Elimination flags: **F1** born ≥1 session before retest (H1 70%, 2H 76%);
  **F2** zone nested inside a live same-direction D1 OB/FVG at retest, D1 built
  causally from completed dailies (21%); **F3** zone event ≤3 bars after a
  direction-aligned EQ-pool sweep (pools = ≥2 same-side 5/5-fractal swings
  within 0.25×ATR14; sweep = wick through, close back) (6-7%); **F4** zone born
  on the session-open bar (41% / 60%).
- Grid per TF: 4 zone types × subsets {none, F1, F1+F2, F1+F3, F1+F2+F3, F4} ×
  stop k∈{1.5, 2.5}×ATR(14,TF) × exit {2R tgt + 10-sess time-stop, 1.5R +
  5-sess} = 96 cells/TF ⇒ **192 cells examined** (180 evaluable at n≥30). At
  p05, ~9-10 false positives are expected by chance — the gauntlet is mandatory.
- Sim: conservative intrabar order (time-stop at open → gap-through fill at
  open, mandatory → stop before target). Costs = delivery at ₹1L / 0.5% risk
  (₹500) sizing: STT 0.1% both legs, exch 0.004%, DP ₹15/sell, slip 2bp/leg;
  qty floored, notional ≤ ₹1L. Cost drag alone ≈ 0.10-0.19R/trade at this size.

## The nulls — and the trap this run stepped into

**Null A (mandated, month-matched):** per real trade, 5 random entry bars from
the same symbol × calendar month, same direction, geometry, costs.

**Null B (time-local):** per real trade, 5 random entry bars from the trade's
own forward window (entry+1 → entry+10 sessions), same everything.

Null A produced **61/180 "ALIVE" cells** (pooled excess>0, all 3 temporal
thirds, both crc32-symbol halves) with mean excess +0.07R. The signature gave
it away: virtually every "alive" cell has **negative net_R** — the excess comes
from the null being awful (−0.3..−0.45R), not from the trades being good, and
pooled per TF net_R ≈ null_A exactly (−0.194 vs −0.195 H1). That is a
within-month path-selection artifact: a bull zone is only retested in months
where price *fell into it*, so month-uniform null longs sit through the very
decline that created the trade, while the real entry starts after it. Under a
pure martingale this manufactures positive "excess" with zero timing skill.
Null B removes the artifact; against it the board collapses:

| pooled | net_R | null_A | null_B | excess_A | excess_B |
|---|---|---|---|---|---|
| H1 | −0.194 | −0.195 | −0.186 | −0.001 | **−0.008** |
| 2H | −0.155 | −0.148 | −0.138 | −0.007 | **−0.017** |

Cell-level excess_B: mean −0.005, median −0.008; 77/180 cells >0 (coin flip).

## Top-10 cells by excess (null A), with full gauntlet

geom = stop×ATR / target / time-stop. ex_y1-y3 = temporal thirds, ex_h0/h1 =
symbol halves (all vs null A). alive = A-gauntlet, aliveB = B-gauntlet.

| tf | ztype | subset | geom | n | net_R | null_A | excess_A | null_B | excess_B | ex_y1 | ex_y2 | ex_y3 | ex_h0 | ex_h1 | tr/qtr | alive | aliveB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| h1 | BREAKER | F1+F3 | k2.5/2R/10s | 42 | −0.013 | −0.455 | +0.441 | −0.354 | +0.340 | — | +0.83 | +0.33 | +0.50 | +0.34 | 3.6 | no (n) | no |
| h2 | IFVG | F1+F2+F3 | k1.5/2R/10s | 161 | +0.041 | −0.325 | +0.367 | −0.105 | +0.146 | +0.64 | +0.09 | +0.45 | +0.23 | +0.55 | 13.7 | YES | no |
| h1 | FVG | F1+F2+F3 | k2.5/2R/10s | 285 | +0.024 | −0.324 | +0.348 | −0.050 | +0.075 | +0.49 | +0.06 | +0.49 | +0.41 | +0.30 | 24.2 | YES | no |
| h2 | IFVG | F1+F2+F3 | k2.5/2R/10s | 159 | +0.035 | −0.294 | +0.329 | −0.097 | +0.132 | +0.39 | +0.50 | +0.20 | +0.24 | +0.44 | 13.5 | YES | no |
| h2 | IFVG | F1+F2+F3 | k1.5/1.5R/5s | 161 | −0.030 | −0.355 | +0.325 | −0.220 | +0.191 | +0.06 | +0.14 | +0.54 | +0.28 | +0.38 | 13.7 | YES | no |
| h1 | FVG | F1+F2+F3 | k1.5/2R/10s | 287 | −0.043 | −0.333 | +0.291 | −0.225 | +0.182 | +0.27 | +0.02 | +0.48 | +0.43 | +0.17 | 24.4 | YES | no |
| h1 | FVG | F1+F2+F3 | k2.5/1.5R/5s | 285 | −0.010 | −0.293 | +0.283 | −0.134 | +0.123 | +0.48 | +0.10 | +0.34 | +0.36 | +0.21 | 24.2 | YES | no |
| h1 | BREAKER | F1+F3 | k2.5/1.5R/5s | 42 | +0.030 | −0.249 | +0.279 | −0.104 | +0.134 | — | +0.63 | +0.24 | +0.45 | −0.01 | 3.6 | no (n) | no |
| h2 | IFVG | F1+F2+F3 | k2.5/1.5R/5s | 159 | +0.042 | −0.231 | +0.273 | −0.131 | +0.173 | +0.43 | +0.17 | +0.28 | +0.26 | +0.29 | 13.5 | YES | **YES** |
| h1 | BREAKER | F1+F3 | k1.5/1.5R/5s | 43 | −0.052 | −0.316 | +0.264 | −0.135 | +0.083 | — | +0.22 | +0.19 | +0.32 | +0.17 | 3.7 | no (n) | no |

## Survivors of BOTH gauntlets (6 of 192) — with paired t-stats

| tf | ztype | subset | geom | n | excess_A (t) | excess_B (t) | net_R (t) | tr/qtr |
|---|---|---|---|---|---|---|---|---|
| h1 | FVG | F1+F2+F3 | k1.5/1.5R/5s | 288 | +0.214 (2.7) | +0.129 (1.6) | −0.069 (−0.9) | 24.5 |
| h1 | FVG | F1+F2 | k2.5/1.5R/5s | 2218 | +0.126 (4.8) | +0.039 (1.4) | −0.075 (−3.0) | 188.6 |
| h1 | FVG | F1+F3 | k2.5/1.5R/5s | 1137 | +0.075 (2.1) | +0.025 (0.7) | −0.137 (−3.9) | 96.7 |
| h2 | FVG | F1+F2 | k2.5/2R/10s | 1745 | +0.158 (5.0) | +0.037 (1.2) | −0.034 (−1.1) | 148.4 |
| h2 | FVG | F1+F2 | k2.5/1.5R/5s | 1745 | +0.140 (5.3) | +0.060 (2.2) | −0.041 (−1.6) | 148.4 |
| h2 | IFVG | F1+F2+F3 | k2.5/1.5R/5s | 159 | +0.273 (3.1) | +0.173 (2.1) | +0.042 (0.5) | 13.5 |

Read the columns left to right and the story is uniform: the big excess_A
t-stats are the artifact; excess_B t-stats are 0.7-2.2 — none survives even a
mild multiple-testing correction over 180 cells (Bonferroni p05 needs t≈3.6;
~10 cells were expected to reach naive p05 by chance and 6 heavily-overlapping
ones did). Five of six lose money outright. The single net-positive cell
(2H iFVG F1+F2+F3, +0.042R) is n=159 over three years — 13.5 trades/quarter
pooled across all 138 symbols (one trade per symbol per ~2.6 years) — with
net_R t=+0.50: statistically indistinguishable from zero and selected as the
best of 192.

## Anchor comparison to LADDER.md

LADDER (different setups, MFE/MAE vs unconditional random-entry null) found
excess-over-null flat at ≈0 across 5m→H4 and zero of 24+64 cells econ-stable.
This sweep — different zone constructors (pure ported SMC), an elimination-flag
grid, explicit geometry, and a per-trade matched null — lands in exactly the
same place once the null is honest: **pooled excess −0.005R, median cell
−0.008R, no cell that is jointly net-positive, robust, and non-trivial.** The
run's one new lesson is methodological: a symbol/month/direction-"matched" null
is not conservative for retest strategies — it inherits the selection path and
manufactures false survivors (61 of them here). The time-local null killed all
of it, which is a *confirmation* of the program's core lesson, not a failure.

## VERDICT

**Dead.** Across 192 combination×geometry cells at H1 and 2H on three years ×
138 symbols: (1) zone-retest entries carry no timing edge over random entries
in their own forward window (pooled excess_B ≈ −0.01R, cells split 77/103 on
sign); (2) after delivery costs every zone type at every flag depth is
net-negative except three tiny n≤161 iFVG/FVG cells whose best t-stat is +0.5
against 192 draws; (3) the elimination flags (F1 maturity, F2 D1-nesting, F3
sweep-alignment, F4 gap-origin) monotonically shrink n without ever producing
a robust net-positive cell. There is no surviving cell to promote. The
month-matched-null artifact is documented above so it is not rediscovered as
"edge" later. Pure-SMC zone fading at intraday-to-2H scale on NSE cash equity
is falsified at every combination this program can construct; anything further
here is curve-fitting the noise floor.

---
Artifacts (scratchpad, `h1grid_` prefix): `h1grid_lib.py` (ported
constructors), `h1grid_build.py` (zones+flags+retests), `h1grid_sim.py` (real +
null A), `h1grid_sim2.py` (null B), `h1grid_agg.py` (cells+gauntlet),
`h1grid_cells.csv` (all 192 cells, both nulls, full holdout columns),
`h1grid_trades_{h1,h2}.parquet`, `h1grid_res_{h1,h2}.parquet`,
`h1grid_nullb_{h1,h2}.parquet`, logs `h1grid_*.log`.
