# OPPORTUNITY-COVERAGE (RECALL) AUDIT + LAYERED-CASCADE TEST

The two never-done analyses: (1) enumerate what a human SEES on the M5 chart and measure which fraction the 7 parity-locked v2 tools fire on (recall — the inverse of every study run so far); (2) test the role-separated L1-direction → L2-location → L3-timing cascade, causal at every stage, with realistic fills.

**Data**: `data/long5m/`, native 5m, 57 sessions (2026-04-27 … 2026-07-17). **Top-10 by median rupee-volume** (HDFCBANK ₹24.8cr/5m, RELIANCE, ICICIBANK, SBIN, INFY, BHARTIARTL, TCS, LT, AXISBANK, BAJFINANCE ₹6.9cr) + **mid-liquidity 10** (ranks 65-74 of 138, ₹1.7-1.9cr: MOTHERSON, MUTHOOTFIN, DRREDDY, CHOLAFIN, LODHA, LUPIN, PNB, BHARATFORG, MAXHEALTH, GRASIM).

**Signals** (44,038 across the 20 symbols, ~38/symbol/session): the 7 v2 detectors driven tick-by-tick per symbol with the REAL detector classes + CandleStore + StockContext + LevelEngine zone lifecycle + session-end hooks + the pipeline's OB/FVG carry/prune rule, default params (what the registry instantiates — config has no overrides). **Parity gate vs the completed 2-symbol orchestrator capture (RELIANCE+INFY, `signals60.parquet`): 100% precision, 99.73% recall** (11 of 4,047 signal keys missing, all fvg_cb/ob_lux level-lifecycle edge cases from omitting the support detectors' level interplay), identical entries. NIFTY wyckoff phase timeline driven the same way (same-close, index-first semantics). Each signal also snapshots the LIVE carried OB/FVG levels at fire time — the true L2 location data.

## Method — opportunity definition (Part 1)

OPPORTUNITY = bar `t` + direction `d` where, walking forward bar-by-bar within the session from entry = `close[t]`: favorable excursion reaches **≥ X·ATR14(t) before adverse ≥ 0.75·ATR14(t)** (X = 2.5 main; 2.0 / 3.0 swept). ATR14 = trailing SMA of TR (identical to `StockContext.atr`). Intrabar ambiguity conservative (adverse side of a bar checked first, in both qualification and peak walks). Run extent: after qualification the run continues until a 0.75·ATR retrace from the running peak (prior-bar peak checked before the bar can extend it) or session end; **magnitude** = peak favorable in ATR(t). Non-overlap greedy by start (both directions qualify → larger magnitude; scan resumes after run end). Spot-verified by hand against raw bars.

Pattern heuristics (first match wins, causal, lookbacks may cross the overnight gap): **gap-open** (one of first 3 session bars & |open−prev close| ≥ 0.75·ATR), **reversal-after-sweep** (last-3-bars sweep of the prior 12-bar extreme against `d`, close back through it), **coil-break** (6-bar range ≤ 2·ATR, close breaks it in `d`), **trend-continuation** (3-bar net ≥ 1·ATR in `d`), **other**. Time-of-day: open <11:00 / release 11:00-14:45 / late ≥14:45.

## Table A — opportunity census ("how much visible trade IS there")

| thr (X·ATR) | group | n opps | opps/sess/sym | mag q25/50/75/90 (ATR) | med bars→peak | long% |
|---|---|---|---|---|---|---|
| 2.0 | top10 | 3161 | 5.55 | 2.20/2.52/3.15/4.10 | 6 | 47% |
| 2.0 | mid10 | 3366 | 5.91 | 2.21/2.57/3.23/4.13 | 6 | 50% |
| **2.5** | **top10** | **2343** | **4.11** | 2.70/3.04/3.64/4.56 | 8 | 47% |
| **2.5** | **mid10** | **2491** | **4.37** | 2.71/3.07/3.72/4.56 | 8 | 49% |
| 3.0 | top10 | 1798 | 3.15 | 3.21/3.52/4.13/5.10 | 11 | 47% |
| 3.0 | mid10 | 1972 | 3.46 | 3.20/3.54/4.18/5.16 | 10 | 50% |

@2.5, all 20 symbols (n=4,834): time-of-day — open(<11:00) **42%** (first 30 min alone 23%), release(11:00-14:45) **51%**, late(≥14:45) 7%. Pattern — other **66%**, gap-open 14%, reversal-after-sweep 13%, trend-continuation 6%, coil-break 0.6%. Magnitude is pattern-independent (median 3.0-3.2 ATR in every class). Median run peaks 8 bars (40 min) after start, q90 = 27 bars.

**Reading**: a clean ≥2.5-ATR run exists ~4×/day/symbol — the market is NOT opportunity-poor. Two-thirds of run starts have no obvious 3-bar setup shape (drift/rotation starts), and 42% start before the system's trade window opens.

## Table B — per-tool recall @2.5, top10 (coverage = opp has a same-direction fire within ±3 bars of start)

| tool | n signals | coverage | med lag (bars) | med captured (frac of run) | % of tool's fires near an opp start |
|---|---|---|---|---|---|
| ob_lux | 5394 | 16.8% | −2 | 1.00 | 17.9% |
| fvg_cb | 2346 | 16.9% | 0 | 0.98 | 26.7% |
| compression_fade | 8836 | 46.8% | −1 | 1.00 | 16.7% |
| inducement | 700 | 5.2% | −1 | 1.00 | 17.1% |
| bpr | 924 | 5.3% | −1 | 1.00 | 19.7% |
| mitigation | 3193 | 23.5% | −1 | 1.00 | 19.8% |
| turtle_soup | 419 | 4.1% | −1 | 0.96 | 22.9% |
| **UNION(7)** | **21812** | **72.5%** | — | — | **18.8%** |
| **RANDOM control** (same per-session signal counts, uniform re-timing, 20 draws) | 21812 | **81.1%** | — | — | — |

Sweeps: union 72.1% @2.0, 73.1% @3.0 (threshold-insensitive). Release-window-only opps: union 71.7%, entry-class-only union 64.3%. Entry-class union all-day 62.5%. Best pairwise unions: mitigation+compression_fade 58.5%, fvg_cb+compression_fade 56.1%, ob_lux+compression_fade 55.4% — everything else adds ≤3 pts over compression_fade alone (46.8%).

**The honest read**: 72.5% union coverage sounds high, but a random generator with the same signal budget covers **81.1%** — at ~38 fires/symbol/day the ±3-bar windows tile the session. The tools' fires are slightly ANTI-correlated with run starts (clustered in bursts, and biased to pullback locations). Only ~19% of all fires sit near any clean-run start. Recall per se is not the binding failure — signal discrimination is. When a tool IS present at a run it is punctual (median lag −2…0 bars, median captured fraction ≈ 1.0 of the run).

## Table C — the MISSED set (645/2343 = 27.5% of top10 opps; no tool fired in ±3 bars)

| dimension | missed | covered | note |
|---|---|---|---|
| time-of-day | 26-28% missed in every bucket | — | timing-flat |
| magnitude (med ATR) | 3.06 | 3.03 | misses are NOT small runs |
| pattern: trend-continuation | **57.9% missed** (n=140) | — | the standout class |
| pattern: coil-break | 40.0% missed (n=35, small) | — | flag: tiny sample |
| pattern: gap-open / sweep-reversal / other | 21/27/26% missed | — | tool-shaped patterns are seen |
| pre-drift (6-bar net in d, med) | **+0.24 ATR** | **−0.28 ATR** | missed runs are already moving in d; covered runs start after a pullback |
| pre-drift ≥0.5 ATR in d | 46% | 28% | |
| start = fresh 12-bar breakout | 11% | 4% | 2.75× |
| dist below recent 6-bar favorable extreme (med) | −1.35 ATR | −1.96 ATR | missed starts sit HIGH in the recent range |
| volume spike ≥2× at start | 16% | 17% | volume-neutral — not an ignition-volume story |

Same profile in mid10 (missed drift +0.34 vs covered −0.38; trend-continuation 50.3% missed). **Detector-shape the missed set implies** (descriptive, data-driven — not a validated edge): a **quiet drift-continuation / shallow-pullback breakout** detector — 6-bar net progress ≥ ~0.5 ATR in `d`, price within ~1.5 ATR of (or breaking) the recent 12-bar extreme, no ≥0.75-ATR adverse leg in the preamble, normal volume, any hour. All 7 current tools are pullback-to-zone / sweep-reversal / fade shapes; a trend already in motion with only shallow pullbacks is structurally invisible to them.

## Table D — layered cascade funnel (top10; causal fields at fire time; fills = `step2_engine.simulate`, deduped (symbol,ts,dir); primary scheme k=1.0×ATR be1r_t2; hit = +1ATR-before-−1ATR/24bar, undecided=miss)

L1 DIRECTION = closed-M15 net(8 bars) ≥0.5 ATR aligned OR NIFTY wyckoff phase aligned. L2 LOCATION = entry inside a live carried OB/FVG level of matching kind (±0.25 ATR tol, born >3 bars earlier) OR fresh cluster (≥2 same-direction fires within ±2 bars). L3 TIMING = entry-class tool (compression_fade/inducement/turtle_soup/bpr/mitigation) in 11:00-14:45.

| stage | n sig | n trades | hit% | mean max_r | exp (R) | win% | exp k0.75 fix_t1.5 | exp k1.0 fix_t2 |
|---|---|---|---|---|---|---|---|---|
| S0 all entry-class | 14072 | 12064 | 47.8% | 3.13 | **−0.433** | 22.6% | −0.443 | −0.424 |
| L3-solo baseline (release win) | 8440 | 7377 | 49.4% | 3.26 | −0.464 | 21.8% | −0.452 | −0.449 |
| D1 +direction (htf OR wyck) | 8163 | 6909 | 47.2% | 3.04 | −0.432 | 22.8% | −0.450 | −0.429 |
| D2 +location (zone OR cluster) | 6084 | 4830 | 43.3% | 2.75 | −0.495 | 20.7% | −0.520 | −0.490 |
| **D3 +release win [CASCADE FINAL]** | **3513** | **2860** | **43.8%** | **2.81** | **−0.547** | **19.1%** | −0.534 | −0.540 |
| F1 location-first | 10497 | 8489 | 43.8% | 2.86 | −0.499 | 20.5% | −0.514 | −0.488 |
| F2 +direction | 6084 | 4830 | 43.3% | 2.75 | −0.495 | 20.7% | −0.520 | −0.490 |
| F3 +release win (same final set) | 3513 | 2860 | 43.8% | 2.81 | −0.547 | 19.1% | −0.534 | −0.540 |
| final, L1 = htf AND wyck | 1212 | 959 | 44.8% | 2.74 | −0.526 | 19.9% | −0.527 | −0.508 |
| final, L2 = zone-only | 1383 | 1185 | 46.6% | 3.01 | −0.495 | 21.2% | −0.505 | −0.491 |
| best solo (release win): compression_fade | 5544 | 5235 | 49.3% | 3.50 | −0.463 | 22.0% | −0.451 | −0.439 |
| solo mitigation / bpr / inducement / turtle_soup | 1763/517/385/231 | — | 48-51% | 2.5-3.7 | −0.46/−0.50/−0.51/−0.45 | — | — | — |

**The funnel does not tighten — it degrades.** Direction (L1) is quality-neutral (−0.433→−0.432) while halving the sample. Location (L2) — the carried-zone/cluster layer — actively HURTS (−0.432→−0.495; hit 47→43%, max_r 3.04→2.75): being at a carried OB/FVG zone or in a signal cluster predicts congestion, not release. The release window (L3) hurts again (→−0.547; afternoon ATR decay makes fixed costs relatively heavier). Both orderings converge to the same final set: **n=2860 trades, −0.547R/trade vs best-solo −0.463R** — the cascade is strictly worse than the best solo tool, on 4× fewer trades. The AND-direction and zone-only variants are also negative. No stage, ordering, or scheme (3 tested) produces a positive cell.

## Table E — liquid vs mid-liquidity split

| metric | top10 | mid10 |
|---|---|---|
| opps/sess/sym @2.5 | 4.11 | 4.37 |
| union coverage | 72.5% | 72.9% |
| random control | 81.1% | 81.2% |
| entry-class union | 62.5% | 62.0% |
| % fires near an opp start | 18.8% | 19.4% |
| trend-continuation missed | 57.9% | 50.3% |
| S0 expectancy (R) | −0.433 | −0.367 |
| cascade-final expectancy (R) | −0.547 | −0.467 |
| best solo (release) | cf −0.463 | turtle_soup −0.309 (n=211, small) |
| median ATR (bp of price) | 18.3 | 21.9 |

Liquidity changes essentially nothing about coverage or the cascade shape. Mid-liquidity is uniformly ~0.06-0.08R LESS bad on fills — its ATR is ~20% larger relative to price (21.9 vs 18.3 bp), so spread+costs eat relatively less — but every cell is still deeply negative. Liquidity is not the lever.

## VERDICT

1. **Can the tools see the trades a human sees?** Nominally 72.5% union coverage of clean ≥2.5-ATR runs (and punctual when present: lag −2…0 bars, ~full run capturable) — but a random signal generator with the same 38-fires/symbol/day budget covers **81.1%**. Corrected for chance, the toolset has **zero (slightly negative) selectivity for run starts**; only ~19% of its fires sit near any clean run. The system's problem was never "not enough signals" — it is that fires do not discriminate run-start bars from the rest of the session.
2. **Where they fail**: uniformly across time-of-day and magnitude, but sharply by SHAPE — 58% of trend-continuation starts are missed (vs 21-27% for gap/sweep/other). The missed set starts high in the recent range (−1.35 vs −1.96 ATR below the 6-bar extreme), already drifting in-direction (+0.24 vs −0.28 ATR), 2.75× more often a fresh 12-bar breakout, on normal volume. All 7 tools are pullback/reversion-shaped; quiet continuation is structurally invisible.
3. **Does the layered cascade tighten into viability?** No — it shrinks INTO noise. L1 direction is neutral, L2 location (carried zones/clusters) is quality-NEGATIVE, L3 release-window is quality-negative; final = −0.547R/trade on 2,860 trades vs −0.433R unfiltered and −0.463R best-solo, in both orderings, all 3 fill schemes, both liquidity tiers. The role-separated conjunction is falsified on this data: its layers do not carry independent positive information.
4. **What NEW detector the missed set implies**: a drift-continuation/shallow-pullback-breakout shape (≥0.5-ATR 6-bar drift in `d`, at/near the 12-bar extreme, no ≥0.75-ATR adverse leg, volume-neutral). That is the descriptive gap. BUT the cascade result is the sterner fact: with every current entry class, realistic NSE costs on 5m fills lose ~0.4-0.5R/trade regardless of filtering — so closing the recall gap alone cannot rescue the system; the binding constraint is post-cost extraction (entry granularity + afternoon ATR decay + ₹40+STT round-trip), not signal coverage.

**Small-sample flags**: coil-break n=35 (top10); inducement/turtle_soup/bpr per-stage cells are 200-900 trades; mid10 turtle_soup best-solo n=211. Direct-drive misses 0.27% of orchestrator signals (fvg_cb/ob_lux lifecycle edges) — immaterial at these effect sizes. Native-5m paths make fills coarser (pessimistic) than the production M1 loop — same caveat as RESULTS.md; hit%/max_r (cost-free) columns bound the upside and are also unimproved by the cascade.

*Artifacts (scratchpad): `opportunities.parquet`, `merged_signals.parquet` (20-symbol drive w/ level snapshots), `recall_opps_25_{top10,mid10}[_feat].parquet`, `cascade_{top10,mid10}.csv`, `recall_analysis.out`; scripts `opp_enum.py`, `drive_one.py`, `recall_analysis.py`, `miss_probe.py`, `drive_parity.py`.*
