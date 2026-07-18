# 27 — Continuum Rebuild (2026-07-18)

User directive: the system trades intraday-only but ANALYZES CONTINUOUS multi-day data — yesterday's
OBs/FVGs/coils/structure stay live today. The h2h validation measured exactly that (concatenated
series). Three places the code diverged from the validated continuum (the fuck-ups, owned):

1. **Session-scope "fix" (15b3c97) was WRONG** — compression_fade/turtle_soup/bpr/mitigation validated
   on continuum, then session-scoped. → revert to continuum windows.
2. **ob_lux built per-session** (`today()`) vs validated multi-day luxob.py. → continuum.
3. **OB/FVG zone carry NEVER wired** — `_carry_over` drops all OB/FVG at session boundary; the
   validated cross-day zone-retest edge was never assembled in-framework. → carry until
   mitigated/aged(5d), engine-memory reset (3a1c615) stays.
4. Confluence verdict was measured on the mixed/broken toolset → re-test after fixes.

## Phases
- **CONT-1 (in flight):** continuum windows (5 detectors) + OB/FVG zone carry + inverted tests.
- **CONT-2:** per-tool PARITY harness vs h2h reference on real continuum data — detector event-set must
  match its scratchpad reference (luxob/fvg2/rr/ict_pieces/liq_hunt/ind_sweeps; rules cross-checked
  against dev/h2h Pine). Fix every divergence (inducement-style parity gate for ALL tools).
- **CONT-3:** re-measure on the continuum-faithful toolset: study (hit-edge), confluence re-test (why
  it failed → does continuum change it), full combination/permutation grid (detector × filter × exit),
  realistic-fill extraction. Data decides.
- **Wiring/robustness:** config validation (enabled ⊆ registry, weights nonzero), detector-failure
  degradation audit (run_all catches — verify + test), journal completeness.

## Calibration (honest, once)
Tape-symmetry (MFE≈MAE) was ALSO measured on continuum series directly — wiring fixes may not flip
economics. But the in-framework continuum-zone system was genuinely never tested, parity is the right
engineering regardless, and CONT-3 re-measures everything. No assumptions either way.
