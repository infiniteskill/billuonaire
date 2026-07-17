"""Sweep detector ("sweep"): reversal Evidence when a level got SWEPT on the
latest closed tf candle. HIGH-kind swept -> SHORT, LOW-kind -> LONG.
Quality: 0.4 + 0.25*pool + 0.2 touches>=3 + 0.15 daily/weekly + 0.1 trap
chain depth>=2, cap 1.0; ttl 18.

If that level later turns RECLAIMED within reclaim_bonus_candles of the
sweep, a second, upgraded Evidence is emitted: same fields as the original,
strength = original + 0.1 (cap 1.0), meta gains {"upgrade": True}. Exactly
two Evidence max per (level_id, swept ts) episode (in-instance memory, lost
on restart)."""

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
_HIGH_POOLS = frozenset({LevelKind.PWH, LevelKind.PWL,
                         LevelKind.OPEN_RANGE_H, LevelKind.OPEN_RANGE_L})


@register
class SweepDetector(Detector):
    name = "sweep"

    def __init__(self, params: dict):
        super().__init__({**_DEFAULTS, **params})
        self._seen: set[tuple[str, datetime, bool]] = set()  # (level_id, swept ts, upgraded)
        self._base: dict[tuple[str, datetime], Evidence] = {}  # swept-tick evidence, keyed
        # by (level_id, swept ts); consulted to build the later reclaim upgrade.

    def on_session_end(self) -> None:
        self._seen.clear()   # episodes are ts-keyed: old ts never recurs, and
        self._base.clear()   # the reclaim window never spans a session gap

    def detect(self, ctx: StockContext) -> list[Evidence]:
        tf = Timeframe(self.params["tf"])
        window = ctx.candles.last(int(self.params["reclaim_bonus_candles"]) + 1, tf)
        if not window:
            return []
        out = []
        for lv in ctx.levels:
            side = _SIDE_BY_KIND.get(lv.kind)  # ROUND is side-less: skip
            episode = self._episode(lv, window) if side else None
            if episode is None:
                continue
            swept_ts, is_reclaim = episode
            key = (lv.id, swept_ts, is_reclaim)
            if key in self._seen:
                continue
            self._seen.add(key)
            if is_reclaim:
                base = self._base.get((lv.id, swept_ts))
                if base is None:
                    continue  # episode started before this instance existed
                out.append(Evidence(
                    detector=base.detector, direction=base.direction,
                    strength=min(base.strength + 0.1, 1.0), zone=base.zone,
                    ts=ctx.now, ttl_candles=base.ttl_candles,
                    meta={**base.meta, "upgrade": True},
                ))
                continue
            direction = Direction.SHORT if side == "below" else Direction.LONG
            depth = self._chain_depth(ctx, tf, direction)
            q = (0.4 + 0.25 * self._pool_strength(lv, ctx.now)
                 + 0.2 * (lv.touches >= 3) + 0.15 * (lv.kind in _DAILY_WEEKLY)
                 + 0.1 * (depth >= 2))
            ev = Evidence(
                detector=self.name, direction=direction, strength=min(q, 1.0),
                zone=lv.zone, ts=ctx.now, ttl_candles=18,
                meta={"level_id": lv.id, "kind": lv.kind.name, "chain_depth": depth,
                      "event": "SWEEP"},
            )
            self._base[(lv.id, swept_ts)] = ev
            out.append(ev)
        return out

    @staticmethod
    def _episode(lv: Level, window: list[Candle]) -> tuple[datetime, bool] | None:
        """(swept_ts, is_reclaim) if the level swept on the latest closed
        candle (is_reclaim=False), or RECLAIMED this candle after sweeping at
        most reclaim_bonus_candles earlier (is_reclaim=True); else None."""
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
        if lv.kind in _HIGH_POOLS:  # axiom 5: OR + weekly = HIGH liquidity
            return 0.7
        return 0.6 if lv.kind in (LevelKind.PDH, LevelKind.PDL) else 0.5
