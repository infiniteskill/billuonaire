# 28 — FINAL SYNTHESIS: the complete measured map (2026-07-18)

The definitive close of the intraday research campaign. Every question answered with maximal
sample: **300,153 signals, 138 stocks, 57 sessions (60d native 5m), 8.4M realistic-fill
simulations**, 7 parity-locked tools, all leak-free, all holdout-split. Reports:
`runs/long60/{RESULTS,RECALL,HUNT}.md` (archived in dev/plan/artifacts/).

## THE SNIPER TABLE (definitive — full universe)
| tool | n | hit% | base% | edge | MFE/MAE | best realistic exp | holdout+ |
|---|---|---|---|---|---|---|---|
| inducement | 9,177 | 48% | 33% | **+0.15** | 1.00 | −0.283 | no |
| mitigation | 43,095 | 48% | 39% | +0.10 | 0.97 | −0.276 | no |
| ob_lux | 79,028 | 49% | 40% | +0.09 | 0.96 | −0.302 | no |
| fvg_cb | 37,009 | 48% | 39% | +0.09 | 0.99 | **−0.244 (best)** | no |
| compression_fade | 113,445 | 49% | 39% | +0.09 | 1.00 | −0.291 | no |
| turtle_soup | 5,429 | 46% | 38% | +0.09 | 0.94 | −0.307 | no |
| bpr | 12,970 | 50% | 44% | +0.05 | 1.02 | −0.259 | no |

- **Every tool's hit-edge is REAL and confirms on genuinely new out-of-sample data** (first-half
  sessions never used before: all 7 confirm, ±1pp). The parity+continuum fixes made nothing worse
  (fvg_cb/inducement/bpr materially better).
- **MFE/MAE 0.94–1.02 at n=300k: the tape's excursions are symmetric. Final.**
- **0 of 196 solo configs net-positive. 0 stacked. 0 pairs (of all 42). 0 chains. 0 anything,
  holdout-stable, at any SL × target × management × filter.**

## EVERY QUESTION CLOSED (the campaign's measured answers)
1. Do SMC/ICT tools predict? **YES** — +5–15% hit-edge over matched random, holdout-stable, 300k n.
2. Do they pay? **NO** — symmetric excursions + realistic fills + retail costs = −0.24..−0.31R/trade always.
3. Fade vs momentum? **Both dead** — symmetry is a property of the M1/M5 NSE tape, not signal polarity.
4. Confluence/stacking? **Dead** — apparent lift was look-ahead; causally the FIRST signal is fullest.
5. Layered cascade (direction→location→timing)? **Dead** — each layer worsens (−0.43→−0.55); zones
   predict CONGESTION, not release.
6. Do tools see the human-visible trades? **NO** — union 72.5% vs random-budget 81.1%; zero run-start
   selectivity; 58% of trend-continuation starts invisible (all tools pullback-shaped).
7. Stop-hunt thesis? **PROVEN + quantified** — the stop is the product: tight −1.07R → no-stop −0.19R
   (tax scales inversely with distance); 82–93% of hunts complete within the first hour post-entry;
   shadow-stops get re-harvested.
8. Hunter's seat (passive limit into the sweep)? **Canceled exactly by adverse selection**
   (discount +0.09..+0.39R vs penalty −0.07..−0.40R at every depth) — the efficient price of the seat.
9. Volatility/straddle (compression→expansion)? **NO-GO** — expansion ×1.02–1.08 vs random, random bar
   captures 95% of the payoff.
10. Liquidity subset? **Not the lever** (identical coverage; mid-caps marginally less bad).
11. More data? Used the max free depth (60d 5m × 139 + 30d M1 × 141). Edges stable across all of it.

**BOTTOM LINE: free-data NSE intraday cash equity, traded by OHLCV-technical signals at retail
costs, has NO extractable edge — proven from every angle, in dry-run, with zero rupees lost.**
The prediction edge is real but magnitude-less; extraction fails structurally, not parametrically.

## WHAT SURVIVES (the assets)
- A production-clean research platform: 7 parity-locked detectors, no-lookahead continuum pipeline,
  replay + realistic-fill + cost engine, study/holdout harnesses. 701 tests green. Externally
  reviewed (9/9 findings verified + fixed).
- The honest map above — which prevents every future re-derivation of these dead ends.

## THE THREE UNTESTED DOORS (need different data or timeframe — user's call)
1. **Kite depth-20/OI** — the hunter's live cluster map; the one data asymmetry that is purchasable.
   All NO-GOs above were OHLCV-only; order-flow signals are a genuinely different class.
2. **Daily/swing timeframe** — above the intraday hunting machine; overnight drift/earnings effects;
   free daily data with DECADES of history (proper multi-regime validation, unlike the 60d cap).
3. **Forward accrual** — weekly re-fetch grows the 5m dataset ~20 sessions/month for free.

## LIVE-READINESS ENGINEERING DEBTS (only if something ever clears the gate)
Incremental detectors (kill O(n)/tick rescans) · process-parallel replay (~10×) · detector-state
persistence across restarts · (all logged; none blocks research).

## ADDENDUM (2026-07-18, post-close tests)
- Daily-POI anchoring: real +1.1pp, economically dead (`artifacts/dailypoi-anchoring.md`).
- NESTED fractal + liquidity-swing conjunction (the full top-down model): +0.5-1.4pp vs +6pp bar, holdout-unstable, 0 positive cells (`artifacts/nested-fractal-confluence.md`). Confluence family closed COMPLETELY.
- Both external code reviews reconciled (24 claims verified; all real bugs fixed). 739 tests green.

## FINAL ADDENDUM — THE COMPLETE TIMEFRAME LADDER (2026-07-18, terminal)
Every rung measured: 5m/M15/H1(3y)/H4/daily(30y)/weekly. Raw asymmetry rises with TF (0.99→1.79); the RANDOM-ENTRY NULL rises in lockstep. **Excess-over-null ≈ 0 at every timeframe.** Cross-TF (daily zone + H1 entry) LOWERS ratios. H4 standout = 2023-24 smallcap beta (dead 2025-26, 5-symbol concentrated). Buy-and-hold of the traded names beats every config (18.4%/yr vs 16.9% best). Costs collapse at daily scale (0.045R) — cost was never the problem; the edge does not exist. THE PROGRAM IS COMPLETE: zone-retest mechanics = repriced noise (intraday) / repriced drift (positional) at every scale. Only free edge: long Indian equities — an index fund implements it better. Reports: runs/ladder/LADDER.md, runs/daily/FEASIBILITY.md, runs/long60/*.md.
