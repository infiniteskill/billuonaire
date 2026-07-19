# Combination / Permutation analysis -- NSE intraday v2 system

Source: `signals_rich.parquet` -- 25138 causal signals, 46 stocks (LTIM/TATAMOTORS have empty CSVs), 19 sessions (2026-06-19...2026-07-16). Temporal holdout cut = 2026-07-03. Cross-sectional = crc32(symbol)%2. Detectors measured in ISOLATION (only the 7 targets enabled: no orderblock/fvg contamination of ob_lux/fvg_cb).

See module docstring of analysis.py for the expectancy model & holdout rule.

## Bottom line

1. **Best exit-target / detector** (SL=1R): ob_lux=1R; fvg_cb=1R; compression_fade=2R; inducement=1R; bpr=5R; mitigation=1R; turtle_soup=1R. The two RR-profitable detectors are **compression_fade** (best 2R, exp +0.30) and **bpr** (best 5R +0.41 but n=222; robust 1.5R +0.31). ob_lux is thinly positive (1R +0.08); inducement/mitigation only ~breakeven at a quick 1R exit; **fvg_cb and turtle_soup are RR-negative at every target** (hit-edge != RR).
2. **Highest-value filters**: the **release window (~11:00-14:45)** is the single most broadly useful lever (compression_fade +0.14, mitigation +0.25, inducement +0.25, ob_lux +0.09 -- all holdout-stable), then **premium/discount** (compression_fade +0.12, ob_lux/mitigation ~+0.04). **Wyckoff-phase alignment is detector-specific, NOT universal**: aligned helps ob_lux (+0.10) but compression_fade fades better COUNTER-phase. Volatility matters in OPPOSITE directions -- compression_fade prefers contraction (+0.09), bpr prefers expansion (+0.18). Freshness is near-worthless (obvious ~ fresh).
3. **Do filters compound?** Modestly, then saturate. compression_fade pd_fav->+pd_fav+vol_con->+release climbs +0.30->+0.39->+0.41 (real but diminishing, and n falls 12278->4028->3348). Beyond 2 filters it is noise on all but compression_fade.
4. **Single best end-to-end config**: **compression_fade @2R, premium/discount-favorable + volatility-contraction** -- exp +0.39, robust +0.39, n=4028, win 46%, dead-stable across BOTH holdouts (T1+0.39/T2+0.40/C0+0.40/C1+0.39). Adding the release window nudges exp to +0.41.
5. **Surprises**: (a) **bpr has NEGATIVE hit-edge (-0.03) yet the best RR of all** -- pure asymmetry, the sharpest hit!=RR case. (b) **Detector stacking still does not pay**: of 42 co-fire pairs, exactly ONE beats both solos (mitigation confirmed by ob_lux, +0.12@1R) and it is still far below compression_fade solo; every holdout-stable compression_fade co-fire DILUTES it. (c) Wyckoff phase is a fade-vs-follow switch, not a universal + lever.

> Repro note: this harness reproduces the reference `rr50.py` EXACTLY on the 5 shared emitters (bpr n=222 exp@3R +0.33, compression_fade n=12278 exp@2R +0.30, ...). The older `rr50-results.md` (bpr n=495) was a STALE snapshot; a fresh `rr50.py` run on current code/data matches this file.

## A. Per-detector SOLO -- hit-edge + expectancy by exit-target

exp@R uses SL=1R, win=P(maxR>=R). **best** = exit-target with max full-sample exp. `hold?` = best target positive on full + both temporal halves + both crc groups.

| detector | n | hit% | base% | hit-edge | exp@1R | exp@1.5R | exp@2R | exp@3R | exp@5R | best | best_exp | robust | hold? |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ob_lux | 5630 | 47% | 39% | +0.08 | +0.08 | +0.06 | +0.04 | -0.05 | -0.31 | 1R | +0.08 | +0.06 | YES |
| fvg_cb | 2535 | 46% | 40% | +0.06 | -0.14 | -0.21 | -0.27 | -0.43 | -0.62 | 1R | -0.14 | -0.16 | no |
| compression_fade | 12278 | 48% | 39% | +0.09 | +0.25 | +0.29 | +0.30 | +0.26 | +0.08 | 2R | +0.30 | +0.30 | YES |
| inducement | 947 | 44% | 32% | +0.12 | +0.07 | +0.04 | -0.01 | -0.13 | -0.36 | 1R | +0.07 | +0.01 | YES |
| bpr | 222 | 46% | 50% | -0.03 | +0.27 | +0.31 | +0.38 | +0.33 | +0.41 | 5R | +0.41 | +0.14 | YES |
| mitigation | 3110 | 46% | 38% | +0.09 | +0.04 | -0.02 | -0.07 | -0.13 | -0.31 | 1R | +0.04 | +0.02 | YES |
| turtle_soup | 416 | 41% | 32% | +0.09 | -0.21 | -0.22 | -0.30 | -0.35 | -0.45 | 1R | -0.21 | -0.25 | no |

## B. detector x SINGLE filter -- lift at each detector's best exit-target

`good` / `bad` = the two sides of the filter (killzone: release vs its complement). d(exp) = good-bad; d(hitedge) = good-bad. `hold?` = good side holdout-stable.

| detector | @R | filter | n_good | exp_good | n_bad | exp_bad | d(exp) | d(hitedge) | hold_good? |
|---|---|---|---|---|---|---|---|---|---|
| ob_lux | 1R | wyck (aligned vs counter) | 2185 | +0.14 | 2640 | +0.04 | +0.10 | +0.03 | YES |
| ob_lux | 1R | premium/discount (fav vs unfav) | 3706 | +0.09 | 1924 | +0.06 | +0.04 | +0.00 | YES |
| ob_lux | 1R | M15 htf (align vs counter) | 1128 | +0.08 | 2270 | +0.08 | -0.00 | -0.01 | YES |
| ob_lux | 1R | vol (expansion vs contraction) | 1866 | +0.10 | 3746 | +0.07 | +0.02 | -0.01 | YES |
| ob_lux | 1R | freshness (fresh vs obvious) | 598 | -0.10 | 5032 | +0.10 | -0.20 | +0.03 | no |
| ob_lux | 1R | killzone (release vs outside) | 4372 | +0.10 | 1258 | +0.01 | +0.09 | -0.01 | YES |
| fvg_cb | 1R | wyck (aligned vs counter) | 1292 | -0.20 | 915 | -0.07 | -0.13 | -0.01 | no |
| fvg_cb | 1R | premium/discount (fav vs unfav) | 946 | -0.16 | 1589 | -0.12 | -0.04 | +0.08 | no |
| fvg_cb | 1R | M15 htf (align vs counter) | 1739 | -0.16 | 451 | -0.11 | -0.05 | -0.04 | no |
| fvg_cb | 1R | vol (expansion vs contraction) | 1729 | -0.17 | 804 | -0.08 | -0.09 | -0.05 | no |
| fvg_cb | 1R | freshness (fresh vs obvious) | 729 | -0.26 | 1806 | -0.09 | -0.17 | +0.10 | no |
| fvg_cb | 1R | killzone (release vs outside) | 1177 | -0.08 | 1358 | -0.19 | +0.11 | +0.05 | no |
| compression_fade | 2R | wyck (aligned vs counter) | 5039 | +0.29 | 5609 | +0.32 | -0.02 | -0.00 | YES |
| compression_fade | 2R | premium/discount (fav vs unfav) | 6909 | +0.35 | 5369 | +0.23 | +0.12 | +0.03 | YES |
| compression_fade | 2R | M15 htf (align vs counter) | 4427 | +0.27 | 4739 | +0.33 | -0.06 | -0.03 | YES |
| compression_fade | 2R | vol (expansion vs contraction) | 4912 | +0.25 | 7318 | +0.34 | -0.09 | +0.00 | YES |
| compression_fade | 2R | freshness (fresh vs obvious) | 2296 | +0.33 | 9982 | +0.29 | +0.04 | +0.05 | YES |
| compression_fade | 2R | killzone (release vs outside) | 8255 | +0.35 | 4023 | +0.21 | +0.14 | +0.02 | YES |
| inducement | 1R | wyck (aligned vs counter) | 521 | +0.09 | 316 | +0.02 | +0.08 | +0.03 | no |
| inducement | 1R | premium/discount (fav vs unfav) | 385 | -0.05 | 562 | +0.15 | -0.21 | -0.03 | no |
| inducement | 1R | M15 htf (align vs counter) | 609 | +0.08 | 113 | -0.03 | +0.11 | -0.03 | YES |
| inducement | 1R | vol (expansion vs contraction) | 460 | -0.01 | 481 | +0.15 | -0.16 | -0.08 | no |
| inducement | 1R | freshness (fresh vs obvious) | 172 | -0.09 | 775 | +0.10 | -0.20 | -0.01 | no |
| inducement | 1R | killzone (release vs outside) | 538 | +0.17 | 409 | -0.07 | +0.25 | +0.01 | YES |
| bpr | 5R | wyck (aligned vs counter) | 91 | +0.45 | 92 | +0.57 | -0.11 | +0.07 | no |
| bpr | 5R | premium/discount (fav vs unfav) | 145 | +0.41 | 77 | +0.40 | +0.00 | +0.07 | no |
| bpr | 5R | M15 htf (align vs counter) | 89 | +0.42 | 82 | +0.32 | +0.10 | -0.02 | no |
| bpr | 5R | vol (expansion vs contraction) | 87 | +0.52 | 135 | +0.33 | +0.18 | -0.04 | no |
| bpr | 5R | freshness (fresh vs obvious) | 0 | - | 222 | +0.41 | - | - | no |
| bpr | 5R | killzone (release vs outside) | 176 | +0.40 | 46 | +0.43 | -0.04 | +0.03 | YES |
| mitigation | 1R | wyck (aligned vs counter) | 1276 | +0.04 | 1392 | +0.04 | -0.00 | -0.00 | YES |
| mitigation | 1R | premium/discount (fav vs unfav) | 1674 | +0.06 | 1436 | +0.01 | +0.05 | +0.01 | YES |
| mitigation | 1R | M15 htf (align vs counter) | 1210 | +0.05 | 952 | +0.06 | -0.01 | -0.03 | YES |
| mitigation | 1R | vol (expansion vs contraction) | 1408 | -0.01 | 1700 | +0.07 | -0.08 | -0.04 | no |
| mitigation | 1R | freshness (fresh vs obvious) | 263 | +0.08 | 2847 | +0.03 | +0.05 | -0.00 | YES |
| mitigation | 1R | killzone (release vs outside) | 2209 | +0.11 | 901 | -0.14 | +0.25 | +0.04 | YES |
| turtle_soup | 1R | wyck (aligned vs counter) | 157 | -0.16 | 199 | -0.23 | +0.07 | +0.01 | no |
| turtle_soup | 1R | premium/discount (fav vs unfav) | 236 | -0.19 | 180 | -0.23 | +0.05 | +0.04 | no |
| turtle_soup | 1R | M15 htf (align vs counter) | 79 | -0.29 | 62 | +0.00 | -0.29 | -0.04 | no |
| turtle_soup | 1R | vol (expansion vs contraction) | 194 | -0.33 | 222 | -0.10 | -0.23 | -0.08 | no |
| turtle_soup | 1R | freshness (fresh vs obvious) | 85 | -0.18 | 331 | -0.21 | +0.04 | +0.07 | no |
| turtle_soup | 1R | killzone (release vs outside) | 282 | -0.10 | 134 | -0.43 | +0.33 | +0.06 | no |

## C. detector x filter PAIRS & TRIPLES -- do filters compound?

For each detector at its best exit-target: solo exp, best single-filter exp, best holdout-stable PAIR, best holdout-stable TRIPLE (n>=40, all 4 holdout cells>0). Shows whether adding filters lifts exp or just shrinks n.

| detector | @R | solo_exp (n) | best_single (n) | best_pair (n) | best_triple (n) | compounds? |
|---|---|---|---|---|---|---|
| ob_lux | 1R | +0.08 (5630) | +0.14 (2185) [wyck_aligned] | +0.16 (2010) [wyck_aligned+obvious] | +0.19 (1566) [wyck_aligned+obvious+release] | saturates |
| fvg_cb | 1R | -0.14 (2535) | -  | -  | +0.05 (445) [wyck_counter+pd_unf+obvious] | n/a |
| compression_fade | 2R | +0.30 (12278) | +0.34 (7318) [vol_con] | +0.39 (4028) [pd_fav+vol_con] | +0.41 (3348) [pd_fav+vol_con+release] | yes |
| inducement | 1R | +0.07 (947) | +0.17 (538) [release] | +0.23 (382) [pd_unf+release] | +0.25 (257) [pd_unf+htf_align+release] | yes |
| bpr | 5R | +0.41 (222) | -  | -  | -  | n/a |
| mitigation | 1R | +0.04 (3110) | +0.11 (2209) [release] | +0.17 (204) [fresh+release] | +0.19 (193) [pd_fav+fresh+release] | yes |
| turtle_soup | 1R | -0.21 (416) | -  | -  | -  | n/a |

## D. detector-PAIR co-fire -- does confluence beat BOTH solos?

co-fire = an A-signal with a B-signal within <=3 M5 bars (<=15min), SAME direction, zone midpoints within 0.5*ATR. All measured at A's best target R. `beats_both?`=YES only if co-fired robust-holdout exp > BOTH solo_A and solo_B (both at R) -- the honest confluence test. Pairs with >=40 co-fire events, sorted by d(vs best solo).

| A (base) | B (confirm) | @R | n_cofire | solo_A | solo_B | exp_cofire | robust | hold? | beats_both? |
|---|---|---|---|---|---|---|---|---|---|
| inducement | mitigation | 1R | 59 | +0.07 | +0.04 | +0.12 | +0.03 | no | no |
| compression_fade | turtle_soup | 2R | 127 | +0.30 | -0.30 | +0.35 | +0.18 | no | no |
| inducement | ob_lux | 1R | 80 | +0.07 | +0.08 | +0.12 | +0.03 | no | no |
| mitigation | ob_lux | 1R | 557 | +0.04 | +0.08 | +0.12 | +0.11 | yes | **YES** |
| compression_fade | mitigation | 2R | 1121 | +0.30 | -0.07 | +0.29 | +0.29 | yes | no |
| ob_lux | mitigation | 1R | 1350 | +0.08 | +0.04 | +0.06 | +0.02 | yes | no |
| compression_fade | ob_lux | 2R | 670 | +0.30 | +0.04 | +0.27 | +0.18 | yes | no |
| compression_fade | fvg_cb | 2R | 403 | +0.30 | -0.27 | +0.24 | +0.19 | yes | no |
| mitigation | inducement | 1R | 62 | +0.04 | +0.07 | +0.00 | -0.07 | no | no |
| inducement | compression_fade | 1R | 303 | +0.07 | +0.25 | +0.17 | +0.15 | yes | no |
| bpr | compression_fade | 5R | 77 | +0.41 | +0.08 | +0.32 | +0.03 | no | no |
| ob_lux | inducement | 1R | 206 | +0.08 | +0.07 | -0.04 | -0.17 | no | no |
| ob_lux | turtle_soup | 1R | 44 | +0.08 | -0.21 | -0.05 | -0.40 | no | no |
| compression_fade | inducement | 2R | 394 | +0.30 | -0.01 | +0.11 | +0.08 | yes | no |
| ob_lux | compression_fade | 1R | 1879 | +0.08 | +0.25 | +0.02 | -0.03 | no | no |
| mitigation | compression_fade | 1R | 913 | +0.04 | +0.25 | -0.02 | -0.03 | no | no |
| compression_fade | bpr | 2R | 102 | +0.30 | +0.38 | +0.03 | -0.22 | no | no |
| fvg_cb | compression_fade | 1R | 589 | -0.14 | +0.25 | -0.24 | -0.32 | no | no |
| turtle_soup | compression_fade | 1R | 109 | -0.21 | +0.25 | -0.27 | -0.30 | no | no |

## E. GLOBAL best end-to-end configs (ranked by robust holdout exp)

Only positive + holdout-stable (full & both temporal halves & both crc groups). robust = worst of the 4 holdout-cell exps. filters = stacked causal conditions.

| # | detector | @R | filters | n | win% | exp | robust | T1 | T2 | C0 | C1 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | compression_fade | 3R | wyck_counter+pd_fav+vol_con | 2136 | 35% | +0.41 | +0.41 | +0.42 | +0.41 | +0.41 | +0.41 |
| 2 | compression_fade | 2R | pd_fav+vol_con | 4028 | 46% | +0.39 | +0.39 | +0.39 | +0.40 | +0.40 | +0.39 |
| 3 | compression_fade | 2R | pd_fav+vol_con+release | 3348 | 47% | +0.41 | +0.37 | +0.42 | +0.40 | +0.43 | +0.37 |
| 4 | bpr | 1.5R | release | 176 | 55% | +0.36 | +0.34 | +0.34 | +0.38 | +0.38 | +0.35 |
| 5 | bpr | 1.5R | (none) | 222 | 52% | +0.31 | +0.29 | +0.29 | +0.32 | +0.31 | +0.30 |
| 6 | ob_lux | 1R | wyck_aligned+obvious+release | 1566 | 60% | +0.19 | +0.17 | +0.22 | +0.17 | +0.21 | +0.17 |
| 7 | mitigation | 1R | pd_fav+fresh+release | 193 | 60% | +0.19 | +0.16 | +0.16 | +0.22 | +0.20 | +0.19 |
| 8 | inducement | 1R | pd_unf+htf_align+release | 257 | 63% | +0.25 | +0.16 | +0.38 | +0.16 | +0.20 | +0.31 |
| 9 | ob_lux | 1R | wyck_aligned+htf_counter+vol_exp | 209 | 62% | +0.24 | +0.15 | +0.15 | +0.31 | +0.16 | +0.33 |
| 10 | inducement | 1.5R | htf_align+vol_con+release | 230 | 53% | +0.32 | +0.15 | +0.55 | +0.15 | +0.36 | +0.26 |
| 11 | ob_lux | 1R | wyck_aligned+vol_exp+release | 425 | 61% | +0.21 | +0.14 | +0.21 | +0.21 | +0.14 | +0.29 |
| 12 | inducement | 1R | pd_unf+release | 382 | 61% | +0.23 | +0.14 | +0.33 | +0.14 | +0.18 | +0.27 |

## Kill-zone detail -- exp@best-target by 30-min bucket

bucket 0=09:15, 3=10:45, 6=12:15, 10=14:15. Cells: exp (n).

| detector | b0 | b1 | b2 | b3 | b4 | b5 | b6 | b7 | b8 | b9 | b10 | b11 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ob_lux @1R | . (0) | +0.30 (23) | +0.18 (154) | +0.25 (334) | +0.18 (479) | +0.09 (534) | +0.08 (570) | +0.09 (586) | +0.11 (619) | +0.06 (639) | +0.03 (611) | +0.09 (676) |
| fvg_cb @1R | -0.20 (498) | -0.05 (345) | +0.03 (231) | -0.08 (184) | -0.16 (177) | -0.09 (173) | +0.00 (140) | +0.05 (145) | -0.13 (133) | -0.11 (106) | -0.08 (119) | -0.40 (94) |
| compression_fade @2R | +0.18 (440) | +0.20 (879) | +0.31 (918) | +0.30 (942) | +0.41 (993) | +0.35 (975) | +0.32 (993) | +0.31 (1047) | +0.41 (1055) | +0.28 (1049) | +0.37 (1201) | +0.32 (1068) |
| inducement @1R | -0.15 (113) | +0.03 (78) | +0.04 (102) | +0.13 (97) | +0.27 (80) | -0.10 (58) | +0.36 (72) | +0.10 (49) | +0.25 (56) | -0.01 (75) | +0.41 (51) | +0.08 (65) |
| bpr @5R | . (1) | . (2) | . (11) | +0.06 (17) | . (14) | +0.11 (27) | +0.91 (22) | +0.06 (17) | +0.71 (28) | +0.57 (23) | +0.50 (28) | . (10) |
| mitigation @1R | . (0) | -0.03 (107) | +0.07 (135) | +0.15 (207) | +0.03 (243) | +0.18 (283) | +0.15 (291) | +0.08 (276) | +0.15 (301) | -0.00 (317) | +0.14 (291) | +0.03 (389) |
| turtle_soup @1R | . (0) | . (0) | . (0) | +0.07 (15) | -0.06 (36) | -0.33 (36) | -0.14 (37) | +0.41 (37) | -0.43 (28) | -0.17 (36) | -0.12 (57) | -0.25 (72) |
