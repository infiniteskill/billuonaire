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
