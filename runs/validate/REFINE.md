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
