"""Breaker-block detector ("breaker_msb"): faithful STATEFUL port of the
EmreKb "MSB-OB" Pine breaker branch (dev/h2h/2.txt) exactly as measured by
scratchpad pine_det.py::emrekb_events, tag "brk_bb" -- the Pine re-audit's
strongest ingredient (+19.6pp 5m hit-edge). The shipped ``breaker`` detector
is a DIFFERENT rule (-7%) and stays untouched for A/B.

Rule (the measured behavior IS the spec): Zigzag(zz) alternating swings --
with trend up, a bar whose low is the min of the last ``zz`` lows flips it
down and confirms the swing HIGH at the first argmax since the previous
flip (mirrored for lows). A bearish MSB fires when market==1 and
l0 < l1 - |h0 - l1| * fib (bullish mirrored: h0 > h1 + |h1 - l0| * fib),
gated to bar index >= max(warm, 14) (pine_det's WARM + ATR-finite ``ok``)
and to BOTH last extremes having changed since the previous MSB. The
BREAKER box exists only when the older swing was SWEPT (bear: h0 > h1;
bull: l0 < l1 -- otherwise the Pine draws a mitigation block, a different,
weaker ingredient this detector deliberately does NOT emit): full range of
the last same-direction candle (bear: down) in [older-high-bar - zz,
older-low-bar] (bull mirrored). Entry = first LATER close back inside the
box (bear: bot < C <= top; bull: bot <= C < top), once per box (per-box
dedupe); the box dies on a close beyond its far edge -- checked BEFORE
entry, so a box can die the very bar it is born.

Incremental exactly like inducement.py: cursor ``self._n`` over the full
continuum closed-candle history, bit-for-bit the reference's single batch
pass, one new bar per step. The reference's per-flip argmax/argmin rescan is
replaced by running since-flip extremes (strict compare keeps numpy's
first-occurrence tie-break) -- bounded per-tick work. The fib confirmation
runs on FLOATS with the reference's operation order: pine_det is float64
end-to-end and a Decimal 0.33 product can flip a boundary tie (the same
double-rounding trap test_mitigation.py pins). Every other comparison is a
raw price ordering, identical in Decimal.

Pure signal-emitter (no Level). sl = the box's far edge (the level whose
close-through kills the box); sl_floor = sl_atr_floor * current ATR.

``on_session_end`` prunes ONLY fired boxes (per-box dedupe memory -- a fired
box can never signal again, so dropping it is behavior-free); live boxes and
the zigzag/market state are market structure and carry across sessions (the
continuum the edge was measured on). ``_collapse``: two live boxes can catch
the SAME close in one tick -- one physical price event, so same-direction
clashes keep the single strongest (constant strength -> tightest zone)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from trader.detectors.base import Detector, register
from trader.engine.context import StockContext
from trader.models.candle import Candle, Timeframe
from trader.models.evidence import Direction, Evidence

_DEFAULTS = {"tf": "5m", "zz": 9, "fib": 0.33, "warm": 25, "sl_atr_floor": 0.15}
_STRENGTH = 0.8  # fixed: the Pine source carries no per-signal quality gradient
_PERIOD = 14     # pine_det's ok[] = ATR(14)-finite <=> bar index >= 14
_ALL = 10 ** 9


@dataclass
class _Box:
    top: Decimal
    bot: Decimal
    d: int          # +1 LONG / -1 SHORT
    born: int       # creation bar index; entry requires a LATER bar
    fired: bool = False


def _collapse(evs: list[Evidence], tick: Decimal) -> list[Evidence]:
    """Per-tick emission hygiene (same rule as mitigation/bpr): collapse
    same-direction clashes (zone overlap or sl within one tick) to the
    single strongest -- constant strength, so the tightest zone wins."""
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
class BreakerMsbDetector(Detector):
    name = "breaker_msb"

    def __init__(self, params: dict):
        super().__init__({**_DEFAULTS, **params})
        self._zz = int(self.params["zz"])
        self._fib = float(self.params["fib"])
        self._warm = max(int(self.params["warm"]), _PERIOD)
        self._n = 0                    # closed bars already consumed
        self._trend = 1
        self._hi = self._lo = None     # running since-flip (bar, price) extremes
        self._highs: list[tuple] = []  # last two swing (bar, price); [-1] newest
        self._lows: list[tuple] = []
        self._market = 1
        self._l0 = self._h0 = None     # extremes at the previous MSB
        self._boxes: list[_Box] = []

    def on_session_end(self) -> None:
        # Dedupe only: a fired box can never signal again. Live boxes and the
        # zigzag/market state are structure and carry across sessions.
        self._boxes = [b for b in self._boxes if not b.fired]

    def _flip(self, i: int, closed: list[Candle]) -> None:
        """One zigzag bar: extend the since-flip extremes (strict compare =
        first-occurrence argmax/argmin), test the zz-window flip condition,
        confirm the swing and reseed both extremes at the flip bar."""
        c = closed[i]
        if self._hi is None or c.high > self._hi[1]:
            self._hi = (i, c.high)
        if self._lo is None or c.low < self._lo[1]:
            self._lo = (i, c.low)
        w = closed[max(0, i - self._zz + 1):i + 1]
        if self._trend == 1 and c.low <= min(x.low for x in w):
            self._highs = (self._highs + [self._hi])[-2:]
        elif self._trend == -1 and c.high >= max(x.high for x in w):
            self._lows = (self._lows + [self._lo])[-2:]
        else:
            return
        self._trend = -self._trend
        self._hi, self._lo = (i, c.high), (i, c.low)

    @staticmethod
    def _origin(closed: list[Candle], a: int, b: int, down: bool) -> int | None:
        """Last bar index in [a, b] of the wanted candle color, else None.
        STRICT compare both ways (pine_det: o[j] > c[j] / o[j] < c[j]) -- a
        doji is neither color and never a breaker origin."""
        return next((j for j in range(b, a - 1, -1)
                     if (closed[j].open > closed[j].close if down
                         else closed[j].open < closed[j].close)), None)

    def _msb(self, i: int, closed: list[Candle]) -> None:
        """Market-structure-break check; on MSB, create the breaker box iff
        the older swing was swept (else the Pine's mitigation block: skipped;
        box lifecycles are independent, so omitting it changes nothing)."""
        if len(self._highs) < 2 or len(self._lows) < 2 or i < self._warm:
            return
        (h0i, h0), (h1i, h1) = self._highs[-1], self._highs[-2]
        (l0i, l0), (l1i, l1) = self._lows[-1], self._lows[-2]
        if l0 == self._l0 or h0 == self._h0:
            return
        if (self._market == 1 and l0 < l1
                and float(l0) < float(l1) - abs(float(h0) - float(l1)) * self._fib):
            self._market, self._l0, self._h0 = -1, l0, h0
            if h0 > h1:  # swing high swept -> breaker
                j = self._origin(closed, max(0, h1i - self._zz), l1i, down=True)
                if j is not None:
                    self._boxes.append(_Box(closed[j].high, closed[j].low, -1, i))
        elif (self._market == -1 and h0 > h1
                and float(h0) > float(h1) + abs(float(h1) - float(l0)) * self._fib):
            self._market, self._l0, self._h0 = 1, l0, h0
            if l0 < l1:  # swing low swept -> breaker
                j = self._origin(closed, max(0, l1i - self._zz), h1i, down=False)
                if j is not None:
                    self._boxes.append(_Box(closed[j].high, closed[j].low, 1, i))

    def _sweep_boxes(self, i: int, closed: list[Candle]) -> list[_Box]:
        """Death check first (far-edge close kills, even the birth bar), then
        the once-per-box entry: a LATER close back inside the zone."""
        C = closed[i].close
        fired, keep = [], []
        for b in self._boxes:
            if (b.d == 1 and C < b.bot) or (b.d == -1 and C > b.top):
                continue
            if not b.fired and i > b.born and (
                    b.bot <= C < b.top if b.d == 1 else b.bot < C <= b.top):
                b.fired = True
                fired.append(b)
            keep.append(b)
        self._boxes = keep
        return fired

    def detect(self, ctx: StockContext) -> list[Evidence]:
        tf = Timeframe(self.params["tf"])
        closed = ctx.candles.last(_ALL, tf)  # full continuum closed history
        atr = ctx.atr(tf)
        floor = Decimal(str(self.params["sl_atr_floor"])) * atr if atr else Decimal(0)
        out: list[Evidence] = []
        for i in range(self._n, len(closed)):
            self._flip(i, closed)
            self._msb(i, closed)
            for b in self._sweep_boxes(i, closed):
                long_ = b.d == 1
                sl = b.bot if long_ else b.top  # structural far edge (kill level)
                out.append(Evidence(
                    detector=self.name,
                    direction=Direction.LONG if long_ else Direction.SHORT,
                    strength=_STRENGTH, zone=(b.bot, b.top), ts=ctx.now,
                    ttl_candles=4,
                    meta={"event": "BREAKER_MSB", "sl": str(sl),
                          "sl_floor": str(floor)}))
        self._n = len(closed)
        return _collapse(out, ctx.spec.tick_size)
