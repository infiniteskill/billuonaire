# PEAD — Post-Earnings Announcement Drift, Indian Equities

**Verdict: NO-GO.** The top-quintile drift exists in isolation (+1.3–1.6% abnormal over 20–30
trading days, survives 0.25% costs) but it is **not an earnings effect**: it fails the
regime-matched random-window null (random same-stock entries in the same half-year do as well
or better, p ≥ 0.73), the per-year sign flips (~half the years negative excess), and the
quintile ladder is not monotonic (only Q5 pops; Q1–Q4 are flat noise). What looks like PEAD
here is local stock momentum in a survivor universe, not announcement drift.

Run: 2026-07-18. Code + caches: scratchpad `pead_fetch_dates.py`, `pead_analysis.py`,
`pead_dates.parquet`, `pead_events.parquet`, `pead_run_full.out`. Production code untouched.

---

## Coverage (honest accounting)

| item | value |
|---|---|
| price data | `dailymax.parquet`, 138 NSE symbols + NIFTY (^NSEI), daily, up to 2026-07-17 |
| earnings dates source | yfinance `get_earnings_dates(limit=100)` per `SYMBOL.NS` (Yahoo caps at 100) |
| symbols with dates | 136 fetched (HEROMOTOCO, RVNL: no earnings table on Yahoo) |
| usable events | **8,053** announcements across **135 symbols** |
| span | **2007-10-11 → 2026-07-17** (~19 years — far better than the feared 2–4y) |
| per-symbol events | mean 60, median 65, min 18 (SJVN), max 76 |
| events/year | 73 (2007) rising to ~500–534/yr from 2019; early years thinner |
| quarters used | 76 (quarters with ≥10 cross-sectional events; median 114 events/qtr) |
| abnormal-return anchor | NIFTY history starts 2007-09, so no events before that |

**Survivorship caveat (prominent):** the universe is *today's* 138 liquid names projected
backward. Dead/delisted/faded names are absent, so absolute drift numbers are inflated —
the same-stock random-window null shares the bias and is therefore the only claim-worthy
comparison. Yahoo earnings dates are also approximate (time-of-day ambiguous, occasional
off-by-one); the reaction-day search below absorbs ±1 day.

## Method (leak-aware)

- **Surprise proxy** = abnormal reaction return: stock close-to-close minus NIFTY
  close-to-close, on the single day with the largest |abnormal move| among {t−1, t, t+1},
  t = first trading day ≥ announcement date (IST). Chosen offsets: t−1 20%, t 34%, t+1 46% —
  consistent with after-market announcements and US-timezone datestamps. Mean |surprise|
  3.9% vs ~1.5% typical daily abnormal move, so the window is catching real reactions.
- **Ranking**: surprise → quintiles per calendar quarter, cross-sectional (academic
  convention; note a live rule would need trailing thresholds — quintile edges here use
  full-quarter information).
- **Trade**: enter next OPEN after the reaction day (never earlier than t+1), hold H ∈
  {10, 20, 30} trading days (entry day = day 1), exit at CLOSE of day H. Abnormal = stock
  open→close window return minus NIFTY same-window return. Costs 0.25% round trip.
- **Timing-leak note**: picking the max-|move| day within t−1..t+1 can, in the r=t case,
  use t+1's move for the comparison. The strictly leak-free variant (surprise = CAR over
  t−1..t+1, entry at t+2 open) reproduces the result slightly *stronger* (H=30: +1.74%
  gross vs +1.60%), so the measurement is not an artifact of that choice.
- **Nulls** (200 seeded draws, seed 42, same stock, identical window length, portfolio
  bootstrap): **A** = uniform over the covered span (spec null); **B** = regime-matched,
  entry within ±126 trading days of the actual entry, the event's own window excluded.

## Quintile × hold drift matrix (mean abnormal %, gross, vs NIFTY)

| surprise quintile | H=10 | H=20 | H=30 |
|---|---:|---:|---:|
| Q1 (most negative, mean −5.6%) | −0.18 | +0.33 | +0.46 |
| Q2 | −0.01 | +0.26 | +0.72 |
| Q3 | −0.22 | −0.12 | +0.42 |
| Q4 | −0.03 | +0.34 | +0.48 |
| **Q5 (most positive, mean +6.4%)** | **+0.43** | **+1.26** | **+1.60** |

n ≈ 1,570–1,625 per cell. **Monotonicity: FAIL.** Spearman ρ(quintile, mean) = 0.5–0.6,
entirely driven by the single Q5 point; Q1–Q4 are indistinguishable noise. Real PEAD
should step up through the quintiles. It does not.

## Q5 long — detail and null comparison

| H | n | abn gross | abn net | raw net | win(abn) | t-stat | null A mean±sd | p vs A | null B mean±sd | p vs B |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 | 1,597 | +0.43% | +0.18% | +0.47% | 51.5% | 2.8 | 0.39±0.16% | 0.38 | 0.59±0.16% | **0.83** |
| 20 | 1,606 | +1.26% | +1.01% | +1.42% | 55.7% | 5.9 | 0.79±0.21% | 0.015 | 1.38±0.22% | **0.73** |
| 30 | 1,608 | +1.60% | +1.35% | +2.09% | 55.2% | 6.3 | 1.28±0.27% | 0.13 | 2.20±0.29% | **0.98** |

Reading: the unconditional null (A) is already strongly positive — these survivor stocks
beat NIFTY on *any* random window. Q5 beats null A only at H=20 (p=0.015), not at 10 or 30.
The regime-matched null (B) is the damning one: random entries in the *same stock within
±6 months of the event* drift **as much or more** than the post-announcement window
(H=30: null 2.20% vs actual 1.60%, actual at the 2nd percentile of the null). The
announcement adds nothing beyond the stock's local trend — Q5 selection is just picking
stocks in strong local regimes (short-term momentum), and the event window itself is if
anything slightly *worse* than its neighbourhood.

Corroborating: pooled across ALL quintiles, announcement windows return +0.74% (H=30) vs
null A's +1.28% — post-earnings periods are, on average, drift-poor, not drift-rich.

## Per-year stability (Q5, excess = actual − null A mean, %)

| year | H10 | H20 | H30 | | year | H10 | H20 | H30 |
|---|---:|---:|---:|---|---|---:|---:|---:|
| 2007 | −0.0 | +0.7 | +5.3 | | 2017 | −0.6 | −0.8 | −0.7 |
| 2008 | −1.4 | −1.3 | −2.7 | | 2018 | −0.8 | −1.7 | −3.5 |
| 2009 | +0.3 | −0.2 | +0.3 | | 2019 | +0.5 | +1.2 | +1.8 |
| 2010 | +0.9 | −0.4 | −1.2 | | 2020 | +0.3 | +0.0 | +0.6 |
| 2011 | +0.6 | +2.9 | +1.9 | | 2021 | −1.1 | −1.2 | −2.1 |
| 2012 | +0.1 | −0.1 | −0.7 | | 2022 | −1.1 | −0.7 | −1.0 |
| 2013 | +0.4 | +0.6 | +1.3 | | 2023 | +1.1 | +3.2 | +4.0 |
| 2014 | +0.5 | +2.8 | +3.7 | | 2024 | −0.3 | +0.4 | +0.2 |
| 2015 | +2.1 | +3.4 | +3.0 | | 2025 | −0.5 | −0.5 | −1.3 |
| 2016 | −0.3 | −0.3 | −1.1 | | 2026* | +1.3 | +1.9 | +2.8 |

Excess vs null A positive in only **10–11 of 20 years** (vs null B: 8 of 20). A coin.
The aggregate is carried by 2011/2014/2015/2023 (+2.8 to +4.0%); 2008/2018/2021/2022 are
deeply negative. **Consistent-sign bar: FAIL.**

## Short side (Q1, academic — cash shorting not possible overnight; futures-only, F&O names)

Gross abnormal short P&L: +0.18% / −0.33% / −0.46% at H=10/20/30 — i.e. negative-surprise
names *keep underperforming NIFTY only briefly if at all*; at 20–30 days they revert.
Net of 0.25% costs everything is ≤ −0.07%, and raw (futures are un-hedged directional)
net is −0.37% to −1.50%. **Dead. Do not build.**

## Costs impact

0.25% round trip halves H=10 (0.43→0.18%) and trims H=20/30 by ~20%. Costs are not the
binding constraint — attribution is. Even gross, the drift fails the null.

## Verdict: NO-GO

- Q5 drift (+1.3–1.6% over 20–30 td, t ≈ 6) is *measurable* and cost-surviving, but it is
  **not attributable to the earnings announcement**: regime-matched same-stock random
  windows match or beat it at every hold (p ≥ 0.73).
- No quintile monotonicity; only the extreme-positive cell is alive → fragile,
  momentum-flavoured, not a PEAD ladder.
- Sign flips in ~half the covered years; the aggregate is 4 good years' worth of edge.
- Short side dead after costs.

If anything in this study deserves a follow-up it is **short-term continuation/momentum in
strong local regimes** (that is what null B revealed the Q5 "drift" actually is), studied
directly — not via earnings dates. As a PEAD strategy on this data: plainly, the edge is
not there.

**Scope caveats**: survivor universe of today's 138 liquid names; Yahoo announcement dates
(approximate timing, ~60 events/symbol, thin pre-2010); quintile edges use full-quarter
information (academic, mildly optimistic); NIFTY-only risk adjustment (no beta/size/sector
model). Every one of these biases points *toward* finding drift — and it still failed.
