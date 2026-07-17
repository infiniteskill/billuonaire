# Gap Audit — 2026-07-17 (4-agent sweep, post-Phase-4)

Sources: plan-vs-impl matrix, 31-axiom/problem-catalog defense audit, code-debt sweep,
operational-readiness audit. All findings verified against code with file:line evidence
(details in the four audit transcripts; this file is the deduped, ranked synthesis).

## A. CORRECTNESS BUGS — silently corrupt decisions/backtests. Fix wave 1 (before Phase 5).

| # | Bug | Where |
|---|---|---|
| A1 | `evidence_history` consumed WITHOUT ttl/session windowing in 3 decision paths: `_m15_trend()` (stale prior-day trend direction), `TemplateClassifier._classify` (BOS scan no date filter), `EntryFSM._targets` energy cap | pipeline.py:209, template.py:90, entry.py:135 |
| A2 | `self.levels` never pruned/session-reset; DEAD/terminal levels block same-price swing re-creation forever (swings dedupe has no state filter) — kills multi-day replay | pipeline.py:68, swings.py:79-85 |
| A3 | INDEX SUBSYSTEM SILENT NO-OP: CLI never passes `index_symbol`; "index" has no confluence weight (⇒ contributes exactly 0); promised counter-index ×0.5 haircut never implemented; `IndexView.phase` can never be ACC/DIST (pipeline's own wyckoff instance never gets `.detect()` — `_last_event` stays None) | cli.py:170, config.json weights, confluence.py, pipeline.py:62-67,115 |
| A4 | `structure._fake` add-only per symbol per RUN — one fake BOS taints `fake_bos_recent` on all future evidence forever (and nothing consumes the flag anyway) | structure.py:33,90 |
| A5 | Wyckoff MARKUP/MARKDOWN continuation evidence zone = current candle range → zones never cluster, sprawl dilutes real clusters (13 spurious stop_too_wide on judas day-2) | wyckoff.py:61-66 |
| A6 | Feed gap spanning >1 M5 bucket: intermediate buckets never evaluated (only last-seen closes) — matters live + gappy data | pipeline.py:77-85 |
| A7 | `Journal.log` ts = wall-clock → replay journals non-reproducible; sim-time (`at`) exists but `ts` misleads | journal.py:49 |
| A8 | Wyckoff `phase()` divides by ATR with None-guard but no 0-guard → flat session crashes | wyckoff.py:97-107 |
| A9 | `m15_trend` is actually last M5 structure event — journal `mults.align` claims M15 confirmation that never happened; no real M15 structure leg runs | pipeline.py:209 (structure runs tf=5m only, config params {}) |

## B. PROMISED-BUT-MISSING MECHANICS (spec/axiom divergences). Wave 2 — design-decided fixes.

| # | Gap | Axiom/spec |
|---|---|---|
| B1 | Targets NEVER EXECUTED — T1/T2/T3 computed+journaled then ignored; exits are R-ladder only. 06 §6 says 33% at T1, 33% at T2, run T3 | manager.py vs entry.py:119 |
| B2 | `wick_tolerance_candles` dead config — stealth stop actually tolerates UNLIMITED wicks (close-confirm only). Decide: keep close-only (stronger) + delete key + update spec, or implement N-candle rule | manager.py:58, config |
| B3 | arm() missing "price within 1×ATR of zone" condition (06 §4) — far zones arm and burn TTL | entry.py:78 |
| B4 | PWH/PWL levels never created (enum + sweep bonus = dead code) — weekly liquidity invisible | liquidity.py |
| B5 | Axiom 16 day-after-TREND size ×0.75 + give-back prior: zero inter-day context exists | — |
| B6 | Axiom 18 gap fade-bias: no gap direction logic anywhere (only cooldown pause) | template.py |
| B7 | Expiry Thursday: `expiry_size_mult` dead config, no expiry calendar | config.py:19 |
| B8 | Portfolio heat / correlated-positions cap promised in 05 config block — absent | gates.py |
| B9 | Obviousness: no ×0.6 tier, applies to all zones not breakout-scoped (06 §8) | confluence.py:157 |
| B10 | PO3 "day" scale (opening-range box) never wired — only "leg"; template classifier substitutes | compression.py:51 |
| B11 | Doc-18 throttles dropped: min-time-between-trades, trades/hour cap | gates.py |
| B12 | OB `_HUNT_MINUTES=105` hardcoded duplicate of config observe_min — drifts if tuned | orderblock.py:33 |
| B13 | Trail stops don't snap off round numbers (entry stops do) | manager.py:101 |
| B14 | Breaker end-to-end unproven (no scenario produces breaker evidence from raw candles) | tests |
| B15 | liquidity `_pool_strength` gives OR levels LOWEST tier — axiom 5 says morning OR pools weight HIGH | liquidity.py:195 |

## C. OPERATIONAL — blocks the real 30-stock dry run. Wave 3 = Phase 5 scope.

| # | Gap | Effort |
|---|---|---|
| C1 | NO REAL DATA: no downloader (plan: yfinance .NS M1 trailing ~30d + NSE bhavcopy D1 warmup), no deps (requests/yfinance) in pyproject | S-M |
| C2 | CandleStore.save() never called → `--auto` unreachable, no warm-start; `trader list` fit hardcoded "-" | S |
| C3 | Phase 5 greenfield: replay engine, metrics (WR/PF/DD, day-clustered, per-detector precision, per-gate skip), `trader replay/report`, learn/calibrate (walk-forward, min-sample gates vs thin-data overfit) | M-L |
| C4 | timestats learning never wired (record/save/load called by nothing) — system cannot learn | S-M |
| C5 | LevelStore built+tested, never wired; no Position/RiskState persistence → crash loses everything | S-M |
| C6 | NSE holiday calendar absent (MarketSpec has no trading-day notion) | S |
| C7 | Logging unconfigured (detector exceptions effectively invisible); no session scheduler/pre-market trigger | S-M |
| C8 | Broker ABC NEVER BUILT (contracts doc promised it) — PaperBroker concrete, call sites direct; Phase-6 "zero changes outside kite.py" is false, budget refactor | M |
| C9 | cage detector = 0 lines (orphaned config weight); options/OI/max-pain fully dark (Phase 6) | L |
| C10 | Memory: levels/_seen sets/evidence unbounded over long runs; FileFeed loads all in RAM | S |
| C11 | Config template not packaged for non-editable installs (`trader init` breaks on real pip install) | S |

## D. Explicitly accepted / LATER
Dead cage weight, po3["day"] key, OI_WALL scaffolding, EventCooldown cross-session self-heal,
classifier 15-min OR fallback, empty learn/replay/risk packages, `_VERDICT_MIN`/stall/pad
constants → config, negative pre-open bucket clamp, all-bonus cap test, `# KNOWN:` markers.

## Fix order
Wave 1 (A1-A9) → Wave 2 (B, each with a design decision recorded) → Wave 3/Phase 5 (C1-C7,C10) →
Phase 6 (C8, C9 + Kite). Waves 1-2 must land before any real-data replay is trusted.
