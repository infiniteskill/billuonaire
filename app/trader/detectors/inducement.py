"""Inducement detector ("inducement"): faithful port of LuxAlgo "Market
Structure with Inducements & Sweeps" -- the IDM (grab) branch only; the BOS
branch is dropped, it is not needed for the entry (see task brief).

``_swings(H, L, ln)``: LuxAlgo's alternating-pivot fractal, confirmed ``ln``
bars after the pivot (long swings feed CHoCH; short swings, len ``short_len``,
feed the inducement). ``_idm_events``: per-bar state machine -- a close
crossing the last confirmed long swing flips the structure bias (CHoCH,
``os_`` 0<->1); once bullish (``os_``==1), price sweeping the short-swing LOW
below the CHoCH is the inducement grab (dir=1); mirror for bearish (dir=-1,
sweeps the short-swing HIGH). Both branches gate on the CHoCH having already
happened -- a sweep before that never fires.

The detector recomputes this state machine from scratch each tick over the
last ``ln * 4`` closed candles (see ``_DEFAULTS``): the true LuxAlgo state is
cumulative from session/history start, so a bounded window is an approximation
-- it can only diverge from the cumulative run in the first ``ln``-ish bars of
the window while the local ``os_``/``topy``/``btmy`` resettle, which is ample
runway before the window's tail (the only bar a fresh event can land on).
Dedupe is by the confirmed event's own candle ts, per session.
"""

from __future__ import annotations

from decimal import Decimal

from trader.detectors.base import Detector, register
from trader.engine.context import StockContext
from trader.models.candle import Timeframe
from trader.models.evidence import Direction, Evidence

_DEFAULTS = {"tf": "5m", "ln": 20, "short_len": 3}
_STRENGTH = 0.75  # fixed: LuxAlgo source carries no per-signal quality gradient


def _swings(H: list[Decimal], L: list[Decimal], ln: int) -> tuple[list, list]:
    n = len(H)
    top: list = [None] * n
    btm: list = [None] * n
    os_ = 0
    for i in range(n):
        prev = os_
        if i >= ln:
            upper, lower = max(H[i - ln + 1:i + 1]), min(L[i - ln + 1:i + 1])
            hlen, llen = H[i - ln], L[i - ln]
            os_ = 0 if hlen > upper else (1 if llen < lower else prev)
        if os_ == 0 and prev != 0:
            top[i] = H[i - ln]
        if os_ == 1 and prev != 1:
            btm[i] = L[i - ln]
    return top, btm


def _idm_events(H: list[Decimal], L: list[Decimal], C: list[Decimal],
                 ln: int, short_len: int) -> list[tuple[int, int, Decimal]]:
    """[(bar_index, direction, swept_extreme), ...]; direction 1=LONG grab
    (swept a short-swing low), -1=SHORT grab (swept a short-swing high)."""
    top, btm = _swings(H, L, ln)
    stop, sbtm = _swings(H, L, short_len)
    os_ = 0
    top_crossed = btm_crossed = stop_crossed = sbtm_crossed = False
    topy = btmy = stopy = sbtmy = None
    events = []
    for i in range(len(H)):
        prev_os = os_
        if top[i] is not None: topy, top_crossed = top[i], False
        if btm[i] is not None: btmy, btm_crossed = btm[i], False
        if topy is not None and C[i] > topy and not top_crossed:
            os_, top_crossed = 1, True
        if btmy is not None and C[i] < btmy and not btm_crossed:
            os_, btm_crossed = 0, True
        if os_ != prev_os:
            stop_crossed = sbtm_crossed = False
        if stop[i] is not None: stopy = stop[i]
        if sbtm[i] is not None: sbtmy = sbtm[i]
        if sbtmy is not None and L[i] < sbtmy and not sbtm_crossed and os_ == 1 and sbtmy != btmy:
            sbtm_crossed = True
            events.append((i, 1, sbtmy))
        if stopy is not None and H[i] > stopy and not stop_crossed and os_ == 0 and stopy != topy:
            stop_crossed = True
            events.append((i, -1, stopy))
    return events


@register
class InducementDetector(Detector):
    name = "inducement"

    def __init__(self, params: dict):
        super().__init__({**_DEFAULTS, **params})
        self._seen: set[tuple[str, object]] = set()  # (symbol, event candle ts)

    def on_session_end(self) -> None:
        self._seen.clear()

    def detect(self, ctx: StockContext) -> list[Evidence]:
        tf = Timeframe(self.params["tf"])
        ln, short_len = int(self.params["ln"]), int(self.params["short_len"])
        window = ctx.candles.last(ln * 4, tf)
        if len(window) < ln + 1:
            return []
        H = [c.high for c in window]
        L = [c.low for c in window]
        C = [c.close for c in window]
        events = _idm_events(H, L, C, ln, short_len)
        if not events or events[-1][0] != len(window) - 1:
            return []  # only act on a grab landing on the latest closed candle
        _, direction, extreme = events[-1]
        key = (ctx.symbol, window[-1].ts)
        if key in self._seen:
            return []
        self._seen.add(key)
        long_ = direction == 1
        T = ctx.spec.tick_size
        sl = extreme - T if long_ else extreme + T
        return [Evidence(
            detector=self.name,
            direction=Direction.LONG if long_ else Direction.SHORT,
            strength=_STRENGTH,
            zone=(extreme - T, extreme + T),
            ts=ctx.now,
            ttl_candles=3,
            meta={"event": "INDUCEMENT_GRAB", "sl": sl, "os": 1 if long_ else 0},
        )]
