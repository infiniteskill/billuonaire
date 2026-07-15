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
