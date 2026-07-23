# R2 — Methodology bug audit of the Yahoo taught-trade validation scripts

Scope: `tools/yvalidate.py`, `tools/yrun.py`, `tools/y5sim.py`, `tools/yanalyze.py`,
inputs `tools/ytrades.json`, outputs `runs/validate/{results,analysis}.json`.
Goal: find bugs that INVALIDATE or INFLATE the reported conclusions
("swept 90%", "target ~96%", "RANGE-fade at extreme wins", "5m 4/8 to target").
No fixes — find + rate + show how each biases the numbers.

Headline verification (recomputed from results.json, n=30): swept_ok 27/30 = **90%**,
target_reached 29/30 = **97%**. So the reported rates are real arithmetic over the
saved rows — but the rows themselves are produced by the flawed procedure below.

---

## CRITICAL

### C1. Target% does not sequence stop-before-target — 19/30 "wins" had the daily SL breached first (13 on the entry bar itself)
`yvalidate.validate()` computes `target_reached = bool(len(reach))` where
`reach = post[price hits target]` over `post = d.iloc[i:i+forward+1]` (up to 61 daily
bars). It is a pure "did price ever touch target" flag; it is **never gated on
`sl_breach_daily`**. The stop breach is computed in the very same window but only
stored as a date, never compared.

Evidence (results.json, target_reached=True AND daily SL breached on/before target_hit):
```
19 of 30 trades. 13 of those had SL breached on the ENTRY DAY itself, e.g.:
H_aug_short   entry 2023-08-07  sl_breach 2023-08-07  target_hit 2023-08-13
H_feb_short   entry 2023-02-07  sl_breach 2023-02-07  target_hit 2023-02-26  (mfe_R 49)
T_jan_short   entry 2025-01-05  sl_breach 2025-01-05  target_hit 2025-01-14
V_may_long    entry 2026-05-17  sl_breach 2026-05-17  target_hit 2026-05-18
H_old_short   entry 2024-05-26  sl_breach 2024-05-30  target_hit 2024-06-03  (swept=false too)
```
The drawn stops are 2–25 pt away; a single daily bar's range spans that, so on daily
data the stop is "hit" on day one for the majority of trades — yet the trade is still
scored a target win because price later wandered to a 2–8% target within ~3 months.

Bias: **inflates "target ~97%" to near-meaninglessness.** It is an MFE-reached rate,
not a win rate. A correctly sequenced (stop-first) daily count would flip at least
~13 entry-day-stop trades to losses, i.e. realistic daily hit-rate ≈ 10/30, not 29/30.
(The script's own docstring admits the daily SL is invisible — but the REPORT headline
"target 96%" does not carry that caveat.)

### C2. Circular year-resolution — the year is CHOSEN to maximize swept+target, then swept+target are reported
`yrun.run_one()` → for each candidate year runs `validate()`, then
`score() = 2·swept_ok + 3·target_reached + 0.3·min(mfe_R,10)` and picks the
highest-scoring year (`scored.sort(reverse=True)`). So when a trade has >1 candidate
year it literally **selects the year whose real data best matches the setup, then
counts that match as evidence the setup holds.** Textbook selection-on-outcome.

Evidence (results.json `cand_years`): **10/30 trades have >1 candidate year**
(H_jul_short, H_jan_long, H_sep_short, H_jan_short, H_feb_range, H_t14_short,
V_jul_short, Da_feb_short, S_t29_long, S_t30_long). Of those 10, **9 resolved to a year
where swept AND target are both true** — exactly the outcome `score()` rewards. A random
pick among candidates could not produce 9/10. The tie-break (`sort` on the year field,
and the `mfe_R` term) further steers toward the most dramatic-looking year.

Bias: **inflates both swept% and target% for the one-third of trades with year
ambiguity.** The remaining 20 single-candidate trades are still analyst-constrained by
the hand-chosen `era` band (which is drawn to contain the entry), so even n=30 is not a
clean out-of-sample test. Severity critical because it is confirmation bias baked into
the pipeline, not a side effect.

### C3. `mfe_R` is 9–69R and feeds every downstream story, but is unrealizable
`mfe_R = fav.max()/risk` where `risk = |entry−sl|` (≈4 pt) and `fav.max()` is the best
excursion over ~61 daily bars. Median mfe_R = 17.4, max 68.6 (H_apr_short). These are
"favor over 3 months ÷ a 4-pt stop that C1 shows was already breached." They are not
achievable R. Yet `mfe_R` (a) is a scoring term in C2's year pick, and (b) is reported
per-trade as if it were edge. Bias: **grossly inflates the apparent payoff/R of the
taught method.**

---

## MAJOR

### M1. Daily regime describes the wrong timeframe for an intraday method
`yanalyze` classifies regime with `regime()` on **daily** bars (ADX-14 + 40-bar drift)
and builds the whole "RANGE-fade at extreme wins" story from `setup_type` = f(daily
regime). The user trades 5m/30m. The intraday regime (`ltf_regime`) is populated for
only **15/30** trades (the rest predate Yahoo's 60-day 5m / 2023-08 1h windows, so it's
null). So the headline setup classification is a daily-frame artifact that does not
describe the intraday setups actually taken. Bias: the conclusion is about the wrong
timeframe; ~half the sample has no intraday check at all.

### M2. "RANGE beats trending" is largely tautological + rests on n=3 cells
`setup_type` maps **any** daily RANGE regime → `RANGE_FADE` regardless of direction, and
RANGE is the *default* bucket (`else` branch when not `ADX≥22 & |drift|>3%`). Result:
RANGE_FADE=18, REVERSAL=9, **CONTINUATION=3**; pd_tag MID=**3**. With target_reached
29/30 (near-zero outcome variance), per-cell hit-rate comparisons carry no information —
every cell "wins" because almost everything is scored a win (see C1). "RANGE wins"
mostly restates "RANGE is the majority default bucket." Bias: manufactured,
uninformative group effect; CONTINUATION and MID cells are too small (n=3) for any claim.

### M3. Premium/discount tag is fragile and internally self-contradictory
`pos_in_range()` uses a fixed **40-bar daily** window and hard cutoffs 0.34/0.66.
- **5 trades contradict the user's own rule** (short at DISCOUNT / long at PREMIUM):
  H_jan_short, H_feb_range, D_aug_short (short@DISCOUNT); D_nov_long, S_t29_long
  (long@PREMIUM). These are counted in the sample as the method yet violate its premise.
- **3 trades have entry_pos > 1** (H_sep_short 1.23, H_feb_short 1.03, H_apr_short 1.01)
  — the drawn entry sits *above the 40-bar high*, i.e. outside the measurement window
  entirely (degenerate; auto-tagged PREMIUM by overflow). Signals wrong-year resolution
  or a broken metric for those rows.
- **5 more are within 0.06 of a cutoff** (D_aug_short 0.28, H_feb_range 0.31,
  S_t29_long 0.69, D_nov_long 0.70, Da_feb_short 0.72) → a small change in window
  length or cutoff flips them.

So "extreme_ok 22/30" is soft: nudging the window/threshold plausibly swings it to
~16–26/30. Bias: the "trades at extremes" claim is threshold-manufactured and partly
contradicted by its own rows.

### M4. y5sim gap-through and timeout outcomes are dropped from the R stats
`y5sim._r()` sets `R=None` for `STOP_GAP` and `TIMEOUT`. A gap through the stop is
*worse* than −1R, but it is recorded as None and thus excluded from any R average rather
than counted as a loss. `STOP` is a flat −1.0 even when the gap/slippage would be worse.
Bias: **removes the worst outcomes from the realized-R distribution → inflates average R
and understates the fill-through risk the sim was built to measure.**

### M5. y5sim skips the entry bar — same-bar stop-outs are invisible
`path = d.iloc[i0+1 : ...]` starts the walk one bar AFTER the bar that first touched
entry. On 5m the stop is only 3–5 pt beyond entry, so the entry bar itself very often
also tags the stop intrabar (touch-and-reverse retests). By starting at i0+1 the sim
never checks the entry bar for a stop, so it silently survives the single most dangerous
bar. Bias: **understates stop-outs / inflates the 4/8 target rate** — and this partly
cancels the "assume stop before target" conservatism the docstring claims, so the net
direction of the 4/8 number is not actually conservative, it's indeterminate.

---

## MINOR

### m1. Two taught trades (SBILIFE) silently dropped — reported n=30, not 32
`ytrades.json` has **32** trades; `results.json`/`analysis.json` have **30**. Missing:
`SL_t31_short`, `SL_t31_long`. `SBILIFE_1d.csv` is timestamped 20:16, after
results.json (18:12) and analysis.json (19:47) — the two SBILIFE trades were appended to
the input after the runs and never re-evaluated (stale outputs, no dedup/consistency
check; `main()` has no guard that results cover all inputs). Also, SBILIFE has only a
`_1d` cache (no 1h/5m). Bias: not an inflation of rates, but "~32 taught trades" is
overstated — only 30 were tested, and any SBILIFE outcome is unmeasured.

### m2. Timezone conversion shifts every daily bar label back one calendar day → date corruption + month/entry-bar off-by-one
`hist()` does `pd.to_datetime(idx, utc=True).tz_localize(None)`. Stored stamps are
`YYYY-MM-DD 00:00:00+05:30`; converting to UTC yields `YYYY-MM-(D-1) 18:30:00`, so
`.date()` is the **previous** calendar day for every daily bar (verified on HAVELLS:
`2026-07-06 00:00+05:30` → `2026-07-05 18:30`). Consequences:
- All reported dates (resolved, sweep_date, target_hit, sl_breach) are one day early —
  hence artifacts like target_hit/sl_breach dated *before* the entry (H_jul_short,
  H_jan_long, H_jun_short_b, Da_jul_short).
- `resolve_year()` filters on `d.index.month`; a true session on the 1st of a month is
  relabeled to the last day of the prior month, so month-boundary trades can be filed
  into the wrong month → wrong candidate session/year. The `±4 day` `day` filter is
  likewise shifted.
- In `validate`, `get_indexer([Timestamp(date)], 'nearest')` snaps midnight to the
  18:30-of-prior-day bar, so the entry bar it uses is one session off from the bar
  `resolve_year` selected.
Aggregate swept/target impact is small (windows are ±40–60 bars), but this is a genuine
systematic off-by-one that corrupts dates, can misresolve month-boundary trades, and is
the mechanism behind the "SL/target before entry" oddities. Rate as minor→major if any
conclusion depends on exact dates or on month-edge trades.

### m3. `swept` detection window peeks 2 bars past entry
`win = d.iloc[max(0,i-lookback):i+3]` includes bars i+1, i+2 (2 days after entry on
daily). A sweep that only occurs *after* the entry still sets `swept_ok=True`. Mild
look-ahead that slightly inflates the 90% swept figure.

### m4. `contain` metric is a mathematical constant (~0.60), carries zero information
`regime()`'s `contain` = fraction of closes between the 20th and 80th percentile of the
window — which is ≈0.60 for any distribution by definition. Observed values: only
{0.61, 0.63} across all 30 trades. It is not used in the regime decision, but if any
narrative cites "containment ~0.61 ⇒ rangy," that is a tautology, not evidence.

### m5. Correlation cited as signal is not significant, and the outcome barely varies
`corr(ADX, move) = -0.26` at n=30 → t=-1.42, df=28, p≈0.16 (needs |r|≥0.36). Recomputed
from data: corr(d_adx, mfe_pct)=-0.26, corr(d_adx, mfe_R)=-0.20 — both noise at this n.
Combined with target_reached variance of 29/30, the dataset lacks the power and the
outcome spread to support any "regime predicts performance" claim.

---

## Net effect on the four headline conclusions
- **"target ~96%"** — invalidated as a win rate (C1: no stop sequencing, 19/30 stopped
  first; C2: year picked to hit target). It is at best an "MFE reached target within
  ~3 months" rate.
- **"swept 90%"** — inflated by C2 (year selection) and m3 (2-bar look-ahead); soft.
- **"RANGE-fade at extreme wins"** — wrong timeframe (M1), tautological/underpowered
  (M2, m5), fragile and self-contradicting tags (M3).
- **"5m 4/8 to target"** — direction of bias indeterminate: M4 (drops worst outcomes)
  and M5 (skips entry-bar stops) inflate; the "stop-before-target" assumption deflates.
- **Sample** — 30 tested, not the stated ~32 (m1); dates off by one day (m2).
