# BATTLE — three-way account backtest (₹1,00,000 each) — 2026-07-19

Window for A/C and the B slice: 57 sessions, 2026-04-27..2026-07-17.
Data: facts_first.parquet (80,636 zone first-retests), dailymax.parquet (138 NSE symbols + NIFTY, 1996/2002→2026-07-17).
Sanity: LADDER cell (nextday & h1_nested & sweep_aligned) reproduced exactly — n=557, hit 52.11%, netR −0.1019.

## A. USER'S STRATEGY — ladder, 0.5% of current equity per trade, compounding

Trades ordered by (session, ri); exact entry timestamps absent, ri (per-symbol bar index) is the intra-session
proxy — ordering affects only drawdown/curve, NOT final equity (the product Π(1+0.005·netR) is commutative).
12 of 557 trades are unresolved (NaN outcome) and were dropped; headline hit/netR already exclude them.

| | full ladder | 50-stock top-4 |
|---|---|---|
| n (resolved) | 545 | 198 |
| win rate | 52.1% | 46.0% |
| final equity | **₹75,233** | **₹79,505** |
| total return | −24.77% | −20.49% |
| max drawdown | −28.75% | −21.96% |
| sum of R | −55.55 | −45.35 |
| simple (non-compounded, fixed ₹1L) | −27.77% | −22.68% |
| best / worst trade | +0.97R (+₹486) / −2.40R (−₹1,202) | +0.94R / −1.46R |

Compounding did NOT flatter A — at a negative edge it cushions losses (−24.8% vs −27.8% simple).
50-stock top-4 variant = top-50 symbols by ladder row count, top-4 per symbol by gap_atr desc (impulse tiebreak);
selection is in-sample (needs the whole window to rank) and its per-trade edge is WORSE (mean R −0.229 vs −0.102,
win 46% vs 52%) — the gap_atr/impulse "best rungs" filter anti-selects.

Weekly equity (full ladder | 50×4):
```
W18 2026-04-30  ₹99,342  | ₹99,902        W24 2026-06-12  ₹92,524 | ₹89,544
W19 2026-05-08  ₹101,821 | ₹100,638       W25 2026-06-19  ₹91,667 | ₹89,670
W20 2026-05-15  ₹98,789  | ₹97,161        W26 2026-06-25  ₹86,858 | ₹87,193
W21 2026-05-22  ₹95,796  | ₹94,967        W27 2026-07-03  ₹82,746 | ₹84,292
W22 2026-05-29  ₹90,689  | ₹94,482        W28 2026-07-10  ₹78,730 | ₹83,027
W23 2026-06-05  ₹87,267  | ₹89,815        W29 2026-07-17  ₹75,233 | ₹79,505
```
Steady bleed, no single blow-up: the −0.10R mean edge × 545 trades is the whole story.

## B. MOMENTUM — 12-1 monthly top-10 EW rotation, 0.2% RT per unit turnover

Formation from 2003-07 (universe hits ~85 names 2002-07 + 12m lookback; ≥50 ranked names required;
pre-2002 data has only ~35 survivors and was excluded). Ranks = close(t−1m)/close(t−12m)−1 at month-ends.

**Full history 2003-08..2026-07 (276 months):** CAGR **40.06%**, maxDD **−64.5%**, worst year 2008 −63.7%,
final ₹1L → ₹22.53 crore (2,252.9×).

**SURVIVORSHIP CAVEAT (do not skip):** the universe is today's 138 actives. EW buy-hold of the same universe
compounds at 38.49% — itself absurd (NIFTY did ~13%); EW-of-survivors beats NIFTY by ~11pp/yr (measured in the
factor program). The absolute CAGR and the ₹22.5cr are NOT attainable. The trustworthy number is the ACTIVE
spread: this top-10/monthly-close config gives **+1.56pp/yr** over EW buy-hold — thinner than the validated
top-15/daily-rank config (+0.4–0.65%/mo, t≈2, runs/factor/MOMENTUM.md), consistent with a real but modest factor.

**Crash-rule table** (index = NIFTY from 2007-09, EW-universe splice before; rule checked at month-end):

| rule | CAGR | maxDD | mo-in-cash | worst year |
|---|---|---|---|---|
| none | 40.06% | −64.5% | 0 | 2008 −63.7% |
| abs-mom idx 12m<0 | 35.01% | −49.9% | 51 | 2008 −49.9% |
| abs-mom EW-idx 12m<0 | 37.44% | −49.9% | 36 | 2008 −49.9% |
| **drawdown >15% off 52w-hi** | **38.68%** | **−30.2%** | **36** | 2008 −21.2% |
| 200DMA | 36.60% | −36.3% | 67 | 2008 −36.3% |

**Recommended non-MA rule: the 15% drawdown rule.** It dominates both abs-mom variants on every column —
costs only −1.4pp CAGR vs no rule, halves maxDD (−64.5% → −30.2%), cuts 2008 from −63.7% to −21.2%,
and spends the fewest defensible months in cash (36, tied with abs-mom-EW which keeps −49.9% DD).
Abs-mom is too slow out of the 2008/2009 turn; 200DMA whipsaws (67 mo cash).

**Same-window slice 2026-04-27..2026-07-17** (daily, portfolio from prior month-end ranks, rebalance at
month-crossings): final **₹100,414** (+0.41%), maxDD −7.97%. NIFTY +1.00%, EW universe +0.71% over the
same window. **Three months of one regime — this slice is noise**; it says "momentum didn't lose money
while the ladder lost 25%", nothing more.

## C. COMBO — ladder gated by momentum top-half (rank at prior month-end)

All 557 ladder trades matched to the dailymax universe; percentile of 12-1 momentum taken at the last
month-end before the trade session.

| cell | n | resolved | hit | netR | sumR |
|---|---|---|---|---|---|
| FULL ladder | 557 | 545 | 52.1% | −0.102 | −55.5 |
| mom TOP-half | 298 | 291 | 54.6% | **−0.055** | −16.1 |
| mom BOTTOM-half | 259 | 254 | 49.2% | −0.155 | −39.5 |

Top-vs-bottom spread +0.100R, but Welch t=1.17, **p=0.24** — not significant at n≈290/254.

4-way holdout (temporal split 2026-06-08 × crc32(symbol)%2), full → combo netR:

| quadrant | full n / netR | combo n / netR | lift? |
|---|---|---|---|
| early/sym0 | 133 / −0.017 | 70 / **+0.161** | yes |
| early/sym1 | 119 / −0.204 | 64 / −0.242 | no |
| late/sym0 | 158 / −0.127 | 92 / −0.060 | yes |
| late/sym1 | 135 / −0.066 | 65 / −0.097 | no |

Combo account sim (0.5% compounding, 291 trades): final **₹91,944** (−8.06%), maxDD −12.30%.

**Verdict:** momentum alignment shifts the ladder by ~+0.05R and +2.5pp hit — directionally positive but
statistically insignificant (p=0.24) and inconsistent (2 of 4 holdout quadrants get worse; the lift lives
entirely in the sym0 half). The aligned cell is STILL sub-cost (−0.055R). Consistent with the prior program
(mom7 alignment: +0.0000 AUC): momentum does not rescue the ladder — it only picks which half of a losing
book to hold.

## THE TABLE

| account (₹1L, 2026-04-27..07-17) | final | return | maxDD |
|---|---|---|---|
| A. Ladder (all 545) | ₹75,233 | −24.8% | −28.7% |
| A′. Ladder 50-stock top-4 | ₹79,505 | −20.5% | −22.0% |
| C. Combo (mom-top-half ladder) | ₹91,944 | −8.1% | −12.3% |
| B. Momentum slice | **₹100,414** | +0.4% | −8.0% |
| B (context) 2003-26 | CAGR 40.1% (survivorship-inflated; active spread +1.6pp/yr); w/ dd-15% rule: 38.7%, maxDD −30.2% | | |

## VERDICTS
1. **Ladder loses money at any size.** −0.10R/trade × 545 = −25% in 3 months at 0.5% risk. The 50×4 "quality"
   filter makes the per-trade edge worse. No position-sizing scheme fixes a negative expectancy.
2. **Momentum is the only live edge in the shop**, but its honest magnitude is the active spread
   (+1.6pp/yr here, +5-8pp/yr in the validated top-15 config), not the 40% CAGR. Use the 15% drawdown
   rule; ignore MA rules.
3. **Combining them doesn't work in the tested direction** (momentum as a ladder filter: p=0.24, holdout-
   inconsistent, still sub-cost). The 3-month slice comparison favors momentum but is itself noise —
   the durable evidence is the 276-month factor record vs the 545-trade negative ladder record.

Caveats: n=557 is small (one regime, 57 sessions); survivorship ~11pp/yr on all absolute momentum numbers;
ladder ordering uses (session, ri) proxy (affects DD only); 12 unresolved trades dropped; 50×4 selection is in-sample.
Scripts: scratchpad/battle_a.py, battle_b.py, battle_c.py.
