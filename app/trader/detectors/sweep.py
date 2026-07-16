"""Sweep detector ("sweep"): reversal Evidence when a level got SWEPT on the
latest closed tf candle, or RECLAIMED this candle after a sweep at most
reclaim_bonus_candles earlier. HIGH-kind swept -> SHORT, LOW-kind -> LONG.
Quality: 0.4 + 0.25*pool + 0.2 touches>=3 + 0.15 daily/weekly + 0.1 fast
reclaim + 0.1 trap chain depth>=2, cap 1.0; ttl 18. One Evidence per
(level_id, swept ts) episode (in-instance memory, lost on restart)."""

from __future__ import annotations

from datetime import datetime

from trader.detectors.base import Detector, register
from trader.engine.context import StockContext
from trader.engine.levels import _SIDE_BY_KIND
from trader.models.candle import Candle, Timeframe
from trader.models.evidence import Direction, Evidence
from trader.models.level import Level, LevelKind, LevelState

_DEFAULTS = {"tf": "5m", "reclaim_bonus_candles": 3, "chain_window": 20}
_DAILY_WEEKLY = frozenset({LevelKind.PDH, LevelKind.PDL, LevelKind.PWH, LevelKind.PWL})


@register
class SweepDetector(Detector):
    name = "sweep"

    def __init__(self, params: dict):
        super().__init__({**_DEFAULTS, **params})
        self._seen: set[tuple[str, datetime]] = set()  # (level_id, swept ts)

    def detect(self, ctx: StockContext) -> list[Evidence]:
        tf = Timeframe(self.params["tf"])
        window = ctx.candles.last(int(self.params["reclaim_bonus_candles"]) + 1, tf)
        if not window:
            return []
        out = []
        for lv in ctx.levels:
            side = _SIDE_BY_KIND.get(lv.kind)  # ROUND is side-less: skip
            hit = self._episode(lv, window) if side else None
            if hit is None or (lv.id, hit[0]) in self._seen:
                continue
            swept_ts, fast_reclaim = hit
            direction = Direction.SHORT if side == "below" else Direction.LONG
            depth = self._chain_depth(ctx, tf, direction)
            q = (0.4 + 0.25 * self._pool_strength(lv, ctx.now)
                 + 0.2 * (lv.touches >= 3) + 0.15 * (lv.kind in _DAILY_WEEKLY)
                 + 0.1 * fast_reclaim + 0.1 * (depth >= 2))
            self._seen.add((lv.id, swept_ts))
            out.append(Evidence(
                detector=self.name, direction=direction, strength=min(q, 1.0),
                zone=lv.zone, ts=ctx.now, ttl_candles=18,
                meta={"level_id": lv.id, "kind": lv.kind.name, "chain_depth": depth},
            ))
        return out

    @staticmethod
    def _episode(lv: Level, window: list[Candle]) -> tuple[datetime, bool] | None:
        """(swept_ts, fast_reclaim) if the level swept on the latest closed
        candle or fast-reclaimed on it; else None."""
        swept = [ts for ts, st in lv.state_history if st is LevelState.SWEPT]
        if not swept:
            return None
        swept_ts, latest = swept[-1], window[-1].ts
        if lv.state is LevelState.SWEPT and swept_ts == latest:
            return swept_ts, False
        if (lv.state is LevelState.RECLAIMED and lv.state_history[-1][0] == latest
                and window[0].ts <= swept_ts < latest):
            return swept_ts, True
        return None

    def _chain_depth(self, ctx: StockContext, tf: Timeframe, direction: Direction) -> int:
        window = ctx.candles.last(int(self.params["chain_window"]), tf)
        prior = [e.meta.get("chain_depth", 0) for e in ctx.evidence_history
                 if e.detector == self.name and e.ts >= window[0].ts
                 and e.direction.value == -direction.value]
        return 1 + max(prior, default=0)

    @staticmethod
    def _pool_strength(lv: Level, now: datetime) -> float:
        if lv.kind in (LevelKind.EQH, LevelKind.EQL):
            recency = max(0.0, 1 - (now - lv.born).total_seconds() / 3600 / 48)
            return min(lv.touches / 5, 1.0) * 0.7 + recency * 0.3
        return 0.6 if lv.kind in _DAILY_WEEKLY else 0.5
