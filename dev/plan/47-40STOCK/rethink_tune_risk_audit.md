# 47-40STOCK — EDGE-PRESERVATION RETHINK: tune risk audit (2026-07-24)

**Mandate.** Do NOT lose the achieved graded edge. Audit each proposed action (#3–#9) for its risk to the
**graded +8R tier (frame B)** — NOT to the symmetric 1ATR:1ATR frame it was measured in (frame A). For each:
classify **EDGE-SAFE / EDGE-RISKY / EDGE-UNKNOWN** + the exact A/B test that must gate it on the DERIVE frame.

**The crown jewel (measured, honest).** `tools/derive_tradebook.py` applies the FROZEN taught grade
(`bos+sweep+ote+phase+nest_depth+maturity`, `decision.py`) + large-R runway targets. Frozen config, unseen
**2024-Q4 BEAR** tape (`runs/validate/tb_2024q4_40.txt`): hi-tier (grade≥4) **intrabar n3001 win62% NET +8.20R**,
**eod n3049 win72% +8.07R**, **all 4 holdout quadrants + every stop-mode positive**, grade ladder MONOTONE
out-of-sample (g1 −1.51 · g2 −1.31 · g3 +0.25 · g4 +5.43 · g5 +8.34 · g6 +9.54 · g7 +8.62). Also holds on
mixed-2026 (+6.13R). This is what we must not lose.

---

## 0. THE CRUX — why a frame-A win can be a frame-B loss (the load-bearing fact)

Two frames. **(A)** the 40-stock deep study analysed the **symmetric 1ATR:1ATR** firing parquet
(`study40_2026/evidence.parquet`, 38,462 decided): a coin-flip frame where the scored objective is
`edge = win% − b_hit` and every detector is 0.49–0.52 AUC. **(B)** the DERIVE frame is a **graded +
RR-asymmetry** product (tight nest/zone stop, far EXT runway target) — the +8R.

**These frames rank b_hit in OPPOSITE directions.** Measured on the parquet, per-firing geometry vs b_hit
(decided n=38,462):

| b_hit bucket | n | win% (frame A) | mean MFE (ATR) | %MFE≥3ATR (far-target reach) | mean MAE (ATR, stop-risk) | frame-A edge (win−b_hit) |
|---|--:|--:|--:|--:|--:|--:|
| **==0** | 9124 | 18.7 | **1.27** | **9.1%** | **3.33** | +0.187* |
| (0,.15] | 2977 | 37.6 | 1.86 | 16.7% | 2.94 | +0.20 |
| (.15,.30] | 5208 | 41.4 | 1.97 | 18.9% | 2.61 | +0.17 |
| (.30,.50] | 6214 | 50.8 | 2.47 | 25.7% | 2.36 | +0.07 |
| (.50,.70] | 5708 | 62.8 | 2.84 | 33.7% | 1.90 | +0.01 |
| **(.70,1]** | 9231 | 80.4 | **3.55** | **48.6%** | **1.33** | **−0.12** |

**Read this carefully.** Frame-A "alpha" (`win − b_hit`) is highest at LOW b_hit and NEGATIVE at high b_hit
(anti-calibration, forensics §2). But **REALIZED LARGE-R geometry is monotone the other way**: high-b_hit
firings reach FAR targets (48.6% hit ≥3ATR vs 9.1%) with SMALL adverse excursion (MAE 1.33 vs 3.33). In a
tight-stop/far-target product, **realized R is maximised at HIGH b_hit, not low.** The frame-A "select
low-b_hit alpha" prescription is a **symmetric-frame artifact** that inverts in the graded frame. This single
table decides half the audit.

---

## 1. HOW THE +8R IS GENERATED (from `decision.py` — so we know exactly what each tune touches)

`decide()` is an AND-chain. **Required hard gates:** (0/1) `premium_discount` permit = price AT an extreme;
(2) a same-direction decisional zone (OB/FVG/breaker) = the entry object; (4) `_runway` = the NEAREST far
`EXT_H`/`EXT_L` opposite extreme = the target. **Grade points:** `bos +1 · sweep +1 · ote +1 · phase +1`,
and node 3 **`htf_nest` → `grade += 1 + nest_depth`** (nest_depth≈2 on this tape ⇒ **+3**, and it OVERRIDES
entry/sl with the tight nest CE), plus `maturity +1`. `min_grade = 4`.

Three consequences that govern every verdict below:
- **b_hit is NOT in the grade.** `decide()` never reads it. #3 and #7 are therefore NEW filters bolted onto
  the derive path, not re-weights of an existing term.
- **strength / zone-width / stacking are NOT in the grade** either (only recorded in `members`). #5 is a
  no-op on the crown jewel.
- **The grade LEANS ON `htf_nest`.** A single nest contributes +3 — three-quarters of `min_grade=4` and
  essentially all of the g5–g7 tail (nest +3 plus 2 confluence). And `htf_nest` is the **highest-b_hit
  detector (0.519)**. Any action that deselects high-b_hit firings attacks the nest engine of the tail.

---

## 2. THE THREE CRITICAL CASES — reasoned + light-measured on the parquet

### (a) Does dropping `b_hit==0` remove firings the hi-grade tier is BUILT from?  → NO. EDGE-SAFE-to-POSITIVE.
The b_hit>0 gate removes **15.8% of `htf_nest` firings** and ~24–27% of zone firings (ob_taught 26.2%,
fvg_n 26.7%, fvg 24.4%). But what it removes is the **worst-geometry cohort, not the tail**:
- Dropped nests (b==0, n=216): win 29.6%, MFE 0.98, MAE **4.24**, and they hold only **6 of 418 (1.4%)** of
  all nest ≥3ATR far-target reachers. Kept nests (b>0, n=1148): win 50.5%, MFE 3.08, MAE 2.33 — they hold
  **98.6%** of the nest far-target reach. The **b>=.5 nests** (750, the majority) reach ≥3ATR **45.3%** vs
  b==0 nests **2.8%**. The +8R nest tail lives in the KEPT half.
- Across ALL detectors: of firings reaching ≥3ATR MFE (n=10,320) only **8.1% are b_hit==0**; of ≥5ATR
  (the +8R fat tail, n=3,859) still only **8.1%**. **The gate keeps 91.9% of the fat-tail winners.**
- Confluence-heavy moments (the grade≥4 proxy) do NOT carry more b==0: stacking-6+ b0share **17.5% < 24.7%**
  at stacking-1. Higher confluence ⇒ higher mean b_hit (0.462) ⇒ FEWER firings the gate touches.

**Verdict (a): the gate GUTS nothing.** It is a purity filter that culls the 4.24-MAE / 0.98-MFE dead cell
and keeps 92–99% of the far-target reach that generates +8R. It should compound like iter-7/8's purity tunes.

### (b) Does the T2 EXT re-anchor REWRITE the crown jewel?  → YES if REPLACE. Must be ADDITIVE. EDGE-RISKY.
The +8R is **generated from EXT levels**: `_runway`'s target IS the nearest `EXT_H`/`EXT_L` (it sets the
R-multiple of every trade), the p/d permit is the required at-extreme gate, and htf_nest parents are EXT
bands. **Moving the EXT anchor regenerates the grade AND the R-distribution that produce the +8R** — you
cannot re-anchor and re-quote +8.20R without a fresh derive + fresh holdout. Highest structural regret.
- **Safe path:** emit a PARALLEL `EXT_LIVE_H/L` (the live unmitigated extreme) and let `_runway`/`htf_nest`
  CONSULT it without deleting the confirmed-pivot EXT. Note `_runway` returns the **nearest** far extreme, so
  an ADDITIONAL farther live-extreme does **not** change existing near targets — additive T2 mostly (i) turns
  on trades that currently skip on "no runway" and (ii) extends a target only where the live extreme is nearer
  than the stale one. That is a far smaller blast radius than replacing the anchor.

### (c) Does #7 (select LOW-b_hit alpha) INVERT the winning selection?  → YES. EDGE-RISKY (highest certainty of harm).
The grade leans on `nest_depth`, whose detector `htf_nest` has the **HIGHEST b_hit (0.519)**. The +8R tail is
built on the **b>=.5 nests** (they are the ≥3ATR far-target reachers, §2a). A "prefer low b_hit" selection
rule would **preferentially drop exactly those nests** — the high-b_hit far-target reachers — because §0 shows
realized large-R is monotone-INCREASING in b_hit (MFE 1.27→3.55, MAE 3.33→1.33). "Alpha in low b_hit" is true
only for the symmetric `win−b_hit` objective, which is the WRONG objective for a large-R product. **Applying
#7's selection to the derive frame is the single most likely action to destroy the edge.** (The *recalibration*
half of #7 — an isotonic/Platt monotone transform — is neutral if used only to set a floor; it is the
SELECT-LOW-b_hit half that inverts.)

---

## 3. PER-ACTION AUDIT (verdict + the A/B that must gate it on the DERIVE frame)

**Universal PASS bar for every A/B below (never the symmetric frame):** re-derive with the change; PASS iff
hi-tier (grade≥5) **NET-R ≥ frozen +8.20R intrabar / +8.07R eod**, **all 4 holdout quadrants ≥ current**, and
the **grade ladder stays monotone**. Measure per-trade NET-R, never symmetric win%. Watch total-R separately
(a purity filter cuts count).

| # | action | verdict for the +8R tier | why (numbers) | required DERIVE-frame A/B |
|---|---|---|---|---|
| **#3** | `b_hit>0` gate (drop b==0 firehose) | **EDGE-SAFE → POSITIVE** | culls worst-geometry cell (win 29.6%, MFE 0.98, MAE 4.24); keeps 91.9% of ≥3ATR & ≥5ATR reachers, 98.6% of nest reach; hi-grade moments have LOWER b0share (17.5%) | re-derive gating the **zone AND/OR nest** b_hit>0 (test both — which firing gates is unspecified); confirm hi-tier ≥ +8.2R, quadrants hold; expect per-trade ↑, total-R ↓ a little |
| **#4** | T3 stop = wick ±0.25·ATR | **EDGE-UNKNOWN → lean RISKY (magnitude)** | win%-positive (+4–10pp, 40/40) BUT mechanically WIDENS the tight nest/zone stop → shrinks the risk denominator → **compresses the R-multiple that IS the edge**; frame-A ΔExpR = **−0.03R** | first verify the frozen derive doesn't already bake it (`stops.atr_buffer=0.25` exists but `decide()` reads meta `sl` directly; `min_stop_atr=1.0` is a PROD floor `entry.py` warns "kills RR edge", NOT in derive). Then re-derive with `sl′=sl±0.25ATR`; PASS only if fewer-stops gain > R-multiple tax on **NET-R**, not win% |
| **#5** | no-blind (strip strength/width/stacking) | **EDGE-SAFE (NO-OP)** | `decide()`'s grade never reads any of them (`decision.py:80-113`); they live only in the production `ConfluenceEngine` (path 1) which never produced +8R | none needed for the crown jewel; the +8R grade is already "no-blind" by construction |
| **#6** | T2 re-anchor EXT to live extreme | **EDGE-RISKY (highest structural regret)** | re-anchoring regenerates `_runway` targets + p/d permit + nest parents = the exact inputs that GENERATE +8R; cannot re-quote without fresh derive+holdout | **additive only**: emit parallel `EXT_LIVE_H/L`, keep confirmed-pivot EXT; full re-derive; co-locate existing hi-tier trades by ts and require their NET-R **unchanged**, new "now-emittable" trades ≥ +8R |
| **#7** | recalibrate b_hit **+ select LOW-b_hit** | **SPLIT: recalibration NEUTRAL; SELECT-LOW-b_hit EDGE-RISKY (highest certainty of harm)** | large-R geometry is monotone in b_hit the OPPOSITE way to frame-A alpha; "prefer low b_hit" deselects the high-b_hit nest engine (b>=.5 nests reach ≥3ATR 45.3% vs 2.8%) | do NOT ship the selection rule. If tested at all: re-derive with a low-b_hit preference — the data PREDICTS hi-tier net-R collapses. Recalibration-as-floor is fine (monotone, preserves #3) |
| **#8** | regime classifier (mode-switch) | **EDGE-RISKY as a HARD gate** | +8R already holds regime-BLIND on mixed-2026 AND unseen bear-2024Q4 (all quadrants, all stop modes) ⇒ mode-switch is OPTIMIZATION not survival; classifier is a 16-bar D1 label where **ADX cannot seat** — hard-gating adds a MISCLASSIFICATION failure mode to a tier that works without it | run classifier as a PARALLEL TAG; split the existing tb by classified regime; only wire suppression if a hi-tier regime cell is actually negative (none is). PASS = hi-tier ≥ +6R in all 3 classified regimes |
| **#9** | extreme + sweep + BOS gate (B8) | **EDGE-RISKY-UNKNOWN** | `decide()` already AWARDS sweep+bos as bonuses; making them REQUIRED at the extreme drops grade≥4 trades that reached 4 via **nest+phase** (nest +3 + phase +1, NO sweep/bos) — could cull real nest winners while targeting held-extreme knife-catches (DOWN-LONG at-extreme 48.8%) | re-derive with sweep+BOS REQUIRED in node 0/1; report hi-tier net-R, all-4-quadrant, AND the count of nest+phase-only grade-4 winners lost |

---

## 4. REGRET-RISK RANKING (most likely / most damaging to the +8R first)

1. **#7 "select LOW-b_hit alpha" — HIGHEST regret.** Near-certain to invert the winning selection: it
   deselects the high-b_hit nests that ARE the far-target reachers. Frame-A measured it; the graded frame
   inverts it. Do not apply. (Recalibration-as-floor is separable and neutral.)
2. **#6 T2 re-anchor (as REPLACE) — HIGHEST magnitude.** Regenerates the grade + R-distribution that produce
   +8R. Safe only as additive `EXT_LIVE` + full re-holdout.
3. **#4 T3 buffer — taxes the R-multiple that is the edge.** Win% up, NET-R unknown; a blanket stop-widen on
   a tight-stop product can quietly convert +8R → ~+6R. Re-race on NET-R first.
4. **#8 regime hard-gate — adds a misclassification failure mode** (ADX can't seat) to a tier that already
   survived a real bear regime blind. Tag-and-measure, don't gate.
5. **#9 sweep+BOS required — may cull nest+phase grade-4 winners.** Moderate; A/B the lost-winner count.
6. **#3 b_hit>0 gate — EDGE-SAFE→POSITIVE, lowest-regret filter.** Culls the 4.24-MAE dead cell, keeps 92%
   of the fat tail. Ship behind the standard A/B; expect it to compound.
7. **#5 no-blind — EDGE-SAFE NO-OP.** The +8R grade never used strength/width/stacking.

**Bottom line.** The two "obvious ship-now" symmetric-frame tunes split hard when projected onto the graded
frame: **#3 and #5 are safe (one positive, one no-op); #7's headline "select low-b_hit" is the crown-jewel
killer, and #4/#6/#8/#9 are RISKY-until-A/B'd on the derive frame.** The frame-A finding that "alpha lives in
low b_hit" is the trap: it is a symmetric-frame artifact that inverts under the RR-asymmetry that makes the
+8R. When in doubt, every one of these is measured in the wrong frame — gate it on a fresh derive against the
frozen +8.20R / all-4-quadrant / monotone-ladder bar before believing it.
