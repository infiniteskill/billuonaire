# CORE-HARDENING LOG (2026-07-26)

## Done
1. INVARIANT TESTS (app/tests/test_invariants.py, 5 green): propulsion-universe==ob_taught (C5),
   min_disp-subset law, poke<=swept + wick-beyond (G3), nest parent strictly-higher-TF (B2/G1),
   p/d lookback param path (C1). Always-on in default suite.
2. GOLDEN 3-REGIME: bull fixtures (ADANIPORTS, BAJAJ-AUTO Dec23-Jan24) + bear (BANKBARODA,
   BERGEPAINT Oct15-Nov24) — calibration + chain tests (see test_golden_path.py additions).

## RESTART-DETERMINISM AUDIT (verdict: replay-heals)
- Cursor detectors (ob_taught/fvg_n/propulsion2 `_n=0` on boot) + LevelEngine: full-history rescan
  rebuilds zones/states DETERMINISTICALLY from candles. Golden/derive reproducibility = the proof.
- Lost-on-crash without replay (graceful, not corrupting): sweep._dead_mem (missed S3 signals),
  fvg episode dedup (possible duplicate CE evidence same session), wyckoff phase memory (brief
  UNCLEAR), LevelEngine mid-episode pendings (a sweep in flight is dropped).
- DOCTRINE: live feed adapter MUST catchup-replay the session's M1 on boot (same code path as
  FileFeed). With replay, restart == never crashed. -> app-phase requirement, recorded in 49-ARCH.

## Remaining (C-list)
- extremes incremental zigzag (last O(n^2)); bit-identity proof required.
- F6 entry-parity test (FSM arm/entry mechanics vs decide-tap).
- Multi-year continuous stress run.

## F6 ENTRY-PARITY LOOP (2026-07-26) — 3 real production divergences found + fixed, 1 truth exposed
1. FIXED: FSM cost/reward priced the legacy mapped ~2R exit, not the taught far target ->
   costs_dominate strangled 55% of taught arms. Taught plans now ship taught_target/taught_sl via
   ScoredZone.mults; entry.arm prices the real target.
2. FIXED: production decide() window (evidence_history[-60:]) != research window (20x5m cutoff) ->
   production took trades research never validated. Aligned to the exact derive window.
3. FIXED(test): qty=1 harness starved economics (31 rupees reward vs 41 flat brokerage).
4. THE TRUTH (not a bug): the fill funnel — 194 verdicts -> ~44 armed -> 4 filled on the fixture.
   Resting limit at zone-CE fills ~10-20% of what the sim counts (rest: limit expires unfilled or
   zone breaks first). **LIVE total R = sim R x fill-rate x fill-quality-shift — the paper-pilot
   metric.** Pilot design must also test entry variants (edge-touch vs CE-limit vs marketable).

## SEAL (2026-07-26): 920 unit + 13 golden (5 chain + 5 regime + 3 parity) ALL GREEN.
Stress: 261-session continuous life, 228MB flat, no creep, no crash. Perf: hours -> ~5min/7mo-stock.
One command: `pytest tests/ -q && pytest tests/ -m golden -q`. CORE = SEALED.
Remaining before live: merge (user word) -> app essentials (feed/scanner/UI) -> PAPER PILOT
(fill-rate x fill-quality = the last unknown, pre-quantified at ~10-20% CE-limit fills on fixture).
