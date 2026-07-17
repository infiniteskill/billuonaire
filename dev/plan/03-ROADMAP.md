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
orderblock (with birth_time/hunt-born flag), breaker, fvg (FVG/iFVG/BPR/CE), volume/VSA,
wyckoff phase classifier, **compression + PO3 FSM**, **index context detector**,
timestats (priors + persistence), template classifier + TemplateGate.
**Exit criteria:** full scenario matrix (02-DETECTOR-SPECS table) passes —
each scenario fires required detectors, fires none of the forbidden ones.

## Phase 4 — Decision, Risk, Paper Execution
Confluence engine (4-layer spatial, 06 §1–2), gates (time/risk/regime/psychology/template
+ **ChaseGate, EventCooldownGate**), 3-stage entry FSM (06 §4), sizing (+max_stop_atr skip),
limits (+daily_profit_lock_R, portfolio heat, correlation cap), opposing-map targets (06 §6),
PaperBroker (fills + costs), PositionManager (TF-promotion ratchet trail 06 §7, wick
tolerance, time-stop, early-exit on counter-zone, squareoff), obviousness multiplier (06 §8),
**pre-market scanner + fit score + --auto** (06 §9), session state machine (06 §10),
`trader watch` rich live table, `trader status`, `trader journal`.
**Exit criteria:** stop_hunt_survive scenario: position survives wick, exits at
target; grind_markdown: zero longs; full trade lifecycle journaled with evidence
snapshot; costs visible in PnL.

## Phase 5 — Replay & Report
Replay engine (FileFeed bar-by-bar, same pipeline), metrics (WR/PF/DD/expectancy,
per-template, per-gate skip analysis, hunt-survival stats, day-clustered CIs),
`trader replay`, `trader report`, skipped-setup outcome scoring,
learn/calibrate.py (nightly self-audit 06 §10: per-detector precision, capped weight
nudges ±10%/wk, auto-bench flag — human kills, walk-forward split, all changes journaled).
**Exit criteria:** replay over 30 stocks × N days of file data produces report;
replay of MockFeed scenarios reproduces Phase 4 outcomes exactly (single-pipeline proof).
**STATUS: COMPLETE** — 565 tests green. fetch/replay/report/calibrate CLI shipped;
single-pipeline gate passed (byte-identical journals); synthetic month (2 sym × 22
sessions) verified end-to-end: tables render, 22-day cluster stats, calibrate closes
the loop (3105 verdicts). Detector memory session-bounded (C10), replay `--fresh`,
stale dated-level carry pruned to newest generation. Known calibration debt for P6
real data: arm knife-edge near round numbers (stop-snap vs max_stop_atr) suppresses
day-2+ mock judas entries; expiry_size_mult×max_qty=1 floors to qty 0 on Thursdays;
flat Rs-20 brokerage swamps small mock notionals (net R misleading on 100-rupee prices).

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
