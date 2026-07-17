from datetime import date
from trader.models.candle import Timeframe
from trader.feed.mock import (ScenarioFeed, double_trap, judas_reversal,
                              range_pin, stop_hunt_survive, trend_day)

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


# --- hardening tests beyond the brief ---------------------------------------

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest

from trader.models.candle import TICK
from trader.store.candles import CandleStore

IST = ZoneInfo("Asia/Kolkata")
D = date(2026, 7, 15)


def _both_scenarios():
    return [judas_reversal("X", D, 100.0), trend_day("Y", D, 500.0)]


@pytest.mark.parametrize("sc", _both_scenarios(), ids=lambda s: s.name)
def test_session_bounds_and_store_ingest(sc, tmp_path):
    candles = [e.candle for e in ScenarioFeed([sc]).events()]
    open_ts = datetime.combine(D, time(9, 15), tzinfo=IST)
    assert [c.ts for c in candles] == [open_ts + timedelta(minutes=i) for i in range(375)]
    store = CandleStore(tmp_path)          # add() rejects anything off-session
    for c in candles:
        store.add(c)
    view = store.view(sc.symbol, open_ts + timedelta(minutes=376))
    assert len(view.today(Timeframe.M1)) == 375


def test_sweep_low_is_unique_day_low():
    sc = judas_reversal("X", D, 100.0)
    candles = sc.candles()
    i = sc.truth["sweep_low_minute"]
    sweep = candles[i]
    others_min = min(c.low for j, c in enumerate(candles) if j != i)
    assert sweep.low < others_min                      # strictly unique low
    assert sweep.low == sc.truth["reversal_from"]
    assert sweep.low % TICK == 0                       # tick-quantized
    zlo, zhi = sc.truth["swept_zone"]
    assert sweep.low < zlo < zhi                       # spike undercuts the ORL zone


def _all_scenarios():
    return _both_scenarios() + [range_pin("Z", D, 100.0), double_trap("W", D, 200.0),
                                stop_hunt_survive("V", D, 100.0)]


@pytest.mark.parametrize("sc", _all_scenarios(), ids=lambda s: s.name)
def test_ohlc_invariants_every_candle(sc):
    for c in sc.candles():
        assert c.high >= max(c.open, c.close)
        assert c.low <= min(c.open, c.close)
        assert c.high >= c.low
        for p in (c.open, c.high, c.low, c.close):
            assert p % TICK == 0
        assert c.volume > 0


def test_sweep_candle_has_volume_spike():
    sc = judas_reversal("X", D, 100.0)
    candles = sc.candles()
    i = sc.truth["sweep_low_minute"]
    neighbours = candles[max(0, i - 5):i] + candles[i + 1:i + 6]
    avg = sum(c.volume for c in neighbours) / len(neighbours)
    assert candles[i].volume > 2 * avg


def test_subscribe_filters_and_merges_time_order():
    feed = ScenarioFeed(_both_scenarios())
    feed.subscribe(["X"])
    xs = [e.candle for e in feed.events()]
    assert len(xs) == 375 and all(c.symbol == "X" for c in xs)
    feed.subscribe(["X", "Y"])
    merged = [e.candle for e in feed.events()]
    assert len(merged) == 750
    assert [c.ts for c in merged] == sorted(c.ts for c in merged)


@pytest.mark.parametrize("sc", _all_scenarios(), ids=lambda s: s.name)
def test_session_length_and_determinism(sc):
    candles = sc.candles()
    assert len(candles) == 375
    assert candles == sc.candles()                      # pure + deterministic


def test_double_trap_spikes_are_unique_day_extremes():
    sc = double_trap("W", D, 200.0)
    candles = sc.candles()
    lo_i, hi_i = sc.truth["sweep_low_minute"], sc.truth["sweep_high_minute"]
    assert candles[lo_i].low == sc.truth["day_low"] == min(c.low for c in candles)
    assert candles[hi_i].high == sc.truth["day_high"] == max(c.high for c in candles)
    assert candles[lo_i].low < min(c.low for i, c in enumerate(candles) if i != lo_i)
    assert candles[hi_i].high > max(c.high for i, c in enumerate(candles) if i != hi_i)


def test_range_pin_holds_the_opening_range():
    sc = range_pin("Z", D, 100.0)
    candles = sc.candles()
    or_high = max(c.high for c in candles[:15])
    or_low = min(c.low for c in candles[:15])
    rest = candles[15:]
    assert max(c.high for c in rest) < or_high          # both edges hold,
    assert min(c.low for c in rest) > or_low            # all day


def test_stop_hunt_survive_shape():
    sc = stop_hunt_survive("X", D, 100.0)
    candles = sc.candles()
    assert len(candles) == 375 and candles == sc.candles()    # deterministic
    slo, shi = sc.truth["stop_zone"]
    hm = sc.truth["hunt_minute"]
    hunt = candles[hm]
    assert hunt.low < slo                       # wick pierces the stop zone...
    b = hm // 5 * 5                             # ...but no M1 of the hunt M5
    assert all(c.close > shi for c in candles[b:b + 5])   # closes at/below it
    plo, phi = sc.truth["pivot_zone"]
    sm = sc.truth["pivot_sweep_minute"]
    assert candles[sm].low < plo                # pivot swept: wick through,
    assert candles[sm // 5 * 5 + 4].close > phi  # M5 close back above the zone
    assert min(c.low for c in candles[105:]) == hunt.low  # hunt = setup's low
    assert candles[-1].close > candles[sm].close          # afternoon rallied


def test_historical_m1_range_and_other_tf_rejected():
    feed = ScenarioFeed(_both_scenarios())
    got = feed.historical("X", Timeframe.M1, D, D)          # date, per contract
    assert len(got) == 375 and all(c.symbol == "X" for c in got)
    with pytest.raises(NotImplementedError):
        feed.historical("X", Timeframe.M5, D, D)
