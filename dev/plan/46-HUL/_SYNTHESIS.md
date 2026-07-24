# 46-HUL — SYNTHESIS: re-verification of the HAVELLS findings on a second stock (2026-07-24)

Rolls up the 4 HUL re-verification studies (`convergence_tree`, `failed_trade_forensics`,
`feature_sl_anatomy`, `htf_alignment_discrimination`) against `45-HAVELLS/_SYNTHESIS.md`. HUL has
**no hand-marks** — every HUL number is firings-based (`hul_study_2026`: 1225 firings / 1088 decided,
19 sessions 2026-06-19→07-16; `hul_study_2024`: 3577 firings / ~3123 decided, 61 sessions Sep–Nov,
folded in as a 3× out-of-regime replication window). Method mirrors HAVELLS §1 exactly (resample 1m →
M15/H1/D1, causal `merge_asof`, symmetric 1-ATR:1-ATR outcome frame). Both HUL windows reconfirm the
same **50.6% / 53.2% coin flip** (AUC 0.52) HAVELLS had.

---

## 0. THE SPINE — one variable explains every split: **regime**

HAVELLS 2026 was **range-bound** (1140–1234, drawn box, EQ 1180). HUL 2026 is a **persistent downtrend**
(open→close 2208→2098, net −5.0%, close at the **5th percentile** of range); HUL 2024-Q4 is also a
downtrend (net −10.8%). This single fact predicts the whole scorecard:

- The **mechanical / regime-free** findings — F1 (the wired `htf_nest` mis-grades → anti-signal), F6
  (native confidence scores are blind, `b_hit` dominates), F3 (the taught tiny wick stop is shaken out) —
  **replicate cleanly on both HUL windows.** These are stock-general.
- Every finding that depends on the **premium/discount range-fade actually working** — nest_depth as a
  discriminator, T1's OTE-gate, "nests-at-a-D1-extreme = 80%" — is **ABSENT or INVERTED** on HUL, because
  premium/discount nesting is a *range-fade* tool and HUL is trending. On a trend, shorting *discount*
  (momentum continuation) equals shorting premium and buying *discount* catches the falling knife: the
  location lever nulls and **side/momentum dominates** (SHORT 54% > LONG 47%).

HUL does not **refute** the HAVELLS mechanism — both its windows are downtrends, so it can't test the
range regime. It **measures the "one 17-day regime" caveat 45-SYNTHESIS §E flagged**: the direction-lever
edge is **regime-conditional**, and it collapses out of its regime.

---

## A. REPLICATION TABLE — each HAVELLS finding × [HAVELLS | HUL | REPLICATES?]

| # | HAVELLS finding | HAVELLS number | HUL number (2026 · 2024-Q4) | REPLICATES? |
|---|---|---|---|---|
| **F1** | **furniture-depth → `htf_nest` is an anti-signal** (highest b_hit of any detector, yet lowest-tier realized win) | b_hit **0.590** (top) / win **41.7%** / edge − | b_hit **0.53–0.60** (top) / win **40.7–44.7%** / edge **−8.4pp** · 2024: b_hit **0.59–0.60** (top) / win **16.2–31.2%** / edge **−27.9pp** | **YES — STRONGLY** (2024 is dead-on the HAVELLS number). *Cause differs*: HUL drag = premium-SHORT failure, not EQ-mid furniture. |
| **F2** | **invisible-extreme** — EXT anchored to latest swing, never re-anchors the later extreme → `zone_hi` capped below the true extreme | zone_hi ≤**1201.2** vs true **1234** (gap **33pt / ~14 ATR**) | HIGH side: zone_hi **2231.5** vs 2238.8 (gap **7.3pt / 1.8 ATR** — mostly reached). LOW side (the *fresh* Jul-15 extreme): zone_lo **2113.3** vs 2091 (gap **22.3pt / 5.5 ATR** — invisible) · 2024: gaps **1.1 / 5.2pt** | **PARTIAL** — replicates only on the **fresh / un-retested** extreme (on HUL's downtrend that's the LOW, not the high); dissolves on old, retested extremes. Same mechanism, far milder bite. |
| **nest_depth discriminator** | depth 0→3 win **monotone up**, fwd12 crosses 0 | **42.9 → 46.4 → 57.7 → 55.8%**; corr **+0.11 / +0.19**, p≈**5e-7** | **54.7 → 46.2 → 50.5 → 48.2%** (non-monotone, depth-0 highest); corr **−0.05 / −0.17** · 2024: depth 2→3 **36.4 → 16.7%** | **NO — ABSENT / INVERTED.** Deep is *worse* (SHORT depth-3 premium craters to ~40%). Only the LONG half keeps the sign, faintly. |
| **F3** | **tiny-stop shakeout** — SL-hold ~30%, majority of winners tag the exact edge, +0.25 ATR buffer lifts win; failure is wick-noise not gap | SL-hold **30.3%**; **62%** of winners tag edge; buffer **44.1→55.4% (+11pp)**; breach **84.8% wick / 15.2% gap** | SL-hold **29.0–33.4%**; tight-cohort winner-tag **51.1%**; **tight-cohort** buffer **41.7→53.5% (+11.8pp)**; breach **83.6% wick / 16.4% gap** · 2024: **88.8 / 11.2**, buffer **39.1→50.8%** | **YES** — near-exact on the **tight-stop tercile** (the true taught-wick geometry); milder in aggregate only because HUL's taught stop runs ~1.4× wider in ATR. Wick/gap split is near-identical. |
| **F5** | **enter-before-sweep — AM shorts worst** (the single worst cell) | SHORT-AM **37.3%** (worst cell) | SHORT-AM **47.9–48.8%** (NOT the worst cell; worst = **LONG-midday 39.3%**); AM<PM for shorts holds *directionally* (48 vs 57%) · 2024: **flat** (SHORT-AM 48.0%, not worst) | **NO** — the "AM shorts worst" claim does not replicate; only the soft same-sign AM<PM-for-shorts pattern survives, and it's gone in 2024. |
| **F6** | **blind confidence** — strength / zone-width / SL-dist / stacking AUC ~0.48; only `b_hit` predicts | strength **0.495**, width 0.478, sl-dist 0.489, stacking flat; **b_hit 0.691** | strength **0.476**, width **0.476**, sl-dist **0.472**, stacking **0.460**; **b_hit 0.739** · 2024: strength **0.490**, **b_hit 0.741** | **YES — STRONGLY** (both windows). `b_hit` is an *even better* separator on HUL; strength is mildly *anti*-monotone. |
| **T1** | **OTE-gate lift** — count depth only when the base sits on the correct D1 side (short pos≥.62 / long ≤.38); extreme nests 80% vs EQ-mid 40% | LONG **48→~70**, SHORT **31→~70** (pred); extreme **80%** vs mid **40%** | LONG **47.1→47.2 (+0.1)**, SHORT **54.0→51.0 (−3.0)**; PASS-gate **49.5%** vs FAIL **53.5%**; at-extreme **16.7%** vs interior **37.5%**; SHORT-at-premium-extreme **17.6%** (worst) | **NO — ABSENT / INVERTED.** Zero-to-negative lift; the gated (extreme) half is the *worse* half. See §C. |

---

## B. STRUCTURAL (both stocks) vs STOCK-/REGIME-SPECIFIC

**STRUCTURAL — regime-free, replicate on both HUL windows → safe to generalise to the 40-stock universe:**

1. **F1 — `htf_nest` is an over-priced anti-signal.** Highest baseline `b_hit` of any detector, lowest-tier
   realized edge (−8.4pp 2026, −27.9pp 2024). Reproduces to two decimals. → keep the nest term **off solo**.
2. **F6 — native confidence is blind; `b_hit` is the one real separator.** strength/width/SL-dist/stacking
   AUC ~0.47–0.48 on both; `b_hit` AUC **0.739/0.741** (> HAVELLS 0.691). → gate on `b_hit`, **never** on
   strength/width/stacking. Corollary **L1** (`b_hit==0` = the single biggest bleed, ~23% of book @ ~22% /
   ≈ −1.1R) also replicates and is the cleanest portable gate.
3. **F3 / T3 — the taught tiny wick stop is run ~70% of the time by wick noise (not gaps), and a +0.25 ATR
   buffer rescues ~+12pp** on the tight-stop cohort. Same sign, same magnitude, both windows. **This is the
   single strongest *transferable structural tune* in the whole set** — regime-independent, +5.8pp aggregate
   / +11.8pp where the taught stop actually lives.
4. **B4 — stop-hold edge is HTF-anchor *distance*, not detector confidence** (htf_nest stop holds ~92% at
   ~10.5 ATR out vs ~34% for tight zones). Replicates, stronger on HUL.
5. **A1 — FVG is an HTF artifact, not a literal 1m gap** (7–15% of firings map to a clean 1m 3-candle gap).
   Replicates at scale → detect FVG on its native TF.

**STOCK-/REGIME-SPECIFIC — depend on the range-fade regime; ABSENT/inverted on HUL's trend → must NOT ship
as universal grade terms without a regime gate:**

- **nest_depth as a discriminator** (ABSENT/inverted, corr −0.05).
- **T1 OTE-gate** (ABSENT/negative — §C).
- **"nests-at-a-D1-extreme = 80%"** (INVERTS to 16.7%; SHORT-at-premium-extreme is the *worst* bucket).
- **F5 AM-shorts-worst** (ABSENT; HUL's worst cell is LONG-midday).
- **time-of-day 2nd lever** (weak 2026, flat 2024).
- **plain-`fvg` / `CE_HOLD` as losers** (ABSENT — they're ~52% on HUL, coin-flips).
- **F2 invisible-extreme** is the in-between case: the mechanism is structural (single-latest-swing anchor)
  but its *bite* is geometry-conditional — it only costs you on the **fresh, un-retested** extreme.

---

## C. Does T1 (OTE-gate) hold on BOTH? — **NO. Confidence to ship it universally: LOW.**

T1 is the exact opposite of a cross-stock confirmation:

| | HAVELLS (range) | HUL 2026 (downtrend) | HUL 2024-Q4 (downtrend) |
|---|---|---|---|
| LONG ungated → gated | 48 → **~70** (pred) | 47.1 → **47.2** (+0.1) | discount-longs 42.2% (no lift) |
| SHORT ungated → gated | 31 → **~70** (pred) | 54.0 → **51.0** (−3.0) | premium-shorts **17.1%** (gate *selects* the losers) |
| PASS-gate vs FAIL-gate win | extreme 80 vs mid 40 | **49.5 vs 53.5** (PASS is worse) | premium-shorts worst |

**All three HUL measurements agree: T1 produces zero-to-negative lift, and the half it keeps (correct-side
extreme) is the *worse* half.** Root cause is regime, and it also explains why the HAVELLS *fix* can't work
here: on HUL the F1 anti-signal is driven by **premium-shorts failing into a downtrend**, so gating the base
*to* the premium extreme actively **selects the losers**. T1 was 45-SYNTHESIS's "single highest-leverage next
tune" (repairs the +6.13R discriminator) — but that ranking was measured on **one range-bound stock**. HUL
demotes it from *ship-it* to **ship-it-behind-a-regime-classifier**:

> **T1 must carry a trend/range gate** (D1 close-position-in-range, or ADX / EMA-slope). Premium/discount
> should *count* only on range-defined tape; on trending tape the system should **flip from fade to
> continuation** (side/momentum), not apply OTE blindly, or it bleeds edge. **Do not implement T1 as a
> universal grade term.** The 40-stock holdout that proved the depth edge (T4, +6.13R) was itself likely
> range-weighted; re-derive T1 across the 40-stock parquet **split by regime** before trusting any magnitude.

---

## D. NEW failure mode HUL reveals that HAVELLS didn't

1. **HELD-EXTREME (tagged-and-held ≠ swept-and-reversed) — the headline new failure.** HAVELLS's extremes
   were *spike* extremes that swept-and-reversed **promptly**, so at-extreme nests hit 80%. HUL's D1 extremes
   (2238.8 in 2026, **3035 in 2024**) were **tagged and then HELD** — 3035 stayed elevated (2905–3030) for a
   **full week** before the real fall. Result: extreme/OTE shorts were the **worst** bucket (16.7% / 17.6%),
   inverting the 80% claim. → **OTE/extreme gating alone grades held-tops as A-setups.** The fix sharpens the
   rule: gate on **extreme AND a confirmed sweep+BOS reversal**, never extreme-location alone. HAVELLS never
   saw this because its extreme always reversed on schedule.

2. **TREND-REGIME COLLAPSE of the fade lever.** On a directional tape the premium/discount *location* signal
   goes null-to-inverted: shorting discount ≈ shorting premium (both ~52%), buying discount = falling knife
   (long-discount 45% ≤ long-premium 44%). This is a *category* failure the range-only HAVELLS study could
   not expose — the lever doesn't just weaken, it stops discriminating, and **momentum (side) becomes the
   only edge** (SHORT>LONG ~7pp, monotone with the drift). A regime-aware system must switch modes, not
   down-weight.

3. **F1's cause is not F1's HAVELLS cause.** Same anti-signal outcome, *different mechanism* — premium-short
   failure vs EQ-mid furniture (HUL has **no** EQ-mid nests; all firings are polarized). This is why the
   HAVELLS-prescribed fix (T1) misfires on HUL: it treats a furniture problem that isn't there.

4. **Sweep detector is poorly localized on HUL** (median firing-bar overshoot **−0.31 ATR** — the firing bar
   is the retest/confirmation, not the poke), so tick-exact "sweep-the-stop" geometry is not co-located with
   the sweep bar. → grade sweep/wyckoff levels with an **ATR tolerance**, not tick-equality. (Minor;
   HAVELLS's cleaner spike-sweeps hid this.)

---

## E. THE 8-LINE VERDICT

1. **REPLICATION VERDICT: split, and the split is regime.** The mechanical findings replicate cleanly on both
   HUL windows; the range-fade findings are absent on HUL's downtrend.
2. **REPLICATE (STRUCTURAL, both stocks):** F1 (htf_nest anti-signal, edge −8.4/−27.9pp), F6 (confidence
   blind, `b_hit` dominates AUC 0.739/0.741), F3 (tiny-wick stop shaken out ~70%, +0.25 ATR = +12pp).
3. **DO NOT REPLICATE (regime-specific):** nest_depth discriminator (corr −0.05, inverted), nests-at-extreme
   (80%→16.7%), T1 OTE-gate, F5 AM-shorts-worst — all need the range regime HUL lacks.
4. **PARTIAL:** F2 invisible-extreme bites only on the *fresh, un-retested* extreme (HUL's low), far milder
   than HAVELLS's 33-pt gap.
5. **T1 is NOT confirmed as the top tune across both stocks — it is falsified as a universal lift:** LONG
   +0.1pp, SHORT −3.0pp, PASS-gate 49.5% < FAIL-gate 53.5% (the gated half is worse).
6. **T1's rank collapses because it is a range tool applied to a trend; on HUL it selects the losing
   premium-shorts.** Ship it only behind a trend/range classifier, never as a universal grade term.
7. **The durable, ship-now cross-stock tunes are the regime-free three:** gate on `b_hit` (drop `b_hit==0`),
   buffer the wick stop +0.25 ATR (T3), and keep confidence/strength/stacking OUT of the grade.
8. **NEW failure mode HUL exposes:** the **held-extreme** (tagged-and-held, not swept-and-reversed) turns
   OTE/extreme shorts into the *worst* bucket — extreme-gating must be conjoined with a confirmed
   sweep+BOS reversal, not used on location alone.
</content>
</invoke>
