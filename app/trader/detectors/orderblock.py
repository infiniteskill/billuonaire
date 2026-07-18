"""Orderblock detector ("orderblock"): a bearish candle followed by >=
``displacement_atr * ATR`` net upward close-to-close displacement within
``lookback`` candles is a bullish order block (mirror for bearish). Creates
an OB_BULL/OB_BEAR Level whose zone is the full OB candle range (low, high),
born at the OB candle ts; mitigation is LevelEngine's job (2nd test ->
MITIGATED).

Quality = min(disp/ATR * 0.27, 0.4) + min(body/ATR * 0.3, 0.3)
          + body_pct * 0.3; hunt-born (OB candle within the first
``hunt_minutes`` of the session) adds +0.15, cap 1.0. The quality map is
instance-lifetime:
a restart re-derives it as candles rescan; OB levels loaded from LevelStore
that never rescan fall back to 0.5.

Evidence (ttl 6, strength = quality incl. hunt bonus) is emitted when the
latest closed candle's close sits inside an ACTIVE/TESTED OB zone: OB_BULL
-> LONG, OB_BEAR -> SHORT. Overlapping same-kind OBs dedupe on creation,
keeping the higher quality one."""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

from trader.detectors.base import Detector, register
from trader.engine.context import StockContext
from trader.models.candle import Candle, Timeframe
from trader.models.evidence import Direction, Evidence
from trader.models.level import Level, LevelKind, LevelState

# hunt_minutes: keep in sync with config time.observe_min (B12)
_DEFAULTS = {"tf": "5m", "displacement_atr": 1.5, "lookback": 3,
             "hunt_minutes": 105}
_LIVE = (LevelState.ACTIVE, LevelState.TESTED)
_OB_KINDS = (LevelKind.OB_BULL, LevelKind.OB_BEAR)


@register
class OrderblockDetector(Detector):
    name = "orderblock"

    def __init__(self, params: dict):
        super().__init__({**_DEFAULTS, **params})
        self._quality: dict[str, float] = {}          # level_id -> base quality
        self._emitted: set[tuple[str, datetime]] = set()  # (level_id, candle ts)

    def on_session_end(self) -> None:
        self._quality.clear()    # carried OBs fall back to 0.5 until rescanned
        self._emitted.clear()

    def detect(self, ctx: StockContext) -> list[Evidence]:
        tf = Timeframe(self.params["tf"])
        atr = ctx.atr(tf)
        lookback = int(self.params["lookback"])
        window = ctx.candles.last(lookback + 2, tf)
        if atr is None or atr <= 0 or len(window) < 2:
            return []
        need = Decimal(str(self.params["displacement_atr"])) * atr
        for i, ob in enumerate(window[:-1]):
            if ob.close == ob.open:  # doji (incl. 0-range): never an OB
                continue
            sign = 1 if ob.close < ob.open else -1  # bearish candle -> bull OB
            disp = max((c.close - ob.close) * sign
                       for c in window[i + 1:i + 1 + lookback])
            if disp < need:
                continue
            q = (min(float(disp / atr) * 0.27, 0.4)
                 + min(float(ob.body / atr) * 0.3, 0.3)
                 + float(ob.body / ob.range) * 0.3)
            kind = LevelKind.OB_BULL if sign == 1 else LevelKind.OB_BEAR
            self._upsert(ctx, ob, tf, kind, q)
        return self._evidence(ctx, window[-1])

    def _upsert(self, ctx: StockContext, ob: Candle, tf: Timeframe,
                kind: LevelKind, q: float) -> None:
        level_id = f"{ctx.symbol}-{kind.name}-{tf.value}-{ob.ts.isoformat()}"
        if any(lv.id == level_id for lv in ctx.levels):
            self._quality[level_id] = q  # lazy re-derive after restart
            return
        # ACTIVE rivals only (as ob_lux): a TESTED zone -- possibly carried
        # from a prior session -- holds real touches/history, never evicted.
        rival = next((lv for lv in ctx.levels if lv.kind is kind
                      and lv.state is LevelState.ACTIVE
                      and lv.zone[0] <= ob.high and ob.low <= lv.zone[1]), None)
        if rival is not None:  # overlap: keep the higher quality OB
            if min(q + 0.15 * self._hunt(ctx, ob.ts), 1.0) <= self._strength(ctx, rival):
                return
            ctx.levels.remove(rival)
            self._quality.pop(rival.id, None)
        self._quality[level_id] = q
        ctx.levels.append(Level(id=level_id, symbol=ctx.symbol, kind=kind,
                                zone=(ob.low, ob.high), born=ob.ts, tf=tf))

    def _evidence(self, ctx: StockContext, last: Candle) -> list[Evidence]:
        out = []
        for lv in ctx.levels:
            key = (lv.id, last.ts)
            if (lv.kind not in _OB_KINDS or lv.state not in _LIVE
                    or not lv.zone[0] <= last.close <= lv.zone[1]
                    or key in self._emitted):
                continue
            self._emitted.add(key)
            hunt = self._hunt(ctx, lv.born)
            out.append(Evidence(
                detector=self.name,
                direction=Direction.LONG if lv.kind is LevelKind.OB_BULL
                else Direction.SHORT,
                strength=self._strength(ctx, lv), zone=lv.zone, ts=ctx.now,
                ttl_candles=6,
                meta={"level_id": lv.id, "hunt_born": hunt, "event": "OB_RETEST"},
            ))
        return out

    def _hunt(self, ctx: StockContext, born: datetime) -> bool:
        """OB candle inside the first hunt_minutes of its session."""
        return born < (ctx.spec.session_open_dt(born)
                       + timedelta(minutes=int(self.params["hunt_minutes"])))

    def _strength(self, ctx: StockContext, lv: Level) -> float:
        return min(self._quality.get(lv.id, 0.5) + 0.15 * self._hunt(ctx, lv.born), 1.0)
