# Phase 3 Implementation Plan — Zones, Wyckoff, PO3, Templates

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Checkbox per task.

**Goal:** Full detection layer: orderblock/breaker/fvg/volume/wyckoff/compression+PO3/timestats/index detectors, day-template classifier, scenario matrix gate.

**Architecture:** Plugins per contracts (01) + algorithm specs (02) + confluence deep design (06 §3 PO3, §5 compression). Registry/LevelEngine/StockContext from Phase 2 (161 tests green at 65ed90f).

**Tech Stack:** existing app/ package.

## Global Constraints

- COMPACT code (owner mandate): shortest clear form, docstrings ≤6 lines, no boilerplate; detector files target ≤150 LOC
- Decimal via ctx.spec.quantize / spec.tick_size; tz-aware; no lookahead; detectors emit Evidence only, never veto, never raise out
- New LevelKinds must be added to `_SIDE_BY_KIND` in engine/levels.py in the SAME task that introduces their use
- Every detector: idempotent per candle (dedupe), inert when inputs absent, disable-safe
- TDD; commit per task, trailer `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`

---

### Task 1: Phase-2 debt hygiene
**Files:** trader/engine/levels.py, trader/detectors/liquidity.py, tests
Fix: LevelStore.load tolerates corrupt/empty JSON (log + return []); EQ group id collision (two groups same max-born → include zone-mid in id); add EQ growth-mutate test (3rd swing joins group → touches 2→3, zone widens). 
**Commit:** `fix: level store corrupt json + EQ group identity`

### Task 2: orderblock detector
**Files:** trader/detectors/orderblock.py, tests
Per 02-spec: name "orderblock", params {tf "5m", displacement_atr 1.5, lookback 3}. Bullish OB = last bearish candle before ≥1.5×ATR net displacement up within ≤3 candles (mirror bearish). Creates Level kind OB_BULL/OB_BEAR (zone = candle body-to-extreme: bullish OB zone = (low, max(open,close))… use full candle range low..high, simplest), meta via id. birth_time = OB candle ts; hunt-born flag: born within first 105 session minutes (config session-relative: before session_open+105min = 11:00 NSE) ⇒ quality +0.15. Quality = min(1, displacement/ATR×0.27) capped 0.4 + body/ATR×0.3 capped 0.3 + body_pct×0.3. Evidence only when latest close INSIDE an unmitigated aligned OB zone (direction = OB direction), strength = quality, ttl 6, meta {level_id, hunt_born}. Overlapping same-kind OBs: keep higher quality (dedupe). Mitigation handled by LevelEngine (2×TESTED→MITIGATED already for OB kinds).
**Commit:** `feat: orderblock detector with hunt-born flag`

### Task 3: breaker detector
**Files:** trader/detectors/breaker.py, tests
name "breaker", params {tf "5m"}. Watches ctx.levels for OB/SWING/OR kinds whose state == INVERTED. On latest close entering inverted zone from the new side ⇒ Evidence direction = post-inversion side (HIGH-kind inverted ⇒ was resistance, now support ⇒ LONG when price above retesting down INTO zone... define: level side flips after inversion — direction = opposite of original kind side), strength 0.85, ttl 12, meta {level_id, "event":"BREAKER_RETEST"}. Dedupe per (level_id, retest candle ts); max 1/candle/level.
**Commit:** `feat: breaker detector`

### Task 4: fvg detector (FVG/iFVG/BPR/CE)
**Files:** trader/detectors/fvg.py, tests
name "fvg", params {tf "5m", min_gap_atr 0.3}. 3-candle gap: bullish c3.low > c1.high (zone = c1.high..c3.low), ≥0.3×ATR. Creates FVG_BULL/FVG_BEAR Levels. Evidence cases: price retraces into gap and holds CE (50% mid) ⇒ direction = gap direction, strength 0.7, ttl 12; gap fully filled ⇒ mark Level DEAD (via record_state); iFVG: FVG level whose state == INVERTED retested ⇒ strength 0.75 opposite direction; BPR: overlapping opposing FVG zones ⇒ single Evidence strength 0.8 in later-gap direction, ttl 12. Dedupe per level per candle.
**Commit:** `feat: fvg detector with inversion and bpr`

### Task 5: volume/VSA detector
**Files:** trader/detectors/volume.py, tests
name "volume", params {tf "5m", sma 20, z_hi 1.5}. Per-candle classification: climax (range>2×ATR ∧ vol>2×SMA), stopping_volume (bearish candle, vol>1.5×SMA, lower_wick≥50% range), no_demand (bullish, vol<0.7×SMA), absorption (vol z>1.5 ∧ body<0.3×ATR). Emits confirming Evidence 0.3 ONLY when co-located: classification zone overlaps zone of any evidence in ctx.evidence_history from another detector within last 6 candles; direction = that evidence's direction. Else no emission (pure booster).
**Commit:** `feat: vsa volume detector`

### Task 6: wyckoff detector
**Files:** trader/detectors/wyckoff.py, tests
name "wyckoff", params {tf "5m", window 40, range_atr 3.0}. Range: (max-min of window closes... use highs/lows) < 3×ATR ⇒ in-range. Events (volume-based, needs volume detector NOT — computes own vol SMA): spring = sweep of range low (wick below, close upper half of candle, vol>1.5×SMA) ⇒ Evidence LONG 0.8 ttl 24 meta {"event":"SPRING"}; upthrust mirror SHORT. Phase output in meta of a NEUTRAL heartbeat evidence? NO — phase exposed via detector method `phase(ctx) -> tuple[str, float]` (ACCUMULATION/DISTRIBUTION/MARKUP/MARKDOWN/UNCLEAR, confidence) callable by gates/template; also emits phase-aligned continuation Evidence 0.5 when in MARKUP/MARKDOWN (direction along phase). htf_phase: same classifier over D1 candles (needs ≥10 D1 candles else UNCLEAR).
**Commit:** `feat: wyckoff phase detector`

### Task 7: compression + PO3 FSM
**Files:** trader/engine/po3.py, trader/detectors/compression.py, tests
Per 06 §3/§5. PO3FSM class (engine, not detector): states ACCUMULATION/MANIPULATION/DISTRIBUTION/IDLE per (symbol, scale); fed each closed tf candle + levels; box = compression cluster or opening range (scale "day"). Transitions per 06 §3 (box edge swept ⇒ MANIPULATION recording side; displacement ≥1.5×ATR away + BOS evidence present ⇒ DISTRIBUTION with true_direction; box break w/ volume expansion no reclaim ⇒ IDLE/trend handoff). compression detector: name "compression", params {tf "5m", window 12}; contraction = mean(range last4)/mean(range first4) < 0.6 ∧ body-overlap of last 6 ∧ vol slope < 0 (linreg) ∧ NR7/inside cluster ≥2 of last 4 ⇒ score ≥0.7 box confirmed ⇒ registers box with FSM via ctx (FSM instance lives in ctx.day.po3: add field to DayState). Evidence: FSM DISTRIBUTION-confirm ⇒ 0.85 true_direction ttl 24; box-on-level (zone overlaps OB/FVG hunt-born level) post-DISTRIBUTION ⇒ 0.75; energy = box_height×2.5 in meta.
**Commit:** `feat: compression detector and po3 fsm`

### Task 8: timestats detector
**Files:** trader/detectors/timestats.py, tests
name "timestats", params {bucket_min 5, prior_weight 20}. Buckets session-relative (spec-aware count = session_minutes/5). Cold priors (NSE mapping by minutes-from-open): 0–75 danger 0.8; 75–105 0.5; 105–225 0.3; 225–285 0.6; 285+ 0.8; non-NSE sessions: flat 0.5 prior. Learns: `record(bucket, swept: bool)` counts sweep events (wired later by learn phase; detector exposes counts dict + persists JSON root/timestats/<symbol>.json via injectable path param... keep in-memory + save/load methods, wiring later). Evidence each candle: NEUTRAL, strength = 1 − danger(current bucket) where danger = Laplace-smoothed blend (prior×prior_weight + observed_sweeps) / (prior_weight + observations). ttl 1.
**Commit:** `feat: timestats detector with learned buckets`

### Task 9: index context detector
**Files:** trader/detectors/index.py, trader/engine/context.py (add field), tests
Add StockContext.index: "IndexView | None" = None — dataclass IndexView {trend: Direction, phase: str, strength: float} (computed upstream by orchestrator running structure+wyckoff on index symbol; Phase 4 wires it). Detector name "index", requires {"index"} (requires-mechanism: satisfied iff ctx.index is not None — extend base.run_all requires check: "options_chain"→ctx.options, "index"→ctx.index; table-driven). Evidence: ctx.index.trend ≠ NEUTRAL ⇒ NEUTRAL-direction context evidence strength = index.strength×0.5, meta {trend, phase}; confluence layer (Phase 4) applies ×0.5 haircut on counter-index entries — detector just surfaces.
**Commit:** `feat: index context detector`

### Task 10: template classifier + scenario matrix gate
**Files:** trader/engine/template.py, trader/feed/mock.py (add range_pin + double_trap generators), tests/test_phase3_scenarios.py
TemplateClassifier(spec, params {lock_minute 135}): fed per closed M5 candle + levels + evidence; state per 00-spec table: TRAP_REVERSAL (one OR/PD edge swept + reclaimed + CHoCH present), TREND (open drives, no edge reclaim, BOS ≥2 same direction, pullbacks shallow), RANGE_PIN (no edge swept by lock time, range < 1.5×ATR... define: day range < 2×ATR(D1-proxy: sum M5 ATR)/simplify: no sweep + no 2×BOS), DOUBLE_TRAP (both OR edges swept), UNCLASSIFIED default; locks at session_open+135min (12:30 NSE... plan says 11:30 = +135 ⇒ correct 09:15+135=11:30). DayState.template updated by classifier. New scenarios: range_pin(symbol,date,open) — narrow chop both OR edges hold; double_trap — sweep OR low ~min 30 reclaim, sweep OR high ~min 150 reclaim, close mid; truth keys template. Gate test: 4 scenarios × classifier locks correct template; judas fires OB evidence + wyckoff spring ± compression sanity (loose: ≥1 evidence each from orderblock/wyckoff on judas; fvg fires on trend day gap-ish… only assert fvg emits SOMEWHERE across scenarios or skip — keep gate assertions per-detector minimal but non-vacuous: each new detector emits ≥1 evidence on at least one scenario, and template lock correct on all 4); isolation re-proof with full detector set (disable breaker ⇒ others identical).
**Commit:** `feat: day template classifier` + `test: phase3 scenario matrix gate`

---
Self-review: PO3 FSM in ctx.day requires DayState mutable — it is (dataclass, non-frozen). Registry order doc: level-writers first — orderblock/fvg write levels: order = swings, liquidity, orderblock, fvg, structure, sweep, breaker, wyckoff, volume, compression, timestats, index. Update shipped config enabled list in Task 10 (all implemented then; registry crash-safety test already exists).
