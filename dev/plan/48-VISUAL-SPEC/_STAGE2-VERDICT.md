# STAGE2 — visual-gap sweep G1-G5: all coded, recognition-tested, edge-gated (2026-07-25)

| gap | code | recognition | edge gate | disposition |
|---|---|---|---|---|
| G1/G2 multi-TF OB/FVG parents | timeframes param (orderblock+fvg), 915 green | **PASS** — t28 exact entry band 583.35-584.40 recovered (base missed); NEST 209→659; depth-3 alive | hi≥5 eod +4.92 vs +6.94 → FAIL (dilution) | **diagnostic layer** — fidelity/faithfulness/selection metadata, NOT a grade input |
| G3 sweep poke localization | LevelEngine poke_ts/poke_price → Level.meta → sweep Evidence | unit-verified both paths (pending-bar poke ✓) | metadata-only = edge-safe by construction | **KEPT in stage2** |
| G4 runway ext+eq targets | runway param in decide, DERIVE_RUNWAY | targets = user's liquidity lines ✓ | +minRR +6.87/81%win vs +7.34/68% → −0.5R = accuracy trap | REJECT; param default-off (high-win variant documented) |
| G5 entry depth 0.25 | entry_depth param, DERIVE_ENTRY_DEPTH | — | ±0.03R noise; sim can't price limit-fill risk | NEUTRAL; keep 0.5 frozen |

META (confirmations 4-6 of robust optimum): every edge-touching visual fix either dilutes (G1),
trades net-R for accuracy (G4), or is noise (G5). The frozen grade + RR asymmetry already captures
the taught edge; visual fidelity improvements belong in the DIAGNOSTIC/RECOGNITION layer.
Fidelity assets gained: 48-VISUAL-SPEC (85-img language), multi-TF parent infra, poke anchoring,
runway/entry params (all env-A/B-able in seconds for any future retest).
Open (needs user answers, _SPEC.md §D): OB far-edge rule, SL law, target priority, entry-depth rule, TF ladder.
