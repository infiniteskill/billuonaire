# Reference Pine Scripts vs Our Detectors — Comparison & Brainstorm (2026-07-17)

Source: `dev/pinescripts.txt` = 4 canonical TradingView indicators —
LuxAlgo **Smart Money Concepts** (the reference thousands use), AlgoAlpha Breakout
Channels, LuxAlgo **Liquidity Swings** (×2). These are battle-tested definitions.
Compared algorithm-by-algorithm against `app/trader/detectors/*`.

**Headline:** the reference implementations independently point to the SAME fixes our
own 64k-evidence study demanded. Theory + measurement agree — high confidence to act.

## Algorithm divergences (ours vs LuxAlgo canonical)

| Concept | LuxAlgo reference | Ours | Study said | Verdict |
|---|---|---|---|---|
| **Order Block anchor** | The EXTREME candle of the impulse leg (min-low for bull), **volatility-adjusted: on bars with range ≥2×ATR, SWAP high/low** so spike bars can't anchor an OB. No quality score. | Last opposite candle before ≥1.5×ATR displacement; quality = disp+body+body_pct+hunt bonus | Our quality formula INVERTED (small subtle OBs win, +0.15 hunt bonus falsified) | **LuxAlgo explains our data**: they structurally exclude volatile spike bars → only "small subtle" OBs remain. Adopt vol-adjusted anchor; drop our (broken) quality score. |
| **FVG** | 3-bar gap AND displacement bar must **CLOSE beyond** the gap origin AND body-delta% > adaptive threshold (cum-mean-abs-delta ×2), not a fixed gap size | 3-bar gap ≥ `min_gap_atr`×ATR; no close-beyond requirement | FVG = our BEST detector (+8.8–14%) | Tighten: add close-beyond-displacement + adaptive body-% threshold. Our best signal, make it cleaner. |
| **EQH/EQL tolerance** | `abs(level − new) < 0.1×ATR` (ATR-relative), confirmed over 3 bars | 0.1% price-relative (`0.001`) | (not isolated) | ATR-relative is the right basis; ours over-groups on high-priced stocks (0.1% of 1300 = 1.3pt vs 0.1×ATR ≈ 0.2pt). Switch to ATR-relative. |
| **Liquidity pool strength** | **Liquidity Swings**: accumulate VOLUME traded in the zone since the pivot (count + volume filter) — a level's strength = resting volume | touches + recency decay | Our pool-strength predicts NOTHING (corr ~0) | Replace with accumulated-volume-in-zone (needs intrabar/M1 volume — we have it). Test if it beats zero. |
| **Structure BOS/CHoCH** | `crossover(close, swing pivot)` at bar 0; trend-relative CHoCH/BOS | Same (close beyond swing) | BOS/CHoCH ANTI-signal at bar 0 (−22%) | **Corroborated**: LuxAlgo fires at the same bar-0 close — the anti-signal is inherent to the SMC definition, not our bug. Confirms demoting structure to context-only. |
| **Structure scales** | TWO: internal (5-bar legs) + swing (50-bar legs); internal break = continuation confidence, swing break = real structure; internal breaks coinciding with swing filtered | swings strength-3 on M5+M15 (conflated) | — | Consider explicit internal(fast)/swing(slow) split; only swing breaks are structural, internal are confluence. |
| **Pivot/leg** | Asymmetric running-leg: new leg-high when `high[N] > highest(N)` (breaks prior N) | Symmetric N-each-side strict pivot | — | Ours is stricter/cleaner for confirmation; keep, but note LuxAlgo's is faster (fewer confirm bars) — matters for entry latency. |

## Concepts LuxAlgo has that WE LACK (candidate adds)

1. **Premium/Discount zones (BIGGEST).** From trailing swing range: Premium = top 5%,
   Discount = bottom 5%, Equilibrium = mid. Rule: only BUY in discount, only SELL in
   premium. **This is range-based "fade extension" — exactly what our study found carries
   ALL the edge** (against-move/extended entries +9–14%, with-move entries poison). We
   have Fib-OTE but no live premium/discount GATE. Adding it as a confluence gate
   (reject longs in premium half, shorts in discount half) formalizes the one law the
   data proved. Highest-value add.
2. **Strong/Weak High/Low.** A swing high is "Strong" (will hold, = wall) if trend is
   down, "Weak" (will break, = target/draw) if trend is up. We treat all pools alike.
   Could sharpen target selection (draw toward weak, fade at strong) and sweep direction.
3. **Volatility-adjusted price series** (the parsedHigh/parsedLow swap). A general
   primitive — spike bars are noise for level-anchoring. Useful beyond OB.
4. **AlgoAlpha Breakout Channels** — momentum breakout continuation. Against our
   reversal thesis (with-move = poison in our data); note but do NOT adopt as entry.

## The convergence (why this matters)
Two independent sources — the canonical community reference AND our own out-of-sample
measurement — agree on four things:
- Fade extension, don't chase (LuxAlgo premium/discount ↔ study against-move edge)
- Don't anchor on spike bars (LuxAlgo vol-swap ↔ study "small OBs win, body terms inverted")
- Structure break ≠ entry (LuxAlgo bar-0 crossover ↔ study −22% anti-signal)
- Volume defines liquidity (LuxAlgo Liquidity Swings ↔ study "touch-count useless")

## Proposed additions to the (pending) detector-retune wave
Fold into the integrator wave that still needs to run (it died mid-work, applied nothing):
- **A. Premium/Discount gate** (new, from swing-range trailing top/bottom) — reject
  counter-zone entries; likely the single biggest expectancy lever.
- **B. Vol-adjusted OB anchor** — replace our broken quality formula with LuxAlgo's
  spike-excluding extreme-candle anchor (already demanded by study finding F).
- **C. FVG close-beyond + adaptive body-% threshold** — tighten our best detector.
- **D. EQH/EQL → ATR-relative tolerance.**
- **E. Volume-in-zone liquidity strength** — replace touch-count (study: it's useless).
- **F. Strong/Weak High/Low tagging** — sharpen targets + sweep direction (later).

All still need out-of-sample validation on a FRESH month (current data is partly
in-sample for retunes). These are hypotheses backed by both theory and one month —
not yet proven on holdout.
