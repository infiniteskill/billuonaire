# dev/research — validated reference scripts

The measurement scripts behind the falsification program (previously only in
ephemeral /tmp scratchpads; preserved here by audit-3 E). Results live in
`runs/` (esp. `runs/long60/`, `runs/wide/`) and `dev/plan/` artifacts —
see `dev/plan/26-AUDIT-AND-VALIDATION-FINDINGS.md` for the verdicts.
All 17 listed scripts were copied; none were missing.

Shared methodology core:
- `h2hlib.py` — shared head-to-head lib: M1 CSV -> session-anchored multi-TF
  bars, outcome/baseline edge scoring, temporal + cross-sectional holdout.
- `rr.py` — RR-aware expectancy (tight SL beyond the destroy extreme; win% at
  R=2/3/5/10) for breaker / compression-fade / sweep-reclaim signals.
- `step2_engine.py` — realistic-fill outcome sim replicating paper.py
  economics (spread/slippage/costs) + filters + holdout.

Concept head-to-heads (ours vs faithful LuxAlgo/ICT ports):
- `luxob.py` — LuxAlgo internal Order Block vs our orderblock.
- `fvg2.py` — LuxAlgo FVG (close-beyond, mean-range threshold) vs our
  0.3xATR gap; retest + CE-hold events, M5/M10/M15.
- `compress.py` — compression coil as timing signal; break-of-compression
  entry with HTF direction filter.
- `ict_pieces.py` — 5 untested ICT structure aspects (iFVG/BPR/CE etc.) as
  standalone detectors.
- `ind_sweeps.py` — LuxAlgo Market Structure with Inducements & Sweeps port.
- `liq_hunt.py` — judas swing, OR-sweep, turtle soup, gap trap, round-number
  sweep-reclaim, draw-on-liquidity.

long60 definitive battery (results in `runs/long60/`):
- `l60_capture.py` — STEP 1: signal capture over data/long5m (138 stocks).
- `l60_solo.py` — STEP 2: per-tool solo SL/target/management grid.
- `l60_combo.py` — STEP 3: causal combination grid (co-fire, sequence, stack).
- `l60_report.py` — assembles `runs/long60/RESULTS.md`.

Higher-timeframe anchoring (confluence family closure):
- `dailypoi_build.py` / `dailypoi_measure.py` — causal daily OB/FVG/S-R POIs
  tagging intraday signals; hit-edge + net expectancy + holdout money scan.
- `nested_build.py` / `nested_measure.py` — nested fractal confluence
  (daily zone -> H1 OB/FVG nest levels) -> `runs/long60/NESTED.md`.
