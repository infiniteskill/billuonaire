# 35 — FEATURE ANATOMY: how the user DRAWS each feature → detector diffs (2026-07-22)
4 parallel vision-agents cataloged how the user hand-draws each SMC feature across all 27 trades
+ the schematic teaching images, then diffed against detector code. This is a FEATURE reference
(not trade analysis): per feature = the user's drawing rule + exact detector changes to match.

## THE ONE BIG CONCLUSION (theme across all features)
Our detectors were built on the RESEARCH/ICT definitions. The user's actual DRAWING differs in a
COHERENT, CONSISTENT way on every feature:
1. ZONE geometry = OUTER WICK box (for the STOP) + INNER BODY block (for the ENTRY). We do
   bodies-only, no inner block.
2. ENTRY = the CE / 50% MIDLINE of the inner block ("ENTRY IN MID"). We are edge-only.
3. SL = beyond the OUTER WICK / sweep spike. We use the body far edge (too tight, wrong place).
4. BIRTH GATE = only AFTER a liquidity sweep of an extreme + a BOS. We fire on ANY cluster/gap,
   mid-air included.
5. LIQUIDITY = a LINE on the wick extreme (+ a stop-band a notch beyond); SWEEP = wick-pierce-then-
   close-back lifecycle. We only emit proximity, from fractal furniture not extremes.
Re-aligning the detectors to the user's drawing = these five changes, centered on ob_taught (OB +
breaker/mitigation), fvg_n (FVG/iFVG/CE), propulsion2 (PB), liquidity (pools+sweep), extremes (anchor).

## SWING / EXTREMES
DRAWING: a CIRCLE/ellipse on the pivot, ONLY dominant two-sided extremes (big leg IN and OUT);
minor wiggles never marked. Master vs major by circle SIZE (biggest = "SWING EXTREME"), never color.
Circle encloses the wick-cluster BAND, not a point.
CODE (extremes.py): MATCHES — leg_in AND leg_out ≥ floor, wick-beyond-bodies band, deepest-wins.
DIFF: (a) add 5m/15m/30m timeframes (user marks 5m & 30m; default is 1h only). (b) master =
largest rank_atr (min(leg_in,leg_out)/ATR), NOT price max/min. (c) lower/expose leg-floor per TF
(6% too coarse for 5m spikes). swings.py = plain fractal furniture → do NOT feed liquidity from it.

## LIQUIDITY
DRAWING: a horizontal LINE on the wick extreme (old high/low). The SL is a SEPARATE line a notch
BEYOND the pool (above highs / below lows = where stops rest). Anchored to an EQUAL-highs/lows pool
(≥2 touches) OR a LONE dominant extreme swing (rails, single lows — t1/t8/t25). SWEEP = a single
wick pierces beyond the line then the candle CLOSES back inside (poke, not deep close-through).
Opposite pool labeled "BOS" (structure). No BSL/SSL/EQH vocab (user uses "liquidity"/"SL taken").
CODE (liquidity.py): MATCHES EQH/EQL ≥2-touch, band = member min-max, touches count.
DIFF: (1) source pools from EXT_H/EXT_L (taught extremes), NOT fractal SWING_H/L. (2) add LONE-
extreme path: promote each EXT master pivot to a liquidity level (touches≥1); add EXT_H/EXT_L to
proximity kinds (lone extremes currently generate nothing). (3) add a STOP-OFFSET outer band above
EQH / below EQL — that offset edge is the line a wick must exceed to be a sweep. (4) add SWEEP
LIFECYCLE: wick beyond outer edge + close back inside → pool flips to SWEPT (currently only
POOL_NEAR proximity, no sweep state).

## ORDER BLOCK + INTERNAL OB (biggest geometry mismatch)
DRAWING: OUTER box = WICK high→low of the whole MIXED-COLOR consolidation CLUSTER (3-8 candles) at
a SWEPT swing extreme (the box is the base/distribution, NOT an isolated opposite-color candle).
The liquidity-sweep spike is left OUTSIDE the far edge; SL just beyond that far wick. INNER box =
the BODY range (open→close) of the origin, with its own 50% MIDLINE = the ENTRY. "SL beyond outer
wick, ENTRY at inner body/mean-threshold." Born only at a swept-swing + BOS.
CODE (ob_taught.py): builds the zone from BODIES only (that is the user's INNER block) and OMITS
the outer wick box; isolates an opposite-color sub-run (user takes the whole cluster); enters at
proximal body edge (user enters at inner CE); SL = body edge (user = outer wick); fires on any
counter-pressure break (user requires sweep+BOS). ob_lux uses wicks for a single bar (closer to
outer geometry).
DIFF (high value): (a) record BOTH zones — outer = cluster wick hi/lo, inner = cluster body min/max;
entry = inner CE/edge, SL = outer far wick / tick beyond sweep. (b) cluster = whole consolidation
at the swept extreme, not opposite-color-only. (c) GATE birth on a preceding same-side sweep + BOS
(read extremes/liquidity/sweep from ctx.levels), not any cluster break. NOTE: this REVISES the
TUNE.md "bodies-only frozen" — user uses BOTH boxes (outer wick=stop, inner body=entry); and it
resolves the earlier edge>CE tension — user's CE-entry + wick-SL construction was NEVER measured.

## FVG + iFVG
DRAWING: bull = [c1.high → c3.low], bear = [c3.high → c1.low] (wick flanks; every middle CLOSES
beyond the near flank). Strict-3 OR multi-candle BURST (2-6) OR a wide "liquidity void" band bounded
by the outer wicks of the whole displacement (continuous gaps = ONE zone, extended right). A 50%
MIDLINE (CE / "equilibrium") is drawn and entry is "ENTRY IN MID" (CE) or near-edge touch. Born
after a sweep/swing/BOS ("PFG after tapping S/R"), NEVER mid-air; usually nested/stacked with OB/
mitigation/breaker/propulsion. iFVG = same box, opposite dir, after a decisive close-through → entry
on retest.
CODE (fvg_n.py): MATCHES wick edges, N-burst (mmax=6), continuous-gap dedup (ONE zone), iFVG flip,
weeks-long live, continuation entry.
DIFF: (a) add CE/50% entry+hold (edge-only now; port fvg_cb._cehold) — this is the user's CORE
action. (b) add born-after-sweep/BOS structure gate (fires mid-air now). (c) wide-void case: keep
the WIDEST/union fragment, not the smallest (dedup currently keeps minimal); raise mmax for voids.
(d) kill 0.5×ATR is stricter than user's plain decisive close-through for the flip.
fvg_cb.py: has CE-hold (good) but strict-3 only + no iFVG flip → add the flip; keep as CE specialist.

## BREAKER / MITIGATION / PROPULSION
BREAKER (user): a prior swing high (resting liquidity) is SWEPT (higher-high taken), THEN structure
breaks the other way; the failed OB FLIPS. Box = BODIES of the failed-OB cluster, inner OB/50% line
= entry, SL beyond the WICK. (t1 = canonical, short.)
MITIGATION (user): next high is a LOWER HIGH — "failure to swing / No Break", prior high NOT swept;
block flips same way. Box = BODIES of the lower-high cluster, often with FVG inside, ENTRY IN MID.
(t4/t15 canonical, short.) => BRK and MIT are the SAME flipped box + SAME direction; the ONLY
discriminator is WAS THE PRIOR EXTREME SWEPT (BRK) or not (MIT).
PROPULSION (user): a candle taps a live PARENT OB and propels away; child zone = tap-candle BODY,
sitting IN FRONT of the parent (above for bull, below for bear), parent-linked, often FVG-paired
(t27 "ob fvg entry"; t25 "ob+propulsion" combined launch).
CODE DIFFS:
- breaker.py (shipped): fires on ANY inverted retest, NO sweep test → cannot separate BRK/MIT →
  defer to breaker_msb/ob_taught.
- breaker_msb.py: sweep gate h0>h1 / l0<l1 is the FAITHFUL swept test ✓; but box = single origin
  candle WICKS + wrong origin color (down-candle) → won't co-locate with the user's bodies-cluster.
- ob_taught.py flip: swept test (ext ≷ pex) is directionally FAITHFUL (t1 BRK, t4/t15 MIT verified).
  REFINE: pex should be the RESTING-LIQUIDITY high the user marks (extreme/equal-highs), not the
  latest-born opposite pivot; add wick-extreme SL. => ob_taught = the home for user-parity BRK/MIT.
- mitigation.py: single-candle (user is multi-candle cluster) + no sweep gate → use ob_taught MIT.
- propulsion_block.py: zone dips INTO parent (straddles, wrong side), full-range, orphan-capable.
- propulsion2.py: BEST — body zone, IN FRONT of parent, parent-linked, dies with parent ✓. ADD FVG
  linkage (t27 "ob fvg entry" = propulsion coincides with an FVG in the leg); confirm t25 combined-
  launch still fires.

## Build homes (where each feature's user-parity lives)
- extremes.py = the anchor (add TFs, master-by-leg). liquidity.py = pools + LONE-extreme + stop-band
  + SWEEP lifecycle, sourced from EXT. ob_taught.py = OB (outer-wick+inner-body, sweep+BOS gate) AND
  BRK/MIT (swept-test flip, better pex, wick-SL). fvg_n.py = FVG/iFVG + CE + structure gate + void-
  union. propulsion2.py = PB (add FVG linkage). fvg_cb.py = strict-3 CE specialist (add iFVG flip).
- The decision tree (33) consumes these; entry=inner-CE, SL=outer-wick, born-after-sweep+BOS
  everywhere. These diffs are the concrete "make detectors draw features the way the user draws
  them" worklist for the build.
