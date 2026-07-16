"""Tests for the structure detector (trader/detectors/structure.py)."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from trader.detectors.structure import StructureDetector
from trader.engine.context import DayState, StockContext
from trader.models.candle import TICK, Candle, Timeframe, tick
from trader.models.evidence import Direction
from trader.models.level import Level, LevelKind, LevelState
from trader.store.candles import CandleStore

IST = ZoneInfo("Asia/Kolkata")
SESSION_START = datetime(2026, 7, 15, 9, 15, tzinfo=IST)
PARAMS = {"tf": "5m", "trend_swings": 4, "trap_window": 6, "fake_window": 5}


def swing(kind, price, born_min):
    p = tick(price)
    return Level(id=f"X-{kind.name}-{born_min}", symbol="X", kind=kind,
                 zone=(p - TICK, p + TICK), tf=Timeframe.M5,
                 born=SESSION_START + timedelta(minutes=born_min))


def bull_swings():  # HH (110->115) + HL (100->105)
    return [swing(LevelKind.SWING_L, 100, 0), swing(LevelKind.SWING_H, 110, 5),
            swing(LevelKind.SWING_L, 105, 10), swing(LevelKind.SWING_H, 115, 15)]


def bear_swings():  # LH (115->110) + LL (105->100)
    return [swing(LevelKind.SWING_H, 115, 0), swing(LevelKind.SWING_L, 105, 5),
            swing(LevelKind.SWING_H, 110, 10), swing(LevelKind.SWING_L, 100, 15)]


def make_ctx(closes, levels, history=None):
    store = CandleStore("/nonexistent")
    for i, c in enumerate(closes):  # one flat M5 bar per close
        start = SESSION_START + timedelta(minutes=5 * i)
        for j in range(5):
            store.add(Candle("X", Timeframe.M1, start + timedelta(minutes=j),
                             tick(c), tick(c + 1), tick(c - 1), tick(c), 100))
    now = SESSION_START + timedelta(minutes=5 * len(closes))
    return StockContext(symbol="X", now=now, candles=store.view("X", now),
                        levels=levels, evidence_history=history if history is not None else [],
                        day=DayState(session_date=now.date()))


def test_bullish_bos_fires_on_breaking_candle():
    [ev] = StructureDetector(PARAMS).detect(make_ctx([116], bull_swings()))
    assert ev.detector == "structure"
    assert ev.direction is Direction.LONG
    assert ev.strength == 0.6
    assert ev.ttl_candles == 12
    assert ev.zone == (tick(115) - TICK, tick(115) + TICK)
    assert ev.meta["event"] == "BOS"
    assert ev.meta["swing_id"] == "X-SWING_H-15"


def test_no_bos_without_break():
    assert StructureDetector(PARAMS).detect(make_ctx([114], bull_swings())) == []


def test_bearish_bos():
    [ev] = StructureDetector(PARAMS).detect(make_ctx([99], bear_swings()))
    assert ev.direction is Direction.SHORT
    assert ev.meta["event"] == "BOS"
    assert ev.zone == (tick(100) - TICK, tick(100) + TICK)


def test_ranging_no_evidence():
    mixed = [swing(LevelKind.SWING_L, 100, 0), swing(LevelKind.SWING_H, 110, 5),
             swing(LevelKind.SWING_L, 95, 10), swing(LevelKind.SWING_H, 115, 15)]
    assert StructureDetector(PARAMS).detect(make_ctx([116], mixed)) == []


def test_choch_flips_direction():
    [ev] = StructureDetector(PARAMS).detect(make_ctx([104], bull_swings()))
    assert ev.direction is Direction.SHORT
    assert ev.strength == 0.5
    assert ev.ttl_candles == 24
    assert ev.zone == (tick(105) - TICK, tick(105) + TICK)
    assert ev.meta["event"] == "CHOCH"


def test_choch_strength_08_with_recent_sweep():
    levels = bull_swings()
    levels[0].record_state(SESSION_START + timedelta(minutes=3), LevelState.SWEPT)
    [ev] = StructureDetector(PARAMS).detect(make_ctx([104], levels))
    assert ev.strength == 0.8


def test_choch_old_sweep_no_boost():
    levels = bull_swings()
    levels[0].record_state(SESSION_START, LevelState.SWEPT)  # 1st of 7 bars, outside last 6
    [ev] = StructureDetector(PARAMS).detect(make_ctx([106] * 6 + [104], levels))
    assert ev.strength == 0.5


def test_dedupe_second_detect_no_repeat():
    det = StructureDetector(PARAMS)
    ctx = make_ctx([116], bull_swings())
    [ev] = det.detect(ctx)
    ctx.evidence_history.append(ev)
    assert det.detect(ctx) == []


def test_fake_bos_memory_flags_later_evidence():
    det, swings = StructureDetector(PARAMS), bull_swings()
    [bos] = det.detect(make_ctx([116], swings))
    assert "fake_bos_recent" not in bos.meta
    assert det.detect(make_ctx([116, 114], swings, [bos])) == []  # closed back: fake
    [choch] = det.detect(make_ctx([116, 114, 104], swings, [bos]))
    assert choch.meta["event"] == "CHOCH"
    assert choch.meta["fake_bos_recent"] is True


def test_needs_swings_guard():
    assert StructureDetector(PARAMS).detect(make_ctx([116], [])) == []
    one_sided = [swing(LevelKind.SWING_H, 110, 0), swing(LevelKind.SWING_H, 115, 5)]
    assert StructureDetector(PARAMS).detect(make_ctx([116], one_sided)) == []
