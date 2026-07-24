# 40-STOCK DEEP STUDY — Failed-trade forensics, regime-split

**Data**: `runs/validate/study40_2026/evidence.parquet` — 44,042 firings, 40 symbols, one 17-day tape (2026-06-19..07-17).
**Decided set** (WIN=`hit=='hit'`, LOSS=`hit=='loss'`, dropped na+undecided): **n=38,462**.
Regime labels from `dev/plan/47-40STOCK/_REGIME.md` (UP 8 / RANGE 21 / DOWN 11 stocks). **COARSE — one regime snapshot, thin tape; treat trend labels as provisional.**

Method: rank-based (Mann-Whitney) **AUC** of each ex-ante feature for WIN vs LOSS, per regime bucket. `b_hit` = per-row baseline hit-prob (the pipeline's own prior). **REALIZED EDGE = mean(win) − mean(b_hit)** per cell. Outcome columns (fwd*/mfe/mae) are used only as descriptive sanity, never as predictors (leakage).

---

## HEADLINE

| | n | win | b_hit | **EDGE** |
|---|---|---|---|---|
| ALL | 38,462 | 0.498 | 0.423 | **+0.075** |
| UP | 7,233 | 0.491 | 0.420 | +0.071 |
| RANGE | 20,592 | 0.501 | 0.422 | +0.079 |
| DOWN | 10,637 | 0.497 | 0.426 | +0.070 |

Raw win-rate is a **coin-flip (~0.498)** in every regime. The system nets +0.075 edge **entirely from `b_hit` ranking**, not from any detector geometry.

---

## 1. AUC of every feature, per regime  (win=1; `[|AUC−.5|]` = discriminative power)

| feature | ALL | UP | RANGE | DOWN | verdict |
|---|---|---|---|---|---|
| **b_hit** | **0.760** | **0.761** | **0.758** | **0.764** | **UNIVERSAL separator** |
| strength | 0.497 | 0.483 | 0.500 | 0.501 | blind, all regimes |
| atr | 0.501 | 0.505 | 0.497 | 0.502 | blind |
| zone-width /atr | 0.493 | 0.498 | 0.489 | 0.497 | blind |
| zone-width /price% | 0.488 | 0.490 | 0.485 | 0.492 | blind |
| price-pos in zone (`ppos`) | 0.479 | 0.494 | 0.486 | **0.456** | **DOWN-only** (+mild RANGE) |
| price-pos, direction-signed | 0.505 | 0.510 | 0.507 | 0.496 | blind |
| hour-of-day | 0.512 | 0.504 | **0.521** | 0.500 | **RANGE-only**, weak |
| is_SHORT | 0.531 | 0.511 | 0.526 | **0.553** | regime-conditional (see §4) |
| is_LONG | 0.469 | 0.489 | 0.474 | **0.447** | loser-marker, grows into DOWN |

**The ONE universal separator = `b_hit`** (AUC ~0.76, flat across UP/RANGE/DOWN). Everything the system could *gate* on — strength, ATR, zone-width, stacking — is **noise (AUC 0.49–0.50) in every regime.** This is F6, replicated at 40-stock scale and **stronger** than the HAVELLS/HUL estimate (0.74).

`b_hit` AUC per stock: **0.715–0.820, and >0.5 in all 40/40 stocks.** Within every detector it still separates (compression 0.89, wyckoff 0.82, orderblock 0.78, fvg 0.74, fvg_n 0.71, ob_taught 0.67, htf_nest 0.61) — so it is a genuine per-firing signal, not a detector-ID proxy.

---

## 2. THE `b_hit` PARADOX — universal anti-calibration (the central bug)

`b_hit` ranks WIN (higher b_hit → higher raw win) but is **systematically over-confident at the top and under-confident at the bottom, identically in every regime:**

| b_hit decile | n | mean b_hit | win | EDGE |
|---|---|---|---|---|
| ≤0.15 | 12,101 | 0.03 | 0.234 | **+0.204** |
| 0.15–0.25 | 3,524 | 0.23 | 0.394 | +0.170 |
| 0.25–0.40 | 4,814 | 0.35 | 0.468 | +0.120 |
| 0.40–0.50 | 3,084 | 0.48 | 0.542 | +0.066 |
| 0.50–0.65 | 4,413 | 0.60 | 0.610 | +0.013 |
| 0.65–0.80 | 3,796 | 0.75 | 0.695 | **−0.054** |
| >0.80 | 6,730 | 0.96 | 0.842 | **−0.121** |

Anti-calibration by tercile is **REPLICATES-ALL** (edge, LOW / HIGH b_hit): UP +0.197 / −0.091 · RANGE +0.205 / −0.084 · DOWN +0.197 / −0.092.

**Consequence — two objectives point opposite ways:** to maximize raw hit-rate, take high-b_hit; to maximize **alpha over baseline, take LOW-b_hit taught firings.** The realized +0.075 comes from the bottom; the top **destroys** edge. (The imperfect calibration also proves b_hit is a real ex-ante prior, not outcome leakage — a leak would be AUC≈1.)

---

## 3. Per-detector edge (where alpha lives / dies) — universal ordering

| detector | n | win | b_hit | EDGE |
|---|---|---|---|---|
| **htf_nest** | 1,364 | 0.472 | **0.519** | **−0.047** |
| compression | 2,550 | 0.490 | 0.490 | −0.000 |
| wyckoff | 6,972 | 0.504 | 0.446 | +0.058 |
| sweep | 1,948 | 0.522 | 0.460 | +0.062 |
| orderblock | 9,074 | 0.498 | 0.434 | +0.064 |
| fvg | 6,384 | 0.496 | 0.408 | +0.088 |
| propulsion2 | 623 | 0.501 | 0.388 | +0.113 |
| fvg_n | 7,658 | 0.495 | 0.369 | +0.126 |
| **ob_taught** | 1,889 | 0.492 | **0.361** | **+0.131** |

Grouped, per regime (edge):

| group | UP | RANGE | DOWN |
|---|---|---|---|
| TAUGHT (fvg_n, ob_taught, propulsion2) | +0.115 | +0.126 | +0.136 |
| BASE (ob, fvg, wyckoff, sweep, compression) | +0.060 | +0.067 | +0.054 |
| **NEST (htf_nest)** | **−0.086** | **−0.027** | **−0.064** |

**F1 htf_nest anti-signal = REPLICATES-ALL.** htf_nest is the **only negative-edge detector**, carries the **highest b_hit (0.519)**, and is negative in every regime (worst in UP −0.086). Its `strength` is flat 0.667 (depth-2) for 1,361/1,364 rows — the depth-2-vs-3 proxy can't split (only 3 depth≥3 rows). As-fired, nesting is a **universal veto candidate, not a gate.** TAUGHT > BASE > NEST ordering holds in all three regimes.

---

## 4. DIRECTION — the regime-conditional lever that INVERTS

Winrate & edge by direction × regime:

| regime | LONG win | LONG edge | SHORT win | SHORT edge |
|---|---|---|---|---|
| UP | 0.480 | +0.058 | 0.503 | +0.086 |
| RANGE | 0.475 | +0.076 | 0.527 | +0.083 |
| DOWN | **0.443** | +0.057 | **0.549** | +0.083 |

- SHORT edge is a **near-constant +0.08 in all regimes** (mild universal short-tilt, AUC 0.53).
- The **absolute** direction spread is **regime-conditional and inverts**: LONG win collapses 0.480→0.443 into DOWN; SHORT climbs 0.503→0.549.
- **Per-stock inversion (the clean evidence):** SHORT beats LONG in **11/11 DOWN stocks** (ABFRL 0.394→0.575, CGPOWER 0.403→0.535, CANBK 0.438→0.572), and in most RANGE — **but LONG beats SHORT in the strongest uptrends** (DLF 0.519 vs 0.469, BAJFINANCE 0.510 vs 0.468, TITAN 0.492 vs 0.441). SHORT>LONG overall only 30/40.

**"Range-fade inverts in trend" = CONFIRMED at the direction level.** The wired system fires LONG/SHORT symmetrically with **no regime-direction gate** → it keeps taking **counter-trend longs in downtrends**, the single biggest per-regime loser marker.

---

## 5. Secondary regime-conditional levers

**Price-position in zone (`ppos`) — DOWN-only.** Win by `ppos` quartile (low→high):
- UP: 0.501 / 0.494 / 0.487 / 0.482 (flat — ABSENT)
- RANGE: 0.523 / 0.504 / 0.489 / 0.486 (mild)
- **DOWN: 0.547 / 0.512 / 0.469 / 0.447** (10pp spread). In downtrends, firings priced at the **bottom** of their zone win; at the **top** lose.

**Hour-of-day — RANGE-only.** RANGE: 9–11h ~0.47 vs 11–15h ~0.51–0.525 (avoid the open). UP/DOWN flat.

---

## 6. MFE/MAE symmetry — the coin-flip signature (fade thesis, replicated)

| regime | WIN mfe / mae | LOSS mfe / mae | win-mfe ≈ loss-mae |
|---|---|---|---|
| UP | 3.36 / 1.37 | 1.49 / 3.19 | Δ0.18 |
| RANGE | 3.23 / 1.43 | 1.49 / 3.22 | Δ0.01 |
| DOWN | 3.33 / 1.51 | 1.51 / 3.35 | Δ0.03 |

Excursions are **mirror-image** across win/loss (median mfe/atr ≈ mae/atr ≈ 0.64). Combined with the ~0.498 win-rate, **entries carry no directional excursion edge** — the outcome is purely which barrier is tagged first. Detector geometry adds nothing; `b_hit` is the sole ranker. This **REPLICATES the falsified-fade / symmetric-excursion finding** at 40-stock scale.

---

## LOSER SIGNATURES (winner−loser feature deltas confirm)

- **UP loser** — `LOW b_hit` and nothing else. b_hit W0.581/L0.265 (Δ+0.316); every other feature |Δ|<0.03 (direction is a wash, 0.542 vs 0.520 long-share). Plus: **htf_nest firings** (worst regime for nest, −0.086). *Signature: high-prior "obvious" setup that fails; taught low-b_hit longs are fine here.*
- **RANGE loser** — `LOW b_hit` + **LONG-leaning** (loser long-share +5.2pp) + **priced at top of zone** + **fired 9–11h**. *Signature: early-session counter-move long at zone top.*
- **DOWN loser** — `LOW b_hit` + **LONG** (loser long-share **+10.6pp**, LONG win 0.443) + **high `ppos`** (price at top of zone, win 0.447). *Signature: counter-trend long chasing into the top of a decisional zone in a downtrend.*

Universal loser core in ALL regimes: **b_hit ≈ 0.27** (vs winners ≈ 0.58). Regime adds the direction/position overlay, heaviest in DOWN.

---

## HYPOTHESIS SCORECARD

| # | Hypothesis | Verdict | Evidence |
|---|---|---|---|
| F1 | htf_nest anti-signal (high b_hit / low win) | **REPLICATES-ALL** | only −edge detector (−0.047), b_hit 0.519 highest; −0.086/−0.027/−0.064 UP/RANGE/DOWN |
| F6 | confidence blind — strength/width/stacking AUC~0.47, only b_hit predicts | **REPLICATES-ALL (stronger)** | b_hit AUC 0.76 (40/40 stocks); strength/atr/width AUC 0.49–0.50 every regime |
| F3 | tiny-wick stop shaken ~70%, +0.25ATR = +12pp | **NOT-TESTABLE here** | no SL/stop column; `mae` is full-window excursion (median 0.64 ATR), not stop-relative — needs tradebook (not run) |
| — | nest_depth discriminator inverts on trend | **UNRESOLVED** | depth ladder not in parquet (htf_nest ≥depth2 only; strength flat 0.667). As-fired nest anti-signal is UNIVERSAL, not range-only |
| — | range-fade INVERTS in trend (direction) | **CONFIRMED (regime-conditional)** | SHORT>LONG 11/11 DOWN stocks; LONG>SHORT in strongest uptrends |
| — | fade / symmetric MFE-MAE, sub-edge entries | **REPLICATES-ALL** | mirror excursions win-mfe≈loss-mae (Δ≤0.18), win-rate 0.498 |

---

## BUGS / TUNES (mechanism → fix)

1. **`b_hit` is anti-calibrated at the top, identically in every regime** (over-confident >0.65, under-confident ≤0.4). Mechanism: the baseline prior rewards "textbook-obvious" high-prior setups (led by htf_nest) that then underperform, and starves the taught detectors that overperform. **Tune:** recalibrate `b_hit` (isotonic/Platt — shrink top, lift bottom); select for **alpha** on LOW-b_hit taught firings, not high raw hit-rate.
2. **htf_nest is a universal anti-signal**, not a confirmation. **Tune:** demote nesting from a positive gate to a **veto/ignore**; never let it raise conviction.
3. **`strength` is near-constant within each detector** (htf_nest 0.667 flat, most detectors single-valued) → it is a detector-ID in disguise, AUC 0.50. Zone-width and ATR likewise blind. **Tune:** stop gating on strength / zone-width / ATR in every regime; they don't separate win from loss.
4. **No regime-direction gate.** LONG is a structural loser in DOWN (win 0.443, +10.6pp loser-share) and the direction edge inverts by regime. **Tune:** suppress counter-trend longs in DOWN / counter-trend shorts in UP; the largest single per-regime lever after b_hit.
5. **Regime-conditional add-ons:** in DOWN, veto high-`ppos` firings (price at zone top, win 0.447); in RANGE, discount the 9–11h open. Secondary but free.

**Caveat:** one 17-day tape, coarse D1 regime labels, ADX can't seat. Verdicts are directionally strong (40/40 and 11/11 replications) but not multi-regime-validated.
