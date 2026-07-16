import json
from pathlib import Path
import pytest
from trader.config import load_settings, load_stocks
from trader.detectors.base import DetectorRegistry
import trader.detectors.breaker  # noqa: F401  -- register all implemented detectors
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

SHIPPED_CONFIG = Path(__file__).resolve().parent.parent / "config" / "config.json"

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

def test_shipped_config_registry_constructs():
    # Regression: the shipped template must only enable detectors that are
    # actually implemented, or DetectorRegistry's typo-guard raises.
    settings = load_settings(SHIPPED_CONFIG)
    registry = DetectorRegistry(settings)
    assert {d.name for d in registry.detectors} == set(settings.detectors.enabled)
