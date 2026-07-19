"""Tests for the extremes detector (trader/detectors/extremes.py).

Ported research contract (dev/research/ext_zigzag.py + tune_lib, TUNE
frozen config, lessons 1+13):
- percent-leg floor via K = clip(leg_pct / median(ATR/close), 3, 14) and
  threshold K*ATR(14). Every synthetic bar below has TR = 2 exactly and
  median close < 100, so K clips to 3.0 and the floor is EXACTLY 6.0 price
  units -- deterministic scenarios;
- causality: a pivot is confirmed (level appears) only once the reversal
  leg reaches the floor, never before;
- alternation: a lower low printed before the up-leg completes REPLACES the
  pending low (deepest extreme wins), mirror at highs;
- band = wick-beyond-bodies (highest open/close of the cluster .. wick
  high at tops);
- rank_atr = min(leg_in, leg_out)/ATR(pivot); master = window max/min.

Gold-label parity: HEROMOTOCO H1 2026-04-27..2026-07-17 fixture (export of
runs/artifacts-data/l4_h1.parquet) must reproduce the EXTREMES.md chart-A
hand-circled pivots at leg_pct=4.7.
"""

import csv
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from trader.detectors.base import REGISTRY
from trader.detectors.extremes import ExtremesDetector
from trader.engine.context import DayState, StockContext
from trader.models.candle import Candle, Timeframe, tick
from trader.models.level import Level, LevelKind, LevelState

IST = ZoneInfo("Asia/Kolkata")
T0 = datetime(2026, 7, 1, 9, 15, tzinfo=IST)
H1 = Timeframe.H1
FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "heromotoco_h1.csv"


class SeqView:
    """Minimal CandleView stand-in: the detector only calls last(n, tf)."""

    def __init__(self, candles):
        self._candles = list(candles)

    def last(self, n, tf):
        xs = [c for c in self._candles if c.tf is tf]
        return xs[-n:] if n > 0 else []


def ctx_at(candles, levels=None):
    now = candles[-1].ts + timedelta(hours=1)
    return StockContext(symbol="X", now=now, candles=SeqView(candles),
                        levels=levels if levels is not None else [],
                        evidence_history=[], day=DayState(session_date=now.date()))


def bar(i, o, h, l, c):
    return Candle("X", H1, T0 + timedelta(hours=i), tick(o), tick(h), tick(l), tick(c), 0)


class Tape:
    """OHLC walk where every bar has true range exactly 2 (no gaps): with
    median close < 100 the leg floor is exactly 6.0 price units."""

    def __init__(self, p):
        self.p, self.rows = p, []

    def flat(self, n=1):
        self.rows += [(self.p, self.p + 1, self.p - 1, self.p)] * n
        return self

    def up(self, n=1):        # +2/bar: o=l=prev close, h=c=prev close+2
        for _ in range(n):
            self.rows.append((self.p, self.p + 2, self.p, self.p + 2))
            self.p += 2
        return self

    def down(self, n=1):      # -2/bar mirror
        for _ in range(n):
            self.rows.append((self.p, self.p, self.p - 2, self.p - 2))
            self.p -= 2
        return self

    def raw(self, o, h, l, c):
        self.rows.append((o, h, l, c))
        self.p = c
        return self

    def candles(self):
        return [bar(i, *r) for i, r in enumerate(self.rows)]


def ext(levels, kind=None):
    out = [lv for lv in levels if lv.kind in (LevelKind.EXT_H, LevelKind.EXT_L)]
    return [lv for lv in out if lv.kind is kind] if kind else out


# Scenario B: boundary L(94)@0, H(103)@17 conf@20, bounce, lower-low
# replacement, L(93)@26 conf@29, H(101)@30 conf@33, trailing pending low.
def tape_b():
    return (Tape(95).flat(14).up(4)      # closes 97 99 101 103 (peak idx 17)
            .down(3)                     # lows 101 99 97 -> H(103) confirms idx 20
            .up(2)                       # bounce to 101: reversal 4 < 6
            .down(4)                     # lows 99 97 95 93: pending low replaced
            .up(3)                       # highs 95 97 99: 99-93=6 -> L(93) confirms
            .up(1).down(3)               # to 101, lows 99 97 95 -> H(101) confirms
            .candles())


def test_registered_and_returns_no_evidence():
    assert REGISTRY["extremes"] is ExtremesDetector
    det = ExtremesDetector({})
    ctx = ctx_at(tape_b())
    assert det.detect(ctx) == []          # infrastructure: levels, no Evidence
    assert ext(ctx.levels)                # side channel did its job


def test_pivot_confirmed_only_after_reversal_leg_completes():
    det = ExtremesDetector({})
    candles = tape_b()
    levels = []
    for i in range(len(candles)):         # closed-candle prefixes, shared levels
        det.detect(ctx_at(candles[: i + 1], levels))
        highs = ext(levels, LevelKind.EXT_H)
        if i < 20:                        # reversal from 103 reaches 6 at idx 20
            assert not highs, f"H must not exist at bar {i}"
        else:
            assert any(lv.born == candles[17].ts for lv in highs)
    [h103] = [lv for lv in ext(levels, LevelKind.EXT_H) if lv.born == candles[17].ts]
    assert not h103.meta["boundary"]
    assert h103.zone[1] == tick(103)      # band top = wick high = pivot price


def test_alternation_lower_low_replaces_pending_pivot():
    det = ExtremesDetector({})
    candles = tape_b()
    levels = []
    for i in range(len(candles)):
        det.detect(ctx_at(candles[: i + 1], levels))
        interior = [lv for lv in ext(levels, LevelKind.EXT_L)
                    if not lv.meta["boundary"]]
        if i < 29:                        # 99 - 93 = 6 first reached at idx 29
            assert not interior, f"L must not exist at bar {i}"
    [low] = [lv for lv in ext(levels, LevelKind.EXT_L) if not lv.meta["boundary"]]
    assert low.born == candles[26].ts     # the DEEPEST low won (93, not 97/95)
    assert low.zone[0] == tick(93)
    # the first dip (97 @ idx 20) and intermediate 95 never became pivots
    assert not any(lv.born in (candles[20].ts, candles[25].ts)
                   for lv in ext(levels, LevelKind.EXT_L))


def test_master_vs_major_and_rank_metric():
    det = ExtremesDetector({})
    ctx = ctx_at(tape_b())
    det.detect(ctx)
    by_born = {lv.born: lv for lv in ext(ctx.levels)}
    ts = lambda i: T0 + timedelta(hours=i)
    b94, h103, l93, h101 = (by_born[ts(i)] for i in (0, 17, 26, 30))
    assert b94.meta["boundary"] and not b94.meta["master"]     # 94 > master 93
    assert h103.meta["master"] and not h101.meta["master"]     # window max high
    assert l93.meta["master"]                                  # window min low
    # rank = min(leg_in, leg_out) / ATR, ATR == 2 exactly on this tape
    assert b94.meta["rank_atr"] == pytest.approx(4.5)   # min(-, 103-94)/2
    assert h103.meta["rank_atr"] == pytest.approx(4.5)  # min(9, 10)/2
    assert l93.meta["rank_atr"] == pytest.approx(4.0)   # min(10, 8)/2
    assert h101.meta["rank_atr"] == pytest.approx(3.0)  # min(8, 101-95)/2
    # the trailing pending extreme (low 95) is NOT a level yet
    assert len(ext(ctx.levels)) == 4


def test_wick_band_is_body_top_of_cluster_to_wick_high():
    # neighbour bar's close (104.4) is the highest body edge of the cluster;
    # peak bar wicks to 105 -> band = [104.4, 105].
    candles = (Tape(95).flat(14).up(4)                 # closes ..101, 103
               .raw(103, 104.4, 102.4, 104.4)          # body top 104.4, joins
               .raw(104.4, 105, 103, 103.8)            # peak: wick 105
               .down(3)                                # 101.8 99.8 97.8 -> confirm
               .candles())
    det = ExtremesDetector({})
    levels = []
    for i in range(len(candles)):
        det.detect(ctx_at(candles[: i + 1], levels))
        if i < 21:                        # 105 - 97.8 = 7.2 >= 6 only at idx 21
            assert not ext(levels, LevelKind.EXT_H)
    [high] = ext(levels, LevelKind.EXT_H)
    assert high.born == candles[19].ts
    assert high.zone == (tick("104.40"), tick("105"))


def test_replaced_pivot_id_is_marked_dead_and_prehistory_untouched():
    candles = tape_b()
    stale = Level(id=f"X-EXT_H-1h-{candles[21].ts.isoformat()}", symbol="X",
                  kind=LevelKind.EXT_H, zone=(tick(99), tick(101)),
                  born=candles[21].ts, tf=H1)
    old_ts = T0 - timedelta(days=1)
    prehistoric = Level(id=f"X-EXT_H-1h-{old_ts.isoformat()}", symbol="X",
                        kind=LevelKind.EXT_H, zone=(tick(99), tick(101)),
                        born=old_ts, tf=H1)
    ctx = ctx_at(candles, levels=[stale, prehistoric])
    ExtremesDetector({}).detect(ctx)
    assert stale.state is LevelState.DEAD          # not in the recompute
    assert prehistoric.state is LevelState.ACTIVE  # born before visible window
    assert all(lv.state is LevelState.ACTIVE for lv in ext(ctx.levels)
               if lv not in (stale, prehistoric))


def load_gold():
    with open(FIXTURE) as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 399
    return [Candle("HEROMOTOCO", H1, datetime.fromisoformat(r["ts"]),
                   tick(r["open"]), tick(r["high"]), tick(r["low"]),
                   tick(r["close"]), int(r["volume"])) for r in rows]


GOLD = [  # EXTREMES.md chart A hand-circles reproduced at the 4.7% floor
    (date(2026, 5, 6), LevelKind.EXT_L, 4953.0),
    (date(2026, 5, 7), LevelKind.EXT_H, 5458.0),
    (date(2026, 5, 14), LevelKind.EXT_L, 4880.5),
    (date(2026, 6, 2), LevelKind.EXT_L, 4747.1),
    (date(2026, 6, 30), LevelKind.EXT_L, 4672.5),
]


def pivot_price(lv):
    """The pivot extreme is the wick edge of the band."""
    return float(lv.zone[1] if lv.kind is LevelKind.EXT_H else lv.zone[0])


def test_gold_label_parity_heromotoco_at_taught_floor():
    candles = load_gold()
    ctx = StockContext(symbol="HEROMOTOCO", now=candles[-1].ts + timedelta(hours=1),
                       candles=SeqView(candles), levels=[], evidence_history=[],
                       day=DayState(session_date=candles[-1].ts.date()))
    ExtremesDetector({"leg_pct": 4.7}).detect(ctx)
    for d, kind, price in GOLD:
        hits = [lv for lv in ext(ctx.levels, kind) if lv.born.date() == d
                and abs(pivot_price(lv) - price) / price <= 0.003]
        assert hits, f"gold pivot {d} {kind.name} ~{price} not found"
    # masters per EXTREMES.md: 07/05 H and 30/06 L
    masters = {(lv.kind, lv.born.date()) for lv in ext(ctx.levels)
               if lv.meta["master"]}
    assert masters == {(LevelKind.EXT_H, date(2026, 5, 7)),
                       (LevelKind.EXT_L, date(2026, 6, 30))}
    # the 07 Jul high is still PENDING at window end -> must NOT be emitted
    assert not any(lv.born.date() == date(2026, 7, 7)
                   for lv in ext(ctx.levels, LevelKind.EXT_H))


def test_frozen_default_floor_absorbs_sub_floor_legs():
    candles = load_gold()
    ctx = StockContext(symbol="HEROMOTOCO", now=candles[-1].ts + timedelta(hours=1),
                       candles=SeqView(candles), levels=[], evidence_history=[],
                       day=DayState(session_date=candles[-1].ts.date()))
    ExtremesDetector({}).detect(ctx)      # defaults: leg_pct 6.0, tf 1h
    assert all(lv.tf is H1 for lv in ext(ctx.levels))
    # 14 May low's legs are sub-6% -> absorbed at the frozen floor
    assert not any(lv.born.date() == date(2026, 5, 14) for lv in ext(ctx.levels))
    # while both master extremes survive
    masters = {(lv.kind, lv.born.date()) for lv in ext(ctx.levels)
               if lv.meta["master"]}
    assert masters == {(LevelKind.EXT_H, date(2026, 5, 7)),
                       (LevelKind.EXT_L, date(2026, 6, 30))}
