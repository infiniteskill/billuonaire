# THE JUICE LOOP — repeatable system-improvement playbook (v1, 2026-07-25)

The exact loop that ran stage2. Re-run any time (new marks, new detectors, new data) to extract more.

## THE LOOP (7 steps)
1. **OBSERVE** — 3-4 parallel agents read trade screenshots pixel-carefully → obs_*.md
   (per image: TF, annotations, box top/bot prices, anchor candle, wick-vs-body edges, trade marks).
   Prompt template in git history (commit c735975 era). ~100k tok/agent.
2. **SPEC** — diff visual language vs detector code myself → _SPEC.md (unified drawing rules + gaps
   ranked + questions for user). Key: separate MATCHES from GAPS, severity by fidelity impact.
3. **AUDIT** — 3-4 parallel agents, one per detector family; each: code-vs-spec (line numbers) +
   DETECTION ACCURACY vs ground-truth marks on data/marks_2026 (zone engines are step-fed classes —
   test WITHOUT pipeline) + surgical tweak proposals with exact A/B commands. → audit_*.md
4. **FIX** — code the tweaks PARAM-GATED, DEFAULTS FROZEN (behavior-preserving; full pytest must stay
   green). Bug fixes (real defects) direct; behavior changes always behind a param + env override
   (DERIVE_PROFILE / DERIVE_* pattern).
5. **RECOGNITION TEST** — does the detector now produce the user's exact drawn object (price±0.4%,
   date±3 bars)? study --only on trimmed mark-window data; compare vs obs notes.
6. **EDGE GATE** — batch battery: solo profiles per variant (runs/validate/aud_<v>/config.json) →
   `DERIVE_PROFILE=... DERIVE_DATA=data/wide derive_parallel.py <40syms> 12 tb_aud_<v>.csv`
   sequential script (thermal-safe). Verdict = deduped eod hi>=5 +minRR net-R must HOLD/IMPROVE
   vs frozen +7.34R AND quads. Cross-regime (bull/bear tapes) before any merge.
7. **VERDICT + LOG** — _<X>-VERDICT.md per round: SHIP (free/improving) / KEEP-stage2 / REJECT→
   fidelity-layer. Update memory + commit. NOTHING ships to main without 6 passing.

## INVARIANT LESSONS (9 gated attempts, stage2)
- fidelity ≠ edge (decoupled, proven 9x). Grade inputs at robust optimum — expect REJECT.
- rejects are NOT waste: they become the DIAGNOSTIC/RECOGNITION layer (faithfulness, selection
  metadata, live-UI drawing, future re-tests in seconds via saved params).
- accuracy trap: higher win% variants (G4 81%) lose net-R. Judge NET-R only.
- broad fixes fail (B1 emit_live), surgical param-gated fixes are testable + reversible.
- sim limits: entry-fill race not modeled (G5), tick fills optimistic — don't over-trust ±0.3R deltas.

## ASSETS (reusable)
- tools/derive_parallel.py (12-shard, verified==serial) · tools/ab_tradebook.py (offline gate) ·
  Z1 tradebook CSVs · DERIVE_{PROFILE,DATA,MIN_RR,RUNWAY,ENTRY_DEPTH,JOURNAL} + PD_LOOKBACK_DAYS +
  EXT_EMIT_LIVE envs · aud_* solo profiles · stage2_profile (keepers+diagnostics).
- ground truths: tools/ytrades.json (32 marks, month/day, year mostly 2026) + obs_*.md exact prices +
  data/marks_2026 (7 stocks Jan-Jul 2026 1m).

## NEXT-JUICE candidates (when re-running)
S3 session-scale sweep pass (multi-day sweeps DEAD-early — needs LevelEngine D1 plumbing) · S4 EXT
carry · S5 recency floor · I1 disp→grade · I2 mono_run (audit-rejected v1) · user's 5 drawing-rule
answers (_SPEC.md §D) · 2H/30m/10m Timeframe extension · G1-as-selection-TAG offline A/B ·
compression maturity duration term (dead constant) · 1d extreme anchor.
