# r4 — Is the taught fade a real automatable edge? Balanced adversarial analysis (2026-07-23)

Inputs: 32 LIVE-traded WINNING taught trades / 7 stocks; this session's validation
(runs/validate/{REPORT,ANALYSIS}.md — 90% of drawn sweeps + 96% of targets on real tape,
profile = "range-extreme fade of a coil"); the prior null battery (memory
trader-fade-thesis-falsified + docs 34/36). Two cases, then a weighed verdict. No cheerleading,
no nihilism.

---

## CASE A — NOT a real automatable edge (the skeptic)

### A1. Survivorship: 32/32 winners is a measurement of the *selector*, not the *setup*
Every trade in the corpus is a winner the user chose to show. 96% target-hit is therefore a
**selection statistic, not an expectancy** (REPORT.md §3, ANALYSIS.md caveat both say this
outright). The population base rate for *anatomically identical* setups is already measured and
brutal: the program's ML pass found **16% run / 41% die outright, 0.52 AUC to separate winner
from losing twin ex-ante on LTF chart features**. So the visible 32 are drawn from a pool where
near-identical zones fail ~4-in-10 and only ~1-in-6 run — and nothing on the LTF chart tells you
which in advance. The validation proved the drawings are *faithful* (not fabricated); fidelity of
a winners-only sample says nothing about win rate.

### A2. Recognition ≠ edge — and recognition was never the weak link
"The structures are really on the tape" is true and already known: the zone-finder rediscovered
the user's hand-drawn zones **8/8**, ML deciles were monotone, yet the family still netted zero.
The program's own verdict: *"Recognition is NOT the weak link (finder 8/8, ML deciles monotone);
payment is."* Confirming 27/30 sweeps and 29/30 targets on real data re-proves recognition — the
part that was never in doubt — and leaves payment (expectancy after cost) exactly where it was.

### A3. The tiny-stop RR is destroyed by realistic entry+stop slippage — quantified in R
The entire RR is *manufactured by the stop*, not the target (doc 34 §6: targets are ~constant
50-90pt; the 1:15 monsters are the ones with 3-4pt stops). So price the friction against a
**3-pt stop on a ₹1200 stock → R = 3.00 pts = 0.250% of price**:

| friction component (per round trip) | pts | as R (÷3) | hits |
|---|---|---|---|
| exchange+regulatory+brokerage toll (~0.06% of price — program's measured figure) | 0.72 | **0.24R** | every trade |
| entry slippage (½-spread + adverse fill; spread ~₹0.4 typ.) | 0.40 | **0.13R** | every trade |
| stop-exit slippage (½-spread + fast-move slip, ~1.0-1.5pt) | 1.25 | **0.42R** | losers |
| target-exit (limit fill, ~0 slip) | 0 | 0 | winners |

- A nominal **−1.0R** stop-out realizes ≈ **−1.79R** (−1.0 − 0.24 − 0.13 − 0.42).
- A nominal **+9R** target realizes ≈ **+8.6R** (limit exit eats only toll+entry).
- **Gap-through** is the tail killer: it *materialised live* on Da_jul_short (3-pt stop → STOP_GAP,
  REPORT.md §2), and the program's M1 fill-through was measured at **2-3R past the stop** and
  **−4.2R** for 1-2m structural stops (REFINE). A single opening gap on a 3-pt stop realizes
  **−3 to −5R**.
- The fixed toll alone is a **24% haircut on R every trade** because a 0.25%-of-price stop is only
  ~4× the ~0.06% round-trip toll. The stop being tiny — the thing that manufactures the RR — is the
  same thing that makes the fixed toll enormous *relative to R*.

Net effect: the loser side is ~−1.8R not −1.0R, winners keep ~96% of R, and the tail gaps are
catastrophic. The paper "1:9" geometry is arithmetic on prices that don't fill at those prices.

### A4. The multi-R payout is a ~3% tail, so expectancy is set by the losing mass
The R-ladder measurement already settled the distance question: **reach-2R ≈ 35% across ALL
grades/types/stacks, reach-5R ≈ 3%, reach-10R ≈ 0.3%** — *"current grammar predicts DIRECTION not
DISTANCE."* The +9.9R / +9.6R paper winners in the 8-trade replay are that ~3% tail. Take the whole
population and the expectancy is dominated by the trades that stop or trail out small, not the tail
that runs 9R. This is not a hypothesis — the program measured it: taught grade at its **best**
form netted **+0.008 to +0.04R** daily (survivorship-inflated, so true ≤ that) and **−0.27R**
intraday; the tiny-stop intraday form specifically measured **−1.32R/trade** economic replay and
**−4.2R** structural-stop fill-through. *Near-zero-to-negative forward returns are the measured
result, not a fear.*

### A5. Identification difficulty + uncodable discretion
The user's own frequency is *"3 trades from 50 stocks"* — the deep-aligned mature state is **rare**,
which means (a) tiny n / wide CIs forever, and (b) in real time you are hunting a needle while the
false-positive noise ratio was measured at **40:1**. And the discretion that *made* these winners is
exactly what a machine loses: mechanical replay of the drawn entry/SL/target hit target **only 4/8
even on the hand-picked winners** (REPORT.md §2). Skip decisions, entry timing, and side-asymmetric
management (short = one retest; long = grind/pyramid, doc 34-C) are doing real work that no coded
rule in the corpus captures.

**Case-A bottom line:** every load-bearing claim of the bull case is either a selection artifact
(A1, A2), already-measured-negative (A4), or arithmetically dismantled by friction on the very tiny
stop that creates the RR (A3). The program has closed this family *"at every timeframe with max
sample"*; this corpus adds faithful winners, not a new expectancy.

---

## CASE B — There IS something genuinely new/untested (the honest counter)

The prior nulls were exhaustive but they measured *specific things*. Two of the four candidate
levers here were genuinely **not** in that battery; two are re-descriptions of measured nulls. Being
honest about which is which is the whole value of this case.

### B1. GENUINELY UNTESTED — HTF-alignment-depth × HTF-maturity as an *ex-ante, causal* gate on a *constructed loser set* (doc 36)
This is the one structurally new argument in the whole corpus, and its novelty is **mechanistic**,
not just another confluence:
- The prior nulls measured features **at the entry bar** on the **LTF chart** (0.52 AUC). Doc 36's
  claim is that the discriminator is **not on the LTF chart at all** — it is the HTF context, which
  **formed earlier and moves slowly**, so it is *knowable pre-entry*. A causal, ex-ante variable is
  a different object than the LTF-bar features the nulls falsified. The nulls could be right *and*
  this be real, because they measured the wrong surface.
- It **dissolves the survivorship objection without loser screenshots**: the loser class is
  *definable from data* as every LTF decisional zone whose HTF context disagrees. That is a test we
  can run, not a plea for more winners.

Honest bracketing (why this is a narrow residual, not open field): the **3-TF direction stack alone
is already measured dead** (full nested fractal daily→H1→M5 + 3-TF stack = +0.5-1.4pp, 0 positive
holdout cells), and **compression/maturity as a magnitude predictor is already measured FLAT**
(reach-2R ~35% across all grades). So neither *component* lifts alone. What is genuinely untested is
strictly their **conjunction as a monotone gate** — alignment-DEPTH (0/1/2/3 same-direction TFs)
**AND** HTF-maturity (HTF at a compressed range extreme) — measured on the *constructed loser set*
with causal pre-entry HTF. Doc 36 §7 defines exactly this and it has **not** been run. The priors
are discouraging, but the specific joint, ex-ante, loser-separated measurement is real and open.

### B2. GENUINELY UNTESTED — the structural OUTER-WICK stop vs the body-edge / fixed-ATR stops that measured −4.2R (docs 35, 36 §2)
The fill-through nulls (−4.2R, −1.32R) used **arbitrary sub-ATR / body-edge stops** (0.15×ATR,
1-2m structural-*edge*). Doc 35's feature-anatomy pass found the user actually stops **beyond the
outer WICK of the sweep spike** — past the liquidity pierce, precisely where fill-through momentum
*exhausts* rather than where it accelerates. That is a **different stop object**, and the decisive
framing (doc 36 §2, t29) is untested: *"does a STRUCTURAL 1m stop below a valid nested OB survive
where an ARBITRARY 1m stop (−4.2R) did not."*
Honest bracketing: the GEO door swept **stop-scale k=1.5→10×ATR** and found gross decays *faster*
than toll at every widening — so buying fill-through survival by widening is net-negative *if the
outer-wick stop is just a wider ATR multiple*. The untested residual is narrow but real: the
outer-wick stop is a **structural placement rule** (a specific price past a specific spike), not a
fixed ATR fraction, and structural-vs-matched-ATR fill-through survival was never compared head to
head. This is the single lever that could rescue A3.

### B3. RE-DESCRIBING A MEASURED NULL — the stacked-zone + swept-EQ-pool + contracting-range conjunction
Feels new, isn't. Stacking was measured (`g = nst≥4 + parent_ok + depth_alive` → respect +2.69pp,
real, but net still negative; *"stacking doesn't lift causally — proven"*); EQ-pool sweeps and
contracting-range were in the taught grade; chains/cascades/filters = 0/196 configs holdout. The
conjunction lifts *respect* (direction) ~58→61% — already known — and leaves *magnitude* flat.
This is the direction lever that is real and already priced as insufficient.

### B4. SPLIT — the draw-on-liquidity target chain / management
- **Target = far liquidity POOL as a *distance/runway* predictor**: GENUINELY UNTESTED. The RR
  ladder tested *fixed* R-targets (2R optimal) and trailing; it never tested whether *"a fat
  untouched pool far away"* lifts **reach-5R share ex-ante** — memory explicitly lists this as an
  open magnitude-hypothesis. This directly attacks the "direction-not-distance" ceiling (A4) that
  kills the RR, so it matters.
- **Cascade re-entry + side-asymmetric management**: UNCODABLE from the corpus — it is the
  discretion that mechanical replay already lost (4/8). Not a testable lever without a rule spec.

**Case-B bottom line:** exactly **two** levers survive honest scrutiny as *untested*: (1) the joint
**deep-HTF-alignment × HTF-maturity** gate measured on a *constructed loser set* with causal
pre-entry HTF (B1) — the direction/win-rate lever with a genuine mechanistic reason to escape the
LTF-feature nulls; and (2) the **structural outer-wick stop's fill-through survival** vs the
body-edge stops that measured −4.2R (B2) — the RR-preservation lever. A third, softer candidate is
**liquidity-pool DISTANCE as an ex-ante magnitude predictor** (B4). Everything else is a
re-description of something already measured null.

---

## VERDICT

**Honest probability this becomes a robustly profitable AUTOMATED system: ~10-12%.**

Reasoning, weighed:
- *Against* (why not lower): doc 36's ex-ante/causal argument is **not** refuted by the LTF-feature
  nulls — those measured the entry bar; HTF alignment is a slow, pre-known variable on a different
  surface. The outer-wick structural stop is genuinely distinct from the −4.2R body-edge stop that
  was measured. Both are real, unmeasured levers with mechanistic stories, and the loser class is
  constructible without more winners. This is not nothing.
- *Against* (why not higher): the profit requires **two multiplicative gates to BOTH clear** —
  (A) alignment-depth separates winners from constructed losers ex-ante, AND (B) the tiny structural
  stop survives fill-through net-positive after realistic slippage. Each is uncertain and the
  *nearest measured proxy to each is null-or-flat*: the 3-TF stack is dead (+0.5-1.4pp), maturity-as-
  magnitude is flat, the GEO stop-scale sweep says widening loses at every point, and the family's
  best measured net across the entire program is ≈ 0 to −0.1R. The base rate of this program is a
  wall of nulls at every timeframe with 8.4M sims. A rare (3-in-50) setup also guarantees thin n /
  wide CIs even in the best case. The genuinely-new levers are each **one adjacent measurement away
  from a null they closely resemble** — that is exactly the profile of a lever that usually resolves
  null, occasionally not. ~1-in-9.

This is above the program's implicit prior for "another confluence" (≈ 0, all measured dead) because
B1's causal ex-ante argument and B2's structural-stop distinction are the first two candidates that
are *not* re-tests of a falsified LTF surface — but it is well below even odds because both must
clear and both resemble measured nulls.

**The SINGLE measurement that would move it most:** run doc 36 §7 — construct the loser class (every
LTF decisional zone whose *causal, pre-entry* HTF context disagrees; no loser screenshots needed) and
measure **net R after realistic fill-through of the deep-aligned + HTF-mature tier vs the depth-0
tier, using the structural outer-wick stop, on a 4-way holdout.** One scalar decides it:
`net_R(deep-aligned+mature) − net_R(depth-0)`, after fill-through.
- If depth does **not** separate → the 32 were survivorship, HTF-alignment is another dead flag →
  method is null, close it (probability collapses to ~2%).
- If depth separates **but** the deep tier still doesn't clear toll after fill-through → the same
  edge≈toll wall as every prior rung → close it.
- If depth separates **and** the deep tier clears toll after fill-through with the structural stop →
  the method is real and we know exactly why (probability jumps toward ~50%+).

That one test collapses gate A (loser separation) and gate B (fill-through survival) simultaneously,
needs no new data the program can't construct, and is the only measurement that can turn ~11% into
either ~2% or ~50%. Everything short of it — including more faithful winners — leaves the probability
exactly where it is.
