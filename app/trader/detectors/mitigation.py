"""Mitigation-block detector ("mitigation"): faithful port of
ict_pieces.py::mitigation_block. The last opposite-color candle immediately
before a displacement leg -- with no intervening opposite candle across the
``lookback`` window -- whose net displacement >= ``disp_atr`` * ATR marks a
BODY-only zone (min(O,C), max(O,C)); this differs from ``orderblock``'s
full-range zone. Direction = displacement direction (down-candle -> up-move
= LONG; up-candle -> down-move = SHORT). The first closed candle *after* the
lookback window whose range overlaps the zone is the return-touch: entry,
sl = min(low[block], low[touch]) for LONG / max(high[block], high[touch])
for SHORT.

Pure signal-emitter (no Level, per brief -- no new LevelKind). ATR is read
live via ``ctx.atr(tf)`` at block-formation time -- the source's per-bar
``atrs[i]`` series has no streaming equivalent here, the same adaptation
``orderblock``/``ob_lux`` make.

strength = linear 0..1 ramp of how far disp exceeds the ``disp_atr``
threshold: 0 at disp==need, capped at 1.0 by disp==2*need (the source has no
strength score of its own; this is the port's proxy for displacement
conviction)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from trader.detectors.base import Detector, register
from trader.engine.context import StockContext
from trader.models.candle import Candle, Timeframe
from trader.models.evidence import Direction, Evidence

_DEFAULTS = {"tf": "5m", "disp_atr": 1.0, "lookback": 3}


@register
class MitigationDetector(Detector):
    name = "mitigation"

    def __init__(self, params: dict):
        super().__init__({**_DEFAULTS, **params})
        self._seen: set[datetime] = set()          # block ts ever formed
        self._blocks: dict[datetime, tuple] = {}   # block ts -> pending-touch data

    def on_session_end(self) -> None:
        self._seen.clear()
        self._blocks.clear()

    def detect(self, ctx: StockContext) -> list[Evidence]:
        tf = Timeframe(self.params["tf"])
        lookback = int(self.params["lookback"])
        window = ctx.candles.today(tf)
        atr = ctx.atr(tf)
        if atr and atr > 0:
            need = Decimal(str(self.params["disp_atr"])) * atr
            self._form(window, lookback, need)
        return self._touch(ctx, window)

    def _form(self, window: list[Candle], lookback: int, need: Decimal) -> None:
        n = len(window)
        for sign in (1, -1):  # 1: down-candle before up-move (LONG)
            for i in range(1, n - lookback):
                blk = window[i]
                if blk.ts in self._seen:
                    continue
                opp = (blk.close < blk.open) if sign == 1 else (blk.close > blk.open)
                if not opp:
                    continue
                seg = window[i + 1:i + 1 + lookback]
                if any((c.close < c.open) if sign == 1 else (c.close > c.open) for c in seg):
                    continue
                disp = max((c.close - blk.close) * sign for c in seg)
                if disp < need:
                    continue
                self._seen.add(blk.ts)
                lo, hi = min(blk.open, blk.close), max(blk.open, blk.close)
                extreme = blk.low if sign == 1 else blk.high
                strength = min(max(float((disp - need) / need), 0.0), 1.0) if need > 0 else 1.0
                self._blocks[blk.ts] = (sign, lo, hi, extreme, i + 1 + lookback, strength)

    def _touch(self, ctx: StockContext, window: list[Candle]) -> list[Evidence]:
        out = []
        for ts, (sign, lo, hi, extreme, start, strength) in list(self._blocks.items()):
            for touch in window[start:]:
                if touch.low > hi or touch.high < lo:
                    continue
                sl = min(extreme, touch.low) if sign == 1 else max(extreme, touch.high)
                del self._blocks[ts]
                out.append(Evidence(
                    detector=self.name,
                    direction=Direction.LONG if sign == 1 else Direction.SHORT,
                    strength=strength, zone=(lo, hi), ts=ctx.now, ttl_candles=6,
                    meta={"event": "MITIGATION", "sl": sl},
                ))
                break
        return out
