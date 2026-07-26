"""Swings detector: confirms swing highs/lows and writes SWING_H/SWING_L
Levels directly onto ``ctx.levels``.

This is an *infrastructure* detector -- other detectors and the confluence
engine consume the levels it creates, not Evidence, so ``detect`` always
returns ``[]``. Level-creation is a documented side channel: detectors are
normally pure (ctx in, Evidence out), but swings/PDH/PWL-style structural
detectors are the one exception that mutate ``ctx.levels`` in place (see
``trader.engine.context.StockContext.levels`` docstring: "live shared
objects (mutable)").

Confirmation rule (binding, see 02-DETECTOR-SPECS + task-3 brief): for a
configured timeframe and ``strength`` N, look at the last ``2N + 1`` fully
closed candles. The middle candle is a confirmed swing high iff its high is
strictly greater than every other high in that window, on both sides --
a tie (``>=``) anywhere disqualifies it. Swing lows mirror this on lows
(strictly lower than every other low in the window).

No-lookahead: ``ctx.candles.last()`` only ever returns fully closed candles
(see ``CandleView``), so a swing at window-index ``strength`` (i.e. N
candles before the most recent close) can only be confirmed once N further
candles have closed after it -- there is no separate "wait N more candles"
bookkeeping needed here, it falls out of using only closed candles.
"""

from __future__ import annotations

from trader.detectors.base import Detector, register
from trader.engine.context import StockContext
from trader.models.candle import Candle, Timeframe
from trader.models.evidence import Evidence
from trader.models.level import TERMINAL, Level, LevelKind, LevelState

_DEFAULT_STRENGTH = 3
_DEFAULT_TIMEFRAMES = ("5m", "15m")
_ALL = 10 ** 9


@register
class SwingsDetector(Detector):
    name = "swings"

    def __init__(self, params: dict):
        super().__init__(params)
        self._sig: dict = {}   # tf -> window signature, full_history rescan memo

    def detect(self, ctx: StockContext) -> list[Evidence]:
        strength = int(self.params.get("strength", _DEFAULT_STRENGTH))
        timeframes = self.params.get("timeframes", _DEFAULT_TIMEFRAMES)
        window_size = 2 * strength + 1

        # SESSION AMNESIA (measured 2026-07-26). SWING_H/SWING_L are in neither
        # pipeline._CARRY nor _ZONES, so _prune_levels() wipes them at every session
        # boundary. extremes survives that because it re-derives from the FULL closed
        # history each tick and re-appends anything missing; this detector only ever
        # looked at the last 2*strength+1 bars, so a pruned swing could never come
        # back. Over a 3-month 5m tape it emitted 12 levels -- all dated to the final
        # session -- while appearing to work. full_history=True rescans everything so
        # pruned swings regenerate. Default False keeps the frozen behaviour.
        full = bool(self.params.get("full_history", False))
        for tf_value in timeframes:
            tf = Timeframe(tf_value)
            if not full:
                window = ctx.candles.last(window_size, tf)
                if len(window) < window_size:
                    continue  # not enough closed candles yet for this tf
                mid = window[strength]
                self._confirm(ctx, window, mid, strength, tf, kind=LevelKind.SWING_H)
                self._confirm(ctx, window, mid, strength, tf, kind=LevelKind.SWING_L)
                continue
            closed = ctx.candles.last(_ALL, tf)
            if len(closed) < window_size:
                continue
            sig = (len(closed), closed[-1].ts, ctx.day.session_date if ctx.day else None)
            if self._sig.get(tf) == sig:       # pure function of the window (perf)
                continue
            self._sig[tf] = sig
            for i in range(strength, len(closed) - strength):
                w = closed[i - strength:i + strength + 1]
                self._confirm(ctx, w, w[strength], strength, tf, kind=LevelKind.SWING_H)
                self._confirm(ctx, w, w[strength], strength, tf, kind=LevelKind.SWING_L)

        return []  # always -- infrastructure detector, no Evidence

    def _confirm(
        self,
        ctx: StockContext,
        window: list[Candle],
        mid: Candle,
        strength: int,
        tf: Timeframe,
        *,
        kind: LevelKind,
    ) -> None:
        is_high = kind is LevelKind.SWING_H
        extreme = mid.high if is_high else mid.low
        others = (c.high if is_high else c.low for i, c in enumerate(window) if i != strength)
        strictly_extreme = all(extreme > v for v in others) if is_high \
            else all(extreme < v for v in others)
        if not strictly_extreme:
            return

        zone = (extreme - ctx.spec.tick_size, extreme + ctx.spec.tick_size)
        level_id = f"{ctx.symbol}-{kind.name}-{tf.value}-{mid.ts.isoformat()}"

        if any(lv.id == level_id for lv in ctx.levels):
            return
        if any(
            lv.kind is kind and lv.tf is tf and lv.state not in TERMINAL
            and self._overlaps(lv.zone, zone)   # dead levels don't block re-formation
            for lv in ctx.levels
        ):
            return

        ctx.levels.append(Level(
            id=level_id,
            symbol=ctx.symbol,
            kind=kind,
            zone=zone,
            born=mid.ts,
            tf=tf,
            state=LevelState.ACTIVE,
        ))

    @staticmethod
    def _overlaps(a: tuple, b: tuple) -> bool:
        return a[0] <= b[1] and b[0] <= a[1]
