import json
from datetime import date
from pathlib import Path
import pytest
from trader.config import load_settings, load_stocks
from trader.detectors.base import DetectorRegistry
from trader.feed.mock import trend_day
import trader.detectors.bpr  # noqa: F401
import trader.detectors.breaker  # noqa: F401  -- register all implemented detectors
import trader.detectors.compression  # noqa: F401
import trader.detectors.compression_fade  # noqa: F401
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

_TEMPLATES = Path(__file__).resolve().parent.parent / "trader" / "templates"
BASELINE_CONFIG = _TEMPLATES / "config.baseline.json"   # obsolete, A/B replay
V2_CONFIG = _TEMPLATES / "config.json"                  # shipped default = v2

def write(tmp_path, cfg):
    p = tmp_path / "config.json"
    p.write_text(json.dumps(cfg))
    return p

BASE = {
    "capital": 100000,
    "risk": {"per_trade_pct": 0.5, "daily_loss_pct": 1.5, "max_trades_day": 3,
             "max_per_stock": 1, "consecutive_loss_stop": 2, "expiry_size_mult": 0.5},
    "time": {"no_entry_after": "14:30", "squareoff": "15:10"},
    "stops": {"atr_buffer": 0.25, "round_offset_ticks": 3},
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

def test_wick_tolerance_key_rejected(tmp_path):
    # B2: stealth stops are close-confirmed only; the dead knob must not load
    bad = dict(BASE, stops=dict(BASE["stops"], wick_tolerance_candles=1))
    with pytest.raises(Exception):
        load_settings(write(tmp_path, bad))

def test_observe_until_key_rejected(tmp_path):
    # dead knob (window derives from observe_min ONLY): must not load
    bad = dict(BASE, time=dict(BASE["time"], observe_until="10:45"))
    with pytest.raises(Exception):
        load_settings(write(tmp_path, bad))

def test_index_symbol_optional(tmp_path):
    assert load_settings(write(tmp_path, BASE)).index_symbol is None      # default
    s = load_settings(write(tmp_path, dict(BASE, index_symbol="NIFTY50")))
    assert s.index_symbol == "NIFTY50"

def test_baseline_config_has_index_weight():
    s = load_settings(BASELINE_CONFIG)
    assert s.index_symbol is None and s.confluence.weights["index"] == 5
    assert "index" in s.enabled_weights()          # enabled => renormalized in

def test_baseline_config_registry_constructs():
    # Regression: the shipped template must only enable detectors that are
    # actually implemented, or DetectorRegistry's typo-guard raises.
    settings = load_settings(BASELINE_CONFIG)
    registry = DetectorRegistry(settings)
    assert {d.name for d in registry.detectors} == set(settings.detectors.enabled)


LEVELS_ONLY = {"swings"}  # documented exception: writes levels, never Evidence


def test_v2_config_loads_and_no_free_rider():
    # E-2: every ENABLED evidence-capable detector must carry a confluence
    # weight, else it is a free-rider (counts toward distinct/
    # min_zone_detectors while scoring 0). LEVELS_ONLY detectors never emit
    # Evidence, so they can neither free-ride nor use a weight.
    s = load_settings(V2_CONFIG)
    missing = [d for d in s.detectors.enabled
               if d not in s.confluence.weights and d not in LEVELS_ONLY]
    assert missing == [], f"enabled detectors without a weight: {missing}"
    assert all(w > 0 for w in s.enabled_weights().values())
    # the two RR-profitable entry signals carry NONZERO weight
    assert s.confluence.weights["compression_fade"] > 0
    assert s.confluence.weights["bpr"] > 0


def test_v2_config_no_dead_weight():
    # Audit-3 B: a weight whose detector can't score is dead config. Every
    # weight key must be an enabled detector, and levels-only detectors
    # (swings: no Evidence, ever) stay ENABLED but carry no weight.
    s = load_settings(V2_CONFIG)
    assert set(s.confluence.weights) <= set(s.detectors.enabled)
    assert LEVELS_ONLY.isdisjoint(s.confluence.weights)
    assert "swings" in s.detectors.enabled       # its levels still matter


def test_v2_config_structure_context_reaches_trend():
    # Audit-3 A: with structure disabled no BOS/CHOCH evidence ever exists,
    # so TREND/TRAP_REVERSAL are unreachable and RANGE_PIN's 0.5 throttle
    # over-fires. structure rides as CONTEXT after the level-writers (small
    # nonzero weight; entries stay compression_fade/bpr).
    from tests.harness import run_scenario
    s = load_settings(V2_CONFIG)
    en = s.detectors.enabled
    assert en.index("structure") > max(en.index("swings"), en.index("liquidity"))
    assert s.confluence.weights["structure"] == 2
    res = run_scenario(trend_day("X", date(2026, 7, 15), 100.0),
                       tuple(en), classify=True)
    bos = [e for e in res.history
           if e.detector == "structure" and e.meta.get("event") == "BOS"]
    assert len(bos) >= 2 and res.day.template == "TREND"


def test_v2_config_elite_solo_settings():
    s = load_settings(V2_CONFIG)
    # a single compression_fade/bpr signal at a fresh zone must be armable
    assert s.detectors.params["confluence"]["min_zone_detectors"] == 1
    assert s.time.no_entry_after == "14:45"          # release-window end
    assert s.exits.target_r_by_source == {"compression_fade": 2.0, "bpr": 1.5}
    # baseline orderblock/fvg dropped (C-2: they clobber ob_lux/fvg_cb levels)
    assert "orderblock" not in s.detectors.enabled
    assert "fvg" not in s.detectors.enabled


def test_v2_config_registry_constructs():
    s = load_settings(V2_CONFIG)
    registry = DetectorRegistry(s)
    assert {d.name for d in registry.detectors} == set(s.detectors.enabled)
