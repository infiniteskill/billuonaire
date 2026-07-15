"""Liquidity detector: creates draw-on-liquidity Levels (PDH/PDL, opening
range, round numbers, equal highs/lows) and emits proximity Evidence when
price trades near an untapped pool.

Design recap (task-4 brief + binding decisions):
- name = "liquidity"; params {"eq_tolerance": 0.001, "round_steps":
  [50, 100, 500], "round_within_pct": 2.0, "proximity_atr": 1.0}.
- Level creation is a documented side channel (see swings.py): this
  detector mutates ``ctx.levels`` in place, in addition to returning
  Evidence.

Level creation:
- PDH/PDL: extremes of ``ctx.candles.prev_day(M1)``; skipped when there is
  no prior session. id ``f"{symbol}-PDH-{session_date}"`` where
  ``session_date`` is the *current* session's date, so a fresh pair is
  created (and only once, by id) each trading day.
- OPEN_RANGE_H/L: extremes of the first 15 M1 candles of today's session
  (09:15-09:29); only creatable once all 15 have closed (now >= 09:30).
- ROUND: for each configured step, the nearest multiple of step to the
  latest closed M1 close; created iff within ``round_within_pct`` % of
  that close. Side-less (no H/L distinction) -- LevelEngine assigns
  significance via prev_close. id includes the step and the rounded price
  so distinct round levels can coexist and re-detection is idempotent.
- EQH/EQL: clusters of 2+ ACTIVE/TESTED SWING_H (or SWING_L) levels whose
  zone midpoints are all within ``eq_tolerance`` (relative) of the
  cluster's anchor (its first, lowest-mid member -- clustering is a
  single left-to-right sweep over midpoint-sorted candidates, not a full
  pairwise search). A new EQH/EQL Level spans the min..max of the
  cluster's zones; ``touches`` = cluster size, ``born`` = the newest
  member's ``born`` (so recency below is measured from the freshest
  swing). An existing EQH/EQL whose zone overlaps a newly computed
  cluster is *updated in place* (touches/zone/born) instead of
  duplicated -- this is how a pool's ``touches`` grows over time as more
  swings cluster in, without ever emitting a second Level for it.

Proximity Evidence (the only Evidence this detector emits):
- Candidate pools: PDH/PDL/EQH/EQL/OPEN_RANGE_H/OPEN_RANGE_L/ROUND levels
  in state ACTIVE or TESTED (SWEPT/DEAD pools are exhausted -- never a
  draw).
- The nearest pool at/above and the nearest pool strictly below the
  latest closed M1 close are each considered; a pool enters if within
  ``proximity_atr * ATR(M5)`` of price. ATR(M5) is None -> no evidence at
  all (no way to measure "close").
- ``strength = pool_strength * 0.5``, where ``pool_strength`` is the EQ
  cluster's strength (touches/recency blend, recomputed every call from
  the level's current ``touches``/``born`` -- Level carries no separate
  meta field for it) for EQH/EQL, 0.6 for PDH/PDL, else 0.4.
- ``Evidence(direction=NEUTRAL, zone=level.zone, ttl_candles=12,
  meta={kind, level_id, distance_atr})``; at most 2 (one above, one
  below) per call.
"""

from __future__ import annotations

from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from trader.detectors.base import Detector, register
from trader.engine.context import StockContext
from trader.models.candle import TICK, Timeframe, tick
from trader.models.evidence import Direction, Evidence
from trader.models.level import Level, LevelKind, LevelState

_ACTIVE_STATES = (LevelState.ACTIVE, LevelState.TESTED)
_PROXIMITY_KINDS = frozenset({
    LevelKind.PDH, LevelKind.PDL, LevelKind.EQH, LevelKind.EQL,
    LevelKind.OPEN_RANGE_H, LevelKind.OPEN_RANGE_L, LevelKind.ROUND,
})
_OPEN_RANGE_MINUTES = 15
_DEFAULT_PARAMS = {
    "eq_tolerance": 0.001,
    "round_steps": [50, 100, 500],
    "round_within_pct": 2.0,
    "proximity_atr": 1.0,
}


def _mid(zone: tuple[Decimal, Decimal]) -> Decimal:
    return (zone[0] + zone[1]) / 2


def _overlaps(a: tuple, b: tuple) -> bool:
    return a[0] <= b[1] and b[0] <= a[1]


@register
class LiquidityDetector(Detector):
    name = "liquidity"

    def detect(self, ctx: StockContext) -> list[Evidence]:
        self._create_pdh_pdl(ctx)
        self._create_open_range(ctx)
        self._create_round(ctx)
        self._create_eq(ctx, LevelKind.SWING_H, LevelKind.EQH)
        self._create_eq(ctx, LevelKind.SWING_L, LevelKind.EQL)
        return self._proximity_evidence(ctx)

    # ---- PDH/PDL -----------------------------------------------------

    def _create_pdh_pdl(self, ctx: StockContext) -> None:
        prev = ctx.candles.prev_day(Timeframe.M1)
        if not prev:
            return
        high = max(c.high for c in prev)
        low = min(c.low for c in prev)
        session_date = ctx.day.session_date
        self._create_once(
            ctx, f"{ctx.symbol}-PDH-{session_date}", LevelKind.PDH,
            (high - TICK, high + TICK),
        )
        self._create_once(
            ctx, f"{ctx.symbol}-PDL-{session_date}", LevelKind.PDL,
            (low - TICK, low + TICK),
        )

    # ---- Opening range -------------------------------------------------

    def _create_open_range(self, ctx: StockContext) -> None:
        today = ctx.candles.today(Timeframe.M1)
        if len(today) < _OPEN_RANGE_MINUTES:
            return
        window = today[:_OPEN_RANGE_MINUTES]
        high = max(c.high for c in window)
        low = min(c.low for c in window)
        session_date = ctx.day.session_date
        self._create_once(
            ctx, f"{ctx.symbol}-ORH-{session_date}", LevelKind.OPEN_RANGE_H,
            (high - TICK, high + TICK),
        )
        self._create_once(
            ctx, f"{ctx.symbol}-ORL-{session_date}", LevelKind.OPEN_RANGE_L,
            (low - TICK, low + TICK),
        )

    # ---- Round numbers -------------------------------------------------

    def _create_round(self, ctx: StockContext) -> None:
        last = ctx.candles.last(1, Timeframe.M1)
        if not last:
            return
        close = last[-1].close
        if close <= 0:
            return
        within_pct = Decimal(str(self.params.get("round_within_pct", _DEFAULT_PARAMS["round_within_pct"])))
        steps = self.params.get("round_steps", _DEFAULT_PARAMS["round_steps"])
        for step in steps:
            step_d = Decimal(str(step))
            nearest = (close / step_d).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * step_d
            if nearest <= 0:
                continue
            pct = abs(nearest - close) / close * 100
            if pct > within_pct:
                continue
            nearest = tick(nearest)
            level_id = f"{ctx.symbol}-ROUND-{step}-{nearest}"
            self._create_once(
                ctx, level_id, LevelKind.ROUND, (nearest - TICK, nearest + TICK),
            )

    # ---- Equal highs/lows -----------------------------------------------

    def _create_eq(
        self, ctx: StockContext, source: LevelKind, target: LevelKind,
    ) -> None:
        tolerance = Decimal(str(self.params.get("eq_tolerance", _DEFAULT_PARAMS["eq_tolerance"])))
        candidates = sorted(
            (lv for lv in ctx.levels if lv.kind is source and lv.state in _ACTIVE_STATES),
            key=lambda lv: _mid(lv.zone),
        )

        groups: list[list[Level]] = []
        current: list[Level] = []
        anchor: Decimal | None = None
        for lv in candidates:
            m = _mid(lv.zone)
            if current and anchor is not None and abs(m - anchor) / anchor <= tolerance:
                current.append(lv)
            else:
                if len(current) >= 2:
                    groups.append(current)
                current = [lv]
                anchor = m
        if len(current) >= 2:
            groups.append(current)

        for group in groups:
            zone = (
                min(lv.zone[0] for lv in group),
                max(lv.zone[1] for lv in group),
            )
            touches = len(group)
            born = max(lv.born for lv in group)
            existing = next(
                (lv for lv in ctx.levels if lv.kind is target and _overlaps(lv.zone, zone)),
                None,
            )
            if existing is not None:
                if touches > existing.touches:
                    existing.touches = touches
                    existing.zone = zone
                    existing.born = born
                continue
            ctx.levels.append(Level(
                id=f"{ctx.symbol}-{target.name}-{born.isoformat()}",
                symbol=ctx.symbol, kind=target, zone=zone, born=born,
                tf=None, state=LevelState.ACTIVE, touches=touches,
            ))

    # ---- Proximity evidence ---------------------------------------------

    def _proximity_evidence(self, ctx: StockContext) -> list[Evidence]:
        atr = ctx.atr(Timeframe.M5)
        if atr is None:
            return []
        last = ctx.candles.last(1, Timeframe.M1)
        if not last:
            return []
        price = last[-1].close
        proximity_atr = Decimal(str(self.params.get("proximity_atr", _DEFAULT_PARAMS["proximity_atr"])))
        max_distance = proximity_atr * atr

        pools = [
            lv for lv in ctx.levels
            if lv.kind in _PROXIMITY_KINDS and lv.state in _ACTIVE_STATES
        ]
        above = sorted((lv for lv in pools if _mid(lv.zone) >= price), key=lambda lv: _mid(lv.zone))
        below = sorted((lv for lv in pools if _mid(lv.zone) < price), key=lambda lv: _mid(lv.zone), reverse=True)

        evidence: list[Evidence] = []
        for nearest in (above[:1], below[:1]):
            if not nearest:
                continue
            lv = nearest[0]
            distance = abs(_mid(lv.zone) - price)
            if distance > max_distance:
                continue
            pool_strength = self._pool_strength(lv, ctx.now)
            evidence.append(Evidence(
                detector=self.name,
                direction=Direction.NEUTRAL,
                strength=pool_strength * 0.5,
                zone=lv.zone,
                ts=ctx.now,
                ttl_candles=12,
                meta={
                    "kind": lv.kind.name,
                    "level_id": lv.id,
                    "distance_atr": float(distance / atr),
                },
            ))
        return evidence

    @staticmethod
    def _pool_strength(level: Level, now: datetime) -> float:
        if level.kind in (LevelKind.EQH, LevelKind.EQL):
            hours = (now - level.born).total_seconds() / 3600
            recency = max(0.0, 1 - hours / 48)
            return min(level.touches / 5, 1.0) * 0.7 + recency * 0.3
        if level.kind in (LevelKind.PDH, LevelKind.PDL):
            return 0.6
        return 0.4

    @staticmethod
    def _create_once(
        ctx: StockContext, level_id: str, kind: LevelKind, zone: tuple[Decimal, Decimal],
    ) -> None:
        if any(lv.id == level_id for lv in ctx.levels):
            return
        ctx.levels.append(Level(
            id=level_id, symbol=ctx.symbol, kind=kind, zone=zone,
            born=ctx.now, tf=None, state=LevelState.ACTIVE,
        ))
