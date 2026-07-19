# ZONES — taught zone toolkit (lessons 2,3,4,9,12,13,14): build + pure-DETECTION respect tests

Scripts: session scratchpad `ts2_lib.py` / `ts2_build.py` / `ts2_tests.py` (+ `ts2_eps.parquet`,
`ts2_zone_counts.csv`). Reuses `dev/research/tob_lib.py` (patched ATR-zigzag, taught OB clusters,
pivot-distance), `ext_zigzag.py` (Wilder ATR), `dgrid_lib.py` (`fvg_cb` strict-3 gap).
Data: `runs/artifacts-data/l4_h1.parquet` — 138 NSE syms × H1, 2023-08 → 2026-07. Splice-guarded
(no episode/null spanning a >20% close→open jump). This run measures **detection quality only**
(does price respect the level more than a matched random level) — no economics, per the standing
honesty note; the H1GRID/TAUGHT_OB net-after-cost verdicts stand untouched.

## The toolkit as built (taught spec)

1. **FVG-N** (lesson 2): generalized N-candle gap — flanking wicks non-overlapping across a
   displacement burst of 1..5 middle candles; burst = every middle CLOSES beyond the near flank
   wick; same adaptive size threshold as `fvg_cb`. Strict-3 = m=1 special case (parity kept:
   `fvg_cb` verbatim). m≥2 gaps deduped against any accepted gap with overlapping candle-window
   AND band — reported gaps are ones strict-3 cannot see.
2. **Taught-OB** (lesson 3): `tob_lib` opposite-candle cluster boxes + pivot-distance rank,
   verified and kept — zone count reproduces TAUGHT_OB.md exactly (54,471).
3. **Flip family** (lessons 4/12): zone closed through its far edge → flip to opposite side.
   OB flips split by the one-question sweep test at flip time (causal running extreme of the birth
   leg vs prior same-side zigzag pivot): swept → **BRK**, failure-to-swing → **MIT**. Gap flips →
   **IFVG**.
4. **Propulsion** (lesson 14): parent OB's first armed retest bar that closes back outside the box
   with a directional body → child zone = that candle's range, parent-linked; parent liveness at
   the child's own retest tagged (`plive`) to test "child dies with parent".
5. **Rejection band** (lesson 13, for the ladder): body-edge → wick extreme at every confirmed
   zigzag pivot, sweep-tagged.
6. **Overlap grade** (lessons 4/9): stacked-zone count `nst` at the touch = live same-direction
   zones (any type, flips die at their flip bar) whose bands intersect the touched band.

Zone counts (138 syms): OB 54,471 · FVG3 27,414 · **FVGN 37,962 (+138% recall over strict-3)** ·
IFVG 59,979 · BRK 29,883 · MIT 17,378 · PRP 8,096 · REJ 11,281. Episodes (armed first retests,
race resolved): 199,641 (72 unresolved dropped).

## Method

- **Respect** = at the first armed retest (price fully left the box, then first touch of the
  proximal edge E): favorable excursion ≥1×ATR(touch) from E before adverse ≥1×ATR, zone's implied
  direction, 70-bar window, same-bar tie = adverse (conservative).
- **Null** (per H1GRID's null-B lesson — month-matched nulls inherit the selection path; time-local
  is the honest frame): per episode, 5 path-clean random levels — anchor bar drawn from the
  episode's own [arm, touch] window, level placed at the SAME signed ATR-distance-from-price the
  real edge had at arming, same symbol/side; first touch of that level races the identical 1×ATR
  test. 98.8% of episodes got ≥1 valid draw (mean 4.3/5). Lift = respect − null, paired.
- **Blow-through** = close through the far edge before the favorable 1×ATR prints.
- **Holdout**: temporal thirds × crc32%2 symbol halves = 6 cells; pass = same-sign lift in all 6.
  `t_sym` = t over 138 per-symbol mean lifts (cluster-robust check).

## T1 — zone-type respect ladder vs matched null

| type | n | respect | null | lift | t | t_sym | holdout 6/6 |
|---|---|---|---|---|---|---|---|
| OB | 45,748 | 59.0% | 56.6% | **+2.36pp** | +12.0 | +11.2 | PASS |
| FVG-N (all gaps) | 52,340 | 56.1% | 54.1% | +2.09pp | +11.9 | +12.4 | PASS |
| — FVG3 (strict) | 22,436 | 56.1% | 53.8% | +2.27pp | +8.4 | +7.3 | PASS |
| — FVGN (new) | 29,904 | 56.2% | 54.2% | +1.95pp | +8.5 | +8.1 | PASS |
| IFVG | 47,644 | 58.2% | 55.4% | **+2.86pp** | +15.6 | +16.2 | PASS |
| BRK | 23,780 | 57.6% | 55.1% | +2.46pp | +9.5 | +8.0 | PASS |
| MIT | 13,965 | 58.4% | 55.8% | +2.58pp | +7.6 | +6.8 | PASS |
| PRP | 4,338 | 59.0% | 55.4% | **+3.57pp** | +5.9 | +5.6 | PASS |
| REJ | 9,444 | 57.8% | 57.1% | +0.76pp | +1.5 | +1.4 | **FAIL** (3/6) |

Every taught zone type except the rejection band beats its matched null with 6/6 holdout cells and
symbol-clustered t ≥ 5.6. The effect is real and systematic — and small: +2–3.6pp on a ~55% base.
REJ is furniture (swept subset no better: +0.48pp, t=0.7).

### P2 — breaker > mitigation (lesson 12): **FALSIFIED**
BRK 57.6% vs MIT 58.4% — diff **−0.76pp** (z=−1.4), null-adjusted lift diff t=−0.3, holdout 2/6.
The sweep test does not rank flip zones; liquidity-taken adds nothing to the flip's respect here.

### P3 — propulsion child dies with parent (lesson 14): **CONFIRMED, strongest result of the run**
Parent-live PRP 60.2% respect (lift +4.05pp, t=+6.6, n=4,219) vs orphaned 16.8% (lift **−13.3pp,
t=−4.3**, n=119) — diff +43.4pp, z=+9.5, 6/6 cells. An orphaned propulsion zone is not merely
weaker, it is anti-signal: worse than a random level at its own distance (its touch usually rides
the same move that killed the parent). Parent linkage is mandatory, exactly as taught.

### P4 — FVG CE midpoint terminus (lesson 2): **FALSIFIED (inverted)**
Respected in-gap retraces (n=29,136): P(terminus within ±0.15×gap of CE) = **24.0%** vs uniform
30.0% (z=−22.3, 6/6 cells negative). Terminus deciles 0.03/0.07/0.12/0.17/0.23/0.30/0.39/0.49/0.65
— bounces cluster at the PROXIMAL EDGE (median depth 0.26 of the gap), not the midpoint. On H1 NSE
tape the working level of a gap is its edge; CE is not a terminus attractor.

## T2 — overlap monotonicity (lesson 9, THE grade law)

| stacked | n | respect | null | lift |
|---|---|---|---|---|
| 1 | 3,414 | 54.6% | 54.6% | +0.08pp |
| 2 | 11,690 | 54.0% | 54.2% | −0.26pp |
| 3 | 18,836 | 55.1% | 54.3% | +0.80pp |
| 4+ | 163,319 | 58.4% | 55.6% | +2.81pp |

**Headline: respect(4+) − respect(1) = +3.80pp, z=+4.5, 6/6 holdout cells positive — PASS on
direction; strict monotonicity FAILS at the low end** (dip 1→2; strictly monotone in only 2/6
cells). Extended tail is cleanly monotone: 54.0% (2) → 57.2% (5) → 60.3% (10+). Stacking grades
zones — but the signal lives in the deep-stack tail, and unstacked/lightly-stacked zones carry no
lift at all (lift ≈ 0 for nst ≤ 2: an isolated zone is indistinguishable from a random level).

## T3 — pivot-distance gradient (lesson 3 power law)

OB (0 / 0–2 / 2–5 / >5 ATR from origin pivot): respect 59.7 / 59.6 / 59.6 / 58.0% — **monotone
decay pooled, at-pivot − mid-leg = +1.68pp, z=+2.8, holdout 5/6 → soft pass** (fails the strict
6/6 gate in one cell; same direction and size as TAUGHT_OB's economic t=2.86). FVG gradient is
non-monotone: the dist=0 bucket (gap straddling the pivot extreme, n=2,452) collapses to 39.1%
respect — but its null is 39.9% (lift −0.8pp): that's location, not detection failure; buckets
0–2/2–5/>5 decay 58.5 → 55.9%. The power law is real for OBs and modest.

## T4 — blow-through decomposition + does the grading predict it?

Blow-through rate at first retest: **27.1%** of 199,641 episodes (REJ worst 37.5%, OB best 23.4%;
definition here = close through far edge before a favorable 1×ATR — TAUGHT_OB's 42% was
max-penetration >1.0 over a trade span, a looser bar). Decomposition confirms the taught ranks:
blow% falls monotonically with stacking 34.7% (nst=1) → 23.3% (6+); by taught-grade quartile
(rank(dist) − rank(overlap)) blow% = 23.1 / 26.0 / 29.1 / **32.1%** best→worst.

**AUC(low-grade → blow-through): composite 0.553, overlap-only 0.581, distance-only 0.505 — all 6
holdout cells >0.5 → PASS.** The taught grading genuinely predicts which zones fail on first touch,
with overlap doing nearly all the work; it is a weak-but-robust one-number detector (0.55–0.58),
nowhere near deterministic.

## T5 — FVG-N recall

The N-candle generalization finds **37,962 additional gaps = +138% recall** over strict-3's 27,414
(per-m: 2→12.7k, 3→8.6k, 4→5.3k, 5→3.3k episodes). Quality of the new gaps is indistinguishable
from strict-3: respect 56.2% vs 56.1% (z=+0.1), lift +1.95pp vs +2.27pp, stable per m (55.5–56.3%).
The new gaps blow slightly more often (31.0% vs 28.0%). Verdict: the generalization more than
doubles gap coverage at equal detection quality — strict-3 was leaving over half the taught
structure on the table.

## Pass/fail summary

| test | prediction | result | holdout |
|---|---|---|---|
| T1 ladder | each type > its null | PASS 7 types (t_sym 5.6–16.2); REJ fails | 6/6 each; REJ 3/6 |
| T1-P2 | breaker > mitigation | **FAIL** — inverted −0.76pp, z=−1.4 | 2/6 |
| T1-P3 | live-parent PRP > orphan | **PASS** +43.4pp, z=+9.5; orphan anti-signal | 6/6 |
| T1-P4 | CE terminus > uniform | **FAIL** — inverted 24.0% vs 30%, z=−22 | 0/6 (all inverted) |
| T2 overlap | monotone increase | PASS direction (+3.80pp 4+ vs 1, z=+4.5); strict mono fails low end | 6/6 direction |
| T3 distance | monotone decay | OB soft pass (+1.68pp, z=+2.8); FVG anomalous at dist=0 | 5/6 |
| T4 grading→blow | AUC > 0.5 | PASS — 0.553 comp / 0.581 overlap; quartile blow 23→32% | 6/6 |
| T5 FVG-N | new gaps as good | PASS — +138% recall at equal respect (z=+0.1) | 6/6 |

## Verdict

The taught zone toolkit **detects real structure**: every constructive zone type (OB, FVG-N, IFVG,
BRK, MIT, PRP) beats path-clean matched random levels in all six holdout cells, the overlap grade
predicts both respect and blow-through, and the two structural mechanisms the lessons insist on —
parent linkage for propulsion and stacking for grade — are the two strongest effects measured.
Three taught refinements are falsified on this tape: the breaker/mitigation sweep ranking (no
difference), the CE midpoint terminus (bounces stop at the edge, inverted at z=−22), and the
rejection band (furniture, swept or not). Magnitudes stay detection-sized: +2–4pp respect over a
~55% null on a ±1×ATR race — consistent with the standing record that recognition is real while
2R-fade economics are sub-cost (TAUGHT_OB, H1GRID). Use: overlap≥4 + live-parent + pivot-near as
zone *context/grading* for the momentum program; drop REJ, drop the sweep split, treat gap CE as a
weakening line only, and always kill propulsion children with their parent.
