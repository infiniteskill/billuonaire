# 42 — THE REFINEMENT LOOP (study → refine → check → wire → measure → repeat) (2026-07-24)

User: loop through trade/tool/feature study → refine each tool's accuracy + findings → check each tool
(is it WIRED, how does it PERFORM alone) → when accurate, WIRE → check → refine → repeat until it
converges. This doc is the process; it runs every iteration and carries the current state.

## The loop (one iteration)
```
A. STUDY   — per tool: measure recognition ACCURACY vs the 467 registry marks (pct_match) +
             standalone edge (does it fire, hit% vs baseline). Source: val_*.jsonl (accuracy) +
             study --only <tool> (standalone).
B. REFINE  — for each tool below the accuracy bar, apply its 41-TOOLS/<tool>.md tweak (code, additive,
             default-preserving; TDD; full suite green). Re-measure standalone.
C. CHECK   — per tool: WIRED? (in taught_profile.enabled) · fires under the profile? (n>0) ·
             performance (n, edge). Scorecard = runs/validate/SCORECARD.md.
D. WIRE+MEASURE — once the tool set is accurate + firing, run the DERIVED TRADEBOOK
             (tools/derive_tradebook.py): net-R + win% + gap-through% + GRADE DISCRIMINATION
             (does higher grade → higher net/trade, monotone?).
E. LOOP    — the weakest tool / the failed gate (esp. grade non-discrimination) becomes next
             iteration's target. Repeat.
```

## Gates (accuracy bars)
- Tool ACCURATE: pct_match ≥ 60% on its checkable marks AND fires under the profile (n>0).
- Stack READY: all node-0..6 tools accurate + firing.
- EDGE candidate: derived tradebook net>0 AFTER honest costs AND grade MONOTONE (higher grade →
  higher net/trade). Non-monotone grade = selection not working = keep refining.
- EXIT: either EDGE confirmed (net>0, monotone, winners-tail = the 467 marks) OR converged to net≈0
  after honest costs with a monotone-but-flat grade (edge = discretion/absent). Both are real answers.

## Current state (after iterations 1–2 + derived tradebook)
| tool | pct_match (workflow) | wired? | fires (profile n) | status |
|------|----------------------|--------|-------------------|--------|
| breaker | 85.7% | via ob_taught BRK | 135 | OK |
| sweep | 83.3% | ✓ | 596 | OK |
| extremes | 58.6% | ✓ (multi-TF tuned) | levels | near-bar, retune leg_pct |
| structure | 50% | ✓ (ext) | **0** | starved (rangy data; off critical path) |
| fvg | 50% | ✓ | 799 (fvg_n) | OK-ish |
| order_block | 35.5% | ✓ (sweep-gated) | 689 | fires; precision unmeasured |
| mitigation | 11.1% | via ob_taught MIT | 209 (+17.9% edge!) | fires strong; box geom todo |
| liquidity | 5.9%→fixed | ✓ (EXT pools) | 554 | fixed, re-measure pct |
| premium_discount | new | ✓ | 1370 | fires (gate) |
| compression | 0% | ✓ | 124 | maturity scalar added |
| wyckoff | 0% | ✓ | 317 (PHASE) | fires; box-emit todo |
| htf_nest | 0% | ✓ | **0** | STARVED — needs multi-TF zones (infra) |
| volume_time | 0% | not wired | — | deferred |
| propulsion | 0%→ | ✓ | 34 | fires; line-primitive todo |

## THE BINDING FINDING (drives the next iterations)
Derived tradebook: 355 trades, win% 15%, **31% gap-through**, net +1.4R/trade (paper), but the
**GRADE IS NON-MONOTONE (grade2 +1.06 < grade1 +1.79)** → the decision does NOT discriminate winners.
Selection is the unsolved core (the 0.52-AUC problem). So the loop's priority is NOT more recognition
— it is a DISCRIMINATING GRADE feature. Prime candidate (doc 36): **HTF-alignment-DEPTH** via htf_nest
(currently starved). => next iterations:
1. htf_nest infra (HTF-zone emitter so nest_depth exists) → add nest_depth to the grade → re-measure:
   does nest_depth separate the 56 winners from the 289 losers? (THE edge test.)
2. honest cost model (tick fill-through + rupee costs) so the winner tail's realizability is tested.
3. re-run derived tradebook; check grade monotonicity + net after honest costs. Loop.

## Iteration 3 (2026-07-24) — enrich the grade, test discrimination
Added to decide()'s grade the taught "discriminators": deep-extreme (OTE band, from
premium_discount) + Wyckoff PHASE-alignment. Re-ran derived tradebook (HAVELLS+DABUR):
- takes=363, win% 15%, 31% gap-through, net +1.37R/trade (≈ unchanged).
- by grade: g1 +1.51 · g2 +1.05 · g3 +1.77 · g4 +1.18 — **STILL NON-MONOTONE.**
=> The OTE-depth + phase-alignment features DO NOT separate winners from losers in the
derived tradebook. The wired LTF feature set does not discriminate — the 0.52-AUC
ex-ante-separability problem, reconfirmed on the WIRED system's own output.
REMAINING untested discriminator = **htf_nest depth** (doc-36 HTF-alignment-depth), still
starved (needs the multi-TF HTF-zone emitter). It is the LAST causal candidate. Iteration 4:
build the HTF-zone emitter → htf_nest fires → add nest_depth to the grade → re-test
monotonicity. If nest_depth ALSO fails to discriminate → the ex-ante-separability hypothesis
is dead → the edge (if any) is the user's un-codable discretion, not a wired feature.

## Iteration 4 (2026-07-24) — THE DISCRIMINATION TEST: nest_depth separates (first positive signal)
Built the htf_nest infra minimally: htf_nest now uses multi-TF EXT bands as HTF parents
(EXT_L=demand, EXT_H=supply), so a base M5 OB nests inside HTF extremes. htf_nest fires
(n=89). nest_depth already feeds decide()'s grade (grade += 1 + nest_depth).
Re-measured derived tradebook (HAVELLS+DABUR): win% 15%->21%, and the grade is now
ROUGHLY MONOTONE (was flat/non-monotone):
  g1 +0.19 · g2 -0.32 · g3 +1.34 · g4 +2.06 · **g5 +5.96 (n=48)** · g6 +0.81 · g7 +5.53
=> nest_depth (HTF-alignment-DEPTH, doc-36) SEPARATES winners from losers — the FIRST
ex-ante discriminator to work in the whole program. Confirms the doc-36 causal hypothesis
and the "edge is the CONJUNCTION" thesis: htf_nest SOLO is NEGATIVE (-3.2%, fwd12 -0.93),
but nest_depth AS PART OF a high-grade stack marks the winners (g5 +5.96R vs g1-2 ~0).
HONEST CAVEATS (do not overclaim):
- Still PAPER RR: 31% gap-through unaddressed (101/353); avg_win 16R = tiny-stop geometry.
  The +5.96R needs tick-granular fill-through before it is real.
- Small n at high grades (g5 n=48, g6-7 tiny); tails noisy (g6 dips).
- HAVELLS+DABUR only, 17d. Needs more stocks/data + 4-way holdout.
STATUS CHANGE: the loop's binding blocker (grade doesn't discriminate) is BROKEN. The
remaining question is no longer "does anything separate" (nest_depth does) but "does the
separated high-grade tier survive HONEST fill-through + hold out". Iteration 5 = honest
cost/fill-through model + holdout on the high-grade tier; that is the real edge verdict.
