from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from trader.models.candle import Candle, Timeframe, tick
from trader.store.candles import CandleStore

IST = ZoneInfo("Asia/Kolkata")
D = datetime(2026, 7, 15, tzinfo=IST)

def m1(minute_offset, o, h, l, c, v=100):
    ts = D.replace(hour=9, minute=15) + timedelta(minutes=minute_offset)
    return Candle("X", Timeframe.M1, ts, tick(o), tick(h), tick(l), tick(c), v)

def fill(store, n):
    for i in range(n):
        store.add(m1(i, 100 + i, 101 + i, 99 + i, 100.5 + i))

def test_m5_aggregation(tmp_path):
    s = CandleStore(tmp_path)
    fill(s, 5)                                # 09:15..09:19 → one closed M5
    v = s.view("X", D.replace(hour=9, minute=20))
    [agg] = v.last(1, Timeframe.M5)
    assert agg.open == tick(100) and agg.close == tick("104.5")
    assert agg.high == tick(105) and agg.low == tick(99) and agg.volume == 500

def test_no_lookahead(tmp_path):
    s = CandleStore(tmp_path)
    fill(s, 10)                               # data to 09:24
    v = s.view("X", D.replace(hour=9, minute=18))   # but now = 09:18
    assert v.last(100, Timeframe.M1)[-1].ts.minute == 17   # 09:17 last CLOSED
    assert v.last(1, Timeframe.M5) == []      # first M5 closes 09:20

def test_partial_bucket_hidden(tmp_path):
    s = CandleStore(tmp_path)
    fill(s, 7)                                # 09:15..09:21
    v = s.view("X", D.replace(hour=9, minute=22))
    assert len(v.last(10, Timeframe.M5)) == 1  # second M5 incomplete → hidden

def test_persistence_roundtrip(tmp_path):
    s = CandleStore(tmp_path); fill(s, 5); s.save("X")
    s2 = CandleStore(tmp_path); s2.load("X")
    v = s2.view("X", D.replace(hour=9, minute=20))
    assert len(v.last(5, Timeframe.M1)) == 5


def test_load_rederives_missing_derived_timeframes_from_m1(tmp_path):
    """An M1-only parquet set (derived TF files absent/deleted) must not
    leave M5/M15/H1/D1 empty on load -- detectors would silently see empty
    views. load() re-derives them from the loaded M1 candles."""
    s = CandleStore(tmp_path)
    fill(s, 375)                                # full session -> D1 exists too
    s.save("X")

    # Simulate an M1-only parquet set: delete every derived TF file.
    sym_dir = tmp_path / "X"
    for tf in (Timeframe.M5, Timeframe.M15, Timeframe.H1, Timeframe.D1):
        path = sym_dir / f"{tf.value}.parquet"
        assert path.exists()
        path.unlink()

    s2 = CandleStore(tmp_path)
    s2.load("X")

    now = D.replace(hour=15, minute=30)         # session close -> D1 visible too
    v = s2.view("X", now)
    expected = CandleStore(tmp_path)
    fill(expected, 375)
    ev = expected.view("X", now)

    assert v.last(5, Timeframe.M5) == ev.last(5, Timeframe.M5)
    assert v.last(1, Timeframe.D1) == ev.last(1, Timeframe.D1)
    assert v.last(500, Timeframe.M15) == ev.last(500, Timeframe.M15)
    assert v.last(500, Timeframe.H1) == ev.last(500, Timeframe.H1)


# --- extra edge-case tests (beyond the brief) ---

def test_add_rejects_non_m1(tmp_path):
    s = CandleStore(tmp_path)
    c5 = Candle("X", Timeframe.M5, D.replace(hour=9, minute=15),
                tick(100), tick(101), tick(99), tick(100), 100)
    with pytest.raises(ValueError):
        s.add(c5)


def test_add_rejects_out_of_session_ts(tmp_path):
    s = CandleStore(tmp_path)
    with pytest.raises(ValueError):
        s.add(m1(-1, 100, 101, 99, 100.5))      # 09:14 pre-open
    with pytest.raises(ValueError):
        s.add(m1(375, 100, 101, 99, 100.5))     # 15:30 post-close
    s.add(m1(0, 100, 101, 99, 100.5))           # 09:15 first session minute OK
    s.add(m1(374, 100, 101, 99, 100.5))         # 15:29 last session minute OK


def test_h1_buckets_anchor_to_session_open(tmp_path):
    s = CandleStore(tmp_path)
    fill(s, 120)                                # 09:15..11:14
    v = s.view("X", D.replace(hour=11, minute=15))
    h1 = v.last(2, Timeframe.H1)
    assert [(c.ts.hour, c.ts.minute) for c in h1] == [(9, 15), (10, 15)]  # not 10:00
    assert h1[0].open == tick(100) and h1[0].close == tick(100.5 + 59)
    assert h1[1].open == tick(100 + 60) and h1[1].close == tick(100.5 + 119)
    assert all(c.volume == 60 * 100 for c in h1)
    # M15 anchors the same way: 09:15, 09:30, 09:45, 10:00, ... (offset from
    # 09:15 is always a whole multiple of 15 minutes)
    m15 = v.last(8, Timeframe.M15)
    assert m15[0].ts == D.replace(hour=9, minute=15)
    assert all((c.ts - D.replace(hour=9, minute=15)).total_seconds() % (15 * 60) == 0
               for c in m15)


def test_duplicate_and_out_of_order_adds(tmp_path):
    s = CandleStore(tmp_path)
    s.add(m1(1, 101, 102, 100, 101.5))     # out of order: 09:16 before 09:15
    s.add(m1(0, 100, 101, 99, 100.5))
    for i in range(2, 5):
        s.add(m1(i, 100 + i, 101 + i, 99 + i, 100.5 + i))
    s.add(m1(0, 50, 120, 40, 60))          # duplicate 09:15 -> replaces
    v = s.view("X", D.replace(hour=9, minute=20))
    m1s = v.last(10, Timeframe.M1)
    assert [c.ts.minute for c in m1s] == [15, 16, 17, 18, 19]  # sorted
    assert m1s[0].open == tick(50)                             # last write won
    [agg] = v.last(1, Timeframe.M5)                            # bucket recomputed
    assert agg.open == tick(50) and agg.high == tick(120) and agg.low == tick(40)
    assert agg.close == tick("104.5") and agg.volume == 500
    # parquet roundtrip preserves derived TFs and exact Decimals/tz
    s.save("X")
    s2 = CandleStore(tmp_path); s2.load("X")
    [agg2] = s2.view("X", D.replace(hour=9, minute=20)).last(1, Timeframe.M5)
    assert agg2 == agg


# --- completeness fail-closed (audit 5): missing M1 members hide the bucket
# from complete_only (detector-facing) views; plain views keep raw access ---

def test_incomplete_bucket_hidden_until_backfilled(tmp_path):
    """An M5 bucket missing an M1 member (feed gap) is closed by clock but
    incomplete -- hidden from complete_only views; a backfill of the missing
    minute makes it visible again."""
    s = CandleStore(tmp_path)
    for i in (0, 1, 2, 3, 5, 6, 7, 8, 9):       # 09:19 missing
        s.add(m1(i, 100 + i, 101 + i, 99 + i, 100.5 + i))
    now = D.replace(hour=9, minute=25)
    v = s.view("X", now, complete_only=True)
    assert [c.ts.minute for c in v.last(10, Timeframe.M5)] == [20]  # 4/5 hidden
    assert [c.ts.minute for c in v.today(Timeframe.M5)] == [20]
    raw = s.view("X", now)                      # store keeps it: raw view sees it
    assert [c.ts.minute for c in raw.last(10, Timeframe.M5)] == [15, 20]
    s.add(m1(4, 104, 105, 103, 104.5))          # backfill completes the bucket
    v2 = s.view("X", now, complete_only=True)
    assert [c.ts.minute for c in v2.last(10, Timeframe.M5)] == [15, 20]


def test_missing_m1_hides_exactly_the_affected_buckets(tmp_path):
    s = CandleStore(tmp_path)
    for i in range(375):
        if i != 100:                            # 10:55 missing
            s.add(m1(i, 100, 101, 99, 100.5))
    v = s.view("X", D.replace(hour=16, minute=15), complete_only=True)
    assert v.last(1, Timeframe.D1) == []                       # whole day 374/375
    assert [(c.ts.hour, c.ts.minute) for c in v.last(10, Timeframe.H1)] == [
        (9, 15), (11, 15), (12, 15), (13, 15), (14, 15), (15, 15)]  # 10:15 gone
    m5 = v.last(100, Timeframe.M5)
    assert len(m5) == 74 and all(c.ts != D.replace(hour=10, minute=55) for c in m5)


def test_session_truncated_last_bucket_counts_as_complete(tmp_path):
    """The session's last H1 bucket (15:15-16:15 by clock) only ever holds 15
    M1s; expected-member accounting respects the close truncation, so a full
    session marks NOTHING incomplete -- complete data => no behavior change."""
    s = CandleStore(tmp_path)
    fill(s, 375)
    v = s.view("X", D.replace(hour=16, minute=15), complete_only=True)
    h1 = v.last(10, Timeframe.H1)
    assert len(h1) == 7 and h1[-1].ts == D.replace(hour=15, minute=15)
    assert len(v.last(1, Timeframe.D1)) == 1
    assert s._incomplete == set()


def test_incompleteness_survives_parquet_roundtrip(tmp_path):
    s = CandleStore(tmp_path)
    for i in (0, 1, 2, 3, 5, 6, 7, 8, 9):
        s.add(m1(i, 100, 101, 99, 100.5))
    s.save("X")
    s2 = CandleStore(tmp_path); s2.load("X")    # marks re-derived from M1
    v = s2.view("X", D.replace(hour=9, minute=25), complete_only=True)
    assert [c.ts.minute for c in v.last(10, Timeframe.M5)] == [20]


def test_d1_visible_only_after_session_close(tmp_path):
    s = CandleStore(tmp_path)
    fill(s, 375)                            # full session 09:15..15:29
    before = s.view("X", D.replace(hour=15, minute=29, second=59))
    assert before.last(1, Timeframe.D1) == []          # 15:30 not reached
    assert before.today(Timeframe.D1) == []
    at_close = s.view("X", D.replace(hour=15, minute=30))
    [d1] = at_close.last(1, Timeframe.D1)              # visible at exactly 15:30
    assert d1.ts == D.replace(hour=9, minute=15)
    assert d1.open == tick(100) and d1.close == tick(100.5 + 374)
    assert d1.high == tick(101 + 374) and d1.low == tick(99)
    assert d1.volume == 375 * 100
    assert at_close.today(Timeframe.D1) == [d1]
    assert at_close.prev_day(Timeframe.D1) == []       # no earlier session
