"""Propulsion-block detector ("propulsion_block"): the ICT Propulsion Block.
A live OB_BULL/OB_BEAR Level (states ACTIVE/TESTED) is wick-TAPPED by a later
candle that RESPECTS it -- bull: the candle's low trades inside the OB zone
while its body (min(O,C)) stays at/above the zone top (a low punched below
the zone, or a body closing inside it, is a violation, not a tap; bear
mirror: high inside the zone from below, max(O,C) at/below the zone bottom).
Within ``propel_bars`` following candles price must PROPEL away: some close
displaced >= ``propel_atr`` * ATR from the tap close in the OB direction.
The tapping candle IS the propulsion block; its full range (low, high) is the
refined zone. SIGNAL: the first later close back inside that zone -> Evidence
in the parent OB direction (OB_BULL -> LONG, OB_BEAR -> SHORT), ttl 4,
strength = min(disp/ATR, 1.0) * 0.8, meta = {"event": "PROPULSION",
"sl": zone far edge (raw structural extreme, tap low for LONG / high for
SHORT), "sl_floor": 0.15*ATR} -- stringified Decimals; the executor applies
the floor, this detector never floors "sl" itself (as compression_fade).

WRITER ORDER: consumes OB_BULL/OB_BEAR Levels from ``ctx.levels`` written by
the ``orderblock``/``ob_lux`` detectors -- those must precede this one in
``settings.detectors.enabled`` (run_all executes in config order), as
structure/sweep require their level writers.

Bounded single-eval (mitigation.py's post-fix architecture, avoiding its
stale-touch class of bug): each tick judges ONLY the newly-closed candle --
as a fresh tap of a live OB (ATR and need = propel_atr * ATR are captured at
that one tick and never re-thresholded against later ATR readings), as the
propelling close for taps still inside the ``ctx.candles.last(propel_bars +
1, tf)`` window (a tap aged past it is dropped forever), and as the
return-touch against blocks confirmed on PRIOR ticks only -- so a touch is
always live, never stale, and a block can never fire on its own confirm bar.

CONTINUUM: the window is continuous multi-day history, never session-scoped.
``on_session_end`` prunes only the pending-tap dedupe memory by age (a tap
older than propel_bars bars can never confirm -- provably safe); confirmed
blocks are keyed by (tap ts, sign) with NO linkage to their parent OB
Levels -- they persist across the boundary untouched until a return-touch
consumes them (``_blocks`` itself is never pruned).

Emission hygiene (``_collapse``): two different confirmed blocks can contain
the SAME touch close in one tick -- one physical price event fires once;
same-direction clashes collapse to the single strongest Evidence."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from trader.detectors.base import Detector, register
from trader.engine.context import StockContext
from trader.models.candle import Candle, Timeframe
from trader.models.evidence import Direction, Evidence
from trader.models.level import LevelKind, LevelState

_DEFAULTS = {"tf": "5m", "propel_bars": 3, "propel_atr": 1.0, "sl_atr_floor": 0.15}
_LIVE = (LevelState.ACTIVE, LevelState.TESTED)
_SIGN = {LevelKind.OB_BULL: 1, LevelKind.OB_BEAR: -1}


def _collapse(evs: list[Evidence], tick: Decimal) -> list[Evidence]:
    """Per-tick emission hygiene: two different confirmed blocks can both
    contain the SAME touch close (overlapping zones, or sl within one tick)
    -- one physical price event, not two signals. Collapse same-direction
    clashes to the single strongest (max strength; tie -> tightest zone)."""
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
class PropulsionBlockDetector(Detector):
    name = "propulsion_block"

    def __init__(self, params: dict):
        super().__init__({**_DEFAULTS, **params})
        self._pending: dict[tuple[datetime, int], tuple] = {}  # (tap ts, sign) -> (lo, hi, close, need, atr)
        self._blocks: dict[tuple[datetime, int], tuple] = {}   # (tap ts, sign) -> (lo, hi, strength)

    def on_session_end(self) -> None:
        # Continuum: _blocks is kept as-is -- confirmed blocks carry no
        # parent-OB linkage; only a return-touch consumes them. Prune only
        # pending taps by age: older than propel_bars bars can never
        # confirm (window membership), so dropping them is provably safe.
        self._pending = dict(sorted(self._pending.items())[-int(self.params["propel_bars"]):])

    def detect(self, ctx: StockContext) -> list[Evidence]:
        tf = Timeframe(self.params["tf"])
        window = ctx.candles.last(int(self.params["propel_bars"]) + 1, tf)
        if not window:
            return []
        j = window[-1]
        atr = ctx.atr(tf)
        floor = Decimal(str(self.params["sl_atr_floor"])) * atr if atr else Decimal(0)
        touches = self._touch(ctx, j, floor)  # blocks confirmed on PRIOR ticks only
        self._confirm(j, window)
        if atr:
            self._tap(ctx, j, atr)
        return _collapse(touches, ctx.spec.tick_size)

    def _tap(self, ctx: StockContext, j: Candle, atr: Decimal) -> None:
        need = Decimal(str(self.params["propel_atr"])) * atr
        for lv in ctx.levels:
            sign = _SIGN.get(lv.kind)
            if sign is None or lv.state not in _LIVE or j.ts <= lv.born:
                continue
            lo, hi = lv.zone
            wick, body, edge = ((j.low, min(j.open, j.close), hi) if sign == 1
                                else (j.high, max(j.open, j.close), lo))
            if lo <= wick <= hi and (body - edge) * sign >= 0:  # respect, not violation
                self._pending[(j.ts, sign)] = (j.low, j.high, j.close, need, atr)

    def _confirm(self, j: Candle, window: list[Candle]) -> None:
        live = {c.ts for c in window[:-1]}
        for key, (lo, hi, close, need, atr) in list(self._pending.items()):
            if key[0] < window[0].ts:      # aged out of the propel window
                del self._pending[key]
            elif key[0] in live:           # never against the tap's own bar
                disp = (j.close - close) * key[1]
                if disp >= need:
                    del self._pending[key]
                    self._blocks[key] = (lo, hi, min(float(disp / atr), 1.0) * 0.8)

    def _touch(self, ctx: StockContext, j: Candle, floor: Decimal) -> list[Evidence]:
        out = []
        for (ts, sign), (lo, hi, strength) in list(self._blocks.items()):
            if not lo <= j.close <= hi:
                continue
            del self._blocks[(ts, sign)]
            out.append(Evidence(
                detector=self.name,
                direction=Direction.LONG if sign == 1 else Direction.SHORT,
                strength=strength, zone=(lo, hi), ts=ctx.now, ttl_candles=4,
                meta={"event": "PROPULSION", "sl": str(lo if sign == 1 else hi),
                      "sl_floor": str(floor)}))
        return out
