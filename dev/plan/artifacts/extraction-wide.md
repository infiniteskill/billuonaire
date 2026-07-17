# Realistic-fill extraction sweep -- NSE intraday (data/wide, 141 stocks + NIFTY, M1)

Signals captured (7 v2 detectors, --only-equivalent + non-colliding context detectors): **69151**. Fills replicate paper.py: entry = next-M1-open + half-spread; stop = level/gap-open + half-spread+slippage (never a clean stop fill); target = limit at level + half-spread; EOD = last close + half+slippage. Intrabar stop-before-target. Costs: Rs20x2 brokerage + 0.025% sell STT + 0.00297% exchange both legs. Sizing 1% of Rs10L = Rs10k risk (=1R), qty capped at 5x leverage. net_R = net_rupees/10,000.

## Per-detector signal counts

| detector | n | DOUBLE_TRAP | RANGE_PIN | TRAP_REVERSAL | TREND | UNCLASSIFIED |
|---|---|---|---|---|---|---|
| bpr | 741 | 34 | 434 | 31 | 4 | 238 |
| compression_fade | 32757 | 1634 | 17501 | 1004 | 106 | 12512 |
| fvg_cb | 7121 | 278 | 4349 | 166 | 19 | 2309 |
| inducement | 2559 | 120 | 1475 | 65 | 9 | 890 |
| mitigation | 8498 | 445 | 4403 | 272 | 28 | 3350 |
| ob_lux | 16396 | 915 | 8102 | 567 | 88 | 6724 |
| turtle_soup | 1079 | 64 | 493 | 54 | 5 | 463 |

## STEP 3.5 -- MFE/MAE reality per detector (ATR units, EOD path)

| detector | n | mean MFE | mean MAE | median MFE | median MAE | MFE/MAE |
|---|---|---|---|---|---|---|
| inducement | 2559 | 3.09 | 2.78 | 2.20 | 2.01 | 1.11 |
| compression_fade | 32757 | 2.95 | 2.89 | 2.12 | 2.00 | 1.02 |
| ob_lux | 16396 | 2.87 | 3.00 | 1.98 | 2.00 | 0.96 |
| bpr | 741 | 2.81 | 2.88 | 2.07 | 1.91 | 0.97 |
| mitigation | 8498 | 2.80 | 2.90 | 1.94 | 1.93 | 0.96 |
| turtle_soup | 1079 | 2.80 | 2.84 | 1.88 | 1.89 | 0.99 |
| fvg_cb | 7121 | 2.76 | 2.72 | 1.90 | 2.02 | 1.02 |

## STEP 2 -- realistic-fill grid, best 8 configs per detector (net expectancy R, n>=40)

| detector | k(ATR) | scheme | mgmt | target | n | win% | exp R | med R |
|---|---|---|---|---|---|---|---|---|
| bpr | 1.5 | fixed_t1.5 | fixed | 1.5R | 741 | 39% | -0.280 | -1.133 |
| bpr | 1.5 | fixed_t5 | fixed | 5.0R | 741 | 29% | -0.302 | -1.191 |
| bpr | 1.5 | fixed_t1 | fixed | 1.0R | 741 | 46% | -0.304 | -0.636 |
| bpr | 1.5 | be1r_t1.5 | be1r | 1.5R | 741 | 33% | -0.305 | -0.636 |
| bpr | 1.5 | be1r_t5 | be1r | 5.0R | 741 | 21% | -0.311 | -0.636 |
| bpr | 1.5 | fixed_t2 | fixed | 2.0R | 741 | 33% | -0.315 | -1.176 |
| bpr | 1.5 | fixed_t3 | fixed | 3.0R | 741 | 30% | -0.322 | -1.189 |
| bpr | 1.5 | be1r_t3 | be1r | 3.0R | 741 | 22% | -0.323 | -0.636 |
| compression_fade | 1.5 | fixed_t1 | fixed | 1.0R | 32757 | 45% | -0.304 | -0.889 |
| compression_fade | 1.5 | fixed_t1.5 | fixed | 1.5R | 32757 | 37% | -0.305 | -1.159 |
| compression_fade | 1.5 | fixed_t2 | fixed | 2.0R | 32757 | 33% | -0.307 | -1.178 |
| compression_fade | 1.5 | fixed_t5 | fixed | 5.0R | 32757 | 29% | -0.311 | -1.194 |
| compression_fade | 1.5 | fixed_t3 | fixed | 3.0R | 32757 | 30% | -0.312 | -1.190 |
| compression_fade | 1.5 | be1r_t1.5 | be1r | 1.5R | 32757 | 32% | -0.315 | -0.905 |
| compression_fade | 1.5 | be1r_t2 | be1r | 2.0R | 32757 | 26% | -0.319 | -0.909 |
| compression_fade | 1.5 | trail_t2 | trail | 2.0R | 32757 | 27% | -0.325 | -0.635 |
| fvg_cb | 1.5 | fixed_t1 | fixed | 1.0R | 7121 | 46% | -0.255 | -0.919 |
| fvg_cb | 1.5 | trail | trail | trail | 7121 | 29% | -0.262 | -0.563 |
| fvg_cb | 1.5 | be1r_t2 | be1r | 2.0R | 7121 | 27% | -0.263 | -0.931 |
| fvg_cb | 1.5 | trail_t5 | trail | 5.0R | 7121 | 29% | -0.263 | -0.563 |
| fvg_cb | 1.5 | trail_t2 | trail | 2.0R | 7121 | 29% | -0.265 | -0.563 |
| fvg_cb | 1.5 | trail_t3 | trail | 3.0R | 7121 | 29% | -0.265 | -0.563 |
| fvg_cb | 1.5 | fixed_t2 | fixed | 2.0R | 7121 | 34% | -0.265 | -1.147 |
| fvg_cb | 1.5 | be1r_t1.5 | be1r | 1.5R | 7121 | 32% | -0.268 | -0.931 |
| inducement | 1.5 | fixed_t5 | fixed | 5.0R | 2559 | 29% | -0.245 | -1.182 |
| inducement | 1.5 | fixed_t1.5 | fixed | 1.5R | 2559 | 39% | -0.264 | -1.150 |
| inducement | 1.5 | fixed_t1 | fixed | 1.0R | 2559 | 47% | -0.267 | -0.696 |
| inducement | 1.5 | be1r_t1.5 | be1r | 1.5R | 2559 | 33% | -0.276 | -0.697 |
| inducement | 1.5 | be1r_t5 | be1r | 5.0R | 2559 | 21% | -0.282 | -0.733 |
| inducement | 1.5 | fixed_t3 | fixed | 3.0R | 2559 | 30% | -0.287 | -1.180 |
| inducement | 1.5 | trail_t2 | trail | 2.0R | 2559 | 29% | -0.288 | -0.598 |
| inducement | 1.5 | fixed_t2 | fixed | 2.0R | 2559 | 34% | -0.293 | -1.169 |
| mitigation | 1.5 | fixed_t1 | fixed | 1.0R | 8498 | 45% | -0.323 | -0.805 |
| mitigation | 1.5 | fixed_t1.5 | fixed | 1.5R | 8498 | 36% | -0.335 | -1.175 |
| mitigation | 1.5 | be1r_t1.5 | be1r | 1.5R | 8498 | 31% | -0.345 | -0.831 |
| mitigation | 1.5 | fixed_t2 | fixed | 2.0R | 8498 | 32% | -0.348 | -1.196 |
| mitigation | 1.5 | fixed_t5 | fixed | 5.0R | 8498 | 28% | -0.351 | -1.211 |
| mitigation | 1.5 | be1r_t2 | be1r | 2.0R | 8498 | 25% | -0.363 | -0.843 |
| mitigation | 1.5 | fixed_t3 | fixed | 3.0R | 8498 | 29% | -0.366 | -1.208 |
| mitigation | 1.5 | trail_t2 | trail | 2.0R | 8498 | 25% | -0.369 | -0.655 |
| ob_lux | 1.5 | fixed_t1 | fixed | 1.0R | 16396 | 44% | -0.344 | -0.946 |
| ob_lux | 1.5 | fixed_t1.5 | fixed | 1.5R | 16396 | 35% | -0.369 | -1.185 |
| ob_lux | 1.5 | fixed_t3 | fixed | 3.0R | 16396 | 28% | -0.371 | -1.214 |
| ob_lux | 1.5 | fixed_t2 | fixed | 2.0R | 16396 | 31% | -0.371 | -1.204 |
| ob_lux | 1.5 | fixed_t5 | fixed | 5.0R | 16396 | 27% | -0.372 | -1.217 |
| ob_lux | 1.5 | be1r_t1.5 | be1r | 1.5R | 16396 | 30% | -0.373 | -0.948 |
| ob_lux | 1.5 | be1r_t2 | be1r | 2.0R | 16396 | 24% | -0.381 | -0.949 |
| ob_lux | 1.5 | trail_t2 | trail | 2.0R | 16396 | 24% | -0.385 | -0.677 |
| turtle_soup | 1.5 | fixed_t2 | fixed | 2.0R | 1079 | 33% | -0.336 | -1.189 |
| turtle_soup | 1.5 | fixed_t3 | fixed | 3.0R | 1079 | 29% | -0.337 | -1.207 |
| turtle_soup | 1.5 | fixed_t1.5 | fixed | 1.5R | 1079 | 37% | -0.341 | -1.168 |
| turtle_soup | 1.5 | fixed_t1 | fixed | 1.0R | 1079 | 43% | -0.346 | -0.664 |
| turtle_soup | 1.5 | be1r_t1.5 | be1r | 1.5R | 1079 | 32% | -0.351 | -0.701 |
| turtle_soup | 1.5 | fixed_t5 | fixed | 5.0R | 1079 | 28% | -0.351 | -1.209 |
| turtle_soup | 1.5 | be1r_t2 | be1r | 2.0R | 1079 | 27% | -0.351 | -0.701 |
| turtle_soup | 1.5 | be1r_t3 | be1r | 3.0R | 1079 | 22% | -0.375 | -0.701 |

## STEP 2 -- expectancy by SL-size k (pooled, BEST scheme at each k)

Tests the core thesis (a stop tighter than M1 noise gets shredded): wider stops strictly reduce the loss, but NONE cross zero.

| k (xATR) | best scheme | n | win% | exp R | med R |
|---|---|---|---|---|---|
| 0.25 | fixed_t1 | 69151 | 15% | -0.457 | -0.594 |
| 0.5 | fixed_t1 | 69151 | 39% | -0.444 | -0.738 |
| 0.75 | fixed_t1 | 69151 | 43% | -0.418 | -0.864 |
| 1.0 | fixed_t1 | 69151 | 44% | -0.393 | -0.979 |
| 1.5 | fixed_t1 | 69151 | 45% | -0.310 | -0.875 |

## STEP 2 -- pooled (ALL detectors), best 12 configs

| k(ATR) | scheme | n | win% | exp R | med R |
|---|---|---|---|---|---|
| 1.5 | fixed_t1 | 69151 | 45% | -0.310 | -0.875 |
| 1.5 | fixed_t1.5 | 69151 | 37% | -0.319 | -1.160 |
| 1.5 | fixed_t2 | 69151 | 33% | -0.323 | -1.179 |
| 1.5 | fixed_t5 | 69151 | 28% | -0.324 | -1.194 |
| 1.5 | be1r_t1.5 | 69151 | 31% | -0.327 | -0.891 |
| 1.5 | fixed_t3 | 69151 | 29% | -0.328 | -1.191 |
| 1.5 | be1r_t2 | 69151 | 26% | -0.333 | -0.895 |
| 1.5 | trail_t2 | 69151 | 26% | -0.338 | -0.640 |
| 1.5 | trail | 69151 | 26% | -0.339 | -0.640 |
| 1.5 | trail_t5 | 69151 | 26% | -0.341 | -0.640 |
| 1.5 | be1r_t5 | 69151 | 20% | -0.341 | -0.898 |
| 1.5 | trail_t3 | 69151 | 26% | -0.342 | -0.640 |

## STEP 3 -- filters on each detector's BEST base config

| detector | best cfg (k/scheme) | filter | n | win% | exp R |
|---|---|---|---|---|---|
| bpr | 1.5/fixed_t1.5 | none | 741 | 39% | -0.280 |
| bpr | 1.5/fixed_t1.5 | regime(TREND/TRAP) | 69 | 51% | -0.033 |
| bpr | 1.5/fixed_t1.5 | release(11-14:45) | 573 | 40% | -0.295 |
| bpr | 1.5/fixed_t1.5 | wyck_align | 289 | 36% | -0.361 |
| bpr | 1.5/fixed_t1.5 | htf_align | 265 | 40% | -0.228 |
| bpr | 1.5/fixed_t1.5 | pd_favorable | 472 | 38% | -0.299 |
| bpr | 1.5/fixed_t1.5 | vol_expansion | 277 | 41% | -0.168 |
| bpr | 1.5/fixed_t1.5 | vol_contraction | 464 | 37% | -0.346 |
| compression_fade | 1.5/fixed_t1 | none | 32757 | 45% | -0.304 |
| compression_fade | 1.5/fixed_t1 | regime(TREND/TRAP) | 2744 | 44% | -0.329 |
| compression_fade | 1.5/fixed_t1 | release(11-14:45) | 21550 | 46% | -0.322 |
| compression_fade | 1.5/fixed_t1 | wyck_align | 13788 | 46% | -0.287 |
| compression_fade | 1.5/fixed_t1 | htf_align | 11745 | 44% | -0.326 |
| compression_fade | 1.5/fixed_t1 | pd_favorable | 18475 | 46% | -0.295 |
| compression_fade | 1.5/fixed_t1 | vol_expansion | 12966 | 45% | -0.263 |
| compression_fade | 1.5/fixed_t1 | vol_contraction | 19664 | 46% | -0.330 |
| fvg_cb | 1.5/fixed_t1 | none | 7121 | 46% | -0.255 |
| fvg_cb | 1.5/fixed_t1 | regime(TREND/TRAP) | 463 | 42% | -0.371 |
| fvg_cb | 1.5/fixed_t1 | release(11-14:45) | 3188 | 46% | -0.294 |
| fvg_cb | 1.5/fixed_t1 | wyck_align | 3716 | 45% | -0.276 |
| fvg_cb | 1.5/fixed_t1 | htf_align | 4867 | 46% | -0.259 |
| fvg_cb | 1.5/fixed_t1 | pd_favorable | 2650 | 44% | -0.288 |
| fvg_cb | 1.5/fixed_t1 | vol_expansion | 4743 | 46% | -0.235 |
| fvg_cb | 1.5/fixed_t1 | vol_contraction | 2359 | 46% | -0.294 |
| inducement | 1.5/fixed_t5 | none | 2559 | 29% | -0.245 |
| inducement | 1.5/fixed_t5 | regime(TREND/TRAP) | 194 | 30% | -0.187 |
| inducement | 1.5/fixed_t5 | release(11-14:45) | 1364 | 28% | -0.299 |
| inducement | 1.5/fixed_t5 | wyck_align | 1361 | 31% | -0.230 |
| inducement | 1.5/fixed_t5 | htf_align | 1565 | 30% | -0.214 |
| inducement | 1.5/fixed_t5 | pd_favorable | 1019 | 29% | -0.152 |
| inducement | 1.5/fixed_t5 | vol_expansion | 1220 | 30% | -0.290 |
| inducement | 1.5/fixed_t5 | vol_contraction | 1318 | 29% | -0.224 |
| mitigation | 1.5/fixed_t1 | none | 8498 | 45% | -0.323 |
| mitigation | 1.5/fixed_t1 | regime(TREND/TRAP) | 745 | 44% | -0.326 |
| mitigation | 1.5/fixed_t1 | release(11-14:45) | 6103 | 45% | -0.344 |
| mitigation | 1.5/fixed_t1 | wyck_align | 3558 | 45% | -0.309 |
| mitigation | 1.5/fixed_t1 | htf_align | 3312 | 45% | -0.317 |
| mitigation | 1.5/fixed_t1 | pd_favorable | 4553 | 44% | -0.341 |
| mitigation | 1.5/fixed_t1 | vol_expansion | 3585 | 44% | -0.297 |
| mitigation | 1.5/fixed_t1 | vol_contraction | 4905 | 45% | -0.343 |
| ob_lux | 1.5/fixed_t1 | none | 16396 | 44% | -0.344 |
| ob_lux | 1.5/fixed_t1 | regime(TREND/TRAP) | 1570 | 46% | -0.265 |
| ob_lux | 1.5/fixed_t1 | release(11-14:45) | 12959 | 45% | -0.353 |
| ob_lux | 1.5/fixed_t1 | wyck_align | 6502 | 46% | -0.300 |
| ob_lux | 1.5/fixed_t1 | htf_align | 3328 | 45% | -0.313 |
| ob_lux | 1.5/fixed_t1 | pd_favorable | 10405 | 43% | -0.352 |
| ob_lux | 1.5/fixed_t1 | vol_expansion | 5184 | 44% | -0.300 |
| ob_lux | 1.5/fixed_t1 | vol_contraction | 11166 | 44% | -0.363 |
| turtle_soup | 1.5/fixed_t2 | none | 1079 | 33% | -0.336 |
| turtle_soup | 1.5/fixed_t2 | regime(TREND/TRAP) | 123 | 31% | -0.369 |
| turtle_soup | 1.5/fixed_t2 | release(11-14:45) | 834 | 33% | -0.338 |
| turtle_soup | 1.5/fixed_t2 | wyck_align | 423 | 33% | -0.314 |
| turtle_soup | 1.5/fixed_t2 | htf_align | 216 | 31% | -0.372 |
| turtle_soup | 1.5/fixed_t2 | pd_favorable | 592 | 30% | -0.400 |
| turtle_soup | 1.5/fixed_t2 | vol_expansion | 465 | 33% | -0.303 |
| turtle_soup | 1.5/fixed_t2 | vol_contraction | 614 | 32% | -0.362 |

## STEP 3 -- compounding helpful filters (stacked)

| detector | k/scheme | stacked filters | n | win% | exp R |
|---|---|---|---|---|---|
| inducement | 1.5/fixed_t5 | regime(TREND/TRAP)+wyck_align+htf_align+pd_favorable+vol_contraction | 5 | 40% | +0.148 |
| fvg_cb | 1.5/fixed_t1 | vol_expansion | 4743 | 46% | -0.235 |
| bpr | 1.5/fixed_t1.5 | regime(TREND/TRAP)+htf_align+vol_expansion | 8 | 50% | -0.117 |
| compression_fade | 1.5/fixed_t1 | wyck_align+pd_favorable+vol_expansion | 2709 | 47% | -0.220 |
| mitigation | 1.5/fixed_t1 | wyck_align+htf_align+vol_expansion | 739 | 46% | -0.234 |
| turtle_soup | 1.5/fixed_t2 | wyck_align+vol_expansion | 185 | 30% | -0.316 |
| ob_lux | 1.5/fixed_t1 | regime(TREND/TRAP)+wyck_align+htf_align+vol_expansion | 35 | 46% | -0.273 |

## STEP 4 -- holdout (net exp R on each split; all_pos = positive on full + both temporal halves + both cross halves)

Configs (n>=40) that are net-positive on the full sample AND all four holdout splits:

**NONE.** No base config survives all four holdout splits positive.


### Top-15 base configs by full-sample expectancy (with holdout)

| detector | k | scheme | n | exp | t1st | t2nd | crc0 | crc1 | all_pos |
|---|---|---|---|---|---|---|---|---|---|
| inducement | 1.5 | fixed_t5 | 2559 | -0.245 | -0.154 | -0.298 | -0.220 | -0.272 | no |
| fvg_cb | 1.5 | fixed_t1 | 7121 | -0.255 | -0.235 | -0.269 | -0.258 | -0.252 | no |
| fvg_cb | 1.5 | trail | 7121 | -0.262 | -0.228 | -0.283 | -0.241 | -0.284 | no |
| fvg_cb | 1.5 | be1r_t2 | 7121 | -0.263 | -0.223 | -0.288 | -0.262 | -0.264 | no |
| fvg_cb | 1.5 | trail_t5 | 7121 | -0.263 | -0.229 | -0.285 | -0.244 | -0.284 | no |
| inducement | 1.5 | fixed_t1.5 | 2559 | -0.264 | -0.178 | -0.315 | -0.260 | -0.269 | no |
| fvg_cb | 1.5 | trail_t2 | 7121 | -0.265 | -0.246 | -0.277 | -0.250 | -0.281 | no |
| fvg_cb | 1.5 | trail_t3 | 7121 | -0.265 | -0.234 | -0.285 | -0.247 | -0.285 | no |
| fvg_cb | 1.5 | fixed_t2 | 7121 | -0.265 | -0.224 | -0.292 | -0.265 | -0.265 | no |
| inducement | 1.5 | fixed_t1 | 2559 | -0.267 | -0.212 | -0.299 | -0.260 | -0.274 | no |
| fvg_cb | 1.5 | be1r_t1.5 | 7121 | -0.268 | -0.234 | -0.290 | -0.275 | -0.260 | no |
| fvg_cb | 1.5 | fixed_t5 | 7121 | -0.269 | -0.200 | -0.313 | -0.262 | -0.276 | no |
| fvg_cb | 1.5 | fixed_t1.5 | 7121 | -0.271 | -0.245 | -0.288 | -0.277 | -0.265 | no |
| fvg_cb | 1.5 | be1r_t5 | 7121 | -0.272 | -0.207 | -0.313 | -0.257 | -0.288 | no |
| inducement | 1.5 | be1r_t1.5 | 2559 | -0.276 | -0.211 | -0.314 | -0.271 | -0.281 | no |
