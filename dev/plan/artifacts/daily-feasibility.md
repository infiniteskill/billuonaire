# DAILY-NATIVE SWING FEASIBILITY — NSE, max free history

**Date:** 2026-07-18 · **Data:** yfinance `period="max"`, `auto_adjust=False`, 138 NSE symbols (data/long5m stems, LTIM/TATAMOTORS skipped) + ^NSEI. 758,526 daily rows, most series 1996–2002 → 2026-07-17 (~24–30y). Splice guard: doctor.splices logic at >25% close→open → **226 independent segments**; no signal, window, or trade spans a splice. Bad-row guard: H/L clamped to contain O/C; bars with ATR < 0.2% of price (stale/flat illiquid stretches) ineligible. ATR = Wilder ATR(14, daily). All setups leak-free: signal on closed daily bar, entry next day's OPEN ± 2bp half-spread.

---

## ⚠️ SURVIVORSHIP CAVEAT (read first)

**This universe is today's liquid F&O names backtested up to 30 years into their own past. It contains only winners — every bankruptcy, delisting and fade-to-illiquidity is absent.** Quantified below: equal-weight buy-and-hold of this universe returned **+18.4%/yr** vs NIFTY's +9.4% — that ~9pp gap *is* the survivorship inflation, and it leaks into every long expectancy in this report (setups AND null alike). All headline long numbers are biased UP; only the *setup-minus-null* differences and regime-split stability are trustworthy.

**⚠️ SHORTS CAVEAT:** cash-delivery shorts are impossible in India (no overnight short in cash segment). Every short row below is futures-only hypothetical (margin, rollover and lot-size costs NOT modelled — real shorts are worse than shown). As shown, all shorts lose anyway.

---

## STEP 1 — Asymmetry discriminator: MFE/MAE in dATR units

Median dATR = **3.24% of price** (daily-scale stops confirmed ≥2%).

**The null (random-entry LONG, every eligible day, n≈740k; SHORT = exact mirror):**

| N (days) | MFE mean | MAE mean | MFE med | MAE med | **ratio** | P(MFE≥2) | P(MAE≥2) |
|---|---|---|---|---|---|---|---|
| 5  | 1.239 | 1.133 | 0.927 | 0.882 | **1.094** | 0.188 | 0.156 |
| 10 | 1.854 | 1.583 | 1.417 | 1.235 | **1.171** | 0.352 | 0.290 |
| 20 | 2.792 | 2.183 | 2.157 | 1.703 | **1.279** | 0.531 | 0.432 |
| 40 | 4.278 | 2.962 | 3.289 | 2.303 | **1.444** | 0.683 | 0.556 |

Equity drift alone produces 1.44 asymmetry at 40 days. **A setup only matters if it beats THIS, not 1.0.**

**Setups, LONG, MFE/MAE ratio vs the null (condensed):**

| setup (long) | n | N=10 | N=20 | N=40 | vs null @40 (1.444) |
|---|---|---|---|---|---|
| daily_ob_retest | 4.9k | 1.151 | 1.277 | **1.480** | +0.036 |
| daily_fvg_retest | 30.4k | 1.192 | 1.301 | **1.461** | +0.017 |
| daily_coil_break | 31.3k | 1.203 | 1.316 | **1.452** | +0.008 |
| daily_bos_retest | 13.5k | 1.128 | 1.253 | 1.403 | −0.041 |
| daily_coil_fade | 23.7k | 1.075 | 1.172 | 1.364 | −0.080 |
| daily_sweep_reclaim | 21.6k | 1.018 | 1.114 | 1.303 | −0.141 |

**Setups, SHORT: every ratio < 1.0 at every horizon** (0.63–0.98; e.g. pooled short N=40 ratio 0.708). Shorting into structural drift.

**Reading:** best setup beats the drift null by +0.008…+0.036 ratio points. The user-shape setups (OB/FVG retest) sit *at* the null, not above it. P(MFE≥2)−P(MAE≥2) for the best long setup (ob@40: 0.669−0.532 = +0.137) vs null (0.683−0.556 = +0.127): ~1pp of "edge".

## STEP 2 — Economics (structural SL floored at 1.5×dATR, targets/trail, time-stop 40d)

Costs modelled: 0.1% STT both sides + 0.004% txn + ₹15 DP/sell + 2bp half-spread both sides; risk sizing ₹10k (1% of ₹10L). Median stop distance = **4.93% of price** → measured cost drag = **0.045R mean** round trip. *Hypothesis (b) — delivery costs shrink below 0.1R at daily scale — is CONFIRMED. Cost was never the problem here.*

Net expectancy (R/trade), LONG | SHORT, by config:

| setup | tgt2 | tgt3 | tgt5 | trail |
|---|---|---|---|---|
| daily_ob_retest | **+0.125** \| −0.180 | **+0.184** \| −0.227 | **+0.255** \| −0.262 | +0.202 \| −0.207 |
| daily_fvg_retest | +0.102 \| −0.177 | +0.162 \| −0.217 | +0.223 \| −0.255 | +0.208 \| −0.228 |
| daily_bos_retest | +0.068 \| −0.195 | +0.136 \| −0.231 | +0.203 \| −0.270 | +0.200 \| −0.268 |
| daily_coil_break | +0.060 \| −0.215 | +0.121 \| −0.263 | +0.213 \| −0.303 | +0.211 \| −0.301 |
| daily_coil_fade | +0.075 \| −0.241 | +0.138 \| −0.295 | +0.192 \| −0.335 | +0.117 \| −0.221 |
| daily_sweep_reclaim | +0.058 \| −0.222 | +0.111 \| −0.276 | +0.154 \| −0.307 | +0.068 \| −0.208 |

**The economics null — random long entries through the IDENTICAL engine** (stop = 1.5×dATR, same targets/costs, n≈29.5k, seed 42):

| cfg | random-long net_R | random-short net_R |
|---|---|---|
| tgt2 | **+0.086** | −0.222 |
| tgt3 | **+0.146** | −0.277 |
| tgt5 | **+0.216** | −0.308 |
| trail | **+0.199** | −0.261 |

Every setup's win rate ~0.30–0.42 with median trade ≈ **−1.03R** (most trades stop out; the mean is carried by drift-tail winners) — for setups and null alike. **Random entry with the same trade template earns +0.216R at tgt5; the best setup earns +0.255R.** The entire economic result is the template + drift, not the setup.

## STEP 3 — Walk-forward regime splits (E1 ≤2012 · E2 2013–19 · E3 2020–26)

All 24 long setup×config cells are net-positive in ALL three eras — **but so is the random-entry null in all three eras** (e.g. tgt5: +0.228/+0.175/+0.238). "Positive in every era" is achieved trivially by drift; the criterion that matters is **edge over the era-matched null**:

Edge (setup_netR − null_netR), LONG:

| setup · cfg | E1 | E2 | E3 | all-era positive? |
|---|---|---|---|---|
| ob_retest tgt3 | +0.047 | +0.054 | **+0.003** | ✓ (barely) |
| fvg_retest tgt2 | +0.031 | +0.003 | +0.008 | ✓ (barely) |
| ob_retest tgt2 | +0.046 | +0.074 | −0.009 | ✗ |
| ob_retest tgt5 | +0.040 | +0.083 | −0.007 | ✗ |
| fvg_retest tgt5 | +0.032 | +0.001 | −0.025 | ✗ |
| bos_retest (all cfgs) | + | − | − | ✗ |
| coil_break (all cfgs) | ± | − | ± | ✗ |
| sweep_reclaim tgt5/trail | −0.095/−0.147 | ±0.01/−0.042 | −0.087/−0.196 | ✗ (sig. negative) |

- Only **2 of 24** configs have positive edge in all eras, both ≤+0.05R with the weakest era at +0.003…+0.008R — i.e. zero within noise, and shrinking toward the present.
- Pooled t-stats vs null: best is ob_retest tgt2 **t=+1.79** (24 comparisons → Bonferroni needs |t|≳3; nothing qualifies). The only |t|>3 results are **negative**: sweep_reclaim trail t=−7.47, coil_fade trail t=−4.55, sweep tgt5 t=−3.42 — the mean-reversion-shaped setups are reliably *worse* than random.
- crc32%2 split: all cells positive in both halves (drift again), but the "best" setup ob_retest is the least stable: tgt5 +0.323 (crc0) vs +0.176 (crc1) — its apparent edge halves across a random symbol split.

## STEP 4 — vs buy-and-hold

| benchmark | E1 | E2 | E3 | FULL |
|---|---|---|---|---|
| NIFTY B&H (from 2007-09, index inception on Yahoo) | +5.30%/yr | +10.66%/yr | +11.16%/yr | **+9.38%/yr** |
| **Equal-weight B&H of the SAME 138 survivor names** | +20.40%/yr | +13.71%/yr | +18.27%/yr | **+18.38%/yr** |

System, capital-constrained on ₹10L (avg position ≈ ₹2L → ~5 slots vs 10–80 signal-concurrency; expectation-scaled):

| strategy | constrained return |
|---|---|
| best setup: ob_retest tgt5 | +16.9%/yr |
| fvg_retest trail | +14.0%/yr |
| typical setups | +5.4…+13%/yr |
| **random-entry long, same engine** | **+13.3…+13.8%/yr** |
| **EW buy-and-hold, same names** | **+18.4%/yr** |

**Passive holding of the very names the system trades beats every configuration of every setup — with zero effort, zero churn, and full STT/DP costs avoided. The setups' 14–17% is (a) mostly the null's 13–14%, and (b) entirely inside the survivor-universe drift of 18.4%.** Against the bias-free benchmark (NIFTY 9.4%), nothing here demonstrates edge beyond universe selection.

---

## Weekly TF (amendment: same machinery, daily bars aggregated 5→1, Mon-anchored, within-segment)

4 setups (ob/fvg/bos + sweep on 20-**week** extremes), ATR(14, weekly), horizons in weeks. Median stop = **11.0% of price** → cost drag **0.021R** (negligible, as hypothesized).

**Weekly null (random-entry long, n≈150k):** ratio 1.308 @5w, 1.494 @10w, **1.794 @20w** — drift asymmetry grows with holding scale, without any setup.

| setup (long) | ratio @10w | ratio @20w | vs null (1.494/1.794) |
|---|---|---|---|
| daily_fvg_retest | 1.542 | 1.865 | +0.05/+0.07 |
| daily_bos_retest | 1.446 | 1.763 | −0.05/−0.03 |
| daily_ob_retest | 1.429 | 1.743 | −0.07/−0.05 |
| daily_sweep_reclaim | 1.288 | 1.506 | −0.21/−0.29 |
| all shorts | 0.63–0.75 | 0.52–0.63 | deeply below 1 |

**Weekly economics (net_R, long | null):**

| cfg | fvg | bos | ob | sweep | **random null** |
|---|---|---|---|---|---|
| tgt5 | +0.782 | +0.731 | +0.654 | +0.551 | **+0.785** |
| trail | +0.997 | +0.957 | +0.715 | +0.427 | **+0.971** |

Per-era (longs, trail): fvg +1.033/+0.746/+1.171 vs null +1.046/+0.689/+1.152 — edges of ±0.06R, sign-flipping across eras. All weekly shorts −0.26…−0.54R. **Weekly is the same verdict at bigger scale: expectancies triple because holds triple and stops widen — the null triples right alongside. Best weekly setup edge over null ≈ +0.03R on a 20-week hold.**

---

# VERDICT

1. **Do daily setups show asymmetry beyond the drift null? NO.** Long null MFE/MAE = 1.44 @40d (1.79 @20w weekly); the best setup reaches 1.48. Edge over null ≤ +0.04 ratio points / ≤ +0.04R, max t = +1.79 across 24 comparisons (needs ≳3). Three setups are *significantly worse* than random. Shorts are uniformly destroyed at every horizon and timeframe.
2. **Any setup net-positive in ALL eras after costs? Trivially yes — and meaningless**, because the random-entry null is also net-positive in all eras in every config. Against the era-matched null, only 2/24 configs stay positive, with worst-era edge ≈ +0.003R (zero). Nothing survives honest regime-split scrutiny, and the survivor universe makes even those crumbs suspect.
3. **Does it beat buy-and-hold? NO.** Best constrained config +16.9%/yr vs +18.4%/yr for equal-weight holding of the same names (and the +16.9% is itself survivorship-inflated; the clean benchmark, NIFTY, is +9.4%).
4. **Is a full daily-system build justified? NO.** The one genuinely positive finding: at daily/weekly scale, delivery costs really do collapse (0.045R daily, 0.021R weekly) — cost hypothesis (b) confirmed. But hypothesis (a) fails: the payoff asymmetry that appears at daily scale is *equity drift itself*, fully captured by random long entries with the same stop/target template. With ~30 years, 252k daily + 27k weekly signals, and no excuses left: **daily and weekly setups are repriced drift, exactly as the 5m setups were repriced noise. The only validated free-data edge in this entire program is "be long Indian equities" — and an index fund implements it better than any of these detectors.**

*Artifacts: scratchpad/{dailymax,dmaster,dsignals,dtrades,dtrades_null,dstep1_sig,dstep1_null,wstep1_sig,wstep1_null,wtrades,wtrades_null}.parquet · scripts dailymax_fetch.py, dsetups.py, dstep1.py, dstep2.py, dstep2b.py, dstep3_4.py, dweekly.py · raw tables dstep1.out, dstep2.out, dstep34.out, dweekly.out.*
