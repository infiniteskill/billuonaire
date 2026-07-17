"""Wyckoff detector ("wyckoff"): range events + phase classifier.

Range: the ``window`` closed tf candles before the latest one form a band;
band height < range_atr*ATR => in-range (lo/hi = that min low / max high).
Events on the latest candle, both needing vol > 1.5x own SMA (prior
``vol_sma`` candles): spring = wick below lo with close in the upper half of
its own range => LONG 0.8 ttl 24, zone lo +/- 1 tick; upthrust mirror =>
SHORT 0.8. Deduped per (candle ts, event); last event kept in instance
memory for phase().

``phase(ctx) -> (name, confidence)`` -- NOT Evidence -- classifies the last
``window`` candles: <window or no ATR => UNCLEAR 0.0; in-range => event
within the last 10 candles ? ACCUMULATION/DISTRIBUTION 0.7 : UNCLEAR 0.4;
out-of-range => |net close change| > 1xATR ? MARKUP/MARKDOWN with confidence
min(1, |net|/(3xATR)) : UNCLEAR 0.0; ``atr<=0`` also => UNCLEAR 0.0.
MARKUP/MARKDOWN with confidence >= 0.5 also emits ONE continuation Evidence
0.5 ttl 12 along the phase direction, zone = the latest confirmed
same-direction M5 swing level (SWING_L for MARKUP, SWING_H for MARKDOWN)
from ``ctx.levels`` -- a stable pullback-to-swing entry zone that clusters
with other evidence at that swing instead of drifting every candle; no
such swing yet => no emission that candle. Deduped per candle.

``htf_phase(ctx)``: net D1 close change over the last 10 D1 candles (else
UNCLEAR 0.0); > +2% MARKUP / < -2% MARKDOWN, confidence min(1, |pct|/5)."""

from __future__ import annotations

from decimal import Decimal
from statistics import fmean

from trader.detectors.base import Detector, register
from trader.engine.context import StockContext
from trader.models.candle import Candle, Timeframe
from trader.models.evidence import Direction, Evidence
from trader.models.level import LevelKind

_DEFAULTS = {"tf": "5m", "window": 40, "range_atr": 3.0, "vol_sma": 20}


@register
class WyckoffDetector(Detector):
    name = "wyckoff"

    def __init__(self, params: dict):
        super().__init__({**_DEFAULTS, **params})
        self._seen: set = set()  # (candle ts, event) already emitted
        self._last_event: tuple | None = None  # (name, candle ts), instance memory

    def _band_max(self, atr: Decimal) -> Decimal:
        return Decimal(str(self.params["range_atr"])) * atr

    def detect(self, ctx: StockContext) -> list[Evidence]:
        w = int(self.params["window"])
        candles = ctx.candles.last(w + 1, Timeframe(self.params["tf"]))
        atr = ctx.atr(Timeframe(self.params["tf"]))
        out = []
        if len(candles) == w + 1 and atr is not None:
            ev = self._event(ctx, candles, atr)
            if ev is not None:
                out.append(ev)
        name, conf = self.phase(ctx)
        if name in ("MARKUP", "MARKDOWN") and conf >= 0.5 and candles:
            latest = candles[-1]
            if (latest.ts, "PHASE") not in self._seen:
                zone = self._continuation_zone(ctx, name)
                if zone is not None:
                    self._seen.add((latest.ts, "PHASE"))
                    out.append(Evidence(
                        detector=self.name,
                        direction=Direction.LONG if name == "MARKUP" else Direction.SHORT,
                        strength=0.5, zone=zone,
                        ts=ctx.now, ttl_candles=12,
                        meta={"event": "PHASE", "phase": name}))
        return out

    def _continuation_zone(self, ctx: StockContext, name: str) -> tuple[Decimal, Decimal] | None:
        """Stable continuation zone = latest confirmed same-direction M5 swing
        (pullback-to-swing entry): SWING_L for MARKUP, SWING_H for MARKDOWN.
        None if no such swing exists yet -- caller skips emission."""
        kind = LevelKind.SWING_L if name == "MARKUP" else LevelKind.SWING_H
        swings = [lv for lv in ctx.levels if lv.kind is kind and lv.tf is Timeframe.M5]
        return max(swings, key=lambda lv: lv.born).zone if swings else None

    def _event(self, ctx: StockContext, candles: list[Candle], atr: Decimal) -> Evidence | None:
        rng, latest = candles[:-1], candles[-1]
        lo, hi = min(c.low for c in rng), max(c.high for c in rng)
        if hi - lo >= self._band_max(atr):
            return None  # not in-range: no spring/upthrust possible
        if not latest.volume > 1.5 * fmean(
                c.volume for c in candles[-int(self.params["vol_sma"]) - 1:-1]):
            return None
        mid = latest.low + latest.range / 2
        if latest.low < lo and latest.close > mid:
            event, direction, edge = "SPRING", Direction.LONG, lo
        elif latest.high > hi and latest.close < mid:
            event, direction, edge = "UPTHRUST", Direction.SHORT, hi
        else:
            return None
        if (latest.ts, event) in self._seen:
            return None
        self._seen.add((latest.ts, event))
        self._last_event = (event, latest.ts)
        t = ctx.spec.tick_size
        return Evidence(detector=self.name, direction=direction, strength=0.8,
                        zone=(edge - t, edge + t), ts=ctx.now, ttl_candles=24,
                        meta={"event": event})

    def phase(self, ctx: StockContext) -> tuple[str, float]:
        w = int(self.params["window"])
        candles = ctx.candles.last(w, Timeframe(self.params["tf"]))
        atr = ctx.atr(Timeframe(self.params["tf"]))
        if len(candles) < w or atr is None or atr <= 0:
            return "UNCLEAR", 0.0
        lo, hi = min(c.low for c in candles), max(c.high for c in candles)
        if hi - lo < self._band_max(atr):
            if self._last_event is not None and self._last_event[1] >= candles[-10].ts:
                return ("ACCUMULATION" if self._last_event[0] == "SPRING"
                        else "DISTRIBUTION"), 0.7
            return "UNCLEAR", 0.4
        net = candles[-1].close - candles[0].close
        if abs(net) > atr:
            return ("MARKUP" if net > 0 else "MARKDOWN"), min(1.0, float(abs(net) / (3 * atr)))
        return "UNCLEAR", 0.0

    def htf_phase(self, ctx: StockContext) -> tuple[str, float]:
        d1 = ctx.candles.last(10, Timeframe.D1)
        if len(d1) < 10:
            return "UNCLEAR", 0.0
        pct = float((d1[-1].close - d1[0].close) / d1[0].close * 100)
        if abs(pct) > 2:
            return ("MARKUP" if pct > 0 else "MARKDOWN"), min(1.0, abs(pct) / 5)
        return "UNCLEAR", 0.0
