# HUNT -- stop-hunt economics: is the stop the product?

Signals: 14764 focus-tool signals, top-10 liquidity symbols, 57 sessions (2026-04-27 .. 2026-07-17). Sources: orchestrator capture (RELIANCE+INFY) + direct detector drive (other 8). Parity on the 2 shared symbols (capture_n/direct_n/common): {'RELIANCE': (1321, 1321, 1321), 'INFY': (1462, 1462, 1462)} -- exact.

Caveat: trades overlap heavily (~26 signals/symbol-session); these are event-study expectancies per signal, not a portfolio equity curve.

## Normalization (honest units)
Every mode risks a nominal Rs10,000 per trade: qty = floor(min(10000/size_dist, 50L/entry_fill)); size_dist = the mode's defined worst-case price move (A 0.5xATR, B 1.5xATR, C/D/F 3.0xATR assumption, E signal-close -> shadow-stop distance). net_R = net_rupees / (qty x size_dist), i.e. P&L per Rs10k of that mode's own worst case. Fills/costs = step2_engine (entry next-5m-open +half-spread; stop market w/ gap-through +5bp; target limit +2bp; EOD market; Rs20x2 brokerage, 0.025% sell STT, 0.00297% exchange both legs). C/D/F have NO hard floor: realized adverse beyond 3xATR is real risk -- see tail table. mean_risk column shows where the 5x-leverage notional cap compresses the budget (tight stops on low-ATR names).

## Pooled mode table
| mode | n | win_pct | mean_R | med_R | p10_R | p90_R | se_R | stop_pct | tgt_pct | cost_R | mean_risk | gross_R |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 14764 | 10.045 | -1.070 | -1.839 | -2.303 | 0.043 | 0.026 | 88.614 | 0.000 | 0.353 | 5052.310 | -0.717 |
| B | 14764 | 27.804 | -0.349 | -1.222 | -1.414 | 1.905 | 0.014 | 63.811 | 0.000 | 0.119 | 9793.773 | -0.230 |
| C | 14764 | 42.800 | -0.187 | -0.168 | -1.659 | 1.261 | 0.012 | 0.000 | 0.000 | 0.061 | 9994.727 | -0.126 |
| D | 14764 | 62.246 | -0.179 | 0.369 | -1.414 | 0.433 | 0.008 | 0.000 | 59.564 | 0.061 | 9994.727 | -0.117 |
| E | 14764 | 26.334 | -0.554 | -1.257 | -2.339 | 1.521 | 0.022 | 61.149 | 0.000 | 0.198 | 8093.437 | -0.356 |
| F | 14764 | 20.462 | -0.182 | -0.328 | -0.829 | 0.785 | 0.007 | 72.487 | 0.000 | 0.061 | 9994.727 | -0.121 |
| At | 14764 | 19.609 | -1.062 | -1.792 | -2.279 | 2.444 | 0.014 | 79.558 | 19.101 | 0.353 | 5052.310 | -0.708 |
| Bt | 14764 | 44.656 | -0.331 | -1.115 | -1.394 | 0.860 | 0.008 | 50.501 | 43.091 | 0.119 | 9793.773 | -0.212 |

Modes: A tight 0.5xATR stop | B wide 1.5xATR | C no stop, EOD | D no stop + 1.5xATR target | E shadow stop beyond recent 12-bar swept extreme +0.25xATR | F 0.5xATR stop armed after 6 bars (chosen on T1 among [3, 6, 12, 18]: N=3:-0.171R(n=7096), N=6:-0.171R(n=7096), N=12:-0.178R(n=7096), N=18:-0.185R(n=7096)) | At/Bt anchors = 0.5x/1.5xATR stop PLUS the same 1.5xATR target as D (isolates the stop's marginal cost under an identical target policy). cost_R = mean total friction (brokerage+STT+exchange, spread excluded -- it is in the fills) per risk unit; gross_R = mean_R + cost_R. Note A/At carry ~2x cost_R: the capped notional (mean_risk ~5k) makes the flat Rs40 + STT loom larger per risk unit -- a real NSE effect, not an artifact.

## Per-tool mode tables
### bpr
| mode | n | win_pct | mean_R | med_R | p10_R | p90_R | se_R | stop_pct | tgt_pct | cost_R | mean_risk | gross_R |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 924 | 8.874 | -1.069 | -1.792 | -2.248 | -1.253 | 0.102 | 90.043 | 0.000 | 0.333 | 5402.467 | -0.737 |
| B | 924 | 27.814 | -0.264 | -1.204 | -1.397 | 2.169 | 0.062 | 63.853 | 0.000 | 0.112 | 9863.475 | -0.151 |
| C | 924 | 40.043 | -0.244 | -0.231 | -1.766 | 1.295 | 0.052 | 0.000 | 0.000 | 0.058 | 9994.335 | -0.186 |
| D | 924 | 59.199 | -0.248 | 0.366 | -1.480 | 0.438 | 0.036 | 0.000 | 57.143 | 0.058 | 9994.335 | -0.190 |
| E | 924 | 32.684 | -0.309 | -0.629 | -1.593 | 1.426 | 0.055 | 45.563 | 0.000 | 0.110 | 9361.550 | -0.199 |
| F | 924 | 19.048 | -0.168 | -0.322 | -0.750 | 0.851 | 0.028 | 75.649 | 0.000 | 0.058 | 9994.335 | -0.110 |
| At | 924 | 17.749 | -1.085 | -1.730 | -2.225 | 2.388 | 0.055 | 81.277 | 17.749 | 0.333 | 5402.467 | -0.752 |
| Bt | 924 | 44.264 | -0.324 | -1.113 | -1.382 | 0.873 | 0.034 | 50.974 | 43.074 | 0.112 | 9863.475 | -0.211 |

### compression_fade
| mode | n | win_pct | mean_R | med_R | p10_R | p90_R | se_R | stop_pct | tgt_pct | cost_R | mean_risk | gross_R |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 8836 | 10.163 | -1.096 | -1.882 | -2.347 | 0.125 | 0.035 | 88.400 | 0.000 | 0.369 | 4819.274 | -0.728 |
| B | 8836 | 27.988 | -0.359 | -1.236 | -1.427 | 1.872 | 0.018 | 63.524 | 0.000 | 0.124 | 9749.341 | -0.235 |
| C | 8836 | 43.029 | -0.179 | -0.157 | -1.620 | 1.244 | 0.015 | 0.000 | 0.000 | 0.064 | 9994.748 | -0.115 |
| D | 8836 | 62.415 | -0.172 | 0.364 | -1.384 | 0.429 | 0.010 | 0.000 | 59.857 | 0.064 | 9994.748 | -0.108 |
| E | 8836 | 26.505 | -0.550 | -1.269 | -2.316 | 1.565 | 0.030 | 61.114 | 0.000 | 0.201 | 8073.161 | -0.349 |
| F | 8836 | 20.496 | -0.186 | -0.335 | -0.839 | 0.770 | 0.009 | 72.171 | 0.000 | 0.064 | 9994.748 | -0.122 |
| At | 8836 | 19.771 | -1.092 | -1.832 | -2.322 | 2.423 | 0.019 | 79.357 | 19.251 | 0.369 | 4819.274 | -0.723 |
| Bt | 8836 | 44.375 | -0.347 | -1.129 | -1.404 | 0.849 | 0.011 | 50.656 | 42.847 | 0.124 | 9749.341 | -0.223 |

### fvg_cb_cehold
| mode | n | win_pct | mean_R | med_R | p10_R | p90_R | se_R | stop_pct | tgt_pct | cost_R | mean_risk | gross_R |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 1111 | 10.891 | -0.922 | -1.650 | -2.043 | 0.716 | 0.080 | 88.299 | 0.000 | 0.280 | 6239.964 | -0.642 |
| B | 1111 | 28.803 | -0.306 | -1.178 | -1.330 | 2.019 | 0.049 | 63.906 | 0.000 | 0.095 | 9949.973 | -0.211 |
| C | 1111 | 43.924 | -0.152 | -0.154 | -1.624 | 1.286 | 0.040 | 0.000 | 0.000 | 0.049 | 9993.794 | -0.102 |
| D | 1111 | 63.366 | -0.120 | 0.397 | -1.333 | 0.445 | 0.027 | 0.000 | 60.666 | 0.049 | 9993.794 | -0.070 |
| E | 1111 | 28.893 | -0.551 | -1.112 | -2.421 | 1.271 | 0.067 | 54.185 | 0.000 | 0.172 | 8299.350 | -0.379 |
| F | 1111 | 21.782 | -0.109 | -0.286 | -0.673 | 0.946 | 0.024 | 73.447 | 0.000 | 0.049 | 9993.794 | -0.060 |
| At | 1111 | 20.612 | -0.844 | -1.608 | -2.026 | 2.570 | 0.052 | 78.848 | 20.252 | 0.280 | 6239.964 | -0.564 |
| Bt | 1111 | 47.255 | -0.228 | -0.480 | -1.306 | 0.890 | 0.031 | 48.605 | 45.815 | 0.095 | 9949.973 | -0.133 |

### inducement
| mode | n | win_pct | mean_R | med_R | p10_R | p90_R | se_R | stop_pct | tgt_pct | cost_R | mean_risk | gross_R |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 700 | 9.143 | -1.097 | -1.828 | -2.252 | -1.142 | 0.118 | 89.857 | 0.000 | 0.344 | 5134.130 | -0.753 |
| B | 700 | 26.143 | -0.360 | -1.228 | -1.404 | 1.790 | 0.069 | 66.571 | 0.000 | 0.116 | 9843.933 | -0.244 |
| C | 700 | 42.571 | -0.178 | -0.203 | -1.728 | 1.397 | 0.055 | 0.000 | 0.000 | 0.060 | 9994.981 | -0.118 |
| D | 700 | 62.429 | -0.198 | 0.374 | -1.510 | 0.433 | 0.037 | 0.000 | 60.286 | 0.060 | 9994.981 | -0.138 |
| E | 700 | 18.143 | -0.875 | -1.639 | -2.757 | 1.661 | 0.113 | 77.286 | 0.000 | 0.284 | 6708.573 | -0.591 |
| F | 700 | 19.000 | -0.189 | -0.328 | -0.888 | 0.777 | 0.032 | 75.571 | 0.000 | 0.060 | 9994.981 | -0.129 |
| At | 700 | 18.714 | -1.079 | -1.798 | -2.247 | 2.485 | 0.065 | 80.714 | 18.429 | 0.344 | 5134.130 | -0.735 |
| Bt | 700 | 44.429 | -0.336 | -1.146 | -1.384 | 0.864 | 0.039 | 51.429 | 43.000 | 0.116 | 9843.933 | -0.220 |

### mitigation
| mode | n | win_pct | mean_R | med_R | p10_R | p90_R | se_R | stop_pct | tgt_pct | cost_R | mean_risk | gross_R |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 3193 | 9.959 | -1.044 | -1.810 | -2.268 | -0.017 | 0.057 | 88.631 | 0.000 | 0.344 | 5164.680 | -0.700 |
| B | 3193 | 27.310 | -0.360 | -1.214 | -1.405 | 1.908 | 0.030 | 63.952 | 0.000 | 0.116 | 9831.215 | -0.244 |
| C | 3193 | 42.624 | -0.209 | -0.160 | -1.744 | 1.273 | 0.025 | 0.000 | 0.000 | 0.060 | 9995.054 | -0.149 |
| D | 3193 | 62.230 | -0.194 | 0.372 | -1.479 | 0.434 | 0.018 | 0.000 | 58.910 | 0.060 | 9995.054 | -0.134 |
| E | 3193 | 24.930 | -0.569 | -1.320 | -2.359 | 1.505 | 0.049 | 64.641 | 0.000 | 0.206 | 8014.531 | -0.363 |
| F | 3193 | 20.639 | -0.198 | -0.327 | -0.884 | 0.747 | 0.015 | 71.438 | 0.000 | 0.060 | 9995.054 | -0.138 |
| At | 3193 | 19.543 | -1.045 | -1.771 | -2.246 | 2.449 | 0.031 | 79.612 | 18.822 | 0.344 | 5164.680 | -0.701 |
| Bt | 3193 | 44.692 | -0.325 | -1.119 | -1.389 | 0.862 | 0.018 | 50.391 | 42.844 | 0.116 | 9831.215 | -0.209 |

## Holdout (temporal halves T1/T2, symbol split S1/S2) -- mean net_R
| mode | T1 | T2 | S1 | S2 |
|---|---|---|---|---|
| A | -0.984 | -1.150 | -1.043 | -1.098 |
| B | -0.328 | -0.368 | -0.339 | -0.360 |
| C | -0.186 | -0.188 | -0.165 | -0.210 |
| D | -0.182 | -0.176 | -0.162 | -0.197 |
| E | -0.527 | -0.580 | -0.554 | -0.555 |
| F | -0.171 | -0.193 | -0.183 | -0.181 |
| At | -0.985 | -1.133 | -1.053 | -1.070 |
| Bt | -0.307 | -0.353 | -0.327 | -0.336 |

n per cell:
| mode | T1 | T2 | S1 | S2 |
|---|---|---|---|---|
| A | 7096 | 7668 | 7527 | 7237 |
| B | 7096 | 7668 | 7527 | 7237 |
| C | 7096 | 7668 | 7527 | 7237 |
| D | 7096 | 7668 | 7527 | 7237 |
| E | 7096 | 7668 | 7527 | 7237 |
| F | 7096 | 7668 | 7527 | 7237 |
| At | 7096 | 7668 | 7527 | 7237 |
| Bt | 7096 | 7668 | 7527 | 7237 |

## Tail risk -- no-stop / late-stop modes (the honest part)
| mode | n | mae_atr_p50 | mae_atr_p90 | mae_atr_p99 | mae_atr_max | pct_beyond_3atr | worst_trough_R | p1_net_R | worst_net_R |
|---|---|---|---|---|---|---|---|---|---|
| C | 14764.000 | 2.155 | 6.510 | 14.960 | 38.585 | 37.029 | 12.862 | -4.232 | -11.812 |
| D | 14764.000 | 1.519 | 5.802 | 13.239 | 38.585 | 28.441 | 12.862 | -3.773 | -11.812 |
| F | 14764.000 | 1.199 | 3.042 | 6.622 | 17.486 | 10.336 | 5.829 | -1.827 | -5.465 |

mae_atr = worst adverse excursion actually endured (ATR units, entry bar through exit bar, wick-based). mae_R / worst_trough_R = that trough as a fraction of the Rs10k budget. pct_beyond_3atr = trades whose realized adverse exceeded the sizing assumption.

## Hunt timing -- P(adverse >= kxATR), first hour vs later
| k | p_ever | p_first_hour | p_later | share_of_hits_early | hazard_early | hazard_late | hazard_ratio | med_cross_bar |
|---|---|---|---|---|---|---|---|---|
| 0.250 | 0.952 | 0.927 | 0.025 | 0.974 | 0.428 | 0.017 | 25.879 | 0.000 |
| 0.500 | 0.884 | 0.821 | 0.063 | 0.929 | 0.218 | 0.018 | 11.851 | 0.000 |
| 0.750 | 0.816 | 0.718 | 0.097 | 0.880 | 0.138 | 0.018 | 7.560 | 1.000 |
| 1.000 | 0.754 | 0.619 | 0.135 | 0.821 | 0.097 | 0.018 | 5.297 | 3.000 |
| 1.250 | 0.692 | 0.533 | 0.159 | 0.770 | 0.073 | 0.017 | 4.231 | 4.000 |
| 1.500 | 0.636 | 0.455 | 0.180 | 0.716 | 0.056 | 0.016 | 3.420 | 5.000 |
| 1.750 | 0.580 | 0.382 | 0.198 | 0.659 | 0.044 | 0.016 | 2.798 | 7.000 |
| 2.000 | 0.532 | 0.324 | 0.207 | 0.610 | 0.035 | 0.015 | 2.403 | 8.000 |

hazard_* = crossings per bar-at-risk inside/outside the first 12 path bars; hazard_ratio > 1 = hunt front-loaded.

## Verdict
1. Hunt-tax recovery: stop-only vs no-stop, EOD exit: A -1.070R -> C -0.187R (recovers +0.883R); B -0.349R -> C (recovers +0.162R). Cleanest read, identical 1.5xATR target policy: Bt (stop) -0.331R vs D (no stop) -0.179R = stop tax -0.152R; At (tight stop) -1.062R vs D = -0.883R. So yes -- deleting the huntable stop recovers more than the ~0.2R background tax; but expectancy stays NEGATIVE.
2. Net-positive: NO. Best pooled mode = D (-0.179R, SE 0.008); holdout T1/T2/S1/S2 all negative for every mode. Removing the stop shrinks the bleed ~5x vs tight-stop but does not flip the sign: these signals have no positive raw edge to unlock.
3. Shadow stop E -0.554R vs tight A -1.070R: parking the stop behind the just-swept extreme helps massively (+0.516R, stop-out 61.1% vs 88.6%) but still stops out ~60% and lags no-stop C by -0.367R -- the 'dead zone' gets re-harvested. Weakest for inducement (E -0.88R, 77% stop-out, the worst E of any tool): there the swept extreme IS the signal's own trigger level and routinely gets swept again. Best for bpr (E -0.31R ~= B).
4. Front-loading: YES, extreme. At k=1.0 ATR, 82% of all hunts that ever happen complete within the first hour (per-bar hazard ratio 5.3x); at k=0.5 it is 93% (ratio 11.9x); median crossing bar is 0-3. But F (0.5xATR stop armed after 6 bars) only matches C (-0.182R vs -0.187R) -- the delay dodges the harvest window yet the late stop still clips recoveries (72% eventually stop out). F's real value is tail shape: same mean as C with p10 -0.83R vs -1.66R and worst-case -5.5R vs -11.8R.

The tax is structural, not fee-driven: gross of brokerage/STT/exchange (spread still in fills) A -0.717R vs C -0.126R -- the stop itself converts the front-loaded wiggle into realized loss; fees only widen the gap (A pays 0.35R/trade in friction vs 0.06R for C, the leverage-capped tight-stop qty being the most notional-hungry).

Bottom line: the stop IS the product -- every huntable-stop mode pays a tax that scales inversely with stop distance (A -1.07R, E -0.55R, B -0.35R, no-stop -0.18R), the adverse wiggle is almost entirely front-loaded into the first hour, and stop placement (even in the hunter's dead zone) only mitigates, never escapes. But escaping the hunt only gets you back to roughly break-even-minus-costs: no mode is net-positive, so no-stop sizing is a loss-shrinker here, not a strategy.
## MODE G -- "hunter's seat": resting limit into the sweep

Limit at signal_close -/+ gxATR, TTL 12 bars (the measured hunt window), passive fill AT the limit only when the bar trades through it by >= 1 tick (no adverse slippage -- maker side). Unfilled = no trade. Exits from FILL price, sizing/costs identical to C/D/F (3xATR size_dist, Rs10k): G-C no stop EOD | G-D no stop, 1.5xATR target (eligible only from the bar AFTER the fill bar -- intrabar order unknowable, conservative) | G-F 0.5xATR stop armed 6 bars post-fill.

### Fill rate, expectancy, adverse selection (pooled)
| g | n_signals | n_filled | fill_pct | med_fill_bar | GC_net | GD_net | GF_net | D_all_b | D_filled_c | improve_a_c | select_c_b | GD_win_pct | GD_tgt_pct |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.250 | 14764.000 | 12991.000 | 87.991 | 0.000 | -0.167 | -0.158 | -0.162 | -0.179 | -0.250 | 0.091 | -0.071 | 63.352 | 60.003 |
| 0.500 | 14764.000 | 11381.000 | 77.086 | 0.000 | -0.172 | -0.160 | -0.166 | -0.179 | -0.322 | 0.162 | -0.143 | 63.694 | 60.250 |
| 0.750 | 14764.000 | 9921.000 | 67.197 | 1.000 | -0.176 | -0.159 | -0.170 | -0.179 | -0.400 | 0.241 | -0.221 | 64.147 | 60.246 |
| 1.000 | 14764.000 | 8524.000 | 57.735 | 2.000 | -0.188 | -0.173 | -0.178 | -0.179 | -0.489 | 0.316 | -0.310 | 63.409 | 59.784 |
| 1.250 | 14764.000 | 7336.000 | 49.688 | 3.000 | -0.181 | -0.183 | -0.169 | -0.179 | -0.574 | 0.391 | -0.395 | 63.263 | 59.542 |

b = market-entry D on ALL signals = -0.179R (mode D above). c = D_filled = market-entry D restricted to G's filled subset. improve_a_c = G-D minus D-on-same-trades = pure price improvement of the discounted passive entry. select_c_b = fill-filter selection effect (negative = the trades that reach the limit are worse than average BEFORE the discount).

### Holdout (mean net_R, filled subsets)
| g | GD_T1 | GF_T1 | GD_T2 | GF_T2 | GD_S1 | GF_S1 | GD_S2 | GF_S2 |
|---|---|---|---|---|---|---|---|---|
| 0.250 | -0.169 | -0.158 | -0.148 | -0.165 | -0.143 | -0.160 | -0.174 | -0.163 |
| 0.500 | -0.168 | -0.160 | -0.153 | -0.171 | -0.139 | -0.168 | -0.183 | -0.164 |
| 0.750 | -0.165 | -0.163 | -0.154 | -0.176 | -0.145 | -0.170 | -0.174 | -0.170 |
| 1.000 | -0.177 | -0.177 | -0.170 | -0.178 | -0.154 | -0.174 | -0.194 | -0.181 |
| 1.250 | -0.186 | -0.163 | -0.180 | -0.173 | -0.153 | -0.160 | -0.213 | -0.177 |

### Per-tool x g (filled subsets)
| tool | g | n | GD | GC | GF | D_filled |
|---|---|---|---|---|---|---|
| bpr | 0.250 | 820 | -0.188 | -0.217 | -0.146 | -0.315 |
| bpr | 0.500 | 724 | -0.193 | -0.202 | -0.151 | -0.392 |
| bpr | 0.750 | 621 | -0.173 | -0.203 | -0.128 | -0.471 |
| bpr | 1.000 | 513 | -0.225 | -0.246 | -0.181 | -0.597 |
| bpr | 1.250 | 437 | -0.248 | -0.256 | -0.154 | -0.685 |
| compression_fade | 0.250 | 7743 | -0.153 | -0.157 | -0.165 | -0.243 |
| compression_fade | 0.500 | 6783 | -0.160 | -0.169 | -0.174 | -0.315 |
| compression_fade | 0.750 | 5914 | -0.165 | -0.178 | -0.186 | -0.394 |
| compression_fade | 1.000 | 5100 | -0.170 | -0.183 | -0.188 | -0.478 |
| compression_fade | 1.250 | 4408 | -0.173 | -0.176 | -0.185 | -0.561 |
| fvg_cb_cehold | 0.250 | 977 | -0.094 | -0.134 | -0.100 | -0.188 |
| fvg_cb_cehold | 0.500 | 854 | -0.086 | -0.095 | -0.089 | -0.253 |
| fvg_cb_cehold | 0.750 | 729 | -0.065 | -0.103 | -0.101 | -0.332 |
| fvg_cb_cehold | 1.000 | 613 | -0.099 | -0.112 | -0.123 | -0.414 |
| fvg_cb_cehold | 1.250 | 496 | -0.111 | -0.096 | -0.110 | -0.515 |
| inducement | 0.250 | 617 | -0.194 | -0.162 | -0.188 | -0.274 |
| inducement | 0.500 | 545 | -0.178 | -0.149 | -0.159 | -0.352 |
| inducement | 0.750 | 479 | -0.187 | -0.148 | -0.142 | -0.434 |
| inducement | 1.000 | 408 | -0.206 | -0.209 | -0.163 | -0.539 |
| inducement | 1.250 | 350 | -0.216 | -0.194 | -0.150 | -0.633 |
| mitigation | 0.250 | 2834 | -0.179 | -0.191 | -0.172 | -0.264 |
| mitigation | 0.500 | 2475 | -0.173 | -0.203 | -0.174 | -0.339 |
| mitigation | 0.750 | 2178 | -0.165 | -0.191 | -0.164 | -0.411 |
| mitigation | 1.000 | 1890 | -0.186 | -0.205 | -0.168 | -0.503 |
| mitigation | 1.250 | 1645 | -0.204 | -0.196 | -0.150 | -0.583 |

### Tail risk per g
| exit | g | n | mae_p50 | mae_p90 | mae_p99 | mae_max | pct_gt_3atr | worst_trough_R | p1_net | worst_net |
|---|---|---|---|---|---|---|---|---|---|---|
| G-C | 0.250 | 12991 | 2.061 | 6.353 | 15.496 | 38.195 | 35.694 | 12.732 | -4.257 | -11.682 |
| G-C | 0.500 | 11381 | 2.060 | 6.459 | 15.576 | 37.927 | 36.007 | 12.642 | -4.377 | -11.592 |
| G-C | 0.750 | 9921 | 2.057 | 6.427 | 15.784 | 37.683 | 35.783 | 12.561 | -4.404 | -11.511 |
| G-C | 1.000 | 8524 | 2.085 | 6.508 | 16.375 | 37.439 | 35.969 | 12.480 | -4.571 | -11.430 |
| G-C | 1.250 | 7336 | 2.112 | 6.523 | 16.338 | 37.195 | 36.437 | 12.398 | -4.562 | -11.348 |
| G-D | 0.250 | 12991 | 1.384 | 5.688 | 13.450 | 38.195 | 27.227 | 12.732 | -3.769 | -11.682 |
| G-D | 0.500 | 11381 | 1.366 | 5.670 | 13.804 | 37.927 | 27.388 | 12.642 | -3.983 | -11.592 |
| G-D | 0.750 | 9921 | 1.359 | 5.683 | 13.971 | 37.683 | 27.205 | 12.561 | -4.003 | -11.511 |
| G-D | 1.000 | 8524 | 1.389 | 5.741 | 14.483 | 37.439 | 27.628 | 12.480 | -4.083 | -11.430 |
| G-D | 1.250 | 7336 | 1.415 | 5.815 | 14.827 | 37.195 | 28.531 | 12.398 | -4.180 | -11.348 |
| G-F | 0.250 | 12991 | 1.113 | 2.992 | 6.719 | 18.601 | 9.884 | 6.200 | -1.856 | -5.322 |
| G-F | 0.500 | 11381 | 1.110 | 3.039 | 6.866 | 18.338 | 10.333 | 6.113 | -1.919 | -5.251 |
| G-F | 0.750 | 9921 | 1.117 | 3.103 | 7.417 | 18.141 | 11.078 | 6.047 | -2.085 | -5.162 |
| G-F | 1.000 | 8524 | 1.135 | 3.222 | 8.315 | 18.642 | 11.649 | 6.214 | -2.110 | -5.991 |
| G-F | 1.250 | 7336 | 1.167 | 3.285 | 8.499 | 18.388 | 12.459 | 6.129 | -2.176 | -5.906 |

### Verdict addendum -- does buying the hunt flip anything positive?
NO (tool, g, exit) config is net-positive with all four holdout splits positive at n>=100.

Adverse selection vs price improvement, headline numbers: at g=0.5 improvement +0.162R vs selection -0.143R -> G-D -0.160R; at g=1.0 improvement +0.316R vs selection -0.310R -> G-D -0.173R.
