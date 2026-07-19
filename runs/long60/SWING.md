# SWING — the MULTI-DAY HOLD hypothesis, measured

**Question**: the validated tools fire at the right zones but EOD squareoff amputates the payoff (user's HINDUNILVR 16/07 15:00 entry → +10R via overnight gap + next morning). Do the SAME signals, held ACROSS sessions, show the payoff asymmetry intraday lacked?

**Data**: all 300,153 signals (`signals60.parquet`, 7 parity-locked detectors, 138 stocks, 57 sessions 2026-04-27…2026-07-17) walked forward on the CONTINUUM native-5m series (`data/long5m/`), crossing overnights, N ∈ {1,2,3,5} full sessions beyond the signal session. Entry = next-bar open. N=0 (EOD) anchor reproduces RESULTS.md intraday numbers exactly (pooled 2.99/3.03, per-detector ratios 0.94–1.02) — methodology validated. Scripts: scratchpad `swing_step1.py`, `swing_econ.py`, `swing_econ_raw.py`, `swing_step4.py`; per-signal outputs `swing_mfe.parquet`, `swing_trades.parquet`.

**Units caveat**: ATR = the signal's 5m ATR (median **0.21% of price**, p25–p75 0.16–0.28%). Multi-day excursions are huge in these units precisely because the unit is tiny — and stops sized in it are tiny vs overnight gaps.

## STEP 1 — multi-day MFE/MAE asymmetry (THE HEADLINE)

Pooled, all 299,151 matched signals (n shrinks with N as horizon runs off the data edge):

| N sessions | n | mean MFE | mean MAE | **ratio** | med MFE | med MAE | P(MFE≥3ATR) | P(MAE≥1.5ATR) |
|---|---|---|---|---|---|---|---|---|
| 0 (intraday anchor) | 299,151 | 2.99 | 3.03 | **0.985** | 2.14 | 2.14 | 36.7% | 62.1% |
| 1 | 293,849 | 7.10 | 7.21 | **0.985** | 5.15 | 5.23 | 67.8% | 82.8% |
| 2 | 288,522 | 9.75 | 9.83 | **0.992** | 7.16 | 7.20 | 75.9% | 87.3% |
| 3 | 283,108 | 11.84 | 11.94 | **0.991** | 8.72 | 8.81 | 80.1% | 89.5% |
| 5 | 272,109 | 15.15 | 15.35 | **0.987** | 11.38 | 11.49 | 84.4% | 91.9% |

Per-detector MFE/MAE ratio by N:

| detector | N=0 | N=1 | N=2 | N=3 | N=5 |
|---|---|---|---|---|---|
| ob_lux | 0.965 | 0.986 | 1.004 | 1.001 | 0.985 |
| compression_fade | 1.003 | 0.987 | 0.987 | 0.987 | 0.987 |
| mitigation | 0.966 | 0.982 | 0.990 | 0.993 | 0.997 |
| fvg_cb | 0.990 | 0.989 | 0.991 | 0.979 | 0.966 |
| bpr | 1.018 | 0.961 | 0.964 | 0.990 | 1.019 |
| inducement | 0.996 | 1.011 | 0.983 | 0.978 | 0.970 |
| turtle_soup | 0.938 | 0.985 | 0.997 | 1.004 | 1.012 |

Holdouts (pooled ratio, N=1/3/5): T1 0.983/0.992/0.993 · T2 0.988/0.991/0.981 · C0 0.982/0.992/0.987 · C1 0.990/0.991/0.987.

**Verdict pivot: FAIL.** Intraday was 0.94–1.02; multi-day is **0.96–1.02 at every horizon, every detector, every holdout split**. The ratio does NOT reach 1.15 and does NOT grow with N. Holding across sessions makes both tails grow in lockstep (~random-walk √t scaling: 3.0 → 7.1 → 11.9 → 15.2 ATR). P(MAE≥1.5ATR) reaches 92% by N=5 — the stop gets hit long before the target on most paths. The overnight does not convert the zone edge into directional payoff; it just adds symmetric variance.

## STEP 2 — realistic swing economics

Deduped to real cadence: max 1 signal per (symbol, session, detector, direction), first-of-day → **72,641 trades** (from 300,153 raw). Fills: entry next-bar-open +2bp; stop = level-or-gap-open (overnight gaps DO gap through) +5bp; target limit −2bp, favorable gap-opens fill at open; intrabar stop-before-target; time-stop at close of session s0+H −5bp. Delivery costs: STT 0.1% BOTH legs, exch+GST 0.004% both, DP ₹15/sell, brokerage ₹0 (Zerodha delivery; ₹20-cap plans would add ~0.05R). Sizing: ₹10k risk, notional cap ₹2L, no leverage.

```
   k   scheme  H      n  win%   gross    netR      Rs      T1      T2      C0      C1   longR  shortR
 1.0  be1r_t3  3  68507   17%  -0.053  -0.966    -447  -0.925  -1.008  -0.954  -0.979  -1.193  -0.739
 1.0       t2  3  68507   31%  -0.066  -0.978    -454  -0.932  -1.027  -0.977  -0.980  -1.194  -0.763
 1.0       t3  3  68507   24%  -0.060  -0.972    -452  -0.934  -1.012  -0.961  -0.984  -1.206  -0.739
 1.0       t5  3  68507   16%  -0.050  -0.962    -449  -0.916  -1.010  -0.939  -0.987  -1.179  -0.746
 1.0   trail2  3  68507   19%  -0.020  -0.932    -432  -0.900  -0.965  -0.904  -0.963  -1.181  -0.683
 1.5  be1r_t3  3  68507   17%  -0.035  -0.643    -449  -0.615  -0.673  -0.631  -0.657  -0.796  -0.490
 1.5       t2  3  68507   32%  -0.054  -0.662    -466  -0.635  -0.691  -0.662  -0.663  -0.816  -0.509
 1.5       t3  3  68507   24%  -0.049  -0.658    -465  -0.623  -0.695  -0.647  -0.670  -0.810  -0.505
 1.5       t5  3  68507   17%  -0.042  -0.650    -467  -0.599  -0.704  -0.650  -0.649  -0.810  -0.489
 1.5   trail2  3  68507   22%  -0.016  -0.625    -437  -0.604  -0.647  -0.613  -0.638  -0.791  -0.458
 2.0  be1r_t3  3  68507   17%  -0.025  -0.481    -454  -0.452  -0.512  -0.477  -0.486  -0.597  -0.365
 2.0       t2  3  68507   32%  -0.041  -0.497    -470  -0.464  -0.531  -0.495  -0.499  -0.612  -0.382
 2.0       t3  3  68507   25%  -0.035  -0.491    -472  -0.450  -0.535  -0.492  -0.491  -0.606  -0.377
 2.0       t5  3  68507   18%  -0.028  -0.485    -475  -0.441  -0.531  -0.488  -0.481  -0.604  -0.366
 2.0   trail2  3  68507   24%  -0.012  -0.469    -438  -0.452  -0.486  -0.460  -0.479  -0.596  -0.342
```
(H=5 rows within ±0.015R of H=3 everywhere; full 30-config grid in `swing_econ.out`.)

- **0 of 30 configs positive; 0 of 30 even gross-positive pooled.** Gross (pre-cost) expectancy is −0.01…−0.08R — the Step-1 symmetry, restated in R. Best gross cells anywhere: bpr t5 H5 +0.04R, mitigation trail2 H5 +0.007R — noise-level, and both still net −0.61R.
- **Cost structure is fatal at this stop scale**: the ₹2L notional cap binds on 95% of trades (median real risk = qty×stop ≈ ₹766 at k=1.5), while delivery STT+DP ≈ ₹430–470 per round trip → **~0.48–0.91R structural drag** (0.61R mean at k=1.5). To dilute delivery costs below 0.1R the stop must be ≥~2% of price ≈ 10×(5m ATR) — daily-ATR geometry, not these zones' 5m geometry.
- **Raw (no dedupe) is worse**: k=1.5 raw net −0.73…−0.78R (gross −0.02…−0.06R, n=283k) vs deduped −0.62…−0.66R.
- **Shorts flag**: shortR shown for completeness but **cash delivery cannot short overnight** — shorts would need F&O (different cost stack). Long-only (the actually implementable side) is the WORSE half in this window: −0.60…−1.21R (the 57 sessions had a soft tape; another regime dependency, not an edge).

### Overnight gap tail — the real swing risk (dir-adjusted, 5m-ATR units)

```
night 1: n=68507 mean=-0.01 p1=-10.23 p5=-5.33 p50=+0.00 p95=+5.33 p99=+10.12 min=-64.13 max=+63.41 P(<-1.5atr)=27.65%
night 2: n=68507 mean=-0.02 p1=-10.88 p5=-5.31 p50=+0.00 p95=+5.25 p99=+10.31 min=-50.18 max=+52.35 P(<-1.5atr)=27.53%
night 3: n=68507 mean=+0.01 p1=-10.57 p5=-5.37 p50=+0.00 p95=+5.40 p99=+10.66 min=-46.42 max=+56.81 P(<-1.5atr)=27.24%
night 4: n=67211 mean=+0.01 p1=-10.73 p5=-5.26 p50=+0.00 p95=+5.38 p99=+11.32 min=-62.10 max=+64.26 P(<-1.5atr)=27.13%
night 5: n=65896 mean=-0.01 p1=-10.67 p5=-5.20 p50=+0.00 p95=+5.21 p99=+10.41 min=-53.26 max=+52.97 P(<-1.5atr)=27.01%
```

**~27% of held nights gap adversely by more than the ENTIRE k=1.5 stop distance.** Mean gap ≈ 0 (symmetric), worst single gap −64 ATR (≈ −13%). Realized in the sim (k=1.5 t3 H5): 76% of trades stop out; 5.6% of stops are gap-throughs; overnight gap-stops fill on average **1.50R beyond the stop** (p90 +3.3R, p99 +9.6R, worst +26.9R extra loss on 1R intended risk). Wider stops reduce excess but raise overnight-gap-stop frequency (k=2.0: 4.5% of trades, mean excess 1.18R). A stoploss is a fiction across NSE overnights at 5m-ATR scale — risk per trade is NOT 1R, it's 1R + a fat symmetric tail.

## STEP 3 — the user's trade shape: late entry (ts ≥ 14:00), held overnight

Step-1 asymmetry, late signals only (n=69,845 raw; pooled):

| N | n | mMFE | mMAE | ratio |
|---|---|---|---|---|
| 0 | 69,845 | 1.99 | 1.94 | 1.024 |
| 1 | 68,673 | 7.65 | 7.62 | **1.004** |
| 3 | 66,318 | 13.48 | 13.38 | **1.007** |
| 5 | 63,782 | 17.50 | 17.31 | **1.011** |

The exact user window — entry near close, hold through the overnight + next morning's first hour (deduped late, n=6,397):
- MFE 4.49 vs MAE 3.85 ATR → **ratio 1.169 — the only window in the entire study that crosses 1.15**.
- Overnight gap (dir-adjusted): mean **+0.28 ATR** (≈ +0.19R at k=1.5), P(gap ≥ +3ATR) 22.2% vs P(≤ −3ATR) 19.0% — a real but small favorable tilt: the tools do lean the right way into the close.
- The +10R shape (≥15 ATR by next morning at k=1.5): favorable 5.9% vs adverse 4.8% of late trades. The user's win is a ~1-in-17 draw whose mirror-image loss occurs at ~4/5 the frequency — and the mirror realizes WORSE than −10R because it gaps through the stop.
- **Decay**: the 1.17 edge exists only overnight+first-hour; by next-day EOD (N=1) the ratio is back to 1.004. The kernel is morning-gap momentum, not multi-day drift.
- **Economics**: late-only gross turns slightly positive at k≥1.5 (+0.01…+0.07R, best trail2 H5 +0.071R) vs pooled gross negative — but net stays **−0.56…−0.83R** after delivery costs. The tilt is ~0.06% of notional; delivery costs are ~0.21%. Costs are 3× the entire effect.

**Case study (the user's trade, found in-data)**: HINDUNILVR 2026-07-16 — compression_fade LONG 14:45 & 14:55: intraday MFE 0.74–1.16 ATR (dead at squareoff), held 1 session MFE **17.3–19.1 ATR ≈ +12R** at k=1.5. Real. But the SAME toolset fired HINDUNILVR SHORTS at 14:05/15:10/15:15 that day: overnight MAE **16.6–20.8 ATR** — the identical gap, wrong side, −11R through the stop. Four of five same-day signals straddled the gap in both directions. That is what ratio ≈ 1.0 looks like in a single name.

## STEP 4 — daily TOP-3 cross-sectional tournament (cadence model)

Per session pool all deduped universe signals, rank by a causal score, take top-3 (max 1/symbol) vs 200 seeded random-3 draws (same constraint). Outcomes at realistic costs, both capture modes. NOTE: ranking the day's full pool is selection-with-hindsight for BOTH arms — this measures picker skill, not a live policy.

```
INTRADAY capture (k=1.5 t1 EOD, intraday costs), 57 sessions; random-3 mean -0.156R [p10 -0.246, p90 -0.065]
strength   top3 -0.154R  pctile-vs-random  51.0  T1 -0.271 (p12)  T2 -0.041 (p91)
detpri     top3 +0.003R  pctile-vs-random  98.0  T1 -0.110 (p63)  T2 +0.113 (p100)
dailypoi   top3 -0.112R  pctile-vs-random  73.5  T1 -0.198 (p32)  T2 -0.030 (p92)
tight_sl   top3 -0.278R  pctile-vs-random   4.0  T1 -0.152 (p47)  T2 -0.399 (p1)
composite  top3 -0.213R  pctile-vs-random  22.5  T1 -0.284 (p11)  T2 -0.144 (p56)

SWING capture (k=1.5 t3 H=3, delivery costs), 54 sessions; random-3 mean -0.666R [p10 -0.841, p90 -0.469]
strength   top3 -0.447R  pctile-vs-random  93.5  T1 -0.507 (p74)  T2 -0.383 (p92)
detpri     top3 -0.483R  pctile-vs-random  88.5  T1 -0.423 (p86)  T2 -0.548 (p76)
dailypoi   top3 -0.424R  pctile-vs-random  95.5  T1 -0.609 (p54)  T2 -0.225 (p98)
composite  top3 -0.454R  pctile-vs-random  92.5  T1 -0.565 (p68)  T2 -0.334 (p96)
tight_sl   top3 -0.733R  pctile-vs-random  33.5  T1 -0.512 (p73)  T2 -0.971 (p10)
```

Several rankings beat random-3 pooled (dailypoi p95.5, composite p92.5 swing; detpri p98 intraday — the single ~breakeven cell in the whole study at +0.003R). But **no ranking clears p90 in BOTH temporal halves** in either mode — every pooled winner is carried by one half (usually T2, the half containing the old in-sample window). And even granting the best pick skill at face value, top-3 swing expectancy is still **−0.42R**. Plainly: **daily top-K selection shows no holdout-stable picker skill — cadence alone doesn't fix per-trade expectancy**, and tight_sl (tighter structural stop first) is actively harmful. The weak POI/detector-priority tilts are worth remembering as context features, nothing more.

## VERDICT

1. **Does holding across sessions create MFE/MAE asymmetry ≥ 1.15?** **No.** 0.985–0.992 pooled at every N, 0.96–1.02 per detector, stable across all four holdout splits. Identical to intraday. The overnight adds symmetric variance, not directional payoff. This is the load-bearing answer and it is unambiguous on 300k signals.
2. **Does ANY swing config net positive holdout-stable?** **No.** 0/30 deduped (and 0/10 raw) configs positive; none is even gross-positive pooled. Delivery costs (0.2% of notional round-trip vs stops of 0.3–0.6% of price) add a structural −0.5…−0.9R on top of ~0R gross. Plus ~27% of nights gap through the entire stop — realized overnight gap-stops average 1.5R excess loss; tail risk is unbounded relative to intended 1R.
3. **Is the late-entry-overnight shape special?** **Marginally, and honestly the only positive finding**: overnight+first-hour after a ≥14:00 signal is the one window with ratio ≥1.15 (1.169; gap tilt +0.28 ATR, 22.2% vs 19.0% at ±3ATR; late gross turns +0.01…+0.07R). But it decays to ~1.00 by next-day close, is ~3× smaller than delivery costs, and the user's +10R draw has a near-equal-frequency mirror loss (5.9% vs 4.8%) that gaps THROUGH the stop. The HINDUNILVR win and its four same-day wrong-side siblings coexist in the data. The shape is a tail memory, not an edge.
4. **Does this justify the full 20-year daily-data system build?** **Not on this evidence.** The specific hypothesis "these 5m zone signals + longer holds = payoff" is dead: zero multi-day drift (gross ≈ 0 before costs), and 5m-scale stop geometry cannot carry delivery costs or overnight gaps. A daily-data system would have to be a DIFFERENT system — daily-native setups, daily-ATR stops (≥~2% of price), where costs are <0.1R and gaps are intrabar noise rather than stop-killers. Nothing measured here supports (or tests) that; the one transferable seed is the small late-day/overnight-gap-direction tilt and the weak POI/detector-priority ranking signal. If the 20-year build proceeds, it proceeds on a new hypothesis, not on these signals' demonstrated carry — and this study says their carry is zero.
