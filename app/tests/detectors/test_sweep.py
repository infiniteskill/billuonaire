"""Tests for the sweep detector (trader/detectors/sweep.py).
Binding design: task-6 brief (quality formula, trap chains, dedupe)."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from trader.detectors.sweep import SweepDetector
from trader.engine.context import DayState, StockContext
from trader.models.candle import TICK, Candle, Timeframe, tick
from trader.models.evidence import Direction, Evidence
from trader.models.level import Level, LevelKind, LevelState
from trader.store.candles import CandleStore

IST = ZoneInfo("Asia/Kolkata")
SESSION_START = datetime(2026, 7, 15, 9, 15, tzinfo=IST)
M5 = Timeframe.M5


def bar_ts(i):
    return SESSION_START + timedelta(minutes=i * M5.minutes)


def make_ctx(n_bars=6, levels=None, history=None):
    """n_bars closed flat M5 bars; latest closed bar ts == bar_ts(n_bars-1)."""
    store = CandleStore("/nonexistent")
    for i in range(n_bars * M5.minutes):
        ts = SESSION_START + timedelta(minutes=i)
        store.add(Candle("X", Timeframe.M1, ts, tick(100), tick(101), tick(99), tick(100), 10))
    now = SESSION_START + timedelta(minutes=n_bars * M5.minutes)
    return StockContext(
        symbol="X", now=now, candles=store.view("X", now),
        levels=levels if levels is not None else [],
        evidence_history=history if history is not None else [],
        day=DayState(session_date=now.date()),
    )


def lvl(kind, swept_ts, reclaim_ts=None, touches=1, born=None):
    lv = Level(
        id=f"X-{kind.name}-1", symbol="X", kind=kind,
        zone=(tick(100) - TICK, tick(100) + TICK),
        born=born or SESSION_START, tf=None, touches=touches,
    )
    lv.record_state(swept_ts, LevelState.SWEPT)
    if reclaim_ts:
        lv.record_state(reclaim_ts, LevelState.RECLAIMED)
    return lv


def test_pdl_sweep_exact_score_and_evidence_fields():
    # 0.4 base + 0.25*0.6 (PDL pool) + 0.15 daily kind = 0.70; no other bonus
    ctx = make_ctx(levels=[lvl(LevelKind.PDL, bar_ts(5))])
    [ev] = SweepDetector({}).detect(ctx)
    assert ev.detector == "sweep"
    assert ev.direction is Direction.LONG
    assert ev.strength == pytest.approx(0.70)
    assert ev.zone == ctx.levels[0].zone
    assert ev.ttl_candles == 18
    assert ev.meta == {"level_id": "X-PDL-1", "kind": "PDL", "chain_depth": 1}


def test_fast_reclaim_adds_bonus():
    # ONE detector instance sees the episode across two ticks: swept tick
    # emits the base evidence, then the reclaim tick (<=3 candles later)
    # emits a second, upgraded evidence -- not a bonus folded into the first.
    det = SweepDetector({})
    level = lvl(LevelKind.PDL, bar_ts(3))
    ctx1 = make_ctx(n_bars=4, levels=[level])
    [ev1] = det.detect(ctx1)
    assert ev1.strength == pytest.approx(0.70)
    assert "upgrade" not in ev1.meta

    level.record_state(bar_ts(5), LevelState.RECLAIMED)
    ctx2 = make_ctx(n_bars=6, levels=[level])
    [ev2] = det.detect(ctx2)
    assert ev2.strength == pytest.approx(0.80)
    assert ev2.meta["upgrade"] is True
    assert ev2.meta["level_id"] == "X-PDL-1"


def test_reclaim_upgrade_caps_at_one():
    # EQL, touches=5 (pool maxed), born == ctx1.now (recency=1.0), plus a
    # chain-depth>=2 bonus -> base = 0.4 + 0.25*1.0 + 0.2 + 0.1 = 0.95.
    # Upgrade would be 1.05; must cap at 1.0 exactly.
    det = SweepDetector({})
    prior = Evidence(detector="sweep", direction=Direction.SHORT, strength=0.7,
                     zone=(tick(105), tick(105)), ts=bar_ts(1), ttl_candles=18,
                     meta={"level_id": "X-PDH-0", "kind": "PDH", "chain_depth": 1})
    born = SESSION_START + timedelta(minutes=4 * M5.minutes)  # == ctx1.now
    level = lvl(LevelKind.EQL, bar_ts(3), touches=5, born=born)
    ctx1 = make_ctx(n_bars=4, levels=[level], history=[prior])
    [ev1] = det.detect(ctx1)
    assert ev1.strength == pytest.approx(0.95)

    level.record_state(bar_ts(5), LevelState.RECLAIMED)
    ctx2 = make_ctx(n_bars=6, levels=[level], history=[prior])
    [ev2] = det.detect(ctx2)
    assert ev2.strength == pytest.approx(1.0)
    assert ev2.meta["upgrade"] is True


def test_touches_bonus():
    # 0.70 + 0.2 (touches>=3) = 0.90
    ctx = make_ctx(levels=[lvl(LevelKind.PDL, bar_ts(5), touches=3)])
    [ev] = SweepDetector({}).detect(ctx)
    assert ev.strength == pytest.approx(0.90)


def test_eql_pool_strength_recomputed():
    # EQL touches=2 born=now: pool = 2/5*0.7 + 1.0*0.3 = 0.58 -> 0.4+0.25*0.58
    ctx = make_ctx(levels=[])
    ctx.levels.append(lvl(LevelKind.EQL, bar_ts(5), touches=2, born=ctx.now))
    [ev] = SweepDetector({}).detect(ctx)
    assert ev.strength == pytest.approx(0.4 + 0.25 * 0.58)


def test_direction_both_sides():
    ctx = make_ctx(levels=[lvl(LevelKind.PDH, bar_ts(5)), lvl(LevelKind.PDL, bar_ts(5))])
    evs = {e.meta["kind"]: e for e in SweepDetector({}).detect(ctx)}
    assert evs["PDH"].direction is Direction.SHORT
    assert evs["PDL"].direction is Direction.LONG


def test_chain_depth_2_bonus():
    # prior opposite (SHORT) sweep evidence within the 20-candle window
    prior = Evidence(detector="sweep", direction=Direction.SHORT, strength=0.7,
                     zone=(tick(105), tick(105)), ts=bar_ts(3), ttl_candles=18,
                     meta={"level_id": "X-PDH-0", "kind": "PDH", "chain_depth": 1})
    ctx = make_ctx(levels=[lvl(LevelKind.PDL, bar_ts(5))], history=[prior])
    [ev] = SweepDetector({}).detect(ctx)
    assert ev.meta["chain_depth"] == 2
    assert ev.strength == pytest.approx(0.80)  # 0.70 + 0.1 chain bonus


def test_same_direction_history_does_not_chain():
    prior = Evidence(detector="sweep", direction=Direction.LONG, strength=0.7,
                     zone=(tick(95), tick(95)), ts=bar_ts(3), ttl_candles=18,
                     meta={"level_id": "X-PDL-0", "kind": "PDL", "chain_depth": 1})
    ctx = make_ctx(levels=[lvl(LevelKind.PDL, bar_ts(5))], history=[prior])
    [ev] = SweepDetector({}).detect(ctx)
    assert ev.meta["chain_depth"] == 1


def test_dedupe_same_episode():
    det = SweepDetector({})
    ctx = make_ctx(levels=[lvl(LevelKind.PDL, bar_ts(5))])
    assert len(det.detect(ctx)) == 1
    assert det.detect(ctx) == []


def test_no_trigger_when_swept_old():
    # SWEPT two candles ago, never reclaimed -> not this candle, no evidence
    ctx = make_ctx(levels=[lvl(LevelKind.PDL, bar_ts(3))])
    assert SweepDetector({}).detect(ctx) == []


def test_no_trigger_on_slow_reclaim():
    # reclaim this candle but sweep 4 candles earlier (> reclaim_bonus_candles)
    ctx = make_ctx(levels=[lvl(LevelKind.PDL, bar_ts(1), reclaim_ts=bar_ts(5))])
    assert SweepDetector({}).detect(ctx) == []
