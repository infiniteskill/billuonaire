# 47-40STOCK — _RETHINK-EDGE-SAFE: the edge-preserving synthesis of the 4 attack agents (2026-07-24)

Rolls up the four edge-preservation attacks — `rethink_reconcile_frames` (frame reconciliation),
`rethink_red_team_edge` (adversarial break attempt), `rethink_regime_and_instrument` (regime + the
instrument enabler), `rethink_tune_risk_audit` (per-tune frame-B risk) — against `_SYNTHESIS.md`
(the deep study), `_NEXT-ACTIONS.md`, and the crown jewel itself, `runs/validate/tb_2024q4_40.txt`.

**Mandate above all else: PROTECT the crown jewel.** Frozen `runs/validate/taught_profile/config.json`,
unseen 2024-Q4 BEAR tape (31/41 down): hi-tier (grade≥4) **intrabar +8.200R/win62% · m5_close +8.352R/65 ·
eod +8.068R/72**, grade ladder **monotone g1→g7** (g1 −1.51 · g3 +0.25 · g5 +8.34 · g6 +9.54), **all 4
holdout quadrants + under every stop mode**; also **+6.13R** on mixed-2026. This is the object every action
is measured against. When in doubt: **do not touch it.**

---

## 1. THE ONE-PARAGRAPH RESOLUTION — are the two studies contradictory?

**No. They measure different quantities, and all four agents converge on it.** FRAME A (the deep study) is
the **symmetric 1·ATR : 1·ATR first-touch** parquet — 38,462 decided firings, one 17-day tape, where payoff
is 1:1 so **win% *is* the signal** and the metric is `win − b_hit`; every detector is a **0.49–0.52 AUC
coin-flip** with mirror MFE/MAE. FRAME B (the crown jewel) is a **graded, RR-asymmetric net-R product**: a
tight ~0.42-ATR taught wick stop against a far EXT runway target (**≈15:1**), graded by the `decide()`
AND-conjunction (**bos + sweep + ote + phase + htf_nest→grade+=1+nest_depth + maturity**, `min_grade=4`).
**Frame A caps every outcome at ±1 ATR — it is blind by construction to the >1-ATR right tail where Frame
B's entire +8R lives.** So **the edge is the grade-conjunction × the RR-asymmetry**, working together two
ways: (i) the conjunction is *intrinsically a confirmed-continuation filter* (BOS = momentum break, sweep =
liquidity grab, phase = Wyckoff alignment), and (ii) the far target *auto-sorts* regime for free — a
counter-trend knife-catch has a ~0.64-ATR excursion, never reaches the target, stops at −1R, and **lands in
g1–g2 (negative)**, while a with-trend continuation rides 3+ ATR into g5–g7. That is exactly *why* the frozen
config held **+8.20R monotone on an unseen bear tape with no regime term** — the mode-switch is **implicitly
baked into the conjunction + RR-asymmetry.** **Therefore the deep study is a DIAGNOSTIC of the mechanism (why
the edge is regime-robust), NOT a MANDATE to rewire the frozen config.** Its central trap: it was *entirely
measured in Frame A*, and **a Frame-A win can be a Frame-B loss** — most sharply, "alpha lives in the LOW
b_hit tail" is a symmetric-frame artifact that **INVERTS in Frame B**, where realized large-R is monotone in
**HIGH** b_hit (MFE 1.27→3.55, MAE 3.33→1.33 across the b_hit range; b≥.5 nests reach ≥3ATR **45.3% vs 2.8%**).

---

## 2. THREE BUCKETS — every action sorted

### BUCKET A — ZERO-REGRET (read-only / additive-only; cannot touch the edge). **DO THESE NOW, in this order.**

These add *information* or an *offline A/B surface*; none alters `decide()` or the sim, so none can move the
+8R. This is the whole of what is genuinely safe today.

| order | action | why it is zero-regret | output |
|---|---|---|---|
| **Z1** | **Instrument `derive_tradebook.py` to persist the per-trade tradebook** — additive logging in `report(mode)`: one parquet per stop-mode (`tradebook_intrabar/m5_close/eod.parquet`) with `sym, ts, reg`(regime tag), `dir, grade, entry, sl, target, outcome, R, netR, reasons`(the bos/sweep/ote/phase/nest:N/maturity decomposition). ~15-line additive diff (spec in `rethink_regime_and_instrument §c`). | writes a file at the END of a run we already do; cannot perturb path/logic/decide()/sim | 3 parquet frames = the A/B harness |
| **Z2** | **Sustained-BULL adversarial test** — frozen config UNCHANGED on an unseen **low-volatility GRINDING melt-up** tape (2023-Q4 / 2024-Q1 large-caps; `drift>+3 & close_pos>65` **AND** a grind gate `down_day_frac<0.40 & median(mfe/atr)<1.0`). Harden the sim two ways: **(1) slippage THROUGH the 0.12% tight stop** (loss allowed past −1R on realistic ticks), **(2) count `timeout` as a LOSS, not a drop.** Report hi-tier **net-R + ladder + per-direction net-R + the excursion distribution (median/mean mfe·atr)**. | read-only re: config; a FAIL is information, not damage; this is the ONE untested regime | binary make-or-break |
| **Z3** | **Faithfulness co-location** — are the hi-grade winners the user's **467 hand-marks**? | information only; changes narrative/trust, not config | PASS = "+8R IS the taught method" |
| **Z4** | **Walk-forward** — rolling refit vs the frozen config (current holdout is frozen-config, not walk-forward). | information only; guards researcher degrees-of-freedom | overfit guard |

**Sequence: Z1 first (it is the enabler for every gated change), then Z2 (the make-or-break), Z3+Z4 in
parallel.** Ship nothing to config until Z1 exists and Z2 has reported.

### BUCKET B — GATED-CHANGE (touches config → **MUST A/B on the derive frame**).

**Universal ship gate (identical for every item, on the DERIVE frame, never Frame A):** re-derive (or, for
pure filters, run the offline A/B over the Z1 frame); **ship ONLY IF** hi-tier (grade≥5) **NET-R ≥ frozen
+8.20R intrabar / +8.07R eod** AND **all 4 holdout quadrants ≥ current** AND **grade ladder stays monotone
g1→g7**. Measure **NET-R, never symmetric win%.** **Else REJECT.** Ordered lowest-regret / highest-value first:

| order | change | frame-B verdict (agents) | its specific pass/fail gate |
|---|---|---|---|
| **G1** | **no-blind** — strip `strength`/zone-width/stacking from the grade | **EDGE-SAFE NO-OP** — `decide()` never reads them; they live only in the production `ConfluenceEngine` that never produced +8R | trivially passes; verify grade decomposition unchanged. Lowest regret; do first |
| **G2** | **`b_hit>0` gate** — drop the b_hit==0 firehose | **EDGE-SAFE → POSITIVE** — culls the worst-geometry cell (win 29.6%, MFE 0.98, MAE **4.24**); **keeps 91.9% of ≥3ATR & ≥5ATR reachers, 98.6% of nest far-target reach**; hi-grade moments carry LOWER b0-share (17.5%) | re-derive gating **zone AND/OR nest** (test both — which firing gates is unspecified); PASS on the universal bar; expect per-trade net-R ↑, total-R ↓ slightly. REJECT if hi-tier < +8.20R |
| **G3** | **T2 — ADDITIVE `EXT_LIVE_H/L`** (emit the live unmitigated extreme in **parallel**, `_runway`/`htf_nest` CONSULT it; **NEVER delete the confirmed-pivot EXT**) | **EDGE-RISKY unless additive** — re-anchoring regenerates the runway target + p/d permit + nest parents = the exact inputs that GENERATE +8R | full re-derive; **co-locate existing hi-tier trades by ts → require their net-R UNCHANGED**; new now-emittable trades ≥ +8R; quadrants hold. REJECT if any existing hi-tier net-R moves down |
| **G4** | **b_hit recalibration as a monotone FLOOR only** (isotonic/Platt to set a floor) | **NEUTRAL** as a floor (monotone, preserves G2). The **SELECT-low-b_hit half is DO-NOT-TOUCH** (bucket C) | re-derive; hi-tier ≥ frozen. Ship the floor; NEVER ship the selection rule |
| **G5** | **Regime classifier as a PARALLEL TAG** (not a hard gate) | **EDGE-RISKY as a hard gate** — +8R already holds regime-BLIND on bear+mixed; classifier is a 16-bar D1 label where **ADX cannot seat** → hard-gating ADDS a misclassification failure mode | split the Z1 tb by classified regime; PASS = hi-tier ≥ +6R in all 3 classified regimes. **Only wire suppression if a hi-tier regime cell is actually negative (none is today)** |
| **G6** | **Extreme + sweep + BOS required gate (B8)** | **EDGE-RISKY-UNKNOWN** — `decide()` already AWARDS sweep+bos; REQUIRING them at the extreme drops grade-4 trades that reached 4 via **nest+phase (no sweep/bos)** — may cull real nest winners while it targets held-extreme knife-catches | re-derive with sweep+BOS required in node 0/1; report hi-tier net-R, 4 quadrants, **AND the count of nest+phase-only grade-4 winners lost.** REJECT if it culls real nest winners / hi-tier drops |

### BUCKET C — DO-NOT-TOUCH (freeze until proven on the graded frame). These are the ways we *actively delete the edge.*

- **The frozen config `runs/validate/taught_profile/config.json`** — the `decide()` AND-chain, `min_grade=4`,
  `leg_pct=2.0`, `atr_buffer=0.25`, the large-R EXT runway target, the tight nest/zone CE stop. **This IS the
  +8R generator.** No line changes except through Bucket B's gate.
- **SELECT-LOW-b_hit alpha (#7 select half) — THE CROWN-JEWEL KILLER.** Frame-A "alpha in the low b_hit tail"
  **INVERTS in Frame B**: realized large-R is monotone in **HIGH** b_hit (the b≥.5 nests are the ≥3ATR
  far-target reachers, 45.3% vs 2.8%; `htf_nest` is the highest-b_hit detector at 0.519 and carries the +3
  grade that builds the g5–g7 tail). Selecting for low b_hit **deselects the exact engine of the edge.** Never.
- **T3 stop-WIDEN — do NOT re-apply / widen the tight wick stop.** `atr_buffer=0.25` is **already in the
  frozen config** (it produced the +8R). Re-applying/widening **widens the stop → shrinks the R-multiple
  denominator → directly attacks +8R** (Frame-A ΔExpR is already **−0.03R**; a 0.42→0.67-ATR stop is a ~38%
  haircut on every winner). The wick-noise mechanism T3 diagnosed is **real but already neutralized at zero R
  cost by the `m5_close` production rule** (+8.35R ≈ intrabar +8.20R). Fix wick-noise with the M5-close stop,
  **not** a wider stop.
- **"Strip detectors because they are 0.49 AUC."** 0.49 AUC is a **Frame-A geometry** fact; the +8R rests on
  the **conjunction + RR-asymmetry**, not any detector's directional AUC. Stripping the 0.49-AUC detectors
  **deletes the conjunction's inputs.** Do not.
- **T2 REPLACE-anchor** — never *replace* the confirmed-pivot EXT (that regenerates the whole grade + R
  distribution). Only the **additive** `EXT_LIVE` variant (G3) is allowed, gated.
- **Do not "fix" `htf_nest` blind.** The −4.7pp is a Frame-A marginal on 3% of firings, near-constant depth-2,
  **already priced into the +8R**; and the "median 4.87-ATR invisible-extreme cap / 92%-never-re-anchor"
  severity was **measured at `leg_pct=6.0`, not the frozen `leg_pct=2.0`** — a different parameterization than
  the crown jewel. Not a mandate.

---

## 3. THE SAFE MECHANISM — instrument → A/B harness → the one gate on ALL future change

This is the machinery that lets us touch anything without risking the crown jewel. Three steps:

1. **INSTRUMENT (Z1, additive-only).** In `tools/derive_tradebook.py` `report(mode)`, after the existing
   `rows` loop, dump one parquet per stop-mode with each take's `sym, ts, reg`(regime tag from `_REGIME.md`),
   `dir, grade, entry, sl, target, outcome, R, netR, reasons`(the grade decomposition
   bos/sweep/ote/phase/nest:N/maturity — add `reasons` to the `Decision` dataclass + `_tap`'s
   `trades.append`, 1 line each). It writes a file at the end of a run we already do — **it cannot alter
   `decide()`/`_sim`, so it cannot move the +8R.** ~15-line diff (spec: `rethink_regime_and_instrument §c`).

2. **A/B HARNESS.** With the tradebook persisted, every **pure-filter** tune (G1 no-blind, G2 b_hit>0, G4
   b_hit-floor, G5 regime-split) becomes an **offline pandas query over the saved frame** — e.g.
   `df[~df.reasons.str.contains('nest:0')]` or `df.groupby(['reg','grade']).netR.mean()` — read in **seconds**
   instead of a ~3hr re-derive. Tunes that change **what is emittable** (G3 T2-additive, G6 sweep+BOS-required)
   still need a full re-derive, but the saved tradebook is what you co-locate against (ts-match existing
   hi-tier trades, require net-R unchanged).

3. **THE GATE — the rule on EVERY future config change.** *No config change ships unless a graded re-derive
   (or offline A/B for pure filters) shows hi-tier (grade≥5) **NET-R ≥ frozen +8.20R intrabar / +8.07R eod**,
   **all 4 holdout quadrants ≥ current**, and the **grade ladder stays monotone g1→g7**. Measure NET-R, never
   symmetric win%. Else REJECT.* This single gate governs every SHIP/FIX/BUILD item, forever. Ship-into-config-
   blind = crown-jewel risk.

---

## 4. THE DECISIVE RISK + THE SINGLE SAFEST, HIGHEST-VALUE FIRST MOVE

**The decisive risk (most likely way we LOSE the edge by ACTING):** shipping a Frame-A tune blind into the
frozen config. The sharpest instance — near-certain harm — is applying **"select LOW-b_hit alpha"**: it reads
as the deep study's headline prescription, but realized large-R is monotone in **HIGH** b_hit, so it
**deselects the high-b_hit nest engine (b≥.5 nests = the ≥3ATR far-target reachers) that literally builds the
g5–g7 tail.** The runner-up is **re-applying/widening the T3 tight stop**, which cuts the R-multiple
denominator that *is* the edge. Both were measured in the wrong frame; both feel like "obvious fixes"; both
delete the crown jewel. *(Separately, the biggest way we could DISCOVER the edge was never robust — not lose
it by acting — is the untested **low-oscillation bull melt-up**, where the far target stops being tagged and
the ~15:1 RR harvester deflates. That is what Z2 exists to find out.)*

**The single safest, highest-value first move: Z1 — instrument `derive_tradebook.py` to persist the per-trade
tradebook (additive, zero risk to the frozen config), THEN run Z2 (frozen config on a low-vol grinding bull
tape, with slippage-through-stop + timeout=loss).** Z1 first, because it converts every future tune from a
3hr edge-gamble into a seconds-long offline A/B — it is the enabler that makes the gate cheap and makes every
Bucket-B change *possible to test safely*. Z2 second, because it is the one make-or-break piece of
information — does the edge survive the one regime that could kill it — and it changes only our **trust**, not
one config line.

---

## 12-LINE VERDICT

1. **NOT contradictory** — the two studies measure different quantities: Frame A = symmetric ±1-ATR
   first-touch (win%=signal, 0.49-AUC coin-flip); Frame B = graded RR-asymmetric net-R (the +8R). Frame A is
   blind by construction to the >1-ATR tail where the whole edge lives.
2. **The edge = the grade-CONJUNCTION × the RR-ASYMMETRY** — the conjunction (bos+sweep+ote+phase+nest+maturity)
   is an implicit continuation filter, and the far target auto-sorts with-trend from counter-trend (knife-catches
   stop at −1R → g1–g2). The mode-switch is already baked in; that is *why* it held +8.20R monotone on unseen bear.
3. **The deep study is a DIAGNOSTIC of the mechanism, NOT a MANDATE** to change the frozen config; every one of
   its tunes was measured in Frame A, and a Frame-A win can be a Frame-B loss.
4. **ZERO-REGRET, do NOW in order: Z1** instrument+persist tradebook (additive) → **Z2** bull grind-melt-up
   test on frozen config (slippage-through-stop + timeout=loss) → **Z3** faithfulness → **Z4** walk-forward.
5. **GATED-CHANGE, ordered lowest-regret first: G1** no-blind (no-op) → **G2** b_hit>0 gate (safe→positive) →
   **G3** T2 additive EXT_LIVE only → **G4** b_hit floor-recalibration only → **G5** regime as a parallel TAG →
   **G6** sweep+BOS-required. Each ships ONLY if hi-tier net-R holds/improves AND all 4 quadrants stay +, else REJECT.
6. **DO-NOT-TOUCH: the frozen config; SELECT-low-b_hit (the killer — large-R is monotone in HIGH b_hit);
   T3 stop-widen (already in config, use m5_close for wick-noise); "strip 0.49-AUC detectors"; T2 REPLACE-anchor;
   blind htf_nest "fixes" (measured at leg_pct=6 ≠ frozen leg_pct=2).**
7. **THE GATE on ALL future change:** no config line ships unless a graded re-derive/offline A/B shows hi-tier
   grade≥5 **NET-R ≥ +8.20R intrabar / +8.07R eod**, all 4 quadrants ≥ current, ladder monotone g1→g7 — NET-R,
   never win%. Else REJECT.
8. **THE SAFE MECHANISM = Z1 → A/B harness → the gate:** persist the tradebook once (additive), then every pure
   filter is a seconds-long `df.query`; emittability changes (T2/sweep+BOS) still need a full re-derive co-located
   against the saved hi-tier.
9. **The decisive risk = shipping a Frame-A tune blind;** the near-certain-harm instance is "select LOW-b_hit
   alpha," which deselects the high-b_hit nest engine that builds the g5–g7 tail; runner-up is widening the T3 stop.
10. **The one real external fragility = a low-oscillation bull melt-up** (the ~15:1 RR harvester deflates when the
    far target stops being tagged); both winning tapes are non-bull; Z2 is the one experiment that resolves it.
11. **The safest highest-value first move = Z1 then Z2:** instrument (zero config risk) → prove on the untested
    bull regime (frozen config). Instrument first because it makes every later change cheap and safe to A/B.
12. **Bottom line: PROTECT the +8R. Instrument, then bull-test — before changing a single config line.**
