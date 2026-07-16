"""Scanner (fit score) boundary-case tests: one per formula, plus the
missing-data neutral-0.5 fallback and the has_data() helper used by --auto."""

from datetime import datetime, timedelta
from decimal import Decimal as D
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from trader.engine.scanner import fit, has_data
from trader.models.candle import Candle, Timeframe
from trader.models.market import NSE
from trader.store.candles import CandleStore

IST = ZoneInfo("Asia/Kolkata")
T0 = datetime(2026, 6, 1, 9, 15, tzinfo=IST)
SYM = "X"


def d1(i, o, h, l, c, v=100_000):
    return Candle(SYM, Timeframe.D1, T0 + timedelta(days=i),
                 D(str(o)), D(str(h)), D(str(l)), D(str(c)), v)


def m5(i, o, h, l, c, v=1_000):
    return Candle(SYM, Timeframe.M5, T0 + timedelta(minutes=5 * i),
                 D(str(o)), D(str(h)), D(str(l)), D(str(c)), v)


def store(d1s=(), m5s=()):
    s = CandleStore(Path("unused"), NSE)
    s._data[SYM] = {tf: [] for tf in Timeframe}
    s._data[SYM][Timeframe.D1] = list(d1s)
    s._data[SYM][Timeframe.M5] = list(m5s)
    return s


# --------------------------------------------------------------- missing data

def test_missing_data_all_components_neutral():
    res = fit(SYM, store(), NSE)
    assert res["components"] == {"cleanliness": 0.5, "energy": 0.5,
                                 "liquidity": 0.5, "setup": 0.5, "context": 0.5}
    assert res["score"] == pytest.approx(50.0)


def test_has_data_false_on_empty_store():
    assert has_data(SYM, store(), NSE) is False


def test_has_data_true_when_d1_present():
    assert has_data(SYM, store(d1s=[d1(0, 100, 101, 99, 100)]), NSE) is True


# --------------------------------------------------------------- cleanliness

def test_cleanliness_perfect_no_gaps_constant_ranges():
    d1s = [d1(i, 150, 151, 149, 150) for i in range(4)]     # 0 gaps, range=2 always
    m5s = [m5(i, 10, 10.5, 9.5, 10) for i in range(4)]       # constant range=1
    res = fit(SYM, store(d1s, m5s), NSE)
    assert res["components"]["cleanliness"] == pytest.approx(1.0)


def test_cleanliness_penalized_by_gap():
    d1s = [d1(0, 150, 151, 149, 150), d1(1, 150, 151, 149, 150),
          d1(2, 160, 161, 159, 160),                          # gap: |160-150|=10 > avg_range=2
          d1(3, 160, 161, 159, 160)]
    m5s = [m5(i, 10, 10.5, 9.5, 10) for i in range(4)]
    res = fit(SYM, store(d1s, m5s), NSE)
    expected_gap = 1 - 1 / 3                                  # 1 gap out of 3 transitions
    expected = (expected_gap + 1.0 + 1.0) / 3
    assert res["components"]["cleanliness"] == pytest.approx(expected)


# -------------------------------------------------------------------- energy

def _energy_for(atr_pct: float) -> float:
    price = 100.0
    rng = price * atr_pct / 100
    d1s = [d1(i, price, price + rng / 2, price - rng / 2, price) for i in range(5)]
    return fit(SYM, store(d1s), NSE)["components"]["energy"]


def test_energy_peaks_at_2_5_pct():
    assert _energy_for(2.5) == pytest.approx(1.0)


def test_energy_zero_at_lower_edge():
    assert _energy_for(1.0) == pytest.approx(0.0)


def test_energy_zero_at_upper_edge():
    assert _energy_for(4.0) == pytest.approx(0.0)


def test_energy_zero_outside_band():
    assert _energy_for(0.5) == pytest.approx(0.0)
    assert _energy_for(5.0) == pytest.approx(0.0)


def test_energy_midpoint_below_peak():
    assert _energy_for(1.75) == pytest.approx(0.5)


# ---------------------------------------------------------------- liquidity

def test_liquidity_full_at_20x_notional():
    m5s = [m5(i, 100, 100, 100, 100, v=1000) for i in range(3)]   # notional 100_000
    res = fit(SYM, store(m5s=m5s), NSE, qty_notional=5_000)        # ratio = 20x
    assert res["components"]["liquidity"] == pytest.approx(1.0)


def test_liquidity_half_at_10x_notional():
    m5s = [m5(i, 100, 100, 100, 100, v=1000) for i in range(3)]
    res = fit(SYM, store(m5s=m5s), NSE, qty_notional=10_000)       # ratio = 10x
    assert res["components"]["liquidity"] == pytest.approx(0.5)


def test_liquidity_neutral_when_qty_notional_missing():
    m5s = [m5(i, 100, 100, 100, 100, v=1000) for i in range(3)]
    res = fit(SYM, store(m5s=m5s), NSE)
    assert res["components"]["liquidity"] == pytest.approx(0.5)


# -------------------------------------------------------------------- setup

def test_setup_full_on_new_5day_high():
    d1s = [d1(i, 100, 100 + i, 99, 100) for i in range(5)]          # rising highs
    d1s.append(d1(5, 100, 110, 99, 100))                            # new 5-day high
    res = fit(SYM, store(d1s), NSE)
    assert res["components"]["setup"] == pytest.approx(1.0)


def test_setup_zero_when_inside_prior_range():
    d1s = [d1(i, 100, 105, 95, 100) for i in range(6)]               # flat range every day
    res = fit(SYM, store(d1s), NSE)
    assert res["components"]["setup"] == pytest.approx(0.0)


def test_setup_neutral_with_insufficient_history():
    d1s = [d1(i, 100, 101, 99, 100) for i in range(3)]                # <6 candles
    res = fit(SYM, store(d1s), NSE)
    assert res["components"]["setup"] == pytest.approx(0.5)


# ------------------------------------------------------------------- context

def test_context_always_neutral():
    d1s = [d1(i, 100, 101, 99, 100) for i in range(10)]
    assert fit(SYM, store(d1s), NSE)["components"]["context"] == pytest.approx(0.5)
