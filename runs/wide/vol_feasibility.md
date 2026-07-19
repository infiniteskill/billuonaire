# Volatility-Expansion Feasibility Gate — compression → straddle

**Question:** does a compression candle predict a *big-enough* volatility
expansion to make a non-directional ATM straddle viable? This is the free
gate before spending money on Kite, and the last surviving hypothesis after
both directional theses (fade + momentum) were falsified on symmetric MFE/MAE.

**Method (leak-free, free — no Kite):** 138 NSE stocks (NIFTY excluded as an
index), 20 sessions 2026-06-19..2026-07-17, M1→M5. Compression = detector
rule `is_compress(c)`: body ≤ 0.35·range AND both wicks ≥ 0.2·range. ATR is
`trader.tools.study.atr_series` (trailing SMA-14 of TR, bars ≤ i only). For
each compression bar i we measure forward vol over the next K ∈ {3, 6, 12} M5
bars (≈15/30/60 min), EOD-truncated by requiring i+K to be in-session. Every
metric is in ATR[i] units. **Baseline** = the mean metric of NON-compression
valid bars in the SAME (symbol, session, 30-min bucket) cell — composition-
matched, i.e. the expected value of a `study.baseline`-style seeded same-
bucket sampler, controlling for symbol, day and time-of-day.

Compression is **not rare**: 34,960 / 170,098 M5 bars = **20.6%** qualify.
This is essentially "small-body bar," not a selective coil — already a warning.

---

## VERDICT — NO-GO (do not buy Kite for this thesis)

1. **Is compression→expansion real and holdout-stable? Yes in sign, but the
   magnitude is economically negligible.** The forward-vol LIFT over a random
   same-bucket bar is positive on *all four* holdout partitions (temporal 1st/
   2nd half + cross-sectional crc32%2), but tiny and *decaying with horizon*:

   | metric (ATR units) | K=3 lift / ratio | K=6 | K=12 |
   |---|---|---|---|
   | abs_move (held straddle capture) | +0.063 / ×1.08 | +0.050 / ×1.04 | +0.037 / ×1.02 |
   | max_leg (managed single-exit)    | +0.079 / ×1.06 | +0.077 / ×1.04 | +0.060 / ×1.02 |
   | max_range (both-legs upper bound)| +0.074 / ×1.04 | +0.076 / ×1.03 | +0.063 / ×1.02 |

   A compression bar moves only **2–8% more** than a random bar in the same
   session/time-bucket, and the edge *shrinks* as the hold lengthens. This is
   precisely the "weak / near-symmetric expansion" the brief flagged as a
   clear NO-GO. Tightening the coil does **not** rescue it: at body≤0.10,
   wicks≥0.35 the abs_move lift *falls* to +0.029 (K=6); strength terciles are
   flat (+0.037…+0.052). Higher coil quality buys nothing — consistent with
   tighter coils being lower-vol regimes that expand less in absolute ATR.

2. **The modeled straddle's viability comes from baseline intraday vol, NOT
   from the compression signal.** Held-to-K breakeven premium
   p* = E[abs_move] − c (payoff = metric − p − c is linear in p):

   | version | K | p* comp (c=.1) | p* baseline (c=.1) | **p\* the SIGNAL adds** |
   |---|---|---|---|---|
   | held (abs_move)    | 3 | 0.77 | 0.70 | **+0.06** |
   |                    | 6 | 1.14 | 1.09 | **+0.05** |
   |                    | 12| 1.64 | 1.61 | **+0.04** |
   | managed-leg        | 6 | 1.90 | 1.83 | **+0.08** |

   The absolute p* looks generous (0.77–1.64 ATR), but a **random bar reaches
   ~95% of it**. Compression as a *gate* contributes ~0.04–0.08 ATR of breakeven
   room — trivial next to a real option's bid/ask + theta. The straddle either
   works on the whole universe (a general realized-vs-implied-vol bet, which is
   NOT a compression thesis) or it doesn't; the signal doesn't move the needle.

3. **Step 2 is modeled, not real prices — and the omitted costs point the
   wrong way.** The p×ATR premium model ignores the dominant real drags on an
   intraday straddle buyer: NSE weekly ATM premium + theta bleed over a 15–60
   min hold, a wider two-legged spread, and the well-documented positive
   variance-risk-premium (implied > realized) that structurally favors the
   *seller*. Realized medians are also well below the tail-inflated means
   (K=3 median abs_move 0.61 vs mean 0.87) — the modeled payoff leans on rare
   tails while premium is paid every trade. Plausible real premiums likely
   exceed even the baseline p*, and the signal's +0.04–0.08 ATR does not close
   that gap.

**Recommendation: NO-GO.** Do not buy Kite to validate the compression→straddle
thesis on real option chains. The compression→expansion effect is statistically
real and holdout-stable but too small (×1.02–1.08, shrinking with horizon, and
non-improving with coil quality) to matter economically, and the modeled
straddle edge is a property of baseline volatility rather than of the signal.
Honest caveat: Step 2 uses a modeled premium, not real NSE option prices — but
Step 1 (which needs no options data) already kills it: an expansion this weak
cannot support a signal-gated straddle regardless of the exact premium.

---

## STEP 1 — Compression vs baseline forward vol (composition-matched)

`abs_move` = |close[i+K] − close[i]| / ATR[i] (what a held straddle captures);
`max_range` = (max high − min low over i+1..i+K) / ATR[i] (both-legs upper
bound); `max_leg` = max(favorable, adverse excursion) / ATR[i] (best single
straddle exit). Lift = comp_mean − base_mean; Ratio = comp_mean / base_mean.

### abs_move
| K | n | comp mean | comp med | base mean | base med | LIFT | ratio |
|---|---|---|---|---|---|---|---|
| 3 | 33100 | 0.866 | 0.610 | 0.803 | 0.606 | +0.063 | 1.08 |
| 6 | 31620 | 1.242 | 0.881 | 1.192 | 0.870 | +0.050 | 1.04 |
| 12| 28535 | 1.741 | 1.235 | 1.705 | 1.228 | +0.037 | 1.02 |

### max_range
| K | n | comp mean | comp med | base mean | base med | LIFT | ratio |
|---|---|---|---|---|---|---|---|
| 3 | 33100 | 1.739 | 1.487 | 1.664 | 1.477 | +0.074 | 1.04 |
| 6 | 31620 | 2.492 | 2.150 | 2.416 | 2.108 | +0.076 | 1.03 |
| 12| 28535 | 3.491 | 3.008 | 3.428 | 2.949 | +0.063 | 1.02 |

### max_leg
| K | n | comp mean | comp med | base mean | base med | LIFT | ratio |
|---|---|---|---|---|---|---|---|
| 3 | 33100 | 1.403 | 1.143 | 1.324 | 1.137 | +0.079 | 1.06 |
| 6 | 31620 | 2.003 | 1.642 | 1.926 | 1.609 | +0.077 | 1.04 |
| 12| 28535 | 2.797 | 2.297 | 2.737 | 2.254 | +0.060 | 1.02 |

## STEP 1b — Holdout stability of the LIFT

Lift computed independently on each partition. Sign-stable = lift > 0 on ALL
of {temporal 1st half, 2nd half, crc32(symbol)%2==0, ==1}.

### abs_move — LIFT by partition
| K | FULL | T-1st | T-2nd | X-crc0 | X-crc1 | stable? |
|---|---|---|---|---|---|---|
| 3 | +0.063 | +0.072 | +0.056 | +0.056 | +0.070 | YES |
| 6 | +0.050 | +0.050 | +0.050 | +0.052 | +0.048 | YES |
| 12| +0.037 | +0.050 | +0.027 | +0.031 | +0.043 | YES |

### max_leg — LIFT by partition
| K | FULL | T-1st | T-2nd | X-crc0 | X-crc1 | stable? |
|---|---|---|---|---|---|---|
| 3 | +0.079 | +0.088 | +0.073 | +0.074 | +0.085 | YES |
| 6 | +0.077 | +0.083 | +0.074 | +0.071 | +0.084 | YES |
| 12| +0.060 | +0.073 | +0.050 | +0.049 | +0.072 | YES |

Sign-stable everywhere, but every cell is ≤ +0.09 ATR. Stable ≠ tradeable.

### Coil-quality sensitivity (K=6, does tighter compression help? No)
| definition | n | abs_move lift | max_leg lift |
|---|---|---|---|
| baseline  body≤.35 wick≥.20 | 31620 | +0.050 | +0.077 |
| tight     body≤.25 wick≥.25 | 19947 | +0.046 | +0.070 |
| tighter   body≤.15 wick≥.30 | 10723 | +0.045 | +0.068 |
| v-tight   body≤.10 wick≥.35 |  5897 | +0.029 | +0.058 |

Strength terciles within baseline compression: weak +0.044 / mid +0.037 /
strong +0.052 (abs_move). No monotone gain from coil quality — the edge is
flat-to-declining, so there is no "clean subset" to salvage.

## STEP 2 — Modeled ATM-straddle breakeven premium p*

MODELED, not real option prices. Long ATM straddle, premium = p·ATR (p folds
in implied-vol/theta over the hold), extra options cost = c·ATR (~2× equity
round-trip), c ∈ {0.1, 0.2}. Held-to-K P&L per trade (ATR units) = metric − p
− c; E[] over all compression signals (mean); breakeven p* = E[metric] − c.

| version | K | E[metric] comp | E[metric] base | p*(c=.1) comp | p*(c=.2) comp | p*(c=.1) base | p* the signal adds |
|---|---|---|---|---|---|---|---|
| held (abs_move)     | 3 | 0.866 | 0.803 | 0.766 | 0.666 | 0.703 | +0.063 |
|                     | 6 | 1.242 | 1.192 | 1.142 | 1.042 | 1.092 | +0.050 |
|                     | 12| 1.741 | 1.705 | 1.641 | 1.541 | 1.605 | +0.037 |
| managed-leg (max_leg)   | 3 | 1.403 | 1.324 | 1.303 | 1.203 | 1.224 | +0.079 |
|                     | 6 | 2.003 | 1.926 | 1.903 | 1.803 | 1.826 | +0.077 |
|                     | 12| 2.797 | 2.737 | 2.697 | 2.597 | 2.637 | +0.060 |
| managed-range (max_range, optimistic upper bound) | 6 | 2.492 | 2.416 | 2.392 | 2.292 | 2.316 | +0.076 |

Note: `held` uses abs_move (correct held-to-expiry long-straddle P&L, floored
at −p−c since abs_move ≥ 0). `managed-leg` uses max_leg = the best single exit
of ONE straddle (theoretically correct active exit). `managed-range` uses the
brief's max_range, which credits BOTH legs — physically unreachable by a single
straddle, kept only as an absolute optimistic ceiling.

### Held-to-K E[payoff] = E[abs_move] − p − c (c=0.1), compression signals
| K | p=0.4 | p=0.6 | p=0.8 | p=1.0 | p=1.2 |
|---|---|---|---|---|---|
| 3 | +0.366 | +0.166 | −0.034 | −0.234 | −0.434 |
| 6 | +0.742 | +0.542 | +0.342 | +0.142 | −0.058 |
| 12| +1.241 | +1.041 | +0.841 | +0.641 | +0.441 |

These E[payoff] cells are positive across most of the premium band — but the
baseline (random-bar) table is nearly identical (p* differs by only +0.04…+0.08
ATR). So the positivity is a statement about intraday realized vol, not about
compression. The signal-specific edge is negligible → NO-GO stands.
