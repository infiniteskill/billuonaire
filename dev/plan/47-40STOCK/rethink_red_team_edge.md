# 47 — RED-TEAM: is the +6.13R / +8.20R graded edge illusory or fragile?

**Mandate.** Build the STRONGEST adversarial, quantitative case that the crown-jewel edge is fake or
fragile — then protect it. Every claim carries a number + n. Method: read `decision.py` (the grader) +
`derive_tradebook.py` (the sim) as source, re-derive the tier arithmetic from `tb_2024q4_40.txt`, and run
light joins on `study40_2026/evidence.parquet` (38,462 decided firings) + the `derive_work/*.jsonl`
verdict journals. **No pipeline/derive re-run** (hard rule).

**THE EDGE UNDER ATTACK (frozen `taught_profile/config.json`, `decide()` AND-chain, large-R runway target):**
- 2026 (mixed/range): hi-tier grade≥4 **+6.13R/win49%**; ungated **+0.52R**.
- 2024-Q4 BEAR holdout, unseen, frozen: intrabar **+8.20R/win62%**, eod **+8.07R/win72%**, all 4 quadrants +,
  grade ladder monotone (g1/g2 neg, g3 breakeven, g4 +5.4, g5 +8.3, g6 +9.5, g7 +8.6R).

---

## VERDICT (top-line)

**I could NOT break the +8R with the cost, thin-tier, censoring, or squareoff attacks — it survives all
four with large margins.** The edge is REAL AS MEASURED and the 44-AUDIT causal claim survives a fresh
source re-read. **But its NATURE is not what the "monotone grade ladder" story implies.** The edge is a
**reward:risk-asymmetry harvester (~15:1 tight-stop / far-runway), NOT a win-prediction engine.** The grade
ladder rises because grade **mechanically couples to the R-multiple of the target**, while the deep study
proves the same grade terms carry **~zero win-discrimination** (corr(strength,win) = **−0.005**;
per-detector edge ≤ ±2.6pp; MFE≈MAE 2.48/2.46). Its two winning tapes are **both non-bull, both
short-tilted** (frame-A SHORT wins 52.9% vs LONG 46.7%). **The single most likely way it is fake: it is a
fade that harvests RR in oscillating / mean-reverting tapes, and neither test window is the regime that
kills a fade — a sustained low-pullback trend where the nearest-opposite-extreme target stops getting
tagged before the 0.12%-tight stop.** That regime is UNTESTED. **And the biggest edge-PRESERVATION danger
is internal: every frame-A "ship-now" tune (b_hit gate, T3 stop-buffer, mode-switch, T2 re-anchor) perturbs
the exact levers — stop distance, target distance, direction — that GENERATE the +8R in frame B, and NONE
has been measured in frame B. A symmetric-frame win is very plausibly a graded-frame loss.**

---

## ATTACK 1 — contamination / lookahead (re-audit the 44-AUDIT "0 contamination")

Tried to break it from source. **It holds.**

- `derive_tradebook.py:109` builds `Orchestrator(... journal_dir=..., **no level_dir**)` → `pipeline.py:94`
  `self.levels = [] ` (empty start). Levels are grown **incrementally, bar-by-bar** by
  `level_engine.update(self.levels, c5, atr)` (`pipeline.py:253`) as each M5 candle streams. So `ctx.levels`
  at decision time contains only levels realized from bars **≤ now**.
- `decision.py` reads only `evidence` (the tap passes `evs + [e in ctx.evidence_history if e.ts ≥ cutoff]`,
  cutoff = 20 M5 bars back — strictly past) and `ctx.levels`. No detector, no scanner, no future series.
- The runway **target** (`_runway`, decision.py:50) = nearest opposite `EXT_H/EXT_L`. Per `htf_nest_bug.md`,
  `extremes.py:218` emits an EXT level **only after** a ≥6% confirmed reversal leg — i.e. the level becomes
  visible only *after* price already bounced off it. The target is therefore a **strictly-past, already-
  defended level**; the forward `_sim` walks a **separate pass** over stored 1m/5m to score whether price
  returns to it. No future price enters the decision.
- **Concession + reframe:** there is no leak, but the target being a *confirmed, already-defended* pivot is
  precisely a **mean-reversion target** — the reason the fade "works" is that it aims at levels the tape has
  proven it respects. That is not contamination; it is the *mechanism* (see Attack 5). Contamination-audit
  and regime-fragility are the same fact seen from two sides.

**Residual I cannot verify by reading:** per-detector causality of every one of the 14 taught detectors.
Spot-checks (extremes, htf_nest) both *lag* (conservative), so leakage is unlikely — but a full
detector-by-detector causality proof was not in scope and remains an open (low-probability) hole.

**Attack 1 verdict: FAILS to break the edge.** 0-contamination survives a source re-read.

---

## ATTACK 2 — is the tier net-R load-bearing on thin high-grade cells (g7 n=323, g8 n=22)?

Recomputed the 2024-Q4 intrabar tier with cells removed:

| tier subset | n | win% | gross | **NET/trade** |
|---|---|---|---|---|
| hi ≥4 (all) | 3001 | 62 | +9.37R | **+8.200R** |
| **excl g7,g8** | 2656 | 61 | +9.38R | **+8.177R** |
| excl g6,g7,g8 | 1653 | 57 | +8.59R | +7.352R |
| g5+g6 only | 2095 | 64 | +10.06R | +8.913R |
| g4 alone | 561 | 50 | +6.82R | +5.428R |

Dropping g7+g8 moves the tier by **−0.023R** (+8.200 → +8.177). The tier rests on **g5 (n=1092)** and
**g6 (n=1003)**, both large-n, both +8–9.5R. **The thin cells are NOT load-bearing.**

**Attack 2 verdict: FAILS.** This one is a point *for* the edge.

---

## ATTACK 3 — cost-model realism / what cost flips the tier to breakeven?

Modeled cost (`cost_R`, derive:36) = `0.1309% of price/round-trip ÷ risk` + `Rs40/Rs500 = 0.08R` flat.
On the hi-tier: gross **+9.37R**, net **+8.20R** ⇒ modeled cost **1.172R/trade** (implied avg stop
**0.120% of price** — a *tiny* ~0.42-ATR wick, consistent with `sl_anatomy`).

- Breakeven needs cost = 9.37R ⇒ **×8.0** the modeled cost. Even **doubling** cost (→2.34R) leaves **+7.0R**.
- The cost fraction is **leverage-invariant** (it is cost-per-share ÷ risk-per-share; both scale with qty),
  so the 5× leverage does not secretly under-count it. Cost is genuinely *heavy* here (>1R/trade), which is
  conservative, not optimistic.

**One real optimism (flagged, bounded):** intrabar mode caps every stop loss at **exactly −1.0R** — no
slippage *through* a 0.120%-wide stop. Real fills on a fast 1m move blow past such a tight stop
(−1.5..−3R). The `m5_close` mode (fills at the M5 close beyond sl, loss unbounded) is the stress proxy and
costs only **−5%** (+8.20 → +8.35R stays, hi-tier held). True fill sits between the two.

**Attack 3 verdict: FAILS to break; ×8 margin.** Flag the tight-stop slippage model as the one place to
harden (see decisive test).

---

## ATTACK 4 — is eod win-72% a squareoff artifact hiding losers?

eod outcomes: stop 1991 / gap 1071 / target 2401 / **eod 1513**. The 1513 forced 15:10 closes are booked at
their **actual R** — net-R already counts them honestly. eod net **+8.07R** ≈ intrabar **+8.20R** (−1.6%).
The 72% "win" is inflated by reclassifying small-positive squareoffs as wins, **but net-R does not move**.
Critically, **eod closes MORE trades (6976) than intrabar (6925)** ⇒ intrabar drops almost no trades as
timeouts, and eod has **zero censoring** — so the edge is not a "timeout-drop" survivorship artifact either.

**Attack 4 verdict: FAILS on net-R.** Caveat: quote net-R, never win% — win% is a misleading lens here.

---

## ATTACK 5 — REGIME favorability (the strongest vector) + the MECHANISM reframe

### 5a. The ladder is R-MULTIPLE scaling, not win-skill (the load-bearing finding)

Decomposing each 2024-Q4 grade into (win rate) × (avg winner-R, assuming loss=−1R):

| grade | win% | avg winner | RR | breakeven-win (gross / net) |
|---|---|---|---|---|
| g1 | 27 | +5.2R | 5:1 | 16% / **51%** → LOSES (net −1.5R) |
| g2 | 28 | +5.6R | 6:1 | 15% / 48% → LOSES |
| g3 | 28 | +11.2R | 11:1 | 8% / 26% → breakeven |
| g4 | 50 | +14.6R | 15:1 | 6% / **15%** |
| g5 | 61 | +16.2R | 16:1 | 6% / 13% |
| g6 | 68 | +16.2R | 16:1 | 6% / 12% |
| g7 | 71 | +13.9R | 14:1 | 7% / 13% |

Two effects compound across the ladder: **win rate 27%→71%** AND **avg winner-R 5R→16R (≈3×)**. The
R-multiple triple is **mechanical**: the grade terms that define a high grade — `ote` (a *deeper* extreme →
a *farther* opposite runway) and `nest` (a *tighter* CE stop) — literally place entry farther from target
and stop closer, i.e. they encode **how big the RR is**, not **how likely the win**. Proof it is not win-
skill: on the symmetric 1:1 parquet (frame A, 38,462 decided) **corr(strength,win)=−0.005**, and the grade's
own component detectors carry ~0 edge (htf_nest **−2.6pp**, sweep +2.4, wyckoff +0.6, ob_taught −0.5, fvg_n
−0.3, orderblock 0.0); only b_hit ranks win (corr **0.45**, and it is anti-calibrated). **Give g1's
coin-flip 27%-win setups a g5-sized 16R target and they turn profitable** (0.27×16 − 0.73 − cost ≈ +1.4R).
So a large share of the "monotone grade edge" is the grade acting as a **target-distance proxy**, applied to
entries that the deep study shows are directionally coin-flips.

This is NOT "fake" — a bigger realized RR on a coin flip IS a real edge. But it relocates the entire
question from "is the grader smart?" to **"is the ~15:1 RR realizable across regimes?"**

### 5b. Both winning tapes are non-bull and short-tilted

- Frame A (2026 symmetric): **SHORT win 52.9% vs LONG 46.7%** — a structural **+6.2pp** short edge baked
  into this window; MFE≈MAE (2.48/2.46) confirms no directional excursion edge, only which barrier tags first.
- Regime labels: 2026 = 21 range / 8 up / **11 down**; 2024-Q4 = **31/41 down** (bear). **Neither is a
  sustained bull.** The deep study's own headline (`_SYNTHESIS` (a)/(c)) is that every SMC lever
  **sign-flips UP↔DOWN**. So "cross-regime holdout" is really **two flavors of not-bull**.
- Journal cross-check (production F1 path, a proxy — not the derive tier): 2024-Q4 high-grade verdicts are
  **61% LONG / 39% SHORT**; 2026 ≈ 50/50. Reading: the fade generates *both* directions; in an oscillating
  bear the nearest-opposite-extreme target gets tagged **both ways** (bounces reach the nearest prior high
  for longs; continuation reaches the nearest prior low for shorts). That is exactly why a *fade* survives a
  *trend* here — and exactly what a low-oscillation tape would remove.

### 5c. Why the RR cushion makes win-rate erosion a WEAK kill vector

At the tier's ~15:1 RR, **net breakeven win rate is ~12–15%.** Actual win is 50–71%. To break the tier by
win erosion alone you must delete **35–55pp** of win rate. The largest regime win-swing the deep study
measures is ~10pp (one cell, at-extreme 60%→32%, is 28pp). Even a *severe* inversion (−25pp → ~35–45% win)
leaves the tier **deeply positive** purely on RR. **So win-rate erosion does NOT break this edge.**

### 5d. The one regime that DOES break it

The only way to kill a ~15:1 fade is to make the **realized R-multiple collapse**, not the win rate:
a regime where price **does not return to the nearest opposite extreme** before the 0.12%-tight stop —
a strong, low-pullback one-way trend (a steady bull melt-up or a gap-driven tape). There, fade targets stop
being tagged (they become timeouts/stops), the +16R winners shrink to −1R stops, and the RR engine — the
*entire* edge — deflates. **2024-Q4 was a bear TREND but a high-oscillation one, so it did NOT test this.**

**Attack 5 verdict: the edge is real but is a REGIME-CONDITIONAL RR harvester whose defining regime (a
low-oscillation trend that defeats the fade target) is UNTESTED in either window.**

---

## ATTACK 6 — survivorship in the 40-stock universe

The 40 names are the alphabetical A–D liquid-F&O block + TITAN/VOLTAS — **not** cherry-picked winners, run
on 2024-Q4 data. Survivorship (names liquid enough to persist to 2026) is **mild** for an intraday,
both-directions R strategy (survivorship bites buy-and-hold, not intraday fades). One second-order effect:
the fade's target mechanism needs **intraday oscillation**, and a liquid universe is *selected for* it — a
gappier/illiquid universe might tag targets less cleanly. Minor relative to Attack 5.

**Attack 6 verdict: minor.**

---

## EDGE-PRESERVATION — which frame-A "ship-now" tunes ENDANGER the +8R (frame B)?

The crux the mandate names: the deep study's tunes were measured in **frame A (symmetric 1:1, win%==signal)**,
never against **frame B's +8R tier**. Frame B's edge lives entirely in stop-distance × target-distance ×
direction — exactly what these tunes move. Ranked by risk to the crown jewel:

| tune (frame-A result) | touches frame-B lever? | edge-risk verdict |
|---|---|---|
| **T3 stop buffer +0.25·ATR** (+10.5pp win A) | **YES — widens R denominator** | **RISKY.** 0.42→0.67 ATR stop = R-multiple ÷1.6; a 16R target → ~10R. The +10.5pp win must overcome a ~38% haircut on *every* winner. Net sign on the tier is **unknown**; `_SYNTHESIS` itself says "re-race on 1m before quoting a net-R." Do NOT ship blind. |
| **mode-switch** (with-trend direction, invert OTE→continuation) | **YES — rewrites direction+location** | **HIGH RISK.** The +8R is *symmetric fade-at-extremes*. Forcing with-trend direction + continuation-location deletes the counter-trend bounce-fades that produced the bear tape's big-R longs. It is a **different strategy**; must be re-derived in frame B before adoption. |
| **T2 re-anchor EXT to live extreme** | **YES — moves the runway target** | **HIGH RISK.** The runway IS the R-multiple. A farther live extreme → bigger R but lower hit-rate; net on the tier is a full re-derive, not a safe infra fix. |
| **b_hit>0 gate / drop b_hit==0** (−0R→+0.19R in A) | maybe (tier is high-b_hit already) | **RISKY-UNKNOWN.** Measured in frame A only. The tier already skews high-b_hit (nest 0.519); few tier trades are b_hit==0, but those that hit far targets add large +R. Sign on the tier unmeasured. |
| **no-blind** (strip strength/width/stacking) | **NO** | **SAFE.** `decision.py` grade never reads strength/width/stacking (it counts bos/sweep/ote/phase/nest/maturity). Stripping them from the *confluence* score cannot touch `decide()`. Lowest-risk ship. |

**Edge-preservation rule: only `no-blind` is safe to ship without a frame-B re-derive. Every other
frame-A tune must be measured against the +8R tier BEFORE adoption — treat as RISKY by default.**

---

## THE SINGLE MOST LIKELY WAY THE EDGE IS FAKE + THE ONE DECISIVE TEST

**Most likely failure:** the +8R is a **RR-asymmetry fade that only pays in oscillating / mean-reverting
tapes**, and both test windows (2024-Q4 bear, 2026 range-down) are exactly that — high-oscillation,
short-tilted. In a **sustained low-pullback trend** (a bull melt-up, or any regime that stops respecting
prior extremes), the nearest-opposite-extreme target stops being tagged, the ~15:1 winners collapse to −1R
stops, and the engine deflates. The "monotone grade ladder" masks this because grade is a **target-distance
proxy**, not a win predictor (corr(strength,win)=−0.005) — so the ladder will look monotone right up until
the tape stops honoring the targets.

**The ONE decisive test:** re-derive the **frozen** config, unchanged, on a **sustained bull / low-
oscillation trending regime** (e.g. an Indian-equity 2023 or 2024-H1 melt-up window) **with two fixes to the
sim: (1) a slippage-through-tight-stop fill (loss allowed past −1R by realistic ticks on a 0.12% stop), and
(2) count `timeout` as a loss, not a drop.** Report the hi-tier net-R and, decisively, the **realized
avg-winner-R** (the RR itself). If net-R and the avg-winner-R hold, the edge is regime-robust and proven.
If the avg-winner-R collapses (targets → timeouts/stops) while win-rate erodes toward the ~13% RR breakeven,
the +8R was a fade-in-an-oscillating-tape artifact. **This isolates the exact mechanism no existing test
touches; every other stress (cost, thin-tier, eod, m5_close) has already been run and the edge survived.**

---

## SCOREBOARD

| attack | result | margin |
|---|---|---|
| 1 contamination/lookahead | edge SURVIVES | causal by construction; 0-leak re-confirmed |
| 2 thin high-grade cells | edge SURVIVES | −0.023R excl g7/g8; rests on g5+g6 (n≈2100) |
| 3 cost realism | edge SURVIVES | ×8 to breakeven; m5_close −5% |
| 4 eod squareoff | edge SURVIVES | net +8.07≈+8.20; zero censoring |
| 5 regime favorability | **edge FRAGILE** | both tapes non-bull/short-tilt; RR engine untested vs low-oscillation trend |
| 6 survivorship | minor | mild; oscillation-selection second-order |

*Written 2026-07-24. Numbers from `tb_2024q4_40.txt`, `decision.py`, `derive_tradebook.py`,
`study40_2026/evidence.parquet` (38,462 decided), `derive_work/*.jsonl` (2024 vs 2026 split).
No pipeline/derive re-run.*
