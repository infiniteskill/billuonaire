# 34 — DEEP-OBSERVATION CONCLUSIONS (all 27 trades, feature-level) (2026-07-22)
4 parallel vision-observers combed every screenshot in dev/IMG/trades/ for EVERY feature
(liquidity, OB, FVG, sweep depth, internal-OB, flip-family, BOS/CHoCH, P/D, entry, SL, target,
runway, compression, touches, timing, cascade, micro). This is the QUANTIFIED fingerprint and
what it changes for the build. Supersedes the qualitative reads where more precise.

## The corpus, corrected
- 27 trades. **t1–t17 are ALL HAVELLS** across DIFFERENT YEARS/eras (tab title constant, price
  eras 1125–1234 / 1500–2100 / 1240–1360). Cross-STOCK proof = VOLTAS (t18/t19), DLF (t19b/t20/
  t21), TITAN (t22/t23), DABUR (t24–t27, low-vol FMCG). So: cross-TIME (HAVELLS, many years) +
  cross-STOCK (5 names) + cross-VOL (fast TITAN ↔ slow DABUR). Fractal confirmed at feature level.
- FILING NOTE: the cleanest Lesson-7 composite (DLF short, SWING-LIQ/OB/BOS/FVG-target) is
  MISFILED in T19/ (a VOLTAS folder) as the 10-40-23 image.

## The quantified fingerprint (hard numbers across the 27)
1. SWEEP = wick-through-close-back (failed breakout) of an OBVIOUS level in ~26/27. The level is
   specifically EQUAL-HIGHS/EQUAL-LOWS (double/triple tap), not just any pivot. Poke beyond is
   SMALL (~3pt HAVELLS, ~12pt TITAN — a fraction of range), NEVER a deep close-through.
2. ZONE at the sweep candle: opposite-color-before-impulse bodies-cluster. STACKS — OB+FVG+
   propulsion+breaker co-locate (t25 "ob+propulsion", t27 "ob fvg entry", T1 OB+FVG+breaker).
   Internal-OB nesting gives the precise entry (T9 literally OB→INTERNAL OB→ENTRY; T8/T13/T20).
3. ENTRY = MID of the zone (literally written on T3/T4/T6/T9/T16) or edge; on a DELAYED retest
   (hours → 2–3 weeks). Persistent zones: entry on the FINAL of 4–6 touches.
4. **SL = JUST beyond the swept extreme, TINY: 2–5pt DABUR, 3–13pt HAVELLS, 7–11pt VOLTAS,
   20–50pt TITAN.** THIS is what manufactures the RR — see #6.
5. TARGET = opposite extreme / far liquidity pool / unfilled FVG. Runway ~constant per stock
   (~50–90pt HAVELLS). Direction always into the correct P/D half.
6. **RR IS MANUFACTURED BY THE STOP, NOT THE TARGET.** Targets are ~constant (50–90pt HAVELLS);
   stops vary from tiny (3–4pt) to modest. The 1:15–1:18 monsters (T10-leg2, T12, T15) are the
   ones with ~3–4pt stops, NOT bigger targets. => the WHOLE RR edge lives in the stop being tiny
   => the FILL-THROUGH question (does the 3pt structural stop hold or gap through) is even MORE
   central than thought: it is the entire edge, not a detail.

## THE MAGNITUDE DRIVER — now concretely MEASURABLE (was the open problem)
Every big runner followed a MATURE, TIGHTENING consolidation AT the zone; the ONE non-runner
(T7) had a YOUNG/OPEN range and two-sided-scratched. Quantified maturity of the runners:
- T12: ~13-DAY coil under the ceiling, 5–6 touches → 1:18 (biggest)
- T10-leg2: ~10-day coil → 1:15 ; T15: 157 bars at ceiling (tooltip) → 1:15–20
- T16: ~3-week ceiling → 1:10–13 ; T17/T18/t21: 2–3-week floor, 3–4 touches → 1:10–14
- T7 (counter-example): open ~5-day range, NO compression → scratch
=> The maturity flag is THREE hard features, not a vibe: (a) range DURATION in bars, (b) TOUCH
COUNT of the extreme, (c) range/ATR NARROWING (contraction ratio). These are exactly what
32-SYNTHESIS §6-A must test ex-ante on winners AND losers.

## NEW conclusions (beyond prior synthesis)
A. The swept level is specifically an EQUAL-HIGHS/LOWS cluster (double-tap), not any extreme →
   the SWEEP node requires an EQ-POOL, not a lone pivot. Sharpens decision-tree node 1.
B. RR edge = the tiny stop → fill-through is THE whole game (not one of two numbers — the
   dominant one). Prioritize the fill-through measurement first.
C. DIRECTIONAL ASYMMETRY: shorts cascade in ONE clean leg (down faster: T15 −105/T16 −137/T19
   −80). Longs GRIND, needing REPEATED floor taps (T17 double-bottom, T18 double-sweep, t21
   literal pyramid). => entry logic differs by side: short = one retest; long = expect multiple
   taps / scale-in. Node-6 management must be side-asymmetric.
D. Maturity is measurable as duration+touches+contraction (above) — the missing "compression
   detector" now has a concrete spec.
E. T7 is the corpus's proto-LOSER: same zones, NO compression → scratch. It is the single most
   valuable trade for the ex-ante test — it shows the compression flag SEPARATES a scratch from
   the runners IN THE CORPUS. (Still n=1; needs the full loser set, but it's a real signal.)

## Honest limits (all 4 observers independently flagged)
- All 27 are hand-picked winners; T7 is the only near-scratch. The fingerprint proves the pattern
  EXISTS and is consistent across time/stock/vol — it does NOT prove the zone is separable from
  its losing twin ex-ante. The quantified maturity features (duration/touches/contraction) are
  the concrete thing to test on winners AND losers.

## What this changes for the build (sharpened)
1. SWEEP node: require EQ-pool (equal-highs/lows), wick-through-close-back, small poke (< k×ATR).
2. COMPRESSION detector (the missing tool): range duration (bars) + touch-count + ATR-contraction
   ratio → a maturity score = the magnitude/grade input.
3. STOP: structural, just beyond the swept EQ extreme, LTF-internal-OB-refined → and MEASURE
   fill-through FIRST (it is the whole edge).
4. Management: side-asymmetric (short = single retest hold; long = multi-tap / pyramid).
5. Grade = maturity(duration+touches+contraction) + stack + parent-link + failed-breakout-of-EQ
   + runway. Journal all; measure A(maturity flags runners ex-ante on losers too) + B(fill-through).

## One-line conclusion
The 27 trades are one setup whose ENTIRE edge is a tiny structural stop beyond a swept equal-
highs/lows cluster, taken only when the range at that extreme is MATURE/COMPRESSED (measurable as
duration + touch-count + ATR-contraction); the target is fixed runway to the opposite extreme, so
profitability reduces to two measurements — does maturity flag the runners ex-ante (incl. losers),
and does the tiny stop survive fill-through — the second being dominant.
