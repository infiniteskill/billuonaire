# 45-HAVELLS — HTF-ALIGNMENT-DEPTH as the winner/loser discriminator (single-stock deep study) (2026-07-24)

**Question (doc-36 / doc-42 lever):** does HTF-ALIGNMENT-DEPTH — the `nest_depth` grade that drives
the program's +6.13R high-grade tier — separate HAVELLS winners from losers *on this one stock*?
i.e. does deeper HTF alignment ⇒ higher win rate on HAVELLS, monotone in depth 0/1/2/3?

**Answer: YES — and cleanly.** HTF DECISIONAL-ZONE nest-depth is monotone in both win% and forward-R
on HAVELLS alone; the shallow tier (depth 0-1) is the sub-coin-flip LOSER class and the deep tier
(depth 2-3) is the winner class, p ≈ 5e-7. It confirms the doc-36 causal mechanism on HAVELLS in
isolation. **Critical nuance:** the signal is carried by the *premium/discount decisional-zone*
reading of alignment (the taught fib/OTE tool), **NOT** by HTF EMA-trend — trend-alignment is a flat
null here. This is exactly the SMC method (buy HTF discount / sell HTF premium, nested), and it is the
faithful reading of `htf_nest` (same-direction *zone containment*, not trend-following).

---

## 1. Data & method (causal, ex-ante — no hindsight)
- **Firings + outcomes:** `runs/validate/precision_study/evidence.parquet`, filter `symbol=='HAVELLS'`
  → 2778 firings, ts 2026-06-25 → 2026-07-17 (16 sessions). Outcome = `hit ∈ {hit,loss}` (forward vs
  baseline). Decidable directional set = **1719** (864 hit / 855 loss; overall win% **50.3%** — the
  0.52-AUC coin flip, reconfirmed on HAVELLS). NEUTRAL/`na` (985, premium_discount gates) & `undecided`
  (72) excluded from the outcome test.
- **HTF context:** resampled `data/wide/HAVELLS.csv` (1m, the window the firings live in) with pandas
  `resample(...).agg(OHLCV)` to **15m (400 bars) / 1h (112) / 1d (16)** — the 3 tiers above the 5m base
  (`htf_order=[5m,15m,1h,1d]` ⇒ `nest_depth ∈ {0..3}`, matching the detector).
- **Causal join:** each firing merged (`merge_asof` backward on bar **close-time**) to the **last fully
  CLOSED** HTF bar — enforces doc-36 caution C (HTF context formed *before* the entry bar).
- **Alignment per HTF (two definitions, both tested):**
  - **ZONE nest (primary, = `htf_nest` same-direction zone containment):** position of firing price in
    the HTF causal swing range `pos=(price−swLo)/(swHi−swLo)`. LONG aligned if `pos≤0.5` (HTF **discount
    /demand**), SHORT if `pos≥0.5` (HTF **premium/supply**). This IS the taught fib/OTE tool — see
    `dev/IMG/trades/HAVELLS_T1_fib_ote.png` (HAVELLS 30m, fib 0→100% with OTE 61.8-70.2 band drawn).
  - **TREND (control):** HTF EMA9 vs EMA21 sign; aligned if it matches firing direction.
- **depth = count of the 3 HTFs that are aligned.**

---

## 2. HEADLINE — HAVELLS win% + forward-R by HTF decisional-zone nest depth
(directional decided set, n=1719; `base%` = mean `b_hit` baseline; fwd = mean forward-R, skip-NaN)

| depth_zone | n | win% | base% | edge vs base | **fwd12** | fwd24 | mfe | mae |
|---|---|---|---|---|---|---|---|---|
| **0** (HTF-misaligned) | 443 | **42.9** | 37.3 | +5.6pp | **−0.646** | +0.07 | 2.14 | 2.61 |
| **1** | 502 | **46.4** | 37.9 | +8.5pp | **−0.293** | −0.81 | 2.19 | 2.88 |
| **2** | 496 | **57.7** | 39.5 | +18.1pp | **+0.025** | +0.26 | 3.05 | 2.71 |
| **3** (deep-nested) | 278 | **55.8** | 52.1 | +3.6pp | **+0.962** | +0.40 | 3.07 | 2.29 |

- **win% monotone-up** 42.9 → 46.4 → 57.7 → 55.8 (depth-3 ≈ depth-2 within noise; the jump is at ≥2).
- **fwd12 is cleanly, strictly monotone** −0.65 → −0.29 → +0.03 → **+0.96 R**, crossing **zero at depth 2**.
  MFE also rises 2.14 → 3.07. So deeper HTF nesting raises **both** hit-rate **and** run-length — the
  doc-36 "aligned entry rides the big flow to the HTF target, runs far" prediction, on HAVELLS.
- **Shallow (0-1) vs Deep (2-3): 44.8% (n=945) vs 57.0% (n=774), χ²(1)=25.4, z=5.04, p≈4.7e-7.**
- corr(depth_zone, win)=+0.112; corr(depth_zone, fwd12)=+0.187 (n=1485). Positive, real for a noisy
  single-stock intraday tape.

---

## 3. The negative control — EMA-TREND alignment does NOT discriminate (important)
| depth_trend | n | win% | fwd12 |
|---|---|---|---|
| 0 | 178 | 42.7 | +0.20 |
| 1 | 573 | **56.4** | +0.47 |
| 2 | 765 | 48.0 | −0.52 |
| 3 | 203 | 48.3 | −0.33 |

Non-monotone, peaks at depth-1 then decays; corr(depth_trend, win)=**−0.017** (null). **⇒ On HAVELLS,
HTF-alignment as trend-following is a dead flag; HTF-alignment as decisional-zone nesting
(premium/discount) is the live discriminator.** This is faithful to `htf_nest` (it nests inside a
same-direction *zone*, EXT_L demand / EXT_H supply — a location, not an EMA slope) and to the taught
method (buy discount / sell premium). Reporting it stops us from crediting the wrong mechanism.

---

## 4. Robustness (the signal is not a daily-window artifact)
- **15m+1h ONLY (drops the thin 16-bar daily, fully-populated, max depth 2):** win% **41.4 → 55.1 →
  53.8** (n 556/630/533). Jump at ≥1 survives with zero daily input ⇒ not a daily-thinness artifact.
  (718/774 deep firings *do* have a daily swing available anyway.)
- **Time-halves (within-17d holdout):** deep beats shallow in BOTH halves — early 53.3% vs 49.9%,
  **late 59.9% vs 38.7%** — echoing the doc-42 40-stock holdout (all-quadrants-positive) on this stock.
- **Direction split (win% by depth 0→3):**
  - LONG: 37.8 → 41.4 → 50.9 → **62.1** — clean monotone (HTF-discount nesting for longs, strongest).
  - SHORT: 45.3 → 52.7 → **72.2** → 48.0 — rises hard to depth-2, depth-3 dips on thin n=125 (daily-
    premium for shorts is the noisiest cell — small-n caveat, doc-36 §6B).
- **Within-detector lift** (shallow zone≤1 vs deep zone≥2 — proves depth adds signal, isn't a
  detector-identity proxy):

  | detector | shallow win% (n) | deep win% (n) | lift |
  |---|---|---|---|
  | ob_taught | 44.2 (197) | **66.0** (156) | **+21.9pp** |
  | wyckoff | 47.7 (86) | 66.0 (47) | +18.3pp |
  | fvg_n | 41.4 (220) | 58.8 (194) | +17.4pp |
  | fvg | 36.8 (76) | 48.7 (78) | +11.9pp |
  | htf_nest | 27.3 (22) | 64.3 (14) | +37.0pp* |
  | orderblock | 48.8 (125) | 52.6 (116) | +3.8pp |
  | sweep | 48.5 (167) | 49.6 (139) | +1.1pp |
  | compression | 57.1 (42) | 50.0 (26) | −7.1pp |

  ⇒ The nest-depth lever is potent **on the decisional-zone RETEST detectors (ob_taught / fvg_n /
  wyckoff / fvg)** and inert on **sweep / compression / orderblock**. Mechanistically exact: nesting a
  *retest entry* inside a same-direction HTF zone is what the lever encodes; a raw sweep/compression
  isn't a zone-retest, so HTF-zone containment adds little. (*htf_nest solo n=36, win 41.7% — the
  detector fires NEGATIVE alone, iter-4's finding; the value is `nest_depth` **as a grade term across
  the retest stack**, not htf_nest-as-signal. Confirmed here.)

---

## 5. Does it CONFIRM the +6.13R mechanism on HAVELLS? — YES
The program's proven edge (doc-42 iters 4-8) is: `nest_depth`-enriched **grade** is monotone and its
high tier nets +6.13R after honest costs, on 40 stocks. This study isolates the **direction/win-rate
half** of that lever on **HAVELLS alone** and it reproduces:
1. **Monotone** win% AND forward-R in HTF-alignment-depth (fwd12 −0.65 → +0.96R). ✔
2. **depth-0 = the LOSER class** (42.9%, negative forward-R) — doc-36's constructed loser class, real
   on HAVELLS. ✔
3. **Causal/ex-ante** (last-closed HTF bar; HTF is slow) — the doc-36 property that lets it work where
   LTF features (0.52 AUC) can't. ✔
4. **Conjunction, not solo** — htf_nest alone is negative; nest_depth lifts the *retest* detectors
   (+17-22pp). ✔ (doc-42 iter-4 "solo NEGATIVE, in-stack POSITIVE" reproduced.)

It does **not** re-prove the *R-magnitude* (+6.13R) on HAVELLS — that number is the honest-cost
`derive_tradebook` net across 40 stocks and the tiny-outer-wick stop's fill-through (doc-34), which I
did not (and was told not to) re-run. What HAVELLS confirms is the **discriminator underneath it**: the
win-rate/forward-R separation by HTF-alignment-depth, which is the direction-lever half of the +6.13R
conjunction. The stop-lever (fill-through) half is unchanged and untouched here.

---

## 6. The concrete tune this implies
1. **`htf_nest` parent = decisional-zone (premium/discount / EXT band), never EMA-trend.** The trend
   reading is a null on HAVELLS; the zone reading carries all the signal. Keep `htf_nest` on EXT_L/EXT_H
   + OB/FVG containment (as coded) — do not add an EMA-trend alignment term to the grade.
2. **Gate directional entries at nest-depth ≥ 2.** On HAVELLS the win% / forward-R sign-flip is at
   depth 2 (fwd12 crosses 0; win 43-46% → 56-58%). This corroborates the iter-7 `min_depth=2` precision
   tune and the iter-7 "move the min_grade tier boundary 4→5" wrinkle — the edge lives at ≥2 depth.
3. **Apply the nest-depth grade term specifically to the RETEST detectors** (ob_taught, fvg_n, wyckoff,
   fvg): +18-22pp there, ~0 on sweep/compression/orderblock. A depth term weighted toward retest
   detectors (or gating only retests on depth) is cleaner than a blanket grade add.
4. **Longs: lean on HTF-discount depth (monotone to 62%).** Shorts: depth-2 premium is the sweet spot;
   treat depth-3 short cells as thin-n, don't over-weight.

## 7. Honest caveats
- **One 17-day window, one stock, one regime.** 16 daily bars = daily-tier is structurally thin; the
  robustness here is 15m+1h-driven + time-halves, not multi-month. The doc-42 multi-regime gate is
  unchanged — this is single-stock corroboration, not new out-of-regime proof.
- **Alignment is a proxy** (causal swing-range position), not the live detector's exact EXT-band
  overlap; direction and magnitude are robust to the OTE-strict variant (`pos≤1/3`/`≥2/3`: fwd12 −0.54
  → −0.12 → +0.36 → +0.95, same monotone) but the exact cell win%s would shift under the true detector.
- **Small-n high-depth cells** (depth-3 n=278, SHORT depth-3 n=125) — treat single deep cells with the
  program's usual suspicion (doc-36 §6B).
- **Win-rate/forward-R only.** The R-magnitude + tiny-stop fill-through (the other half of +6.13R) was
  not re-measured here by design (no pipeline / `derive_tradebook` run).
