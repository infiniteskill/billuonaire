"""Liquidity detector ("liquidity"): creates PDH/PDL, PWH/PWL (prior
ISO-week D1 extremes, one pair per iso-week), OPEN_RANGE_H/L, ROUND
and EQH/EQL Levels on ctx.levels (side channel, like swings.py) and emits at
most 2 NEUTRAL proximity Evidence (nearest untapped ACTIVE/TESTED pool above
and below price, within proximity_atr * ATR(M5); strength = pool * 0.5).
Params: eq_tolerance, round_steps, round_within_pct, proximity_atr,
or_minutes (opening range = first or_minutes of the session).
"""

from __future__ import annotations

from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from trader.detectors.base import Detector, register
from trader.engine.context import StockContext
from trader.models.candle import Timeframe
from trader.models.evidence import Direction, Evidence
from trader.models.level import Level, LevelKind, LevelState

_ACTIVE_STATES = (LevelState.ACTIVE, LevelState.TESTED)
_PROXIMITY_KINDS = frozenset({
    LevelKind.PDH, LevelKind.PDL, LevelKind.PWH, LevelKind.PWL,
    LevelKind.EQH, LevelKind.EQL,
    LevelKind.EXT_H, LevelKind.EXT_L,
    LevelKind.OPEN_RANGE_H, LevelKind.OPEN_RANGE_L, LevelKind.ROUND,
})
_EXT = frozenset({LevelKind.EXT_H, LevelKind.EXT_L})  # lone-extreme pools: master only
_HIGH_POOLS = frozenset({LevelKind.PWH, LevelKind.PWL,
                         LevelKind.OPEN_RANGE_H, LevelKind.OPEN_RANGE_L})
_DEFAULTS = {"eq_tolerance": 0.001, "round_steps": [50, 100, 500],
             "round_within_pct": 2.0, "proximity_atr": 1.0, "or_minutes": 15,
             "emit_only": None}   # e.g. ["EQH","EQL","EXT_H","EXT_L"] to surface only taught pools


def _mid(zone: tuple[Decimal, Decimal]) -> Decimal:
    return (zone[0] + zone[1]) / 2


def _overlaps(a: tuple, b: tuple) -> bool:
    return a[0] <= b[1] and b[0] <= a[1]


@register
class LiquidityDetector(Detector):
    name = "liquidity"

    def __init__(self, params: dict):
        super().__init__({**_DEFAULTS, **params})

    def detect(self, ctx: StockContext) -> list[Evidence]:
        self._create_pdh_pdl(ctx)
        self._create_pwh_pwl(ctx)
        self._create_open_range(ctx)
        self._create_round(ctx)
        self._create_eq(ctx, LevelKind.SWING_H, LevelKind.EQH)
        self._create_eq(ctx, LevelKind.SWING_L, LevelKind.EQL)
        self._create_eq(ctx, LevelKind.EXT_H, LevelKind.EQH)  # EQ pools from taught
        self._create_eq(ctx, LevelKind.EXT_L, LevelKind.EQL)  # extremes, not just fractal
        return self._proximity_evidence(ctx)

    # ---- PDH/PDL + opening range (high/low pairs) ------------------------

    def _create_pdh_pdl(self, ctx: StockContext) -> None:
        prev = ctx.candles.prev_day(Timeframe.M1)
        if prev:
            self._hl_pair(ctx, prev, ("PDH", LevelKind.PDH), ("PDL", LevelKind.PDL))

    def _create_pwh_pwl(self, ctx: StockContext) -> None:
        """Latest ISO week before the session's week: max D1 high / min D1
        low. Skipped with no prior-week D1 candle; id per (symbol, iso-week)
        so the pair persists all week."""
        y, w = ctx.day.session_date.isocalendar()[:2]
        days = [c for c in ctx.candles.last(15, Timeframe.D1)
                if c.ts.isocalendar()[:2] < (y, w)]
        if not days:
            return
        wk = max(c.ts.isocalendar()[:2] for c in days)
        week = [c for c in days if c.ts.isocalendar()[:2] == wk]
        T = ctx.spec.tick_size
        for tag, kind, p in (("PWH", LevelKind.PWH, max(c.high for c in week)),
                             ("PWL", LevelKind.PWL, min(c.low for c in week))):
            self._create_once(ctx, f"{ctx.symbol}-{tag}-{y}-W{w:02d}",
                              kind, (p - T, p + T))

    def _create_open_range(self, ctx: StockContext) -> None:
        """Opening range = first or_minutes of the session."""
        n = int(self.params["or_minutes"])
        today = ctx.candles.today(Timeframe.M1)
        if len(today) >= n:
            self._hl_pair(ctx, today[:n], ("ORH", LevelKind.OPEN_RANGE_H),
                          ("ORL", LevelKind.OPEN_RANGE_L))

    def _hl_pair(self, ctx: StockContext, window, hi, lo) -> None:
        """One (tag, kind) level at the window high, one at the window low."""
        d, T = ctx.day.session_date, ctx.spec.tick_size
        for (tag, kind), p in ((hi, max(c.high for c in window)),
                               (lo, min(c.low for c in window))):
            self._create_once(ctx, f"{ctx.symbol}-{tag}-{d}", kind, (p - T, p + T))

    # ---- Round numbers -------------------------------------------------

    def _create_round(self, ctx: StockContext) -> None:
        last = ctx.candles.last(1, Timeframe.M1)
        if not last:
            return
        close = last[-1].close
        if close <= 0:
            return
        within_pct = Decimal(str(self.params["round_within_pct"]))
        steps = self.params["round_steps"]
        for step in steps:
            step_d = Decimal(str(step))
            nearest = (close / step_d).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * step_d
            if nearest <= 0:
                continue
            pct = abs(nearest - close) / close * 100
            if pct > within_pct:
                continue
            nearest, T = ctx.spec.quantize(nearest), ctx.spec.tick_size
            level_id = f"{ctx.symbol}-ROUND-{step}-{nearest}"
            self._create_once(
                ctx, level_id, LevelKind.ROUND, (nearest - T, nearest + T),
            )

    # ---- Equal highs/lows -----------------------------------------------

    def _create_eq(
        self, ctx: StockContext, source: LevelKind, target: LevelKind,
    ) -> None:
        tolerance = Decimal(str(self.params["eq_tolerance"]))
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
                # zone-mid disambiguates two distinct groups whose max-born
                # timestamp collides (e.g. formed from the same closing candle).
                id=f"{ctx.symbol}-{target.name}-{born.isoformat()}-{_mid(zone)}",
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
        proximity_atr = Decimal(str(self.params["proximity_atr"]))
        max_distance = proximity_atr * atr

        emit_only = self.params.get("emit_only")   # None = all cataloged pools
        pools = [
            lv for lv in ctx.levels
            if lv.kind in _PROXIMITY_KINDS and lv.state in _ACTIVE_STATES
            and (emit_only is None or lv.kind.name in emit_only)  # surface only taught pools
            and (lv.kind not in _EXT or lv.meta.get("master"))  # lone EXT: master only
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
                    "event": "POOL_NEAR",
                },
            ))
        return evidence

    @staticmethod
    def _pool_strength(level: Level, now: datetime) -> float:
        if level.kind in (LevelKind.EQH, LevelKind.EQL):
            hours = (now - level.born).total_seconds() / 3600
            recency = max(0.0, 1 - hours / 48)
            return min(level.touches / 5, 1.0) * 0.7 + recency * 0.3
        if level.kind in _HIGH_POOLS:  # axiom 5: OR + weekly = HIGH liquidity
            return 0.7
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
