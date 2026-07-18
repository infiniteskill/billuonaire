"""Shared scenario-run harness for the phase gate tests.

Pumps a ScenarioFeed day through the real pipeline exactly as production
would: CandleStore ingest per M1, then at every M5 close LevelEngine.update
on the latest closed M5, DetectorRegistry.run_all on a fresh StockContext
(shared live ``levels`` + ``evidence_history``, one persistent DayState for
the session), and -- when ``classify`` is on -- TemplateClassifier.update.
"""

import json
from datetime import timedelta
from pathlib import Path
from typing import NamedTuple

import trader.detectors.breaker  # noqa: F401  -- @register all implemented
import trader.detectors.compression  # noqa: F401
import trader.detectors.fvg  # noqa: F401
import trader.detectors.index  # noqa: F401
import trader.detectors.liquidity  # noqa: F401
import trader.detectors.orderblock  # noqa: F401
import trader.detectors.structure  # noqa: F401
import trader.detectors.sweep  # noqa: F401
import trader.detectors.swings  # noqa: F401
import trader.detectors.timestats  # noqa: F401
import trader.detectors.volume  # noqa: F401
import trader.detectors.wyckoff  # noqa: F401
from trader.config import Settings
from trader.detectors.base import DetectorRegistry
from trader.engine.context import DayState, StockContext
from trader.engine.levels import LevelEngine
from trader.engine.template import TemplateClassifier
from trader.feed.mock import Scenario, ScenarioFeed
from trader.models.candle import Timeframe
from trader.store.candles import CandleStore

CONFIG = Path(__file__).resolve().parent.parent / "trader" / "templates" / "config.baseline.json"
PHASE2 = ("swings", "liquidity", "structure", "sweep")
# Registry order IS execution order: level-writers before their consumers.
ALL_IMPLEMENTED = ("swings", "liquidity", "orderblock", "fvg", "structure",
                   "sweep", "breaker", "wyckoff", "volume", "compression",
                   "timestats", "index")


class Run(NamedTuple):
    now: object               # datetime: M5 close this tick evaluated at
    evidence: list
    template: str | None      # classifier answer this tick (None if off)


class Result(NamedTuple):
    runs: list[Run]
    levels: list
    history: list
    day: DayState


def scenario_settings(enabled: tuple = PHASE2) -> Settings:
    """Shipped config, cost-viability guard OFF: fixture scenarios trade toy
    prices (~100) with ~0.1% risk where real NSE costs always dominate; guard
    economics are unit-tested in tests/engine/test_entry.py."""
    raw = json.loads(CONFIG.read_text())
    raw["detectors"]["enabled"] = list(enabled)
    raw["risk"]["max_cost_reward_ratio"] = 1000.0
    return Settings.model_validate(raw)


def run_scenario(scenario: Scenario, enabled: tuple = PHASE2,
                 classify: bool = False) -> Result:
    """Pump the scenario's M1s; at each M5 close run LevelEngine.update on the
    latest closed M5, then the registry (then the template classifier when
    ``classify``), accumulating evidence_history."""
    registry = DetectorRegistry(scenario_settings(enabled))
    engine = LevelEngine({})
    classifier = TemplateClassifier(scenario.spec) if classify else None
    store = CandleStore(Path("/unused"))
    day = DayState(session_date=scenario.date)
    levels, history, runs = [], [], []
    feed = ScenarioFeed([scenario])
    feed.subscribe([scenario.symbol])
    for i, event in enumerate(feed.events()):
        store.add(event.candle)
        if (i + 1) % 5:
            continue
        now = event.candle.ts + timedelta(minutes=1)
        view = store.view(scenario.symbol, now)
        ctx = StockContext(symbol=scenario.symbol, now=now, candles=view,
                           levels=levels, evidence_history=history, day=day)
        engine.update(levels, view.last(1, Timeframe.M5)[-1], ctx.atr(Timeframe.M5))
        evidence = registry.run_all(ctx)
        template = classifier.update(ctx) if classifier else None
        runs.append(Run(now, evidence, template))
        history.extend(evidence)
    assert len(runs) == scenario.spec.session_minutes // 5
    return Result(runs, levels, history, day)
