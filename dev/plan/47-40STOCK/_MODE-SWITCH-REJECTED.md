# 47-40STOCK — regime/mode-switch gate REJECTED; the edge is at a ROBUST OPTIMUM (2026-07-24)

Tested the deep-study's central recommendation (the regime "mode-switch": suppress counter-trend,
keep range + with-trend) as a post-hoc direction gate on the graded hi-tier (hi>=5 eod, deduped, min-RR):

| tape | ALL net | counter-trend cells | GATED (range+with-trend) | verdict |
|---|---|---|---|---|
| 2026 (rangey) | +7.34R | +4.53R | +8.74R (n102) | helps |
| bull-2023 | +8.63R | **+9.93R** | +7.51R (n173) | **HURTS** |
| bear-2024 | +6.75R | +5.78R | +7.02R (n355) | ~neutral |

REJECTED: helps 2026 but HURTS bull. In the bull tape "counter-trend" shorts (fading uptrend-stock
spikes) made +9.93R -- the taught FADE catching pullbacks = the method working. Suppressing them removes
good trades. A rule that hurts a regime cannot ship.

## THE META-FINDING (three strikes)
Three deep-study-endorsed "improvements" now tested on the GRADED frame, all REJECTED by the gate:
1. B1 anchor fix (emit_live) -> net-R +6.94->+4.78R, didn't even promote the target 1221. REVERTED.
2. premium_discount warm-up recall -> coverage not edge; loosening risks noise. Not pursued.
3. regime/mode-switch direction gate -> hurts bull. REJECTED (this doc).
Root cause: the deep-study recommendations were derived from the UNGATED SYMMETRIC (coin-flip) frame.
The GRADED + RR-asymmetry edge already encodes regime/direction IMPLICITLY (the far-liquidity target
auto-sorts with-trend winners from counter-trend knife-catches). Bolting on explicit regime/direction
rules DOUBLE-COUNTS and HURTS. The chameleon self-adapts.

## CONCLUSION: STOP TUNING, START VALIDATING
The proven, shipped edge (min-RR>=3 + everything else frozen) is at a ROBUST LOCAL OPTIMUM -- it resists
improvement; every tested addition fails the gate or breaks a regime. The gate harness has done its job:
it protected the edge from three plausible, well-motivated "fixes." Further tuning is contraindicated
(diminishing/negative returns + overfit risk). The remaining work is VALIDATION, not tuning:
- walk-forward (rolling refit vs frozen) -- the rigor finish.
- 12 prior-year marks (2024/25 fetch) -- extend faithfulness.
- tick-granular fills -- replace the 1m gap-aware model.
- a small paper pilot -- the one thing sim cannot answer (live fills).
State: a VALIDATED CANDIDATE, honestly at its ceiling for historical-1m research.
