# 47-40STOCK — EDGE-PRESERVATION RETHINK: reconciling the two frames (2026-07-24)

**Mandate:** do NOT lose the achieved +6–8R graded edge. Reconcile the apparent contradictions
between the **40-stock DEEP STUDY** (`_SYNTHESIS`, `forensics`, `htf_nest_bug`, `sl_anatomy`,
`structural_tunes`, `t1_and_bughunt`, `_REGIME`) and the **DERIVE product** (`tb_2024q4_40.txt`,
`42-REFINE-LOOP`, `44-AUDIT-VERIFY`). Be adversarial + quantitative. Verdict per change:
SAFE / RISKY, and — the decisive question — is the deep study a **MANDATE** to change the frozen
config or a **DIAGNOSTIC** of why it works?

**Sources checked directly this pass:** frozen config `runs/validate/taught_profile/config.json`;
`tools/derive_tradebook.py` (`_sim`, `_tap`, `cost_R`); `runs/validate/study40_2026/summary.csv`
(the deep-study firing aggregates); the six forensics docs. (Parquet re-read blocked by a pyarrow-19
histogram incompat; summary.csv + docs carry every number with its n, so all figures below are cited
from measured artifacts, not recomputed.)

---

## 0. THE TWO FRAMES — stated precisely (this is the whole reconciliation)

**FRAME A — the deep study.** `runs/validate/study40_2026/evidence.parquet`, 44,042 firings /
**38,462 decided**, one 17-day 2026 tape. Outcome = **symmetric 1·ATR : 1·ATR** first-touch race on M5,
same session. Payoff is 1:1, so **win% *is* the edge signal** and the natural metric is `mean(win) −
mean(b_hit)`. It measures, per **individual firing**, *which barrier is tagged first at ±1 ATR*.

**FRAME B — the derive product.** `derive_tradebook.py`: each `decide()`-take is a **trade** with the
**taught tight wick stop** (`_sim` uses `d.sl` verbatim, `risk=|entry−sl|`, capped at **−1R** on an
intrabar touch) and a **large-R runway target**; **R = target_dist / stop_dist ≫ 1**. The **grade** is
a **conjunction** (bos + sweep + ote + phase + nest_depth + maturity), reported **by grade tier** and
gated to **grade ≥ 4/5**. It measures **net R of a graded, RR-asymmetric trade**.

> These are not two views of one number — they measure **different quantities**. Frame A caps every
> outcome at ±1 ATR; Frame B's entire edge lives in the **>1 ATR right tail** that Frame A is blind to
> by construction. **A symmetric-frame win can be a graded-frame loss, and vice-versa.** Every one of
> the three "contradictions" is this single frame mismatch wearing three hats.

---

## 1. THE EDGE WE MUST NOT LOSE (measured, honest) — the crown jewel numbers

**2026 (mixed/range, in-sample, iter-8 frozen):** ungated **+0.52R**; hi-tier (grade≥5) **+6.13R /
win 49%**; all-4-quadrant holdout +.

**2024-Q4 (BEAR tape, 31/41 downtrend, UNSEEN, frozen config)** — `tb_2024q4_40.txt`:

| stop mode | hi-tier (≥4) | win% | grade ladder (NET/t) | 4 quadrants |
|---|---|---|---|---|
| intrabar | **+8.20R** (n=3001) | 62 | g1 −1.51 · g2 −1.31 · g3 +0.25 · g4 +5.43 · g5 +8.34 · g6 +9.54 · g7 +8.62 | +12.1/+11.1/+5.1/+6.6 |
| m5_close (prod F9) | **+8.35R** (n=3016) | 65 | g1 −1.92 · … · g5 +8.41 · g6 +9.89 · g7 +8.97 | +12.5/+11.2/+5.1/+6.7 |
| eod (prod intraday) | **+8.07R** (n=3049) | 72 | g1 −1.54 · … · g5 +8.57 · g6 +8.86 · g7 +8.73 | +10.6/+9.8/+5.8/+7.3 |

Grade ladder **monotone g1→g7 out-of-sample**, all 4 quadrants + under **every** stop mode. The bear
tape is **STRONGER** than the mixed tape (+8R vs +6R). **This is the object every proposed change is
tested against.**

---

## 2. CONTRADICTION 1 — "detectors 0.49 AUC, htf_nest −4.7pp" vs "nest_depth tier +8R"

**FRAME ARTIFACT — not a real contradiction.**

- Frame A: no geometric feature separates win/loss at 1:1 — `strength` AUC 0.497, width 0.493,
  stacking 0.496 (35–37/40 blind); detector win 47–52%; **MFE/MAE mirror** (WIN mfe ≈ 3.2–3.4 ATR ≈
  LOSS mae; `summary.csv`: every detector mfe≈2.1–2.7 ≈ mae). True statement: **at ±1 ATR, first-touch
  is a coin flip.**
- The +8R does **not** come from beating a 1:1 flip. It comes from **(a) RR-asymmetry** — a ~0.42-ATR
  taught stop (`sl_anatomy`: tight-tercile SL_atr median **0.42**) against a large target, so the very
  mirror excursion Frame A caps at 1 ATR is a **3.2–3.4 ATR / ≈8R** win in Frame B — **and (b) the
  conjunction grade sorting which trades reach that target** (win% climbs 27%→71% across g1→g7).
  Frame A **cannot see the 8R tail**; it clips it at 1.0.
- **htf_nest −4.7pp** is a *marginal, symmetric, per-firing* stat on **1,364/44,042 = 3%** of firings,
  99.8% of which emit the identical depth-2 flag. In Frame B it is **one conjunctive +1 among six**.
  `42-REFINE-LOOP` iter-4 proved the split directly: **htf_nest SOLO −3.2%**, but **nest_depth AS PART
  of the high-grade stack marks winners** (g5 +5.96 vs g1–2 ≈0). The *same term* is symmetric-negative
  and conjunction-positive — the textbook definition of a frame artifact.

**Implies for what is SAFE:** 0.49 AUC is **NOT** a mandate to strip detectors. The +8R does not rest
on any detector's directional AUC; it rests on the **conjunction + RR-asymmetry**. Stripping detectors
because they're 0.49-AUC in Frame A would delete the conjunction's inputs. **RISKY.**

---

## 3. CONTRADICTION 2 — "alpha in the LOW-b_hit tail" vs "grade leans on high-b_hit nest terms"

**FRAME ARTIFACT + a mischaracterization.**

- Frame A "edge" = win% − b_hit. High b_hit → high win% but **negative alpha-over-baseline** (top decile
  >0.80, n=6,730: win 0.842, **edge −0.121**; bottom ≤0.15, n=12,101: win 0.234, **edge +0.204**).
  This is a statement about **marginal calibration in the symmetric frame**. Frame B's objective is
  **net R**, not win% − b_hit: a high-win setup at large R is +EV *regardless* of whether it "beats its
  own prior."
- **Does the grade lean on high-b_hit?** No — it leans the *opposite* way. The grade is built on the
  **TAUGHT detectors**, which are the **LOWEST-b_hit, highest-edge** group: `ob_taught` b_hit **0.345**
  edge **+13.8pp**, `fvg_n` **0.353** / +11.8pp, `propulsion2` **0.372** / +10.5pp (`summary.csv`).
  These **ARE** the low-b_hit taught-alpha firings the deep study says carry the edge. The grade is
  **already consistent** with "alpha in the low-b_hit tail."
- The **only** high-b_hit term is `htf_nest` (b_hit **0.518**, the single highest) — a **3%-of-book**,
  near-constant +1 flag, not the load-bearing ranker. "The grade leans on high-b_hit nest terms" **mis-
  states** its weight.

**Implies for what is SAFE:** b_hit-recalibration / "select low-b_hit alpha" is **diagnostic-consistent
with what the grade already does**, not a mandate to re-engineer it. The **`b_hit>0` gate** drops the
23.7%-of-book / 18.7%-win `b_hit==0` firehose — but those are **low-grade furniture**, and **iter-8
precision tunes already cut volume 7392→2155 (−71%) and flipped ungated to +0.52R**, i.e. most of that
mass is *already gone from the hi-tier*. The gate is **largely redundant**; its incremental effect *on
the +8R tier* is **unmeasured** (could trim a few hi-tier trades). **Re-derive before shipping — not
free.**

---

## 4. CONTRADICTION 3 — "mode-switch is the central missing piece" vs "tier survives cross-regime WITHOUT one"

**FRAME ARTIFACT — and the CROSS-REGIME DATA adjudicates it decisively AGAINST the deep study's claim.**

- The "missing mode-switch" is inferred from the **ungated symmetric frame**, where the marginal SMC
  levers **sign-flip UP↔DOWN** and a regime-blind grader averages them to mush: direction (LONG win
  0.480→**0.443** into DOWN; SHORT>LONG **11/11** DOWN stocks), HTF-alignment (**+10.5pp UP / −8.5pp
  DOWN**, z +3.2/−3.6), at-extreme (RANGE 60% → DOWN 32%). All true — **as marginal, ungated,
  symmetric stats.**
- But the +8R hi-tier is a **conjunction requiring bos + sweep + ote + phase + maturity SIMULTANEOUSLY**.
  That conjunction is *intrinsically* a **confirmed-continuation filter**: **BOS** = momentum break in
  the trade's direction; **sweep** = liquidity grab preceding the move; **phase** = Wyckoff alignment.
  A setup that passes all of them **is** a with-momentum entry. **The mode-switch is IMPLICITLY baked
  into the conjunction** — which is *why* no explicit regime classifier is needed.
- **The RR-asymmetry auto-sorts regime for free.** A counter-trend knife-catch (DOWN-LONG) has a small
  favorable excursion (mirror median ≈0.64 ATR) → never reaches the large target → **stops at −1R →
  lands in g1–g2 (both negative)**. A with-trend continuation short rides 3+ ATR → **large R → g5–g7**.
  The grade separates with-trend from counter-trend **without a regime term**, because the *target*
  does the gating.
- **THE DECISIVE EVIDENCE:** the frozen config on the **unseen 2024-Q4 BEAR tape (31/41 down)** — the
  *exact* regime where the −8.5pp DOWN sign-flip / knife-catch should destroy the tier — instead prints
  **+8.20R / win 62% intrabar, +8.07R / win 72% eod, monotone ladder, all 4 quadrants +, every stop
  mode**, and is **stronger** than the mixed tape. In a downtrend, Frame A's own numbers say SHORT edge
  is +0.08 and SHORT>LONG 11/11 — the conjunction naturally selects with-trend shorts, so a *more*
  trending tape makes the tier *better*. `_NEXT-ACTIONS` already drew the conclusion: the cross-regime
  PASS **downgrades the mode-switch from SURVIVAL to OPTIMIZATION.**

**Implies for what is SAFE:** the mode-switch is **NOT required** for the hi-tier and is **NOT a
mandate**. Its residual value (lift the *ungated* book, trim the counter-trend-long tail) is on the
**low tier**, marginal on the already-strong hi-tier. Building it is a **change to the frozen grade**
with a **large overfit surface** (fit to a 21-range/19-trend cross-section on ONE window). **RISKY;
optional optimization at best.**

---

## 5. THE DECISIVE QUESTION — DIAGNOSTIC, not MANDATE

**Verdict: the deep study is a DIAGNOSTIC of the MECHANISM (why the +8R works), NOT a mandate to change
the frozen config.** Three load-bearing reasons:

1. **Every deep-study finding and every ship-now tune was measured in FRAME A, and NONE was measured
   for its effect on FRAME B's +8R tier.** The synthesis says so itself ("the deep-study tunes were
   measured in frame A, not frame A's effect on frame B"). A Frame-A win is not a Frame-B action.

2. **The frozen config already contains the substance of the "safe" tunes, so shipping them is
   redundant-to-harmful:**
   - **T3 (`atr_buffer 0.25`) is ALREADY in `stops` in the frozen config** — it produced the +8R.
     "Shipping T3" is a no-op at best; re-applying/widening **widens the stop → shrinks the R-multiple
     denominator → directly attacks the +8R.** The deep study's *own* Frame-A number is **ΔExpR −0.03R**
     (it pays 0.25R on 17,422 deep losers to rescue 1,324 wins). **The correct Frame-B response to the
     "tight wick shaken 88%" mechanism is NOT to widen the stop — it is the `m5_close` production rule
     (don't stop on an intrabar wick, stop on an M5 close beyond SL), which ALREADY gives +8.35R ≈
     intrabar +8.20R.** T3's mechanism is real and **already handled without cutting R.**
   - The grade is **already built on low-b_hit taught detectors**; the b_hit==0 furniture is **already
     cut** by the iter-8 precision tunes.

3. **The changes the deep study frames as urgent (mode-switch, T2 anchor rewrite, b_hit recalibration,
   strip-detectors) are edits to the frozen grade whose effect on the +8R is UNMEASURED, and the
   cross-regime holdout proves the tier does not need them.** The T2/htf_nest analysis was even run at
   **`extremes.leg_pct=6.0`** (`htf_nest_bug` §Part-3) while the **frozen +8R config uses `leg_pct=2.0`**
   — a 2% reversal leg re-anchors far more readily, so the "median 4.87-ATR invisible-extreme cap /
   92%-never-re-anchor" severity is **measured on a different parameterization than the crown jewel.**
   htf_nest is already "priced into" the +8R.

**So: the deep study explains WHY the edge is regime-robust** — b_hit ranks *when/where* you traded,
the conjunction implicitly gates *continuation*, and the RR-asymmetry *auto-sorts* with-trend from
counter-trend — **which is exactly why it survived bear + mixed with a frozen config.** That is a
reason to **trust and protect** the frozen config, not to rewire it.

---

## 6. PER-CHANGE EDGE-RISK VERDICT (protect the +8R; when in doubt, RISKY)

| proposed change | frame it was measured in | effect on the +8R tier | verdict |
|---|---|---|---|
| **T3 — widen stop to wick ±0.25 ATR** | A (ΔExpR **−0.03R** even in A) | **already in frozen config**; re-applying widens stop → **cuts R-multiple**; mechanism already handled by `m5_close` | **RISKY — do NOT re-apply.** Highest direct threat to the crown jewel |
| **`b_hit>0` gate** | A (+0.19R on *ungated* book) | furniture already cut by iter-8; effect on hi-tier **unmeasured**, may trim hi-tier takes | **RISKY-ish — re-derive in Frame B first.** Not free |
| **no-blind (strip strength/width/stacking)** | A (AUC 0.49) | if grade doesn't read them → no-op; if it does → untested on tier | **LOW-MED — re-derive; likely harmless but verify** |
| **T2 — re-anchor EXT to live extreme / htf_nest fix** | A, and at `leg_pct=6` ≠ frozen `leg_pct=2` | edits a term inside the frozen grade; htf_nest already priced into +8R; unmeasured in B | **RISKY — full graded re-derive required** |
| **b_hit recalibration (isotonic/Platt)** | A | grade already selects low-b_hit taught alpha; rescaling the ranker unmeasured in B | **RISKY — re-derive** |
| **mode-switch / regime classifier** | A (marginal sign-flips) | downgraded to OPTIMIZATION by cross-regime PASS; marginal on hi-tier; big overfit surface | **RISKY — optional, not a mandate** |
| **Sustained-BULL adversarial test (frozen config)** | — (information only) | changes trust, not config | **SAFE — do this** |
| **Faithfulness co-location (winners vs 467 marks)** | — (information only) | changes narrative, not config | **SAFE — do this** |

**Rule:** the only genuinely SAFE moves are the two **PROVE** checks (they add information, they do not
touch the frozen config). Every SHIP/FIX/BUILD item must be run as a **graded A/B against the frozen
+8R, split by regime**, and adopted **only if the hi-tier net-R and the g1→g7 monotonicity do not
degrade.** Ship-into-config-blind = crown-jewel risk.

---

## 7. THE ONE REAL RESIDUAL FRAGILITY (not a frame artifact)

The +8R rests on the tight-stop RR-asymmetry, and `sl_anatomy` shows the literal taught wick is
**shaken out ~88%** (SL-hold 11.9% at exact edge) with **44% of eventual winners first tagged at the
stop**. In the intrabar sim a stop-touch = immediate −1R. **If real tick fills stop out those wick-
tagged winners, win% and R compress.** This is a genuine **fill-model / execution** risk (already the
#2 residual in `_NEXT-ACTIONS`, audit F9) — **but the data already bounds it:** the `m5_close`
production rule (stops only on an M5 *close* beyond SL, surviving intrabar wicks) gives **+8.35R ≈
intrabar +8.20R** on the bear tape. So the wick-noise fragility that T3 diagnosed is **already
neutralized by the production stop, at no cost to R.** The remaining unknown is **tick-granular fills**,
which is an *execution* question, not a *frame* or *edge-existence* question.

---

## 8. BOTTOM LINE

The two studies do not contradict — they **measure different quantities** (symmetric ±1-ATR first-touch
vs. graded RR-asymmetric net-R), and all three "contradictions" dissolve into that one mismatch. The
deep study is a **DIAGNOSTIC of the mechanism** (b_hit ranks when/where · the conjunction implicitly
gates continuation · RR-asymmetry auto-sorts with-trend from counter-trend), which is precisely **why**
the frozen config held **+8R monotone across an unseen bear tape**. It is **NOT a mandate** to change
the frozen config. **PROTECT the frozen +8R.** Run the two SAFE PROVE checks now; treat every SHIP/FIX/
BUILD tune as an unproven hypothesis that must survive a **graded, regime-split re-derive against the
+8R** before it is allowed near the config — **and treat T3's stop-widen as an active threat to the
crown jewel, not a safe ship.**
