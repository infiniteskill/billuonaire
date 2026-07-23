"""Structure detector ("structure"): BOS/CHoCH Evidence from SWING_H/L levels
of its tf. Trend = last `trend_swings` swings (HH+HL bullish, LH+LL bearish,
else ranging -> nothing). BOS: close beyond last same-side swing mid with
trend (0.6, ttl 12). CHoCH: close beyond last opposite swing mid against trend
(0.8 if any SWEPT transition within last `trap_window` candles, else 0.5;
ttl 24); wins over BOS. Fake-BOS memory is in-instance only (lost on restart),
expires `fake_window` candles after the fake and clears on session change.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from trader.detectors.base import Detector, register
from trader.engine.context import StockContext
from trader.models.candle import Candle, Timeframe
from trader.models.evidence import Direction, Evidence
from trader.models.level import Level, LevelKind, LevelState

_DEFAULTS = {"tf": "5m", "trend_swings": 4, "trap_window": 6, "fake_window": 5,
             "anchor": "swing"}  # "ext" -> grade against taught EXT extremes not fractal


def _mid(zone: tuple[Decimal, Decimal]) -> Decimal:
    return (zone[0] + zone[1]) / 2


@register
class StructureDetector(Detector):
    name = "structure"

    def __init__(self, params: dict):
        super().__init__({**_DEFAULTS, **params})
        ext = self.params.get("anchor") == "ext"
        self._hk = LevelKind.EXT_H if ext else LevelKind.SWING_H
        self._lk = LevelKind.EXT_L if ext else LevelKind.SWING_L
        self._pending: dict[str, list[dict]] = {}  # symbol -> unresolved BOS breaks
        self._fake: dict[str, datetime] = {}       # symbol -> ts of last fake BOS
        self._session: date | None = None

    def on_session_end(self) -> None:
        self._pending, self._fake = {}, {}

    def detect(self, ctx: StockContext) -> list[Evidence]:
        if ctx.day.session_date != self._session:  # new session: stale memories
            self._session = ctx.day.session_date
            self._pending, self._fake = {}, {}
        tf = Timeframe(self.params["tf"])
        last = ctx.candles.last(1, tf)
        swings = sorted(
            (lv for lv in ctx.levels
             if lv.kind in (self._hk, self._lk) and lv.tf is tf),
            key=lambda lv: lv.born,
        )
        if not last or not swings:
            return []
        candle = last[-1]
        self._update_fake(ctx, tf, candle)

        trend = self._trend(swings[-int(self.params["trend_swings"]):])
        if trend is Direction.NEUTRAL:
            return []
        highs = [lv for lv in swings if lv.kind is self._hk]
        lows = [lv for lv in swings if lv.kind is self._lk]
        up = trend is Direction.LONG
        with_, against = (highs[-1], lows[-1]) if up else (lows[-1], highs[-1])

        c = candle.close
        if (c < _mid(against.zone)) if up else (c > _mid(against.zone)):  # CHoCH wins
            strength = 0.8 if self._swept_recently(ctx, tf) else 0.5
            ev = self._evidence(ctx, "CHOCH", against,
                                Direction.SHORT if up else Direction.LONG, strength, 24)
        elif (c > _mid(with_.zone)) if up else (c < _mid(with_.zone)):
            ev = self._evidence(ctx, "BOS", with_, trend, 0.6, 12)
            if ev:
                self._pending.setdefault(ctx.symbol, []).append(
                    {"ts": candle.ts, "level": _mid(with_.zone), "up": up})
        else:
            return []
        return [ev] if ev else []

    def _trend(self, recent: list[Level]) -> Direction:
        highs = [_mid(lv.zone) for lv in recent if lv.kind is self._hk]
        lows = [_mid(lv.zone) for lv in recent if lv.kind is self._lk]
        if len(highs) < 2 or len(lows) < 2:
            return Direction.NEUTRAL
        rising = lambda xs: all(a < b for a, b in zip(xs, xs[1:]))
        falling = lambda xs: all(a > b for a, b in zip(xs, xs[1:]))
        if rising(highs) and rising(lows):
            return Direction.LONG
        if falling(highs) and falling(lows):
            return Direction.SHORT
        return Direction.NEUTRAL

    def _evidence(self, ctx: StockContext, event: str, swing: Level,
                  direction: Direction, strength: float, ttl: int) -> Evidence | None:
        if any(e.detector == self.name and e.meta.get("event") == event
               and e.meta.get("swing_id") == swing.id for e in ctx.evidence_history):
            return None  # already emitted for this swing
        meta = {"event": event, "swing_id": swing.id}
        if ctx.symbol in self._fake:               # unexpired: pruned in detect
            meta["fake_bos_recent"] = True
        m, T = _mid(swing.zone), ctx.spec.tick_size
        return Evidence(detector=self.name, direction=direction, strength=strength,
                        zone=(m - T, m + T), ts=ctx.now, ttl_candles=ttl, meta=meta)

    def _swept_recently(self, ctx: StockContext, tf: Timeframe) -> bool:
        window = ctx.candles.last(int(self.params["trap_window"]), tf)
        cutoff = window[0].ts
        return any(ts >= cutoff and st is LevelState.SWEPT
                   for lv in ctx.levels for ts, st in lv.state_history)

    def _update_fake(self, ctx: StockContext, tf: Timeframe, candle: Candle) -> None:
        """Resolve pending BOS breaks: close back beyond the break level within
        `fake_window` candles -> record fake; older with no close-back -> drop."""
        fw = int(self.params["fake_window"])
        keep = []
        for p in self._pending.get(ctx.symbol, []):
            since = [c for c in ctx.candles.last(fw + 1, tf) if c.ts > p["ts"]]
            if any((c.close < p["level"]) if p["up"] else (c.close > p["level"])
                   for c in since[:fw]):
                self._fake[ctx.symbol] = candle.ts
            elif len(since) <= fw:
                keep.append(p)  # still inside the watch window
        self._pending[ctx.symbol] = keep
        ts = self._fake.get(ctx.symbol)            # expire the flag after fw candles
        if ts is not None and candle.ts - ts > fw * timedelta(minutes=tf.minutes):
            del self._fake[ctx.symbol]
