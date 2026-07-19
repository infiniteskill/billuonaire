# LIQ — taught-spec LIQUIDITY tools (lessons 5, 15, 16): build + behavioral test

Question: do the user-taught liquidity organs — pools beyond zigzag extremes, sweep→reversal,
void corridors, PO3 accumulation→manipulation — behave as taught, against path-clean matched
nulls? Detection-behavior study, no economics (per standing honesty note).

## Data & method

- `runs/artifacts-data/l4_h1.parquet`: 138 NSE stocks × H1, 2023-08-04 → 2026-07-17 (2.94y,
  ~5052 bars/sym). Splice guard: symbols segmented at >20% close→open jumps, segments <300 bars
  dropped (same 6 affected symbols as H1GRID).
- Anchors: `dev/research/ext_zigzag.py` zigzag reused verbatim (one empty-slice guard patched at
  import), K=6×ATR with the lesson-1 percent floor — threshold = max(6×ATR14, 4.7%×price).
  Confirmed pivots only; pools activate at the pivot's CONFIRM bar (causal).
- **POOLS v2 (lesson 5)**: band just beyond each extreme, width 0.25×ATR(pivot). Fatness =
  EQH/EQL cluster (prior same-side pivots within 0.25×ATR) + held-touch episodes (debounced
  approaches within 0.25×ATR that did not penetrate). Life ends at first penetration:
  close back inside → SWEEP (tagged, feeds breaker family), close beyond → BREAK.
- **VOIDS (lesson 16)**: maximal same-direction-candle runs, travel ≥2×ATR, body-path efficiency
  ≥0.6 (or single marubozu, body ≥0.7×range). Zone = open(start)→close(end); far edge = origin;
  3-candle FVGs counted inside. Lone FVGs = plain 3-candle gaps outside any void run.
- **PO3 coils (lesson 15)**: 14-bar range ≤2.6×ATR (≈p5-10 of range/ATR, measured), debounced
  onsets; frozen edges; first wick beyond an edge = the break; outcome race (12 bars): close back
  inside = REVERSAL (manipulation signature) vs close ≥1×ATR beyond edge = CONTINUATION.
- **Nulls (H1GRID method lesson respected — no month-matched trap)**: every real event gets 5
  time-local (±70..250 bar) matched random events on the same symbol/segment — same distance/ATR,
  same side/direction, same race/horizon. T1 adds a second **virgin null**: matched level must
  also lie beyond the rolling 100-bar extreme (see decomposition below). Holdouts: temporal
  thirds y1/y2/y3 + crc32(sym)%2 halves; PASS = same-sign effect in all 5 cells.
- Inventory: 9,122 pools (37% swept, 44% broken; fatness f0/f1/f2+ = 51/33/16%; median birth
  distance 6.1 ATR, median life 108 bars), 3,354 sweeps, 37,790 voids (median 2.68 ATR, 96%
  contain ≥1 FVG), 93,259 lone FVGs, 9,123 coil breaks. Invariants independently brute-force
  verified on 3 symbols (pivot prices, no pre-death penetration, sweep/break tags, run
  direction/efficiency, compression edges): all clean.

## T1 — pool magnetism ("price goes there")

Reach probability of the pool level within N bars vs a matched random level at the same
distance/ATR/side.

| event | N | pool | null | excess | t | cells | gauntlet |
|---|---|---|---|---|---|---|---|
| birth | 100 | 0.389 | 0.395 | −0.007 | −1.5 | mixed | fail |
| birth | 200 | 0.533 | 0.540 | −0.007 | −1.8 | mixed | fail |
| approach (≤3 ATR) | 24 | 0.480 | 0.559 | **−0.079** | **−12.8** | all − | PASS (reversed) |
| approach (≤3 ATR) | 50 | 0.622 | 0.722 | **−0.100** | **−17.5** | all − | PASS (reversed) |
| birth, VIRGIN null | 100 | 0.389 | 0.373 | +0.016 | +3.2 | all + | PASS |
| birth, VIRGIN null | 200 | 0.533 | 0.490 | **+0.043** | **+9.3** | all + | PASS |
| approach, VIRGIN null | 24 | 0.480 | 0.472 | +0.009 | +1.4 | mixed | fail |
| approach, VIRGIN null | 50 | 0.624 | 0.592 | +0.033 | +5.4 | all + | PASS |

**The decomposition is the finding.** Against an honest distance-matched null, pools are NOT
magnets — an approaching price is 8-10pp MORE likely to stall short of the old extreme than
short of an arbitrary equally-distant level (t −13..−18, all cells). The deficit is entirely the
virgin-territory effect: any level beyond the recently-traded range is hard to reach, and pool
levels are virgin by construction. Restrict the null to equally-virgin levels and the sign flips
to a modest positive (+1.6pp N=100, +4.3pp N=200, t +9.3): among untraded levels at the same
distance, the old-extreme-anchored one is the most reachable. So the taught claim survives only
in comparative form — "of the hard-to-reach levels, price prefers the old extreme" — and fails
as an absolute targeting law.

Fatness: NOT monotone vs plain null (f0 −1.6pp, f1 +0.8, f2+ −0.7). Vs virgin null the taught
direction weakly appears (approach N=50: f0 +1.8pp t2.1, f1 +5.1 t4.7, f2+ +4.4 t2.8 — fat >
thin, but f1 > f2+, not strictly monotone). "Fatter = fatter magnet" unproven; what fatness
demonstrably measures is the level's tendency to keep HOLDING (its plain-null deficit grows with
fatness: −7.0/−8.3/−8.9pp).

## T2 — sweep → reversal prophecy (the stop-hunt engine)

1×ATR first-crossing race from the event close, reversal direction = away from the swept side;
null = same race at matched time-local bars (drift-honest: null "reversal" rate 0.46, not 0.50).

| event | n | respect | null | excess | t | gauntlet |
|---|---|---|---|---|---|---|
| sweep (wick through + close back) | 3,290 | 0.482 | 0.460 | **+0.022** | **+2.25** | **PASS** (5/5 cells +) |
| plain touch (held, no penetration) | 2,745 | 0.466 | 0.466 | +0.001 | +0.05 | fail |
| sweep − touch | — | — | — | +0.016 | z +1.24 | fail (y1,y3 ≈ 0) |

- The sweep event carries a real but TINY prophecy: +2.2pp over null, symmetric across sides
  (H +2.2, L +2.3), flat across fatness. Absolute respect is still <50% — a sweep does not make
  reversal the majority outcome; it only beats the drift-adjusted coin.
- Plain touches carry nothing → the signal is in the wick-through-and-reject event itself, not in
  proximity to the level (this also kills the "mechanical lid" objection: touches sit closer to
  the level than sweep closes and show zero). But sweep≫touch as taught is NOT robust (z 1.2).
- **HUNT reconcile**: of sweeps whose reversal does arrive, median arrival = 2 H1 bars; 67% ≤3,
  88% ≤6, 98% ≤12 bars. Same front-loading HUNT measured at 5m (82-93% of hunts complete within
  the first hour, hazard ratio 5-12×), one TF up. Consistent verdict: the post-sweep reversal is
  real, small, and mostly SPENT within hours of the sweep — by the time the sweep closes, the
  harvest is largely done. The stop-hunt engine exists; its tradable residue at H1 is +2pp.

## T3 — void corridor law

| claim | measured | verdict |
|---|---|---|
| price travels FAST inside a re-entered void | per-bar speed inside 0.508 vs 0.527 ATR/bar matched-outside (ratio 0.96, t −11.2, all cells; close-in-zone conditioning biases slow — but even the unbiased traversal test shows no speed) | **rejected** |
| — traversal-time version | P(cross full span ≤30 bars) 0.516 vs momentum-matched null 0.520 (fail); ≤100 bars 0.728 vs 0.714 (+1.4pp, t +5.8, PASS) | no speed edge; weak completion-reliability edge only |
| voids fill SLOWLY vs lone FVGs | median bars-to-full-fill: void 23 (89.5% filled) vs lone FVG 3 (96.6%); FVG by size: <0.25 ATR → 2, 0.25-0.5 → 3, ≥0.5 → 7; all 5 cells +20 bars | **CONFIRMED** (size-confounded — voids are ~10× taller — but holds vs the largest FVG tier) |
| origin (far edge) = decision point ≫ mid-void | edge respect 0.491 (n=33k) vs mid respect 0.496 (n=31k), z −1.25, cells mixed | **rejected** — no edge premium at all |

The void is a real container that takes ~an order of magnitude longer to repay than its FVG
bricks — but once price is inside there is no frictionless corridor (if anything marginally
slower per bar), and the origin edge decides nothing that the middle doesn't.

## T4 — PO3 accumulation → manipulation

9,123 coil breaks (median wick-break lag 0 bars from onset; 49% upside — symmetric).

| comparison | rev rate | vs | rev rate | diff | z/t | gauntlet |
|---|---|---|---|---|---|---|
| coil break | 0.724 | non-coil 14-bar range break (matched, range ≥4×ATR) | 0.717 | +0.007 | +1.4 | fail |
| swept-pool break (n=182) | 0.363 | plain break (n=8,921) | 0.731 | **−0.369** | −10.2 | PASS — but REVERSED vs taught |

Depth-controlled (break-wick penetration beyond edge): shallow <0.5 ATR reverts 0.90/0.89
(swept/plain), 0.5-1 → 0.62/0.65, 1-2 → 0.35/0.37, ≥2 → 0.03/0.11. Two conclusions:
1. **"Manipulation" is the default grammar of ANY range edge, not a compression specialty**:
   ~72% of all wick-breaks of a 14-bar range close back inside, coiled or not. The coil adds
   +0.7pp — nothing. Detectability of the AMD manipulation phase ex ante ≈ zero at H1; what is
   detectable is the universal fact that shallow edge-breaks fail (0.90 → 0.10 monotone in depth).
2. The taught "swept break → reversal more often" is REJECTED and reversed: raw swept breaks
   revert far less, and that entire −37pp gap is the depth mechanical (a wick that reaches a pool
   is by construction a deep wick); within depth buckets swept ≈ plain or slightly worse. Pools
   beyond a coil edge add no reversal information.

## Pass/fail vs the taught claims

| # | taught claim | effect | t/z | robust (5 cells) | verdict |
|---|---|---|---|---|---|
| T1 | pools are targets, price goes there | −0.079/−0.100 (approach, plain null) | −12.8/−17.5 | yes (reversed) | **REJECTED absolute**; +1.6..+4.3pp survives vs virgin null (comparative form only) |
| T1 | fatter pool → stronger magnet | non-monotone (plain); fat>thin weakly (virgin) | ≤2.8 | no | unproven |
| T2 | sweep → reversal | +0.022 | +2.25 | yes | **CONFIRMED, tiny**; front-loaded (med 2 bars, 88% ≤6) |
| T2 | sweep ≫ plain touch | +0.016 | +1.24 | no | direction right, not robust |
| T3 | void = fast corridor | −0.019 ATR/bar; traversal ≤30 −0.004 | −11.2/−1.4 | — | **REJECTED** (weak completion edge ≤100 only) |
| T3 | voids fill slower than FVGs | +20 bars median | — | yes | **CONFIRMED** |
| T3 | origin edge ≫ mid-void | −0.005 | −1.25 | no | **REJECTED** |
| T4 | coil break = manipulation (reverts > matched break) | +0.007 | +1.37 | no | **REJECTED** — 72% reversion is universal to range edges |
| T4 | swept break → reverts more | −0.369 raw; ≈0 depth-controlled | −10.2 | yes (reversed) | **REJECTED** (depth artifact) |

## VERDICT

The taught liquidity grammar, re-anchored to validated zigzag extremes and tested against honest
time-local matched nulls on 3y × 138 symbols: **two organs are real, most of the mythology is
not.** Real: (1) the sweep event — wick through an extreme-anchored pool and close back — carries
a small (+2.2pp, t 2.25, all-cell robust), heavily front-loaded reversal edge, the H1 echo of
HUNT's 5m front-loading; (2) the void/FVG asymmetry — containers repay ~10× slower than their
bricks. Not real at H1: pool magnetism as an absolute law (approaching price stalls short of old
extremes 8-10pp MORE than the null; only the within-virgin comparative form survives), fatness
monotonicity, the frictionless void corridor, the origin-edge decision point, compression as a
manipulation precursor, and swept-breaks-revert-more (a depth artifact — the real, strong,
universal law is: shallow range-edge breaks revert 90%, deep ones 10%, monotone). Methodological
lesson of the run: a distance-matched null silently mixes traded and virgin territory — the
virgin-null decomposition is what separated "pools repel" from "pools are the least-avoided
virgin levels"; both statements are true and neither is the taught one. Nothing here re-opens
economics; per H1GRID any tradable residue must clear ~0.1-0.2R toll and +2pp of direction at
1×ATR scale does not.

---
Artifacts (scratchpad, `ts3_` prefix): `ts3_lib.py` (detectors: pools v2 / sweeps / voids /
coils, patched-zigzag reuse), `ts3_build.py` (events + outcomes + matched & virgin nulls),
`ts3_agg.py` (stats + gauntlet, log `ts3_agg.log`), `ts3_check.py` (independent invariant
verification), `ts3_probe.py` (calibration), parquets `ts3_t1_pools / ts3_t1_app / ts3_t2_events
/ ts3_t3_voids / ts3_t3_fvgs / ts3_t4_coils`.
