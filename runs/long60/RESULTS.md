# DEFINITIVE 60d measurement battery — parity-locked v2 toolset

**Data**: `data/long5m/` — 138 stocks + NIFTY index, NATIVE 5m bars, 57 sessions (2026-04-27 … 2026-07-17), ~2x the old 30d window. Rows fed to the pipeline as M1; **M5 aggregation verified IDENTITY** on RELIANCE (store M5 == CSV rows == store M1, every field, 4275/4275 bars — `l60_verify.py`). No CSV was empty/thin (min 4268 rows).

**Capture**: real Orchestrator/SymbolPipeline, 7 parity-locked v2 detectors + non-colliding context providers (swings/liquidity/structure/wyckoff), index=NIFTY. **300153** signals with causal context (template, wyckoff-align, 30-min bucket, premium/discount, vol-regime, closed-M15 trend) + forward 5m path to EOD. All filters backward-looking; outcomes EOD-truncated.

**Realistic fills** (step2_engine, replicates paper.py): entry = next-bar OPEN + half-spread; stop = level-or-gap-open + half-spread+slippage (never a clean stop fill); target = limit + half-spread; EOD = last close + half+slippage; intrabar stop-before-target. Costs ₹20×2 + 0.025% sell STT + 0.00297% exchange both legs. Sizing ₹10k risk (1R), 5x leverage cap. **Caveat: bars are native 5m, so "next bar" = 5 minutes** — entries are coarser and gap-through-stop fills more pessimistic than the old M1 runs.

**Holdouts**: temporal (sessions < / >= 2026-06-08; the second half contains the OLD 30d window 2026-06-19…2026-07-17, so the **first (earlier) half is the genuinely NEW out-of-sample data**) + cross-sectional (crc32(symbol)%2). Grid: SL k∈{0.5,0.75,1.0,1.5}×ATR × target∈{1,1.5,2,3}R × {fixed, breakeven-at-1R}.


## Table 1 — per-tool SOLO sniper table

hit% = MFE>=1ATR before MAE>=1ATR (24-bar window, EOD-truncated); base% = 20 seeded random same-session/same-30min-bucket/same-direction bars; MFE/MAE = full-EOD-path excursions in ATR from next-bar open. best = best realistic-fill config (net expectancy in R after costs); T1/T2 = temporal halves (T1 = NEW earlier OOS), C0/C1 = symbol-hash halves.

| detector | n | hit% | base% | edge | MFE | MAE | MFE/MAE | best cfg | best exp | win% | T1 | T2 | C0 | C1 | both holdouts+? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ob_lux | 79028 | 49% | 40% | +0.09 | 2.98 | 3.09 | 0.96 | k=1.5 fixed_t1 | -0.302 | 45% | -0.276 | -0.326 | -0.301 | -0.303 | no |
| fvg_cb | 37009 | 48% | 39% | +0.09 | 2.93 | 2.96 | 0.99 | k=1.5 fixed_t1 | -0.244 | 46% | -0.226 | -0.261 | -0.244 | -0.243 | no |
| compression_fade | 113445 | 49% | 39% | +0.09 | 3.00 | 2.99 | 1.00 | k=1.5 fixed_t1.5 | -0.291 | 37% | -0.273 | -0.309 | -0.284 | -0.299 | no |
| inducement | 9177 | 48% | 33% | +0.15 | 3.06 | 3.07 | 1.00 | k=1.5 fixed_t1 | -0.283 | 46% | -0.269 | -0.295 | -0.301 | -0.263 | no |
| bpr | 12970 | 50% | 44% | +0.05 | 3.02 | 2.96 | 1.02 | k=1.5 fixed_t3 | -0.259 | 30% | -0.243 | -0.270 | -0.237 | -0.283 | no |
| mitigation | 43095 | 48% | 39% | +0.10 | 2.97 | 3.07 | 0.97 | k=1.5 fixed_t1 | -0.276 | 46% | -0.259 | -0.292 | -0.276 | -0.275 | no |
| turtle_soup | 5429 | 46% | 38% | +0.09 | 3.11 | 3.32 | 0.94 | k=1.5 fixed_t1 | -0.307 | 45% | -0.276 | -0.337 | -0.327 | -0.285 | no |

### Table 1b — per (detector, event): hit metrics + best realistic config

| detector | event | n | hit% | base% | edge | best cfg | best exp | T1 | T2 | all_pos |
|---|---|---|---|---|---|---|---|---|---|---|
| ob_lux | OB_RETEST | 79028 | 49% | 40% | +0.09 | k=1.5 fixed_t1 | -0.302 | -0.276 | -0.326 | no |
| fvg_cb | FVG_RETEST | 19959 | 48% | 41% | +0.07 | k=1.5 fixed_t1 | -0.238 | -0.227 | -0.249 | no |
| fvg_cb | FVG_CE_HOLD | 17050 | 48% | 37% | +0.11 | k=1.5 fixed_t1 | -0.250 | -0.225 | -0.276 | no |
| compression_fade | COMPRESSION_FADE | 113445 | 49% | 39% | +0.09 | k=1.5 fixed_t1.5 | -0.291 | -0.273 | -0.309 | no |
| inducement | INDUCEMENT_GRAB | 9177 | 48% | 33% | +0.15 | k=1.5 fixed_t1 | -0.283 | -0.269 | -0.295 | no |
| bpr | BPR | 12970 | 50% | 44% | +0.05 | k=1.5 fixed_t3 | -0.259 | -0.243 | -0.270 | no |
| mitigation | MITIGATION | 43095 | 48% | 39% | +0.10 | k=1.5 fixed_t1 | -0.276 | -0.259 | -0.292 | no |
| turtle_soup | TURTLE_SOUP | 5429 | 46% | 38% | +0.09 | k=1.5 fixed_t1 | -0.307 | -0.276 | -0.337 | no |

### Table 1c — realistic grid, top 3 configs per tool

| detector | k | scheme | n | win% | exp R | T1 | T2 | C0 | C1 | all_pos |
|---|---|---|---|---|---|---|---|---|---|---|
| ob_lux | 1.5 | fixed_t1 | 79028 | 45% | -0.302 | -0.276 | -0.326 | -0.301 | -0.303 | no |
| ob_lux | 1.5 | fixed_t1.5 | 79028 | 37% | -0.317 | -0.286 | -0.345 | -0.316 | -0.317 | no |
| ob_lux | 1.5 | be1r_t1.5 | 79028 | 31% | -0.322 | -0.292 | -0.349 | -0.321 | -0.323 | no |
| fvg_cb | 1.5 | fixed_t1 | 37009 | 46% | -0.244 | -0.226 | -0.261 | -0.244 | -0.243 | no |
| fvg_cb | 1.5 | fixed_t1.5 | 37009 | 38% | -0.247 | -0.228 | -0.266 | -0.252 | -0.242 | no |
| fvg_cb | 1.5 | fixed_t2 | 37009 | 33% | -0.250 | -0.238 | -0.262 | -0.257 | -0.242 | no |
| compression_fade | 1.5 | fixed_t1.5 | 113445 | 37% | -0.291 | -0.273 | -0.309 | -0.284 | -0.299 | no |
| compression_fade | 1.5 | fixed_t1 | 113445 | 45% | -0.292 | -0.273 | -0.310 | -0.286 | -0.299 | no |
| compression_fade | 1.5 | fixed_t2 | 113445 | 33% | -0.295 | -0.280 | -0.310 | -0.285 | -0.308 | no |
| inducement | 1.5 | fixed_t1 | 9177 | 46% | -0.283 | -0.269 | -0.295 | -0.301 | -0.263 | no |
| inducement | 1.5 | fixed_t1.5 | 9177 | 37% | -0.294 | -0.291 | -0.297 | -0.319 | -0.267 | no |
| inducement | 1.5 | be1r_t1.5 | 9177 | 32% | -0.298 | -0.285 | -0.310 | -0.316 | -0.279 | no |
| bpr | 1.5 | fixed_t3 | 12970 | 30% | -0.259 | -0.243 | -0.270 | -0.237 | -0.283 | no |
| bpr | 1.5 | fixed_t2 | 12970 | 34% | -0.259 | -0.237 | -0.274 | -0.240 | -0.281 | no |
| bpr | 1.5 | fixed_t1.5 | 12970 | 38% | -0.270 | -0.255 | -0.280 | -0.255 | -0.286 | no |
| mitigation | 1.5 | fixed_t1 | 43095 | 46% | -0.276 | -0.259 | -0.292 | -0.276 | -0.275 | no |
| mitigation | 1.5 | fixed_t1.5 | 43095 | 38% | -0.279 | -0.267 | -0.291 | -0.278 | -0.280 | no |
| mitigation | 1.5 | fixed_t2 | 43095 | 33% | -0.284 | -0.272 | -0.295 | -0.281 | -0.287 | no |
| turtle_soup | 1.5 | fixed_t1 | 5429 | 45% | -0.307 | -0.276 | -0.337 | -0.327 | -0.285 | no |
| turtle_soup | 1.5 | fixed_t1.5 | 5429 | 36% | -0.321 | -0.300 | -0.342 | -0.340 | -0.300 | no |
| turtle_soup | 1.5 | be1r_t1.5 | 5429 | 31% | -0.326 | -0.308 | -0.343 | -0.339 | -0.311 | no |

Configs with positive net expectancy anywhere in the grid (n>=300): **0 of 196**. Holdout-stable positive: **0**.


## Table 2 — tool×tool co-fire pair matrix (CAUSAL: B fired 0–3 bars BEFORE/at A, same direction, zone-mids <=0.5×ATR)

Cell = hit-edge LIFT of the co-fired A-subset vs solo A (percentage points). n in parentheses.

| A \ B | ob_lux | fvg_cb | compression_fade | inducement | bpr | mitigation | turtle_soup |
|---|---|---|---|---|---|---|---|
| **ob_lux** | — | +0.03 (1377) | +0.00 (15458) | +0.01 (1751) | -0.02 (469) | +0.04 (15362) | +0.02 (519) |
| **fvg_cb** | +0.03 (852) | — | +0.03 (4038) | -0.01 (162) | -0.02 (2998) | -0.02 (1009) | -0.01 (275) |
| **compression_fade** | +0.03 (7480) | +0.03 (4689) | — | +0.04 (2142) | -0.02 (3114) | +0.03 (9989) | +0.05 (950) |
| **inducement** | +0.00 (1006) | -0.03 (203) | +0.01 (2451) | — | -0.06 (84) | -0.00 (984) | -0.03 (270) |
| **bpr** | -0.01 (276) | +0.04 (2378) | +0.03 (3200) | +0.06 (122) | — | +0.07 (635) | +0.01 (32) |
| **mitigation** | +0.04 (6522) | -0.00 (879) | +0.04 (6669) | +0.06 (810) | +0.01 (420) | — | +0.01 (531) |
| **turtle_soup** | -0.02 (315) | -0.01 (277) | -0.00 (812) | +0.01 (328) | . (12) | +0.01 (569) | — |

### Table 2b — pair detail (realistic expectancy at A's best config), sorted by exp lift

| A | B | n | edge_cofire | edge_solo_A | exp_cofire | solo_A | solo_B | robust | beats both? |
|---|---|---|---|---|---|---|---|---|---|
| bpr | turtle_soup | 32 | +0.07 | +0.05 | -0.050 | -0.259 | -0.307 | -0.266 | no |
| turtle_soup | fvg_cb | 277 | +0.08 | +0.09 | -0.138 | -0.307 | -0.244 | -0.174 | no |
| mitigation | inducement | 810 | +0.15 | +0.10 | -0.151 | -0.276 | -0.283 | -0.184 | no |
| mitigation | fvg_cb | 879 | +0.09 | +0.10 | -0.195 | -0.276 | -0.244 | -0.230 | no |
| inducement | mitigation | 984 | +0.15 | +0.15 | -0.221 | -0.283 | -0.276 | -0.249 | no |
| compression_fade | fvg_cb | 4689 | +0.12 | +0.09 | -0.229 | -0.291 | -0.244 | -0.282 | no |
| ob_lux | fvg_cb | 1377 | +0.12 | +0.09 | -0.245 | -0.302 | -0.244 | -0.329 | no |
| bpr | ob_lux | 276 | +0.05 | +0.05 | -0.209 | -0.259 | -0.302 | -0.507 | no |
| bpr | fvg_cb | 2378 | +0.10 | +0.05 | -0.213 | -0.259 | -0.244 | -0.253 | no |
| compression_fade | bpr | 3114 | +0.08 | +0.09 | -0.259 | -0.291 | -0.259 | -0.324 | no |
| ob_lux | inducement | 1751 | +0.10 | +0.09 | -0.274 | -0.302 | -0.283 | -0.302 | no |
| turtle_soup | inducement | 328 | +0.10 | +0.09 | -0.282 | -0.307 | -0.283 | -0.391 | no |
| ob_lux | mitigation | 15362 | +0.13 | +0.09 | -0.285 | -0.302 | -0.276 | -0.341 | no |
| fvg_cb | turtle_soup | 275 | +0.08 | +0.09 | -0.227 | -0.244 | -0.307 | -0.251 | no |
| fvg_cb | compression_fade | 4038 | +0.11 | +0.09 | -0.230 | -0.244 | -0.291 | -0.249 | no |
| fvg_cb | bpr | 2998 | +0.07 | +0.09 | -0.232 | -0.244 | -0.259 | -0.260 | no |
| compression_fade | mitigation | 9989 | +0.13 | +0.09 | -0.281 | -0.291 | -0.276 | -0.309 | no |
| inducement | ob_lux | 1006 | +0.15 | +0.15 | -0.277 | -0.283 | -0.302 | -0.318 | no |
| fvg_cb | ob_lux | 852 | +0.12 | +0.09 | -0.240 | -0.244 | -0.302 | -0.358 | no |
| ob_lux | bpr | 469 | +0.06 | +0.09 | -0.300 | -0.302 | -0.259 | -0.509 | no |
| fvg_cb | mitigation | 1009 | +0.07 | +0.09 | -0.246 | -0.244 | -0.276 | -0.272 | no |
| turtle_soup | mitigation | 569 | +0.10 | +0.09 | -0.313 | -0.307 | -0.276 | -0.382 | no |
| mitigation | ob_lux | 6522 | +0.14 | +0.10 | -0.282 | -0.276 | -0.302 | -0.330 | no |
| bpr | compression_fade | 3200 | +0.09 | +0.05 | -0.266 | -0.259 | -0.291 | -0.331 | no |
| inducement | compression_fade | 2451 | +0.16 | +0.15 | -0.294 | -0.283 | -0.291 | -0.313 | no |
| ob_lux | compression_fade | 15458 | +0.09 | +0.09 | -0.315 | -0.302 | -0.291 | -0.336 | no |
| compression_fade | ob_lux | 7480 | +0.12 | +0.09 | -0.307 | -0.291 | -0.302 | -0.339 | no |
| inducement | turtle_soup | 270 | +0.11 | +0.15 | -0.300 | -0.283 | -0.307 | -0.391 | no |
| mitigation | compression_fade | 6669 | +0.13 | +0.10 | -0.295 | -0.276 | -0.291 | -0.317 | no |
| mitigation | turtle_soup | 531 | +0.10 | +0.10 | -0.296 | -0.276 | -0.307 | -0.366 | no |
| turtle_soup | compression_fade | 812 | +0.08 | +0.09 | -0.333 | -0.307 | -0.291 | -0.361 | no |
| compression_fade | inducement | 2142 | +0.13 | +0.09 | -0.317 | -0.291 | -0.283 | -0.333 | no |
| mitigation | bpr | 420 | +0.10 | +0.10 | -0.307 | -0.276 | -0.259 | -0.371 | no |
| bpr | mitigation | 635 | +0.12 | +0.05 | -0.290 | -0.259 | -0.276 | -0.348 | no |
| compression_fade | turtle_soup | 950 | +0.14 | +0.09 | -0.323 | -0.291 | -0.307 | -0.353 | no |
| ob_lux | turtle_soup | 519 | +0.11 | +0.09 | -0.360 | -0.302 | -0.307 | -0.440 | no |
| turtle_soup | ob_lux | 315 | +0.07 | +0.09 | -0.369 | -0.307 | -0.302 | -0.427 | no |
| inducement | fvg_cb | 203 | +0.12 | +0.15 | -0.378 | -0.283 | -0.244 | -0.475 | no |
| inducement | bpr | 84 | +0.09 | +0.15 | -0.458 | -0.283 | -0.259 | -0.490 | no |
| fvg_cb | inducement | 162 | +0.08 | +0.09 | -0.421 | -0.244 | -0.283 | -0.500 | no |
| bpr | inducement | 122 | +0.11 | +0.05 | -0.452 | -0.259 | -0.283 | -0.576 | no |

## Table 3 — top stacked configs (tool + filters + exit), holdout-stable only

**NONE.** No (tool + causal-filter set + exit) combination has positive net realistic expectancy on the full sample AND all four holdout cells (n>=300 full / >=75 per cell).


### Table 3b — best stacked config per tool by FULL-sample exp (any sign, n>=300) — the honest ceiling

| detector | k | scheme | filters | n | win% | exp R | robust | T1 | T2 | C0 | C1 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| turtle_soup | 1.5 | fixed_t1 | outside+wyck_aligned+pd_unf | 512 | 53% | -0.075 | -0.131 | -0.031 | -0.131 | -0.121 | -0.035 |
| bpr | 1.5 | fixed_t3 | outside+wyck_counter+vol_con | 678 | 33% | -0.077 | -0.302 | +0.291 | -0.302 | -0.061 | -0.095 |
| inducement | 1.5 | be1r_t1.5 | outside+wyck_aligned+vol_exp | 1514 | 37% | -0.140 | -0.207 | -0.068 | -0.207 | -0.181 | -0.096 |
| mitigation | 1.5 | fixed_t1.5 | outside+wyck_aligned+vol_exp | 5533 | 40% | -0.170 | -0.183 | -0.157 | -0.183 | -0.178 | -0.162 |
| compression_fade | 1.5 | fixed_t2 | outside+wyck_counter+htf_counter | 11091 | 35% | -0.189 | -0.245 | -0.135 | -0.245 | -0.200 | -0.178 |
| ob_lux | 1.5 | fixed_t1.5 | outside+htf_counter+vol_exp | 9638 | 38% | -0.201 | -0.233 | -0.175 | -0.226 | -0.173 | -0.233 |
| fvg_cb | 1.5 | fixed_t1 | regime_range+wyck_aligned+vol_exp | 12223 | 46% | -0.208 | -0.237 | -0.178 | -0.237 | -0.202 | -0.215 |

## Table 4 — causal filter Δ matrix (net realistic exp change vs solo, at each tool's best config)

| detector | regime(TRAP) | release(11-14:45) | wyck_align | htf_align | pd_favorable | vol_expansion | vol_contraction |
|---|---|---|---|---|---|---|---|
| **ob_lux** | -0.04 (2479) | -0.03 (53287) | -0.01 (28861) | +0.01 (13343) | +0.01 (55693) | +0.03 (33001) | -0.02 (45990) |
| **fvg_cb** | -0.12 (712) | -0.05 (13624) | +0.00 (17272) | +0.01 (19037) | -0.01 (19941) | +0.02 (26319) | -0.05 (10685) |
| **compression_fade** | -0.06 (3086) | -0.03 (72839) | -0.00 (46701) | +0.00 (40840) | +0.00 (64088) | +0.03 (46841) | -0.02 (66479) |
| **inducement** | -0.03 (193) | -0.08 (5021) | +0.01 (4923) | +0.00 (5602) | +0.03 (3722) | +0.05 (4316) | -0.04 (4839) |
| **bpr** | -0.07 (368) | -0.02 (7703) | -0.03 (6235) | -0.00 (7450) | -0.01 (4245) | -0.01 (6275) | +0.01 (6695) |
| **mitigation** | -0.02 (1099) | -0.05 (23800) | +0.01 (16306) | +0.02 (15173) | +0.00 (26219) | +0.03 (25359) | -0.04 (17736) |
| **turtle_soup** | -0.00 (135) | -0.07 (2860) | +0.05 (2174) | +0.03 (1512) | -0.03 (2597) | +0.04 (3259) | -0.06 (2170) |

Same matrix, hit-edge Δ (pp):

| detector | regime(TRAP) | release(11-14:45) | wyck_align | htf_align | pd_favorable | vol_expansion | vol_contraction |
|---|---|---|---|---|---|---|---|
| **ob_lux** | -0.01 | +0.00 | +0.00 | +0.00 | +0.01 | +0.00 | -0.00 |
| **fvg_cb** | +0.03 | +0.03 | -0.00 | -0.03 | +0.04 | -0.01 | +0.02 |
| **compression_fade** | +0.01 | +0.00 | -0.00 | -0.02 | +0.02 | +0.00 | -0.00 |
| **inducement** | +0.00 | +0.02 | +0.01 | -0.02 | +0.00 | -0.02 | +0.02 |
| **bpr** | +0.01 | -0.00 | +0.00 | +0.00 | +0.02 | +0.00 | -0.00 |
| **mitigation** | +0.03 | +0.02 | +0.00 | -0.02 | +0.02 | -0.01 | +0.02 |
| **turtle_soup** | -0.03 | +0.01 | -0.00 | -0.02 | +0.01 | -0.01 | +0.01 |

## Sequence chains (A fires 1–6 bars before B, same direction; entry on B at B's best config)

| A first | B entry | n | exp_chain | solo_B | solo_A | lift vs B | robust | beats both? |
|---|---|---|---|---|---|---|---|---|
| fvg_cb | turtle_soup | 286 | -0.212 | -0.307 | -0.244 | +0.095 | -0.231 | no |
| bpr | turtle_soup | 160 | -0.242 | -0.307 | -0.259 | +0.065 | -0.278 | no |
| fvg_cb | mitigation | 4487 | -0.215 | -0.276 | -0.244 | +0.060 | -0.255 | no |
| turtle_soup | bpr | 279 | -0.201 | -0.259 | -0.307 | +0.058 | -0.325 | no |
| fvg_cb | bpr | 1885 | -0.209 | -0.259 | -0.244 | +0.050 | -0.262 | no |
| fvg_cb | compression_fade | 11287 | -0.245 | -0.291 | -0.244 | +0.047 | -0.292 | no |
| fvg_cb | ob_lux | 7462 | -0.260 | -0.302 | -0.244 | +0.042 | -0.305 | no |
| bpr | compression_fade | 4817 | -0.255 | -0.291 | -0.259 | +0.036 | -0.281 | no |
| fvg_cb | inducement | 900 | -0.247 | -0.283 | -0.244 | +0.036 | -0.295 | no |
| mitigation | bpr | 2140 | -0.229 | -0.259 | -0.276 | +0.029 | -0.275 | no |
| inducement | turtle_soup | 607 | -0.282 | -0.307 | -0.283 | +0.025 | -0.322 | no |
| bpr | ob_lux | 3279 | -0.279 | -0.302 | -0.259 | +0.022 | -0.322 | no |

Chains beating BOTH solos with holdout stability: **0** of 42 testable chains.


## Old-window overlap vs NEW out-of-sample

OLD 30d datasets covered 2026-06-19…2026-07-17. Splitting this 60d sample at 2026-06-19: `overlap` reproduces the old measurement window on the fixed toolset; `new-OOS` is data the toolset has NEVER been tuned or evaluated on.

| detector | old 30d edge | edge overlap | edge new-OOS | old 30d best real exp | real exp overlap* | real exp new-OOS* |
|---|---|---|---|---|---|---|
| ob_lux | +0.08 | +0.09 | +0.09 | -0.344 | -0.323 | -0.290 |
| fvg_cb | +0.06 | +0.09 | +0.09 | -0.255 | -0.269 | -0.230 |
| compression_fade | +0.09 | +0.09 | +0.09 | -0.304 | -0.305 | -0.284 |
| inducement | +0.12 | +0.14 | +0.15 | -0.245 | -0.279 | -0.285 |
| bpr | -0.03 | +0.05 | +0.06 | -0.280 | -0.253 | -0.263 |
| mitigation | +0.09 | +0.09 | +0.10 | -0.323 | -0.298 | -0.264 |
| turtle_soup | +0.09 | +0.10 | +0.08 | -0.336 | -0.300 | -0.311 |

\* at this run's best config per tool; old best exp came from the M1 fill grid (finer fills, wider scheme set) — directionally comparable only.


## VERDICT

**(1) Did the parity+continuum fixes change the edges vs the old 30d numbers?** (compared on the SAME sessions — the overlap window — so the period is held fixed and only the toolset changed)

Hit-edge, old toolset (old 30d run) vs fixed toolset (overlap window), with full-60d in brackets: ob_lux old +0.08 -> +0.09 [60d +0.09]; fvg_cb old +0.06 -> +0.09 [60d +0.09]; compression_fade old +0.09 -> +0.09 [60d +0.09]; inducement old +0.12 -> +0.14 [60d +0.15]; bpr old -0.03 -> +0.05 [60d +0.05]; mitigation old +0.09 -> +0.09 [60d +0.10]; turtle_soup old +0.09 -> +0.10 [60d +0.09].
Materially better on the same window: fvg_cb, inducement, bpr. Materially worse: none. Unchanged (±2pp): ob_lux, compression_fade, mitigation, turtle_soup.

**(2) Does the NEW out-of-sample half confirm?**

ob_lux: edge +0.09 new vs +0.09 overlap (confirms); fvg_cb: edge +0.09 new vs +0.09 overlap (confirms); compression_fade: edge +0.09 new vs +0.09 overlap (confirms); inducement: edge +0.15 new vs +0.14 overlap (confirms); bpr: edge +0.06 new vs +0.05 overlap (confirms); mitigation: edge +0.10 new vs +0.09 overlap (confirms); turtle_soup: edge +0.08 new vs +0.10 overlap (confirms).

**(3) Is ANY realistic config net-positive + holdout-stable?**

Solo grid: 0 of 196 (det,k,scheme) cells positive; 0 holdout-stable. Best solo cell: fvg_cb k=1.5 fixed_t1 exp=-0.244. Stacked (tool+filters+exit): 0 holdout-stable positive configs.

**(4) Best tool combinations, ranked.**

Top co-fire pairs by realistic exp lift: bpr+turtle_soup (n=32, exp -0.05 vs solo -0.26, edge lift +0.01); turtle_soup+fvg_cb (n=277, exp -0.14 vs solo -0.31, edge lift -0.01); mitigation+inducement (n=810, exp -0.15 vs solo -0.28, edge lift +0.06). Pairs beating both solos holdout-stably: 0. Top sequence chains: fvg_cb->turtle_soup (n=286, -0.21 vs solo -0.31); bpr->turtle_soup (n=160, -0.24 vs solo -0.31); fvg_cb->mitigation (n=4487, -0.22 vs solo -0.28). Chains beating both solos holdout-stably: 0.

**Bottom line.** The parity-locked toolset has REAL, out-of-sample-stable directional signal: every tool beats its matched random baseline (+5..+15pp), the edges reproduce across 57 sessions x 138 stocks, on the never-seen earlier half, and on both symbol halves — bpr even flipped from negative to positive edge after the parity fixes. But that signal does NOT survive execution: MFE/MAE stays ~1.0 (excursions symmetric), so no SL/target geometry converts the hit-edge into net rupees. All 196 realistic-fill grid cells are negative (best -0.244R), every best config sits at the WIDEST tested stop (k=1.5 ATR) with plain fixed targets (breakeven management never helps), the best filter stack reaches only -0.075R, and 0 of 42 co-fire pairs and 0 of 42 sequence chains beat both solos holdout-stably. A notable reversal vs the old 30d RR study: under realistic fills the 11:00-14:45 release window HURTS every tool (Δ -0.02..-0.08R); the best stacks all prefer 'outside'. Verdict: at 5m granularity, NSE intraday costs (~Rs40 brokerage + STT + spread/slippage per round trip on Rs10k risk) plus symmetric excursions consume the entire information edge. Nothing here is tradeable as-is; the toolset is a valid DIRECTION/CONTEXT layer, not an entry/exit system.

