"""Index-context detector ("index"): surfaces the parent index's trend as
NEUTRAL-direction context evidence (Phase 4's confluence layer applies the
counter-index haircut; this detector just reports).

requires {"index"} -> skipped while ``ctx.index`` is None (Phase 4 wires the
orchestrator that populates it). trend NEUTRAL -> no evidence. Otherwise one
NEUTRAL Evidence per new closed M5 candle: strength = index.strength * 0.5,
zone = candle's (low, high); [] (no evidence) when no closed M5 candle
exists yet. ttl 1, meta {"trend": index.trend.name, "phase": index.phase,
"event": "INDEX"}."""

from __future__ import annotations

from trader.detectors.base import Detector, register
from trader.engine.context import StockContext
from trader.models.candle import Timeframe
from trader.models.evidence import Direction, Evidence


@register
class IndexDetector(Detector):
    name = "index"
    requires = frozenset({"index"})

    def __init__(self, params: dict):
        super().__init__(dict(params))
        self._seen: set = set()

    def on_session_end(self) -> None:
        self._seen.clear()   # ts-keyed: old ts never recurs

    def detect(self, ctx: StockContext) -> list[Evidence]:
        if ctx.index.trend is Direction.NEUTRAL:
            return []
        window = ctx.candles.last(1, Timeframe.M5)
        if not window:
            return []
        key = window[-1].ts
        if key in self._seen:
            return []
        self._seen.add(key)
        zone = (window[-1].low, window[-1].high)
        return [Evidence(
            detector=self.name, direction=Direction.NEUTRAL,
            strength=ctx.index.strength * 0.5, zone=zone, ts=ctx.now, ttl_candles=1,
            meta={"trend": ctx.index.trend.name, "phase": ctx.index.phase, "event": "INDEX"},
        )]
