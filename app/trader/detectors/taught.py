"""Shared machinery for the taught zone detectors (fvg_n / ob_taught /
propulsion2) -- the frozen configs of runs/taught/TUNE.md.

BREAK-DEPTH LAW (frozen): a zone lives until a candle CLOSES through its far
edge by >= depth(0.5) x ATR(14); shallower close-throughs leave it alive
("second life", validated +2.69pp t=10 on all 5 holdout cells). Retest =
arm (a later bar fully beyond the box on the origin side) then first touch
of the proximal edge; one-shot per zone. A bar that deep-breaks never also
retests (kill checked first -- ts2's tie=adverse conservatism). ATR = per-bar
trailing SMA of the last 14 true ranges (ctx.atr's exact formula, maintained
rolling as in ob_lux), so every kill decision is causal at its own bar.

The trackers built on this are tf-agnostic: they consume closed bars as
plain Decimals, so research TFs (30m gold labels) test the same code the
detectors run on the engine's candle continuum."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal


@dataclass
class Zone:
    kind: str            # FVG | IFVG | OB | BRK | MIT | PRP
    dir: int             # +1 bull/demand, -1 bear/supply
    lo: Decimal
    hi: Decimal
    born: datetime       # ts of the last birth bar (window end)
    a: int               # bar-index window start (fvg merge rule)
    b: int               # bar-index window end; eligible strictly after
    id: str = ""
    meta: dict = field(default_factory=dict)
    alive: bool = True
    armed: bool = False
    fired: bool = False


class Tape:
    """Bar cursor + trailing ATR(14): SMA of the last 14 TRs, per bar."""

    def __init__(self):
        self.i = -1
        self.atr: Decimal | None = None
        self._prev: Decimal | None = None
        self._trs: deque[Decimal] = deque(maxlen=14)
        self._sum = Decimal(0)

    def step(self, h: Decimal, l: Decimal, c: Decimal) -> int:
        self.i += 1
        if self._prev is not None:
            tr = max(h - l, abs(h - self._prev), abs(l - self._prev))
            if len(self._trs) == self._trs.maxlen:
                self._sum -= self._trs[0]
            self._trs.append(tr)
            self._sum += tr
        full = len(self._trs) == self._trs.maxlen
        self.atr = self._sum / self._trs.maxlen if full else None
        self._prev = c
        return self.i


def step_zone(z: Zone, i: int, h: Decimal, l: Decimal, c: Decimal,
              atr: Decimal | None, depth: Decimal) -> str | None:
    """One closed bar against one zone: 'kill' | 'retest' | None."""
    if not z.alive or i <= z.b:
        return None
    far_out = z.lo - c if z.dir == 1 else c - z.hi
    if atr is not None and far_out >= depth * atr:
        z.alive = False
        return "kill"
    left = l > z.hi if z.dir == 1 else h < z.lo
    if not z.armed:
        z.armed = left
    elif not z.fired and not left:
        z.fired = True
        return "retest"
    return None
