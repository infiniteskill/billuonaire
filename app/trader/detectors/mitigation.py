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
``ctx.candles.last(lookback + 2, tf)`` window -- CONTINUOUS multi-day
history, never session-scoped: that is how the edge was VALIDATED
(ict_pieces.py ran one concatenated series), so a block/leg may span the
overnight gap and pending-touch blocks carry across sessions -- against the
block candle's OWN-bar ATR, matching ict_pieces.py's ``atrs[i]`` exactly (NOT
the later, current-tick ATR, which would let a volatility spike or lull
between the block and its formation tick silently move the goalposts). That
ATR is recomputed on demand from a wider ``ctx.candles.last(lookback + 15,
tf)`` fetch -- the same 15-candle-trailing-SMA formula as ``StockContext.atr``,
just anchored ``lookback`` bars earlier -- so formation is a pure function of
``ctx.candles`` at call time, not of how many prior ticks were observed (a
detector that skipped ticks, e.g. in a test replaying only some bars, must see
the identical outcome as one that saw every tick). Persisted (once) in
instance state. A candle that fails its displacement check at that single
tick is rejected forever; it is never retried against a later (e.g.
post-spike, lower) ATR reading, which would otherwise stamp an old candle's
already-fixed displacement with a fresh, misleadingly-current touch. Touch is
checked separately, every tick, against ONLY the newest closed candle vs. all
persisted blocks' body zones -- so a touch is always live, never stale.

Pure signal-emitter (no Level, per brief -- no new LevelKind).

strength = linear 0..1 ramp of how far disp exceeds the ``disp_atr``
threshold: 0 at disp==need, capped at 1.0 by disp==2*need (the source has no
strength score of its own; this is the port's proxy for displacement
conviction). Degenerate case: disp_atr == 0 -> need == 0 -> strength == 1.0
(no ramp denominator, treated as maximally-conviction).

Emission hygiene (``_collapse``): two different pending blocks can mitigate
off the SAME touch candle in one tick (overlapping/adjacent body zones) --
one physical price event should fire once, so same-direction clashes within
a single ``detect()`` call collapse to the single strongest Evidence."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from trader.detectors.base import Detector, register
from trader.engine.context import StockContext
from trader.models.candle import Candle, Timeframe
from trader.models.evidence import Direction, Evidence

_DEFAULTS = {"tf": "5m", "disp_atr": 1.0, "lookback": 3, "sl_atr_floor": 0.15}
_PERIOD = 14


def _atr_of(candles: list[Candle], period: int = _PERIOD) -> Decimal | None:
    """SMA(period) of true range over ``candles`` -- identical formula to
    ``StockContext.atr``, but callable on an arbitrary (already-sliced) run of
    candles so callers can ask for the ATR as of an EARLIER bar's close, not
    just the current tick's."""
    if len(candles) < period + 1:
        return None
    trs = [max(c.high - c.low, abs(c.high - p.close), abs(c.low - p.close))
           for p, c in zip(candles, candles[1:])]
    return sum(trs) / Decimal(period)


def _collapse(evs: list[Evidence], tick: Decimal) -> list[Evidence]:
    """Per-tick emission hygiene: two different pending blocks can both be
    mitigated by the SAME touch candle (overlapping/adjacent body zones, or
    sl within one tick) -- one physical price event, not two signals.
    Collapse same-direction clashes to the single strongest (max strength;
    tie -> tightest zone)."""
    kept: list[Evidence] = []
    for e in evs:
        j = next((k for k, o in enumerate(kept) if o.direction is e.direction and
                  (o.zone[0] <= e.zone[1] and e.zone[0] <= o.zone[1] or
                   abs(Decimal(o.meta["sl"]) - Decimal(e.meta["sl"])) <= tick)), None)
        if j is None:
            kept.append(e)
        elif (e.strength, e.zone[0] - e.zone[1]) > (kept[j].strength, kept[j].zone[0] - kept[j].zone[1]):
            kept[j] = e
    return kept


@register
class MitigationDetector(Detector):
    name = "mitigation"

    def __init__(self, params: dict):
        super().__init__({**_DEFAULTS, **params})
        self._seen: set[datetime] = set()          # block ts ever formed
        self._blocks: dict[datetime, tuple] = {}   # block ts -> pending-touch data

    def on_session_end(self) -> None:
        # Continuum: pending-touch blocks are structure and carry across
        # days. Prune only _seen by age -- a ts already deeper than the
        # candidate slot can never be re-evaluated, so dropping it is safe.
        self._seen = set(sorted(self._seen)[-(int(self.params["lookback"]) + 2):])

    def detect(self, ctx: StockContext) -> list[Evidence]:
        tf = Timeframe(self.params["tf"])
        lookback = int(self.params["lookback"])
        window = ctx.candles.last(lookback + 2, tf)
        atr = ctx.atr(tf)
        floor = Decimal(str(self.params["sl_atr_floor"])) * atr if atr else Decimal(0)
        touches = self._touch(ctx, window, floor)  # against blocks formed on PRIOR ticks
        if len(window) >= lookback + 2 and window[-(lookback + 1)].ts not in self._seen:
            hist = ctx.candles.last(lookback + _PERIOD + 1, tf)
            self._form(window, hist, lookback)
        return _collapse(touches, ctx.spec.tick_size)

    def _form(self, window: list[Candle], hist: list[Candle], lookback: int) -> None:
        blk = window[-(lookback + 1)]
        need_len = lookback + _PERIOD + 1
        # the (period+1)-candle run ending at blk's own close, not the current
        # tick's -- ict_pieces' atrs[i], never a later (or earlier) bar's ATR
        a = _atr_of(hist[:_PERIOD + 1]) if len(hist) == need_len else None
        if not a or a <= 0:
            return
        need = Decimal(str(self.params["disp_atr"])) * a
        seg = window[-lookback:]
        for sign in (1, -1):  # 1: down-candle before up-move (LONG)
            opp = (blk.close < blk.open) if sign == 1 else (blk.close > blk.open)
            if not opp:
                continue
            if any((c.close < c.open) if sign == 1 else (c.close > c.open) for c in seg):
                continue
            disp = max((c.close - blk.close) * sign for c in seg)
            # float, not Decimal, and each close independently rounded to
            # float BEFORE subtracting: ict_pieces.py::mitigation_block
            # precomputes C = [float(c.close) for c in m5] once, then diffs
            # those floats -- not the same value as float()-casting the
            # Decimal-exact disp above (double rounding), so a boundary tie
            # can disagree unless replicated bit-for-bit (parity-gated in
            # test_mitigation.py, same fix as compression_fade's _is_compress).
            disp_f = max((float(c.close) - float(blk.close)) * sign for c in seg)
            if disp_f < float(self.params["disp_atr"]) * float(a):
                continue
            self._seen.add(blk.ts)
            lo, hi = min(blk.open, blk.close), max(blk.open, blk.close)
            extreme = blk.low if sign == 1 else blk.high
            strength = min(max(float((disp - need) / need), 0.0), 1.0) if need > 0 else 1.0
            self._blocks[blk.ts] = (sign, lo, hi, extreme, strength)

    def _touch(self, ctx: StockContext, window: list[Candle],
               floor: Decimal) -> list[Evidence]:
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
                meta={"event": "MITIGATION", "sl": str(sl), "sl_floor": str(floor)},
            ))
        return out
