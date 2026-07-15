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
from trader.models.candle import TICK, Candle, Timeframe
from trader.models.evidence import Evidence
from trader.models.level import Level, LevelKind, LevelState

_DEFAULT_STRENGTH = 3
_DEFAULT_TIMEFRAMES = ("5m", "15m")


@register
class SwingsDetector(Detector):
    name = "swings"

    def detect(self, ctx: StockContext) -> list[Evidence]:
        strength = int(self.params.get("strength", _DEFAULT_STRENGTH))
        timeframes = self.params.get("timeframes", _DEFAULT_TIMEFRAMES)
        window_size = 2 * strength + 1

        for tf_value in timeframes:
            tf = Timeframe(tf_value)
            window = ctx.candles.last(window_size, tf)
            if len(window) < window_size:
                continue  # not enough closed candles yet for this tf
            mid = window[strength]
            self._confirm(ctx, window, mid, strength, tf, kind=LevelKind.SWING_H)
            self._confirm(ctx, window, mid, strength, tf, kind=LevelKind.SWING_L)

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

        zone = (extreme - TICK, extreme + TICK)
        level_id = f"{ctx.symbol}-{kind.name}-{tf.value}-{mid.ts.isoformat()}"

        if any(lv.id == level_id for lv in ctx.levels):
            return
        if any(
            lv.kind is kind and lv.tf is tf and self._overlaps(lv.zone, zone)
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
