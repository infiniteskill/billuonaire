# htf_nest / nest_depth — 40-STOCK DEEP STUDY (regime-split)

Data: `runs/validate/study40_2026/evidence.parquet` (44,042 firings, 40 stocks, 2026-06-19..07-17 single ~17d tape).
Regime labels: `dev/plan/47-40STOCK/_REGIME.md` (RANGE 21 / UPTREND 8 / DOWNTREND 11).
Outcome rule: WIN = `hit=='hit'`, LOSS = `hit=='loss'`, drop `na`+`undecided`. REALIZED EDGE = mean(win) − mean(b_hit) over the cell.

**TL;DR** — Three claims tested at scale:
1. **F1 htf_nest anti-signal** → **REPLICATES but HETEROGENEOUS** (pooled −4.7pp, 23/39 stocks negative; the real mechanism is *baseline over-selection*, not a clean −8..−28pp fade).
2. **depth-2 vs depth-3** → **UNTESTABLE / dead knob** (only 3 of 1,385 firings are depth-3; the wired conviction output is a near-constant 0.667).
3. **Full depth ladder (recomputed HTF-alignment-depth)** → the range-vs-trend framing is **REFUTED**; what actually replicates is a **UP-vs-DOWN directional sign-flip**: HTF-aligned entries pay **+10.5pp in UPTREND, +2.7pp (ns) in RANGE, −8.5pp in DOWNTREND** (both trend cells significant, z=+3.2 / −3.6).

---

## Context — what htf_nest does to the base population

| population | n | win | b_hit | **edge** |
|---|---|---|---|---|
| base retest (ob_taught+fvg_n+fvg+wyckoff) | 22,903 | 49.8% | 40.3% | **+9.5pp** |
| **htf_nest** | 1,364 | 47.2% | **51.9%** | **−4.7pp** |
| all decided firings | 38,462 | 49.8% | 42.3% | +7.4pp |

htf_nest fires on setups whose **baseline hit-prob is the 61st percentile** of all firings (0.519 vs population 0.423). It takes a +9.5pp base-retest edge, filters to the **higher-baseline (more "obvious") subset, and turns it into −4.7pp.** The nesting filter is **anti-selective**: it selects setups the baseline already prices in, then under-delivers them.

---

## PART 1 — F1 ANTI-SIGNAL (htf_nest, directly in parquet)

### Per-regime (pooled)
| regime | n | win | b_hit | **edge** |
|---|---|---|---|---|
| UPTREND | 246 | 44.3% | 52.9% | **−8.6pp** |
| RANGE | 782 | 48.8% | 51.6% | **−2.7pp** |
| DOWNTREND | 336 | 45.5% | 51.9% | **−6.4pp** |
| **ALL** | 1,364 | 47.2% | 51.9% | **−4.7pp** |

The anti-signal is **NOT worse in trend-vs-range in the claimed direction** — it is *worst in UPTREND* and *mildest in RANGE*. The common thread across all regimes is the **elevated b_hit (~0.52) with sub-baseline realized win**.

### Per-stock (edge = win − b_hit, pp)
**UPTREND** (pooled −8.6pp): BAJFINANCE −29.1 (n27), APOLLOHOSP −28.9 (n19), BIOCON −19.6 (n60), DLF −1.3, ABB +2.3, AARTIIND +3.2, TITAN +4.2, BAJAJ-AUTO +6.1.
**RANGE** (pooled −2.7pp): BAJAJFINSV −25.7 (n21), ADANIPORTS −24.4 (n27), ADANIENT −15.6 (n88), HAVELLS −10.5, COFORGE −7.6, ALKEM −7.4, APOLLOTYRE −7.3, BHARATFORG −6.4, AUBANK −5.0, BEL −1.8, CHOLAFIN −1.0, BHARTIARTL +0.4, COLPAL +0.5, AUROPHARMA +2.4, ASIANPAINT +5.2, BPCL +6.9, VOLTAS +8.8, BOSCHLTD +13.0 (n5), CIPLA +21.8 (n14), DABUR +25.2 (n21).
**DOWNTREND** (pooled −6.4pp): BERGEPAINT −43.7 (n4), CGPOWER −40.0 (n7), ADANIPOWER −27.3 (n24), BANKBARODA −24.2 (n6), CROMPTON −17.5 (n50), COALINDIA −10.0, ASHOKLEY −4.9, BALKRISIND −2.7, CANBK +2.1, ABFRL +6.5, AXISBANK +11.2.

**Breadth:** 23/39 stocks negative, 13/39 below −8pp, median stock edge −2.7pp. The strong per-stock negatives (−20..−44pp) are concentrated in **low-n cells** (n≤27); the large-n stocks cluster near 0.

**VERDICT F1: REPLICATES (pooled negative) but HETEROGENEOUS** — it is a majority-negative tendency, not the universal −8..−28pp fade from HAVELLS/HUL. Mechanism = **baseline over-selection**, not a mean-reversion fade.

---

## PART 2 — DEPTH-2 vs DEPTH-3 within htf_nest (strength 0.667 vs 1.0)

| depth | strength | n | win | b_hit | edge |
|---|---|---|---|---|---|
| 2 | 0.667 | 1,361 | 47.1% | 51.9% | −4.8pp |
| 3 | 1.000 | **3** | 100% | 33.3% | +66.7pp |

**Only 3 of 1,385 htf_nest firings reach depth-3.** The split is **DEGENERATE — UNTESTABLE.**

**Why (code cause):** depth-3 requires a same-direction parent on *all three* of 15m+1h+1d. On a ~16-bar daily tape, D1 almost never seats both a confirmed high and low pivot, so the 1d tier is effectively absent → depth caps at 2. With the live `min_depth=2` gate + `strength=min(1, nest_depth/3)` (`app/trader/detectors/htf_nest.py:80`), **99.8% of firings emit the identical strength 0.667.** The conviction output is a **DEAD KNOB** — this is F6 (confidence-blind) proven at the code level for htf_nest specifically.

---

## PART 3 — FULL DEPTH LADDER (recomputed offline)

`htf_nest` depth is not in the parquet (only depth≥2 rows survive). I **recomputed an HTF-alignment-depth** for every base retest firing (ob_taught/fvg_n/fvg/wyckoff, LONG/SHORT, decided; n=22,903), porting the extremes zigzag verbatim from `app/trader/detectors/extremes.py` (leg_pct=6.0 TUNE-frozen, Wilder ATR14, wick bands) onto raw 1m resampled to **15m / 1h / 1d** (the three tiers above a 5m base, matching htf_nest's `htf_order`).

Two parent definitions were tried:
- **(a) EXT-band overlap** (faithful to `_overlaps(z.zone, b.zone)`, EXT_L for LONG / EXT_H for SHORT): **near-zero — 22,663/22,903 at depth-0.** Retest zones are too tight to overlap narrow HTF wick bands. *Finding:* htf_nest's live depth is carried almost entirely by **OB/FVG parents ("OB inside OB")**, not the taught EXT anchor — the extreme-anchored nest rarely seats at retest-zone scale.
- **(b) HTF premium/discount alignment** (the "HTF-alignment-depth" of memory): at each tier, price on the **trade's side** of that tier's current dealing range (LONG in discount rp≤0.5 / SHORT in premium rp≥0.5). depth = # of higher TFs aligned (0..3). **This is the populated ladder used below.**

**Availability caveat:** only **5,275/22,903 (23%)** of firings had ≥1 HTF dealing range at fire-time (thin tape; D1 rarely seats). Ladder is computed on that navail≥1 subset. depth-0 within navail≥1 = "HTF range exists but price is on the *wrong* side of all of them."

### Binary HTF-alignment (aligned = depth≥1), navail≥1, per regime
| regime | aligned n / win | not-aligned n / win | **Δ (aligned−not)** | z | per-stock (≥10/side) |
|---|---|---|---|---|---|
| **UPTREND** | 453 / 51.4% | 445 / 40.9% | **+10.5pp** | **+3.17** | **4 pos / 1 neg** |
| RANGE | 1,164 / 52.9% | 1,436 / 50.2% | +2.7pp | +1.38 (ns) | 8 pos / 4 neg |
| **DOWNTREND** | 878 / 42.5% | 899 / 50.9% | **−8.5pp** | **−3.57** | 2 pos / **4 neg** |

**The sign flips with TREND DIRECTION**, significant in both trend cells, mixed/insignificant in range.
- UPTREND: buying HTF-discount pullbacks / (net) aligning to the trend **pays** — deeper is better (monotone, below).
- DOWNTREND: being "at your side of the HTF extreme" **loses −8.5pp** — the aligned extreme gets **held/broken, not swept-and-reversed** (HELD-EXTREME confirmed at scale). Buying discount in a downtrend = knife-catch.
- RANGE: weak, not significant, and NOT monotone-rising.

### Full ladder 0/1/2/3 (edge = win − b_hit), navail≥1
| regime | d0 | d1 | d2 | d3 | shape |
|---|---|---|---|---|---|
| UPTREND | 40.9% / +6.3 | 50.4% / +9.8 | 56.9% / +7.2 | — | **RISES monotone** |
| RANGE | 50.2% / +7.7 | 55.7% / **+13.4** | 51.5% / +9.3 | 45.2% / **+0.6** | **HUMP — peaks d1, decays to 0 by d3** |
| DOWNTREND | 50.9% / +9.6 | 40.4% / +3.6 | 22.2%(n9) | 61.7%(n94)/+18.6 | **INVERTS at d1 (noisy tail)** |

### Detector robustness (aligned−not Δ, navail≥1)
| regime | ob_taught | fvg_n | fvg | wyckoff |
|---|---|---|---|---|
| UPTREND | −8.0 (thin) | +5.3 | **+17.4** | **+17.8** |
| RANGE | +1.8 | −0.5 | −3.1 | **+13.4** |
| DOWNTREND | **−16.9** | −0.4 | **−9.9** | **−14.6** |

The DOWNTREND inversion and the UPTREND lift **replicate across independent detectors** (fvg + wyckoff carry both; fvg_n is flat). Not a one-detector artifact.

**VERDICT PART 3:**
- "Rises monotone in RANGE, inverts in TREND" (HAVELLS/HUL) → **REFUTED at scale.** Monotone-rise is an **UPTREND** phenomenon; RANGE is **hump-shaped** (peaks at shallow depth-1 +13.4pp, *decays to ~0 by depth-3* — deep multi-TF alignment pins price at a shared extreme that fails); DOWNTREND **inverts**.
- What REPLICATES (all-40, both trend regimes significant): **a directional sign-flip — HTF-alignment is an edge WITH an uptrend and an anti-edge AGAINST a downtrend.** The discriminating axis is **trend direction, not range-vs-trend.**

---

## THE BUG / TUNE the wired system implies

`app/trader/detectors/htf_nest.py`:

1. **Regime-blind (primary bug).** `detect()` emits a NEST from same-direction *containment* (`_PAR_BULL`/`_PAR_BEAR`, `_overlaps`) with **zero trend context** (line 64-85). But the realized sign of "HTF-aligned" **flips +10.5pp (up) / −8.5pp (down)**. A regime-blind detector **averages the two into net −4.7pp mush.** → *Fix:* conjoin with the D1 trend — take HTF-aligned entries **with** the daily trend (continuation), **suppress/invert counter-trend** (do not buy discount in a downtrend; require sweep+BOS reversal at the extreme, per HELD-EXTREME).

2. **Dead conviction knob (F6, code-level).** `strength=min(1.0, len(tiers)/3)` under `min_depth=2` on a ~16-bar D1 tape ⇒ 99.8% of firings emit **strength 0.667** (only 3/1385 reach depth-3). Depth carries **no** usable conviction as wired. → *Fix:* stop using depth as a monotone conviction multiplier; either drop the gate or use depth as a **regime-conditioned** feature (deep-alignment is good in UPTREND, ~0 in RANGE at depth-3, bad in DOWNTREND).

3. **Anti-selective nesting.** The parent-containment filter selects **high-b_hit "obvious" levels** (b_hit 0.519 vs base 0.403) and **destroys** the base-retest +9.5pp edge → −4.7pp. The taught EXT anchor barely participates (EXT-overlap depth ≈ 0 at retest scale); depth is effectively "OB-inside-OB" clustering. → *Fix:* the nest must gate on **HTF premium/discount side conjoined with trend**, not raw zone overlap; that alignment carries a real, sign-stable-within-regime edge (+10.5 up / −8.5 down) that the current overlap-nesting does not.

4. **Thin-tape structural note:** HTF nesting is under-seated — only 23% of firings even have an HTF dealing range, and D1 (the tier that would make depth-3) almost never seats on 16 daily bars. Any depth-≥3 gate is **inert on this tape**; validate depth on a longer history before trusting it.
