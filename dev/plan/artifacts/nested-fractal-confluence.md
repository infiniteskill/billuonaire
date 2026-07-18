# NESTED FRACTAL CONFLUENCE — daily zone > H1 OB/FVG > M5 signal (+ liquidity-pool nest)

**The bar to clear:** base win ~49% at 1:1 (decided-only hit%; net win%(k1.5 fixed_t1)=45.5% on all 300,153 signals); breakeven at adequate capital ~55%; every prior conditioning gave <=+2pp. The nest must deliver **>=+6pp holdout-stable** to matter.

Build (leak-free; for each signal only bars with end<=ts): H1 = session-anchored 5m aggregation, 15:15 stub merged into 14:15 bar (6 bars/session). H1 zones: OB = last opposite-color H1 candle within 5 bars before body>=1.5xATR14(H1) displacement, dies on H1 close beyond far edge; FVG = 3-candle gap >=0.3xATR14(H1), dies when a later H1 wick fully fills the gap. Daily zones: exact dailypoi_build rules (L1 parity with dailypoi_tags = 100%). Zone-in-zone: H1 zone midpoint inside matched daily zone +/-0.25xdailyATR; signal inside H1 zone +/-0.25xH1ATR, direction-consistent. Directions: close>SMA20 (daily bars strictly before session; closed H1 bars only; m5 = signal direction). Liquidity pools: unswept H1 2-2 fractal swings, equal-H/L clusters (<=0.15xATR_H1, level=extreme), PDH/PDL, prior-week H/L; sweeps/reclaims detected on closed 5m bars; L1_swept window = 6 H1 bars; pool proximity = 0.5xATR_H1 (H1 ATR used, documented choice).

## Funnel — daily-zone nest (pooled)

| level | n | win% (k1.5 t1) | d vs L0 | hit% | hit-edge | netR t1 | netR t3 |
|---|---|---|---|---|---|---|---|
| L0 any signal | 300,153 | 45.5% | +0.0pp | 50.0% | +9.9% | -0.2856 | -0.2992 |
| L1 in daily zone | 117,539 | 46.4% | +0.9pp | 50.9% | +10.5% | -0.2653 | -0.2774 |
| L2 L1+H1 zone nested in daily | 41,496 | 46.0% | +0.5pp | 50.2% | +11.3% | -0.2721 | -0.2971 |
| L3 L2+all dirs agree | 8,204 | 46.0% | +0.5pp | 50.3% | +12.1% | -0.2584 | -0.2990 |
| L3relaxed L2+(h1|daily dir) | 27,734 | 45.6% | +0.1pp | 49.6% | +11.4% | -0.2794 | -0.3037 |
| CTRL L2' H1 zone only | 91,898 | 45.3% | -0.2pp | 49.8% | +11.4% | -0.2912 | -0.3155 |
| CTRL L3' dirs only | 91,937 | 44.8% | -0.7pp | 49.4% | +10.2% | -0.2984 | -0.3299 |
| CTRL L1+dirs (no H1 zone) | 17,575 | 45.9% | +0.4pp | 50.5% | +11.9% | -0.2645 | -0.3004 |
| CTRL H1zone+dirs (no daily) | 30,378 | 44.4% | -1.0pp | 49.4% | +12.2% | -0.3025 | -0.3444 |

## Funnel — liquidity-pool nest + cross (pooled)

| level | n | win% (k1.5 t1) | d vs L0 | hit% | hit-edge | netR t1 | netR t3 |
|---|---|---|---|---|---|---|---|
| L1_liq_away (unswept pool, targets away) | 57,667 | 46.0% | +0.5pp | 50.4% | +11.0% | -0.2782 | -0.3074 |
| L1_liq_into (unswept pool, targets into) | 19,798 | 45.5% | +0.0pp | 48.6% | +5.5% | -0.2968 | -0.2984 |
| L1_swept (pool swept<=6 H1 bars, reclaim dir) | 153,417 | 46.0% | +0.5pp | 50.4% | +9.7% | -0.2696 | -0.2823 |
| L2_liq (L1_swept + H1 zone on pool) | 37,431 | 45.8% | +0.3pp | 50.3% | +10.3% | -0.2761 | -0.3075 |
| L3_liq (L2_liq + h1_dir agrees) | 10,273 | 45.6% | +0.1pp | 50.2% | +11.2% | -0.2724 | -0.2967 |
| X1 dailyL1 & L1_swept | 78,794 | 46.5% | +1.0pp | 51.0% | +10.5% | -0.2600 | -0.2740 |
| X2 dailyL2 & L1_swept | 28,369 | 46.0% | +0.5pp | 50.3% | +11.0% | -0.2690 | -0.3003 |
| X3 X2 & all dirs agree (full model) | 3,867 | 46.2% | +0.7pp | 50.8% | +12.7% | -0.2515 | -0.2786 |
| X4 dailyL2 & L2_liq | 22,304 | 45.7% | +0.2pp | 50.1% | +10.4% | -0.2768 | -0.3077 |
| X5 dailyL1 & liq_away | 31,715 | 45.9% | +0.4pp | 50.6% | +11.7% | -0.2777 | -0.3163 |
| X6 dailyL2 & liq_away | 13,970 | 46.9% | +1.4pp | 50.9% | +12.6% | -0.2544 | -0.2919 |

## Per-detector: L2 / L3 (daily nest)

| detector | n L2 | win L2 | n L3 | win L3 | d L3 vs det-L0 | netR t1 L3 |
|---|---|---|---|---|---|---|
| bpr | 1,154 | 45.9% | 184 | 51.6% | +5.9pp | -0.1021 |
| compression_fade | 14,877 | 46.1% | 2,524 | 46.6% | +1.1pp | -0.2565 |
| fvg_cb | 4,915 | 45.8% | 1,463 | 46.1% | +0.3pp | -0.2385 |
| inducement | 644 | 45.2% | 166 | 51.2% | +5.5pp | -0.1322 |
| mitigation | 6,758 | 46.9% | 1,430 | 46.5% | +0.8pp | -0.2358 |
| ob_lux | 12,494 | 45.6% | 2,319 | 44.3% | -0.9pp | -0.3014 |
| turtle_soup | 654 | 45.4% | 118 | 39.8% | -4.7pp | -0.4002 |

## Holdout cells (temporal half x crc32(symbol)%2) — win% at k1.5 fixed_t1

| cell | n L0 | win L0 | n L3 | win L3 | d | n L3rlx | win L3rlx | d | n X3 | win X3 | d |
|---|---|---|---|---|---|---|---|---|---|---|---|
| T0S0 | 79,370 | 46.1% | 2,179 | 43.2% | -2.9pp | 7,360 | 46.2% | +0.1pp | 1,005 | 43.1% | -3.0pp |
| T0S1 | 71,014 | 46.0% | 1,656 | 45.8% | -0.2pp | 5,716 | 45.6% | -0.4pp | 831 | 46.2% | +0.2pp |
| T1S0 | 79,040 | 45.0% | 2,169 | 49.3% | +4.3pp | 7,528 | 46.3% | +1.3pp | 978 | 49.0% | +4.0pp |
| T1S1 | 70,729 | 44.8% | 2,200 | 45.5% | +0.7pp | 7,130 | 44.1% | -0.7pp | 1,053 | 46.4% | +1.6pp |

## Money scan (all 28 cfgs x level x detector, n>=200)

Positive = mean net_R>0 overall; stable = also >0 in both temporal and both symbol halves.

**NO holdout-stable net-positive cell (n>=200) at any cfg.**

## Small-cell note (n<200, excluded from money scan)

bpr L3: n=184, win 51.6% (+5.9pp vs bpr L0 45.7%); half-splits 48.8/54.0 (T) and 49.0/54.7 (S)
— all four above baseline but netR t1 = -0.1021 (still loses money) and n is far too small to
call. inducement L3: n=166, win 51.2%; T-split 46.0/57.0 — the first temporal half shows ~0
edge, i.e. not stable. Both are noise-compatible; neither clears anything.

## VERDICT — against the +6pp bar

**The nest FAILS the bar. It saturates at the same <=+2pp as every prior conditioning.**

- L3 (full daily>H1>M5 recursion, all directions agreeing): n=8,204, win 46.0% vs L0 45.5%
  = **+0.5pp** (hit% basis: 50.3% vs 50.0% = +0.3pp). Required: >=+6pp. Delivered: ~one tenth.
- Holdout cells for L3: -2.9 / -0.2 / +4.3 / +0.7pp — the sign flips across cells; not stable
  at even +0.5pp, let alone +6pp.
- The controls show why: L1 alone = +0.9pp (the known daily-zone effect), H1-zone alone =
  -0.2pp, direction-agreement alone = -0.7pp. Nesting them does not compound — L2 (+0.5pp) and
  L3 (+0.5pp) sit BELOW plain L1. The recursion adds selection, not signal.
- Liquidity-pool anchors (amendment): same story. Unswept-pool-away +0.5pp, swept-pool-reclaim
  +0.5pp, zone-on-swept-pool (L2_liq) +0.3pp, +h1 direction (L3_liq) +0.1pp. Trading INTO the
  pool is flat (+0.0pp) with visibly degraded hit-edge (+5.5% vs +9.9%) — consistent with the
  prior finding that obvious pool touches are anti-signal.
- The full user model (X3: daily zone + nested H1 zone + recent liquidity grab + all directions)
  = n=3,867, **+0.7pp**, holdout -3.0..+4.0pp. The best cross of all (X6: daily-nested H1 zone
  sitting on an unswept pool) = **+1.4pp** — the single best number in the whole study, and
  still inside the <=+2pp saturation band.
- Money scan across all 28 cfgs x every level x every detector (n>=200): **zero net-positive
  cells, even before the stability requirement.** Best netR at the headline cfg is X3's -0.2515
  (L0: -0.2856). Nothing is tradeable.

Conclusion: multi-timeframe confluence at every tested permutation — proximity, nesting,
direction stacking, liquidity grabs, and their conjunction — reprices the SAME ~1-2pp of
information. The daily zone carries essentially all of it (+0.9pp); H1 nesting and direction
agreement are redundant conditioning on top. This closes the last untested permutation:
top-down recursion does NOT rescue the 45.5% -> 55% gap. The edge needed to make this system
net-positive will not come from confluence filters.
