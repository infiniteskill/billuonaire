# 47-40STOCK — NEXT ACTIONS + EXPECTED OUTCOME (2026-07-24)

Consolidates the two studies: the 40-stock deep study (`_SYNTHESIS.md`, symmetric-frame firing
analysis) + the 2024-Q4 cross-regime holdout (`../../../runs/validate/tb_2024q4_40.txt`, graded
derive on an unseen bear tape). The cross-regime PASS reorders the plan: **the edge survives across two
regimes as-is, so building is no longer urgent — the two highest-value moves are cheap PROOF checks.**

## MASTER TABLE — ranked by leverage × proof-value × risk

| # | action | bucket | why (evidence) | effort | risk |
|---|---|---|---|---|---|
| 1 | Sustained-BULL adversarial test — frozen config on a melt-up tape (2023-H2 / early-24) | PROVE | holds mixed-2026 + bear-2024Q4; bull = the ONE untested regime (longs-only, few pullbacks) | S | — |
| 2 | Faithfulness — co-locate hi-grade winners vs the 467 hand-marks | PROVE | both studies assume grade == the user's setups; never checked | S | — |
| 3 | Ship `b_hit>0` gate (drop 23.7% `b_hit==0` firehose) | SHIP | 40/40, regime-flat, −0R→+0.19R ungated | XS | low |
| 4 | Ship T3 stop = wick ±0.25·ATR | SHIP | 40/40, +10.5pp, does not invert | XS | low |
| 5 | Ship no-blind (strip strength/width/stacking from grade) | SHIP | AUC 0.49 = scoring noise on 35-37/40 | XS | low |
| 6 | Fix B1/T2 — re-anchor EXT to live unmitigated extreme | FIX | nest capped median 4.87 ATR inside true extreme on 92% stocks → best +8..26R shorts unemittable; fixes the one −edge detector | M [infra] | med |
| 7 | Recalibrate `b_hit` (isotonic) + select LOW-b_hit alpha | FIX | anti-calibrated: top-decile edge −0.121, bottom +0.204 | M | med |
| 8 | Build regime classifier (mode-switch) | BUILD | 2024-Q4 downgraded to OPTIMIZATION not survival; kills counter-trend-long tail (DOWN-LONG 44%) | L | med |
| 9 | Extreme + sweep + BOS gate (B8) | BUILD | held-extreme graded as A-setup; inverts RANGE 60%→DOWN 32% | M | med |
| 10 | Walk-forward (rolling refit vs frozen config) | PROVE | current holdout = frozen config, not walk-forward | M | — |

**Sequence:** (1)+(2) in parallel + ship (3-5) alongside → if pass, (6) T2 anchor → (8) regime classifier.

## EXPECTED OUTCOME — per bucket (honest, evidence-anchored, NOT invented precision)

| bucket | what to expect | what it will NOT do |
|---|---|---|
| SHIP (3-5) | ungated system cleaner: ~breakeven → modestly + (b_hit>0 = measured +0.19R); hi-tier win% a bit higher, variance lower | won't transform the hi-tier (already +6-8R); T3's net-R needs a 1m re-race vs the large-R target to quote |
| PROVE #1 bull | BINARY. PASS → thesis = "regime-proven across bull+bear+mixed" → green-light paper pilot. FAIL → edge is bear/range-specific → mode-switch (#8) becomes MANDATORY | not a P&L change; it's information |
| PROVE #2 faithful | PASS → "+8R IS the user's method." FAIL → it's a profitable LOOKALIKE (still maybe tradeable, but not the taught method) → re-frame | doesn't change historical R, changes the narrative + trust |
| FIX #6 T2 | the best textbook extreme-mitigations become EMITTABLE → hi-tier trade COUNT grows, htf_nest flips −edge → +edge; net-R likely up (those setups currently invisible) | magnitude unquantified until re-run |
| BUILD #8 regime | lifts ungated + trims the counter-trend-long tail; bigger effect on overall/low-tier than on the already-strong hi-tier | marginal on hi-tier |

## REALISTIC END-STATE (if all pass)

A cross-regime-validated, faithful, intraday-compatible GRADED system: hi-tier ~+6-8R/trade, win
~50-72%, gated to a few trades/stock/week → candidate for **small-size paper trading, then a live
pilot.** This is the strongest the thesis can get from historical 1m data.

**Residual risks that NO amount of the above removes** (the honest ceiling):
1. 2-3 historical regimes ≠ the future; regime can shift live.
2. 1m gap-aware sim ≠ real tick fills / slippage / partial fills / latency.
3. Live execution: order routing, liquidity/capacity per stock, squareoff mechanics.
4. Researcher degrees-of-freedom: every tune is a fitting choice — walk-forward (#10) is the guard.
5. The hi-tier's high bear-regime win may compress in chop; sample is finite.

**Bottom line:** the historical-edge question is nearly closed (2 regimes + grade ladder monotone
out-of-sample). After #1+#2, the remaining unknowns are **execution / live-frictions / future-regime**
— not whether the pattern existed. That is exactly the boundary where research ends and a paper pilot
begins.
