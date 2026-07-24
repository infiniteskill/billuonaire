# 47-40STOCK — edge by regime: p/d/fade is a CHAMELEON, best in the DOMINANT regime (2026-07-24)

User hypothesis: "for ranging market p/d can be good." Tested the edge (hi>=5 eod, deduped, min-RR>=3)
split by per-stock D1 regime, across all 3 tapes:

| tape (market) | RANGE | UPTREND | DOWNTREND |
|---|---|---|---|
| 2026 (rangey/mixed) | **+9.51R / 75%** | +2.05R / 63% | +6.59R / 60% |
| bull-2023 | +7.03R / 69% | **+9.73R / 71%** | — |
| bear-2024Q4 | +6.62R / 68% | +3.41R / 64% | **+7.37R / 65%** |

CONFIRMED (in context): in a RANGING market (2026), RANGE stocks give the best edge (+9.51R) — the
premium/discount fade is a range construct and pays most where price oscillates. UPTREND is the WORST
cell in the two non-bull tapes (+2.05 / +3.41R).

REFINED (the full picture): NOT "RANGE always best." The edge is strongest in whichever regime MATCHES
the broad market: bull->UPTREND stocks (+9.73), bear->DOWNTREND (+7.37), rangey->RANGE (+9.51). The edge
is a CHAMELEON — range-fade in a range, trend-continuation in a trend (buy-dip in bull / sell-rip in
bear). The grade + far-liquidity target AUTO-ADAPTS to the dominant regime (= the deep-study "mode-switch
is baked in" via the far target auto-sorting with-trend winners from counter-trend knife-catches).

IMPLICATION: a REGIME CLASSIFIER (detect the dominant market regime -> weight/focus aligned stocks) would
CONCENTRATE the edge (e.g., RANGE-only in a rangey market = +9.51R/75%). But the shipped edge already
works across all 3 regimes (all quads +), so this is an optimization, not a fix. The local-window p/d
(coded, unproven) is one path to a range-aware gate; a dominant-market classifier is the fuller version.
