"""ConfluenceEngine unit tests: hand-built evidence sets, exact arithmetic.

Contexts are built by hand (candles=None); ``ctx.atr`` is stubbed per
instance so the merge-gap tolerance is exact. Weights below sum to 100 so
``enabled_weights()`` renormalization is the identity.
"""

import json
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from trader.config import Settings
from trader.engine.confluence import ConfluenceEngine
from trader.engine.context import DayState, StockContext
from trader.models.evidence import Direction, Evidence
from trader.models.level import Level, LevelKind, LevelState

IST = ZoneInfo("Asia/Kolkata")
DAY = date(2026, 7, 15)
NOW = datetime.combine(DAY, time(11, 0), tzinfo=IST)
LONG, SHORT, NEUTRAL = Direction.LONG, Direction.SHORT, Direction.NEUTRAL
CONFIG = Path(__file__).resolve().parent.parent.parent / "trader" / "templates" / "config.baseline.json"
WEIGHTS = {"sweep": 20, "structure": 15, "orderblock": 15, "fvg": 10,
           "liquidity": 10, "wyckoff": 10, "breaker": 10, "compression": 5,
           "timestats": 5}  # sum 100


def engine() -> ConfluenceEngine:
    raw = json.loads(CONFIG.read_text())
    raw["confluence"]["weights"] = WEIGHTS
    raw["detectors"]["enabled"] = list(WEIGHTS) + ["volume", "swings", "index"]
    return ConfluenceEngine(Settings.model_validate(raw))


def ev(det: str, dirn: Direction, s: float, lo="100", hi="101",
       ts: datetime = NOW, ttl: int = 12) -> Evidence:
    return Evidence(detector=det, direction=dirn, strength=s,
                    zone=(Decimal(lo), Decimal(hi)), ts=ts, ttl_candles=ttl,
                    meta={"event": "event"})


def ctx(levels=(), template="TREND", atr="2", index=None) -> StockContext:
    c = StockContext(symbol="X", now=NOW, candles=None, levels=list(levels),
                     evidence_history=[],
                     day=DayState(session_date=DAY, template=template), index=index)
    c.atr = lambda tf, period=14: Decimal(atr)  # dataclass: instance override
    return c


def score(evidence, htf=("UNCLEAR", 0.0), m15=LONG, **kw):
    return engine().score(ctx(**kw), evidence, htf, m15)


def level(kind: LevelKind, *states: LevelState, lo="100", hi="101",
          touches: int = 0) -> Level:
    lv = Level(id=f"X-{kind.name}", symbol="X", kind=kind,
               zone=(Decimal(lo), Decimal(hi)), born=NOW, tf=None,
               touches=touches)
    for st in states:
        lv.record_state(NOW, st)
    return lv


# LONG trio: sweep 20x0.9=18, structure 15x0.8=12, orderblock 15x0.6=9 => 39
TRIO = [ev("sweep", LONG, 0.9), ev("structure", LONG, 0.8),
        ev("orderblock", LONG, 0.6)]


# ------------------------------------------------------------ Layer 1 cluster

def test_cluster_merges_overlap_and_small_gap_splits_large():
    zones = score([ev("sweep", LONG, 0.9, "100", "101"),           # overlap
                   ev("structure", LONG, 0.8, "100.5", "101.4"),   # gap 0.4<=0.5
                   ev("orderblock", LONG, 0.6, "101.9", "102.5"),  # gap 2.5>0.5
                   ev("fvg", LONG, 0.5, "105", "106")], atr="2")
    assert [z.zone for z in sorted(zones, key=lambda z: z.zone[0])] == [
        (Decimal("100"), Decimal("102.5")), (Decimal("105"), Decimal("106"))]


def test_gap_just_over_quarter_atr_splits():
    zones = score([ev("sweep", LONG, 0.9, "100", "101"),
                   ev("structure", LONG, 0.8, "101.6", "102")], atr="2")
    assert len(zones) == 2  # gap 0.6 > 0.25x2


def test_same_detector_dedupe_keeps_best_strength():
    z, = score([ev("sweep", LONG, 0.5), ev("sweep", LONG, 0.9)])
    assert z.members == [("sweep", "event", 0.9)]
    assert z.raw == pytest.approx(18.0)  # 20 x 0.9 once


# --------------------------------------------------------- directional mass

def test_direction_subtraction_exact():
    z, = score(TRIO + [ev("fvg", SHORT, 0.5)])
    assert z.direction is LONG
    assert z.raw == pytest.approx(39 - 0.8 * 5)  # loser at 0.8x


def test_neutral_pool_added_to_winner():
    z, = score(TRIO + [ev("fvg", SHORT, 0.5), ev("liquidity", NEUTRAL, 0.4)])
    assert z.raw == pytest.approx(39 - 4 + 0.5 * 10 * 0.4)  # pool 2 to LONG


def test_volume_flat_boost_direction_ignored():
    z, = score(TRIO + [ev("volume", SHORT, 0.9)])  # SHORT dir contributes 0 mass
    assert z.direction is LONG and z.raw == pytest.approx(39 + 3)
    assert z.distinct == 3  # volume never counts distinct


def test_distinct_below_three_unarmable_but_returned():
    z, = score([ev("sweep", LONG, 0.9), ev("structure", LONG, 0.8)])
    assert z.distinct == 2 and z.final == 0.0
    assert z.raw == pytest.approx(30.0) and len(z.members) == 2  # journal keeps it


# ------------------------------------------------------------ Layer 2 align

def test_htf_markdown_zeroes_long_markup_zeroes_short():
    assert score(TRIO, htf=("MARKDOWN", 0.9))[0].final == 0.0
    assert score(TRIO, htf=("MARKUP", 0.9))[0].final > 0
    short_trio = [ev("sweep", SHORT, 0.9), ev("structure", SHORT, 0.8),
                  ev("orderblock", SHORT, 0.6)]
    assert score(short_trio, htf=("MARKUP", 0.9), m15=SHORT)[0].final == 0.0


def test_m15_trend_oppose_zero_neutral_dampens():
    assert score(TRIO, m15=SHORT)[0].final == 0.0
    agree, neutral = score(TRIO, m15=LONG)[0], score(TRIO, m15=NEUTRAL)[0]
    # NEUTRAL m15: align 0.8 AND TREND play (=m15) no longer matches => x0.5
    assert neutral.final == pytest.approx(agree.final * 0.8 * 0.5, abs=0.06)


# ---------------------------------------------------------- Layer 3 context

def test_time_mult_from_latest_timestats_default_half():
    base = score(TRIO)[0]                                     # default 0.5
    zones = score(TRIO + [ev("timestats", NEUTRAL, 0.7, "200", "201", ttl=1)])
    main = max(zones, key=lambda z: z.final)
    assert base.final == pytest.approx(39 * 0.5 * 1.0, abs=0.05)
    assert main.final == pytest.approx(39 * 0.7 * 1.0, abs=0.05)


def test_timestats_single_count_no_cluster_mass():
    """Audit 5: timestats is the global time multiplier ONLY -- its Evidence
    adds no neutral-pool mass to the cluster it lands in (it used to count
    twice: pool mass AND multiplier)."""
    z, = score(TRIO + [ev("timestats", NEUTRAL, 0.8)])   # same 100-101 zone
    assert z.raw == pytest.approx(39.0)                  # no +0.5 x 5 x 0.8
    assert z.mults["time"] == 0.8                        # multiplier kept
    assert z.distinct == 3                               # never counts distinct


def test_template_unclassified_zeroes_range_pin_halves():
    assert score(TRIO, template="UNCLASSIFIED")[0].final == 0.0
    assert score(TRIO, template="RANGE_PIN")[0].final == pytest.approx(
        score(TRIO)[0].final * 0.5, abs=0.06)  # no edge nearby: not a fade


def test_range_pin_fade_of_or_edge_full_score():
    # zone 100-101, OR_L 98-98.5: gap 1.5 <= 1xATR(2), LONG points away => 1.0
    orl = level(LevelKind.OPEN_RANGE_L, lo="98", hi="98.5")
    assert score(TRIO, template="RANGE_PIN",
                 levels=[orl])[0].mults["template"] == 1.0
    # LONG INTO the upper edge is a breakout attempt, not a fade => 0.5
    orh = level(LevelKind.OPEN_RANGE_H, lo="101.2", hi="101.5")
    assert score(TRIO, template="RANGE_PIN",
                 levels=[orh])[0].mults["template"] == 0.5
    # right direction but edge 9.5 away > 1xATR => 0.5
    far = level(LevelKind.OPEN_RANGE_L, lo="90", hi="90.5")
    assert score(TRIO, template="RANGE_PIN",
                 levels=[far])[0].mults["template"] == 0.5


def test_range_pin_fade_of_day_extreme_full_score():
    from types import SimpleNamespace
    day = lambda h, lo: SimpleNamespace(today=lambda tf: [    # noqa: E731
        SimpleNamespace(high=Decimal(h), low=Decimal(lo))])
    c = ctx(template="RANGE_PIN")
    c.candles = day("110", "99")       # day low 99 inside zone: LONG fades it
    assert engine().score(c, TRIO, ("UNCLEAR", 0.0),
                          LONG)[0].mults["template"] == 1.0
    c2 = ctx(template="RANGE_PIN")
    c2.candles = day("101.5", "95")    # near edge is the HIGH: LONG not a fade
    assert engine().score(c2, TRIO, ("UNCLEAR", 0.0),
                          LONG)[0].mults["template"] == 0.5


def test_trap_reversal_play_away_from_swept_edge():
    orl = level(LevelKind.OPEN_RANGE_L, LevelState.SWEPT, LevelState.RECLAIMED,
                lo="98", hi="98.5")
    matched = score(TRIO, template="TRAP_REVERSAL", levels=[orl])[0]
    off = score([ev("sweep", SHORT, 0.9), ev("structure", SHORT, 0.8),
                 ev("orderblock", SHORT, 0.6)], m15=SHORT,
                template="TRAP_REVERSAL", levels=[orl])[0]
    assert matched.final == pytest.approx(39 * 0.5, abs=0.05)      # play LONG
    assert off.final == pytest.approx(39 * 0.5 * 0.5, abs=0.06)    # off-template


def test_obviousness_unswept_obvious_haircut_reclaimed_boost():
    plain = score(TRIO)[0].final
    unswept = score(TRIO, levels=[level(LevelKind.ROUND)])[0].final
    reclaimed = score(TRIO, levels=[level(
        LevelKind.ROUND, LevelState.SWEPT, LevelState.RECLAIMED)])[0].final
    touched = score(TRIO, levels=[level(LevelKind.SWING_H, touches=3)])[0].final
    assert unswept == touched == pytest.approx(plain * 0.85, abs=0.05)
    assert reclaimed == pytest.approx(plain * 1.15, abs=0.05)


def test_counter_index_haircut_halves_final():
    from trader.engine.context import IndexView
    base = score(TRIO)[0]
    z = score(TRIO, index=IndexView(SHORT, "MARKDOWN", 0.6))[0]   # LONG vs SHORT idx
    assert z.mults["index"] == 0.5
    assert z.final == pytest.approx(base.final * 0.5, abs=0.06)
    for idx in (None,                                  # no index context
                IndexView(LONG, "MARKUP", 0.9),        # aligned
                IndexView(SHORT, "MARKDOWN", 0.4),     # opposing but weak
                IndexView(NEUTRAL, "RANGE", 0.9)):     # trendless
        assert score(TRIO, index=idx)[0].mults["index"] == 1.0


# ------------------------------------------------------------ ttl windowing

def test_expired_evidence_excluded_ttl_zero_current_only():
    old = ev("sweep", LONG, 0.9, ts=NOW - timedelta(minutes=65), ttl=12)
    live = ev("sweep", LONG, 0.9, ts=NOW - timedelta(minutes=60), ttl=12)
    fresh0 = ev("fvg", LONG, 0.5, ts=NOW, ttl=0)
    stale0 = ev("liquidity", LONG, 0.5, ts=NOW - timedelta(minutes=5), ttl=0)
    z, = score([old, live, fresh0, stale0])
    assert [m[0] for m in z.members] == ["fvg", "sweep"]
    assert score([old, stale0]) == []


# ----------------------------------------------------------- full stack e2e

def test_end_to_end_exact_final():
    evidence = TRIO + [ev("fvg", SHORT, 0.5), ev("liquidity", NEUTRAL, 0.4),
                       ev("volume", LONG, 0.8),
                       ev("timestats", NEUTRAL, 0.7, "200", "201", ttl=1)]
    orl = level(LevelKind.OPEN_RANGE_L, LevelState.SWEPT, LevelState.RECLAIMED,
                lo="98", hi="98.5")
    rnd = level(LevelKind.ROUND, LevelState.SWEPT, LevelState.RECLAIMED,
                lo="100.4", hi="100.6")
    zones = engine().score(ctx(levels=[orl, rnd], template="TRAP_REVERSAL"),
                           evidence, ("MARKUP", 0.6), LONG)
    z = zones[0]  # sorted desc: armable zone first
    # raw = 39 - 0.8x5 + 2 (+3 volume) = 40; final = 40 x 1 x 0.7 x 1 x 1.15
    assert z.direction is LONG and z.distinct == 3
    assert z.raw == pytest.approx(40.0)
    assert z.final == 32.2
    assert ("sweep", "event", 0.9) in z.members
