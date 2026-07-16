"""Volume/VSA detector ("volume"): classifies the latest closed tf candle as
climax, stopping_volume, no_demand or absorption (priority order; first
match wins), then emits ONE confirming Evidence -- strength 0.3, ttl 6 --
ONLY when some other detector's Evidence in ctx.evidence_history overlaps
the candle's (low, high) range within the last 6 closed tf-candles (nearest
ts wins). Direction and zone are copied from that confirmed evidence; a pure
booster, it never speaks on its own. Needs sma+1 closed candles (SMA/stddev
exclude the current candle) else []. Params: tf, sma, z_hi."""

from __future__ import annotations

import statistics

from trader.detectors.base import Detector, register
from trader.engine.context import StockContext
from trader.models.candle import Candle, Timeframe
from trader.models.evidence import Evidence

_DEFAULTS = {"tf": "5m", "sma": 20, "z_hi": 1.5}


def _overlaps(a: tuple, b: tuple) -> bool:
    return a[0] <= b[1] and b[0] <= a[1]


@register
class VolumeDetector(Detector):
    name = "volume"

    def __init__(self, params: dict):
        super().__init__({**_DEFAULTS, **params})
        self._seen: set = set()  # latest-candle ts already processed

    def detect(self, ctx: StockContext) -> list[Evidence]:
        tf = Timeframe(self.params["tf"])
        n = int(self.params["sma"])
        window = ctx.candles.last(n + 1, tf)
        if len(window) < n + 1:
            return []
        latest = window[-1]
        if latest.ts in self._seen:
            return []
        self._seen.add(latest.ts)

        volumes = [c.volume for c in window[:-1]]
        sma = statistics.fmean(volumes)
        stddev = statistics.pstdev(volumes)
        classification = self._classify(latest, sma, stddev, ctx.atr(tf))
        if classification is None:
            return []

        confirmed = self._colocated(ctx, tf, latest)
        if confirmed is None:
            return []

        return [Evidence(
            detector=self.name, direction=confirmed.direction, strength=0.3,
            zone=confirmed.zone, ts=ctx.now, ttl_candles=6,
            meta={"vsa": classification, "confirms": confirmed.detector, "event": "VSA"},
        )]

    def _classify(self, latest: Candle, sma: float, stddev: float, atr) -> str | None:
        vol = latest.volume
        if atr is not None and latest.range > 2 * atr and vol > 2 * sma:
            return "climax"
        if not latest.is_bullish and vol > 1.5 * sma and latest.range > 0 and \
                latest.lower_wick >= latest.range / 2:
            return "stopping_volume"
        if latest.is_bullish and vol < 0.7 * sma:
            return "no_demand"
        z = (vol - sma) / stddev if stddev else 0.0
        if atr is not None and z > self.params["z_hi"] and latest.body < atr * 3 / 10:
            return "absorption"
        return None

    def _colocated(self, ctx: StockContext, tf: Timeframe, latest: Candle) -> Evidence | None:
        window = ctx.candles.last(6, tf)
        cutoff = window[0].ts
        zone = (latest.low, latest.high)
        candidates = [
            e for e in ctx.evidence_history
            if e.detector != self.name and e.ts >= cutoff and _overlaps(e.zone, zone)
        ]
        return max(candidates, key=lambda e: e.ts, default=None)
