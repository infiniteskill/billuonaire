# 32 — DEEP SYNTHESIS of the 20 taught trades (2026-07-22)
Re-brainstorm across ALL trades in dev/IMG/trades/ (t1..T20). Individual reads in
31-TOOL-TWEAKS.md. This is the step-back: what is the method REALLY, what drives the big RR,
and what single test settles whether it is real or survivorship.

## 1. The corpus, factually
- 20 trades, 3 stocks (HAVELLS ~15, VOLTAS ~3, DLF ~2). Both directions (slightly more shorts —
  down-moves are faster/cleaner). 5m execution, 30m context. Holds: hours (LTF tight-stop, T5)
  to WEEKS (persistent zones, T12/T15/T16). RR ~1:3 to ~1:15.
- EVERY ONE IS A WINNER the user hand-picked. This is the load-bearing fact (see §5).

## 2. Strip the SMC vocabulary — what the method ACTUALLY is
Under all the OB/FVG/breaker/mitigation language, every one of the 20 is the SAME trade:

  **FADE THE FAILED BREAKOUT OF A MATURE RANGE'S EXTREME.**

  Mature range forms (days-weeks) → price SWEEPS a range extreme = an OBVIOUS liquidity level
  (old high/low, equal-highs, breakout point where retail stops + breakout orders cluster; T11
  "all SL taken by bank", "all breakout longs destroyed") → the breakout FAILS (closes back
  inside) → the zone (OB/FVG) at the sweep is where smart money transacted → price RETESTS it →
  ENTER mid, tight structural stop just beyond the swept extreme → target the OPPOSITE extreme /
  far liquidity / unfilled FVG.

This reframe unifies all 20 and connects to a KNOWN effect (false-breakout reversal / turtle
soup), which we measured real but small: sweep→reversal +2.2pp, front-loaded (LIQ.md).

## 3. What drives the BIG RR (the 1:15) — the magnitude hypothesis
The tight RR comes from LTF-refined structural stops (T5/T9 internal-OB → 3-5pt stop). The big
REWARD (the move running far) correlates, across the 20, with ONE thing more than any other:

  **RANGE MATURITY / VOLATILITY CONTRACTION before the break.**

  The biggest runners (T12 −137pt, T15 −105, T16 −137, T17 +49, T19 −80) ALL came after a LONG,
  TIGHTENING consolidation AT the zone (13-day ceiling, 157-bar block, coil-under-resistance /
  coil-above-support). This is volatility contraction → expansion — a documented, real market
  behavior. The zone that produces the runner is the extreme of a MATURE, COMPRESSED range that
  finally breaks; a zone in an open/young range just scratches (T7 two-sided fades).

  => magnitude driver = range maturity + compression + runway to opposite extreme. This subsumes
  the three earlier runner-flag candidates (trapped-crowd T11, runway T5/T10, compression T15-17)
  into one: the failed-breakout of a MATURE COMPRESSED range with runway to the far extreme.

## 4. The composite the method reduces to (ONE measurable strategy)
  FIND: mature range (rolling N-day, tightening ATR/range) on a stock.
  MARK: its extremes = obvious liquidity + the OB/FVG there.
  WAIT: sweep of an extreme + failed breakout (close back inside).
  ENTER: retest of the sweep zone, MID, tight structural stop just beyond the swept extreme
         (LTF internal-OB refined).
  TARGET: opposite range extreme / far liquidity / unfilled FVG.
  GRADE(magnitude): range maturity + compression + runway distance.
This is neither "generic OB fade" (measured dead) nor plain momentum. It is a specific
false-breakout-after-contraction play. UNTESTED as a composite with honest fill-through.

## 5. The brutal honest limitation (must lead every conclusion)
All 20 are WINNERS, hand-picked, 3 stocks. The 44-feature ML on 300k signals already showed
identical-anatomy setups: ~16% become these runners, ~41% die immediately, and NO chart feature
separated them out-of-sample better than ~0.52 AUC. So the 20 are the 16% tail, selected AFTER
they won. The corpus teaches what a winner looks like in HINDSIGHT — NOT how to tell it from its
losing twin AT ENTRY. Until we measure the §4 composite on ALL setups (winners AND losers) across
138 stocks with holdouts, the 20 prove the pattern EXISTS, not that it is TRADEABLE.

## 6. The two numbers that decide everything (the build's only job)
  A. RANGE-MATURITY/COMPRESSION FLAG: does "failed-breakout of a mature-compressed-range extreme
     + runway" separate the 1:5+ runners from the scratches EX-ANTE, holdout-stable, on all
     setups (not just the 20)? (Attacks §5.)
  B. FILL-THROUGH: does the tight structural stop (beyond the swept extreme, LTF-refined) realize
     its paper RR after honest gap-through fills, or does it fill through to −2/−3R (REFINE −4.2R
     ghost)? (Decides if 1:15 paper = 1:15 real.)
  If A yes AND B holds → profit lever, and we know WHY (contraction→expansion + trapped crowd).
  If either fails → the 20 are survivorship + paper mirage; method = scratch + toll (settled).

## 7. Build order (when the ~50-example corpus is complete)
1. Range/compression detector (rolling maturity + ATR contraction) — the missing tool; everything
   else (extremes, sweep, OB/FVG, internal-OB, break-depth) is built.
2. Composite finder: mature-range extreme + failed-breakout sweep + retest zone + LTF internal-OB
   entry + tight structural stop + far-extreme target. Universe scan (138 stocks).
3. Measure A and B on ALL emitted setups, 4-way holdout, honest fill-through. That single run is
   the verdict on the entire taught method.

## The one-line synthesis
The 20 trades are one strategy — fade the failed breakout of a mature, compressed range's extreme,
enter the retest with a tight structural stop, target the far extreme — and its profitability
rides entirely on (A) whether range-maturity/compression flags the runners ex-ante and (B)
whether the tight stop survives fill-through. Both are measurable; neither is measured yet; the
20 winners prove the pattern is real but not that it beats the toll.
