# Phase 5 Implementation Plan — Data, Replay, Reports, Learning

> **For agentic workers:** superpowers:subagent-driven-development. COMPACT code mandate.
> Folds in gap-audit items C1-C7, C10, B11, B14. 505 tests green at 6d2edc0.

**Goal:** `trader fetch` pulls real NSE data → `trader replay` runs the month over 30 stocks
through the SAME pipeline → `trader report` prints honest metrics → learning loop wired.

## Global Constraints
- Decimal/tz/no-lookahead as ever; single pipeline (replay = Orchestrator on FileFeed, no forked logic)
- Every task commits with trailer `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`
- Metrics report GROSS R and NET (costs) separately — flat ₹20 brokerage swamps small notionals

### Task 1: Data downloader (C1)
tools/fetch.py + CLI `trader fetch SYMBOLS... --days N --data DIR [--source yfinance|csv]`.
yfinance `.NS` M1 (trailing ~30d, chunked ≤7d requests) → FileFeed CSV schema
(ts ISO +05:30, tick-quantized, volume int); NSE bhavcopy D1 backfill appended as
09:15-anchored session bars? NO — D1 kept separate dir for scanner warmup (store ingests M1 only).
Validation: session-bounds filter, dedupe, gap report printed. Add `yfinance` dep (app extra "data").
Holiday skip natural (no data = no session). Tests: converter pure-function w/ fixture frames (no network).

### Task 2: Persistence wiring (C2+C5 partial)
`trader watch`/`replay` load candle cache before run + save after; `trader list` computes real
fit when cache present ("-" only when empty); LevelStore save/load per symbol per session end
in pipeline (config paths under --dir). Crash-recovery scope NOTE: positions/RiskState still
memory-only (deferred to live phase — replay doesn't need it). Tests incl list-fit rendering.

### Task 3: Replay CLI + metrics (C3)
replay/engine.py: thin driver — build FileFeed(data dir), Orchestrator over date range, per-day
journal dirs. replay/metrics.py: from journals — trades, WR, gross/net PF, expectancy (R),
max DD (equity curve on net R), per-template + per-symbol + per-gate-skip tables, day-clustered
(mean/std per day, n_days, naive CI note when n<10). CLI `trader replay --data DIR --from --to
[--stocks nums|--all] [--index SYM]` and `trader report --journal DIR [--gross]`.
Gate: replay of the 5 mock scenarios written as CSV → identical results to ScenarioFeed run
(single-pipeline proof at file layer).

### Task 4: Learning wiring (C4)
Pipeline records sweep outcomes into timestats (`record(symbol, bucket, swept=True)` on SWEPT
transitions; every bucket gets total increment via detect-time hook — design: pipeline calls
record once per closed M5: swept=any sweep transition this candle). save/load wired
(watch/replay end/start, path under --dir). learn/calibrate.py v1: reads journals, computes
per-detector precision (evidence in winning-trade zones / total evidence emitted, per detector),
prints table + suggested weight nudges (±10% cap, min 30 samples gate) — PRINT ONLY, no auto-apply.
CLI `trader calibrate --journal DIR`.

### Task 5: B11 throttles + B14 breaker proof + logging (C7)
Gates: min_minutes_between_trades (15, config) via RiskState.last_close_ts. Logging: single
setup in cli entry (INFO console, DEBUG file under --dir/logs, --verbose flag). Breaker e2e:
new scenario `breaker_retest` (level swept→reclaimed→inverted→retest fires breaker evidence
→ contributes to an armed cluster) + gate assertion.

### Task 6: Memory bounds + final review (C10)
Detector _seen sets pruned per session (registry reset hook or per-detector session check —
pick ONE mechanism, apply uniformly); levels list cap sanity test over 30-day synthetic run;
final whole-phase review + fix wave.

Exit: `trader fetch` → `trader replay` month × N stocks → `trader report` produces the
honest table (gross+net, per-template, per-day-cluster) the user asked for on day one.
