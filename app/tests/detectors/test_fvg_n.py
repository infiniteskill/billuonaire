"""Tests for the fvg_n detector (trader/detectors/fvg_n.py).
Binding design: runs/taught/TUNE.md frozen config -- generalized MERGED
fair-value gaps. Burst of 1..6 middle candles (mmax=6), gap = flanking
wicks non-overlap with every middle CLOSING beyond the near flank wick,
min gap 0 (any size). USER MERGE RULE: continuous/overlapping fragments
from the same displacement burst = ONE zone, box = union. BREAK-DEPTH LAW:
killed only by a close through the far edge by >= 0.5xATR(14); shallower
closes = second life. Kill flips the box to an iFVG (opposite direction,
same box, same law). Evidence on first armed retest: continuation of the
birth impulse, edge entry, meta {"event","sl","sl_floor"}.

Fixture geometry: one M1 candle per M5 bucket start -> the derived M5 bar
equals it exactly. FLAT primes ATR(M5,14) == 2 after 15 closed candles."""

from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from trader.detectors.base import REGISTRY
from trader.detectors.fvg_n import FvgNDetector, FvgZones
from trader.engine.context import DayState, StockContext
from trader.models.candle import Candle, Timeframe, tick
from trader.models.evidence import Direction
from trader.store.candles import CandleStore

IST = ZoneInfo("Asia/Kolkata")
SESSION_START = datetime(2026, 7, 15, 9, 15, tzinfo=IST)
M5 = Timeframe.M5
DATA = Path(__file__).resolve().parents[3] / "data" / "long5m" / "HDFCBANK.csv"

FLAT = (100, 101, 99, 100)          # doji, TR=2, primes ATR(M5,14) == 2

# --- bull burst: 3-candle gap [101, 103] (m=1: flank H 101 / flank L 103) ---
GAP2 = (100, 106, 100, 106)          # middle, closes 106 > 101 (displacement)
GAP3 = (106, 108, 103, 107)          # right flank, low 103 -> zone (101, 103)
BRKR = (107, 110, "100.9", 101)      # burst breaker: close 101 == lo (no kill),
                                     # tall high blocks later flanks
REC = (101, 106, "100.8", "105.5")   # recovery (touches unarmed: no event)
ARM = ("105.5", 107, "103.5", 106)   # low 103.5 > 103 -> fully left = armed
TOUCH = (106, "106.5", "102.5", 104)  # low 102.5 <= 103 -> first retest

SHAL = (107, 110, "99.4", 100)       # close 100: 1.0 below lo < 0.5xATR -> alive
REC2 = (100, 106, "99.9", "105.5")
DEEP = (107, 110, 97, 98)            # close 98: 3.0 below lo >= 0.5xATR -> kill
IARM = (98, "100.5", "97.5", 100)    # high 100.5 < 101 -> iFVG armed
ITOUCH = (100, "101.8", 99, "101.5")  # high 101.8 >= 101 -> iFVG retest

# --- bear mirror: gap (97, 99) (flank L 99 / flank H 97) ---
BGAP2 = (100, 100, 94, 94)
BGAP3 = (94, 97, 92, 93)
BBRKR = (93, "99.1", 90, "99.1")     # shallow far-edge close-through, deep low
BREC = ("99.1", "99.2", 94, 95)
BARM = (95, "96.5", 93, 94)          # high 96.5 < 97 -> armed
BTOUCH = (94, "97.5", "93.5", 95)    # high 97.5 >= 97 -> retest


def bar_ts(i):
    return SESSION_START + timedelta(minutes=i * M5.minutes)


def bar(i, o, h, l, c, v=10):
    return Candle("X", Timeframe.M1, bar_ts(i), tick(o), tick(h), tick(l), tick(c), v)


def make_store(bars):
    store = CandleStore("/nonexistent")
    for i, b in enumerate(bars):
        store.add(bar(i, *b))
    return store


def ctx_at(store, n_bars):
    now = bar_ts(n_bars)
    return StockContext(symbol="X", now=now, candles=store.view("X", now),
                        levels=[], evidence_history=[],
                        day=DayState(session_date=now.date()))


def run_to(det, store, n_last):
    """Tick every bar close up to n_last, asserting silence before it;
    return the final tick's output."""
    for n in range(15, n_last):
        assert det.detect(ctx_at(store, n)) == []
    return det.detect(ctx_at(store, n_last))


def test_registered():
    assert REGISTRY["fvg_n"] is FvgNDetector
    d = FvgNDetector({})
    assert d.params == {"tf": "5m", "mmax": 6, "depth_atr": 0.5,
                        "sl_atr_floor": 0.15, "min_gap_atr": 0.0}


def test_long_gap_retest_fires():
    store = make_store([FLAT] * 15 + [GAP2, GAP3, BRKR, REC, ARM, TOUCH])
    [ev] = run_to(FvgNDetector({}), store, 21)
    assert ev.detector == "fvg_n"
    assert ev.direction is Direction.LONG
    assert ev.zone == (tick(101), tick(103))
    assert ev.ttl_candles == 6
    assert ev.strength == 0.6
    assert ev.meta["event"] == "FVG_N_RETEST"
    assert ev.meta["sl"] == str(tick(101))   # below the zone (far edge, raw)


def test_bear_mirror():
    store = make_store([FLAT] * 15 + [BGAP2, BGAP3, BBRKR, BREC, BARM, BTOUCH])
    [ev] = run_to(FvgNDetector({}), store, 21)
    assert ev.direction is Direction.SHORT
    assert ev.zone == (tick(97), tick(99))
    assert ev.meta["event"] == "FVG_N_RETEST"
    assert ev.meta["sl"] == str(tick(99))    # above the zone


def test_merge_dedup_keeps_first_and_keeps_distinct():
    # Frozen DEDUP (ts2_lib.fvg_n_extra), NOT growing union: an m=2 fragment
    # whose window+band overlaps the strict-3 zone already birthed at the same
    # ending bar is DROPPED (box never grows into the mega-void a staircase
    # union produces); genuinely separate gaps (non-overlapping bands) stay
    # separate. Bars 15-17 leave two distinct bull gaps [101,104] and
    # [105,107] -- the 104..105 region is not a gap, so it is never bridged.
    rows = [FLAT] * 15 + [(100, 105, 100, 105), (105, 109, 104, 108),
                          (108, 112, 107, 111)]
    z = FvgZones()
    for i, r in enumerate(rows):
        z.step(bar_ts(i), *(tick(x) for x in r))
    bulls = sorted(((x.lo, x.hi) for x in z.zones
                    if x.kind == "FVG" and x.dir == 1))
    assert bulls == [(tick(101), tick(104)), (tick(105), tick(107))]


def test_second_life_shallow_close_through_keeps_zone():
    # SHAL closes 1.0 below the far edge; 0.5xATR > 1.0 there -> zone lives
    # and the later armed retest still fires (TUNE second-life law, t=10).
    store = make_store([FLAT] * 15 + [GAP2, GAP3, SHAL, REC2, ARM, TOUCH])
    [ev] = run_to(FvgNDetector({}), store, 21)
    assert ev.direction is Direction.LONG
    assert ev.zone == (tick(101), tick(103))
    assert ev.meta["event"] == "FVG_N_RETEST"


def test_deep_close_through_kills_and_flips_ifvg():
    # DEEP closes 3.0 below the far edge (>= 0.5xATR) -> FVG dead, iFVG born
    # (opposite direction, same box); retest from below fires SHORT.
    store = make_store([FLAT] * 15 + [GAP2, GAP3, DEEP, IARM, ITOUCH,
                                      ("101.5", 106, 101, 105)])
    det = FvgNDetector({})
    [ev] = run_to(det, store, 20)
    assert ev.direction is Direction.SHORT
    assert ev.zone == (tick(101), tick(103))   # same box
    assert ev.meta["event"] == "IFVG_RETEST"
    assert ev.meta["sl"] == str(tick(103))     # above the zone
    assert det.detect(ctx_at(store, 21)) == []  # dead FVG never fires again


def test_meta_schema_contract():
    store = make_store([FLAT] * 15 + [GAP2, GAP3, BRKR, REC, ARM, TOUCH])
    [ev] = run_to(FvgNDetector({}), store, 21)
    assert set(ev.meta) == {"event", "sl", "sl_floor"}
    for k in ("sl", "sl_floor"):
        assert isinstance(ev.meta[k], str)
        Decimal(ev.meta[k])
    assert ev.meta["sl_floor"] == str(Decimal("0.15") * ctx_at(store, 21).atr(M5))
    assert 0.0 <= ev.strength <= 1.0


# ---------------------------------------------------------------- gold labels

LABELS = [  # (dir, lo, hi, born date) -- user's hand-marked HDFCBANK 30m FVGs
    (1, Decimal("767.0"), Decimal("770.4"), date(2026, 5, 5)),
    (1, Decimal("752.3"), Decimal("767.1"), date(2026, 5, 14)),
    (1, Decimal("759.4"), Decimal("769.5"), date(2026, 5, 22)),
    (1, Decimal("801.5"), Decimal("820.8"), date(2026, 7, 6)),
    (-1, Decimal("816"), Decimal("829"), date(2026, 7, 8)),   # 08/09 window
]


def hdfc_30m():
    """data/long5m/HDFCBANK.csv resampled 5m -> 30m (session-anchored 09:15)."""
    import csv
    out = []
    with DATA.open() as f:
        for r in csv.DictReader(f):
            ts = datetime.fromisoformat(r["ts"])
            key = (ts.date(), (ts.hour * 60 + ts.minute - 555) // 30)
            o, h, l, c = (Decimal(r[k]) for k in ("open", "high", "low", "close"))
            if out and out[-1][0] == key:
                _, pts, po, ph, pl, _ = out[-1]
                out[-1] = (key, pts, po, max(ph, h), min(pl, l), c)
            else:
                out.append((key, ts, o, h, l, c))
    return [row[1:] for row in out]


def test_hdfcbank_gold_labels():
    z = FvgZones()
    for ts, o, h, l, c in hdfc_30m():
        z.step(ts, o, h, l, c)
    fvgs = [x for x in z.zones if x.kind == "FVG"]
    for d, lo, hi, born in LABELS:
        hits = [x for x in fvgs if x.dir == d
                and abs(x.lo - lo) / lo <= Decimal("0.005")
                and abs(x.hi - hi) / hi <= Decimal("0.005")
                and abs((x.born.date() - born).days) <= 2]
        assert hits, f"label {d:+d} [{lo}-{hi}] {born} not found"
