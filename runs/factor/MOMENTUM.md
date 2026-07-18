# MOMENTUM FACTOR — VALIDATED (first PASS of the program) 2026-07-18
12-1 cross-sectional momentum, monthly top-K rotation, 138-symbol NSE universe, 2003-07→2026-06
(275 months), 0.25% RT delivery costs. Full numbers: MOMENTUM_raw.txt.

## VERDICT: GO (qualified)
- Beats the random-rotation null (identical turnover, 200 seeded draws) at the 100th percentile
  pooled, every variant (mom ~31% ann vs random median ~23.5%).
- Beats EW buy-hold of the SAME universe (the survivorship-neutral test): +0.41..+0.65%/mo active,
  t = 1.94..2.24 pooled; eras: <=2012 flat (+0.03..0.12), 2013-19 +0.57..0.65 (t up to 2.15),
  2020-26 +0.68..1.15 (t up to 1.99). Majority-of-eras bar met.
- DECILES MONOTONE: rho 0.794 (p=0.004), D10-D1 +0.97%/mo (12.3%/yr, t=2.07) — real-factor signature.
- Sharpe 1.1-1.3; dd -30..-57%; turnover ~0.32-0.36/mo.

## Risks / prerequisites before live
1. MOMENTUM CRASHES are real here: 2009-05 active -22.2% (mom +64.6% vs EW +123.4% in the 2009
   rebound); 2020 handled well (mom 92.9% vs EW 83.1%). Add the standard crash rule (halve/skip
   exposure for N months after a >20% index drawdown) before live.
2. Survivorship: absolute returns inflated; the ACTIVE spread is the trustworthy number.
3. t~2 = solid, not bulletproof. Start small, monthly cadence, judge on active-vs-EW not absolute.
4. Taxes (STCG on <12mo holds) not modeled.

## Ops sketch
Month-end: rank 138 names by t-252..t-21 return -> hold top 15 EW -> rotate (~5 names/mo).
Delivery, no leverage. ~30 min/month.
