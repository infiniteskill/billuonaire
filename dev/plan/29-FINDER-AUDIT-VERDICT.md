# 29 — FINDER AUDIT: "Are we really finding trades, or are we idiots?" (2026-07-18)

The user's exact question, answered with every measurement in the program. Verdict up front:

> **We really do find the setups — provably, repeatedly, at every timeframe. We are not failing
> at finding. We are failing because A FOUND SETUP IS NOT A WON TRADE: the same perfectly-found
> setup wins ~17–51% of the time depending on target, and the outcome is not knowable at find-time
> from any chart-visible feature. That is the audited, five-times-replicated answer.**

## PART 1 — Do we find the setups? YES (the evidence)
1. Parity: all 8 detectors bit-exact vs validated reference rules on real data (test-locked).
2. The user's own examples: **6 of 6 in-window chart setups found** (16/07 long, 10/07 short→32R,
   05/06 long→5.7R, 19/05 short→28R, 19/06 M1 wick short at 2201.9 — entry price matched TO THE
   TICK; 2 out-of-window zones explained by dataset start).
3. Coverage: union of tools reaches 75.5% of all clean ≥2.5-ATR runs; the missed residual is
   measured FEATURELESS (no M5-visible preamble — nothing left to find them by).
4. Timing: median lag −2..0 bars from ideal.
5. Multi-TF: the same zone is found at 1m/4m/15m zooms (it is ONE zone; TF is magnification, not
   information — outcome distribution identical across the ladder, measured).

## PART 2 — Are found setups "trades that don't fail"? NO (the evidence)
1. Same stock, same tools, same anatomy as the user's screenshots (HINDUNILVR, 57 sessions):
   1,995 found setups → **16% ran ≥5R (the screenshots), 41% went straight against and died.**
   8 losing twins with timestamps handed over for manual chart-verification.
2. The full conjunction ("everything coincides" = valid opportunity): 46% win at 1:1, −0.25R.
3. The 19/06 exhibit: perfect find, entry at the wick's exact top — survived by **12 ticks**.
   Its class (sub-0.2×ATR stops at refined zones): 83% stopped, **−4.2R/trade average**, exit
   slippage alone ≈ 2.8× the stop. "The trade being there" was decidable only AFTER the wick.
4. Adverse selection at refined limits: filled → −0.48R, never-filled → +0.56R (the market fills
   precisely the ones that keep going against you). Ex-post knowledge, not a rule.
5. No chart-visible feature separates the 16% from the 41% in advance: strength, freshness,
   confluence, nesting, daily anchors, direction stacks, liquidity pools, top-K ranking — each
   ≤+2pp, breakeven needs +6–14pp. (All holdout-tested.)

## PART 3 — the logical repair
"If the trade is there, we don't fail" assumes the trade IS there at find-time. Audited truth:
at find-time there is only a SETUP with a probability distribution (~48–51% direction, symmetric
size). "The trade" (the 32R run) comes into existence AFTER, and nothing in OHLCV pre-announces
it. Finding cannot fail less — it already finds everything the data shows. The failing lives
entirely in the part no finder can see: WHICH found setup the market chooses to pay.

## Standing verdicts (do not re-audit; all reports in runs/ + dev/plan/artifacts/)
finder accuracy ✅ · setup→outcome link ❌ at every TF (5m→weekly) · every entry/stop/trail/
selection/refinement variant ❌ · costs honest ✅ · the three doors (drift/index, order-flow data,
audited human discretion) remain the only unexplored positives.
