"""Breaker detector ("breaker"): continuation Evidence when an inverted
level (former support/resistance flipped by the LevelEngine to INVERTED) is
retested from its new side and holds.

Watched kinds: OB_BULL, OB_BEAR, SWING_H, SWING_L, OPEN_RANGE_H,
OPEN_RANGE_L, state == INVERTED. Direction is the flip of the level's
original side (``_SIDE_BY_KIND``): original "below" (price used to sit
below the zone) -> now price lives above it -> LONG; original "above" ->
now below -> SHORT.

Retest: the latest closed tf candle's range overlaps the zone while its
close is fully back on the new side (beyond the near edge, away from the
zone) -- same "on origin side" shape the LevelEngine itself uses, just
mirrored to the post-inversion side. Fires strength 0.85, ttl 12 candles,
meta {"level_id", "event": "BREAKER_RETEST"}.

Dedupe is per INVERTED episode, not per candle: keyed on (level_id, ts of
the level's latest INVERTED entry in state_history). Once an episode has
fired, later retest candles within that same episode are silent; a fresh
inversion (new ts) starts a new episode and can fire again.
"""

from __future__ import annotations

from trader.detectors.base import Detector, register
from trader.engine.context import StockContext
from trader.engine.levels import _SIDE_BY_KIND
from trader.models.candle import Timeframe
from trader.models.evidence import Direction, Evidence
from trader.models.level import LevelKind, LevelState

_DEFAULTS = {"tf": "5m"}
_WATCH_KINDS = frozenset({
    LevelKind.OB_BULL, LevelKind.OB_BEAR, LevelKind.SWING_H, LevelKind.SWING_L,
    LevelKind.OPEN_RANGE_H, LevelKind.OPEN_RANGE_L,
})


@register
class BreakerDetector(Detector):
    name = "breaker"

    def __init__(self, params: dict):
        super().__init__({**_DEFAULTS, **params})
        self._seen: set[tuple[str, object]] = set()  # (level_id, inversion ts)

    def on_session_end(self) -> None:
        self._seen.clear()   # watched kinds never carry across sessions

    def detect(self, ctx: StockContext) -> list[Evidence]:
        tf = Timeframe(self.params["tf"])
        window = ctx.candles.last(1, tf)
        if not window:
            return []
        candle = window[-1]
        out = []
        for lv in ctx.levels:
            if lv.kind not in _WATCH_KINDS or lv.state is not LevelState.INVERTED:
                continue
            inv_ts = next((ts for ts, st in reversed(lv.state_history)
                           if st is LevelState.INVERTED), None)
            if inv_ts is None or (lv.id, inv_ts) in self._seen:
                continue
            lo, hi = lv.zone
            orig_side = _SIDE_BY_KIND[lv.kind]
            overlap = candle.low <= hi and candle.high >= lo
            on_new_side = candle.close > hi if orig_side == "below" else candle.close < lo
            if not (overlap and on_new_side):
                continue
            self._seen.add((lv.id, inv_ts))
            direction = Direction.LONG if orig_side == "below" else Direction.SHORT
            out.append(Evidence(
                detector=self.name, direction=direction, strength=0.85,
                zone=lv.zone, ts=ctx.now, ttl_candles=12,
                meta={"level_id": lv.id, "event": "BREAKER_RETEST"},
            ))
        return out
