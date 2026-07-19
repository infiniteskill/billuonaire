# MOMENTUM / CONTINUATION hypothesis -- realistic-fill test (data/wide, 138 stocks, M1; 2 files empty: LTIM, TATAMOTORS; NIFTY excluded as index)

Pivot after fades were falsified (symmetric MFE~MAE, ~-0.31R/trade). Thesis: entering WITH a confirmed move captures continuation where favorable excursion EXCEEDS adverse (MFE>>MAE). Detection on M5 (M15 for trend), forward-walk on M1. Fills replicate app/trader/execution/paper.py: entry=next-M1-open+half-spread; stop=level/gap-open+half+slippage (never a clean stop fill); target=limit; EOD=last close+half+slippage; intrabar stop-before-target (conservative). Costs Rs20x2 + 0.025% sell STT + 0.00297% exchange both legs; spread embedded. Sizing 1% of Rs10L = Rs10k = 1R, qty capped 5x leverage. Leak-free: detection uses bars up to the M5 signal close; entry starts next M1 bar.

## STEP A -- MFE/MAE DISCRIMINATOR (target-independent, EOD M1 path, ATR units)  << reported FIRST >>

If symmetric like the fades (ratio ~1.0), the variant is dead before any exit tuning.

| variant | n | dir(L/S) | mean MFE | mean MAE | med MFE | med MAE | MFE/MAE | P(MFE>=2ATR) | P(MAE>=1ATR) | asymmetric? |
|---|---|---|---|---|---|---|---|---|---|---|
| bos_cont | 733 | 384/349 | 3.45 | 2.90 | 2.30 | 2.26 | 1.19 | 55% | 74% | weak |
| disp_break | 6351 | 3023/3328 | 3.10 | 2.96 | 2.05 | 2.18 | 1.05 | 51% | 75% | no |
| trend_pull | 3106 | 1536/1570 | 2.93 | 2.84 | 2.05 | 1.99 | 1.03 | 51% | 73% | no |
| orb_break | 2490 | 1190/1300 | 3.01 | 3.02 | 2.19 | 2.38 | 1.00 | 54% | 76% | no |
| ign_retest | 1352 | 738/614 | 2.62 | 2.69 | 1.88 | 1.83 | 0.97 | 47% | 71% | no |

Fade baseline for comparison (from runs/wide/extraction.md): every fade detector MFE/MAE in **0.96-1.11** (inducement 1.11, compression 1.02, ob_lux 0.96, mitigation 0.96). i.e. fades were symmetric.

## STEP B -- realistic-fill extraction grid, best 6 configs per variant (net exp R, n>=40)

SL: k in {0.5,0.75,1.0,1.5}xATR or 'struct' (signal's natural structural stop). Schemes: fixed_t{1..5}, be1r (breakeven@1R), trail (ATR-ratchet), trail_t{2,3,5}.

| variant | SL | scheme | n | win% | exp R | med R |
|---|---|---|---|---|---|---|
| bos_cont | struct | fixed_t1 | 727 | 42% | -0.018 | -0.048 |
| bos_cont | struct | fixed_t2 | 727 | 42% | -0.019 | -0.051 |
| bos_cont | struct | be1r_t2 | 727 | 41% | -0.020 | -0.054 |
| bos_cont | struct | fixed_t1.5 | 727 | 42% | -0.020 | -0.051 |
| bos_cont | struct | fixed_t5 | 727 | 42% | -0.020 | -0.051 |
| bos_cont | struct | be1r_t1.5 | 727 | 41% | -0.020 | -0.054 |
| disp_break | struct | trail | 6351 | 27% | -0.291 | -0.612 |
| disp_break | struct | trail_t5 | 6351 | 27% | -0.294 | -0.612 |
| disp_break | struct | fixed_t1 | 6351 | 43% | -0.295 | -0.628 |
| disp_break | struct | be1r_t3 | 6351 | 23% | -0.296 | -0.658 |
| disp_break | struct | be1r_t2 | 6351 | 27% | -0.296 | -0.654 |
| disp_break | struct | fixed_t2 | 6351 | 32% | -0.297 | -1.137 |
| ign_retest | struct | fixed_t1 | 1352 | 45% | -0.293 | -0.489 |
| ign_retest | 1.5 | fixed_t1 | 1352 | 44% | -0.305 | -0.717 |
| ign_retest | struct | fixed_t2 | 1352 | 32% | -0.305 | -1.079 |
| ign_retest | struct | be1r_t2 | 1352 | 27% | -0.305 | -0.597 |
| ign_retest | struct | fixed_t1.5 | 1352 | 37% | -0.306 | -1.016 |
| ign_retest | struct | be1r_t5 | 1352 | 20% | -0.311 | -0.603 |
| orb_break | struct | fixed_t1 | 2490 | 44% | -0.090 | -0.097 |
| orb_break | struct | be1r_t2 | 2490 | 40% | -0.093 | -0.121 |
| orb_break | struct | be1r_t3 | 2490 | 40% | -0.094 | -0.123 |
| orb_break | struct | be1r_t1.5 | 2490 | 41% | -0.094 | -0.119 |
| orb_break | struct | be1r_t5 | 2490 | 40% | -0.097 | -0.123 |
| orb_break | struct | trail_t2 | 2490 | 39% | -0.098 | -0.162 |
| trend_pull | 1.5 | fixed_t1.5 | 3106 | 37% | -0.314 | -1.164 |
| trend_pull | 1.5 | fixed_t1 | 3106 | 45% | -0.316 | -1.019 |
| trend_pull | 1.5 | fixed_t2 | 3106 | 32% | -0.322 | -1.187 |
| trend_pull | 1.5 | be1r_t1.5 | 3106 | 32% | -0.324 | -1.021 |
| trend_pull | 1.5 | be1r_t2 | 3106 | 26% | -0.328 | -1.021 |
| trend_pull | 1.5 | trail_t2 | 3106 | 26% | -0.340 | -0.663 |

## STEP B -- pooled across variants, best scheme at each SL size

| SL | best scheme | n | win% | exp R | med R |
|---|---|---|---|---|---|
| 0.5 | fixed_t5 | 14032 | 15% | -0.450 | -0.858 |
| 0.75 | fixed_t5 | 14032 | 17% | -0.425 | -1.064 |
| 1.0 | fixed_t5 | 14032 | 20% | -0.391 | -1.209 |
| 1.5 | be1r_t5 | 14032 | 18% | -0.305 | -1.088 |
| struct | fixed_t1 | 14026 | 43% | -0.264 | -0.277 |

## STEP C -- filters on each variant's BEST base config (does any lift net expectancy?)

| variant | best cfg | filter | n | win% | exp R | dExp |
|---|---|---|---|---|---|---|
| bos_cont | struct/fixed_t1 | none | 727 | 42% | -0.018 | - |
| bos_cont | struct/fixed_t1 | regime(TREND) | 329 | 43% | -0.008 | +0.010 |
| bos_cont | struct/fixed_t1 | release(11-14:45) | 342 | 44% | +0.005 | +0.022 |
| bos_cont | struct/fixed_t1 | htf_align | 409 | 40% | -0.021 | -0.003 |
| bos_cont | struct/fixed_t1 | vol_expansion | 421 | 43% | +0.004 | +0.022 |
| disp_break | struct/trail | none | 6351 | 27% | -0.291 | - |
| disp_break | struct/trail | regime(TREND) | 3122 | 29% | -0.238 | +0.053 |
| disp_break | struct/trail | release(11-14:45) | 4658 | 28% | -0.252 | +0.039 |
| disp_break | struct/trail | htf_align | 4132 | 27% | -0.297 | -0.005 |
| disp_break | struct/trail | vol_expansion | 1851 | 31% | -0.182 | +0.109 |
| ign_retest | struct/fixed_t1 | none | 1352 | 45% | -0.293 | - |
| ign_retest | struct/fixed_t1 | regime(TREND) | 233 | 51% | -0.118 | +0.176 |
| ign_retest | struct/fixed_t1 | release(11-14:45) | 953 | 48% | -0.259 | +0.034 |
| ign_retest | struct/fixed_t1 | htf_align | 798 | 45% | -0.288 | +0.005 |
| ign_retest | struct/fixed_t1 | vol_expansion | 575 | 44% | -0.285 | +0.009 |
| orb_break | struct/fixed_t1 | none | 2490 | 44% | -0.090 | - |
| orb_break | struct/fixed_t1 | regime(TREND) | 1377 | 44% | -0.083 | +0.008 |
| orb_break | struct/fixed_t1 | release(11-14:45) | 889 | 44% | -0.089 | +0.001 |
| orb_break | struct/fixed_t1 | htf_align | 1440 | 41% | -0.105 | -0.015 |
| orb_break | struct/fixed_t1 | vol_expansion | 1315 | 45% | -0.056 | +0.034 |
| trend_pull | 1.5/fixed_t1.5 | none | 3106 | 37% | -0.314 | - |
| trend_pull | 1.5/fixed_t1.5 | regime(TREND) | 589 | 39% | -0.258 | +0.057 |
| trend_pull | 1.5/fixed_t1.5 | release(11-14:45) | 2240 | 38% | -0.298 | +0.016 |
| trend_pull | 1.5/fixed_t1.5 | htf_align | 3106 | 37% | -0.314 | +0.000 |
| trend_pull | 1.5/fixed_t1.5 | vol_expansion | 655 | 37% | -0.276 | +0.038 |

## STEP D -- holdout on each variant's best base config (positive on full + BOTH temporal halves + BOTH cross-sectional halves = survives)

| variant | best cfg | n | exp | t1st | t2nd | crc0 | crc1 | survives? |
|---|---|---|---|---|---|---|---|---|
| bos_cont | struct/fixed_t1 | 727 | -0.018 | -0.050 | -0.006 | -0.023 | -0.011 | no |
| disp_break | struct/trail | 6351 | -0.291 | -0.339 | -0.258 | -0.306 | -0.274 | no |
| ign_retest | struct/fixed_t1 | 1352 | -0.293 | -0.264 | -0.313 | -0.283 | -0.306 | no |
| orb_break | struct/fixed_t1 | 2490 | -0.090 | -0.052 | -0.116 | -0.103 | -0.075 | no |
| trend_pull | 1.5/fixed_t1.5 | 3106 | -0.314 | -0.235 | -0.370 | -0.304 | -0.327 | no |

### Best filtered config per variant (best single filter applied), with holdout

| variant | cfg + filter | n | exp | t1st | t2nd | crc0 | crc1 | surv |
|---|---|---|---|---|---|---|---|---|
| bos_cont | struct/fixed_t1+release(11-14:45) | 342 | +0.005 | -0.029 | +0.016 | -0.016 | +0.031 | no |
| disp_break | struct/trail+vol_expansion | 1851 | -0.182 | -0.358 | -0.071 | -0.209 | -0.149 | no |
| ign_retest | struct/fixed_t1+regime(TREND) | 233 | -0.118 | -0.226 | -0.045 | -0.184 | -0.042 | no |
| orb_break | struct/fixed_t1+vol_expansion | 1315 | -0.056 | -0.050 | -0.059 | -0.047 | -0.066 | no |
| trend_pull | 1.5/fixed_t1.5+regime(TREND) | 589 | -0.258 | -0.161 | -0.315 | -0.292 | -0.219 | no |

## VERDICT

**(1) MFE>>MAE asymmetry (the key result):**
- bos_cont: MFE/MAE = 1.19 (n=733) -> weakly asym
- disp_break: MFE/MAE = 1.05 (n=6351) -> SYMMETRIC (dead)
- trend_pull: MFE/MAE = 1.03 (n=3106) -> SYMMETRIC (dead)
- orb_break: MFE/MAE = 1.00 (n=2490) -> SYMMETRIC (dead)
- ign_retest: MFE/MAE = 0.97 (n=1352) -> SYMMETRIC (dead)

**(2) Net-positive after realistic fills + costs + holdout:** NONE
No momentum config is net-positive across the full sample and all four holdout splits.

