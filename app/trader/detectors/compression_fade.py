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

CONTINUUM: the window is ``ctx.candles.last(bw + 1)`` -- continuous
multi-day history, never session-scoped. That is how the edge was VALIDATED
(rr.py::compress_fade ran one concatenated multi-day series): a coil formed
on day 1's last bars stays fadeable by day 2's first bars.

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
        # Continuum: coils carry across the gap, so dedupe must survive the
        # boundary. Prune by age only -- a coil older than break_window bars
        # can never re-enter the window, so dropping it is provably safe.
        self._emitted = set(sorted(self._emitted)[-int(self.params["break_window"]):])

    def detect(self, ctx: StockContext) -> list[Evidence]:
        tf = Timeframe(self.params["tf"])
        bw = int(self.params["break_window"])
        window = ctx.candles.last(bw + 1, tf)
        if len(window) < 2:
            return []
        j = window[-1]
        atr = ctx.atr(tf)
        floor = Decimal(str(self.params["sl_atr_floor"])) * atr if atr else Decimal(0)
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
            meta = {"event": "COMPRESSION_FADE", "sl": str(sl), "sl_floor": str(floor)}
            out.append(Evidence(detector=self.name, direction=direction,
                                strength=self._strength(c),
                                zone=(min(sl, entry), max(sl, entry)),
                                ts=ctx.now, ttl_candles=2, meta=meta))
        return out

    def _is_compress(self, c: Candle) -> bool:
        # float, not Decimal: rr.py::compress_fade classifies in float, and
        # its 0.2/0.35*range rounding occasionally lands exactly on a tick-
        # quantized wick/body (e.g. 0.2*1.5 == 0.30000000000000004 in float
        # but == 0.3 in Decimal) -- Decimal here would silently reclassify
        # those candles, diverging from the validated reference (parity-gated
        # in test_compression_fade.py).
        r = float(c.range)
        if r <= 0:
            return False
        bf, wf = float(self.params["body_frac"]), float(self.params["wick_frac"])
        return (float(c.body) <= bf * r and float(c.upper_wick) >= wf * r
                and float(c.lower_wick) >= wf * r)

    def _strength(self, c: Candle) -> float:
        """Coil quality: tighter body + bigger min-wick => higher, linear in
        [0, 1] over the [threshold, extreme] range of each ratio."""
        bf, wf = float(self.params["body_frac"]), float(self.params["wick_frac"])
        body_ratio = float(c.body / c.range)
        wick_ratio = float(min(c.upper_wick, c.lower_wick) / c.range)
        wick_span = max(0.5 - wf, 1e-9)
        s = (bf - body_ratio) / bf * 0.5 + (wick_ratio - wf) / wick_span * 0.5
        return min(1.0, max(0.0, s))
