# INTERMEDIATE-TIMEFRAME LADDER — M15 / H1 / H4 (NSE zone-trading)

Concurrent sibling of the daily-native test. Question per TF: does zone-to-zone
travel become capturable (asymmetry beyond the random-entry null + net-positive
after costs) anywhere between the falsified 5m regime and daily?

## Data & method (documented choices)

| TF | Source | Span | Bars |
|---|---|---|---|
| M15 | 3x5m aggregated from `data/long5m/*.csv` (LTIM/TATAMOTORS skipped, NIFTY excluded from detection) | 2026-04-27 → 2026-07-17 (60d) | 196k, 25/day |
| H1 | fresh yfinance `60m` fetch, 138 syms (`l4_h1.parquet`; Yahoo returned ~3y, not 2) | 2023-08-04 → 2026-07-17 | 690k, 7/day |
| H4 | H1 aggregated session-aware, **2 buckets/day**: 09:15–12:15 (3h) + 12:15–15:30 (3.25h) | same | 199k, 2/day |

- Setups (validated daily-native rules, TF-scaled ATR14 Wilder): **ob_retest**
  (opp-candle zone before ≥1.5×ATR displacement, live till close beyond far
  edge, NO age limit), **fvg_retest** (3-bar gap ≥0.3×ATR, till filled),
  **sweep_reclaim** (20-bar extreme sweep, close back inside), **bos_retest**
  (2-2 fractal break, retest, 20-bar TTL). Signal on closed bar, entry
  next-bar open ±2bp. Dedup 5 bars per (setup,dir).
- Splice guard: segments cut at >25% close→open jumps (`trader.tools.doctor.splices`,
  read-only); nothing spans a splice. ATR-eligibility floor sqrt-scaled from
  daily 0.2%: M15 0.04%, H1 0.075%, H4 0.14% of close.
- MFE/MAE in ATR(TF) units at N∈{5,10,20,40} bars vs the **random-entry null**
  (every eligible bar, long side; short = mirror). Headline N=20.
- Economics: SL = structural zone edge floored at 1.5×ATR(TF); configs
  tgt{2,3,5}R + 20-bar-extreme trail; time-stop 40 bars; risk ₹10k/trade.
  **M15 = intraday**: forced flat at session close; ₹20×2 brokerage + 0.025%
  sell STT + 2bp half-spread/side; MIS cap 5×₹10L. **H1/H4 = delivery**
  (trades span days): 0.1% STT both sides + 0.004% txn + ₹15 DP + 2bp
  half-spread/side; no leverage (notional ≤ ₹10L); overnight gap-through-stop
  fills at session open beyond the stop. Shorts on H1/H4 are **futures-only**
  (cash shorts can't hold overnight); costed with the same delivery model
  (overstates futures costs slightly — doesn't change any sign below).
- Holdouts: temporal halves (data midpoint) × crc32(symbol)%2; half-year eras
  for H1/H4 (~3y ⇒ 7 eras). `econ_hold` = best-cfg net_R>0 in all 4 splits;
  `asym_hold` = MFE/MAE ratio > null ratio in all 4 splits.

## Random-entry null (the drift baseline)

| TF | N=5 L/S | N=10 L/S | N=20 L/S | N=40 L/S |
|---|---|---|---|---|
| M15 | 1.016 / 0.984 | 1.027 / 0.973 | 1.036 / 0.965 | 1.037 / 0.964 |
| H1 | 1.044 / 0.957 | 1.056 / 0.947 | 1.072 / 0.933 | 1.101 / 0.908 |
| H4 | 1.029 / 0.972 | 1.065 / 0.939 | 1.118 / 0.895 | 1.196 / 0.836 |

The null itself grows with TF — that is the 2023-26 upward drift, and it is the
yardstick every setup must beat.

## TF ladder (N=20; net_R = best config, delivery/intraday costs)

| TF | setup | dir | n | MFE/MAE | null | excess | best cfg | net_R | econ_hold | asym_hold |
|---|---|---|---|---|---|---|---|---|---|---|
| m15 | bos_retest | S | 3202 | 0.980 | 0.965 | +0.015 | tgt5 | -0.032 | no | no |
| m15 | bos_retest | L | 2842 | 1.082 | 1.036 | +0.046 | tgt5 | -0.157 | no | no |
| m15 | fvg_retest | S | 7712 | 0.956 | 0.965 | -0.009 | tgt3 | -0.021 | no | no |
| m15 | fvg_retest | L | 8096 | 1.008 | 1.036 | -0.028 | tgt5 | -0.138 | no | no |
| m15 | ob_retest | S | 2062 | 0.977 | 0.965 | +0.012 | tgt5 | +0.032 | no | no |
| m15 | ob_retest | L | 2199 | 0.961 | 1.036 | -0.075 | trail | -0.140 | no | no |
| m15 | sweep_reclaim | S | 5686 | 0.861 | 0.965 | -0.104 | tgt5 | -0.027 | no | no |
| m15 | sweep_reclaim | L | 6322 | 0.944 | 1.036 | -0.093 | trail | -0.154 | no | no |
| h1 | bos_retest | S | 11686 | 0.904 | 0.933 | -0.029 | tgt2 | -0.233 | no | no |
| h1 | bos_retest | L | 10884 | 1.054 | 1.072 | -0.018 | trail | -0.112 | no | no |
| h1 | fvg_retest | S | 32085 | 0.912 | 0.933 | -0.021 | tgt2 | -0.222 | no | no |
| h1 | fvg_retest | L | 35588 | 1.074 | 1.072 | +0.003 | trail | -0.065 | no | no |
| h1 | ob_retest | S | 8551 | 0.880 | 0.933 | -0.052 | tgt5 | -0.230 | no | no |
| h1 | ob_retest | L | 8214 | 1.035 | 1.072 | -0.037 | trail | -0.099 | no | no |
| h1 | sweep_reclaim | S | 24472 | 0.882 | 0.933 | -0.051 | trail | -0.216 | no | no |
| h1 | sweep_reclaim | L | 22946 | 1.000 | 1.072 | -0.072 | trail | -0.124 | no | no |
| h4 | bos_retest | S | 3422 | 0.832 | 0.895 | -0.062 | tgt2 | -0.215 | no | no |
| h4 | bos_retest | L | 3174 | 1.080 | 1.118 | -0.038 | trail | +0.011 | no | no |
| h4 | fvg_retest | S | 9255 | 0.883 | 0.895 | -0.012 | tgt2 | -0.165 | no | no |
| h4 | fvg_retest | L | 10471 | 1.130 | 1.118 | +0.012 | trail | +0.023 | no | **YES** |
| h4 | ob_retest | S | 1703 | 0.900 | 0.895 | +0.005 | tgt2 | -0.148 | no | no |
| h4 | ob_retest | L | 1819 | 1.200 | 1.118 | +0.083 | trail | +0.013 | no | **YES** |
| h4 | sweep_reclaim | S | 7595 | 0.938 | 0.895 | +0.043 | tgt2 | -0.106 | no | **YES** |
| h4 | sweep_reclaim | L | 6279 | 1.168 | 1.118 | +0.051 | trail | -0.014 | no | **YES** |

## CROSS-TF CELL — daily direction/zone + H1/H4 entry (the MTF model)

Daily context is CAUSAL: dailies aggregated from the same H1 data; for a signal
on session D only daily bars with date < D count. `in_dzone` = entry inside a
live direction-consistent daily OB/FVG (displacement ≥1.5×dATR14 / gap
≥0.3×dATR14; live till daily close beyond far edge, NO age limit; tol
0.25×dATR14). `trend_agree` = daily close vs SMA20 (close>SMA20 = up). Longs
shown; **all 32 short cells are net-negative** (H1 net −0.18..−0.26, H4
−0.08..−0.23, none econ-stable).

| TF | setup | subset | n | ratio | excess | best cfg | net_R | econ_hold | asym_hold |
|---|---|---|---|---|---|---|---|---|---|
| h1 | bos_retest L | uncond | 10884 | 1.054 | -0.018 | trail | -0.112 | no | no |
| h1 | bos_retest L | in_dzone | 2010 | 0.990 | -0.082 | tgt5 | -0.095 | no | no |
| h1 | bos_retest L | trend_agree | 6067 | 0.998 | -0.074 | tgt5 | -0.200 | no | no |
| h1 | bos_retest L | both | 847 | 0.911 | -0.161 | tgt5 | -0.160 | no | no |
| h1 | fvg_retest L | uncond | 35588 | 1.074 | +0.003 | trail | -0.065 | no | no |
| h1 | fvg_retest L | in_dzone | 10311 | 1.041 | -0.030 | trail | -0.069 | no | no |
| h1 | fvg_retest L | trend_agree | 20107 | 1.057 | -0.015 | trail | -0.097 | no | no |
| h1 | fvg_retest L | both | 4897 | 1.015 | -0.057 | trail | -0.070 | no | no |
| h1 | ob_retest L | uncond | 8214 | 1.035 | -0.037 | trail | -0.099 | no | no |
| h1 | ob_retest L | in_dzone | 3724 | 1.040 | -0.032 | trail | -0.061 | no | no |
| h1 | ob_retest L | trend_agree | 4573 | 1.019 | -0.053 | trail | -0.126 | no | no |
| h1 | ob_retest L | both | 1825 | 1.049 | -0.023 | tgt5 | -0.046 | no | no |
| h1 | sweep_reclaim L | uncond | 22946 | 1.000 | -0.072 | trail | -0.124 | no | no |
| h1 | sweep_reclaim L | in_dzone | 12521 | 0.980 | -0.092 | trail | -0.138 | no | no |
| h1 | sweep_reclaim L | trend_agree | 10072 | 0.981 | -0.091 | trail | -0.152 | no | no |
| h1 | sweep_reclaim L | both | 5489 | 0.978 | -0.094 | trail | -0.150 | no | no |
| h4 | bos_retest L | uncond | 3174 | 1.080 | -0.038 | trail | +0.011 | no | no |
| h4 | bos_retest L | in_dzone | 766 | 1.084 | -0.034 | trail | -0.013 | no | no |
| h4 | bos_retest L | trend_agree | 2322 | 1.055 | -0.063 | trail | -0.024 | no | no |
| h4 | bos_retest L | both | 614 | 1.097 | -0.021 | trail | -0.009 | no | no |
| h4 | fvg_retest L | uncond | 10471 | 1.130 | +0.012 | trail | +0.023 | no | YES |
| h4 | fvg_retest L | in_dzone | 4032 | 1.118 | +0.000 | trail | -0.011 | no | no |
| h4 | fvg_retest L | trend_agree | 7326 | 1.112 | -0.005 | trail | +0.028 | no | no |
| h4 | fvg_retest L | both | 2515 | 1.117 | -0.000 | trail | -0.005 | no | no |
| h4 | ob_retest L | uncond | 1819 | 1.200 | +0.083 | trail | +0.013 | no | YES |
| h4 | ob_retest L | in_dzone | 1074 | 1.152 | +0.034 | trail | +0.011 | no | no |
| h4 | ob_retest L | trend_agree | 996 | 1.201 | +0.083 | trail | +0.020 | no | YES |
| h4 | ob_retest L | both | 533 | 1.189 | +0.071 | trail | +0.032 | no | YES |
| h4 | sweep_reclaim L | uncond | 6279 | 1.168 | +0.051 | trail | -0.014 | no | YES |
| h4 | sweep_reclaim L | in_dzone | 3379 | 1.109 | -0.009 | trail | -0.052 | no | no |
| h4 | sweep_reclaim L | trend_agree | 1212 | 1.306 | +0.189 | trail | +0.114 | no | YES |
| h4 | sweep_reclaim L | both | 661 | 1.330 | +0.212 | tgt2 | +0.110 | no | YES |

**The daily-zone filter does not help.** On H1 every `in_dzone` subset has a
*lower* ratio than unconditioned and all are net-negative. On H4, `in_dzone`
*reduces* excess in 3 of 4 setups. Trend agreement helps only H4
sweep_reclaim — dissected below.

## Era stability (excess ratio / net_R of best long cfg per half-year)

H1 (trail):

| setup-L | 2023H2 | 2024H1 | 2024H2 | 2025H1 | 2025H2 | 2026H1 | 2026H2 |
|---|---|---|---|---|---|---|---|
| bos_retest | +0.02/+0.28 | -0.04/+0.10 | -0.01/-0.24 | -0.01/-0.23 | -0.04/-0.24 | -0.02/-0.25 | -0.16/-0.54 |
| fvg_retest | -0.01/+0.25 | -0.02/+0.09 | -0.00/-0.15 | +0.04/-0.07 | +0.03/-0.19 | -0.01/-0.20 | -0.08/-0.41 |
| ob_retest | -0.14/+0.11 | -0.03/+0.04 | -0.01/-0.14 | -0.03/-0.10 | +0.00/-0.18 | -0.04/-0.22 | +0.18/-0.29 |
| sweep_reclaim | -0.13/+0.10 | -0.08/-0.04 | -0.12/-0.24 | -0.10/-0.14 | -0.01/-0.18 | +0.04/-0.14 | +0.08/-0.27 |

Every H1 long is net-positive only in 2023H2–2024H1 (the smallcap bull) and
net-negative in **all ten** later setup×era cells of 2024H2 onward. Excess
ratio hugs zero throughout: the early profits are drift, not setup asymmetry.

H4 shows the same shape (positive only 2023H2/2024H1, negative after). The one
standout cell decays identically:

**h4 sweep_reclaim-L + trend_agree (trail), net_R by era:**
2023H2 **+0.74** → 2024H1 **+0.66** → 2024H2 −0.24 → 2025H1 +0.19 → 2025H2
−0.25 → 2026H1 −0.36 → 2026H2 −0.21. Ratio decays 2.43 → 1.97 → 1.01 → 1.56 →
1.08 → **0.72**. Temporal halves: first +0.36, second **−0.14** (why
`econ_hold=no`). Top-5 symbols carry 65% of total profit (87% for `both`).
The +0.11 pooled net expectancy is 2023-24 bull beta, dead for two years.
Caveat: no trend-conditioned null was computed, so even the early "excess" is
partly trend-continuation drift the unconditional null understates.

## VERDICT

1. **Asymmetry beyond null:** appears nowhere on M15 or H1 (long excess
   −0.09..+0.00; all H1 conditioned subsets *worse* than unconditioned). On H4
   a small long-side excess exists (ob +0.08, sweep +0.05, sweep×trend +0.19)
   and passes the 4-way asym holdout — but the era decomposition shows it is
   front-loaded in 2023H2–2024H1 and ≈0 or negative in 2025–26. It is regime
   beta, not a durable zone mechanism.
2. **Net-positive holdout-stable (TF, setup):** none. Zero of 24 ladder cells
   and zero of 64 cross-TF cells pass `econ_hold`. Best pooled cells (H4
   sweep×trend +0.11R, fvg-L +0.02R) are negative in the second temporal half
   and in 4 of the last 5 half-years. All shorts are net-negative everywhere
   (and H1/H4 shorts need futures anyway).
3. **Where the ladder points:** raw MFE/MAE ratio rises with TF (5m 0.99 → M15
   ~1.00 → H1 ~1.04 → H4 ~1.14 pooled longs) — but the random-entry null rises
   in lockstep (1.00 → 1.036 → 1.072 → 1.118). **Excess-over-null is flat at
   ~0 across the entire ladder.** The apparent improvement with timeframe is
   drift accrual, not capturable zone-to-zone asymmetry; after delivery costs
   H1 loses −0.07..−0.25R per trade on every setup. The intermediate
   timeframes are, plainly, the same symmetric repriced drift as 5m. Whatever
   hope remains lives at daily scale (sibling test) or requires a different
   edge class (not zone-retest mechanics) at these TFs.

---
Artifacts (scratchpad, `l4_` prefix): `l4_fetch.py/l4_h1.parquet` (60m, 138
syms, ~3y), `l4_build.py` (M15/H4/daily), `l4_setups.py`, `l4_measure.py`,
`l4_tags.py`, `l4_econ.py`, `l4_report.py`; tables `l4_ladder.csv`,
`l4_cells_h1.csv`, `l4_cells_h4.csv`; full console dump `l4_report.out`.
