# PINE RE-AUDIT — zone/block concepts vs the original TradingView scripts

Date: 2026-07-18. Research only — no production code touched.
Sources of truth: `dev/h2h/{1,2,3,pinescripts,CHECKLIST}.txt` + validated ports in `dev/research/`.
Code: scratchpad `pine_lib.py` / `pine_det.py` / `pine_run.py` / `pine_stats.py`;
raw rows `pine_rows_{5m,h1}.parquet`, aggregates `pine_agg_{5m,h1}.csv` (copied here).

**Datasets** — (a) `data/long5m` 5m x 57 trading days x 137 syms (NIFTY excluded), intraday;
(b) scratchpad `l4_h1.parquet` H1 x 3y (2023-08→2026-07) x 137 syms, continuum, splice-segmented.

**Method (locked)** — hit-edge = P(MFE≥1·ATR before MAE≥1·ATR, 24-bar walk, same-bar→loss,
undecided→miss) minus a 20-draw crc32-seeded random baseline from the same bucket (5m: same
session + same 30-min bucket, `study.py` convention; H1: same segment + same hour). ATR =
trailing SMA-TR14. Econ = k=1.5 `fixed_t1`/`fixed_t3`: 5m via `dev/research/step2_engine.simulate`
verbatim (MIS intraday costs, path to EOD); H1 via the `l4_econ.py` delivery sim (adapted only for
a target-mult param; gap-through-stop, 40-bar time stop, 0.104% notional + Rs15). Events deduped
5 bars per (detector, dir). Holdouts: temporal (ts > dataset mid) + crc32(sym)%2==1.

---

## 1. INVENTORY — every zone/block/structure concept in the h2h Pines

Scripts: **1.txt** = Liquidity Pools [LuxAlgo] + Fair Value Gap [LuxAlgo] (dedicated);
**2.txt** = MSB-OB (EmreKb) + Market Structure CHoCH/BOS Fractal [LuxAlgo] + TFlab Market
Structure Inducements ICT + Market Structure with Inducements & Sweeps [LuxAlgo];
**3.txt** = MTF BOS & MSS (Lenny_Kiruthu) + Market Structure Zig-Zag/BoS/Supply-Demand/Inflection
(The_Forex_Steward); **pinescripts.txt** = Smart Money Concepts [LuxAlgo] + Smart Money Breakout
Channels [AlgoAlpha] + Liquidity Swings [LuxAlgo] (duplicated); **CHECKLIST.txt** = concept list.

| Concept | Pine rule (source) | Our impl | Divergence | Verdict |
|---|---|---|---|---|
| OB internal/swing | SMC: pivot via one-sided `leg(size)`; OB = bar with extreme *parsed* low/high in [pivot, close-crossover break]; hi-vol bar (range ≥ 2×ATR200 or cum-TR-mean) gets H/L swapped; mitigation close or wick past bar edge | `ob_lux.py` (validated port of `luxob.py`) | Port uses per-bar trailing TR14 ATR, Pine uses ATR200/cum-TR — deliberate, parity-gated vs the *measured* winner | Faithful to validated port; ATR-period departs from raw Pine (flagged, not re-opened — port was the A/B winner) |
| OB (displacement) | — (no Pine source; our own rule) | `orderblock.py` | n/a | Production-only variant |
| OB (EmreKb MSB-OB) | zigzag(9) swings, MSB confirmed at 0.33 fib; OB = last opposite candle between prior swings; alert on close in zone; dies close beyond | was MISSING → built `brk_ob` | — | 5m hit-edge **+15.0** (val +13.8/crcB +13.4), net −0.28R; H1 −1.9. Detects, doesn't pay |
| **Breaker block** | EmreKb: same MSB; BB = last same-direction candle in [older-swing−9 .. prior swing] **when the swing was swept** (bull l0<l1 / bear h0>h1); entry = close in box | our `breaker.py` = level-inversion retest (different rule, prior −7%) → Pine-exact built as `brk_bb` | Ours is not the Pine rule at all | 5m **+19.6** (val +21.2/crcB +19.4) — best hit-edge in audit, overturns −7% on detection; net −0.27..−0.33R; H1 −2.2. See §4 |
| Mitigation block | EmreKb MB = same box when swing NOT swept; ICT body-zone variant in `ict_pieces.py` | `mitigation.py` (ict_pieces port) + Pine-exact `brk_mb` built | Two different "mitigation" rules coexist | `brk_mb` 5m +17.1 / H1 −0.6; net negative |
| FVG (dedicated Lux) | gap + middle-candle **close beyond** origin + gap% > auto-thr `cum((H−L)/L)/bar_index` | `fvg_cb.py` (port: cum from bar 2, ÷(i+1)) | Denominator off-by-one + start-index only | **A/B identical** (5m cehold +10.7 both; zones 17 419 vs 17 175). Port faithful in effect |
| FVG (SMC Lux) | threshold gates the **middle-candle body**: signed (C₁−O₁)/O₁ > 2×mean&#124;body%&#124; (`cum/bar_index×2`); gap size not filtered; wick-fill mitigation | not shipped → built `fvg_smc` | Semantically different filter (body vs gap) — the divergence flagged in the fvg_cb review actually belongs to the SMC script, not the dedicated FVG | SMC finds 2.4× more zones, only ~34% overlap, **lower** edge (+9.5 vs +10.7 cehold 5m; H1 −0.7 vs −1.2 ≈ both dead). Port wins |
| FVG (ours 0.3·ATR) | — | `fvg.py` | n/a | +9.5 cehold 5m at 3× events; H1 −0.7 |
| iFVG | no Pine defines it (CHECKLIST concept); inversion rule = close-fill then flip-retest (`ict_pieces.py`) | `fvg.py` IFVG event | — | Re-measured: 5m −4.1/−4.4 (confirms prior negative); H1 +0.5, val +0.1 ≈ flat. **Negative verdict stands** |
| BPR | no Pine source (CHECKLIST) | `bpr.py` (validated ict_pieces port) | n/a | Not re-opened |
| CE / consequent encroachment | no Pine source (CHECKLIST) | `fvg_cb.py` CE_HOLD (validated) | n/a | Covered |
| Swings/pivots | 3 Pine defs: SMC `leg(len)` **one-sided** (vs following bars only, alternating); `ta.pivothigh(n,n)` two-sided (TFlab/Lenny/LiqSwings); strict-monotonic fractal (Lux fractal, `dh==−p`) | `swings.py` strict two-sided N=3; research 2-2 fractal; `ob_lux` uses Lux one-sided ✓ | `swings.py` matches none exactly (strictest two-sided) | Downstream A/B (§3): pivot rule is **immaterial** — bos_retest edge identical across all three despite 2× density differences |
| BOS/CHoCH/MSS | SMC close-crossover of pivot with crossed-flag + trend bias; fractal script; TFlab pivot(30); Lenny MTF | `structure.py` (swing-mid crossover, 4-swing trend) | Formulation differs (zone-mid vs exact level) | All bos_retest variants: 5m −6, H1 ≈0 → no formulation of structure-break retest carries edge here |
| Inducement (IDM) | Lux Mkt Structure w/ Inducements & Sweeps | `inducement.py` faithful stateful port (parity-gated) | TFlab pivot-3 "Sweeps" variant not ported | Faithful; alternate variant noted only |
| Sweeps | Lux: wick past trailing max/min with close back, os-gated | `sweep.py` (level-state) + `turtle_soup.py` (validated +8.6) | Different mechanics, same concept | Covered |
| Liquidity Pools (1.txt) | multi-contact wick zones: ≥2 contacts, ≥5-bar gaps, 10-bar confirmation, zone merge, volume totals | **MISSING** (our `liquidity.py` does PDH/PDL/PWH/PWL/OR/ROUND/EQH-EQL instead) | Contact-counted wick-pool zones never ported | Not built here (out of the 6 mandated builds); all zone-entry families measured ≈0/negative on H1 — low expected value |
| Liquidity Swings (pinescripts) | `pivothigh(14)` wick-extremity zones + touch counts | **MISSING** (partial overlap w/ swings+liquidity) | — | Same note as pools |
| EQH/EQL | SMC: &#124;level−prev&#124; < 0.1×ATR200 on len-3 legs | `liquidity.py`: relative 0.001×price on confirmed swings | ATR-scaled vs price-relative tolerance | Real divergence, flagged; no Pine event semantics to A/B (labels only) |
| Premium/Discount/Equilibrium | SMC: trailing swing range bands (top/bottom 5%, 47.5–52.5 eq) | **MISSING** in production (no impl found) | — | Context feature, unimplemented |
| Strong/Weak High/Low | SMC trailing extremes | MISSING | — | Context labels only |
| Supply/Demand + Inflection zones | Forex_Steward: SMA-close breakout zigzag, zones from control swings; "Institutional OB" trigger = HTF opposite candle + close beyond | not ported verbatim | concept family covered by `orderblock`/`ob_lux` | Mapping only |
| Breakout channels | AlgoAlpha stdev-of-normalized-price channels | `compression.py` (own math) | different construction | Prior compression tests: no edge |
| Rejection/vacuum block | no Pine (CHECKLIST) | measured in `ict_pieces.py` (negative) | n/a | Closed previously |

## 2. PINE-EXACT FVG A/B (same retest/CE events on all variants)

Zones (whole dataset): port 17 419 / dpine 17 175 / smc 41 245 / ours03 71 182 (5m);
27 388 / 27 181 / 62 589 / 97 671 (H1). port∩smc only **34.7% / 33.1%** of union — genuinely
different zone populations, not a threshold rescale.

5m x 57d x 137 (n / edge / val / crcB / net_t1 / net_t3):

| det | n | edge | val | crcB | net1 | net3 |
|---|---|---|---|---|---|---|
| fvg_port_cehold | 13 133 | **+10.7** | +10.5 | +10.6 | −0.24 | −0.24 |
| fvg_dpine_cehold | 12 976 | +10.7 | +10.4 | +10.6 | −0.24 | −0.24 |
| fvg_smc_cehold | 22 679 | +9.5 | +9.1 | +9.4 | −0.26 | −0.26 |
| fvg_ours03_cehold | 37 706 | +9.5 | +9.1 | +9.4 | −0.27 | −0.28 |
| fvg_port_retest | 14 374 | +4.6 | +5.0 | +4.9 | −0.24 | −0.25 |
| fvg_dpine_retest | 14 186 | +4.7 | +5.0 | +4.8 | −0.24 | −0.25 |
| fvg_smc_retest | 26 728 | +2.6 | +2.8 | +2.3 | −0.25 | −0.26 |
| fvg_ours03_retest | 44 597 | +1.6 | +1.7 | +1.5 | −0.28 | −0.28 |

H1 x 3y x 137: every variant −1.4..−0.1 edge (port_cehold −1.2, smc_cehold −0.7, all val/crcB
same sign or noise), net −0.17..−0.24. **FVG zones have no edge at H1 horizon, any threshold.**

**Which finds better zones?** The shipped port (gap-size vs mean-bar-range filter). The literal
SMC body-based threshold admits 2.4× more zones at strictly lower per-event edge on 5m and is
equally dead on H1. The literal dedicated-Pine denominator (`/bar_index` vs port `/(i+1)`) is a
no-op (<2% zone diff, same edge to 0.1pp). No adoption.

## 3. SWINGS / PIVOT PARITY

Pivot counts (both sides): frac22 148k / prod33 98k / lux5 76k (5m); 191k / 136k / 93k (H1) —
up to 2× density spread. Downstream bos_retest (break+retest FSM held constant):

| | 5m edge (val/crcB) | H1 edge (val/crcB) | net3 5m/H1 |
|---|---|---|---|
| bos_frac22 (research 2-2) | −5.9 (−5.8/−6.1) | −0.2 (−0.8/+0.2) | −0.30/−0.21 |
| bos_lux5 (SMC one-sided leg) | −6.4 (−6.2/−6.1) | −0.3 (−1.5/−0.5) | −0.30/−0.19 |
| bos_prod33 (production strict 3-3) | −6.3 (−6.2/−6.3) | +0.1 (−0.8/+0.7) | −0.30/−0.20 |

Production `swings.py` (strict two-sided) matches no Pine definition; `ob_lux` already uses the
Pine-exact one-sided leg. **The divergence does not matter**: swapping the pivot definition moves
downstream zone quality by <1pp everywhere. No parity fix warranted on measurement grounds.

## 4. BREAKER PER PINE (EmreKb MSB-OB, the only h2h script defining BB)

Pine-exact zigzag(9) + 0.33-fib MSB + boxes; entry = first close inside box after creation.

| | n 5m | edge | val | crcB | net1 | net3 | n H1 | edge H1 |
|---|---|---|---|---|---|---|---|---|
| brk_bb (breaker) | 1 437 | **+19.6** | +21.2 | +19.4 | −0.27 | −0.33 | 1 792 | −2.2 |
| brk_mb (mitigation) | 2 590 | +17.1 | +18.0 | +16.8 | −0.25 | −0.27 | 2 931 | −0.6 |
| brk_ob (MSB order block) | 5 229 | +15.0 | +13.8 | +13.4 | −0.28 | −0.30 | 5 903 | −1.9 |

The Pine breaker **beats our −7% implementation decisively on detection** (5m, sign-stable across
both holdouts, n=1.4k) — our `breaker.py` (inverted-level retest) is simply a different, worse
rule. But at k=1.5 fixed t1/t3 with real MIS costs it still loses ~0.3R/trade, and on H1 the same
rule is *negative*. Detection quality ≠ tradable edge. (Deviations from Pine kept honest: current
l0i/h0i instead of the 9-bar-lagged `valuewhen` copy; broken box deletes itself — Pine's
`f_delete_box` pops the oldest box, a bug not replicated.)

## 5. PROPULSION BLOCK (not defined in any h2h txt → standard ICT def)

Tap of a live displacement-OB + close beyond it → block = tapping candle; entry on block retest.
5m: n=9 397, edge −2.2 (val −2.0/crcB −2.3), net −0.28/−0.31. H1: n=11 411, edge +0.6
(val +1.3/crcB +0.8) — sub-noise, net −0.21/−0.17. **Nothing there.**

## 6. iFVG RE-VERIFY (H1 x 3y, fresh data + longer TF)

ifvg_ours03 H1: n=37 722, edge +0.5 (val +0.1, crcB +0.5), net −0.21/−0.17.
ifvg_dpine H1: n=11 415, edge +0.5 (val +0.1, crcB +0.8), net −0.20/−0.19.
5m re-run: −4.4 / −4.1. **Prior negative verdict CONFIRMED, not overturned** — at best flat on
H1, still negative intraday, never net-positive.

---

## VERDICT

**(a) Is our detection faithful to the Pines where it matters?** Mostly yes. `fvg_cb` ≡ the
dedicated Lux FVG in effect (A/B identical); `ob_lux` and `inducement` are faithful ports of
their scripts; the flagged fvg_cb threshold "divergence" is real but belongs to the *SMC* script's
FVG — a different indicator — and the Pine-exact SMC rule measures *worse*. Genuine unfaithful
spots: `breaker.py` is not the Pine breaker (the Pine one detects far better — see (b));
`swings.py` matches no Pine pivot rule (measured immaterial); EQH/EQL tolerance is price-relative
vs Pine's ATR-scaled; Liquidity-Pools contact zones, Liquidity-Swings zones and Premium/Discount
zones were never ported (context features, unbuilt).

**(b) Does any Pine-exact variant or missing block measurably beat the shipped set or clear
zero?** On *detection* (hit-edge): yes — the EmreKb breaker family is the single biggest find
(brk_bb +19.6pp on 5m, sign-stable, vs our breaker's historical −7%), and Pine-exact ded-FVG ties
the shipped port (+10.7 cehold). On *money* (k=1.5 fixed_t1/t3, realistic costs): **no. Nothing
clears zero.** Every one of the 17 detector-events on both datasets nets −0.1..−0.33R. On H1x3y
every zone/block concept in this audit is edge-dead (±1pp) before costs even apply.

**(c) What to adopt?** Nothing into the trading path — no measured rule earns net money under the
locked cost model, consistent with every prior campaign. Two bookkeeping adoptions worth making if
the CAGE→TRAP confluence layer ever wants stronger *ingredients*: (1) replace/augment
`breaker.py`'s inversion rule with the EmreKb MSB breaker as a confluence-only signal (it is the
strongest 5m hit-edge ingredient measured to date, ahead of turtle_soup +8.6); (2) keep `fvg_cb`
exactly as shipped — the Pine-exact alternatives are equal or worse. Do **not** build propulsion
or resurrect iFVG; both are closed with fresh negative/flat evidence on two datasets.
