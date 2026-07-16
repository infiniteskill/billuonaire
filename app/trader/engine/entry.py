"""EntryFSM: precision entry machinery (06-CONFLUENCE-ENGINE-DEEP §4/§6).

One FSM per symbol, IDLE -> ARMED -> fill/disarm. arm() builds the draft
TradePlan; threshold/gates are the CALLER's job (GateChain), as is
journalling the skip/disarm reasons returned here.

  STOP     zone far edge, pushed past any swept-trap extreme (level with
           SWEPT history overlapping the zone), buffered by atr_buffer x ATR;
           if within 2 ticks of a ROUND level edge, landed round_offset_ticks
           PAST the round zone's far edge (never tighter), tick-quantized.
           Skip "stop_too_wide" if risk > max_stop_atr x ATR.
  TARGETS  opposing liquidity map: ACTIVE/TESTED levels + opposing
           ScoredZones beyond entry (near edge, quantized). T1 = nearest
           >= 1.5R (none => skip "no_room"); T2 = next beyond T1 (else 2.5R);
           T3 = nearest PDH/PDL beyond T2 (else 4R), capped at entry +/-
           compression energy (evidence meta) overlapping the zone; T3 is
           DROPPED if the cap pulls it inside T2 (monotonic T1<T2<T3).
  QTY      min(max_qty, floor(capital x per_trade_pct% / risk)); 0 => skip.
  TRIGGER  latest closed M5 enters the zone AND (rejection wick >= 60% of
           range off the far side | same-direction CHoCH/VSA evidence
           overlapping the zone, stamped in (c.ts, c.ts + 5m]).
  DISARM   "chased" (close beyond far edge + chase_tolerance x ATR),
           "expired" (armed > arm_ttl_candles), "zone_broken" (OB level in
           zone DEAD/INVERTED).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from enum import Enum, auto

from trader.config import Settings
from trader.engine.confluence import ScoredZone
from trader.engine.context import StockContext
from trader.models.candle import Timeframe
from trader.models.evidence import Direction, Evidence
from trader.models.level import LevelKind, LevelState
from trader.models.market import MarketSpec
from trader.models.signal import TradePlan

_M5 = timedelta(minutes=5)
_TARGETABLE = (LevelState.ACTIVE, LevelState.TESTED)
_EXTERNAL = (LevelKind.PDH, LevelKind.PDL)
_OB = (LevelKind.OB_BULL, LevelKind.OB_BEAR)
_BROKEN = (LevelState.DEAD, LevelState.INVERTED)
_CONFIRM = ("CHOCH", "VSA")


class EntryState(Enum):
    IDLE = auto(); ARMED = auto()


@dataclass(frozen=True)
class ArmResult:
    armed: bool
    reason: str | None = None    # "stop_too_wide" | "no_room" | "qty_zero"
    plan: TradePlan | None = None


@dataclass(frozen=True)
class TriggerResult:
    action: str                  # "fill" | "disarm" | "hold"
    reason: str | None = None    # "chased" | "expired" | "zone_broken"
    plan: TradePlan | None = None


def _overlaps(a, b) -> bool:
    return min(a) <= max(b) and max(a) >= min(b)


class EntryFSM:
    def __init__(self, settings: Settings, spec: MarketSpec):
        self.s, self.spec = settings, spec
        self.state, self.plan, self._armed_ts = EntryState.IDLE, None, None

    def arm(self, zone: ScoredZone, ctx: StockContext, max_qty: int,
            opps: list[ScoredZone] = ()) -> ArmResult:
        lo, hi = zone.zone
        up = zone.direction is Direction.LONG
        atr = ctx.atr(Timeframe.M5) or Decimal(0)
        entry = self.spec.quantize((lo + hi) / 2)    # zone CE
        stop = self._stop(lo, hi, up, atr, ctx)
        risk = abs(entry - stop)
        if risk > Decimal(str(self.s.entry.max_stop_atr)) * atr:
            return ArmResult(False, "stop_too_wide")
        targets = self._targets(entry, risk, up, (lo, hi), ctx, opps)
        if targets is None:
            return ArmResult(False, "no_room")
        budget = (Decimal(str(self.s.capital))
                  * Decimal(str(self.s.risk.per_trade_pct)) / 100)
        qty = min(max_qty, int(budget // risk))
        if qty <= 0:
            return ArmResult(False, "qty_zero")
        plan = TradePlan(ctx.symbol, zone.direction, (lo, hi), stop, targets,
                         qty, zone.final, ctx.now,
                         {"final": zone.final, "mults": dict(zone.mults),
                          "entry": str(entry), "risk_pts": str(risk)})
        self.state, self.plan, self._armed_ts = EntryState.ARMED, plan, ctx.now
        return ArmResult(True, plan=plan)

    def _stop(self, lo, hi, up, atr, ctx) -> Decimal:
        traps = [min(lv.zone) if up else max(lv.zone) for lv in ctx.levels
                 if _overlaps(lv.zone, (lo, hi))
                 and any(s is LevelState.SWEPT for _, s in lv.state_history)]
        buf = Decimal(str(self.s.stops.atr_buffer)) * atr
        stop = self.spec.quantize(min([lo, *traps]) - buf if up
                                  else max([hi, *traps]) + buf)
        tick = self.spec.tick_size
        off = self.s.stops.round_offset_ticks * tick
        for lv in ctx.levels:                        # land PAST the round number
            if (lv.kind is LevelKind.ROUND
                    and any(abs(stop - e) <= 2 * tick for e in lv.zone)):
                stop = (min(stop, min(lv.zone) - off) if up
                        else max(stop, max(lv.zone) + off))  # never tighter
        return stop

    def _targets(self, entry, risk, up, zone, ctx, opps) -> list[Decimal] | None:
        sign = 1 if up else -1
        near = lambda z: self.spec.quantize(min(z) if up else max(z))  # noqa: E731
        cands = ([(near(lv.zone), lv.kind) for lv in ctx.levels
                  if lv.state in _TARGETABLE]
                 + [(near(z.zone), None) for z in opps])
        cands = sorted(((p, k) for p, k in cands if (p - entry) * sign > 0),
                       key=lambda c: abs(c[0] - entry))
        t1 = next((p for p, _ in cands
                   if abs(p - entry) >= Decimal("1.5") * risk), None)
        if t1 is None:
            return None
        t2 = next((p for p, _ in cands if (p - t1) * sign > 0),
                  self.spec.quantize(entry + sign * Decimal("2.5") * risk))
        t3 = next((p for p, k in cands if k in _EXTERNAL and (p - t2) * sign > 0),
                  self.spec.quantize(entry + sign * 4 * risk))
        for e in ctx.evidence_history:               # compression energy cap
            if "energy" in e.meta and _overlaps(e.zone, zone):
                cap = self.spec.quantize(entry + sign * Decimal(e.meta["energy"]))
                t3 = min(t3, cap) if up else max(t3, cap)
        return [t1, t2, t3] if (t3 - t2) * sign > 0 else [t1, t2]

    def step(self, ctx: StockContext,
             evidence: list[Evidence] = ()) -> TriggerResult:
        if self.state is not EntryState.ARMED:
            return TriggerResult("hold")
        lo, hi = self.plan.entry_zone
        up = self.plan.direction is Direction.LONG
        c = ctx.candles.last(1, Timeframe.M5)[-1]
        atr = ctx.atr(Timeframe.M5) or Decimal(0)
        far, sign = (lo, 1) if up else (hi, -1)
        if (far - c.close) * sign > Decimal(str(self.s.entry.chase_tolerance_atr)) * atr:
            return self._disarm("chased")
        if (ctx.now - self._armed_ts) // _M5 > self.s.entry.arm_ttl_candles:
            return self._disarm("expired")
        if any(lv.kind in _OB and lv.state in _BROKEN
               and _overlaps(lv.zone, (lo, hi)) for lv in ctx.levels):
            return self._disarm("zone_broken")
        wick = c.lower_wick if up else c.upper_wick   # rejection off far side
        confirmed = (c.range > 0 and wick >= Decimal("0.6") * c.range) or any(
            c.ts < e.ts <= c.ts + _M5                 # stamped while c formed
            and e.meta.get("event") in _CONFIRM
            and e.direction is self.plan.direction
            and _overlaps(e.zone, (lo, hi)) for e in evidence)
        if c.low <= hi and c.high >= lo and confirmed:
            plan, self.state, self.plan = self.plan, EntryState.IDLE, None
            return TriggerResult("fill", plan=plan)
        return TriggerResult("hold")

    def _disarm(self, reason: str) -> TriggerResult:
        self.state, self.plan = EntryState.IDLE, None
        return TriggerResult("disarm", reason)
