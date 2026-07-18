"""FVG detector ("fvg"). Creation: over the last 3 closed tf candles, a
bullish FVG is c3.low > c1.high with gap >= min_gap_atr * ATR -> FVG_BULL
Level, zone (c1.high, c3.low), born c2.ts (bearish mirror: (c3.high,
c1.low)); idempotent by id. Evidence (all ttl 12):
- CE_HOLD 0.7: close inside a live gap holding the CE (zone mid) on the gap
  side -> gap direction; once per touch episode (reset on a close outside).
- Full fill: close beyond the far edge -> record_state DEAD unless already
  DEAD (or INVERTED, which lives beyond the far edge). No evidence after.
- IFVG 0.75: INVERTED gap retested breaker-style (candle overlaps zone,
  close on the new side) -> direction away from the zone (flip of original
  side); deduped per inversion episode like breaker.
- BPR 0.8: close inside the overlap of live FVG_BULL x FVG_BEAR zones ->
  direction of the newer (later-born) gap; once per pair."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from trader.detectors.base import Detector, register
from trader.engine.context import StockContext
from trader.models.candle import Candle, Timeframe
from trader.models.evidence import Direction, Evidence
from trader.models.level import Level, LevelKind, LevelState

_DEFAULTS = {"tf": "5m", "min_gap_atr": 0.3}
_LIVE = (LevelState.ACTIVE, LevelState.TESTED)
_FVG_KINDS = (LevelKind.FVG_BULL, LevelKind.FVG_BEAR)


@register
class FvgDetector(Detector):
    name = "fvg"

    def __init__(self, params: dict):
        super().__init__({**_DEFAULTS, **params})
        self._episode: dict[str, datetime] = {}            # level_id -> entry ts
        self._ce_fired: set[tuple[str, datetime]] = set()  # (level_id, entry ts)
        self._ifvg_seen: set[tuple[str, datetime]] = set()  # (level_id, inv ts)
        self._bpr_fired: set[tuple[str, str]] = set()      # (bull_id, bear_id)

    def on_session_end(self) -> None:
        for m in (self._episode, self._ce_fired, self._ifvg_seen, self._bpr_fired):
            m.clear()   # episodes are per-session; carried zones re-fire fresh

    def detect(self, ctx: StockContext) -> list[Evidence]:
        tf = Timeframe(self.params["tf"])
        window = ctx.candles.last(3, tf)
        if not window:
            return []
        atr = ctx.atr(tf)
        if len(window) == 3 and atr is not None and atr > 0:
            self._create(ctx, tf, window, atr)
        last = window[-1]
        out: list[Evidence] = []
        for lv in ctx.levels:
            if lv.kind not in _FVG_KINDS:
                continue
            bull = lv.kind is LevelKind.FVG_BULL
            filled = last.close < lv.zone[0] if bull else last.close > lv.zone[1]
            if filled and lv.state not in (LevelState.DEAD, LevelState.INVERTED):
                lv.record_state(last.ts, LevelState.DEAD)
            if lv.state is LevelState.INVERTED:
                out += self._ifvg(ctx, lv, last, bull)
            elif lv.state in _LIVE:
                out += self._ce_hold(ctx, lv, last, bull)
            else:
                self._episode.pop(lv.id, None)
        return out + self._bpr(ctx, last)

    def _create(self, ctx: StockContext, tf: Timeframe,
                window: list[Candle], atr: Decimal) -> None:
        c1, c2, c3 = window
        need = Decimal(str(self.params["min_gap_atr"])) * atr
        for kind, zone in ((LevelKind.FVG_BULL, (c1.high, c3.low)),
                           (LevelKind.FVG_BEAR, (c3.high, c1.low))):
            gap = zone[1] - zone[0]
            if gap <= 0 or gap < need:
                continue
            level_id = f"{ctx.symbol}-{kind.name}-{tf.value}-{c2.ts.isoformat()}"
            if all(lv.id != level_id for lv in ctx.levels):
                ctx.levels.append(Level(id=level_id, symbol=ctx.symbol,
                                        kind=kind, zone=zone, born=c2.ts, tf=tf))

    def _ce_hold(self, ctx: StockContext, lv: Level, last: Candle,
                 bull: bool) -> list[Evidence]:
        lo, hi = lv.zone
        if not lo <= last.close <= hi:  # left the zone: episode over
            self._episode.pop(lv.id, None)
            return []
        entry = self._episode.setdefault(lv.id, last.ts)
        ce = (lo + hi) / 2
        holds = last.close >= ce if bull else last.close <= ce
        if not holds or (lv.id, entry) in self._ce_fired:
            return []
        self._ce_fired.add((lv.id, entry))
        return [Evidence(detector=self.name,
                         direction=Direction.LONG if bull else Direction.SHORT,
                         strength=0.7, zone=lv.zone, ts=ctx.now, ttl_candles=12,
                         meta={"level_id": lv.id, "event": "CE_HOLD"})]

    def _ifvg(self, ctx: StockContext, lv: Level, last: Candle,
              bull: bool) -> list[Evidence]:
        inv_ts = next((ts for ts, st in reversed(lv.state_history)
                       if st is LevelState.INVERTED), None)
        if inv_ts is None or (lv.id, inv_ts) in self._ifvg_seen:
            return []
        lo, hi = lv.zone
        on_new_side = last.close < lo if bull else last.close > hi
        if not (last.low <= hi and last.high >= lo and on_new_side):
            return []
        self._ifvg_seen.add((lv.id, inv_ts))
        return [Evidence(detector=self.name,
                         direction=Direction.SHORT if bull else Direction.LONG,
                         strength=0.75, zone=lv.zone, ts=ctx.now, ttl_candles=12,
                         meta={"level_id": lv.id, "event": "IFVG"})]

    def _bpr(self, ctx: StockContext, last: Candle) -> list[Evidence]:
        live = [lv for lv in ctx.levels
                if lv.kind in _FVG_KINDS and lv.state in _LIVE]
        out = []
        for b in (lv for lv in live if lv.kind is LevelKind.FVG_BULL):
            for r in (lv for lv in live if lv.kind is LevelKind.FVG_BEAR):
                lo = max(b.zone[0], r.zone[0])
                hi = min(b.zone[1], r.zone[1])
                if ((b.id, r.id) in self._bpr_fired or lo > hi
                        or not lo <= last.close <= hi):
                    continue
                self._bpr_fired.add((b.id, r.id))
                newer = max(b, r, key=lambda lv: lv.born)
                out.append(Evidence(
                    detector=self.name,
                    direction=Direction.LONG if newer.kind is LevelKind.FVG_BULL
                    else Direction.SHORT,
                    strength=0.8, zone=(lo, hi), ts=ctx.now, ttl_candles=12,
                    meta={"event": "BPR", "bull_id": b.id, "bear_id": r.id}))
        return out
