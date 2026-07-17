"""Phase-4 Task 3: EntryFSM -- stealth stops, opposing-map targets, triggers.

Fixture geometry: calm() candles have range 2 => ATR(14) = 2 exactly, so
buffer = 0.25*ATR = 0.50, chase tol = 0.1*ATR = 0.20, stop FLOOR =
min_stop_atr 1.0*ATR = 2.00 (tighter stops widen to it), max stop =
2.0*ATR = 4.00. LONG zone (98, 100) => entry CE 99.00; its natural stop
97.50 (risk 1.50) widens to the floor 97.00 (risk 2.00, qty 250).
capital 100000 x 0.5% => budget 500.
"""
import json
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from trader.config import Settings
from trader.engine.confluence import ScoredZone
from trader.engine.context import DayState, StockContext
from trader.engine.entry import EntryFSM, EntryState
from trader.models.candle import Candle, Timeframe, tick
from trader.models.evidence import Direction, Evidence
from trader.models.level import Level, LevelKind, LevelState
from trader.store.candles import CandleStore

IST = ZoneInfo("Asia/Kolkata")
CONFIG = Path(__file__).resolve().parents[2] / "config" / "config.json"
TODAY = datetime(2026, 7, 15, tzinfo=IST)
D = Decimal
SWEPT = [(TODAY, LevelState.SWEPT)]


@pytest.fixture
def fsm():
    settings = Settings.model_validate_json(CONFIG.read_text())
    return EntryFSM(settings, settings.market_spec())


def at(hh, mm):
    return TODAY.replace(hour=hh, minute=mm)


def m1(ts, o=100, h=101, lo=99, c=100):
    return Candle("X", Timeframe.M1, ts, tick(o), tick(h), tick(lo), tick(c), 100)


def calm(n=15):  # one M1 per M5 bucket, range 2 => ATR(14) = 2
    return [m1(at(9, 15) + timedelta(minutes=5 * i)) for i in range(n)]


def ctx_at(now, candles, levels, history=()):
    store = CandleStore("/nonexistent")
    for c in candles:
        store.add(c)
    return StockContext("X", now, store.view("X", now), list(levels),
                        list(history), DayState(session_date=now.date()))


def lvl(kind, lo, hi, state=LevelState.ACTIVE, hist=()):
    return Level(f"{kind.name}-{lo}", "X", kind, (D(lo), D(hi)), TODAY,
                 Timeframe.M5, state=state, state_history=list(hist))


def zone(lo, hi, dirn=Direction.LONG, final=72.5):
    return ScoredZone((D(lo), D(hi)), dirn, [], 3, 40.0, final,
                      {"align": 1.0, "time": 0.9})


def t_lvl():  # T1 source: 102.50 is 3.50 away >= 1.5R for floor risk 2.00
    return lvl(LevelKind.SWING_H, "102.50", "103.00")


# --- arm(): stop construction + qty ---

def test_arm_plain_stop_widens_to_cost_floor(fsm):
    # natural stop 97.50 (far edge 98 - 0.25*ATR, risk 1.50) is under the
    # 1.0*ATR floor: widened to CE - 2.00 = 97.00 and qty SHRINKS to
    # floor(500 / 2.00) = 250 (was 333 off the tight 1.50)
    r = fsm.arm(zone("98.00", "100.00"), ctx_at(at(11, 0), calm(), [t_lvl()]), 1000)
    assert r.armed and r.reason is None and fsm.state is EntryState.ARMED
    p = r.plan
    assert p.stop == D("97.00")
    assert p.meta["risk_pts"] == "2.00"
    assert p.qty == 250
    assert p.symbol == "X" and p.direction is Direction.LONG
    assert p.score == 72.5 and p.meta["mults"] == {"align": 1.0, "time": 0.9}


def test_arm_floor_widened_stop_resnaps_off_round(fsm):
    # the widened stop 97.00 lands ON a ROUND zone: re-snapped 3 ticks past
    # its far edge (96.85, never tighter) -- floor and anti-hunt compose;
    # qty shrinks further to floor(500 / 2.15) = 232
    levels = [lvl(LevelKind.ROUND, "97.00", "97.00"), t_lvl()]
    p = fsm.arm(zone("98.00", "100.00"), ctx_at(at(11, 0), calm(), levels), 1000).plan
    assert p.stop == D("96.85")
    assert p.meta["risk_pts"] == "2.15"
    assert p.qty == 232


def test_arm_sweep_trap_round_snap_targets_decimal(fsm):
    levels = [lvl(LevelKind.SWING_L, "97.40", "98.50", LevelState.SWEPT, SWEPT),
              lvl(LevelKind.SWING_L, "96.00", "98.00", LevelState.SWEPT, SWEPT),
              lvl(LevelKind.ROUND, "95.45", "95.45"),
              lvl(LevelKind.SWING_H, "100.50", "101.00"),
              lvl(LevelKind.SWING_H, "102.40", "102.80"),
              lvl(LevelKind.SWING_H, "104.00", "104.50"),
              lvl(LevelKind.PDH, "106.00", "106.10")]
    p = fsm.arm(zone("98.00", "100.00"), ctx_at(at(11, 0), calm(), levels), 1000).plan
    # traded zone = swept SWING_L 97.40-98.50 (span 1.10, the only STRICTLY
    # tighter overlap -- the 96.00-98.00 trap spans 2.00, not < cluster):
    # entry CE 97.95; deepest trap extreme 96.00 - 0.50 buffer = 95.50;
    # within 2 ticks of round 95.45 => landed 3 ticks PAST the round far
    # edge; risk 97.95 - 95.30 = 2.65 >= floor 2.00, untouched
    # (1.5R = 3.975 so 100.50 fails and 102.40 is T1)
    assert p.entry_zone == (D("97.40"), D("98.50"))
    assert p.meta["cluster"] == ["98.00", "100.00"]  # scoring zone kept intact
    assert p.stop == D("95.30")
    assert p.targets == [D("102.40"), D("104.00"), D("106.00")]
    assert p.qty == 188                             # floor(500 / 2.65)
    assert all(isinstance(x, Decimal) and x % D("0.05") == 0
               for x in [p.stop, *p.targets, *p.entry_zone])


def test_arm_stop_too_wide_skips(fsm):
    # CE 96.00, stop 91.50: risk 4.50 > max 2.0*ATR = 4.00
    r = fsm.arm(zone("92.00", "100.00"), ctx_at(at(11, 0), calm(), []), 1000)
    assert (r.armed, r.reason, r.plan) == (False, "stop_too_wide", None)
    assert fsm.state is EntryState.IDLE


# knife-edge: un-snapped risk 3.95 <= budget 4.00, but round-snap alone
# vaults it to 4.15 > budget => arm with the un-snapped stop instead of
# dying stop_too_wide (trap 95.55 - buf 0.50 = 95.05; ROUND edge 95.00 is
# within 2 ticks of 95.05 so snap would land 94.85, budget-breaching).
# The swept SWING_L spans 4.95 > cluster 2.00, so it is a trap extreme but
# NOT the traded zone (traded zone never widens): entry stays CE 99.00.
def test_arm_prefers_unsnapped_stop_over_stop_too_wide(fsm):
    levels = [lvl(LevelKind.SWING_L, "95.55", "100.50", LevelState.SWEPT, SWEPT),
              lvl(LevelKind.ROUND, "95.00", "95.00"),
              lvl(LevelKind.SWING_H, "105.00", "105.50")]
    r = fsm.arm(zone("98.00", "100.00"), ctx_at(at(11, 0), calm(), levels), 1000)
    assert r.armed and r.reason is None
    p = r.plan
    assert p.stop == D("95.05")                      # un-snapped, not 94.85
    assert p.meta["risk_pts"] == "3.95"
    assert p.meta["snap_skipped"] is True
    assert p.qty == 126                               # floor(500 / 3.95)


# genuinely wide even un-snapped (trap 94.50 pushes stop to 94.00, risk
# 5.00 > 4.00): round-snap present but irrelevant -- still skips.
def test_arm_stop_too_wide_skips_even_with_round_nearby(fsm):
    levels = [lvl(LevelKind.SWING_L, "94.50", "98.50", LevelState.SWEPT, SWEPT),
              lvl(LevelKind.ROUND, "96.60", "96.60")]
    r = fsm.arm(zone("98.00", "100.00"), ctx_at(at(11, 0), calm(), levels), 1000)
    assert (r.armed, r.reason, r.plan) == (False, "stop_too_wide", None)


def test_arm_no_room_skips(fsm):  # only opposing level is < 1.5R away
    ctx = ctx_at(at(11, 0), calm(), [lvl(LevelKind.SWING_H, "100.50", "101.00")])
    r = fsm.arm(zone("98.00", "100.00"), ctx, 1000)
    assert (r.armed, r.reason) == (False, "no_room")


def test_arm_qty_zero_skips(fsm):
    r = fsm.arm(zone("98.00", "100.00"), ctx_at(at(11, 0), calm(), [t_lvl()]), 0)
    assert (r.armed, r.reason) == (False, "qty_zero")


def fsm_cfg(patch: dict) -> EntryFSM:
    raw = json.loads(CONFIG.read_text())
    for path, v in patch.items():
        d = raw
        *ks, last = path.split(".")
        for k in ks:
            d = d[k]
        d[last] = v
    s = Settings.model_validate(raw)
    return EntryFSM(s, s.market_spec())


def test_arm_notional_cap_exact_and_leverage_config():
    # leverage 0.2 => floor(100000 x 0.2 / entry 99.00) = 202, binding under
    # both max_qty 1000 and budget qty 250 (default leverage 5 caps at 5050,
    # never binding here: the plain test's 250 covers that)
    p = fsm_cfg({"risk.leverage": 0.2}).arm(
        zone("98.00", "100.00"), ctx_at(at(11, 0), calm(), [t_lvl()]), 1000).plan
    assert p.qty == 202
    s = Settings.model_validate_json(CONFIG.read_text())
    assert (s.risk.leverage, s.risk.max_cost_reward_ratio) == (5.0, 0.15)


def test_arm_costs_dominate_boundary_vs_reward():
    # Viability judges costs against the REWARD to T1, not risk: qty 100,
    # entry 99.00, T1 102.50 => reward 350; cap 0.15 x 350 = 52.50. Round
    # trip = 2 x flat + (stt + 2 x exch)% x turnover -- STT once (sell leg
    # only, shared broker costing) = 2f + 14.85. flat 18.825 => rt exactly
    # 52.50 (== cap, strict > so it ARMS); 18.83 => 52.51 skips.
    base = {"fills.costs.stt_pct": 0.05, "fills.costs.exchange_pct": 0.05}
    args = (zone("98.00", "100.00"), ctx_at(at(11, 0), calm(), [t_lvl()]), 100)
    assert fsm_cfg({**base, "fills.costs.brokerage_flat": 18.825}).arm(*args).armed
    r = fsm_cfg({**base, "fills.costs.brokerage_flat": 18.83}).arm(*args)
    assert (r.armed, r.reason) == (False, "costs_dominate")


# --- traded zone: tightest overlapping level, not the cluster span ---

def test_arm_tightens_to_tightest_overlapping_level(fsm):
    levels = [lvl(LevelKind.OB_BULL, "98.60", "99.20"),      # span 0.60: traded
              lvl(LevelKind.SWING_L, "97.80", "99.00"),      # span 1.20: wider
              t_lvl()]
    p = fsm.arm(zone("98.00", "100.00"), ctx_at(at(11, 0), calm(), levels), 1000).plan
    assert p.entry_zone == (D("98.60"), D("99.20"))
    assert p.meta["cluster"] == ["98.00", "100.00"]
    assert p.meta["entry"] == "98.90"                        # traded-zone CE
    assert p.stop == D("96.90")     # natural 98.10 (risk 0.80) -> CE - floor


def test_traded_zone_tie_breaks_nearest_close(fsm):
    # two span-0.60 levels; last close 100 => the nearer (higher) one wins
    levels = [lvl(LevelKind.OB_BULL, "98.10", "98.70"),
              lvl(LevelKind.FVG_BULL, "99.20", "99.80"), t_lvl()]
    p = fsm.arm(zone("98.00", "100.00"), ctx_at(at(11, 0), calm(), levels), 1000).plan
    assert p.entry_zone == (D("99.20"), D("99.80"))


def test_traded_zone_ignores_terminal_and_wider_levels(fsm):
    levels = [lvl(LevelKind.OB_BULL, "98.60", "99.20", LevelState.DEAD),  # dead
              lvl(LevelKind.SWING_L, "97.00", "100.50"),  # span 3.50 >= cluster
              t_lvl()]
    p = fsm.arm(zone("98.00", "100.00"), ctx_at(at(11, 0), calm(), levels), 1000).plan
    assert p.entry_zone == (D("98.00"), D("100.00"))      # fallback: cluster


def test_arm_too_far_from_traded_zone_skips(fsm):
    # close 100 touches the CLUSTER, but the traded level sits 4.00 below
    # (> 1xATR): the level being traded is far => too_far, no TTL burn
    levels = [lvl(LevelKind.OB_BULL, "95.60", "96.00")]
    r = fsm.arm(zone("95.50", "100.00"), ctx_at(at(11, 0), calm(), levels), 1000)
    assert (r.armed, r.reason) == (False, "too_far")


# --- arm proximity (06 §4: price must be approaching, within 1 x ATR) ---

def test_arm_too_far_below_close_skips(fsm):
    # close 100, zone hi 96: gap 4 > 1*ATR(2) => never arms, no TTL burn
    r = fsm.arm(zone("94.00", "96.00"), ctx_at(at(11, 0), calm(), [t_lvl()]), 1000)
    assert (r.armed, r.reason, r.plan) == (False, "too_far", None)
    assert fsm.state is EntryState.IDLE


def test_arm_too_far_above_close_skips_short(fsm):
    r = fsm.arm(zone("104.00", "106.00", Direction.SHORT),
                ctx_at(at(11, 0), calm(), []), 1000)
    assert (r.armed, r.reason) == (False, "too_far")


def test_arm_at_exactly_one_atr_allowed(fsm):
    # close 100, zone hi 98: gap 2 == 1*ATR(2) => still arms (farther rejects);
    # CE 96.50, stop 94.50: risk exactly == floor 2.00 stays UNtouched
    r = fsm.arm(zone("95.00", "98.00"), ctx_at(at(11, 0), calm(), [t_lvl()]), 1000)
    assert r.armed and r.reason is None
    assert r.plan.stop == D("94.50") and r.plan.meta["risk_pts"] == "2.00"


# --- targets ---

def test_t2_t3_fallback_prices(fsm):  # single level beyond: 2.5R / 4R fallbacks
    p = fsm.arm(zone("98.00", "100.00"), ctx_at(at(11, 0), calm(), [t_lvl()]), 1000).plan
    assert p.targets == [D("102.50"), D("104.00"), D("107.00")]   # risk 2.00


def energy_ev(energy):
    return Evidence("compression", Direction.LONG, 0.75, (D("98.50"), D("99.50")),
                    at(10, 0), 24, meta={"event": "PO3_DIST", "energy": energy})


def test_t3_capped_by_compression_energy(fsm):
    ctx = ctx_at(at(11, 0), calm(), [t_lvl()], history=[energy_ev("6.00")])
    p = fsm.arm(zone("98.00", "100.00"), ctx, 1000).plan
    assert p.targets[2] == D("105.00")              # min(4R=107, entry + 6.00)


def test_t3_dropped_when_energy_cap_inside_t2(fsm):
    ctx = ctx_at(at(11, 0), calm(), [t_lvl()], history=[energy_ev("3.00")])
    p = fsm.arm(zone("98.00", "100.00"), ctx, 1000).plan
    assert p.targets == [D("102.50"), D("104.00")]  # cap 102.00 < T2: T3 dropped


def test_t2_fallback_inside_t1_dropped_t3_promoted(fsm):
    # T1 104.00 (5.00 >= 1.5R=3.00); T2 fallback 99 + 2.5*2.00 = 104.00
    # <= T1: dropped (strict T1<T2<T3); T3 = 4R = 107 takes the second slot
    ctx = ctx_at(at(11, 0), calm(), [lvl(LevelKind.SWING_H, "104.00", "104.50")])
    p = fsm.arm(zone("98.00", "100.00"), ctx, 1000).plan
    assert p.targets == [D("104.00"), D("107.00")]


def test_t2_fallback_inside_t1_dropped_short(fsm):
    # SHORT mirror: T1 96.00; T2 fallback 101 - 5.00 = 96.00 inside T1
    ctx = ctx_at(at(11, 0), calm(), [lvl(LevelKind.SWING_L, "95.50", "96.00")])
    p = fsm.arm(zone("100.00", "102.00", Direction.SHORT), ctx, 1000).plan
    assert p.targets == [D("96.00"), D("93.00")]


def test_opposing_scored_zone_supplies_t1(fsm):
    ctx = ctx_at(at(11, 0), calm(), [lvl(LevelKind.SWING_H, "100.50", "101.00")])
    opp = zone("102.60", "103.00", Direction.SHORT)
    p = fsm.arm(zone("98.00", "100.00"), ctx, 1000, opps=[opp]).plan
    assert p.targets == [D("102.60"), D("104.00"), D("107.00")]


def test_short_direction_stop_and_t1_boundary(fsm):  # T1 at exactly 1.5R counts
    ctx = ctx_at(at(11, 0), calm(), [lvl(LevelKind.SWING_L, "97.25", "98.00")])
    p = fsm.arm(zone("100.00", "102.00", Direction.SHORT), ctx, 1000).plan
    # natural stop 102.50 (risk 1.50) widens SHORT-side to CE + floor
    assert p.stop == D("103.00")
    assert p.targets == [D("98.00"), D("96.00"), D("93.00")]


# --- step(): triggers + disarms ---

def armed(fsm, extra_levels=()):
    levels = [t_lvl(), *extra_levels]
    assert fsm.arm(zone("98.00", "100.00"), ctx_at(at(10, 31), calm(), levels), 1000).armed
    return levels


def step_ctx(trigger=None, now=at(10, 36), levels=()):
    return ctx_at(now, calm() + ([trigger] if trigger else []), levels)


@pytest.mark.parametrize("o,filled", [(99.2, True),    # lower wick 1.2 = 60% exactly
                                      (99.1, False)])  # 55% + no evidence: hold
def test_trigger_rejection_wick_boundary(fsm, o, filled):
    levels = armed(fsm)
    r = fsm.step(step_ctx(m1(at(10, 30), o=o, h=100.0, lo=98.0, c=99.9), levels=levels))
    assert (r.action == "fill") is filled
    if filled:
        assert r.plan.qty == 250 and fsm.state is EntryState.IDLE
    else:
        assert r.action == "hold" and fsm.state is EntryState.ARMED


@pytest.mark.parametrize("det,event", [("structure", "CHOCH"), ("volume", "VSA")])
def test_trigger_on_confirmation_evidence(fsm, det, event):
    levels = armed(fsm)
    # detectors stamp ts=ctx.now = candle close = c.ts + 5min (window edge)
    ev = Evidence(det, Direction.LONG, 0.7, (D("98"), D("100")), at(10, 35), 6,
                  meta={"event": event})
    c = m1(at(10, 30), o=99.1, h=100.0, lo=98.0, c=99.9)  # wick 55%: needs evidence
    assert fsm.step(step_ctx(c, levels=levels), [ev]).action == "fill"


@pytest.mark.parametrize("dirn,zlo,zhi,ts_mm", [
    (Direction.SHORT, "98", "100", 35),   # opposing CHoCH must not fill LONG
    (Direction.LONG, "103", "104", 35),   # zone does not overlap entry zone
    (Direction.LONG, "98", "100", 30),    # stale: ts = c.ts, before c formed
])
def test_confirmation_evidence_rejected(fsm, dirn, zlo, zhi, ts_mm):
    levels = armed(fsm)
    ev = Evidence("structure", dirn, 0.7, (D(zlo), D(zhi)), at(10, ts_mm), 6,
                  meta={"event": "CHOCH"})
    c = m1(at(10, 30), o=99.1, h=100.0, lo=98.0, c=99.9)
    r = fsm.step(step_ctx(c, levels=levels), [ev])
    assert r.action == "hold" and fsm.state is EntryState.ARMED


def test_disarm_chased_close_beyond_far_edge(fsm):
    levels = armed(fsm)
    c = m1(at(10, 30), o=99.0, h=99.2, lo=97.5, c=97.7)   # close < 98 - 0.1*ATR
    r = fsm.step(step_ctx(c, levels=levels))
    assert (r.action, r.reason) == ("disarm", "chased") and fsm.state is EntryState.IDLE


def test_disarm_expired_after_ttl(fsm):
    levels = armed(fsm)
    assert fsm.step(step_ctx(now=at(11, 31), levels=levels)).action == "hold"  # age 12
    r = fsm.step(step_ctx(now=at(11, 36), levels=levels))                      # age 13
    assert (r.action, r.reason) == ("disarm", "expired")


def test_disarm_zone_broken_on_dead_ob(fsm):
    ob = lvl(LevelKind.OB_BULL, "98.20", "99.00", LevelState.DEAD)
    levels = armed(fsm)
    r = fsm.step(step_ctx(levels=[*levels, ob]))
    assert (r.action, r.reason) == ("disarm", "zone_broken")


def test_step_when_idle_holds(fsm):
    assert fsm.step(step_ctx(levels=[])).action == "hold"
