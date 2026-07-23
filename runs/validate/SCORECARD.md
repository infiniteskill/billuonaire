# SCORECARD — per-tool detection accuracy vs solo performance (2026-07-24)

Detection accuracy = hit/(hit+partial+miss) on the 467 registry marks (runs/validate/tools/val_*.jsonl).
Solo = wired standalone edge + fwd12 (runs/validate/taught_refine/summary.csv).

| tool | detect% | hit/part/miss/unchk | wired n | solo edge | fwd12 |
|------|---------|---------------------|---------|-----------|-------|
| premium_discount | 100 | 2/0/0/6 | 1370 | gate | 1.77 |
| breaker | 85.7 | 6/1/0/7 | 689 | +7.2% | -0.18 |
| sweep | 83.3 | 15/2/1/2 | 596 | +10.8% | -0.06 |
| extremes | 58.6 | 17/5/7/39 | levels | — | — |
| fvg | 50 | 9/9/0/17 | 799 | +8.9% | 0.02 |
| structure | 50 | 8/4/4/45 | 0 | — | — |
| order_block | 35.5 | 22/40/0/83 | 689 | +7.2% | -0.18 |
| mitigation | 11.1 | 1/8/0/7 | 689 | +7.2% | -0.18 |
| liquidity | 5.9 | 2/27/5/24 | 554 | pools | 1.68 |
| propulsion | 0 | 0/1/8/6 | 34 | +9.7% | 0.25 |
| compression | 0 | 0/2/0/0 | 124 | +2.5% | 0.29 |
| wyckoff | 0 | 0/1/1/11 | 317 | +7.0% | 0.12 |
| htf_nest | 0 | 0/2/6/1 | 0 | — | — |
| volume_time | 0 | 0/0/2/1 | 0 | — | — |

## WHY they fail solo (4 structural reasons)
1. RECOGNITION != PREDICTION. Every tool has +hit-edge but fwd12 ~= 0 -> the detected object
   (OB/FVG/sweep) is real but ALONE is directionless over the next 12 bars.
2. LOW PRECISION (recall-heavy). Partials >> hits (order_block 22h/40p, liquidity 2h/27p) and
   huge off-mark firing (ob_taught 689 vs ~22 clean marks) -> solo signal drowns in noise.
3. EDGE IS THE CONJUNCTION. The taught setup = sweep AND extreme AND zone AND maturity AND runway
   together; no single detector holds it. Solo = one weak ingredient vs random price. -> measure
   the wired stack's derived tradebook, not solo tools.
4. RR EDGE = THE TINY STOP (fill-through, 31% gap-through), orthogonal to detection accuracy.

## Tool-specific detection faults
liquidity/mitigation: wrong geometry (fractal pools; body-only slivers). order_block: mostly partial
(bodies-only vs outer-wick) + over-fires. propulsion: marks are LINES, detector draws boxes.
htf_nest/wyckoff/compression/volume: starved or firing on wrong instances.
