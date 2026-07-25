# ERROR PROPAGATION MAP — the tool chain + observed fault cascades (2026-07-25)

## THE DEPENDENCY DAG
extremes(zigzag pivots) ─┬→ liquidity (EQ pools from EXT/SWING mids, EXT pools master-gated)
                         ├→ structure (anchor=ext trend/BOS)
                         ├→ premium_discount (masters → dealing range → DIRECTION permit)
                         ├→ htf_nest (EXT bands = parents → nest_depth grade)
                         └→ ob_taught._grade (pivot_dist, pex sweep-test)
swings(fractal) ─────────┴→ (fallbacks for all of the above)
LevelEngine (state machine) → sweep detector (SWEPT episodes) → ob_taught gate_mode=sweep (ARM gate)
                                                              → structure CHoCH trap bonus
orderblock/fvg (Levels) → htf_nest bases+parents → decide node-3
ALL → decide(): node-0 p/d permit → node-2 zone → grade(bos+sweep+ote+phase+nest+maturity) → RR → take

## OBSERVED CASCADES (all found by the audits — real, not theoretical)
| # | fault at | propagates to | blast radius | status |
|---|---|---|---|---|
| C1 | extremes master=ALL-HISTORY | p/d range 1514/1123 vs taught 1234/1125 → WRONG DIRECTION permit | every trade's side (node-0) | p/d local-recompute coded; grade-input rejected, direction-layer kept |
| C2 | structure trend_swings=2 (dead) | bos grade NEVER fires | grade −1 UNIFORM (tier survived because error was uniform, not selective — luck) | fixed (ts4) |
| C3 | swings TF-echo | EQ fake touches → sweep min_touches strangles 69% → sweep grade point missing SELECTIVELY on taught setups | grade −1 selective | S2 coded, in gate |
| C4 | LevelEngine 2-close DEAD on 5m | multi-day lines die a day early → never SWEPT → gate_mode=sweep can't ARM | whole taught trades missing | S3 OPEN (D1-scale pass) |
| C5 | ob_taught min_disp wipes _run | zone never minted; propulsion2 (own tracker, NO gate) births children ob never saw | divergent universes 8.2× | prp fix shipped |
| C6 | ATR warm-up/backfill | every ATR-scaled gate shifts (min_disp, min_gap, depth-law, bands) | all zone lifecycles | monitored (Wilder backfill verified in extremes port) |

## DEFENSE DOCTRINE
1. **Per-stage recognition tests** (the audits) — each tool vs ground-truth marks INDEPENDENTLY,
   before blaming downstream. Order of debugging = DAG order: extremes first, decide last.
2. **Uniform vs selective errors**: uniform grade shifts (C2) mostly cancel in the tier; SELECTIVE
   errors (C3, C4 — biased against taught setups) silently rot the edge. Always ask which kind.
3. **GOLDEN-PATH chain test** (to build, next-juice): for 2-3 ground-truth trades (t28 SBICARD long,
   t24 DABUR short, HAVELLS 1221 short) assert EVERY stage end-to-end on real data:
   extreme@price → line@price → SWEPT on poke bar → zone edges ±0.4% → nest fires → grade ≥ X →
   decide.take with entry/SL/target ±0.4%. One pytest; breaks loudly when ANY link regresses.
4. **Consistency invariants** (cheap asserts): propulsion2 parent set ⊆ ob_taught journaled set;
   p/d range == extremes master pair when lb=0; sweep poke_ts ≤ swept_ts; htf_nest parent tf > base tf.
5. **Never trust a downstream metric to validate an upstream fix** — gate on BOTH recognition
   (stage-local) AND the end tier (global). The battery does the global half; golden-path the local.
