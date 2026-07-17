"""Inducement detector ("inducement"): faithful STATEFUL port of LuxAlgo
"Market Structure with Inducements & Sweeps" -- the IDM (grab) branch.

The reference (``scratchpad/ind_sweeps.py`` ``simulate(m5, ln, shortLen)[0]``)
is a single forward pass over the WHOLE continuous multi-day candle series --
never reset at a day/window boundary. This detector reproduces that pass
exactly by keeping the state machine live on the instance and advancing it one
newly-closed candle at a time (``self._n`` = count of closed bars already
consumed). It is bit-for-bit the same run as recomputing ``simulate`` over all
history every tick, only incremental.

Two things a naive windowed port loses -- both restored here:

* BOS re-arm (side-effect only, no event emitted). In ``simulate`` a break of
  the trailing extreme (``maxv``/``minv``) established since the CHoCH clears
  the inducement latch (``sbtm_crossed``/``stop_crossed``), so a second sweep
  fires in the *same* os-regime. We carry ``maxv``/``minv`` (seeded to
  ``H[i]``/``L[i]`` on every os flip, extended each bar) and replicate the
  latch reset. Without it the detector fires at most one IDM per regime.

* Full-history state. os / CHoCH bias is cumulative from the very first bar;
  a CHoCH older than any fixed window must stay visible. So we never window,
  never reset at session open -- structure carries across days.

``swings(ln)`` is LuxAlgo's alternating-pivot fractal, the pivot at ``i-ln``
confirmed at bar ``i`` using bars <= ``i`` (no lookahead), which is exactly
what makes the incremental step sound. Long swings (len ``ln``) feed CHoCH,
short swings (len ``short_len``) feed the inducement. dir=1 => a short-swing
LOW swept below the CHoCH => LONG grab; dir=-1 => a short-swing HIGH swept =>
SHORT grab. Both gate on the CHoCH having already flipped os.

Dedupe is by the confirmed grab's own candle ts. ``on_session_end`` prunes
only that dedupe set -- it MUST NOT touch the structural FSM state, which
carries across sessions.
"""

from __future__ import annotations

from trader.detectors.base import Detector, register
from trader.engine.context import StockContext
from trader.models.candle import Candle, Timeframe
from trader.models.evidence import Direction, Evidence

_DEFAULTS = {"tf": "5m", "ln": 20, "short_len": 3}
_STRENGTH = 0.75  # fixed: LuxAlgo source carries no per-signal quality gradient
_ALL = 10 ** 9    # "all closed candles" sentinel for CandleView.last


@register
class InducementDetector(Detector):
    name = "inducement"

    def __init__(self, params: dict):
        super().__init__({**_DEFAULTS, **params})
        self._ln = int(self.params["ln"])
        self._short_len = int(self.params["short_len"])
        self._seen: set[tuple[str, object]] = set()  # (symbol, grab candle ts)
        self._reset_state()

    def _reset_state(self) -> None:
        """Initial FSM/swing state -- the start of ``simulate``. Called once at
        construction; NEVER from ``on_session_end`` (structure is multi-day)."""
        self._n = 0                       # closed bars already consumed
        self._swl_os = self._sws_os = 0   # swings() os_ for long / short lengths
        self._os = 0
        self._top_crossed = self._btm_crossed = False
        self._stop_crossed = self._sbtm_crossed = False
        self._topy = self._btmy = self._stopy = self._sbtmy = None
        self._maxv = self._minv = None

    def on_session_end(self) -> None:
        # Prune the dedupe set only. The FSM state is market structure and
        # carries across days -- wiping it would blind the detector to any
        # CHoCH older than the new session (the very bug this port fixes).
        self._seen.clear()

    def _swing(self, i: int, closed: list[Candle], ln: int, os_: int) -> tuple:
        """One bar of LuxAlgo ``swings(ln)``: returns (new os_, top_i, btm_i),
        where top_i/btm_i is the confirmed pivot price this bar or None."""
        prev = os_
        if i >= ln:
            window = closed[i - ln + 1:i + 1]
            upper = max(c.high for c in window)
            lower = min(c.low for c in window)
            hlen, llen = closed[i - ln].high, closed[i - ln].low
            os_ = 0 if hlen > upper else (1 if llen < lower else prev)
        top_i = closed[i - ln].high if (os_ == 0 and prev != 0) else None
        btm_i = closed[i - ln].low if (os_ == 1 and prev != 1) else None
        return os_, top_i, btm_i

    def _step(self, i: int, closed: list[Candle]) -> tuple | None:
        """Advance the state machine by the single closed bar ``i``. Returns a
        (direction, swept_extreme) grab landing on this bar, else None. Mirrors
        the forward loop of ``simulate`` exactly (minus emitting BOS events)."""
        c = closed[i]
        H, L, C = c.high, c.low, c.close
        self._swl_os, top_i, btm_i = self._swing(i, closed, self._ln, self._swl_os)
        self._sws_os, stop_i, sbtm_i = self._swing(i, closed, self._short_len, self._sws_os)

        prev_os = self._os
        if top_i is not None:
            self._topy, self._top_crossed = top_i, False
        if btm_i is not None:
            self._btmy, self._btm_crossed = btm_i, False
        if self._topy is not None and C > self._topy and not self._top_crossed:
            self._os, self._top_crossed = 1, True
        if self._btmy is not None and C < self._btmy and not self._btm_crossed:
            self._os, self._btm_crossed = 0, True
        if self._os != prev_os:
            self._maxv, self._minv = H, L
            self._stop_crossed = self._sbtm_crossed = False
        if stop_i is not None:
            self._stopy = stop_i
        if sbtm_i is not None:
            self._sbtmy = sbtm_i

        grab = None
        # Bullish IDM then BOS re-arm
        if (self._sbtmy is not None and L < self._sbtmy and not self._sbtm_crossed
                and self._os == 1 and self._sbtmy != self._btmy):
            self._sbtm_crossed = True
            grab = (1, self._sbtmy)
        if self._maxv is not None and C > self._maxv and self._sbtm_crossed and self._os == 1:
            self._sbtm_crossed = False  # BOS: re-arm the inducement latch
        # Bearish IDM then BOS re-arm
        if (self._stopy is not None and H > self._stopy and not self._stop_crossed
                and self._os == 0 and self._stopy != self._topy):
            self._stop_crossed = True
            grab = (-1, self._stopy)
        if self._minv is not None and C < self._minv and self._stop_crossed and self._os == 0:
            self._stop_crossed = False  # BOS: re-arm the inducement latch

        if self._maxv is not None:
            self._maxv = max(H, self._maxv)
        if self._minv is not None:
            self._minv = min(L, self._minv)
        return grab

    def detect(self, ctx: StockContext) -> list[Evidence]:
        tf = Timeframe(self.params["tf"])
        closed = ctx.candles.last(_ALL, tf)  # full continuous closed history
        out: list[Evidence] = []
        T = ctx.spec.tick_size
        for i in range(self._n, len(closed)):
            grab = self._step(i, closed)
            if grab is None:
                continue
            ts = closed[i].ts
            key = (ctx.symbol, ts)
            if key in self._seen:
                continue
            self._seen.add(key)
            direction, extreme = grab
            long_ = direction == 1
            sl = extreme - T if long_ else extreme + T
            out.append(Evidence(
                detector=self.name,
                direction=Direction.LONG if long_ else Direction.SHORT,
                strength=_STRENGTH,
                zone=(extreme - T, extreme + T),
                ts=ctx.now,
                ttl_candles=3,
                meta={"event": "INDUCEMENT_GRAB", "sl": sl, "os": 1 if long_ else 0},
            ))
        self._n = len(closed)
        return out
