# LEARN — winner-autopsy supervised loop (ML-grade)

Question: do the big winners (the screenshot class) differ from the silent failures in any
way visible at signal time — across ALL tool/context features simultaneously?
Data: `signals60` — 300,153 signals, 138 stocks, 57 sessions (2026-04-27..2026-07-17, 5m),
joined with every tag ever computed (daily-POI, nested/liquidity flags, mom7 aligns) plus
bar-series features computed inline. Money = `net_R` at k=1.5 stop, fixed 1R target (cfg 21),
delivery costs included. Precedent guarding this run: the mom7 mirage (+16pp discovery →
-0.8pp at scale). Nothing below counts unless it survived BOTH symbol-fold and temporal holdouts.

## Features (44, all causal — known at the signal bar close)

| group | features |
|---|---|
| signal geometry | risk_atr (stop size / ATR), zone_size_atr, entry_in_zone, atr_rel (ATR % of price), strength, direction |
| tool identity | detector (7), template (5) |
| context pipeline | idx_phase, wyck, pd_pos, pd_cls, m15_net_atr, htf, vol, vol_ratio, tb |
| daily-POI tags | in_daily_poi, in_ob, in_fvg, in_swing, deep, has_daily, poi_age_days |
| nested/liquidity | l1, in_h1z, l2, daily_align, h1_align, liq_away, liq_into, swept_rec, l2_liq |
| bar-series (inline) | bars_since_open, hour, dow, atr_pct (500-bar vol regime), retr_depth50, pos_in_range50, range50_atr, dist_fav100_atr, dist_adv100_atr, drift1d_atr, drift1d_align |

Excluded from main runs: mom7 `align5/7/10/14` — present for 99.9% of early-half signals but
6.3% of late-half (pipeline artifact ⇒ missingness = time proxy). Tested separately below.

## Labels

- **L1** big winner (max_r ≥ 5, n=43,702) vs silent failure (max_r < 1, n=129,207); middle dropped.
- **L2** hit vs loss (n=292,107, undecided dropped).
- **L3** regression on net_R @ k=1.5 fixed_t1 (n=300,153, mean −0.286R).
- **L4** shakeout: stopped at 1.5R then ≥3R favorable within 60 bars, among stopped trades
  (70.7% of signals get stopped at 1.5R; 46.7% of those recover to 3R — the "SL by mistake" class).

## Validation gauntlet

GroupKFold(5) by SYMBOL (conclusions must transfer across stocks) + strict temporal split at
2026-06-08 run BOTH directions. Model: HistGradientBoosting (+ logistic/ridge baseline).

## AUC / rank-IC — everything survives both holdouts

| task | n | base | GKF folds (by symbol) | pooled | linear | temporal e→l | temporal l→e |
|---|---|---|---|---|---|---|---|
| L1 big vs fail | 172,909 | .253 | .768 .763 .773 .772 .766 | **.768** | .750 | **.758** | **.750** |
| L2 hit vs loss | 292,107 | .500 | .543 .554 .554 .548 .549 | **.549** | .524 | **.518** | **.519** |
| L3 net_R rank-IC | 300,153 | −.286R | .309 .311 .298 .310 .315 | **.310** | .326 | **.201** | **.248** |
| L4 shakeout | 212,159 | .467 | .826 .823 .823 .821 .827 | **.824** | .816 | **.808** | **.809** |

Stable, real, out-of-sample. **But look at what carries it** — permutation importance
(trained early, permuted on late half):

| task | #1 | #2 | #3 | rest |
|---|---|---|---|---|
| L1 | risk_atr **0.241** | bars_since_open 0.010 | detector 0.003 | all ≤ 0.003 |
| L4 | risk_atr **0.271** | bars_since_open 0.019 | atr_rel 0.004 | all ≤ 0.003 |
| L2 | risk_atr 0.004 | direction 0.004 | dist_adv100 0.003 | flat tail |

## The mechanical confession

`max_r` is measured in R = move/risk. A stop of 0.15 ATR makes "5R" ≈ 0.75 ATR of ordinary
noise; a stop of 1.5 ATR makes 5R a genuine 7.5-ATR run. The "big winner" class is therefore
mostly a **stop-size artifact**, and the model found exactly that:

| risk_atr bucket | P(max_r≥5) early/late | net_R21 early/late |
|---|---|---|
| ≤ 0.24 ATR | .532 / .552 | −0.25 / −0.29 |
| 0.24–0.49 | .298 / .292 | −0.27 / −0.29 |
| 0.49–0.80 | .224 / .214 | −0.27 / −0.31 |
| 0.80–1.33 | .154 / .156 | −0.27 / −0.32 |
| > 1.33 ATR | .051 / .056 | −0.28 / −0.31 |

10× swing in "big winner" rate; **net_R flat and negative everywhere**. Same story per
detector (all 7 between −0.23 and −0.34 in both halves). L4 likewise: shakeout probability is
79% for sub-0.24-ATR stops with session time remaining vs 6% for wide stops — i.e. "your SL
was hit by mistake" ≈ "your SL was smaller than the noise", predictable at AUC 0.81 and
worth nothing, because re-entering only re-enters the same negative-expectancy trade.

### De-mechanized check (what remains after removing stop geometry)

| experiment | GKF | temporal e→l | temporal l→e |
|---|---|---|---|
| L1, all 44 features | .768 | .758 | .750 |
| L1, **risk_atr ONLY** | .745 | .749 | .741 |
| L1, minus stop geometry (risk_atr, zone_size, atr_rel, entry_in_zone) | .671 | .648 | .644 |
| L1, minus stop geometry AND detector (detector proxies stop size) | .646 | .620 | .620 |
| L1atr — stop-free label: mfe ≥ 2 ATR vs < 0.5 ATR | .676 | .622 | .622 |
| L1atr, bars_since_open ONLY | | .600 | |
| L1atr, bars_since_open + atr_pct + atr_rel | | .618 | |
| L4, all 44 features | .824 | .808 | .809 |
| L4, **risk_atr + bars_since_open ONLY** | | .813 | |

Reading: one feature (stop size in ATR) carries .745 of L1's .768. Strip stop geometry and
its detector proxy and only .62 remains. Re-pose the question stop-free ("will price move
2 ATR my way?") and the temporal AUC is .622 — of which .600 is *bars since open alone*
(early signals simply have a longer measurement window before session end) and .618 adds only
vol regime. Chart-visible features contribute ≤ .004 AUC to predicting big ATR moves.
For L4, two mechanical features replicate the entire 44-feature model (.813 vs .808).

## THE MONEY TEST — no decile is net-positive, anywhere

Top decile of out-of-sample predictions vs the rest (net_R @ cfg21, hit%):

| ranking | half | top-decile hit% | top-decile net_R | rest net_R |
|---|---|---|---|---|
| L2 GKF-OOF | early | 58.3% | −0.105 | −0.283 |
| L2 GKF-OOF | late | 55.7% | −0.198 | −0.317 |
| L2 temporal-OOS | early | 53.0% | −0.213 | −0.271 |
| L2 temporal-OOS | late | 53.2% | −0.265 | −0.310 |
| L3 GKF-OOF | early | 55.1% | **−0.029** | −0.292 |
| L3 GKF-OOF | late | 52.3% | −0.116 | −0.326 |
| L3 temporal-OOS | early | 48.7% | −0.173 | −0.276 |
| L3 temporal-OOS | late | 49.3% | −0.212 | −0.315 |
| L1 GKF-OOF | early | 62.3% | −0.143 | −0.464 |
| L1 GKF-OOF | late | 62.2% | −0.171 | −0.495 |
| L1 temporal-OOS | early | 61.2% | −0.151 | −0.463 |
| L1 temporal-OOS | late | 61.5% | −0.183 | −0.494 |
| naive tightest-stop | early | 51.9% | −0.234 | −0.269 |
| naive tightest-stop | late | 50.4% | −0.281 | −0.307 |

Full L3 decile curve (GKF-OOF, early): −.52 −.43 −.37 −.33 −.29 −.24 −.19 −.16 −.10 −.03 —
perfectly monotone ranking, ceiling below zero. The temporal-OOS ceiling is −0.17/−0.21.
The model is genuinely learning to rank; what it ranks is cost drag and stop mechanics, and
even the best-ranked 10% of 300k signals loses money after costs.

## Stable patterns that DID survive both holdouts (for the record)

Every one is small, or mechanical, or both — none monetizes at cfg 21:

- **Shorts > longs**: hit% 51.7/51.8 vs 48.4/47.9 (early/late) — +3pp, stable, the largest
  honest non-mechanical signal in the whole dataset.
- **Old daily POIs beat young**: POI age > 31 days → hit 53.2/51.9 vs ≤1 day 50.5/49.7.
- **Entry deep in the zone beats entry at the edge**: entry_in_zone bottom quintile hit
  51.5/51.3 vs beyond-zone 48.1/48.3.
- **fvg_cb is the outlier tool**: lowest big-winner rate (11.6/9.9% vs 33.7/33.9% for
  compression_fade) and by far the fewest shakeouts (17.2/13.2% vs 59.4/59.2%) — because its
  stops are structurally wide, not because its charts are better; its net_R (−0.23/−0.26) is
  the least bad of the 7 detectors in both halves.
- **Deep retracement (>0.88 of the 50-bar leg) lifts P(big)** 30.5/30.2% vs 23.0/22.3% —
  the one classic-TA pattern with a stable non-trivial edge on max_r, still net-negative.
- **Low vol-regime helps big winners** (atr_pct bottom quintile 28.3/27.7% vs top 23.0/21.7%).
- L2 tree at depth 3: best leaf reaches 55% hit — worth ≈ −0.15R after costs.

## mom7 side-check (align7, early half where coverage is 99.9%)

GKF AUC with vs without align7: L1 .7695 → .7695, L2 .5717 → .5717. Delta = 0.0000.
The momentum-alignment feature adds literally nothing on top of the other 44 features.
MOM7 closure re-confirmed at ML grade.

## VERDICT

**ML-grade closure, with the mechanism named.** A gradient-boosted model given every feature
ever computed in this project — tool identity, zone geometry, Wyckoff/premium-discount
context, daily-POI residence, nested liquidity flags, momentum alignment, vol regime, time
of day, retracement depth, prior drift — and validated across 138 symbols and two disjoint
time halves, finds:

1. The big-winner class IS predictable (AUC .77) and shakeouts ARE identifiable in advance
   (AUC .81) — but both are one feature in disguise: **stop size relative to ATR**. R-unit
   inflation, not chart quality. The screenshot class is mostly tight stops on ordinary moves.
   Re-posed stop-free ("will price move 2 ATR my way?"), predictability falls to .622
   temporal, of which .600 is the session clock and vol regime; chart features add ≤ .004.
2. Genuine trade-direction skill — hit vs loss from chart-visible features — is AUC 0.549
   within-period, **0.518 across time**: the 0.5–0.55 closure band.
3. The money test is unanimous: across L1/L2/L3 rankings, both validation schemes, both
   temporal halves, **no out-of-sample decile of 300k signals is net-positive**. Best ceiling
   −0.03R in-fold, −0.17R strict-temporal, vs base −0.29R.

No learnable combination of chart-visible features separates winners from failures well
enough to overcome the cost structure. The tools' R-multiples are a geometry of stop
placement; the "SL by mistake" experience is the statistically expected behavior of sub-ATR
stops, not evidence of a readable edge being narrowly missed.

Artifacts: `learn_features.py/.parquet`, `learn_train.py/.out`, `learn_rules.py`,
`learn_demech.py`, `learn_results.json`, `learn_money.csv`, `learn_scan_*.json`,
`learn_tree_*.txt`, `learn_oof_*.parquet` (scratchpad, `learn_` prefix).
