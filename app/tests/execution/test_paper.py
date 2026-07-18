"""Phase-4 Task 4: PaperBroker -- adverse fills + costs, exact Decimal.

Adverse = (half_spread 2 + slippage 3) bps = 5 bps = x0.0005 on the fill
candle's open, always against us. Cost config stt_pct/exchange_pct are
PERCENTS of turnover, + flat 20/fill. STT (0.025%) is SELL-leg only (LONG
exit / SHORT entry); exchange_pct (0.00297%) applies both legs.
"""
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from trader.config import Settings
from trader.execution.paper import PaperBroker, leg_cost, round_trip_cost
from trader.models.candle import Candle, Timeframe
from trader.models.evidence import Direction
from trader.models.position import Fill, Position
from trader.models.signal import TradePlan

IST = ZoneInfo("Asia/Kolkata")
CONFIG = Path(__file__).resolve().parents[2] / "trader" / "templates" / "config.baseline.json"
TODAY = datetime(2026, 7, 15, tzinfo=IST)
D = Decimal
TS = TODAY.replace(hour=10, minute=0)


@pytest.fixture
def broker():
    return PaperBroker(Settings.model_validate_json(CONFIG.read_text()))


def candle(o):
    o = D(str(o))
    return Candle("X", Timeframe.M5, TS, o, o + 1, o - 1, o, 100)


def plan(direction=Direction.LONG, qty=100):
    return TradePlan("X", direction, (D("98"), D("100")), D("95"),
                     [D("105"), D("110"), D("115")], qty, 70.0, TODAY, {})


def position(direction=Direction.LONG, qty=100):
    return Position(plan=plan(direction, qty),
                    entry=Fill(D("100"), qty, TS, D("20")),
                    remaining_qty=qty, stop=D("95"))


def test_long_entry_pays_up(broker):
    f = broker.entry_fill(plan(), candle(100))
    assert f.price == D("100.05")          # 100 x (1 + 5/10000)
    assert f.qty == 100 and f.ts == TS


def test_short_entry_pays_down(broker):
    assert broker.entry_fill(plan(Direction.SHORT), candle(100)).price == D("99.95")


def test_long_exit_gives_back(broker):
    f = broker.exit_fill(position(), candle(100), 33)
    assert f.price == D("99.95") and f.qty == 33


def test_short_exit_pays_up(broker):
    assert broker.exit_fill(position(Direction.SHORT), candle(100), 33).price == D("100.05")


def test_target_exit_limit_fill_half_spread_only(broker):
    # limit AT target: half_spread 2 bps adverse, slippage NOT applied
    f = broker.exit_fill(position(), candle(100), 34, price=D("500"))
    assert f.price == D("499.90")               # 500 x (1 - 2/10000)
    assert f.ts == TS
    assert f.costs == D("20") + D("0.0002797") * D("499.90") * 34


def test_target_exit_limit_fill_short_pays_up(broker):
    f = broker.exit_fill(position(Direction.SHORT), candle(100), 33,
                         price=D("500"))
    assert f.price == D("500.10")               # cover: 500 x (1 + 2/10000)


def test_fill_price_tick_quantized(broker):
    # 100.03 x 1.0005 = 100.080015 -> nearest 0.05 tick (half-up) = 100.10
    f = broker.entry_fill(plan(), candle("100.03"))
    assert f.price == D("100.10")


def test_costs_formula_exact(broker):
    # LONG entry = BUY leg -> exchange_pct only (no STT).
    # price 100.05, qty 100: 20 + 0.0000297 x 10005.00 = 20.2971485
    f = broker.entry_fill(plan(), candle(100))
    assert isinstance(f.costs, Decimal)
    assert f.costs == D("20.2971485")


def test_costs_percent_semantics(broker):
    # SHORT entry = SELL leg (sell to open) -> STT + exchange both apply.
    # off open 100.05 -> 99.999975 -> quantized 100.00 exactly;
    # turnover 100000: percent leg = 100000 x (0.025+0.00297)% = 27.97
    f = broker.entry_fill(plan(Direction.SHORT, qty=1000), candle("100.05"))
    assert f.price == D("100.00")
    assert f.costs == D("47.97")


def test_costs_buy_leg_no_stt_on_cover(broker):
    # SHORT exit = BUY to cover -> exchange_pct only (no STT).
    # target price 100 fixed, qty 1000: 20 + 0.0000297 x 100000 = 22.97
    f = broker.exit_fill(position(Direction.SHORT, qty=1000), candle(100),
                         1000, price=D("100"))
    assert f.costs == D("22.97")


def test_shared_costing_helpers_stt_once_per_round_trip():
    # leg_cost is THE costing truth (broker fills + entry viability gate):
    # SELL 47.97 / BUY 22.97 at 100 x 1000; a round trip charges STT
    # exactly once = 70.94.
    c = Settings.model_validate_json(CONFIG.read_text()).fills.costs
    assert leg_cost(c, D("100"), 1000, True) == D("47.97")
    assert leg_cost(c, D("100"), 1000, False) == D("22.97")
    assert round_trip_cost(c, D("100"), 1000) == D("70.94")
