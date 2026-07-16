"""PO3 (Power of Three) FSM: Accumulation -> Manipulation -> Distribution
made computable (dev/plan/06 SS3). One instance per (symbol, scale); lives
in ``ctx.day.po3`` keyed by scale ("day" opening range / "leg" compression
box, SS5). ``set_box(lo, hi, ts)`` arms the FSM => ACCUMULATION. ``step``
consumes one closed candle, returns the new state on a transition else None:

- ACCUMULATION -> MANIPULATION: wick beyond a box edge with close back
  inside (sweep); records ``swept_side`` ("low"/"high") + ``sweep_extreme``.
- MANIPULATION -> DISTRIBUTION: close displaced >= displacement_atr x ATR
  from box mid away from the swept side AND recent BOS evidence; records
  ``true_direction`` (opposite the sweep). Terminal until the next set_box.
- -> IDLE (``reason`` "trend"): two consecutive closes beyond the same box
  edge with no reclaim -- trend continuation, not manipulation; hand off."""

from __future__ import annotations

from decimal import Decimal

from trader.models.candle import Candle
from trader.models.evidence import Direction

_DEFAULTS = {"displacement_atr": 1.5, "reclaim_candles": 3}


class PO3FSM:
    def __init__(self, spec=None, params: dict | None = None):
        self.spec = spec
        self.params = {**_DEFAULTS, **(params or {})}
        self.state = "IDLE"
        self.box: tuple[Decimal, Decimal] | None = None
        self.box_ts = None
        self.reason: str | None = None
        self._last_ts = None  # ts of last candle consumed by step (idempotency)
        self._reset_sequence()

    def _reset_sequence(self) -> None:
        self.swept_side: str | None = None
        self.sweep_extreme: Decimal | None = None
        self.true_direction: Direction | None = None
        self._beyond: tuple[str, int] | None = None  # (side, consecutive closes)

    def set_box(self, lo: Decimal, hi: Decimal, ts) -> str:
        self.box, self.box_ts = (lo, hi), ts  # fresh box arms the FSM
        self.state, self.reason = "ACCUMULATION", None
        self._reset_sequence()
        return self.state

    def step(self, candle: Candle, atr: Decimal | None,
             bos_evidence_recent: bool) -> str | None:
        """Feed one closed candle; new state on transition. Re-stepping an
        already-consumed candle ts is a no-op (idempotent per candle)."""
        if (self.state not in ("ACCUMULATION", "MANIPULATION")
                or (self._last_ts is not None and candle.ts <= self._last_ts)):
            return None  # inert state, or same/older candle re-stepped: no-op
        self._last_ts, (lo, hi) = candle.ts, self.box
        if (self.state == "MANIPULATION"
                and self._displaced(candle, atr, bos_evidence_recent, lo, hi)):
            return self.state
        if self._trend_handoff(candle, lo, hi):
            return self.state
        if self.state == "ACCUMULATION" and self._swept(candle, lo, hi):
            return self.state
        return None

    def _swept(self, candle: Candle, lo: Decimal, hi: Decimal) -> bool:
        """Wick beyond an edge, close back inside (or through) => sweep."""
        if candle.low < lo and candle.close >= lo:
            self.swept_side, self.sweep_extreme = "low", candle.low
        elif candle.high > hi and candle.close <= hi:
            self.swept_side, self.sweep_extreme = "high", candle.high
        else:
            return False
        self.state = "MANIPULATION"
        return True

    def _displaced(self, candle: Candle, atr: Decimal | None,
                   bos_recent: bool, lo: Decimal, hi: Decimal) -> bool:
        if atr is None or not bos_recent:
            return False
        need, mid = Decimal(str(self.params["displacement_atr"])) * atr, (lo + hi) / 2
        if self.swept_side == "low" and candle.close - mid >= need:
            self.true_direction = Direction.LONG
        elif self.swept_side == "high" and mid - candle.close >= need:
            self.true_direction = Direction.SHORT
        else:
            return False
        self.state = "DISTRIBUTION"
        return True

    def _trend_handoff(self, candle: Candle, lo: Decimal, hi: Decimal) -> bool:
        side = "high" if candle.close > hi else "low" if candle.close < lo else None
        if side is None:
            self._beyond = None  # close back inside: streak broken
            return False
        n = self._beyond[1] + 1 if self._beyond and self._beyond[0] == side else 1
        self._beyond = (side, n)
        if n < 2:
            return False
        self.state, self.reason = "IDLE", "trend"
        return True
