# Implementation Roadmap

Six phases. Each ends with working, tested software. Phase plans written as
bite-sized TDD task files (`PLAN-PHASE-N.md`) when the phase starts — Phase 1
plan exists now (`04-PLAN-PHASE-1.md`). No API until Phase 6.

## Phase 1 — Skeleton & Data Spine (no market logic)
Models (Candle/Level/Evidence), config loader, CandleStore (parquet, multi-TF
aggregation, no-lookahead views), MockFeed with 2 scenarios, FileFeed (CSV),
CLI shell (`init`, `list`), Journal (JSONL). 
**Exit criteria:** `trader init` + `trader list` work; store aggregates M1→M5/M15/H1/D1
correctly; MockFeed replays a scripted day through the store; pytest green.

## Phase 2 — Levels, Structure, Liquidity
Level state machine (full transition table + tests), swings, structure (BOS/CHoCH
+ fake-BOS memory), liquidity (pools, PDH/PDL, rounds), sweep detector,
DetectorRegistry with enable/disable + weight renormalization proof-test
(disable OB → identical run, weights re-sum to 100).
**Exit criteria:** judas_reversal scenario: sweep + CHoCH fire at scripted candles
(exact indexes asserted); disabling any detector changes no other detector's output.

## Phase 3 — Zones, Wyckoff, Templates
orderblock, breaker, fvg (FVG/iFVG/BPR/CE), volume/VSA, wyckoff phase classifier,
timestats (priors + persistence), template classifier + TemplateGate.
**Exit criteria:** full scenario matrix (02-DETECTOR-SPECS table) passes —
each scenario fires required detectors, fires none of the forbidden ones.

## Phase 4 — Decision, Risk, Paper Execution
Confluence engine, gates (time/risk/regime/psychology/template), sizing, limits,
TradePlan builder (entry zone/stealth stop/targets), PaperBroker (fills + costs),
PositionManager (breakeven 1R, partials 1R/2R, structure trail, wick tolerance,
squareoff), `trader watch` live loop with rich table, `trader status`, `trader journal`.
**Exit criteria:** stop_hunt_survive scenario: position survives wick, exits at
target; grind_markdown: zero longs; full trade lifecycle journaled with evidence
snapshot; costs visible in PnL.

## Phase 5 — Replay & Report
Replay engine (FileFeed bar-by-bar, same pipeline), metrics (WR/PF/DD/expectancy,
per-template, per-gate skip analysis, hunt-survival stats, day-clustered CIs),
`trader replay`, `trader report`, skipped-setup outcome scoring,
learn/calibrate.py (weight + timestats recalibration, walk-forward split).
**Exit criteria:** replay over 30 stocks × N days of file data produces report;
replay of MockFeed scenarios reproduces Phase 4 outcomes exactly (single-pipeline proof).

## Phase 6 — Kite Adapter (when API purchased)
kiteconnect auth flow (daily token), KiteFeed (WebSocket ticks → M1 candles),
historical bootstrap (if add-on) else bhavcopy backfill, instrument token map,
options-chain snapshotter (15-min cadence → disk, builds own OI history),
enable cage detector, paper-live run during market hours.
**Exit criteria:** paper-live session on real ticks, 30 stocks, journal + report;
zero code changes outside `feed/kite.py`, snapshotter, and config.

## Then: iterate loop
Run paper-live ≥10 sessions → report → kill/reweight weak detectors → repeat.
Real orders = separate future decision, behind Broker ABC + kill-switch.

## Testing Discipline (all phases)
- TDD per task. Scenario ground-truth tests are the spec — detector "works" only
  if it fires at the scripted candle index, not "looks right".
- Every bug found later becomes a new scripted scenario.
- No network in tests. Decimal everywhere; tick 0.05 quantization asserted.
