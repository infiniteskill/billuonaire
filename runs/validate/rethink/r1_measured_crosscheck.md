# r1 — ADVERSARIAL CROSS-CHECK of this session's conclusions vs the MEASURED record

Date 2026-07-23. Auditor pass over the THIS-SESSION optimistic conclusions
(`runs/validate/REPORT.md`, `runs/validate/ANALYSIS.md`, `dev/plan/30-LESSONS.md`
Lessons 20–21) against the ALREADY-MEASURED record
(`runs/study/summary.csv`; prior verdicts `runs/taught/ASSEMBLE.md`,
`runs/taught/RLADDER.md`; `runs/long60/FACTS.md`, `NATIVE30.md`;
`runs/ladder/H1GRID.md`, `DGRID.md`).

> Provenance note: the task named `runs/taught/FACTS.md`, `GEO.md`, `NATIVE30.md` —
> those live under `runs/long60/`, not `runs/taught/`. Read from there. Numbers below
> are quoted verbatim from the measured files.

## The measured baseline (what the record actually says)
- **Recognition is real but small.** Assembled top-tier respect: H1 **58.5%** vs 55.7% null
  (+2.69pp, t=19.4); daily **61.5%** vs 58.8% (+2.58pp, t=21.6). Sign-stable in holdout.
- **Net after toll ≈ 0-to-negative.** H1/intraday **−0.27R/trade** at 2R (gross +0.069R,
  cost ≈0.33R); NEGATIVE in all 4 holdout cells and at every R rung (RLADDER).
  Daily 2R absolute net **+0.040R** (survivorship-inflated) / **+0.173R EXCESS** over a
  matched-drift null — real but thin, and turns slightly negative in late-period holdouts.
- **Higher R is strictly worse; peak = 2R on both frames** (RLADDER).
- **FACTS measured breakeven at the tight-stop geometry ≈ 59% hit** — i.e. recognition
  (58.5%) sits *just below* breakeven by construction.
- **The +4–6pp detector edges do NOT clear the toll.** H1GRID: "virtually every alive cell
  has negative net_R"; pooled net_R ≈ the null (−0.194 vs −0.195).

---

## VERDICT TABLE

| # | This-session claim | Verdict | Measured number that decides it |
|---|---|---|---|
| 1 | "Anatomy real: 90% swept, 96% target reached" (as an EDGE) | **CONTRADICTED (as edge) / consistent only as fidelity** | 90/96% are on 30 hand-picked WINNERS (selection). Full-sample **sweep SWEEP fwd12 = −0.0146 (NEGATIVE)**, n=6021. REPORT.md itself: "96% target-hit is selection, not expectancy." |
| 2 | "RANGE-fade of a coil is the edge; corr(ADX,move)=−0.26" | **CONTRADICTED** | Only full-sample compression measurements are NEGATIVE: **BOX_ON_LEVEL edge −2.3pp** (n=956), **PO3_DIST −26.7pp** (n=6). corr=−0.26 is a within-winners magnitude corr on **n=30**, not an edge vs baseline. |
| 3 | "Wyckoff = new long-TF lever; VOLUME = untested confirmation layer" | **CONTRADICTED** | Both ALREADY measured. **volume VSA +5.3pp, n=7260** (2nd-largest study cell — not "untested"). **wyckoff PHASE +4.6pp** (n=4376), **SPRING +38pp but n=8**, **UPTHRUST −9.2pp (NEG), n=6**. "new/untested" is false; edges are sub-toll. |
| 4 | "Semi-auto ~55% profitable / mechanical ~25-30%" | **UNSUPPORTED / INVENTED** | No such number exists anywhere in the repo. No semi-auto system was ever measured. Measured mechanical win% (NATIVE30) = **32–37%, ALL cells net-negative ("dead", −0.16…−0.66R)**; H1 2R hit 31.1%, daily 33.8%. |
| 5 | The general optimism (edges tradable, method "works") | **UNSUPPORTED** | Record = recognition real but **net ≈ 0-to-negative after toll, higher R strictly worse, sweep/FVG fwd12 negative.** The ONE defensible positive (daily-2R excess +0.173R) is thin, regime-fragile, and NOT cited this session. |

---

## CLAIM-BY-CLAIM DETAIL

### 1. "Anatomy real: 90% swept, 96% target reached"
- **Where the numbers are true:** REPORT.md, on the 30 hand-drawn taught trades located on
  real tape. 27/30 swept (90%), 29/30 target-reached (96%), median MFE +12.4% / **+17.4R**
  (hindsight-drawn tiny stop). These are legitimate as **anatomy-fidelity** — the drawings
  match the tape.
- **Why target-reached is NOT a meaningful edge:** the 30 are the user's executed WINNERS.
  96% target-hit is **selection**, and the +17.4R uses stops drawn with hindsight. REPORT.md
  concedes this verbatim (lines 71–72: "96% target-hit is selection, not expectancy. This
  validates ANATOMY FIDELITY, not PROFITABILITY").
- **The full-sample refutation:** on 6,021 unfiltered sweeps the **forward 12-bar return is
  NEGATIVE (fwd12 = −0.0146)**. So "sweep → price reaches target" is not a forward edge once
  you stop conditioning on winners. Same pattern in the FVG family: **CE_HOLD fwd12 = −0.017**
  (its +8.8pp hit-edge is the largest in the study yet its forward drift is negative).
- **Verdict: CONTRADICTED as an edge; CONSISTENT only as anatomy fidelity.** Target-reached
  on a winners-only, undefined-window set is a recognition/selection artifact.

### 2. "RANGE-fade of a coil is the edge; corr(ADX,move)=−0.26"
- **Source:** ANALYSIS.md, DIMENSION 1, computed on the **30 winners** over a fixed 40-bar
  daily window. corr(ADX, move-size) = −0.26 describes the *magnitude spread among winners* —
  it is not a hit-rate or net-R edge versus any baseline, and n=30.
- **The measured compression detectors go the other way:** the study's compression cells are
  **BOX_ON_LEVEL edge −2.3pp (n=956, NEGATIVE)** and **PO3_DIST −26.7pp (n=6)**. On full
  data the "coil" detector under-performs its own baseline. DAILYPOI/H1GRID echo: coil-anchored
  entries are net-negative.
- **Verdict: CONTRADICTED.** The only full-sample compression measurement is negative; the
  −0.26 correlation is a within-winners artifact, not evidence of a tradable coil edge.

### 3. "Wyckoff = new long-TF lever; VOLUME = untested confirmation layer"
- **Both are already in `runs/study/summary.csv`:**
  - `volume,VSA,7260, edge +5.3pp, fwd12 +1.16` — the 2nd-largest cell in the entire study.
    Calling volume "untested" is factually wrong; it is one of the most-tested layers, and its
    +5.3pp hit-edge sits in the same band ASSEMBLE shows does NOT clear the ~0.33R H1 toll.
  - `wyckoff,PHASE,4376, +4.6pp` (real but modest, sub-toll band);
    `wyckoff,SPRING,8, +38.1pp` (**n=8** — statistically meaningless; the task's own note flags it);
    `wyckoff,UPTHRUST,6, −9.2pp` (**NEGATIVE**, n=6).
- The enthusiasm concentrates on SPRING (the +38pp long trigger of Lesson 21) which rests on
  **8 events**, while the short mirror (UTAD/UPTHRUST — what t31 SBILIFE was celebrated as) is
  measured **negative**.
- **Verdict: CONTRADICTED.** "New/untested" is false for both; measured edges are PHASE +4.6pp
  / VSA +5.3pp (sub-toll), SPRING n=8, UPTHRUST negative.

### 4. "Semi-auto ~55% profitable / mechanical ~25-30%"
- **Grep of the entire repo finds no such figure.** There is no measured "semi-auto"
  (discretion-assisted) system anywhere. This claim is **invented**.
- **What IS measured, mechanically:**
  - NATIVE30 (full 30m SMC stack, positional): win% (net>0) **31.9–43.2%**, and **every single
    cell is net-negative — labelled "dead"** (net −0.16 to −0.66R).
  - Assembled H1 2R hit **31.1%**; daily 2R hit **33.8%** — both with negative/thin net R.
  - The 8-trade 5m replay was **4/8 = 50%** target — and those 8 are hand-picked winners.
- So the measured mechanical *win rate* is ~31–37% but always with **negative net R**; there is
  no measured basis for "25-30% mechanical" as a workable floor, and none whatever for "55%
  semi-auto profitable." The claim also conflates win% with profitability (net R), which the
  record keeps separate on purpose.
- **Verdict: UNSUPPORTED / INVENTED.**

### 5. The general optimism
- The measured record is unambiguous: recognition is real (+2.6–2.7pp respect-lift, t up to
  21.6) but **net after cost ≈ 0-to-negative** — H1 −0.27R/trade at 2R, negative at every rung
  and every holdout; daily absolute +0.04R (survivorship) / +0.173R excess (thin, decays late).
  **Higher R strictly worse, peak 2R.** sweep and FVG forward returns are negative. Every
  +4–6pp detector edge fails to clear the toll (H1GRID: alive cells still net-negative).
- The single positive the record supports — **daily-positional 2R, +0.173R excess over drift,
  holdout-stable** — is far more modest than this session's framing, and none of the session
  docs cite it.
- **Verdict: UNSUPPORTED.** The measured record supports none of the session's hopeful framing;
  the one real edge is thin, positional-only, and was not invoked.

---

## OMITTED / SHOULD-HAVE-CITED (present in the record, absent from the session's optimistic docs)

| Omitted measured fact | Value | Why it matters to a session claim |
|---|---|---|
| Assembled economic verdict (ASSEMBLE/RLADDER) | H1 net **−0.27R/trade**, daily net +0.04R / excess +0.17R, **higher R strictly worse** | The frozen assembled system is net-negative intraday — the anchor for any "does it work" claim; never cited in REPORT/ANALYSIS/Lessons 20-21. |
| sweep SWEEP fwd12 | **−0.0146 (NEG)**, n=6021 | Directly undercuts anatomy claim #1 (swept-extreme → move). |
| fvg CE_HOLD fwd12 | **−0.017 (NEG)**, n=2542 | Largest FVG hit-edge (+8.8pp) has negative forward drift. |
| compression BOX_ON_LEVEL / PO3_DIST | **−2.3pp / −26.7pp (NEG)** | Refutes the coil-edge thesis (claim #2). |
| structure CHOCH / BOS | **−20.2pp / −22.4pp (NEG)** | Lesson 21 maps SOS/SOW↔BOS and phase-change↔CHoCH as additive; both structure detectors are strongly negative on hit. |
| breaker BREAKER_RETEST | **−8.0pp (NEG)**, n=785 | Lesson 4 calls breaker "+19.6pp strongest measured ingredient" (a different port); the study's breaker retest is negative — tension unacknowledged. |
| wyckoff UPTHRUST | **−9.2pp (NEG)**, n=6 | The short-side Wyckoff (UTAD/t31 celebration) is measured negative. |
| wyckoff SPRING sample | **n=8** | Lesson 21's "key long trigger" edge rests on 8 events. |
| FACTS measured breakeven | **≈59% hit** at the tight-stop geometry | Recognition (58.5%) sits just BELOW breakeven — the celebrated "58-61% respect" is by construction not enough. |
| Round-trip cost toll | **≈0.33R (H1) / ≈0.12R (daily)** | Every +4-6pp edge must clear this and (on H1) doesn't. |
| NATIVE30 mechanical stack | ALL cells **"dead"** (net −0.16…−0.66R) | Direct measured counter to the "mechanical" leg of claim #4. |

---

## BOTTOM LINE
Of the five audited claims: **#1 contradicted-as-edge, #2 contradicted, #3 contradicted,
#4 invented, #5 unsupported.** The session repeatedly upgraded *recognition on winners*
into *tradable edge*, presented ALREADY-measured layers (wyckoff, volume) as new, built a
coil-edge thesis the full-sample detectors refute, and asserted profitability numbers
(55%/25-30%) with no measured basis — while omitting the standing economic verdict that the
assembled system is **net ≈ 0-to-negative after costs, with higher R strictly worse.**
