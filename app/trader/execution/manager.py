"""PositionManager: per-candle position babysitting (06 §7).

Check order per M5 close: (1) EOD squareoff, (2) stealth stop --
close-confirmed ONLY: a wick through the stop, however many in a row, never
exits; it just flags ``hunt_survived`` for the journal, (3) R/target ladder
(1R close: 33% off + breakeven -- T1 >= 1.5R by construction so 1R is always
nearer; T2 touch or 2R close, whichever first: 33% off + M5 trail; 3R:
promote trail to M15; T3 touch: final third exits AT the target). A
signal-driven plan (meta["sl_source"] mapped in exits.target_r_by_source)
instead takes profit on the whole remainder AT its per-signal R close (the
1R breakeven/stealth-stop machinery still runs; only the take-profit R
changes), (4) swing-trail ratchet, (5) counter-zone exit, (6) stall exit.
Target touches fill at the target price (limit semantics, ``Action.price``).

The manager mutates only ``pos.stop`` / ``pos.partials`` /
``pos.hunt_survived``; the caller executes the returned Actions through the
broker. Every stop write funnels through ``_apply_stop``, the runtime
never-widen guard (trailing filters widening candidates to a no-move first,
so the guard firing means a code bug, not a market condition).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from trader.config import Settings
from trader.engine.context import StockContext
from trader.engine.entry import snap_stop_off_round
from trader.models.candle import Timeframe
from trader.models.level import LevelKind
from trader.models.market import MarketSpec, _minutes
from trader.models.position import ExitReason, Position

_STALL_CANDLES = 18            # M5 candles without progress (06 early-exit)
_STALL_R = Decimal("0.5")
_ATR_PAD = Decimal("0.1")      # trail pad: swing edge -/+ 0.1 x ATR(M5)
_M5 = timedelta(minutes=5)
LADDER_EXITS = 3               # worst case: 1R + T2/2R partials + final third
SIGNAL_EXITS = 2               # signal-driven: 1R partial + take-profit rest


def ladder_exits(settings: Settings, sl_source: str | None = None) -> int:
    """Worst-case exit-tranche count the ladder can emit for a plan (cost
    gates size flat brokerage off this, one fee per order)."""
    return (SIGNAL_EXITS if sl_source in settings.exits.target_r_by_source
            else LADDER_EXITS)


@dataclass(frozen=True)
class Action:
    kind: str                  # "PARTIAL" | ExitReason.*.value
    qty: int | None            # PARTIAL share; None = full remaining qty
    reason: str
    price: Decimal | None = None   # limit fill override (target exits)


def _exit(reason: ExitReason, why: str) -> Action:
    return Action(reason.value, None, why)


class PositionManager:
    def __init__(self, settings: Settings, spec: MarketSpec):
        self.s, self.spec = settings, spec
        self._squareoff = _minutes(settings.time.squareoff)

    def on_candle(self, pos: Position, ctx: StockContext,
                  counter_zone_score: float | None = None) -> list[Action]:
        if ctx.now.hour * 60 + ctx.now.minute >= self._squareoff:
            return [_exit(ExitReason.EOD, "squareoff")]
        sign = pos.plan.direction.value
        c = ctx.candles.last(1, Timeframe.M5)[-1]
        if (pos.stop - c.close) * sign >= 0:            # close at/beyond stop
            return [_exit(ExitReason.STOP, "close_beyond_stop")]
        if (pos.stop - (c.low if sign > 0 else c.high)) * sign >= 0:
            pos.hunt_survived = True                    # wick-through: journal only
        r = pos.r_multiple(c.close)
        actions = self._ladder(pos, r, sign, c, self._target_r(pos))
        self._trail(pos, ctx, sign)
        if (counter_zone_score is not None
                and counter_zone_score >= self.s.confluence.threshold):
            actions.append(_exit(ExitReason.COUNTER,
                                 f"counter_zone_{counter_zone_score:g}"))
        elif r < _STALL_R and (ctx.now - pos.opened_ts) // _M5 >= _STALL_CANDLES:
            actions.append(_exit(ExitReason.STALL, "stall"))
        return actions

    def _target_r(self, pos: Position) -> Decimal | None:
        """Per-signal profit-target R (exits.target_r_by_source keyed by the
        plan's meta["sl_source"] detector), else None => default 3R/T3 ladder."""
        src = pos.plan.meta.get("sl_source")
        tr = self.s.exits.target_r_by_source.get(src) if src else None
        return Decimal(str(tr)) if tr is not None else None

    def _ladder(self, pos: Position, r: Decimal, sign: int, c,
                target_r: Decimal | None = None) -> list[Action]:
        """1R close: 33% off + stop -> breakeven. Then, when ``target_r`` is set
        (signal-driven plan), the whole remainder takes profit AT that R close
        -- replacing the default tail (T2 touch/2R close 33% + M5 trail; 3R M15
        trail; T3 touch final third). Marks in ``partials`` gate each rung once."""
        tg, fav = pos.plan.targets, c.high if sign > 0 else c.low
        hit = lambda t: (fav - t) * sign >= 0                    # noqa: E731
        out, q = [], pos.plan.qty * 33 // 100
        if r >= 1 and "1R" not in pos.partials:
            pos.partials.add("1R")
            if q:
                out.append(Action("PARTIAL", q, "1R"))
            if (pos.entry.price - pos.stop) * sign > 0:
                self._apply_stop(pos, pos.entry.price)  # breakeven
        if target_r is not None:                        # per-signal take-profit
            if r >= target_r:
                out.append(_exit(ExitReason.TARGET, f"{target_r:g}R"))
            return out
        if "2R" not in pos.partials:
            t2 = len(tg) > 1 and hit(tg[1])
            if t2 or r >= 2:
                pos.partials.add("2R")
                if q:
                    out.append(Action("PARTIAL", q, "T2", tg[1]) if t2
                               else Action("PARTIAL", q, "2R"))
        if r >= 3 and "3R" not in pos.partials:
            pos.partials.add("3R")
        if len(tg) > 2 and hit(tg[2]):
            out.append(Action(ExitReason.TARGET.value, None, "T3", tg[2]))
        return out

    def _trail(self, pos: Position, ctx: StockContext, sign: int) -> None:
        """Trail behind the latest confirmed swing of the mode tf, padded by
        0.1 x ATR(M5) and snapped off ROUND zones like entry stops (B13);
        ratchet only -- a widening candidate is a no-move."""
        tf = (Timeframe.M15 if "3R" in pos.partials
              else Timeframe.M5 if "2R" in pos.partials else None)
        if tf is None:
            return
        kind = LevelKind.SWING_L if sign > 0 else LevelKind.SWING_H
        swings = [lv for lv in ctx.levels if lv.kind is kind and lv.tf is tf]
        if not swings:
            return
        zone = max(swings, key=lambda lv: lv.born).zone
        pad = _ATR_PAD * (ctx.atr(Timeframe.M5) or Decimal(0))
        cand = self.spec.quantize(min(zone) - pad if sign > 0 else max(zone) + pad)
        cand = snap_stop_off_round(cand, ctx.levels, self.spec,
                                   self.s.stops.round_offset_ticks, sign > 0)
        if (cand - pos.stop) * sign > 0:
            self._apply_stop(pos, cand)

    @staticmethod
    def _apply_stop(pos: Position, new_stop: Decimal) -> None:
        """Runtime never-widen invariant: every stop write goes through here."""
        if (new_stop - pos.stop) * pos.plan.direction.value < 0:
            raise AssertionError(f"stop ratchet violated: {pos.stop} -> {new_stop}")
        pos.stop = new_stop
