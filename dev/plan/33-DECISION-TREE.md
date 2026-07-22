# 33 — THE DECISION TREE / REASONING ENGINE (TF-invariant) (2026-07-22)
User's reframe (t26): "this setup is irrespective of timeframe; we need deep braining, an
enhanced decision tree, advanced-level reasoning tools." CORRECT. The detectors (swing/sweep/
OB/FVG/breaker/mitigation/propulsion/internal-OB/compression) are BUILT. What is missing is the
REASONING that ORCHESTRATES them into a trade/no-trade decision — the thing the user's eye does.
This doc specifies that engine. It is scale-free: the SAME tree runs at ANY timeframe.

## Core insight
The taught method is not a PATTERN to match — it is a DECISION PROCESS to execute. A fixed
"detector fires -> emit signal" pipeline (what the engine does now) cannot express it, because
the value is in the SEQUENCING and the JUDGMENT at each node (which zone, is the sweep valid, is
there runway). So the build's center of gravity moves from detectors to a DECISION TREE that
consumes detector outputs and REASONS.

## TF-invariance (why one tree, any scale)
Every node's inputs are ratios/relations, not absolute bars: leg size in ATR, sweep = wick-beyond
+ close-back, zone = opposite-candle cluster, compression = range/ATR contraction, runway =
distance-to-far-liquidity in R. All scale-free. So the tree runs on D1, H1, 30m, 5m identically;
HTF picks the structure, LTF (same tree, zoomed) refines the entry. Multi-TF = the tree calling
ITSELF at a finer scale for node 3 (refine).

## THE TREE (each node: question -> branch; uses existing detectors)
0. RANGE/CONTEXT (any TF): is there a MATURE range? (duration >= N, ATR/range CONTRACTING).
   Mark its extremes (EXT pivots) = the liquidity levels. No mature range -> NO SETUP.
   [detector: extremes + NEW compression/range-maturity detector]
1. SWEEP: did price SWEEP an extreme's liquidity = FAILED BREAKOUT (wick beyond an OBVIOUS level
   -old high/low, EQ pool- then CLOSE back inside)? No -> WAIT. Yes -> bias = fade the sweep
   (high-sweep->short, low-sweep->long). [liquidity + turtle_soup + extremes]
2. DECISIONAL ZONE: is there a zone (OB/FVG/breaker/mitigation/propulsion) AT the sweep that is
   (a) FRESH -not run-past by a later same-dir sweep-, (b) NEAR the swept extreme (premium for
   supply / discount for demand), (c) not already deep-broken? No valid decisional zone -> SKIP.
   [ob_taught/fvg_n/flip-family + sweep-sequenced-validity (T1) + location filter (T8)]
3. REFINE (tree calls itself at finer TF): inside the HTF zone, find the INTERNAL zone (internal
   OB / FVG-inside) -> entry = its MID; SL = just beyond it / the swept extreme (structural,
   TIGHT). [internal-OB (T9) + fvg_n]
4. RUNWAY/TARGET: is there a FAR target with CLEAN space (opposite extreme / far liquidity pool /
   unfilled FVG) giving >= target R? Boxed-in / no runway -> SKIP (would only scratch). This is
   the magnitude gate. [liquidity pools + void + FVG-as-target (T19b)]
5. GRADE (magnitude confidence, 0..N): + compression maturity (T15-17) + stack depth (dedup) +
   parent-link (propulsion) + swept-OBVIOUS-liquidity/failed-breakout (T11) + runway distance.
   High -> take (size up); low -> skip. [grade.py extended]
6. MANAGE: hold to target / SLOW trail (1:3 -> 1:5+, never fixed greedy) / CASCADE re-entry on
   each new decisional zone along the trend (T10/T21) / EXIT on opposing CHoCH or zone flip.

## The "advanced reasoning tools" layer
Two nodes resist crisp thresholds and are where "deep braining" lives:
- node 0 "is the range mature/compressed enough" and node 2 "is THIS the decisional zone".
Options, in build order:
1. DETERMINISTIC first: hard features (range-duration, ATR-contraction ratio, sweep recency,
   sweep-sequenced-validity flag, location third). Measurable, holdout-testable. Build this.
2. REASONING-MODEL layer (optional, later): an LLM/vision-reasoning pass that reads the rendered
   chart + detector facts and adjudicates the fuzzy nodes like a human (the user's "advanced
   reasoning"). Use ONLY to re-rank/veto what the deterministic tree already found — never as the
   sole gate (unmeasurable, expensive). Its calls become new labels to measure against outcomes.

## What this changes for the build
- Center = app/trader/engine/decision.py: a tree that consumes detector Levels/Evidence + grade
  and outputs {take/skip, dir, entry, sl, target, grade, reasons[]}, journaled fully.
- Runs at a chosen structure TF; recurses to a finer TF for node-3 refine. TF-invariant by design.
- The two open verdict numbers (32-SYNTHESIS §6) are measured ON THIS TREE'S output: does the
  graded decisional-zone tier (A) flag runners ex-ante on all setups incl losers, and (B) survive
  fill-through. The tree is the thing whose output we measure — not individual detectors.

## t26 (the trade that prompted this) — recorded
DABUR short, FVG entry: swing ~522.5 -> supply FVG 520-521.5 -> mid-entry retest -> −2.3%.
FVG-as-zone = OB-as-zone (interchangeable, node 2). Confirms TF-invariance claim (same structure,
any scale). The trade is ordinary; the LESSON is the reframe: build the TREE, not more detectors.
