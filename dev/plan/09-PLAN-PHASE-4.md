# Phase 4 Implementation Plan — Decision Engine, Risk, Paper Execution

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development.

**Goal:** Trades happen (paper): confluence scoring → gates → entry FSM → paper fills → position management → journal; orchestrator assembles per-symbol pipelines; CLI `watch`/`status` live.

**Architecture:** 06-CONFLUENCE-ENGINE-DEEP.md is the authoritative spec (§1–§10). Phase-3 must-know list (ledger bottom): registry+classifier PER SYMBOL, fresh DayState per session, evidence consumers self-window, LevelEngine same-tf as detectors, volume/compression one-tick lag accepted.

## Global Constraints
- COMPACT code; Decimal for prices/money (convert config floats at boundary — capital/costs become Decimal in engine); tz-aware; no lookahead; single pipeline (live=replay)
- Deterministic: no wall-clock reads inside pipeline — ctx.now injected
- TDD; commit per task + trailer `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`

---

### Task 1: ConfluenceEngine (spatial zones + alignment + context)
**Files:** trader/engine/confluence.py, tests
Per 06 §1–2. `ConfluenceEngine(settings)`; `score(ctx, evidence_window) -> list[ScoredZone]`.
- Input: live evidence (self-windowed: evidence whose ts + ttl_candles×tf ≥ ctx.now; ttl 0 = current candle only)
- Layer 1: cluster by zone overlap (merge if zones overlap or gap ≤ 0.25×ATR); same-detector dupes keep best strength; opposing directions subtract at 0.8×; NEUTRAL-direction evidence adds 0.5×weight×strength to BOTH sides' context pool (time/liquidity/index are context, not direction)
- ScoredZone {zone, direction, members list[(detector,event,strength)], distinct: int, raw: float}
  raw = Σ enabled_weight(detector)×strength (weightless detectors: volume adds flat +3 booster if member; swings never emits)
- Layer 2 alignment multiplier: wyckoff htf_phase (D1): MARKDOWN blocks LONG zones (mult 0) / MARKUP blocks SHORT; H1-proxy = wyckoff phase(M15... use phase(ctx) at M15 param? simplify binding: htf veto only from htf_phase; bias mult: structure trend on M15 evidence agreement — if last CHoCH/BOS direction (M15) opposes zone ⇒ 0, agrees ⇒ 1.0, none ⇒ 0.8
- Layer 3: time mult = latest timestats evidence strength (default 0.5 if absent); template mult 1.0 if zone direction matches template play (TRAP_REVERSAL: reversal dir = away from swept edge; TREND: BOS dir) / 0.5 off-template / 0.0 UNCLASSIFIED; obviousness: zone containing ROUND or EQ level with touches≥3 NOT yet swept ⇒ ×0.85, if that level SWEPT+RECLAIMED ⇒ ×1.15
- final = raw × align × time × template × obviousness, capped 100. Zones with distinct < min_zone_detectors(3) marked unarmable (final forced 0)
**Commit:** `feat: spatial confluence engine`

### Task 2: Gates
**Files:** trader/engine/gates.py, tests
Verdict(allow, gate, reason). Gate ABC + GateChain(settings, state). Gates (all read ctx + optional plan + RiskState):
- TimeWindowGate: now within [session_open+observe_min(105), no_entry_after] (config times)
- TemplateGate: ctx.day.template not UNCLASSIFIED
- RegimeVetoGate: wyckoff htf_phase MARKDOWN ⇒ no LONG, MARKUP ⇒ no SHORT (redundant w/ confluence mult — cheap double lock)
- EventCooldownGate: latest closed candle range > big_candle_atr(3.0)×ATR or session-open gap vs prev close > 1×ATR ⇒ block next cooldown_candles(6)
- ChaseGate: plan.entry zone — latest close beyond zone far edge + chase_tolerance_atr(0.1)×ATR ⇒ block
- RiskBudgetGate: RiskState (dataclass: trades_today, per-symbol counts, consecutive_losses, daily_pnl_R, locked) — max_trades_day, max_per_stock, consecutive_loss_stop, daily_loss_pct breach, daily_profit_lock_R hit ⇒ block
**Commit:** `feat: decision gates`

### Task 3: TradePlan + EntryFSM + targets
**Files:** trader/engine/entry.py, tests
Per 06 §4/§6. `EntryFSM(settings, spec)` per symbol. States IDLE/ARMED/FILLED-handoff.
- arm(zone: ScoredZone, ctx): requires final ≥ threshold + gates pass + price within 1×ATR of zone. Builds draft TradePlan: SL = zone far edge ± (trap extreme if a SWEPT level inside zone else 0) ± atr_buffer×ATR, snapped off round numbers (shift by round_offset_ticks if within 2 ticks of a ROUND level zone); risk_pts = |entry_mid − SL|; skip+journal if risk_pts > max_stop_atr(1.2)×ATR
- Targets: opposing liquidity map — ACTIVE/TESTED levels + opposing-direction ScoredZones beyond entry: T1 = nearest ≥1.5R (none ⇒ skip "no_room"), T2 next, T3 = external (PDH/PDL kind) capped by compression energy meta if present
- step(ctx): ARMED → TRIGGER when latest closed M5 inside zone AND (rejection wick ≥60% range off far side | CHoCH evidence this candle inside zone | volume evidence this candle) ⇒ returns TradePlan (FILL at next open handled by broker). ARMED → disarm on: zone violated (close beyond far edge + wick tolerance), ttl expiry arm_ttl(12) candles, OB level in zone breaks (state DEAD/INVERTED)
- qty: min(user max_qty, floor(risk_budget / risk_pts)) where risk_budget = capital × per_trade_pct/100; qty 0 ⇒ skip
**Commit:** `feat: entry fsm with stealth stop planning`

### Task 4: PaperBroker + PositionManager
**Files:** trader/execution/paper.py, trader/execution/manager.py, tests
- PaperBroker(settings): fill(plan, next_candle) → Fill at next_candle.open ± half_spread_bps ± slippage_bps (direction-adverse), costs = brokerage_flat + stt+exchange pct on turnover (Decimal). exit fills same model.
- Position {plan, fill, remaining_qty, realized_pnl, stop, status, partials_done}
- PositionManager(settings, spec).on_candle(pos, ctx) → list[Action] per 06 §7: stealth stop = close beyond stop (+wick tolerance 1 candle: single wick-through without close-beyond survives, journaled "hunt_survived"); ≥1R ⇒ BREAKEVEN move + PARTIAL 33%; ≥2R ⇒ PARTIAL 33% + trail M5 swings (last confirmed SWING_L−0.1×ATR for LONG); ≥3R ⇒ trail M15 swings; ratchet only; counter-zone: opposing ScoredZone final ≥ threshold ⇒ EXIT_COUNTER; stall: <0.5R after stall_candles(18) ⇒ EXIT_STALL; squareoff time ⇒ EXIT_EOD. Never widen: assert + test.
**Commit:** `feat: paper broker and position manager`

### Task 5: Orchestrator (the loop)
**Files:** trader/engine/pipeline.py, tests
`SymbolPipeline(symbol, settings, store, journal)`: owns levels list, LevelEngine, DetectorRegistry (own instance), TemplateClassifier, ConfluenceEngine, EntryFSM, DayState (reset on new session), evidence_history (pruned > 200), PositionManager+positions. `on_m1(candle)`: store.add; if M5 boundary crossed ⇒ closed-M5 flow: view→ctx (inject index view if provided)→LevelEngine.update→registry.run_all→extend history→classifier.update→confluence.score→gates→fsm.step→broker fill→manager.on_candle→journal every verdict/trade/skip (kind verdict/trade_open/trade_close/skip with score decomposition). `Orchestrator(settings, feed, stocks)`: pipelines per symbol; index pipeline (NIFTY) first each tick → IndexView for others; RiskState shared across pipelines; run(feed) loop consuming feed.events().
**Commit:** `feat: symbol pipeline orchestrator`

### Task 6: Scanner + CLI wiring
**Files:** trader/engine/scanner.py, trader/cli.py (extend), tests
- Scanner: fit(symbol, store) = cleanliness .25 (spread proxy: mean |c−o|/range?, gap freq 20d, swing-size stddev, ATR stability) + energy .20 (ATR% in 1–4% band, D1 compression) + liquidity .20 (avg volume × price vs qty notional) + setup .20 (untapped pools within 2×ATR, EQ levels) + context .15 (skip: index/日after-trend Phase 5 learning) — components 0–1, weighted sum 0–100. Needs prev days data; missing ⇒ component 0.5 neutral.
- CLI: `trader watch 1 4 7 --capital N --max-qty Q [--feed file --data DIR | --feed mock] [--auto K]` — builds Orchestrator, runs feed to exhaustion (file/mock) with rich live table (symbol, template, phase, top zone score, verdict, position, PnL); `trader list` shows fit scores using cached data if store has any; `trader journal --day YYYY-MM-DD` pretty-prints; `trader status` reads last session journal summary.
**Commit:** `feat: scanner and watch cli`

### Task 7: Phase-4 gate — trades on scripted days
**Files:** trader/feed/mock.py (add stop_hunt_survive + grind context helper), tests/test_phase4_e2e.py
- New scenario stop_hunt_survive(symbol,date,open): judas-like LONG setup post-11:00, then ONE M5 wicks through the (predictable) stop zone without closing beyond, reclaims, rallies to T1+. Truth: hunt_minute.
- E2E assertions (full Orchestrator on mock feed, real config template + capital 100000 max_qty 50):
  1. judas: ≥0 trades but IF trade opens: direction LONG, entry ts ≥ 11:00, SL below sweep extreme, journal has verdict entries with score decomposition; assert at least one ARMED zone existed (armable zone score ≥ threshold logged) — trade itself may legitimately not trigger; tune scenario only if NO zone ever arms (report offsets)
  2. range_pin: zero trades, ≥1 skip/verdict logged
  3. double_trap: zero trades before second sweep reclaim
  4. stop_hunt_survive: position survives hunt candle (journal hunt_survived), exits ≥ 1R total realized
  5. RiskState: force 2 consecutive losses via scenario pair ⇒ third arm blocked by gate (unit-level acceptable)
  6. EOD: any open position squared off by 15:10, journal trade_close reason EOD
**Commit:** `test: phase4 end-to-end paper trades`

Self-review notes: config floats→Decimal at engine boundary (capital, costs); evidence pruning cap 200 keeps memory flat; index pipeline ordering documented; CLI keeps typer thin — logic in engine.
