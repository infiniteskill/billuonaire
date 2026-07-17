"""EntryFSM: precision entry machinery (06-CONFLUENCE-ENGINE-DEEP §4/§6).

One FSM per symbol, IDLE -> ARMED -> fill/disarm. arm() builds the draft
TradePlan; threshold/gates are the CALLER's job (GateChain), as is
journalling the skip/disarm reasons returned here.

  ARM      only with price approaching (06 §4): latest closed M5 close
           within arm_proximity_atr x ATR of the zone, else skip "too_far"
           (far zones must not arm and burn TTL). The TRADED zone is the
           tightest non-terminal level overlapping the cluster (nearest the
           last close on span ties; fallback: cluster span) -- real clusters
           span several ATR and armed only to die stop_too_wide. The cluster
           stays the scoring zone; entry/stop/trigger work off the traded
           zone.
  STOP     zone far edge, pushed past any swept-trap extreme (level with
           SWEPT history overlapping the zone), buffered by atr_buffer x ATR;
           if within 2 ticks of a ROUND level edge, landed round_offset_ticks
           PAST the round zone's far edge (never tighter), tick-quantized.
           If that snap alone vaults risk past max_stop_atr x ATR but the
           un-snapped stop does not, arm with the un-snapped stop instead
           (meta["snap_skipped"]=True) -- anti-hunt intent stands, killing
           the trade outright does not. Skip "stop_too_wide" only when even
           the un-snapped risk breaches max_stop_atr x ATR.
  TARGETS  opposing liquidity map: ACTIVE/TESTED levels + opposing
           ScoredZones beyond entry (near edge, quantized). T1 = nearest
           >= 1.5R (none => skip "no_room"); T2 = next beyond T1 (else 2.5R);
           T3 = nearest PDH/PDL beyond T2 (else 4R), capped at entry +/-
           compression energy (evidence meta) overlapping the zone.
           T1<T2<T3 is enforced STRICTLY after all fallbacks: a violating
           target is dropped (e.g. the 2.5R T2 fallback landing at/inside
           T1 drops T2 and promotes T3 into the second slot; a capped T3
           inside T2 is dropped as before).
  QTY      min(max_qty, floor(capital x per_trade_pct% / risk),
           floor(capital x leverage / entry)) -- the notional cap keeps
           risk-derived size fundable on intraday margin; 0 => skip
           "qty_zero". Expected round-trip costs (2 x brokerage_flat + pct
           turnover both legs at entry) > max_cost_risk_ratio x (qty x risk)
           => skip "costs_dominate" (flat costs swamp micro risk amounts).
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
from trader.engine.context import StockContext, live_evidence
from trader.models.candle import Timeframe
from trader.models.evidence import Direction, Evidence
from trader.models.level import TERMINAL, LevelKind, LevelState
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
    reason: str | None = None    # "too_far" | "stop_too_wide" | "no_room"
    #                              | "qty_zero" | "costs_dominate"
    plan: TradePlan | None = None


@dataclass(frozen=True)
class TriggerResult:
    action: str                  # "fill" | "disarm" | "hold"
    reason: str | None = None    # "chased" | "expired" | "zone_broken"
    plan: TradePlan | None = None


def _overlaps(a, b) -> bool:
    return min(a) <= max(b) and max(a) >= min(b)


def snap_stop_off_round(stop: Decimal, levels, spec: MarketSpec,
                        offset_ticks: int, up: bool) -> Decimal:
    """Protective stop within 2 ticks of a ROUND zone edge lands
    offset_ticks PAST the zone's far edge, never tighter (B13: shared by
    entry stops and manager trail candidates). ``up`` = stop below price."""
    tick = spec.tick_size
    off = offset_ticks * tick
    for lv in levels:
        if (lv.kind is LevelKind.ROUND
                and any(abs(stop - e) <= 2 * tick for e in lv.zone)):
            stop = (min(stop, min(lv.zone) - off) if up
                    else max(stop, max(lv.zone) + off))
    return stop


class EntryFSM:
    def __init__(self, settings: Settings, spec: MarketSpec):
        self.s, self.spec = settings, spec
        self.state, self.plan, self._armed_ts = EntryState.IDLE, None, None

    def arm(self, zone: ScoredZone, ctx: StockContext, max_qty: int,
            opps: list[ScoredZone] = ()) -> ArmResult:
        up = zone.direction is Direction.LONG
        atr = ctx.atr(Timeframe.M5) or Decimal(0)
        last = ctx.candles.last(1, Timeframe.M5)
        lo, hi = self._traded_zone(zone.zone, ctx,
                                   last[-1].close if last else None)
        if last:
            gap = max(lo - last[-1].close, last[-1].close - hi)
            if gap > Decimal(str(self.s.entry.arm_proximity_atr)) * atr:
                return ArmResult(False, "too_far")
        entry = self.spec.quantize((lo + hi) / 2)    # traded-zone CE
        stop, unsnapped = self._stop(lo, hi, up, atr, ctx)
        risk, max_risk = abs(entry - stop), Decimal(str(self.s.entry.max_stop_atr)) * atr
        snap_skipped = False
        if risk > max_risk:
            un_risk = abs(entry - unsnapped)
            if un_risk > max_risk:
                return ArmResult(False, "stop_too_wide")
            stop, risk, snap_skipped = unsnapped, un_risk, True  # snap vaulted past budget
        targets = self._targets(entry, risk, up, zone.zone, ctx, opps)
        if targets is None:
            return ArmResult(False, "no_room")
        cap = Decimal(str(self.s.capital))
        budget = cap * Decimal(str(self.s.risk.per_trade_pct)) / 100
        notional = cap * Decimal(str(self.s.risk.leverage))
        qty = min(max_qty, int(budget // risk), int(notional // entry))
        if qty <= 0:
            return ArmResult(False, "qty_zero")
        c = self.s.fills.costs
        rt = 2 * (Decimal(str(c.brokerage_flat))
                  + (Decimal(str(c.stt_pct)) + Decimal(str(c.exchange_pct)))
                  / 100 * entry * qty)
        if rt > Decimal(str(self.s.risk.max_cost_risk_ratio)) * risk * qty:
            return ArmResult(False, "costs_dominate")
        meta = {"final": zone.final, "mults": dict(zone.mults),
                "entry": str(entry), "risk_pts": str(risk),
                "cluster": [str(zone.zone[0]), str(zone.zone[1])]}
        if snap_skipped:
            meta["snap_skipped"] = True
        plan = TradePlan(ctx.symbol, zone.direction, (lo, hi), stop, targets,
                         qty, zone.final, ctx.now, meta)
        self.state, self.plan, self._armed_ts = EntryState.ARMED, plan, ctx.now
        return ArmResult(True, plan=plan)

    def _traded_zone(self, cluster, ctx, ref) -> tuple[Decimal, Decimal]:
        """The tightest live level inside the cluster, nearest ``ref`` (last
        close) on span ties: the actual level being traded. Only levels
        STRICTLY tighter than the cluster qualify -- the traded zone may
        never widen. Fallback: the cluster span itself."""
        lo, hi = cluster
        cands = [lv.zone for lv in ctx.levels
                 if lv.symbol == ctx.symbol and lv.state not in TERMINAL
                 and _overlaps(lv.zone, cluster)
                 and max(lv.zone) - min(lv.zone) < hi - lo]
        if not cands:
            return lo, hi
        mid = lambda z: (min(z) + max(z)) / 2                 # noqa: E731
        z = min(cands, key=lambda z: (max(z) - min(z),
                                      abs(mid(z) - ref) if ref is not None
                                      else 0))
        return min(z), max(z)

    def _stop(self, lo, hi, up, atr, ctx) -> tuple[Decimal, Decimal]:
        """Returns (snapped, unsnapped) -- caller falls back to unsnapped if
        the round-snap alone vaults risk past max_stop_atr (B13 anti-hunt
        intent stands; killing the trade outright does not)."""
        traps = [min(lv.zone) if up else max(lv.zone) for lv in ctx.levels
                 if _overlaps(lv.zone, (lo, hi))
                 and any(s is LevelState.SWEPT for _, s in lv.state_history)]
        buf = Decimal(str(self.s.stops.atr_buffer)) * atr
        unsnapped = self.spec.quantize(min([lo, *traps]) - buf if up
                                       else max([hi, *traps]) + buf)
        snapped = snap_stop_off_round(unsnapped, ctx.levels, self.spec,
                                      self.s.stops.round_offset_ticks, up)
        return snapped, unsnapped

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
        for e in live_evidence(ctx.evidence_history, ctx.now):  # energy cap
            if "energy" in e.meta and _overlaps(e.zone, zone):  # (unexpired)
                cap = self.spec.quantize(entry + sign * Decimal(e.meta["energy"]))
                t3 = min(t3, cap) if up else max(t3, cap)
        out = [t1]                       # strict T1<T2<T3 after ALL fallbacks:
        for t in (t2, t3):               # drop violators (2.5R T2 fallback can
            if (t - out[-1]) * sign > 0:  # land inside T1; cap can pull T3 in)
                out.append(t)
        return out

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
