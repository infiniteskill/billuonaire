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

``detect()`` runs exactly once per closed M5 candle (SymbolPipeline bar-scopes
it), so formation does NOT rescan history: each tick evaluates only the one
newly-eligible block candidate -- the candle whose ``lookback``-bar
displacement window just closed, i.e. ``window[-(lookback + 1)]`` on a
session-scoped ``ctx.candles.today(tf)[-(lookback + 2):]`` window (never
crosses into the prior session) -- against the *current*
``ctx.atr(tf)`` as its formation ATR, then persists it (once) in instance
state. A candle that fails its displacement check at that single tick is
rejected forever; it is never retried against a later (e.g. post-spike,
lower) ATR reading, which would otherwise stamp an old candle's already-fixed
displacement with a fresh, misleadingly-current touch. Touch is checked
separately, every tick, against ONLY the newest closed candle vs. all
persisted blocks' body zones -- so a touch is always live, never stale.

Pure signal-emitter (no Level, per brief -- no new LevelKind).

strength = linear 0..1 ramp of how far disp exceeds the ``disp_atr``
threshold: 0 at disp==need, capped at 1.0 by disp==2*need (the source has no
strength score of its own; this is the port's proxy for displacement
conviction). Degenerate case: disp_atr == 0 -> need == 0 -> strength == 1.0
(no ramp denominator, treated as maximally-conviction)."""

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
        window = ctx.candles.today(tf)[-(lookback + 2):]
        touches = self._touch(ctx, window)  # against blocks formed on PRIOR ticks
        atr = ctx.atr(tf)
        if atr and atr > 0 and len(window) >= lookback + 2:
            need = Decimal(str(self.params["disp_atr"])) * atr
            self._form(window, lookback, need)
        return touches

    def _form(self, window: list[Candle], lookback: int, need: Decimal) -> None:
        blk = window[-(lookback + 1)]
        if blk.ts in self._seen:
            return
        seg = window[-lookback:]
        for sign in (1, -1):  # 1: down-candle before up-move (LONG)
            opp = (blk.close < blk.open) if sign == 1 else (blk.close > blk.open)
            if not opp:
                continue
            if any((c.close < c.open) if sign == 1 else (c.close > c.open) for c in seg):
                continue
            disp = max((c.close - blk.close) * sign for c in seg)
            if disp < need:
                continue
            self._seen.add(blk.ts)
            lo, hi = min(blk.open, blk.close), max(blk.open, blk.close)
            extreme = blk.low if sign == 1 else blk.high
            strength = min(max(float((disp - need) / need), 0.0), 1.0) if need > 0 else 1.0
            self._blocks[blk.ts] = (sign, lo, hi, extreme, strength)

    def _touch(self, ctx: StockContext, window: list[Candle]) -> list[Evidence]:
        if not window:
            return []
        touch = window[-1]
        out = []
        for ts, (sign, lo, hi, extreme, strength) in list(self._blocks.items()):
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
        return out
