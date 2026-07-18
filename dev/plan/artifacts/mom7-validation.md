# MOM7 — prior 7-bar H1 momentum alignment: full-scale validation

Finding under test (post-hoc, HINDUNILVR H1, 154 trades, 2026-01..07): entries
WITH prior 7-bar momentum won 53% at 3R vs 37% AGAINST (+16pp). Tested here on
the full l4 ladder: 138 symbols x 2023-08..2026-07, same setup rules
(fvg/ob/sweep/bos retest), struct SL floored 1.5*ATR, tgt walk with 40-bar
time stop + overnight gap-through, delivery costs. align7 computed at the
closed signal bar (leak-free), inside splice segments only.
Signals: 154992 | align7 coverage 99.9% (WITH 46.5% / AGAINST 53.4%).
hit3 = 3R target reached before stop/time. Verdict bar: spread >=8pp AND
net-improving in majority of eras + both symbol halves OUT of discovery.

## Pooled + per-setup (all data, dirs pooled)

| cell | n_W | n_A | hit3%_W | hit3%_A | spread pp | net2R W/A (d) | net3R W/A (d) | z |
|---|---|---|---|---|---|---|---|---|
| POOLED | 72036 | 82741 | 19.4 | 20.2 | **-0.8** | -0.189/-0.209 (+0.019) | -0.181/-0.191 (+0.010) | -3.7 |
| bos_retest | 19427 | 3216 | 21.1 | 21.0 | **+0.1** | -0.209/-0.204 (-0.006) | -0.207/-0.200 (-0.007) | +0.1 |
| fvg_retest | 44451 | 23359 | 19.3 | 19.5 | **-0.2** | -0.176/-0.174 (-0.002) | -0.165/-0.155 (-0.010) | -0.7 |
| ob_retest | 4909 | 11878 | 17.0 | 19.8 | **-2.8** | -0.235/-0.186 (-0.049) | -0.228/-0.167 (-0.062) | -4.2 |
| sweep_reclaim | 3249 | 44288 | 15.2 | 20.6 | **-5.4** | -0.178/-0.233 (+0.055) | -0.170/-0.215 (+0.045) | -7.4 |

### By direction (all data)

| cell | n_W | n_A | hit3%_W | hit3%_A | spread pp | net2R W/A (d) | net3R W/A (d) | z |
|---|---|---|---|---|---|---|---|---|
| long | 35680 | 42160 | 20.6 | 21.2 | **-0.6** | -0.147/-0.178 (+0.031) | -0.122/-0.147 (+0.025) | -2.1 |
| short | 36356 | 40581 | 18.3 | 19.1 | **-0.8** | -0.231/-0.241 (+0.010) | -0.239/-0.236 (-0.002) | -3.0 |

## Window robustness (align N = 5/7/10/14)

### Full sample

| cell | n_W | n_A | hit3%_W | hit3%_A | spread pp | net2R W/A (d) | net3R W/A (d) | z |
|---|---|---|---|---|---|---|---|---|
| align5 | 71409 | 83366 | 19.5 | 20.1 | **-0.6** | -0.187/-0.210 (+0.023) | -0.180/-0.191 (+0.010) | -3.1 |
| align7 | 72036 | 82741 | 19.4 | 20.2 | **-0.8** | -0.189/-0.209 (+0.019) | -0.181/-0.191 (+0.010) | -3.7 |
| align10 | 71393 | 83413 | 19.3 | 20.3 | **-0.9** | -0.192/-0.206 (+0.013) | -0.185/-0.187 (+0.002) | -4.6 |
| align14 | 69040 | 85759 | 19.3 | 20.3 | **-0.9** | -0.192/-0.206 (+0.014) | -0.183/-0.188 (+0.005) | -4.6 |

### OOS-strict (ex-HINDUNILVR, pre-2026)

| cell | n_W | n_A | hit3%_W | hit3%_A | spread pp | net2R W/A (d) | net3R W/A (d) | z |
|---|---|---|---|---|---|---|---|---|
| align5 | 57387 | 67236 | 19.6 | 19.9 | **-0.3** | -0.182/-0.224 (+0.042) | -0.174/-0.199 (+0.026) | -1.2 |
| align7 | 57916 | 66710 | 19.6 | 19.9 | **-0.3** | -0.183/-0.223 (+0.040) | -0.174/-0.199 (+0.025) | -1.4 |
| align10 | 57395 | 67260 | 19.4 | 20.0 | **-0.6** | -0.189/-0.218 (+0.029) | -0.181/-0.193 (+0.012) | -2.7 |
| align14 | 55409 | 69226 | 19.4 | 20.0 | **-0.6** | -0.191/-0.216 (+0.025) | -0.180/-0.193 (+0.012) | -2.8 |

## Interaction with daily SMA20 alignment (trend_agree)

P(align7=WITH | sma20 agree) = 48.8% ; P(align7=WITH | sma20 disagree) = 44.3% ; phi = 0.045

| cell | n_W | n_A | hit3%_W | hit3%_A | spread pp | net2R W/A (d) | net3R W/A (d) | z |
|---|---|---|---|---|---|---|---|---|
| sma20-agree: mom7 spread | 36918 | 38671 | 18.8 | 19.8 | **-1.0** | -0.216/-0.215 (-0.001) | -0.214/-0.204 (-0.011) | -3.4 |
| sma20-disagree: mom7 spread | 35118 | 44070 | 20.1 | 20.5 | **-0.5** | -0.162/-0.203 (+0.041) | -0.145/-0.179 (+0.034) | -1.6 |

Inverse cut (does sma20 add within mom7 strata? spread here = sma20 W-A):

| cell | n_W | n_A | hit3%_W | hit3%_A | spread pp | net2R W/A (d) | net3R W/A (d) | z |
|---|---|---|---|---|---|---|---|---|
| mom7-WITH: sma20 spread | 36918 | 35118 | 18.8 | 20.1 | **-1.3** | -0.216/-0.162 (-0.054) | -0.214/-0.145 (-0.069) | -4.3 |
| mom7-AGAINST: sma20 spread | 38671 | 44070 | 19.8 | 20.5 | **-0.8** | -0.215/-0.203 (-0.012) | -0.204/-0.179 (-0.025) | -2.7 |

## Era matrix (ex-HINDUNILVR, pooled setups)

| cell | n_W | n_A | hit3%_W | hit3%_A | spread pp | net2R W/A (d) | net3R W/A (d) | z |
|---|---|---|---|---|---|---|---|---|
| 2023H2 | 9176 | 10058 | 20.0 | 19.7 | **+0.3** | -0.186/-0.235 (+0.049) | -0.164/-0.193 (+0.029) | +0.5 |
| 2024H1 | 11603 | 13493 | 19.1 | 19.3 | **-0.1** | -0.168/-0.217 (+0.049) | -0.164/-0.200 (+0.037) | -0.3 |
| 2024H2 | 12337 | 14186 | 19.4 | 19.2 | **+0.3** | -0.187/-0.242 (+0.056) | -0.173/-0.225 (+0.051) | +0.6 |
| 2025H1 | 12285 | 14552 | 20.5 | 21.1 | **-0.6** | -0.145/-0.215 (+0.070) | -0.143/-0.182 (+0.039) | -1.2 |
| 2025H2 | 12515 | 14421 | 19.1 | 20.3 | **-1.2** | -0.230/-0.211 (-0.019) | -0.221/-0.195 (-0.026) | -2.5 |
| 2026H1 | 12309 | 13953 | 19.4 | 22.0 | **-2.5** | -0.212/-0.145 (-0.068) | -0.202/-0.156 (-0.046) | -5.1 |
| 2026H2 | 1335 | 1488 | 12.5 | 16.1 | **-3.6** | -0.250/-0.123 (-0.127) | -0.295/-0.136 (-0.159) | -2.7 |

## Symbol halves crc32%2 (OOS-strict: ex-HUL, pre-2026)

| cell | n_W | n_A | hit3%_W | hit3%_A | spread pp | net2R W/A (d) | net3R W/A (d) | z |
|---|---|---|---|---|---|---|---|---|
| crc=0 | 30342 | 35072 | 19.7 | 19.9 | **-0.2** | -0.182/-0.226 (+0.044) | -0.171/-0.204 (+0.034) | -0.6 |
| crc=1 | 27574 | 31638 | 19.5 | 19.9 | **-0.5** | -0.186/-0.221 (+0.035) | -0.177/-0.193 (+0.016) | -1.4 |

## Discovery vs out-of-sample

| cell | n_W | n_A | hit3%_W | hit3%_A | spread pp | net2R W/A (d) | net3R W/A (d) | z |
|---|---|---|---|---|---|---|---|---|
| DISCOVERY (HUL, 2026) | 110 | 126 | 19.1 | 23.0 | **-3.9** | -0.102/-0.198 (+0.096) | -0.163/-0.127 (-0.036) | -0.7 |
| HUL pre-2026 | 366 | 464 | 18.3 | 18.3 | **-0.0** | -0.160/-0.288 (+0.129) | -0.176/-0.239 (+0.062) | -0.0 |
| non-HUL 2026 | 13644 | 15441 | 18.8 | 21.4 | **-2.7** | -0.216/-0.142 (-0.073) | -0.211/-0.154 (-0.057) | -5.6 |
| OOS-STRICT (non-HUL pre-2026) | 57916 | 66710 | 19.6 | 19.9 | **-0.3** | -0.183/-0.223 (+0.040) | -0.174/-0.199 (+0.025) | -1.4 |

### OOS-strict per setup

| cell | n_W | n_A | hit3%_W | hit3%_A | spread pp | net2R W/A (d) | net3R W/A (d) | z |
|---|---|---|---|---|---|---|---|---|
| bos_retest | 15952 | 2571 | 21.1 | 20.7 | **+0.5** | -0.209/-0.231 (+0.022) | -0.203/-0.205 (+0.002) | +0.5 |
| fvg_retest | 35280 | 18390 | 19.6 | 19.2 | **+0.5** | -0.164/-0.188 (+0.024) | -0.151/-0.164 (+0.013) | +1.3 |
| ob_retest | 4005 | 9602 | 16.7 | 19.9 | **-3.2** | -0.246/-0.189 (-0.056) | -0.244/-0.161 (-0.083) | -4.4 |
| sweep_reclaim | 2679 | 36147 | 14.7 | 20.3 | **-5.5** | -0.197/-0.250 (+0.053) | -0.190/-0.226 (+0.036) | -6.9 |

### OOS-strict by direction

| cell | n_W | n_A | hit3%_W | hit3%_A | spread pp | net2R W/A (d) | net3R W/A (d) | z |
|---|---|---|---|---|---|---|---|---|
| long | 28818 | 33783 | 21.2 | 21.4 | **-0.2** | -0.121/-0.173 (+0.052) | -0.089/-0.131 (+0.042) | -0.6 |
| short | 29098 | 32927 | 18.0 | 18.4 | **-0.4** | -0.245/-0.275 (+0.030) | -0.258/-0.268 (+0.011) | -1.2 |

## Verdict inputs

- OOS eras (ex-HUL, pre-2026-only counted): 5 | spread>=8pp in 0 | dnet3>0 in 4 | dnet2>0 in 4
- crc halves (OOS-strict) spread>=8pp: [np.False_, np.False_] | dnet3>0: [np.True_, np.True_]
- OOS-strict pooled: spread -0.3pp (z=-1.4), dnet3 +0.025R, dnet2 +0.040R

## VERDICT — single-stock mirage. The crack is closed.

1. **The 16pp spread does not exist at scale.** Full universe (154,777 tagged
   signals): hit3 WITH 19.4% vs AGAINST 20.2% = **-0.8pp** (z=-3.7, wrong
   sign). OOS-strict (ex-HUL, pre-2026): **-0.3pp** (z=-1.4). Windows
   5/7/10/14 all land between -0.3 and -0.9pp — no window rescues it.
2. **It does not even reproduce where it was found.** HINDUNILVR 2026 under
   this engine: WITH 19.1% vs AGAINST 23.0% = **-3.9pp** (n=236). The original
   53%/37% came from a different post-hoc engine on 154 trades; under the
   ladder's stop/target/cost rules the discovery cell itself inverts.
3. **Verdict bar:** spread >=8pp in **0 of 5** OOS eras and **0 of 2** symbol
   halves (best era +0.3pp). dnet3>0 in 4/5 eras (+0.01..+0.05R) is
   composition, not signal - see (4) - and both arms stay deeply net-negative
   (WITH -0.17R, AGAINST -0.20R OOS pooled). Nothing is net-positive anywhere.
4. **The pooled "WITH slightly better net" is setup composition.** align7 is
   mechanically confounded with setup type: sweep_reclaim (worst net) is 93%
   AGAINST by construction (a reclaim fires after an adverse swing), bos_retest
   is 86% WITH. Within setups the spread is +0.5pp (fvg, bos), -3.2pp (ob),
   -5.5pp (sweep) - the only sizeable within-setup effects are *negative*.
5. **Not proxying SMA20 - both are dead.** phi(mom7, sma20-align)=0.045
   (near-independent). mom7 spread inside sma20 strata: -1.0 / -0.5pp; sma20
   spread inside mom7 strata: -1.3 / -0.8pp. Two dead filters, independently
   dead.

154 trades on one defensive largecap in one half-year window produced a 16pp
artifact; 154,777 trades on 138 symbols over 3 years show the true value is
~0 (slightly negative). This was the last live hypothesis of the
intermediate-TF program; it dies the same death as SMA20-align and M15-align.

---
Artifacts (scratchpad, `mom7_` prefix): `mom7_run.py`, `mom7_sigtags.parquet`
(per-signal align5/7/10/14). Reuses `l4_signals_h1.parquet` /
`l4_trades_h1.parquet` / `l4_master_h1.parquet` (see LADDER.md).
