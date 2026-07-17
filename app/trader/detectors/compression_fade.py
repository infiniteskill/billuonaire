"""Compression-fade detector ("compression_fade"): highest-sample validated
edge (rr.py::compress_fade, EOD-clean n=6144, win@3R=31%, exp +0.26R). A
compression candle (body <= body_frac*range, both wicks >= wick_frac*range)
that breaks within the next ``break_window`` closed candles is FADED, not
followed: a break of its high => SHORT (retail chases the up-break, we sell
it, sl = break high); a break of its low => LONG (sl = break low). Pure
signal-emitter: no Levels, entry = close of the break candle.

Streaming note: each tick only tests the just-closed candle as a break
candidate against every compression candle still inside the break_window
lookback, so the batch "first break wins" semantics fall out for free -- a
compression candle is deduped (by its ts) the first tick it fires, so a
later tick can never re-attribute its break to a different bar.

The measured 0.15*ATR SL floor is annotated (meta["sl_floor"]) for the
executor to apply; this detector does not floor "sl" itself (that stays the
literal break extreme) and does not wire the planner -- see task brief
integration caveat."""

from __future__ import annotations

from decimal import Decimal

from trader.detectors.base import Detector, register
from trader.engine.context import StockContext
from trader.models.candle import Candle, Timeframe
from trader.models.evidence import Direction, Evidence

_DEFAULTS = {"tf": "5m", "break_window": 3, "body_frac": 0.35,
             "wick_frac": 0.2, "sl_atr_floor": 0.15}


@register
class CompressionFadeDetector(Detector):
    name = "compression_fade"

    def __init__(self, params: dict):
        super().__init__({**_DEFAULTS, **params})
        self._emitted: set = set()  # compression candle ts already fired

    def on_session_end(self) -> None:
        self._emitted.clear()

    def detect(self, ctx: StockContext) -> list[Evidence]:
        tf = Timeframe(self.params["tf"])
        bw = int(self.params["break_window"])
        window = ctx.candles.today(tf)[-(bw + 1):]
        if len(window) < 2:
            return []
        j = window[-1]
        atr = ctx.atr(tf)
        floor = Decimal(str(self.params["sl_atr_floor"])) * atr if atr else None
        out = []
        for c in window[:-1]:
            if c.ts in self._emitted or not self._is_compress(c):
                continue
            if j.high > c.high:
                sl, direction = j.high, Direction.SHORT
            elif j.low < c.low:
                sl, direction = j.low, Direction.LONG
            else:
                continue
            self._emitted.add(c.ts)
            entry = j.close
            meta = {"event": "COMPRESSION_FADE", "sl": sl, "entry": entry}
            if floor is not None:
                meta["sl_floor"] = floor
            out.append(Evidence(detector=self.name, direction=direction,
                                strength=self._strength(c),
                                zone=(min(sl, entry), max(sl, entry)),
                                ts=ctx.now, ttl_candles=2, meta=meta))
        return out

    def _is_compress(self, c: Candle) -> bool:
        r = c.range
        if r <= 0:
            return False
        bf = Decimal(str(self.params["body_frac"]))
        wf = Decimal(str(self.params["wick_frac"]))
        return c.body <= bf * r and c.upper_wick >= wf * r and c.lower_wick >= wf * r

    def _strength(self, c: Candle) -> float:
        """Coil quality: tighter body + bigger min-wick => higher, linear in
        [0, 1] over the [threshold, extreme] range of each ratio."""
        bf, wf = float(self.params["body_frac"]), float(self.params["wick_frac"])
        body_ratio = float(c.body / c.range)
        wick_ratio = float(min(c.upper_wick, c.lower_wick) / c.range)
        wick_span = max(0.5 - wf, 1e-9)
        s = (bf - body_ratio) / bf * 0.5 + (wick_ratio - wf) / wick_span * 0.5
        return min(1.0, max(0.0, s))
