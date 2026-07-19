# GEO — stop/target geometry sweep on the FACTS ladder cell

Question: FACTS.md's only gross-positive stable cell — **nextday+ ∧ sweep_aligned ∧ h1_nested** (n=557, hit 52.1%, netR −0.102 at the uniform 1.5×ATR/1R/0.06% sim) — does ANY stop/target geometry let that gross survive the (shrinking) toll and cross zero net, holdout-stable?

**Answer: NO. All 20 geometries × all 5 cells are net-negative pooled. The gross edge decays FASTER than the cost as the stop widens. DEAD under the program's honesty rule.**

## Setup

- Trades rebuilt per zone from `data/long5m` (bit-identical parity: the exact-fill k=1.5/1R reproduction matches `facts_first.parquet` net_r to 0.0 on all 75,972 valid trades; base 46.1%/−0.187, ladder 52.1%/−0.102).
- Cells: base (all 80,636 zones), nextday+ (n=22,738), nextday+ ∧ h1_nested (14,057), nextday+ ∧ sweep_aligned (936), LADDER (557; 545 valid trades).
- Geometries: stop k×ATR(5m,14) for k ∈ {1.5, 2.5, 4, 6, 10}; targets {1R, 1.5R, 2R}; trail variant = no target, stop trails 1R below run-max once +1R is reached. 20 geometries per cell.
- Realistic fills everywhere below: next-bar-open entry, intrabar stop-first (tie→stop), **gap-through stop fills at bar open beyond stop** (gap past target likewise fills at open), EOD close at the 15:05-bar close (15:10). Trades stay intraday-from-retest; no overnight holds (dead per SWING.md). Realistic fills shift the base by only +0.001R vs exact fills — intraday 5m gaps are small.
- Cost per trade: cost_R = 0.0006·entry/(k·ATR). Ladder-cell ATR5/price: mean 0.29%, median 0.27% → k=10 stop ≈ 2.7–2.9% of price ≈ H1 scale.
- Holdouts: temporal split 2026-06-08 (T1/T2) × crc32(symbol)%2 (C0/C1). CI = t-approx 95% on netR (bootstrap concordant, quoted for the two best rows).
- Trail rows: "hit%" = share of trades with positive gross (no fixed target exists).

## Ladder cell (n=545 valid) — geometry × outcome

| k | target | hit% | grossR | costR | netR | 95% CI netR | T1 / T2 / C0 / C1 (netR) | 4-way |
|---|---|---|---|---|---|---|---|---|
| 1.5 | 1R | 52.1 | +0.058 | 0.159 | −0.101 | [−0.185, −0.017] | −0.105 / −0.098 / −0.076 / −0.131 | all-neg |
| 1.5 | 1.5R | 38.9 | +0.034 | 0.159 | −0.126 | [−0.228, −0.024] | −0.139 / −0.115 / −0.095 / −0.162 | all-neg |
| 1.5 | 2R | 28.8 | +0.024 | 0.159 | −0.135 | [−0.249, −0.021] | −0.157 / −0.116 / −0.097 / −0.178 | all-neg |
| 1.5 | trail | 52.3 | **+0.136** | 0.159 | **−0.024** | [−0.142, +0.095] | −0.021 / −0.026 / +0.001 / −0.052 | mixed (3 neg) |
| 2.5 | 1R | 42.6 | +0.003 | 0.096 | −0.093 | [−0.172, −0.014] | −0.096 / −0.090 / −0.032 / −0.163 | all-neg |
| 2.5 | 1.5R | 26.1 | −0.012 | 0.096 | −0.107 | [−0.197, −0.017] | −0.137 / −0.082 / −0.079 / −0.139 | all-neg |
| 2.5 | 2R | 18.2 | +0.006 | 0.096 | −0.089 | [−0.188, +0.009] | −0.157 / −0.031 / −0.080 / −0.100 | all-neg |
| 2.5 | trail | 50.1 | +0.022 | 0.096 | −0.074 | [−0.169, +0.022] | −0.103 / −0.048 / −0.018 / −0.137 | all-neg |
| 4 | 1R | 27.0 | +0.001 | 0.060 | −0.059 | [−0.126, +0.007] | −0.093 / −0.030 / −0.022 / −0.101 | all-neg |
| 4 | 1.5R | 13.4 | +0.009 | 0.060 | −0.050 | [−0.123, +0.022] | −0.115 / +0.006 / −0.021 / −0.084 | mixed |
| 4 | 2R | 4.4 | −0.000 | 0.060 | −0.060 | [−0.133, +0.014] | −0.141 / +0.009 / −0.018 / −0.108 | mixed |
| 4 | trail | 51.0 | −0.005 | 0.060 | −0.065 | [−0.137, +0.006] | −0.135 / −0.005 / −0.020 / −0.117 | all-neg |
| 6 | 1R | 13.6 | −0.000 | 0.040 | −0.040 | [−0.093, +0.013] | −0.090 / +0.003 / −0.029 / −0.052 | mixed |
| 6 | 1.5R | 3.5 | −0.010 | 0.040 | −0.050 | [−0.103, +0.004] | −0.105 / −0.002 / −0.024 / −0.080 | all-neg |
| 6 | 2R | 1.7 | −0.005 | 0.040 | −0.045 | [−0.100, +0.010] | −0.099 / +0.001 / −0.016 / −0.078 | mixed |
| 6 | trail | 51.0 | −0.004 | 0.040 | −0.044 | [−0.099, +0.011] | −0.096 / +0.001 / −0.016 / −0.076 | mixed |
| 10 | 1R | 2.4 | −0.012 | 0.024 | −0.036 | [−0.071, −0.002] | −0.068 / −0.009 / −0.028 / −0.045 | all-neg |
| 10 | 1.5R | 0.6 | −0.010 | 0.024 | −0.034 | [−0.069, +0.002] | −0.064 / −0.007 / −0.022 / −0.047 | all-neg |
| 10 | 2R | 0.2 | −0.009 | 0.024 | −0.033 | [−0.068, +0.002] | −0.063 / −0.007 / −0.021 / −0.047 | all-neg |
| 10 | trail | 50.8 | −0.009 | 0.024 | −0.033 | [−0.068, +0.002] | −0.063 / −0.007 / −0.021 / −0.047 | all-neg |

Not one of the 20 rows has pooled netR > 0, let alone 4-way positive. The best row (trail @ k=1.5, netR −0.024) straddles zero on CI (bootstrap [−0.141, +0.097]) but is negative in 3 of 4 holdout cells. Most CIs straddle zero at wide k only because the numbers have shrunk toward zero, not because anything turned positive.

## Parent rungs — netR per geometry (same fills/costs)

| k | target | base (75,972) | nextday+ (22,173) | nd+ ∧ h1n (13,652) | nd+ ∧ swp (920) | LADDER (545) |
|---|---|---|---|---|---|---|
| 1.5 | 1R | −0.186 | −0.153 | −0.144 | −0.116 | −0.101 |
| 1.5 | trail | −0.153 | −0.116 | −0.113 | −0.030 | −0.024 |
| 2.5 | 1R | −0.115 | −0.088 | −0.086 | −0.109 | −0.093 |
| 2.5 | trail | −0.089 | −0.070 | −0.070 | −0.082 | −0.074 |
| 4 | 1R | −0.076 | −0.055 | −0.058 | −0.071 | −0.059 |
| 4 | trail | −0.061 | −0.050 | −0.055 | −0.077 | −0.065 |
| 6 | 1R | −0.052 | −0.040 | −0.049 | −0.050 | −0.040 |
| 6 | trail | −0.046 | −0.036 | −0.046 | −0.054 | −0.044 |
| 10 | 1R | −0.032 | −0.027 | −0.033 | −0.042 | −0.036 |
| 10 | trail | −0.031 | −0.026 | −0.033 | −0.041 | −0.033 |

(1.5R/2R targets omitted for brevity: every one is negative in every cell; full grid in scratchpad `geo_cells.csv`.) Every parent × every geometry is net-negative, and all parents are 4-way all-negative or mixed-negative. The parents do agree on geometry *direction* — trail @ k=1.5 is the best geometry in every rung — but "best" means least negative everywhere.

## Is the +6.1pp stop-scale-dependent? Yes — strongly.

Ladder hit-lift and gross-lift vs the base universe at the same geometry (1R target):

| k | base hit% | ladder hit% | lift pp | base grossR | ladder grossR | gross-lift R |
|---|---|---|---|---|---|---|
| 1.5 | 46.1 | 52.1 | +6.1 | +0.001 | +0.058 | +0.057 |
| 2.5 | 37.1 | 42.6 | +5.5 | −0.003 | +0.003 | +0.006 |
| 4 | 22.3 | 27.0 | +4.7 | −0.006 | +0.001 | +0.006 |
| 6 | 10.4 | 13.6 | +3.2 | −0.005 | −0.000 | +0.005 |
| 10 | 2.5 | 2.4 | −0.1 | −0.004 | −0.012 | −0.008 |

- The hit-lift survives to k=6 in pp terms but its gross value collapses immediately: +0.057R at k=1.5 → +0.006R at k=2.5 → ~0 → negative at k=10. The prior program pattern (hit% rises as stops widen) doesn't even apply at fixed R-multiple targets: the target scales with the stop, so hit% *falls* (52→2.4%) and EOD-close takes over the exit mix (1.5% of exits at k=1.5 → 94% at k=10). At H1-scale stops the trade is just "hold to 15:10", where the ladder cell has zero directional drift (gross −0.01R).
- Trail gross-lift, 4-way: pooled +0.101R at k=1.5 [T1 +0.100, T2 +0.102, C0 +0.138, C1 +0.059 — all positive], then −0.001 at k=2.5 and ≤0 beyond. The gross edge is real, 4-way stable — and lives entirely at the 1.5×ATR(5m) scale. It is a small-move edge: +0.136R × 1.5ATR ≈ 0.20×ATR5 ≈ **0.06% of price**.

## The arithmetic

At what k does cost_R fall below gross? **Never.**

| k | costR | best grossR (geometry) | gross − cost |
|---|---|---|---|
| 1.5 | 0.159 | +0.136 (trail) | −0.024 |
| 2.5 | 0.096 | +0.022 (trail) | −0.074 |
| 4 | 0.060 | +0.009 (1.5R) | −0.050 |
| 6 | 0.040 | −0.000 (1R) | −0.040 |
| 10 | 0.024 | −0.009 (2R/trail) | −0.033 |

Cost falls 6.7× from k=1.5→10, but gross falls from +0.136R to below zero over the same span. The closest approach is at the *tightest* stop, not the widest: trail @ k=1.5, where gross ≈ 0.20×ATR5 ≈ 0.060% of price vs the 0.06% toll — **the best geometry earns almost exactly the toll, gross, and nothing more**. Breakeven hit at 1R targets ((1+cost)/2): 58.0% needed vs 52.1 measured at k=1.5; 54.8 vs 42.6 at k=2.5; 53.0 vs 27.0 at k=4 — the gap *widens* with k. FACTS' implied gross (+0.09R) was slightly optimistic: it used the base-universe cost (0.19R); the cell's own cost is 0.159R (higher-ATR names), so measured gross is +0.058R at the uniform geometry.

## Verdict under the honesty rule

This sweep added 100 cell×geometry looks (20 geometries × 5 cells) on top of an already-selected cell (~19 combos in FACTS, ladder z=2.86). The program's standard: a positive counts only if net>0 pooled, same-sign in all 4 holdout cells, AND the parent rung shows the same geometry direction.

- **Zero geometries reach even the first gate**: no pooled netR > 0 anywhere, in the ladder cell or any parent.
- The only 4-way-stable facts found are negative ones: 15 of 20 ladder geometries and nearly all parent geometries are net-negative in all four holdout cells.
- Parent confirmation exists only for the *shape* of the result (trail @ 1.5×ATR is uniformly the least-bad geometry), not for any positive.

**DEAD.** The ladder cell's gross edge is genuine (4-way positive gross at k=1.5, both 1R and trail), but it is a ~0.06%-of-price edge racing a 0.06% toll, and it does not scale: widening the stop dilutes the edge faster than it dilutes the cost. No stop/target geometry monetises this cell at 0.06% round-trip. What would change the answer is not geometry but the toll itself (≲0.03% round-trip would put trail @ k=1.5 near water: gross +0.136R vs cost ~0.08R → ~+0.06R — but that is a different broker, not a different exit).
