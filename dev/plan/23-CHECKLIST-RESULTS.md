# CHECKLIST Results — every aspect measured, honest keep/drop (2026-07-17)

The full comprehensive dry-run (CHECKLIST.txt, 5-agent campaign + clean EOD-truncated
re-checks). All on 20 NIFTY stocks × 19 sessions, temporal + cross-sectional holdout.
Hit-edge = session-safe (study.outcome). RR (exp@3R) is EOD-truncated where noted; earlier
RR numbers were inflated (see corrections). Build ONLY the KEEP rows; weight by measured edge.

## KEEP — measured real edge, holdout-stable
| Aspect | hit-edge | RR (exp@3R) | role |
|---|---|---|---|
| **Order Block** (LuxAlgo vol-adj leg-extreme) | +10–14% | positive | primary zone entry |
| **FVG close-beyond** (LuxAlgo dedicated) | +12% (M10) | positive | zone entry |
| **Compression-FADE** | +9% | **+0.26R** (EOD-clean, n=6144) | base signal, tightest SL |
| **Inducement / IDM sniper** (HTF CHoCH + LTF grab) | +14–20% | strong hit (RR TBD) | the sniper |
| **BPR** (opposing-FVG overlap) | +6–9% | **+0.31R** (best of ICT pieces) | zone entry |
| **Wyckoff spring/upthrust** (retuned) | +23/+32% | — (small n) | confluence |
| **Turtle-soup** (range-extreme sweep + reclaim) | +8.6% | ~flat | sweep-reversal variant |
| **Mitigation block** (body-only zone) | +6–9% | +0.10–0.14 | modest zone |
| **H60 direction filter** (agree, ~12× entry TF) | — | **+0.42–0.45R** vs +0.29 | DIRECTION layer |
| **SMT divergence** (stock vs NIFTY) | — | +0.36 vs +0.32 | modest filter |
| **Premium/Discount** | +3.3% | — | weak position filter |
| **Fresh > obvious** (invert level strength) | large (heavy −11.6 vs light +6.5) | — | SL-cluster weighting |

## DROP — measured ≤0 or noise (do NOT build as entries)
| Aspect | result |
|---|---|
| Structure BOS/CHoCH as ENTRY | −18% (4 defs) → **direction-only** |
| Breaker (our current impl) | −8% → replace w/ seek-destroy harvest |
| iFVG (inversion FVG) | negative even standalone → our dead-path was correct |
| Rejection/vacuum block | noise (+1.4/+0.5, huge n) |
| Judas swing (naive) / OR-sweep (naive) | −11 to −12% |
| Gap-fill / gap-trap | no edge |
| Round-number (as directional signal) | no edge (RR was SL-geometry artifact) |
| PO3-distribution (solo) | −15/−27% |
| PO3 + compression (combined) | **no lift** vs alone (user hypothesis not confirmed) |
| PO3 on 1D | weak, mean-reverting, low power |
| Liquidity pool sweep (heavy/high-vol) | inverted (−6 to −12%) |
| Relative strength vs NIFTY | LOWERS fade edge (trend fights reversal) |
| Cleanliness (as predictor) | zero discrimination |
| Weekly/monthly range | flat (underpowered, 19 sessions) |
| Draw-toward-nearest-cluster | rejected (draw-AWAY mildly +, weak) |
| Confluence COUNT (more aspects = better) | **NO** — declines with count; weight by WHICH not how many |
| Option expiry (Thursday) | more chop, HURTS fades → cut size that day |
| VSA booster (except FVG) | degrades |

## Corrections made during the campaign (integrity)
- **HTF direction**: only H60 helps; M30 was a look-ahead LEAK (agree≈oppose clean).
- **RR numbers**: EOD-truncation cut them (compression-fade +0.33→+0.26R@3R); earlier RR
  and kill-zone/H60 numbers still carry a mild late-session bleed until fully re-run clean.
- **Confluence density**: does not lift — the "everything aligns" belief is FALSE as
  stacked-count; it's marginal-edge-weighted (OB adds +, structure/sweep subtract).
- **PO3+compression "too good"**: measured — not confirmed.

## Honest expected performance (EOD-clean, compression-fade base, single signal)
- **Win rate ~30–45%** (target-dependent): 63% @1R, 44% @2R, **31% @3R**, 18% @5R, **7% @10R**.
- **Low-win, high-RR profile** — profitable via RR: +0.26R/trade @3R = +26R per 100 trades.
  ~7/100 run 10R+ (the sniper shots). NOT a high-win-rate system.
- Caveats: one signal, one month, 20 stocks, **before** the full engine (OB+FVG+inducement+
  H60+SMT layered) and **before** final cost check at tiny-SL rupee risk. The economic replay
  of the assembled v2 is the real number.

## What this means for the build
The system is a **weighted-quality decision** (not stacked-count): a few strong grab-signals
(OB, FVG-close-beyond, compression-fade, inducement, BPR) at **fresh** zones, filtered by
**H60 direction** + **SMT** + **premium/discount**, with **structure as direction-only** and
the losers dropped. Weight each by its measured marginal edge. Then the economic replay decides.
