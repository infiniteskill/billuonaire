"""Tests for the VSA/volume detector (trader/detectors/volume.py).
Binding design: task-5 brief (classification priority, co-location gate)."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from trader.detectors.volume import VolumeDetector
from trader.engine.context import DayState, StockContext
from trader.models.candle import TICK, Candle, Timeframe, tick
from trader.models.evidence import Direction, Evidence
from trader.store.candles import CandleStore

IST = ZoneInfo("Asia/Kolkata")
SESSION_START = datetime(2026, 7, 15, 9, 15, tzinfo=IST)
M1 = Timeframe.M1
PARAMS = {"tf": "1m", "sma": 3, "z_hi": 1.5}


def bar_ts(i):
    return SESSION_START + timedelta(minutes=i)


def bar(i, o, h, l, c, v):
    return Candle("X", M1, bar_ts(i), tick(o), tick(h), tick(l), tick(c), v)


def make_ctx(candles, history=None):
    store = CandleStore("/nonexistent")
    for cd in candles:
        store.add(cd)
    now = candles[-1].ts + timedelta(minutes=1)
    return StockContext(
        symbol="X", now=now, candles=store.view("X", now),
        levels=[], evidence_history=history if history is not None else [],
        day=DayState(session_date=now.date()),
    )


def confirming_evidence(ts, zone, direction=Direction.LONG, detector="orderblock"):
    return Evidence(detector=detector, direction=direction, strength=0.6,
                    zone=zone, ts=ts, ttl_candles=10, meta={})


# ---- 4-bar windows (sma=3, no ATR needed): stopping_volume / no_demand ----

def _sv_candles():
    # priors (indices 0-2) volume=100 -> sma=100; latest (3) bearish, vol=200
    # (>1.5*100), lower_wick=8 of range=10 (>=50%).
    return [bar(0, 100, 101, 99, 100, 100), bar(1, 100, 101, 99, 100, 100),
            bar(2, 100, 101, 99, 100, 100), bar(3, 110, 110, 100, 108, 200)]


def _nd_candles():
    # priors volume=100 -> sma=100; latest bullish, vol=50 (<0.7*100).
    return [bar(0, 100, 101, 99, 100, 100), bar(1, 100, 101, 99, 100, 100),
            bar(2, 100, 101, 99, 100, 100), bar(3, 100, 106, 99, 105, 50)]


def test_stopping_volume_classification_emits_with_colocated_evidence():
    candles = _sv_candles()
    latest = candles[-1]
    ev = confirming_evidence(bar_ts(3), (tick(105), tick(106)), Direction.SHORT)
    ctx = make_ctx(candles, history=[ev])

    [out] = VolumeDetector(PARAMS).detect(ctx)

    assert out.detector == "volume"
    assert out.direction is Direction.SHORT
    assert out.strength == 0.3
    assert out.zone == ev.zone
    assert out.ttl_candles == 6
    assert out.meta == {"vsa": "stopping_volume", "confirms": "orderblock"}


def test_no_demand_classification_emits_with_colocated_evidence():
    candles = _nd_candles()
    ev = confirming_evidence(bar_ts(3), (tick(100), tick(101)), Direction.SHORT)
    ctx = make_ctx(candles, history=[ev])

    [out] = VolumeDetector(PARAMS).detect(ctx)

    assert out.meta["vsa"] == "no_demand"
    assert out.direction is Direction.SHORT


def test_insufficient_candles_returns_empty():
    candles = _sv_candles()[:3]  # only 3 closed candles, sma=3 needs 4
    ctx = make_ctx(candles, history=[confirming_evidence(bar_ts(2), (tick(99), tick(101)))])

    assert VolumeDetector(PARAMS).detect(ctx) == []


def test_no_colocated_evidence_is_silent():
    candles = _sv_candles()  # would classify as stopping_volume
    ctx = make_ctx(candles, history=[])  # no other evidence at all

    assert VolumeDetector(PARAMS).detect(ctx) == []


def test_colocated_evidence_wrong_zone_is_silent():
    candles = _sv_candles()
    # evidence exists but its zone (200-201) doesn't overlap latest (100-110)
    ev = confirming_evidence(bar_ts(3), (tick(200), tick(201)))
    ctx = make_ctx(candles, history=[ev])

    assert VolumeDetector(PARAMS).detect(ctx) == []


def test_dedupe_same_candle_ts():
    candles = _sv_candles()
    ev = confirming_evidence(bar_ts(3), (tick(105), tick(106)))
    ctx = make_ctx(candles, history=[ev])
    det = VolumeDetector(PARAMS)

    assert len(det.detect(ctx)) == 1
    assert det.detect(ctx) == []


def test_nearest_ts_evidence_wins_on_multiple_matches():
    candles = _sv_candles()
    older = confirming_evidence(bar_ts(1), (tick(105), tick(106)), Direction.LONG, "fvg")
    newer = confirming_evidence(bar_ts(3), (tick(105), tick(106)), Direction.SHORT, "breaker")
    ctx = make_ctx(candles, history=[older, newer])

    [out] = VolumeDetector(PARAMS).detect(ctx)

    assert out.meta["confirms"] == "breaker"
    assert out.direction is Direction.SHORT


# ---- 15-bar window (ATR period=14, sma=3): climax / absorption / priority --

def _base15(latest_high, latest_low, latest_close, latest_vol):
    """14 baseline bars (0-13) on a continuous 100+i ramp -> constant TR=4
    for all 13 consecutive pairs among them; priors (11,12,13) get volumes
    [80,100,120] (sma=100, stddev=16.3299) for the sma window. Bar 14 is the
    latest candle, opening at bar13's close (113) so only its own high/low
    determine the final (13,14) TR pair -> ATR = (13*4 + TR14) / 14."""
    candles = [
        bar(i, 100 + i, 100 + i + 2, 100 + i - 2, 100 + i,
            {11: 80, 12: 100, 13: 120}.get(i, 100))
        for i in range(14)
    ]
    candles.append(bar(14, 113, latest_high, latest_low, latest_close, latest_vol))
    return candles


def test_climax_beats_absorption_priority():
    # latest: open=113,high=133,low=113 (range=20), close=114 (body=1),
    # vol=250. TR14=max(20,|133-113|=20,|113-113|=0)=20; ATR=(13*4+20)/14
    # =5.1429; range=20 > 2*ATR=10.29 -> climax. z=(250-100)/16.3299=9.19
    # >1.5 and body=1 < 0.3*ATR=1.54 -> absorption also matches; climax wins.
    candles = _base15(133, 113, 114, 250)
    ev = confirming_evidence(bar_ts(14), (tick(120), tick(121)), Direction.SHORT)
    ctx = make_ctx(candles, history=[ev])

    [out] = VolumeDetector(PARAMS).detect(ctx)

    assert out.meta["vsa"] == "climax"  # not "absorption", despite both matching


def test_absorption_classification_exact_z_score_and_emits():
    # latest: open=113,high=115,low=111 (range=4), close=114 (body=1),
    # vol=250. TR14=max(4,|115-113|=2,|111-113|=2)=4; ATR=(13*4+4)/14=4
    # exactly; range=4 not > 2*ATR=8 -> climax false. bullish with vol=250
    # (not < 0.7*sma=70) -> no_demand false; not bearish -> stopping_volume
    # false. z=(250-100)/16.3299=9.19 > 1.5 and body=1 < 0.3*ATR=1.2 ->
    # absorption.
    candles = _base15(115, 111, 114, 250)
    ev = confirming_evidence(bar_ts(14), (tick(112), tick(113)), Direction.LONG)
    ctx = make_ctx(candles, history=[ev])

    [out] = VolumeDetector(PARAMS).detect(ctx)

    assert out.meta["vsa"] == "absorption"
    assert out.direction is Direction.LONG
    assert out.zone == ev.zone
