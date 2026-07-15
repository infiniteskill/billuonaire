# Phase 2 Implementation Plan — Levels, Structure, Liquidity, Sweeps

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Checkbox tracking per task.

**Goal:** Working detector layer: Level state machine, DetectorRegistry with proof of detachability, swings/liquidity/structure/sweep detectors — all validated against ScenarioFeed ground truth.

**Architecture:** Detectors are plugins per `01-ARCHITECTURE-CONTRACTS.md`; algorithms per `02-DETECTOR-SPECS.md` (authoritative for thresholds). Evidence-only output; never veto; registry catches exceptions.

**Tech Stack:** Python 3.11+, existing app/ package (46 tests green at 819d3b0).

## Global Constraints

- All prices Decimal via `tick()`; tz-aware IST; no network; no lookahead (detectors read only StockContext views)
- Detectors NEVER raise out of registry.run_all; never return None (empty list)
- Every detector must pass the isolation proof: disabling it changes NOTHING in other detectors' output
- TDD per task; commit per task with trailer `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`
- Ground-truth tests assert scripted scenario indexes (tolerances stated per task), not "looks right"

---

### Task 1: StockContext + Detector base + Registry (+ isolation harness)

**Files:** Create `trader/engine/context.py`, `trader/detectors/base.py`, `tests/engine/test_context.py`, `tests/detectors/test_registry.py`

**Interfaces (produces):**
```python
# engine/context.py
@dataclass
class DayState:            # minimal this phase; grows later
    session_date: date
    template: str = "UNCLASSIFIED"
@dataclass
class StockContext:
    symbol: str
    now: datetime
    candles: CandleView                    # from CandleStore.view()
    levels: list[Level]                    # live level objects (mutable, shared)
    evidence_history: list[Evidence]
    day: DayState
    options: object | None = None
    def atr(self, tf: Timeframe, period: int = 14) -> Decimal | None
        # SMA of true ranges over closed candles; None if < period+1 candles
# detectors/base.py
class Detector(ABC):
    name: str; requires: frozenset[str] = frozenset()
    def __init__(self, params: dict): self.params = params
    @abstractmethod
    def detect(self, ctx: StockContext) -> list[Evidence]
class DetectorRegistry:
    def __init__(self, settings: Settings)   # builds enabled detectors from a
        # name->class REGISTRY dict (module-level, populated by each detector module)
    def run_all(self, ctx: StockContext) -> list[Evidence]
        # order = config enabled order; try/except per detector: log via logging,
        # append nothing on failure, continue; detectors with unmet requires skipped
def register(cls) -> cls                      # decorator adding class to REGISTRY by cls.name
```

**Tests (write these + registry behavior):** ATR correctness on hand-built candles (known TR values); ATR None when insufficient; registry instantiates only enabled; broken detector (raises) isolated — others still run; `requires={"options_chain"}` detector skipped when ctx.options None; run_all order deterministic.

**Commit:** `feat: stock context, detector base and registry`

---

### Task 2: Level state machine transitions + LevelStore

**Files:** Create `trader/engine/levels.py`, `tests/engine/test_levels.py`

**Interfaces (produces):**
```python
class LevelEngine:
    def __init__(self, params: dict)      # tolerances: touch_atr=0.1, etc.
    def update(self, levels: list[Level], candle: Candle, atr: Decimal | None) -> list[LevelTransition]
        # applies transition rules to every ACTIVE/TESTED/SWEPT level for one closed candle
@dataclass(frozen=True)
class LevelTransition:
    level_id: str; old: LevelState; new: LevelState; ts: datetime
```
Transition rules (authoritative here):
- ACTIVE→TESTED: candle touches zone (low<=zone_hi and high>=zone_lo) but close stays on origin side; touches += 1
- ACTIVE/TESTED→SWEPT: wick trades through zone (beyond far edge) but close back on origin side ⇒ swept-and-rejected; record sweep extreme in level state_history meta... keep simple: SWEPT means wick-through-close-back
- ACTIVE/TESTED→DEAD: close fully beyond far edge + next candle doesn't reclaim (2-candle confirm) — level broken for real. Implement as: close beyond ⇒ mark PENDING_BREAK in engine-internal memory; next closed candle also beyond ⇒ DEAD; reclaimed instead ⇒ SWEPT→RECLAIMED path
- SWEPT→RECLAIMED: within `reclaim_candles=3` closed candles, close back within/beyond original side of zone
- RECLAIMED→INVERTED: price later closes through zone from the OTHER side and holds 1 candle (breaker seed)
- OB kinds: TESTED twice ⇒ MITIGATED (dead for entries)
LevelStore: persist levels to JSON under root (survive restarts): `save(symbol)`, `load(symbol)` — Decimal as str, enums by name.

**Tests:** hand-built candle sequences driving every transition path (happy + 2-candle break confirm + reclaim window expiry); OB double-touch mitigation; JSON roundtrip.

**Commit:** `feat: level state machine and level store`

---

### Task 3: swings detector

**Files:** Create `trader/detectors/swings.py`, `tests/detectors/test_swings.py`

Spec per 02-DETECTOR-SPECS: strength N=3 strictly lower highs each side (>= disqualifies); writes SWING_H/SWING_L Levels (via returned new-levels mechanism: detector returns Evidence list BUT swing creation is a side-channel — resolve: detectors may append to ctx.levels directly; document + test). Emits NO Evidence (infrastructure). Runs on M5 and M15. Zone width = swing candle high±0.05% or exact high/low ± 1 tick — use exact extreme ± 1 tick. Dedupe: same extreme within tolerance ⇒ no duplicate level.

**Tests:** scripted candles with known swing at index k (confirmable only at k+3 — no-lookahead assertion: swing must NOT exist in levels before k+3rd candle processed); `>=` disqualification case; dedupe.

**Commit:** `feat: swings detector`

---

### Task 4: liquidity detector

**Files:** Create `trader/detectors/liquidity.py`, `tests/detectors/test_liquidity.py`

Spec: creates PDH/PDL (prev session extremes), OPEN_RANGE_H/L (09:15–09:30), ROUND (nearest 50/100/500 within 2% of current price), EQH/EQL (≥2 swing extremes within 0.1%; strength = min(touches/5,1)×0.7 + recency×0.3, 48h decay). Emits proximity Evidence: nearest untapped (ACTIVE/TESTED) pool within 1×ATR above/below → NEUTRAL-direction draw hint, strength = pool_strength × 0.5, ttl 12. Levels created once per day (PDH/PDL/OR) or on swing updates (EQH/EQL); idempotent per candle (no duplicates).

**Tests:** PDH/PDL correct from prev_day view; OR from first 15 min; EQH from two equal swing highs within 0.1% (uses swing levels present in ctx.levels); round numbers; proximity evidence when price within 1 ATR of untapped pool, absent when pool SWEPT.

**Commit:** `feat: liquidity detector`

---

### Task 5: structure detector (BOS/CHoCH + fake-BOS memory)

**Files:** Create `trader/detectors/structure.py`, `tests/detectors/test_structure.py`

Spec: consumes SWING levels from ctx.levels (M5/M15 per own tf param). Trend from last 4 swings: HH+HL bullish, LH+LL bearish, else ranging. BOS = close beyond most recent same-direction swing extreme in trend direction ⇒ Evidence strength 0.6 trend-direction ttl 12. CHoCH = close beyond most recent opposite swing ⇒ Evidence direction=new, strength 0.8 if a SWEPT level transition occurred within last 6 closed candles (trap chain — read from ctx.levels state_history), else 0.5, ttl 24. Fake-BOS memory: internal per-symbol record of BOS that closed back beyond within 5 candles ⇒ meta flag on future evidence (`fake_bos_recent: true`). Stateless across restarts is acceptable this phase (document).

**Tests:** hand-built swing/candle sequences: bullish BOS fires exactly on breaking candle; CHoCH flips direction; CHoCH strength 0.8 with recent sweep vs 0.5 without; fake-BOS recorded.

**Commit:** `feat: structure detector with BOS/CHoCH and fake-BOS memory`

---

### Task 6: sweep detector (+ trap chain depth)

**Files:** Create `trader/detectors/sweep.py`, `tests/detectors/test_sweep.py`

Spec: reads LevelTransitions of this candle — resolve mechanism: sweep detector re-checks levels whose state==SWEPT with last state_history ts == current candle ts. Quality: +0.4 close correct side (implied by SWEPT), +0.25×pool strength (liquidity kinds carry strength in meta; default 0.5), +0.2 if touches>=3, +0.15 kind in {PDH,PDL,PWH,PWL}, +0.1 reversal within <=3 candles (requires RECLAIMED — else omit), cap 1.0. Direction = away from swept side. ttl 18. Trap chain: meta.chain_depth = 1 + chain_depth of any sweep evidence in evidence_history whose zone contains this level's zone origin within 20 candles (default 0 → depth 1); depth 2 ⇒ strength +0.1 (cap 1.0).

**Tests:** PDL sweep with reclaim scores per formula (exact arithmetic asserted); non-reclaimed sweep lower score; chain depth 2 bonus; direction correctness both sides.

**Commit:** `feat: sweep detector with trap chains`

---

### Task 7: Ground-truth wiring + isolation proof (phase exit)

**Files:** Create `tests/test_phase2_scenarios.py`

Harness (in-test): pump judas_reversal("X", 2026-07-15, 100.0) M1s into CandleStore; after each closed M5 candle build StockContext (view at that M5 close time, shared levels list, evidence_history accumulating, LevelEngine.update before registry.run_all) and run registry (settings from shipped config template but detectors limited to phase-2 set: swings, liquidity, structure, sweep).
Assertions:
1. Sweep Evidence fires: some sweep evidence exists with zone containing the scenario truth `reversal_from` price, at an M5 candle whose window covers truth `sweep_low_minute` ± 3 candles (sweep of OPEN_RANGE_L or PDL-equivalent — scenario has no prev day, so the swept level will be OPEN_RANGE_L or an early SWING_L; assert kind ∈ {OPEN_RANGE_L, SWING_L})
2. CHoCH LONG Evidence fires within 12 M5 candles after the sweep evidence
3. trend_day: at least one BOS LONG evidence, and NO sweep evidence with strength > 0.6 (no strong sweep-reversal on a trend day)
4. Isolation proof: run judas harness twice — once all 4 detectors, once with structure disabled in settings; assert swings/liquidity/sweep evidence streams byte-identical (serialize + compare), and enabled_weights renormalize (sum 100 over 3 — note swings emits no evidence but liquidity/sweep weights renormalize; use weights from config for the enabled set)
5. No-lookahead spot check: at M5 index i, no evidence carries ts > view.now

**Commit:** `test: phase2 scenario ground truth and detector isolation`

---

## Self-review notes (resolved inline)
- Detector→levels write access: detectors MAY mutate ctx.levels (append new / LevelEngine mutates states); StockContext documents levels as the shared live list. Confluence-layer purity comes later via evidence-only reads.
- Swings emit no Evidence — isolation test compares levels created too.
- PWH/PWL omitted this phase (needs multi-week fixture data); EQH via swing levels suffices for judas scenario.
