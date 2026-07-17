# Validation Methodology — the bar every idea must clear

Purpose: stop us shipping noise. One correlated month tuned in-sample is how backtests
lie. An idea in `14-IDEA-LEDGER.md` becomes `validated(OOS)` only when it clears ALL of:

## 1. Out-of-sample by TWO independent axes (not just time)
- **Temporal**: derive on earlier days, validate on later days. (Weak alone — one month
  shares one regime; our derive/validate were both rangebound.)
- **Cross-sectional (the real test we haven't done)**: tune on a random 10-stock subset,
  validate on the other 10, SAME period. Edge must survive on unseen instruments. This
  breaks the "both halves are the same range-days" trap.
- **Longer-coarse corroboration**: pull free 15m data (60 days) / daily (years). Detector
  logic is TF-agnostic in principle — a real edge should show at 15m over a longer, more
  regime-varied window. Directional agreement required, not exact magnitude.
- **Forward-accrued (gold standard)**: daily M1 fetch accrues genuinely-unseen days.
  In a few weeks these are the only truly clean OOS. Set up NOW so time compounds.

## 2. Statistical significance respecting autocorrelation
- Evidences are NOT independent (same stock, overlapping windows, same-day cross-stock
  regime). Effective n << raw n. Use **block bootstrap**: resample whole DAYS (or
  stock-days) with replacement, recompute edge, 1000×. Require **95% CI lower bound > 0**
  — point-estimate > baseline is not enough.
- Report effect size (edge in ATR/R units), not just hit%.

## 3. Multiple-comparison discipline
- We tested ~14 detectors × several param grids = dozens of hypotheses. Some "edges"
  survive by chance. Pre-register the idea list (the ledger IS the registry). Apply a
  correction: accept only edges with bootstrap p < 0.01 (roughly Bonferroni for ~20
  tests at 0.05). Marginal (0.01–0.05) → `validating`, needs more data, never `applied`.

## 4. Economic significance (survives the real world)
- Edge must clear the NSE cost floor AND be tradeable: after limit-fill slippage, ₹40
  round-trip, and the 1×ATR stop floor, does the signal produce positive NET expectancy
  at realistic size? A +6% hit-edge that nets negative after costs is not economic.
- Must not depend on lookahead, survivorship (all 20 are current NIFTY names — a survivor
  bias we accept but note), or a single outlier day/stock (jackknife: drop each day/stock,
  edge stays positive).

## 5. Portfolio-level, not just per-signal
- The final gate is the full replay: does the CHANGE improve month-level net expectancy,
  WR, PF, drawdown vs the frozen baseline — on the cross-sectional holdout stocks — with
  the change's own bootstrap CI on daily net-R excluding zero?

## Process per idea
1. Add to ledger as `proposed`.
2. Build the measurement in the validation harness (read-only; never touches prod code).
3. Run: temporal + cross-sectional + bootstrap CI + multiple-comparison check.
4. `validated(OOS)` only if all pass; else `validating` (need data) or `rejected`.
5. Applied to production in BATCHES, each batch re-validated at portfolio level on holdout
   stocks, committed behind the frozen-baseline comparison.

## Honest caveats we carry
- 20 survivor-selected liquid names, one 2026 window. Even "validated" = validated on
  THIS. Forward accrual + more regimes is the only cure; treat all current numbers as
  provisional until forward data confirms.
