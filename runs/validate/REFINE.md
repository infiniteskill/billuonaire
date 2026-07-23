# REFINE — wired taught-profile recognition loop, iteration 1 (2026-07-23)

Harness (profile-respecting): `study --only <14 taught detectors> --dir runs/validate/taught_profile
--data data/wide` — restricts to exactly the taught set WHILE using the profile's params
(anchor=ext, require_sweep_bos, extremes multi-TF). Runs on 1-minute data (data/wide, ~17d; the
pipeline is M1-only — long5m/5m is silently dropped). Measures per-detector recognition (hit% vs a
seeded same-session baseline) UNDER THE WIRED PROFILE. NB: recognition, never edge (RETHINK).

## Iteration-1 measurement (HAVELLS + DABUR, 4533 evidences)
| detector.event | n | edge (hit-base) | fwd12 | note |
|---|---|---|---|---|
| premium_discount (gate) | 1370 | — (NEUTRAL) | 1.77 | gate context firing ✓ |
| liquidity POOL_NEAR | 554 | — (NEUTRAL) | 1.68 | EXT pools now emit ✓ (was starved) |
| sweep SWEEP | 596 | +10.8% | -0.06 | recognition +, fwd ~0 |
| fvg_n IFVG_RETEST | 395 | +13.4% | 0.07 | |
| fvg CE_HOLD | 303 | +9.1% | -0.02 | |
| fvg_n FVG_N_RETEST | 404 | +8.9% | 0.02 | |
| propulsion2 PRP | 34 | +9.7% | 0.25 | |
| wyckoff PHASE | 314 | +7.0% | 0.12 | |
| orderblock OB_RETEST | 399 | +4.6% | -0.11 | GENERIC ob (not ob_taught) |
| compression BOX_ON_LEVEL | 124 | +2.5% | 0.29 | matches prior ~flat |
| wyckoff UPTHRUST | 3 | +26.7% | 4.69 | n=3 noise |

## THE STARVATION CHAIN (iteration-1 finding — the tune targets)
Emitted ZERO under the profile: **structure(anchor=ext) → ob_taught(require_sweep_bos) → htf_nest.**
- **structure(ext)=0**: needs EXT_H/EXT_L on its tf (5m) forming a clean HH+HL / LH+LL trend. Either
  extremes did not emit EXT on 5m (leg_pct 2% still too coarse at 1m→5m, or the tf param path), or
  the EXT trend never formed. ROOT of the chain.
- **ob_taught=0**: its require_sweep_bos gate needs a same-dir structure BOS in history — structure
  emits 0 → gate never opens. Starved DOWNSTREAM of structure, not itself broken.
- **htf_nest=0**: needs the SAME decisional zone on multiple TFs (orderblock/fvg run single-tf) → no
  cross-TF nest ever forms.

## Iteration-2 tune targets (next loop)
1. **Diagnose extremes on 5m**: confirm EXT_H/EXT_L actually emit on the 5m tf under the profile;
   if not, lower leg_pct further per-tf (extremes.md P1: ~1.5%) or fix the multi-tf param path.
2. **structure(ext)**: once EXT_5m exists, verify the trend forms; consider lowering trend_swings
   (4→2) so 2 EXT pairs suffice, or a looser EXT trend rule.
3. **ob_taught gate — DESIGN FLAW found**: require_sweep_bos = sweep AND structure-BOS. But
   `structure` only emits when EXT form a TRENDING HH+HL/LH+LL sequence — and the taught method
   FADES MATURE RANGES, where by definition there is no trend-BOS (a range = NEUTRAL trend →
   structure emits nothing → gate never opens). So the gate starves precisely in the setup's home.
   The real taught birth trigger is the SWEEP at the range extreme + the LTF reversal (a micro-
   CHoCH after the sweep), NOT the HTF trend-BOS. FIX: gate ob_taught on SWEEP (596 available)
   +/- a micro reversal, not on structure's trend-BOS. Relax `_gated` to require swept AND
   (bos OR just-swept-reversal); the sweep is the signal that fires in ranges.
4. **htf_nest**: run orderblock/fvg on multiple TFs (5m/15m/1h) so a base zone has HTF parents to
   nest inside; else htf_nest can never fire.

## Standing read (unchanged)
The recognition-emitting detectors show +2–13% hit-edge but **fwd12 ≈ 0** — the same "recognition
real, edge toll-bound" signature as the prior measured record. The refine loop tunes RECOGNITION
(does the wired stack fire on the taught objects); the PROFITABILITY verdict still needs losing
setups + a tradebook and is not obtainable from this loop.

## Iteration 2 (2026-07-24) — the sweep-gate fix
Applied: ob_taught gate_mode="sweep" (fire on the swept extreme, not trend-BOS);
structure trend_swings 2. Re-measured HAVELLS+DABUR (5222 evidences).
- **ob_taught UNSTARVED: 0 -> 689** (OB_RETEST 345 +7.2%, BRK_RETEST 135 +8.4%,
  MIT_RETEST 209 +17.9%). The range-fade fix works: ob_taught now fires on the
  sweep as designed. MIT (mitigation flip) is the strongest directional edge.
- structure(ext) still 0 (17d rangy data has no EXT trend; no longer on the
  critical path since ob_taught gates on sweep, not structure). Acceptable.
- htf_nest still 0 -> needs multi-TF OB/FVG zones; orderblock/fvg run single-tf,
  so no cross-TF nest forms. Needs an HTF-zone emitter or multi-instance detectors
  (deferred infra). Iteration-3 target.
The entry chain (premium_discount gate + liquidity/sweep trigger + ob_taught entry)
now fires end-to-end -> decision.py can produce take/skip. Edges remain recognition
(+7..18% hit) with the standing fwd12~0 signature; profitability needs the derived
tradebook (run decision.py over all data -> winners+losers -> net-R).

## DERIVED TRADEBOOK (2026-07-24) — the user's idea, measured
tools/derive_tradebook.py: run the wired taught profile over 1m, call decide() on
every fresh-zone bar, each take = a trade, simulate forward on M5 (gap-aware,
slippage on every fill). Winners AND losers derived from the tools — no user log.
HAVELLS+DABUR, min_grade=1, slip=2 ticks:
- takes=355, closed=345. **win%=15% (54W/291L)**. outcomes: stop 181, GAP 108, target 56.
- gross +508R, net +1.4R/trade after slippage (was +7.3R before slippage).
- avg_win **23.7R**, avg_loss -2.64R.
HONEST READ — this is a PAPER MIRAGE, not an edge:
1. **31% GAP-THROUGH** (108/345) — the fill-through killer materialising at scale
   (RETHINK/doc-34's dominant risk, live).
2. Net rests ENTIRELY on a huge-RR winner tail (24R avg wins) = the tiny-stop RR
   illusion; sensitive to slippage (7.3R->1.4R on a 2-tick change) and to M5-vs-tick
   granularity (finer path = MORE stop-outs = worse).
3. **Grade NON-MONOTONE: grade 2 (+1.06R) < grade 1 (+1.79R)** — the decision grade
   does NOT discriminate winners. The SELECTION (the whole point of the tools) is not
   working yet; without it this is the generic pattern, not the user's edge.
4. win% 15% matches the prior measured "16% run" — consistent with the standing null.
=> The derived-tradebook METHOD works (winners+losers from tools, no user log). The
NUMBER is paper. Before it means anything: tick-granular fill-through sim, per-trade
rupee costs (not flat R), and a grade that actually separates winners (selection).
