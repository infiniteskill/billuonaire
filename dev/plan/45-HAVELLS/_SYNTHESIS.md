# 45-HAVELLS — SYNTHESIS: what else can be done / needed / tuned (2026-07-24)

Rolls up the 4 HAVELLS deep-studies (`convergence_tree`, `failed_trade_forensics`,
`feature_sl_anatomy`, `htf_alignment_discrimination`) against the loop state (`42-REFINE-LOOP.md`,
iter-8: ungated **+0.52R**, high-tier ≥4 **+6.13R / win 49%**, holdout-stable @40 stocks; binding gate =
one 17-day regime). All four were RECOGNITION studies on the same tape (2026-06-25→07-17, 16 sessions,
1140–1234, EQ 1180) + the 2778-firing parquet. Every tune below is **additive, default-preserving, and
testable on the existing parquet** (a few need small infra, flagged **[infra]**).

---

## 0. THE SPINE — one paradox, one resolution (read this first)

The four studies look contradictory and are not:

- **htf_alignment** says nest_depth is a **clean monotone discriminator** on HAVELLS (depth 0→3 win
  42.9→46.4→**57.7→55.8%**, fwd12 −0.65→**+0.96R**, p≈5e-7), carried by the **premium/discount
  decisional-zone** reading — EMA-trend is a null (corr −0.017).
- **failed_trade_forensics** says the wired `htf_nest` is a **top loser signature** on HAVELLS: highest
  baseline b_hit (0.590) yet **lowest realized win (41.7%)** — a mild *anti*-signal.
- **convergence_tree** resolves it: the wired detector fires the **wrong nests**. Its EXT parents are a
  single latest swing, so it (a) clips **EQ-mid nests** (1158–1188, ~40% hit) that satisfy depth on
  furniture, and (b) **never re-anchors the later, higher extreme** — across all 37 HAVELLS rows
  `zone_hi` never exceeds **1201.2**, so the user's textbook short (1221 mitigation at the **1234.34**
  premium line, 3-pt stop, +8R hit, ran +26R) is **literally invisible** (nest_depth=0, not emitted).

**Resolution:** the *lever* (depth into a same-direction decisional zone) is real and 40-stock-proven;
the *wired grader* mis-measures it on this symbol. The rule both halves imply:
> **valid entry = LTF retest nested ≥2 TFs deep AND terminating at a D1 OTE-extreme** (premium for
> shorts / discount for longs). Depth is **necessary but not sufficient**; the D1-extreme is the other
> half. Nests at the two D1 extremes hit **80%**; same-depth nests in the EQ mid hit **~40%**.

Nearly every tune below is a way to make the wired system measure *that* object.

---

## A. TOP FAILURE MODES ON HAVELLS + THE FIX

| # | failure mode (measured) | share / cost | fix |
|---|---|---|---|
| **F1** | **Depth satisfied by furniture** — htf_nest clips EQ-mid zones (~40% hit) → the depth term grades the wrong nests, becomes an anti-signal (41.7%). | drags SHORT 31%, LONG 48% | **OTE/premium-discount gate on the BASE** (T1) + **re-anchor EXT to current extreme** (T2). |
| **F2** | **Terminal-extreme mitigation is invisible** — EXT anchored to latest swing, later 1234 high never re-anchored; best short unseen (`zone_hi`≤1201.2). | misses the +8..+26R setups | **T2** re-anchor EXT_H/EXT_L to the current *unmitigated* range extreme. **[infra]** |
| **F3** | **Tiny outer-wick stop shaken out by wick noise** — exact-edge SL holds only 30.3%; **62% of eventual winners first touch the exact-edge stop**; breaches are **84.8% wick-noise, 15.2% gap**. | realized win 44.1% | **T4** buffer SL to `wick ± 0.25·ATR` → measured **44→55%**. |
| **F4** | **Stop parked inside the sweep it's waiting for** — 2 supply shorts stopped at OB edge 1224, price ran to 1234 to grab the pool, *then* dropped. User's own note: "ALL SL TAKEN BY BANK AS LIQUIDITY SWEEP." | the L3/L5 cluster | **T5** when a pool sits past the zone, anchor SL **beyond the POOL**, not the box. **[infra]** |
| **F5** | **Enter before the sweep completes** — AM shorts 37.3% (worst cell), CE_HOLD 42.3%, b_hit=0 wick-entries 22.3%. User: "entered before the liquidity sweep, stop tagged." | 20% of book @ −1.495R | **T6** sweep-then-arm gate + **T7** session gate (block AM shorts). |
| **F6** | **System confidence is blind** — `strength` AUC 0.495 (non-monotone), zone-width/ATR 0.478, SL-dist/ATR 0.489, stacking-count flat ~45–50%. The detectors' own scores predict **nothing**. | — | **T8** never gate on strength/width/stacking; gate on b_hit + OTE + depth only. |

---

## B. RANKED TUNES (numeric · additive · testable · transferable to all stocks)

Transferability note: every constant below is **normalized or structural** (range-position, ATR,
session, config-baseline) — no HAVELLS price level — so each generalizes to the 40-stock universe.

| rank | TUNE | numeric spec | expected impact (measured/predicted) | test (no pipeline) |
|---|---|---|---|---|
| **T1** | **OTE gate on the base retest zone** — depth only *counts* when the base sits on the correct D1 OTE side. | require base range-pos: SHORT `pos≥0.62` (premium), LONG `pos≤0.38` (discount). | kills the ~40% EQ-mid nests; **LONG 48→~70%, SHORT 31→~70%** (pred); flips htf_nest from anti-signal to discriminator. | filter parquet by causal swing-range pos; recompute win% by depth×side. |
| **T2** | **Re-anchor EXT_H/EXT_L to the current unmitigated range extreme** (not latest swing). **[infra]** | anchor = highest-high / lowest-low still unmitigated in the causal window. | makes F2 setups emittable (`zone_hi` reaches 1234); recall of the +8..+26R premium mitigations. | re-derive EXT bands offline; check htf_nest `zone_hi` now tags the range extreme. |
| **T3** | **SL buffer off the outer wick** — applies to *every* trade. | `SL = wick_extreme ± 0.25·ATR`. | realized win **44.1→55.4% (+11pp)**; removes 85% of breaches (all noise-wicks); cost +0.25 ATR on a 6× target. | already computed in `feature_sl_anatomy §B3`; re-race first-touch on 1m. |
| **T4** | **nest_depth ≥ 2 hard gate + move min_grade tier 4→5.** | keep `min_depth=2` (sign-flip is at depth 2, fwd12 crosses 0); gate grade **≥5** (grade-4-alone = −2.97). | 40-stock-proven: high-tier +6.13R; sharpens g5–7 = +8..+11R. | already in loop (iter-7/8); apply boundary, re-read tradebook. |
| **T5** | **Beyond-pool SL** — when an EXT/EQH pool sits between zone edge and target, extend SL 1 tick past the pool. **[infra]** | detect nearest same-side pool; `SL = pool_extreme ± 1 tick`. | kills F4 (measured 1224→1234 sweep-out) at the mechanism. | flag firings with a pool in the wick→stop path; compare sweep-hold. |
| **T6** | **Session gate (orthogonal to b_hit AND to nest).** | de-weight/block AM 09:15–11:00, esp. **AM shorts**; favor PM 13:00–15:30. | `GRADE=(b_hit≥.5)+(isPM)` → win **33→55→73%**, net **−0.77→+1.745R**. AM 43.6% vs PM 57.2%; b_hit flat across sessions (additive, not double-counted). | already computed in `failed_trade §2`; add session term. |
| **T7** | **b_hit gate — paired, not solo.** | drop `b_hit==0`; prefer `b_hit≥0.5`. **Must pair with T1** (htf_nest has HIGH b_hit but is the bad nest). | b_hit AUC **0.691** (dominant); `b_hit==0` = 20% of book @22.3%/−1.495R; `≥0.5` → 67%/+1.05R. | filter parquet by b_hit bin. |
| **T8** | **Hygiene — stop gating on dead features; native-TF FVG.** | drop strength/zone-width/SL-dist/stacking-count as gates (all AUC 0.48–0.50, stacking flat); detect FVG on **5m/30m**, not 1m; retire plain `fvg` (42.9%) & `CE_HOLD` (42.3%); grade pivot-distance with **±0.5–1 ATR** tolerance. | removes noise gates + fixes FVG recall (taught boxes have no 1m 3-candle equal). | AUC tables already in `failed_trade §1` + `feature_sl §A`. |

**Direction/side refinement (free, from htf_alignment §4):** LONGs lean on HTF-**discount** depth
(monotone to 62.1% at depth-3); SHORTs peak at **depth-2 premium** (72.2%) — treat depth-3 short cells
as thin-n. Apply the depth term to the **RETEST detectors** (ob_taught +21.9pp, wyckoff +18.3, fvg_n
+17.4, fvg +11.9) and **not** to sweep/compression/orderblock (+1.1 / −7.1 / +3.8 — a retest-only term
is cleaner than a blanket grade add).

---

## C. WHAT IS MISSING (feature / TF / gate the studies show we need)

1. **A true multi-TF OB/FVG parent emitter** — htf_nest leans on EXT bands *only* (the loop's "STARVED /
   needs infra" note). Depth should count OB/FVG **or** re-anchored-EXT parents at a range extreme, so
   depth measures real D1⊃H1⊃M15 containment (all 3 taught setups are depth-3), not incidental EXT clip.
2. **A "current-extreme" anchor** (T2) — the range's live unmitigated high/low, not the latest swing.
   Without it the best premium-extreme mitigations are structurally unemittable.
3. **A premium/discount gate on the BASE zone** (T1) — currently only parents are checked for zone
   membership; the base can sit anywhere. This is the missing "other half" of the rule.
4. **A sweep-completion gate** (T6) — arm the entry only after the buy/sell-side liquidity is *taken*;
   this is the user's single recurring hand-marked failure ("entered before the sweep").
5. **Native-TF FVG** (T8) — FVG must be detected on 5m/30m; a 1m detector cannot reproduce the taught box.
6. **Session as a grade term** — time-of-day (AUC 0.574) is a real, orthogonal lever entirely outside
   both b_hit and nest, and is not currently in the grade at all.
7. **Multi-regime 1m data** — the loop's unchanged binding gate. Everything here is measured on **one
   17-day regime**; T1/T6 magnitudes especially may compress out-of-regime (honest caveat).

---

## D. THE SINGLE HIGHEST-LEVERAGE NEXT TUNE

**T1 — gate the base retest zone on the correct-side D1 OTE band (short→premium `pos≥0.62`,
long→discount `pos≤0.38`), making it a required term for nest_depth to count — with T2 (re-anchor EXT to
the current extreme) as its infra companion.**

Why it outranks everything else: it is the **one change all four independent studies converge on**, and
it does not merely *add* — it **repairs the program's already-proven +6.13R discriminator**. Today the
nest term grades EQ-mid furniture (→ the 41.7% anti-signal on HAVELLS) and misses the terminal-extreme
mitigations; T1 converts nest_depth from *necessary* to *necessary-and-sufficient* (depth × D1-extreme),
which is exactly what lifts the 80%-hit extreme nests over the 40%-hit mid nests. Predicted LONG
48→~70% / SHORT 31→~70%, and it is a **pure additive filter testable on the existing parquet by
recomputing win% over (depth × range-position × side) — no pipeline run.** The biggest *independent* add
on top is **T3** (SL buffer, measured +11pp, applies to every trade).

---

## E. HONEST CAVEATS
- One stock, one 17-day regime — T1/T6 lifts are **predicted/in-sample**; the 40-stock nest edge (T4) is
  the only holdout-proven number. Re-derive T1/T2 across the 40-stock parquet before trusting magnitudes.
- b_hit (T7) is the config's own historical baseline — partly circular, and it is *high* on exactly the
  bad nests; never use it solo, always pair with T1.
- T2/T5/T8-FVG need small emitter/anchor code (**[infra]**); T1/T3/T4/T6/T7 are measurable on the parquet
  as-is.
