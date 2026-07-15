from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo
import pytest
from trader.store.journal import Journal
from trader.models.evidence import Direction

def test_roundtrip(tmp_path):
    j = Journal(tmp_path)
    ts = datetime(2026, 7, 15, 10, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
    j.log("skip", {"symbol": "X", "price": Decimal("100.05"),
                   "direction": Direction.LONG, "at": ts}, day=date(2026, 7, 15))
    rows = j.read(date(2026, 7, 15))
    assert rows[0]["kind"] == "skip" and rows[0]["price"] == "100.05"
    assert rows[0]["direction"] == "LONG"

def test_appends_not_overwrites(tmp_path):
    j = Journal(tmp_path)
    j.log("a", {}); j.log("b", {})
    assert [r["kind"] for r in j.read(date.today())] == ["a", "b"]

def test_reserved_keys_rejected(tmp_path):
    j = Journal(tmp_path)
    with pytest.raises(ValueError):
        j.log("skip", {"ts": "sneaky"})
    with pytest.raises(ValueError):
        j.log("skip", {"kind": "sneaky"})
    assert j.read(date.today()) == []
