"""ob_lux detector ("ob_lux"): the validated LuxAlgo internal Order Block,
ported faithfully from the measured winner (scratchpad luxob.py). A swing
pivot high/low is confirmed once ``size`` trailing bars fail to exceed it; a
later close crossing back over that pivot level is a structure break. The OB
is the bar within [pivot, break] with the lowest (bull) / highest (bear)
"parsed" extreme, where a bar whose range >= ``hv_atr_mult`` * ATR has its
high/low swapped first -- LuxAlgo's volatility-as-volume proxy (the
validated rule has no real volume term to port; a range-vs-ATR spike is
untrusted as the true wick and excluded from the leg-extreme search).
Creates an OB_BULL/OB_BEAR Level whose zone is (parsed_low, parsed_high) of
that bar, born at its ts; mitigation is LevelEngine's job (as in
``orderblock``).

Quality = min(overshoot / ATR, 1.0), overshoot = how far the confirming
close broke past the pivot level. The source has no strength score of its
own (it is a boolean event detector for offline study); this is the port's
0..1 proxy for break conviction.

Evidence (ttl 6, strength = quality) is emitted when the latest closed
candle's close sits inside an ACTIVE/TESTED OB zone: OB_BULL -> LONG,
OB_BEAR -> SHORT. Overlapping same-kind OBs dedupe on creation, keeping the
higher quality one."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from trader.detectors.base import Detector, register
from trader.engine.context import StockContext
from trader.models.candle import Candle, Timeframe
from trader.models.evidence import Direction, Evidence
from trader.models.level import Level, LevelKind, LevelState

_DEFAULTS = {"tf": "5m", "size": 5, "hv_atr_mult": 2.0}
_LIVE = (LevelState.ACTIVE, LevelState.TESTED)
_OB_KINDS = (LevelKind.OB_BULL, LevelKind.OB_BEAR)


@register
class ObLuxDetector(Detector):
    name = "ob_lux"

    def __init__(self, params: dict):
        super().__init__({**_DEFAULTS, **params})
        self._quality: dict[str, float] = {}          # level_id -> quality
        self._emitted: set[tuple[str, datetime]] = set()  # (level_id, ts)

    def on_session_end(self) -> None:
        self._quality.clear()    # OB levels never carry; new day re-derives
        self._emitted.clear()

    def detect(self, ctx: StockContext) -> list[Evidence]:
        tf = Timeframe(self.params["tf"])
        atr = ctx.atr(tf)
        size = int(self.params["size"])
        window = ctx.candles.today(tf)
        n = len(window)
        if atr is None or atr <= 0 or n <= size:
            return []
        H = [c.high for c in window]; L = [c.low for c in window]; C = [c.close for c in window]
        thr = Decimal(str(self.params["hv_atr_mult"])) * atr
        pH = [L[j] if H[j] - L[j] >= thr else H[j] for j in range(n)]
        pL = [H[j] if H[j] - L[j] >= thr else L[j] for j in range(n)]
        swH = swL = None          # (level, pivot_idx) of the live pivot
        swHc = swLc = True        # confirmed flags (True = none pending)
        for i in range(n):
            if i >= size:
                p = i - size
                win_h, win_l = max(H[p + 1:i + 1]), min(L[p + 1:i + 1])
                if H[p] > win_h:
                    swH, swHc = (H[p], p), False
                if L[p] < win_l:
                    swL, swLc = (L[p], p), False
            if swH and not swHc and C[i] > swH[0] and (i == 0 or C[i - 1] <= swH[0]):
                swHc = True
                idx = min(range(swH[1], i + 1), key=lambda j: pL[j])
                lo, hi = sorted((pL[idx], pH[idx]))
                self._upsert(ctx, window[idx].ts, tf, LevelKind.OB_BULL, lo, hi,
                            min(float((C[i] - swH[0]) / atr), 1.0))
            if swL and not swLc and C[i] < swL[0] and (i == 0 or C[i - 1] >= swL[0]):
                swLc = True
                idx = max(range(swL[1], i + 1), key=lambda j: pH[j])
                lo, hi = sorted((pL[idx], pH[idx]))
                self._upsert(ctx, window[idx].ts, tf, LevelKind.OB_BEAR, lo, hi,
                            min(float((swL[0] - C[i]) / atr), 1.0))
        return self._evidence(ctx, window[-1])

    def _upsert(self, ctx: StockContext, born: datetime, tf: Timeframe,
                kind: LevelKind, lo: Decimal, hi: Decimal, q: float) -> None:
        level_id = f"{ctx.symbol}-{kind.name}-{tf.value}-{born.isoformat()}"
        if any(lv.id == level_id for lv in ctx.levels):
            self._quality[level_id] = q  # lazy re-derive after restart
            return
        rival = next((lv for lv in ctx.levels if lv.kind is kind
                      and lv.zone[0] <= hi and lo <= lv.zone[1]), None)
        if rival is not None:  # overlap: keep the higher quality OB
            if q <= self._quality.get(rival.id, 0.5):
                return
            ctx.levels.remove(rival)
            self._quality.pop(rival.id, None)
        self._quality[level_id] = q
        ctx.levels.append(Level(id=level_id, symbol=ctx.symbol, kind=kind,
                                zone=(lo, hi), born=born, tf=tf))

    def _evidence(self, ctx: StockContext, last: Candle) -> list[Evidence]:
        out = []
        for lv in ctx.levels:
            key = (lv.id, last.ts)
            if (lv.kind not in _OB_KINDS or lv.state not in _LIVE
                    or not lv.zone[0] <= last.close <= lv.zone[1]
                    or key in self._emitted):
                continue
            self._emitted.add(key)
            out.append(Evidence(
                detector=self.name,
                direction=Direction.LONG if lv.kind is LevelKind.OB_BULL
                else Direction.SHORT,
                strength=self._quality.get(lv.id, 0.5), zone=lv.zone, ts=ctx.now,
                ttl_candles=6, meta={"level_id": lv.id, "event": "OB_RETEST"},
            ))
        return out
