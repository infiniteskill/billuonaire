# FACTS — zone-level discrimination, 138 symbols

Universe: first retest per zone, detectors fvg_cb/ob_lux/mitigation, 80636 zones over 57 sessions (1415 zones/day pooled). Uniform sim: next-bar-open entry, 1.5×ATR stop, 1R target, stop-first, EOD 15:10, 0.06% cost.
Base: hit 46.1% | netR -0.187 | MFE 2.77 MAE 2.84. NB: the assumed +6pp (52%) breakeven bar is optimistic — measured breakeven at this geometry is ~59% hit (see Verdict).

## Fact table (zone level, first retest; lift vs 46.1% / -0.186R base)

| fact | n kept | shrink% | n/day | hit% | lift pp | netR | liftR | 4-way stable | cells (hit-lift pp) |
|---|---|---|---|---|---|---|---|---|---|
| nextday+ retest (known ref) | 22738 | 71.8 | 399 | 48.4 | +2.4 | -0.156 | +0.032 | YES | T1:+2.9 T2:+1.9 C0:+2.6 C1:+2.1 |
| gap-origin AND nextday+ retest | 5118 | 93.7 | 90 | 47.9 | +1.8 | -0.165 | +0.022 | YES | T1:+2.2 T2:+1.6 C0:+1.5 C1:+2.2 |
| gap: birth = 09:15 open bar | 4191 | 94.8 | 74 | 47.3 | +1.2 | -0.162 | +0.025 | YES | T1:+1.4 T2:+1.1 C0:+1.3 C1:+1.2 |
| sweep-born aligned (soup direction) | 3141 | 96.1 | 55 | 46.7 | +0.7 | -0.177 | +0.010 | no | T1:+0.4 T2:+0.9 C0:+2.2 C1:-1.0 |
| H1 nested (inside live same-dir H1 zone) | 39283 | 51.3 | 689 | 46.5 | +0.4 | -0.185 | +0.003 | YES | T1:+0.3 T2:+0.6 C0:+0.2 C1:+0.7 |
| gap-origin (open-bar OR gap-overlap) | 22769 | 71.8 | 399 | 46.5 | +0.4 | -0.188 | -0.001 | YES | T1:+0.3 T2:+0.5 C0:+0.6 C1:+0.2 |
| sweep-born (EQ-pool sweep <=3 bars before) | 5220 | 93.5 | 92 | 46.4 | +0.4 | -0.177 | +0.011 | no | T1:+0.3 T2:+0.4 C0:+1.5 C1:-0.9 |
| gap: band overlaps overnight gap >0.3ATR | 22108 | 72.6 | 388 | 46.4 | +0.4 | -0.189 | -0.002 | YES | T1:+0.3 T2:+0.5 C0:+0.5 C1:+0.2 |
| H1 nested any-dir | 54097 | 32.9 | 949 | 46.2 | +0.1 | -0.187 | +0.000 | no | T1:+0.1 T2:+0.2 C0:-0.1 C1:+0.4 |
| impulse <1 ATR (weak birth) | 14740 | 81.7 | 259 | 46.2 | +0.1 | -0.206 | -0.018 | no | T1:+0.1 T2:+0.1 C0:+0.2 C1:-0.0 |
| impulse >=3 ATR | 11819 | 85.3 | 207 | 46.0 | -0.0 | -0.170 | +0.018 | no | T1:+1.2 T2:-1.1 C0:-0.1 C1:+0.0 |
| impulse >=2 ATR | 27780 | 65.5 | 487 | 45.7 | -0.3 | -0.178 | +0.010 | no | T1:+0.3 T2:-0.8 C0:-0.1 C1:-0.6 |
| H1 anchor (long-run H1 swing w/in 1 ATR5) | 35115 | 56.5 | 616 | 45.6 | -0.4 | -0.190 | -0.003 | YES | T1:-0.5 T2:-0.3 C0:-0.6 C1:-0.3 |

## 1. Gap-origin (priority)

- **gap-origin**: n=22769 (28.2% share), hit 46.5% (+0.4pp), netR -0.188, MFE 2.84 MAE 2.92. Revisit delay: same-day q25/med/q75 = 20/30/60 min; buckets % <30m=36.6 30-60m=19.8 1-4h=19.3 >4h=1.8 nextday+=22.5
- **intraday-origin**: n=57867 (71.8% share), hit 45.9% (-0.2pp), netR -0.187, MFE 2.75 MAE 2.81. Revisit delay: same-day q25/med/q75 = 20/35/65 min; buckets % <30m=27.7 30-60m=21.8 1-4h=18.8 >4h=1.2 nextday+=30.4

Cross gap-origin × retest bucket (hit% / netR / n):

| bucket | gap-origin | intraday-origin |
|---|---|---|
| <30m | 47.2% / -0.165 / 8336 | 44.7% / -0.197 / 16049 |
| 30-60m | 45.9% / -0.205 / 4514 | 44.7% / -0.202 / 12634 |
| 1-4h | 44.4% / -0.242 / 4394 | 45.1% / -0.208 / 10882 |
| >4h | 38.9% / -0.225 / 407 | 30.9% / -0.297 / 682 |
| nextday+ | 47.9% / -0.165 / 5118 | 48.6% / -0.153 / 17620 |

**Hand-picked class (gap-origin AND next-day+ retest)**: n=5118 (6.3% of pile, 90/day across 138), hit 47.9% (+1.8pp), netR -0.165, MFE 3.09 MAE 3.23.
4-way holdout hit-lift: T1: +2.2pp (n=2287)  T2: +1.6pp (n=2831)  C0: +1.5pp (n=2753)  C1: +2.2pp (n=2365) → stable=True
BUT: plain nextday+ is 48.4% — adding gap-origin on top of nextday+ REMOVES 0.5pp (intraday-origin & nextday+ = 48.6%). Gap-origin does not add there.

**Where gap-origin actually discriminates: FAST retests.** The <30m pile (30% of zones) splits:
- gap-origin & <30m: n=8336, hit 47.2% (+1.2pp), netR -0.165, stable=True [T1:+1.1 T2:+1.3 C0:+0.7 C1:+1.8]
- intraday & <30m: n=16049, hit 44.7% (-1.3pp), netR -0.197, stable=True [T1:-2.0 T2:-0.6 C0:-1.2 C1:-1.4]
So the earlier "<30m is NOT noise" refines to: fast retests are fine only for gap-origin zones; intraday-origin fast retests are a stable −1.3pp drag.

Per-detector, gap-origin AND nextday+:
- fvg_cb: n=812, hit 46.3% (det-base 46.2, +0.1pp), netR -0.180
- mitigation: n=2720, hit 48.6% (det-base 45.8, +2.9pp), netR -0.150
- ob_lux: n=1586, hit 47.4% (det-base 46.5, +0.8pp), netR -0.185

## 2. Birth impulse (displacement, ATR units)

| impulse | n | share% | hit% | lift | netR |
|---|---|---|---|---|---|
| <1 | 14783 | 18.3 | 46.2 | +0.1 | -0.206 |
| 1-2 | 38107 | 47.3 | 46.2 | +0.2 | -0.188 |
| 2-3 | 15932 | 19.8 | 45.6 | -0.5 | -0.183 |
| >=3 | 11814 | 14.7 | 46.0 | -0.0 | -0.170 |
- fvg_cb: <1: 41.5%/-0.187 (n=580)  1-2: 46.6%/-0.146 (n=4983)  2-3: 46.0%/-0.171 (n=4700)  >=3: 46.5%/-0.160 (n=4962)
- mitigation: <1: 44.9%/-0.245 (n=711)  1-2: 46.0%/-0.198 (n=27410)  2-3: 45.1%/-0.191 (n=9284)  >=3: 45.6%/-0.178 (n=5550)
- ob_lux: <1: 46.4%/-0.204 (n=13492)  1-2: 46.8%/-0.176 (n=5714)  2-3: 46.6%/-0.173 (n=1948)  >=3: 46.3%/-0.172 (n=1302)

## 3. HTF (H1) anchor / nesting

- h1_anchor: share 43.5%, hit 45.6% (-0.4pp), netR -0.190, stable=True [T1:-0.5 T2:-0.3 C0:-0.6 C1:-0.3]
- h1_nested: share 48.7%, hit 46.5% (+0.4pp), netR -0.185, stable=True [T1:+0.3 T2:+0.6 C0:+0.2 C1:+0.7]
- h1_nested_any: share 67.1%, hit 46.2% (+0.1pp), netR -0.187, stable=False [T1:+0.1 T2:+0.2 C0:-0.1 C1:+0.4]

## 4. Revisit index (touch 1 vs 2 vs 3+)

| touch | n | share% | hit% | netR |
|---|---|---|---|---|
| 1st | 80636 | 53.8 | 46.1 | -0.187 |
| 2nd | 22394 | 14.9 | 47.0 | -0.185 |
| 3rd+ | 46842 | 31.3 | 45.9 | -0.231 |
1st-touch minus later-touch hit, 4-way: T1: -0.4  T2: -0.0  C0: -0.2  C1: -0.2

## 5. iFVG (invalidated FVG, trade at re-retest of the band)

Universe: all reconstructed FVG births that got invalidated (close through far edge) then re-retested: n=111617 events, 103155 tradeable (1810/day).
- INVERTED side: hit 46.3%, netR -0.186
- ORIGINAL side: hit 46.4%, netR -0.182
- inv-minus-orig hit, 4-way: T1: -0.3  T2: +0.0  C0: +0.0  C1: -0.3

| inversion latency | n | inv hit% | inv netR | orig hit% |
|---|---|---|---|---|
| <30m | 74503 | 46.2 | -0.191 | 46.4 |
| 30-60m | 6435 | 45.3 | -0.176 | 45.5 |
| 1-4h | 6618 | 44.2 | -0.223 | 45.6 |
| >4h | 815 | 36.4 | -0.227 | 36.1 |
| nextday+ | 14784 | 48.7 | -0.145 | 47.8 |

- big-impulse invalidation (close-through >=1 ATR)=False: n=84572, inv hit 46.3%, inv netR -0.190, orig hit 46.4%
- big-impulse invalidation (close-through >=1 ATR)=True: n=18583, inv hit 46.0%, inv netR -0.169, orig hit 46.4%

## 6. Sweep-born

- sweep-born any: n=5220 (6.5%), hit 46.4% (+0.4pp), netR -0.177, stable=False [T1:+0.3 T2:+0.4 C0:+1.5 C1:-0.9]
- sweep-born aligned: n=3141 (3.9%), hit 46.7% (+0.7pp), netR -0.177, stable=False [T1:+0.4 T2:+0.9 C0:+2.2 C1:-1.0]
- sweep-born anti-aligned: n=2079 (2.6%), hit 46.0% (-0.0pp), netR -0.176, stable=False [T1:+0.2 T2:-0.3 C0:+0.5 C1:-0.7]

## 7. Best stack (greedy over stable facts)

Greedy trace (candidate adds, pooled hit%, 4-way stable):
- nextday+ & gap_origin: n=5118, hit 47.9%, stable=True
- nextday+ & gap_open_bar: n=432, hit 42.3%, stable=True
- nextday+ & impulse>=2: n=11397, hit 48.2%, stable=True
- nextday+ & impulse>=1: n=19420, hit 48.4%, stable=True
- nextday+ & h1_anchor: n=11272, hit 48.0%, stable=True
- nextday+ & h1_nested: n=14057, hit 48.8%, stable=True
- nextday+ & sweep_aligned: n=936, hit 50.5%, stable=True
- nextday+ & sweep_aligned & impulse>=2: n=454, hit 50.1%, stable=True
- nextday+ & sweep_aligned & impulse>=1: n=761, hit 50.8%, stable=True
- nextday+ & sweep_aligned & h1_anchor: n=464, hit 51.2%, stable=True
- nextday+ & sweep_aligned & h1_nested: n=557, hit 52.1%, stable=True
- nextday+ & sweep_aligned & h1_nested & impulse>=1: n=450, hit 51.9%, stable=True

Ladder (each rung 4-way same-sign in BOTH hit-lift and netR-lift):

| stack | n | shrink% | n/day | hit% | lift | netR | 4-way hit-lift |
|---|---|---|---|---|---|---|---|
| nextday+ | 22738 | 71.8 | 398.9 | 48.4 | +2.4 | -0.156 | T1:+2.9 T2:+1.9 C0:+2.6 C1:+2.1 |
| nextday+ & h1_nested | 14057 | 82.6 | 246.6 | 48.8 | +2.7 | -0.147 | T1:+3.1 T2:+2.4 C0:+2.2 C1:+3.3 |
| nextday+ & sweep_aligned | 936 | 98.8 | 16.4 | 50.5 | +4.5 | -0.126 | T1:+4.6 T2:+4.4 C0:+5.8 C1:+3.1 |
| nextday+ & sweep_aligned & h1_nested | 557 | 99.3 | 9.8 | 52.1 | +6.1 | -0.102 | T1:+5.7 T2:+6.4 C0:+7.6 C1:+4.3 |

**BEST STACK = nextday+ & sweep_aligned & h1_nested**
n=557 of 80636 (99.3% count-shrink), 9.8/session across 138 symbols (0.07 per symbol-day).
hit 52.1% (+6.1pp vs base), netR -0.102 (+0.086R), MFE 3.07 MAE 3.18.
4-way holdout hit-lift: T1: +5.7pp (n=257)  T2: +6.4pp (n=300)  C0: +7.6pp (n=298)  C1: +4.3pp (n=259) → stable=True
Concentration: 56/57 sessions, max 19 in one session; top symbol 12 of 557; direction {1: 302, -1: 255}; detector {'ob_lux': 269, 'mitigation': 231, 'fvg_cb': 57}.
Binomial z vs base = 2.86 (p≈0.004 pre-selection; ~19 stack combos examined → treat the last rung as suggestive, the ladder as the fact).
Caveat: sweep_aligned standalone is NOT 4-way stable (C1 negative); its stability appears only inside nextday+.

## 8. Verdict

- Round-trip cost at this geometry is ~0.19R (0.06% on notional, R=1.5×ATR5). Measured netR-vs-hit slope ≈ 0.014R/pp → **measured breakeven ≈ 59% hit**, not the +6pp (52%) bar. Even the best stack (52.1%, netR −0.10) is ~7pp short of water at 1R targets.
- What discriminates (stable in all 4 holdout cells): nextday+ retest (+2.4pp), h1_nested (+0.4pp alone, +2.7pp with nextday+), gap-origin on fast retests (+1.2pp, vs −1.3pp for intraday fast), and the sweep_aligned ladder inside nextday+ (+4.5 → +6.1pp, small n).
- What does NOT discriminate: birth impulse size (flat, user claim not supported), H1 long-run swing anchor (stable −0.4pp, mildly harmful), iFVG inversion (inv ≈ orig ≈ base, dead), sweep-born standalone (unstable), gap-origin as an add-on to nextday+ (−0.5pp).
- Count-shrink without hit loss is real: nextday+ & h1_nested keeps 14,057 zones (83% shrink, 247/day) at 48.8%; the full stack keeps 557 (99.3% shrink, ~10/day) at 52.1%. But at 1R/1.5ATR/0.06% no cell clears costs — the edge must be monetised with wider targets or cheaper execution, not this exit geometry.

