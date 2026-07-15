import logging
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from trader.config import Settings
from trader.detectors.base import REGISTRY, Detector, DetectorRegistry, register
from trader.engine.context import DayState, StockContext
from trader.models.evidence import Direction, Evidence
from trader.store.candles import CandleStore

IST = ZoneInfo("Asia/Kolkata")
NOW = datetime(2026, 7, 15, 10, 0, tzinfo=IST)


def ev(name, ctx):
    return Evidence(detector=name, direction=Direction.NEUTRAL, strength=1.0,
                    zone=(Decimal("100"), Decimal("101")), ts=ctx.now, ttl_candles=3)


@register
class AlphaDetector(Detector):
    name = "alpha"
    def detect(self, ctx):
        return [ev(self.name, ctx)]


@register
class BetaDetector(Detector):
    name = "beta"
    def detect(self, ctx):
        return [ev(self.name, ctx)]


@register
class GammaDetector(Detector):
    name = "gamma"
    instantiated = 0
    def __init__(self, params):
        super().__init__(params)
        GammaDetector.instantiated += 1
    def detect(self, ctx):
        return [ev(self.name, ctx)]


@register
class BoomDetector(Detector):
    name = "boom"
    def detect(self, ctx):
        raise RuntimeError("kaboom")


@register
class OptionsDetector(Detector):
    name = "needs_options"
    requires = frozenset({"options_chain"})
    calls = 0
    def detect(self, ctx):
        OptionsDetector.calls += 1
        return [ev(self.name, ctx)]


def make_settings(enabled, params=None):
    return Settings.model_validate({
        "capital": 100000,
        "risk": {"per_trade_pct": 0.5, "daily_loss_pct": 1.5, "max_trades_day": 3,
                 "max_per_stock": 1, "consecutive_loss_stop": 2, "expiry_size_mult": 0.5},
        "time": {"observe_until": "10:45", "no_entry_after": "14:30", "squareoff": "15:10"},
        "stops": {"atr_buffer": 0.25, "wick_tolerance_candles": 1, "round_offset_ticks": 3},
        "confluence": {"threshold": 65, "weights": {name: 10 for name in enabled}},
        "detectors": {"enabled": enabled, "disabled": [], "params": params or {}},
        "fills": {"slippage_bps": 3, "half_spread_bps": 2,
                  "costs": {"brokerage_flat": 20, "stt_pct": 0.025, "exchange_pct": 0.00297}},
    })


def make_ctx(options=None):
    view = CandleStore("/nonexistent").view("X", NOW)
    return StockContext(symbol="X", now=NOW, candles=view, levels=[],
                        evidence_history=[], day=DayState(session_date=NOW.date()),
                        options=options)


def test_register_adds_to_registry_by_name():
    assert REGISTRY["alpha"] is AlphaDetector
    assert REGISTRY["beta"] is BetaDetector


def test_duplicate_register_name_raises():
    with pytest.raises(ValueError, match="alpha"):
        @register
        class AlphaImpostor(Detector):
            name = "alpha"
            def detect(self, ctx):
                return []
    assert REGISTRY["alpha"] is AlphaDetector  # original untouched


def test_registry_instantiates_only_enabled():
    GammaDetector.instantiated = 0
    reg = DetectorRegistry(make_settings(["alpha", "beta"]))
    assert [d.name for d in reg.detectors] == ["alpha", "beta"]
    assert GammaDetector.instantiated == 0  # registered but not enabled


def test_registry_unknown_name_raises_listing_known():
    with pytest.raises(ValueError) as exc:
        DetectorRegistry(make_settings(["no_such_detector"]))
    msg = str(exc.value)
    assert "no_such_detector" in msg
    assert "alpha" in msg  # known names listed


def test_registry_passes_per_detector_params():
    reg = DetectorRegistry(make_settings(["alpha", "beta"],
                                         params={"alpha": {"lookback": 5}}))
    by_name = {d.name: d for d in reg.detectors}
    assert by_name["alpha"].params == {"lookback": 5}
    assert by_name["beta"].params == {}


def test_broken_detector_isolated_and_logged(caplog):
    reg = DetectorRegistry(make_settings(["alpha", "boom", "beta"]))
    with caplog.at_level(logging.ERROR, logger="trader.detectors"):
        out = reg.run_all(make_ctx())
    assert [e.detector for e in out] == ["alpha", "beta"]  # boom poisoned nothing
    assert any(r.name == "trader.detectors" and "boom" in r.getMessage()
               for r in caplog.records)


def test_requires_unmet_silently_skipped():
    OptionsDetector.calls = 0
    reg = DetectorRegistry(make_settings(["alpha", "needs_options"]))
    out = reg.run_all(make_ctx(options=None))
    assert OptionsDetector.calls == 0  # never invoked, no error
    assert [e.detector for e in out] == ["alpha"]


def test_requires_met_runs():
    OptionsDetector.calls = 0
    reg = DetectorRegistry(make_settings(["alpha", "needs_options"]))
    out = reg.run_all(make_ctx(options=object()))
    assert OptionsDetector.calls == 1
    assert [e.detector for e in out] == ["alpha", "needs_options"]


def test_run_all_order_follows_enabled_config_order():
    forward = DetectorRegistry(make_settings(["alpha", "beta", "gamma"]))
    backward = DetectorRegistry(make_settings(["gamma", "beta", "alpha"]))
    ctx = make_ctx()
    assert [e.detector for e in forward.run_all(ctx)] == ["alpha", "beta", "gamma"]
    assert [e.detector for e in backward.run_all(ctx)] == ["gamma", "beta", "alpha"]
