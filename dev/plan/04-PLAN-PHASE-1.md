# Phase 1 Implementation Plan — Skeleton & Data Spine

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Working package skeleton: models, config, candle store with multi-TF aggregation and no-lookahead views, MockFeed scenario replay, FileFeed, journal, CLI `init`/`list`.

**Architecture:** Modular monolith in `app/` per `01-ARCHITECTURE-CONTRACTS.md`. No market logic this phase — pure data spine, fully tested.

**Tech Stack:** Python 3.11+, typer, rich, pydantic v2, pandas, pyarrow, pytest.

## Global Constraints

- All prices `Decimal`, quantized to `Decimal("0.05")` (NSE tick), ROUND_HALF_UP. Never float for money.
- All timestamps timezone-aware IST (`zoneinfo.ZoneInfo("Asia/Kolkata")`).
- No network access anywhere in Phase 1 (including tests).
- `git init` in `app/` at Task 1; commit after every task.
- Views must make future data unreachable — no method may return candles with `ts > ctx now`.

---

### Task 1: Package scaffold

**Files:**
- Create: `app/pyproject.toml`, `app/trader/__init__.py`, `app/tests/__init__.py`, subpackage `__init__.py` files for `models feed store engine detectors risk execution replay learn`

**Interfaces:**
- Produces: importable `trader` package, `pytest` runs.

- [ ] **Step 1: Write pyproject**

```toml
[project]
name = "trader"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["typer>=0.12", "rich>=13", "pydantic>=2.7", "pandas>=2.2", "pyarrow>=16"]

[project.optional-dependencies]
dev = ["pytest>=8"]

[project.scripts]
trader = "trader.cli:app"

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["trader*"]
```

- [ ] **Step 2: Create empty `__init__.py` in every package dir listed above**
- [ ] **Step 3: Install editable + verify**

Run: `cd /home/doom/Public/PROJECT/2026/trader/app && python -m venv .venv && .venv/bin/pip install -e '.[dev]' && .venv/bin/pytest`
Expected: `no tests ran`

- [ ] **Step 4: Commit**

```bash
git init && git add -A && git commit -m "chore: package scaffold"
```

---

### Task 2: Price + Candle model

**Files:**
- Create: `app/trader/models/candle.py`
- Test: `app/tests/models/test_candle.py`

**Interfaces:**
- Produces: `tick(x) -> Decimal` (quantizer), `Timeframe` enum (`M1,M5,M15,H1,D1` with `.minutes`), frozen `Candle` dataclass with properties `body, range, upper_wick, lower_wick, is_bullish` and `__post_init__` OHLC validation raising `ValueError`.

- [ ] **Step 1: Write the failing tests**

```python
# app/tests/models/test_candle.py
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo
import pytest
from trader.models.candle import Candle, Timeframe, tick

IST = ZoneInfo("Asia/Kolkata")

def c(o, h, l, cl, v=1000):
    return Candle("RELIANCE", Timeframe.M5, datetime(2026, 7, 15, 9, 15, tzinfo=IST),
                  tick(o), tick(h), tick(l), tick(cl), v)

def test_tick_quantizes_to_nse_tick():
    assert tick("100.07") == Decimal("100.05")
    assert tick("100.08") == Decimal("100.10")

def test_properties():
    x = c("100", "110", "95", "105")
    assert x.body == Decimal("5.00") and x.range == Decimal("15.00")
    assert x.upper_wick == Decimal("5.00") and x.lower_wick == Decimal("5.00")
    assert x.is_bullish

def test_invalid_ohlc_rejected():
    with pytest.raises(ValueError):
        c("100", "99", "95", "98")     # high < open
    with pytest.raises(ValueError):
        c("100", "110", "101", "105")  # low > open

def test_naive_timestamp_rejected():
    with pytest.raises(ValueError):
        Candle("X", Timeframe.M5, datetime(2026, 7, 15, 9, 15),
               tick(1), tick(1), tick(1), tick(1), 0)

def test_timeframe_minutes():
    assert Timeframe.M5.minutes == 5 and Timeframe.D1.minutes == 375
```

- [ ] **Step 2: Run to verify fail** — `pytest tests/models/test_candle.py -v` → ImportError
- [ ] **Step 3: Implement**

```python
# app/trader/models/candle.py
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum

TICK = Decimal("0.05")

def tick(value) -> Decimal:
    return Decimal(str(value)).quantize(TICK, rounding=ROUND_HALF_UP)

class Timeframe(Enum):
    M1 = "1m"; M5 = "5m"; M15 = "15m"; H1 = "1h"; D1 = "1d"

    @property
    def minutes(self) -> int:
        return {"1m": 1, "5m": 5, "15m": 15, "1h": 60, "1d": 375}[self.value]

@dataclass(frozen=True)
class Candle:
    symbol: str
    tf: Timeframe
    ts: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int

    def __post_init__(self):
        if self.ts.tzinfo is None:
            raise ValueError("candle timestamp must be timezone-aware")
        if not (self.high >= max(self.open, self.close)
                and self.low <= min(self.open, self.close)
                and self.high >= self.low):
            raise ValueError(f"invalid OHLC {self.open}/{self.high}/{self.low}/{self.close}")

    @property
    def body(self) -> Decimal: return abs(self.close - self.open)
    @property
    def range(self) -> Decimal: return self.high - self.low
    @property
    def upper_wick(self) -> Decimal: return self.high - max(self.open, self.close)
    @property
    def lower_wick(self) -> Decimal: return min(self.open, self.close) - self.low
    @property
    def is_bullish(self) -> bool: return self.close > self.open
```

- [ ] **Step 4: Run to verify pass** — `pytest tests/models/test_candle.py -v` → 5 PASS
- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: candle model with NSE tick precision"`

---

### Task 3: Evidence + Level models

**Files:**
- Create: `app/trader/models/evidence.py`, `app/trader/models/level.py`
- Test: `app/tests/models/test_evidence_level.py`

**Interfaces:**
- Produces: `Direction` enum (LONG/SHORT/NEUTRAL), frozen `Evidence` per contract doc; `LevelKind`, `LevelState` enums, `Level` dataclass with `record_state(ts, state)` appending to `state_history` and setting `.state`. (Transition *rules* come in Phase 2 — here only the data shape.)

- [ ] **Step 1: Failing tests**

```python
# app/tests/models/test_evidence_level.py
from datetime import datetime
from zoneinfo import ZoneInfo
from trader.models.candle import tick
from trader.models.evidence import Evidence, Direction
from trader.models.level import Level, LevelKind, LevelState

IST = ZoneInfo("Asia/Kolkata")
TS = datetime(2026, 7, 15, 10, 0, tzinfo=IST)

def test_evidence_is_frozen_and_shaped():
    e = Evidence("sweep", Direction.LONG, 0.8, (tick(99), tick(100)), TS, 18, {"pool": "PDL"})
    assert e.detector == "sweep" and e.strength == 0.8
    assert e.zone[0] < e.zone[1]

def test_level_state_recording():
    lv = Level(id="RELIANCE-PDL-20260715", symbol="RELIANCE", kind=LevelKind.PDL,
               zone=(tick("98.95"), tick("99.05")), born=TS, tf=None)
    assert lv.state == LevelState.ACTIVE and lv.touches == 0
    lv.record_state(TS, LevelState.SWEPT)
    assert lv.state == LevelState.SWEPT
    assert lv.state_history == [(TS, LevelState.SWEPT)]
```

- [ ] **Step 2: Verify fail** — ImportError
- [ ] **Step 3: Implement**

```python
# app/trader/models/evidence.py
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum

class Direction(Enum):
    LONG = 1; SHORT = -1; NEUTRAL = 0

@dataclass(frozen=True)
class Evidence:
    detector: str
    direction: Direction
    strength: float
    zone: tuple[Decimal, Decimal]
    ts: datetime
    ttl_candles: int
    meta: dict = field(default_factory=dict)
```

```python
# app/trader/models/level.py
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum, auto
from trader.models.candle import Timeframe

class LevelKind(Enum):
    PDH = auto(); PDL = auto(); PWH = auto(); PWL = auto()
    EQH = auto(); EQL = auto(); SWING_H = auto(); SWING_L = auto()
    OB_BULL = auto(); OB_BEAR = auto(); FVG_BULL = auto(); FVG_BEAR = auto()
    ROUND = auto(); OI_WALL_CE = auto(); OI_WALL_PE = auto()
    OPEN_RANGE_H = auto(); OPEN_RANGE_L = auto()

class LevelState(Enum):
    ACTIVE = auto(); TESTED = auto(); SWEPT = auto(); RECLAIMED = auto()
    INVERTED = auto(); MITIGATED = auto(); DEAD = auto()

@dataclass
class Level:
    id: str
    symbol: str
    kind: LevelKind
    zone: tuple[Decimal, Decimal]
    born: datetime
    tf: Timeframe | None
    state: LevelState = LevelState.ACTIVE
    touches: int = 0
    state_history: list[tuple[datetime, LevelState]] = field(default_factory=list)

    def record_state(self, ts: datetime, state: LevelState) -> None:
        self.state = state
        self.state_history.append((ts, state))
```

- [ ] **Step 4: Verify pass**, **Step 5: Commit** — `git commit -m "feat: evidence and level data models"`

---

### Task 4: Config loader

**Files:**
- Create: `app/trader/config.py`, `app/config/config.json`, `app/config/stocks.json`
- Test: `app/tests/test_config.py`

**Interfaces:**
- Produces: `Settings` (pydantic) mirroring the config.json shape in `01-ARCHITECTURE-CONTRACTS.md`; `load_settings(path: Path) -> Settings`; `load_stocks(path: Path) -> list[str]`; `Settings.enabled_weights() -> dict[str, float]` returning **weights renormalized to 100 over enabled detectors only**.

- [ ] **Step 1: Failing tests**

```python
# app/tests/test_config.py
import json
from pathlib import Path
import pytest
from trader.config import load_settings, load_stocks

def write(tmp_path, cfg):
    p = tmp_path / "config.json"
    p.write_text(json.dumps(cfg))
    return p

BASE = {
    "capital": 100000,
    "risk": {"per_trade_pct": 0.5, "daily_loss_pct": 1.5, "max_trades_day": 3,
             "max_per_stock": 1, "consecutive_loss_stop": 2, "expiry_size_mult": 0.5},
    "time": {"observe_until": "10:45", "no_entry_after": "14:30", "squareoff": "15:10"},
    "stops": {"atr_buffer": 0.25, "wick_tolerance_candles": 1, "round_offset_ticks": 3},
    "confluence": {"threshold": 65, "weights": {"sweep": 50, "structure": 30, "orderblock": 20}},
    "detectors": {"enabled": ["sweep", "structure"], "disabled": ["orderblock"], "params": {}},
    "fills": {"slippage_bps": 3, "half_spread_bps": 2,
              "costs": {"brokerage_flat": 20, "stt_pct": 0.025, "exchange_pct": 0.00297}},
}

def test_loads_and_validates(tmp_path):
    s = load_settings(write(tmp_path, BASE))
    assert s.capital == 100000 and s.confluence.threshold == 65

def test_weights_renormalize_over_enabled_only(tmp_path):
    s = load_settings(write(tmp_path, BASE))
    w = s.enabled_weights()
    assert set(w) == {"sweep", "structure"}
    assert abs(sum(w.values()) - 100.0) < 1e-9
    assert w["sweep"] == pytest.approx(62.5)   # 50/(50+30)*100

def test_stocks_list(tmp_path):
    p = tmp_path / "stocks.json"
    p.write_text(json.dumps({"stocks": ["RELIANCE", "TCS", "HDFCBANK"]}))
    assert load_stocks(p) == ["RELIANCE", "TCS", "HDFCBANK"]

def test_bad_config_rejected(tmp_path):
    bad = dict(BASE, risk=dict(BASE["risk"], per_trade_pct=-1))
    with pytest.raises(Exception):
        load_settings(write(tmp_path, bad))
```

- [ ] **Step 2: Verify fail**
- [ ] **Step 3: Implement** — pydantic v2 models: `RiskCfg` (all fields `gt=0` where sensible), `TimeCfg` (strings validated `HH:MM`), `StopsCfg`, `ConfluenceCfg(threshold: float, weights: dict[str, float])`, `DetectorsCfg(enabled: list[str], disabled: list[str], params: dict)`, `FillsCfg` + nested `CostsCfg`, top `Settings` with:

```python
def enabled_weights(self) -> dict[str, float]:
    w = {k: v for k, v in self.confluence.weights.items()
         if k in self.detectors.enabled}
    total = sum(w.values())
    if total == 0:
        return {}
    return {k: v / total * 100 for k, v in w.items()}
```

`load_settings(path)` = `Settings.model_validate_json(path.read_text())`. `load_stocks` reads `{"stocks": [...]}`. Also write `app/config/config.json` with the full default shape from the contracts doc (all detectors listed, `cage` disabled) and `app/config/stocks.json` with `{"stocks": []}`.

- [ ] **Step 4: Verify pass**, **Step 5: Commit** — `git commit -m "feat: validated config with weight renormalization"`

---

### Task 5: CandleStore — aggregation + no-lookahead views

**Files:**
- Create: `app/trader/store/candles.py`
- Test: `app/tests/store/test_candles.py`

**Interfaces:**
- Produces:
  - `CandleStore(root: Path)` — `add(candle: Candle)` (M1 only; aggregates upward), `view(symbol, now) -> CandleView`, `save(symbol)` / `load(symbol)` (parquet under `root/symbol/tf.parquet`).
  - `CandleView` — `last(n: int, tf: Timeframe) -> list[Candle]`, `today(tf) -> list[Candle]`, `prev_day(tf) -> list[Candle]`; every method filters `ts + tf.minutes <= now` (**only fully closed candles visible**).
  - Aggregation boundaries: M5/M15/H1 by floor-division from 09:15 session open; D1 = whole session. open=first, high=max, low=min, close=last, volume=sum.

- [ ] **Step 1: Failing tests**

```python
# app/tests/store/test_candles.py
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from trader.models.candle import Candle, Timeframe, tick
from trader.store.candles import CandleStore

IST = ZoneInfo("Asia/Kolkata")
D = datetime(2026, 7, 15, tzinfo=IST)

def m1(minute_offset, o, h, l, c, v=100):
    ts = D.replace(hour=9, minute=15) + timedelta(minutes=minute_offset)
    return Candle("X", Timeframe.M1, ts, tick(o), tick(h), tick(l), tick(c), v)

def fill(store, n):
    for i in range(n):
        store.add(m1(i, 100 + i, 101 + i, 99 + i, 100.5 + i))

def test_m5_aggregation(tmp_path):
    s = CandleStore(tmp_path)
    fill(s, 5)                                # 09:15..09:19 → one closed M5
    v = s.view("X", D.replace(hour=9, minute=20))
    [agg] = v.last(1, Timeframe.M5)
    assert agg.open == tick(100) and agg.close == tick("104.5")
    assert agg.high == tick(105) and agg.low == tick(99) and agg.volume == 500

def test_no_lookahead(tmp_path):
    s = CandleStore(tmp_path)
    fill(s, 10)                               # data to 09:24
    v = s.view("X", D.replace(hour=9, minute=18))   # but now = 09:18
    assert v.last(100, Timeframe.M1)[-1].ts.minute == 17   # 09:17 last CLOSED
    assert v.last(1, Timeframe.M5) == []      # first M5 closes 09:20

def test_partial_bucket_hidden(tmp_path):
    s = CandleStore(tmp_path)
    fill(s, 7)                                # 09:15..09:21
    v = s.view("X", D.replace(hour=9, minute=22))
    assert len(v.last(10, Timeframe.M5)) == 1  # second M5 incomplete → hidden

def test_persistence_roundtrip(tmp_path):
    s = CandleStore(tmp_path); fill(s, 5); s.save("X")
    s2 = CandleStore(tmp_path); s2.load("X")
    v = s2.view("X", D.replace(hour=9, minute=20))
    assert len(v.last(5, Timeframe.M1)) == 5
```

- [ ] **Step 2: Verify fail**
- [ ] **Step 3: Implement** — internal dict `{symbol: {tf: list[Candle]}}` kept sorted; `add` appends M1 then re-derives affected aggregate buckets (recompute bucket from constituent M1s — simple and correct over fast); bucket start = `09:15 + floor((ts - 09:15) / tf.minutes) * tf.minutes`; D1 bucket = session date. `CandleView` holds `(store, symbol, now)` and filters closed candles: `c.ts + timedelta(minutes=c.tf.minutes) <= now`. Parquet via pandas `to_parquet`/`read_parquet` per tf, Decimal↔str columns on save/load.
- [ ] **Step 4: Verify pass**, **Step 5: Commit** — `git commit -m "feat: candle store with multi-TF aggregation and no-lookahead views"`

---

### Task 6: DataFeed ABC + MockFeed scenarios

**Files:**
- Create: `app/trader/feed/base.py`, `app/trader/feed/mock.py`
- Test: `app/tests/feed/test_mock.py`

**Interfaces:**
- Consumes: `Candle`, `Timeframe`, `tick`.
- Produces: `FeedEvent(candle)`, `DataFeed` ABC per contracts; `ScenarioFeed(DataFeed)` built from a `Scenario` — `Scenario(name, symbol, date, segments)` where each segment = `(minutes, drift_per_min, vol_range, volume)`; helper constructors `judas_reversal(symbol, date, open_price)` and `trend_day(symbol, date, open_price)` returning full 375-minute scripted days **with ground-truth markers**: `scenario.truth` dict, e.g. `{"sweep_low_minute": 22, "reversal_from": Decimal, "afternoon_direction": "LONG"}`.

- [ ] **Step 1: Failing tests**

```python
# app/tests/feed/test_mock.py
from datetime import date
from trader.models.candle import Timeframe
from trader.feed.mock import ScenarioFeed, judas_reversal, trend_day

def test_judas_shape():
    sc = judas_reversal("X", date(2026, 7, 15), 100.0)
    feed = ScenarioFeed([sc]); feed.subscribe(["X"])
    candles = [e.candle for e in feed.events()]
    assert len(candles) == 375 and all(c.tf == Timeframe.M1 for c in candles)
    low_min = sc.truth["sweep_low_minute"]
    day_low = min(c.low for c in candles)
    assert candles[low_min].low == day_low            # scripted low where truth says
    assert candles[-1].close > candles[low_min].close # afternoon rallied

def test_trend_day_shape():
    sc = trend_day("X", date(2026, 7, 15), 100.0)
    candles = [e.candle for e in ScenarioFeed([sc]).events() ]
    assert candles[-1].close > candles[0].open        # closes near high

def test_deterministic():
    a = [e.candle for e in ScenarioFeed([judas_reversal("X", date(2026,7,15), 100.0)]).events()]
    b = [e.candle for e in ScenarioFeed([judas_reversal("X", date(2026,7,15), 100.0)]).events()]
    assert a == b
```

- [ ] **Step 2: Verify fail**
- [ ] **Step 3: Implement** — `base.py` exactly per contracts. `mock.py`: deterministic (seeded `random.Random(hash(name+symbol+str(date)))`) walk per segment; `judas_reversal` segments: 20 min drift down −0.08%/min → sweep spike low at minute ~22 with 3× volume → 40 min recovery +0.06%/min → 180 min flat chop → 135 min rally +0.04%/min; `truth` records scripted indexes/prices. `trend_day`: steady +0.05%/min, pullbacks every 45 min for 10 min at −0.02%/min. OHLC per minute built from segment drift ± vol_range noise, always valid (high≥max, low≤min).
- [ ] **Step 4: Verify pass**, **Step 5: Commit** — `git commit -m "feat: scenario mock feed with ground truth"`

---

### Task 7: FileFeed (CSV)

**Files:**
- Create: `app/trader/feed/file.py`
- Test: `app/tests/feed/test_file.py`

**Interfaces:**
- Produces: `FileFeed(DataFeed)` — `FileFeed(root: Path)`; reads `root/<SYMBOL>.csv` with header `ts,open,high,low,close,volume` (ts ISO-8601 IST); `events()` yields chronologically merged across subscribed symbols; `historical()` filters by date range.

- [ ] **Step 1: Failing tests**

```python
# app/tests/feed/test_file.py
from datetime import date
from pathlib import Path
from trader.feed.file import FileFeed
from trader.models.candle import Timeframe

CSV = """ts,open,high,low,close,volume
2026-07-15T09:15:00+05:30,100,101,99,100.5,1000
2026-07-15T09:16:00+05:30,100.5,102,100,101.5,1200
"""

def test_reads_and_orders(tmp_path):
    (tmp_path / "X.csv").write_text(CSV)
    f = FileFeed(tmp_path); f.subscribe(["X"])
    evs = list(f.events())
    assert len(evs) == 2 and evs[0].candle.ts < evs[1].candle.ts

def test_historical_range(tmp_path):
    (tmp_path / "X.csv").write_text(CSV)
    f = FileFeed(tmp_path)
    got = f.historical("X", Timeframe.M1, date(2026, 7, 15), date(2026, 7, 15))
    assert len(got) == 2

def test_interleaves_symbols(tmp_path):
    (tmp_path / "A.csv").write_text(CSV)
    (tmp_path / "B.csv").write_text(CSV)
    f = FileFeed(tmp_path); f.subscribe(["A", "B"])
    evs = list(f.events())
    assert [e.candle.symbol for e in evs[:2]] == ["A", "B"]   # same ts → stable symbol order
```

- [ ] **Step 2: Verify fail**
- [ ] **Step 3: Implement** — pandas `read_csv`, `tick()` all prices, build `Candle(tf=M1)`, `heapq.merge` per-symbol iterators keyed `(ts, symbol)`.
- [ ] **Step 4: Verify pass**, **Step 5: Commit** — `git commit -m "feat: csv file feed"`

---

### Task 8: Journal (JSONL)

**Files:**
- Create: `app/trader/store/journal.py`
- Test: `app/tests/store/test_journal.py`

**Interfaces:**
- Produces: `Journal(root: Path)` — `log(kind: str, payload: dict)` appends `{"ts": iso, "kind": kind, **payload}` to `root/YYYY-MM-DD.jsonl`; `read(day: date) -> list[dict]`. Serializes `Decimal`→str, `Enum`→name, `datetime`→iso via custom encoder. Kinds used later: `trade_open`, `trade_close`, `skip`, `verdict`, `session`.

- [ ] **Step 1: Failing tests**

```python
# app/tests/store/test_journal.py
from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo
from trader.store.journal import Journal
from trader.models.evidence import Direction

def test_roundtrip(tmp_path):
    j = Journal(tmp_path)
    ts = datetime(2026, 7, 15, 10, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
    j.log("skip", {"symbol": "X", "price": Decimal("100.05"),
                   "direction": Direction.LONG, "at": ts})
    rows = j.read(date(2026, 7, 15))
    assert rows[0]["kind"] == "skip" and rows[0]["price"] == "100.05"
    assert rows[0]["direction"] == "LONG"

def test_appends_not_overwrites(tmp_path):
    j = Journal(tmp_path)
    j.log("a", {}); j.log("b", {})
    assert [r["kind"] for r in j.read(date.today())] == ["a", "b"]
```

Note: `test_appends_not_overwrites` uses `date.today()` — make `log()` accept optional `day: date | None` and default to today so the first test can pass `at`-day explicitly via payload while file naming uses `day=date(2026,7,15)`. Adjust: call `j.log("skip", {...}, day=date(2026, 7, 15))`.

- [ ] **Step 2: Verify fail**
- [ ] **Step 3: Implement** — `json.dumps(payload, default=encode)` where `encode` handles Decimal/Enum/datetime; append mode; one line per entry.
- [ ] **Step 4: Verify pass**, **Step 5: Commit** — `git commit -m "feat: jsonl journal"`

---

### Task 9: CLI `init` + `list`

**Files:**
- Create: `app/trader/cli.py`
- Test: `app/tests/test_cli.py`

**Interfaces:**
- Consumes: `load_settings`, `load_stocks`.
- Produces: typer app with commands `init` (writes default `config.json` + `stocks.json` into `--dir`, refuses overwrite without `--force`) and `list` (numbered rich table of stocks; fit-score column shows `-` this phase). Entry point `trader` (pyproject Task 1).

- [ ] **Step 1: Failing tests**

```python
# app/tests/test_cli.py
import json
from typer.testing import CliRunner
from trader.cli import app

runner = CliRunner()

def test_init_scaffolds(tmp_path):
    r = runner.invoke(app, ["init", "--dir", str(tmp_path)])
    assert r.exit_code == 0
    assert (tmp_path / "config.json").exists() and (tmp_path / "stocks.json").exists()

def test_init_refuses_overwrite(tmp_path):
    runner.invoke(app, ["init", "--dir", str(tmp_path)])
    r = runner.invoke(app, ["init", "--dir", str(tmp_path)])
    assert r.exit_code != 0

def test_list_numbers_stocks(tmp_path):
    runner.invoke(app, ["init", "--dir", str(tmp_path)])
    (tmp_path / "stocks.json").write_text(json.dumps({"stocks": ["RELIANCE", "TCS"]}))
    r = runner.invoke(app, ["list", "--dir", str(tmp_path)])
    assert r.exit_code == 0 and "1" in r.output and "RELIANCE" in r.output and "TCS" in r.output
```

- [ ] **Step 2: Verify fail**
- [ ] **Step 3: Implement** — default config content = full shape from contracts doc (copy `app/config/config.json` template as package data or embedded dict). rich `Table` with columns `#, symbol, fit`.
- [ ] **Step 4: Verify pass**
- [ ] **Step 5: Full suite + commit**

Run: `pytest -q` — all green.
```bash
git add -A && git commit -m "feat: cli init and list commands"
```

---

## Phase 1 Exit Checklist

- [ ] `pytest -q` green, no network, no naive datetimes
- [ ] `trader init && trader list` usable from shell
- [ ] MockFeed judas day flows through CandleStore: write a final integration test
      `tests/test_integration_phase1.py` — pump all 375 ScenarioFeed events into
      CandleStore, view at 15:30, assert 75 closed M5 candles + 1 D1 candle, and
      `view(...).last(1, D1)[0].low == min(all lows)`; commit `test: phase1 integration`.
