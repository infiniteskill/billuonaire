# 43-PRECISION — SYSTEM-ACCURACY SYNTHESIS (2026-07-24)

Rolls up the 12 per-tool precision audits (`43-PRECISION/*.md`) against the derived-tradebook
edge (`42-REFINE-LOOP.md`: high-grade tier **+4.57R**, ungated **−1.29R**, at 40-stock/7392-trade
scale) and the detection scorecard (`runs/validate/SCORECARD.md`). Scope is **RECOGNITION /
PRECISION only** — no new edge claim. Every audit agrees recall is already ~100%; the lever is
*over-fire* — of all firings, what fraction is the REAL taught object.

---

## (a) Overall detection-precision picture

**The suite emits ~18,400 firings over 8 stocks × 17 sessions (~136 stock-sessions) — and by
every audit's density proxy the real-taught-object fraction is single-digit to low-double-digit
percent.** The in-window checkable marks are catastrophically thin for *every* tool (0–4 distinct
objects each — the registry marks are mostly out-of-window / foreign / wrong-price-era), so
**DENSITY (fires/stock/session vs the ~1–3 taught objects a real chart carries) is the honest
precision proxy everywhere**, corroborated by tool-specific tells (box-size, strength-mode,
nest-depth, kind-mix).

| tool / event | fires | density /stk/sess | est. real-object frac | root fault | tune → target fires |
|---|---:|---:|---|---|---:|
| premium_discount | **4634** | 34.1 (~100% of bars) | ~3.4% unique | per-bar re-stamp of a static NEUTRAL zone; whole-half birth | edge-trig OTE → **~158** (−96.6%) |
| fvg_n (FVG+iFVG) | **3376** | 24.8 | ~4% | no min-gap birth gate (q=0); kill→iFVG twin doubles pop | min_gap_atr 0.7 → **~708** (−79%) |
| ob_taught OB_RETEST | 1505 | 11.07 | ~10% | displacement gate absent; sweep+BOS gate OFF | min_disp_atr 1.0 → **~575** (−60%) |
| sweep | **2613** | 19.2 | ~1-in-8 | touches≥3 is a soft nudge not a gate; raw SWINGs sweepable | min_touches 3 → **~1000** (−58%) |
| liquidity POOL_NEAR | 2404 | 17.7 | ~39% (EQ share) | no kind gate — 11 pool families emit; catalog never expires | EMIT={EQ,EXT}+prox0.35 → **~420** (−83%) |
| wyckoff PHASE | 1430 | 10.7 (both-way 46%) | ~0% | emits out-of-range trend branch; bare 5m-trend gate, no event anchor | spring/upthrust-anchor → **~30** (−98%) |
| ob_taught MIT_RETEST | 942 | 6.6 | floor | MIT = fallback bin for every pex-unknown OB death | pex-known No-Break → **~435** (−54%) |
| ob_taught BRK_RETEST | 502 | 3.69 | ~2–11% | zero-margin swept gate; pex = newest wiggle | swept≥0.5·ATR, EXT-pex → **~200** (−60%) |
| compression BOX_ON_LEVEL | 460 | 3.38 | ~1.5% (right scale) | ×1.93 level fan-out + per-candle re-fire; any-overlap | 1-per-box+containment → **~160** (−65%) |
| htf_nest NEST | 382 | 2.81 | ~39.5% (depth≥2) | min_depth=1 admits single-HTF graze (60.5% depth-1) | min_depth 2 → **151** (−60.5%) |
| propulsion2 | 131 | 0.96 | ~5% ceiling | no parent-quality gate — child off *any* live micro-OB | swept-EXT parent ≥0.5·ATR → **~20** (−85%) |
| structure BOS/CHoCH | **0** | 0.00 | undefined | `trend_swings=2` makes `_trend` math-incapable of firing | HH+HL rewrite → **~30–80** (UNDER-fire) |

**Worst over-firers (raw + as a fraction of the conjunction it feeds):**
1. **premium_discount** — largest emitter and the *purest* dilution: a static NEUTRAL stamp on
   ~100% of bars means every grade-stack gets the deep-extreme vote for free (zero discrimination).
2. **fvg_n** — 25:1 over-fire, half the fires sub-0.31·ATR micro-gaps; 48% are iFVG twins with
   **zero** in-window ground-truth object.
3. **sweep + liquidity** — the two leg-0 members of the taught chain, ~17–19/session of which
   ~61–77% is tick-thin fractal/round/prior-day furniture (sweep leg only ~1-in-8 real).
4. **ob_taught family (2949 across OB/MIT/BRK)** — the root entry object; ~90% over-fire, 32% of
   OB boxes are sub-0.3·ATR micro-boxes; MIT is a fallback bin (MIT:BRK 1.88, backwards).
5. **wyckoff** — 1430 votes, 99.6% the wrong (out-of-range trend) object, both directions in 46%
   of stock-sessions — near-pure background noise in the stack.

**Per-stock variance:** the over-fire concentrates in the **heavy-tape liquid names** and the cut
"lands where it is worst." TITAN tops liquidity (24.3), OB_RETEST (14.3), MIT (8.9); HDFCBANK tops
fvg (26.5), sweep (21.9), wyckoff (12.6); HEROMOTOCO tops htf_nest (6.38) and sweep (22.5);
premium_discount peaks HEROMOTOCO 888 / TITAN 864. Low-density names (SBILIFE, DLF, DABUR, VOLTAS)
sit 30–60% below. htf_nest is the sharpest split — HEROMOTOCO 6.38 vs HDFCBANK/SBILIFE ~1.0 — so
the depth gate barely touches the already-clean names. **Read: furniture density scales with tape
liquidity/level-count, not with taught-setup rate, which is why density (not marks) is the proxy
and why the same absolute gate helps the heavy names most.**

---

## (b) RANK — precision tunes by expected impact on the HIGH-GRADE tier / net-R

Ranking criterion = *how much does removing this tool's over-fire sharpen the discriminating
high-grade CONJUNCTION* (not solo edge — every tool's solo fwd12 ≈ 0). Weighted by: (i) load-
bearing-ness to the proven discriminator `nest_depth`, (ii) cascade breadth (does it clean objects
other detectors build on), (iii) contamination mode (always-on background votes dilute most),
(iv) over-fire magnitude, (v) apply-risk (additive, recall-safe, testable).

| # | tune | why it moves the high-grade tier | fires→ | risk |
|---|---|---|---|---|
| **1** | **ob_taught OB `min_disp_atr=1.0`** | **Root object of the whole family — widest cascade.** Cleans the ENTRY leg (the tiny-stop RR sits on it) AND, for free, the MIT/BRK flip children, propulsion parents, and htf_nest *children* (5m OBs that nest into HTF). One local-geometry gate lifts real-object density ~10%→~25–30% across 4 downstream events. | 1505→~575 | low; pure local geom, no cross-detector dep, `disp≥1·ATR` keeps all validated hits |
| **2** | **htf_nest `min_depth 1→2`** | **Directly sharpens `nest_depth` — the ONLY discriminator that survived honest costs + holdout** (g1 −7R → g7 +8.82R). 60.5% depth-1 grazes currently let a single-HTF overlap earn the nest bonus; ≥2 makes every nest-vote genuine multi-TF confluence. | 382→151 | very low; one-line, recall-safe by construction (true nest is depth≥2) |
| **3** | **premium_discount edge-trigger OTE** | **Biggest dilution removal.** A static NEUTRAL on ~100% of bars adds the deep-extreme term to *every* stack → contributes zero discrimination. Edge-trigger converts a constant background into a rare side-permission that fires only when an entry detector coincides with a real deep extreme. | 4634→~158 | low; `ote` already in meta; keep permits on ctx tick-meta so downstream unaffected |
| 4 | sweep `min_touches=3` (exempt PDH/PWH) | leg-0 of the chain; removes the 63% touches<3 fractal grazes → sweep leg ~1-in-8 → ~1-in-3 real | 2613→~1000 | low; daily/weekly exemption + EQ construction preserve recall |
| 5 | fvg_n `min_gap_atr=0.7` | entry pocket; kills sub-0.31·ATR half AND cascades to iFVG twin at source; precision ~4%→15–20% | 3376→~708 | low; marked hits 1.4–3.7·ATR, far above floor |
| 6 | liquidity kind-gate {EQ,EXT} + `prox 1.0→0.35` | leg-0 pool; taught fraction 39%→90%+; density→~1–3 real pools/sess | 2404→~420 | low; catalog stays on ctx.levels so sweep still reads SWEPT |
| 7 | wyckoff spring/upthrust event-anchor | removes ~1400 both-way 0.5-strength background votes → wyckoff vote means a real swept leg | 1430→~30 | med; unmeasurable in-window recall (n=0 marks) |
| 8 | ob_taught BRK swept `≥0.5·ATR` + EXT-only pex | cleans the breaker member of the stack; **partly rides on #1** (BRK is an OB flip child) | 502→~200 | low; self-contained, HAVELLS 1.07·ATR object survives |
| 9 | ob_taught MIT pex-known No-Break | MIT:BRK 1.88→≤1.0; every MIT references a real prior extreme; **rides on #1** | 942→~435 | low; faithful to c31, no structure-detector dep |
| 10 | compression 1-per-box + containment floor | de-dups ×1.93 fan-out + per-candle re-fire; contained coil-on-zone | 460→~160 | low but it de-dups > filters; keep low grade-weight |
| 11 | propulsion2 swept-EXT parent ≥0.5·ATR | high fidelity gain but tiny volume (0.96/sess); real-object frac ~5%→30–40% | 131→~20 | low; needs ctx.levels EXT wired into its private ObZones |
| 12 | structure `_trend` HH+HL rewrite | **UNDER-fire (0)** — supplies a *missing* clean EXT-BOS context member; keep confluence-weight 2 (solo edge negative) | 0→~30–80 | med; a rewrite, not a param; guard as low-weight context only |

**Sequencing note:** apply **#1 before #8/#9/#11** — BRK, MIT and propulsion are all children of
ob_taught OB parents, so the displacement gate improves their precision for free and shrinks the
marginal work of their own tunes. **#2 depends on clean children** (which #1 supplies), so #1→#2
is the natural order. #3 is independent and can land in parallel.

---

## (c) The system-accuracy hypothesis

**Tighter per-tool precision does BOTH — but asymmetrically, and it does NOT create the edge.**

The high-grade tier already works (+4.57R, monotone g1 −7 → g7 +8.82, all 4 holdout quadrants
positive) *despite* the over-fire, and its edge is driven by ONE causal feature — `nest_depth`
(HTF-alignment-depth), the sole discriminator that survived honest 1m fill-through + rupee costs.
So precision tunes cannot manufacture the discriminator; the grade already isolates the winners.

What the over-fire actually does to the tier is **dilute the conjunction**: the grade is a stack of
confluence votes, and the always-on furniture (premium_discount on ~100% of bars, wyckoff both-way,
sweep/liquidity/fvg/ob furniture at 11–34/session) contributes near-constant votes that (a) wash
out — a term that is always on adds no discrimination — and (b) inflate mediocre setups *into*
grade≥4 as false-positives. Cleaning each member therefore **raises the high-grade tier's PURITY**
(the fraction of grade≥4 stacks that are the real taught conjunction) and should nudge win% and
net-R/trade **up** by removing furniture-inflated false-positives — while **shrinking the tier's n**
(fewer candidates reach grade≥4). The DOMINANT measurable effect, though, is a **large volume cut
(~70–85% of the ~18,400 firings)** concentrated on the low/ungated tiers, shrinking the −1.29R
loss mass rather than multiplying the +4.57R.

**Falsifiable prediction, to test on the derived tradebook after each additive tune:** the grade
stays monotone at reduced volume, the high-tier (≥4) net-R **holds or rises** and its win% rises,
while total takes and the low-tier loss both fall. **EDGE-POSITIVE** if high-tier net-R holds/rises
and monotonicity survives; **NULL-leaning** if high-tier net-R falls or its n collapses below
significance (a sign a tune stripped a genuine confluence member, not furniture). Faithfulness gate:
confirm the surviving high-grade winners co-locate with the user's hand-marks (limited by the 17d
window). Net: precision is a **purity + volume** intervention that makes the *existing* edge cleaner
and cheaper to trade — not a new-edge intervention.

---

## (d) Top 3 tunes to APPLY next (code-level, additive, testable)

All three are additive, default-preserving (behind a new default that reproduces current behaviour
if unset), self-contained (no cross-detector dependency), and testable on the derived tradebook
(grade monotonicity + high-tier net-R/win%/n) with TDD + full-suite-green per the loop's B step.

### 1. ob_taught — birth-time DISPLACEMENT gate (`min_disp_atr=1.0`)
`app/trader/detectors/ob_taught.py`. Add `min_disp_atr` to `_DEFAULTS` (default preserves behaviour
only if set to 0). In `_cluster` (the continuation-break branch, ~L98–107), after computing `d`,
gate the Zone birth on displacement magnitude:
```python
disp = (c - bhi) if d == 1 else (blo - c)
if self.tape.atr and disp < Decimal(str(self.params["min_disp_atr"])) * self.tape.atr:
    self._run = []          # sub-displacement break — reset, mint nothing
    return None
```
Encodes the OB's defining property (origin of a ≥1·ATR displacement leg). Cascade: cleans OB entry
+ MIT/BRK flips + propulsion parents + htf_nest children. Target 1505→~575 OB_RETEST (−60%),
density 11.1→~4.0. Recall cost ≈ 0 (all validated hits sit before real displacement legs).

### 2. htf_nest — raise birth gate `min_depth 1 → 2`
`app/trader/detectors/htf_nest.py` L31: `_DEFAULTS["min_depth"]: 1 → 2`. The gate at L73–74
(`len(tiers) < int(min_depth): continue`) already enforces it — one constant. Keeps only births
where ≥2 distinct higher TFs contain the child = genuine multi-TF confluence, directly sharpening
the `nest_depth` discriminator that drives the high-grade tier. Target 382→151 (−60.5%), density
2.81→1.11; drops the 231 depth-1 grazes, keeps every depth≥2. Recall unaffected (true nest is
depth≥2 by construction). Second-order (defer): tighten `_overlaps` to a containment/edge-tol test.

### 3. premium_discount — edge-triggered OTE-band entry
`app/trader/detectors/premium_discount.py` `detect()` (L66–73). Replace the per-bar
`Evidence(NEUTRAL, ttl_candles=1)` with: (a) **birth gate** = emit only when `meta['ote']` is True
(the band is already computed at L: `0.21<=pos<=0.38 or 0.62<=pos<=0.79`); (b) **edge-trigger** =
emit ONE Evidence on the bar `pos` first *enters* the OTE band (state 0→1 per stock-session),
suppress while it dwells, re-arm on exit — track prior-bar in-band state on the detector. Keep the
side-permission always available to downstream by writing `range_pos`/`side`/`permits` to ctx
tick-meta (the spec's context gate), not as a per-bar Evidence. Target 4634→~158 (−96.6%), density
34→~1.7; the deep-extreme member becomes discriminating instead of a free background vote.

**Apply order:** #1 → #2 (│#3 parallel). After each: re-run `tools/derive_tradebook.py`, check
grade monotonicity + high-tier (≥4) net-R/win%/n vs the iter-6 baseline (+4.57R, n=2704). Keep the
change only if the high tier holds/rises at lower volume; revert if its n collapses or net-R falls.
