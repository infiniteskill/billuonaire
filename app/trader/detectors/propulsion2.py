"""propulsion2 detector ("propulsion2"): PARENT-LINKED propulsion -- lesson
14 + ZONES P3, the +43.4pp law (parent-live respect 60.2% vs orphaned 16.8%;
an orphaned propulsion zone is ANTI-signal, so parent linkage is mandatory
and orphan emission is forbidden by construction; propulsion_block -- which
lost the linkage -- stays untouched for parity history).

A candle trading INTO a live taught-OB zone (the parent's first armed
retest) and CLOSING away beyond it in the parent's direction with a
directional body is the propulsion block: child zone = that candle's BODY
range, carrying the parent zone id. The child lives under the same
break-depth law AND dies instantly with its parent: the death cascade runs
BEFORE the child's own bar step, so the bar that kills the parent can
never fire the child, and a dead parent's box can never birth one.
Evidence (one-shot) on the child's first armed retest: parent direction,
edge entry, ttl 4, strength 0.8, meta {"event","sl","sl_floor","parent"};
sl = the child's far edge raw.

Owns a private ObZones tracker -- the same deterministic computation
ob_taught runs over the same closed-candle continuum (detachable-detector
principle; keep tf/depth_atr mirroring ob_taught's params). Config still
requires ob_taught enabled before it (check_detector_deps): a child is
only tradeable context alongside its journaled live parent."""

from __future__ import annotations

from decimal import Decimal

from trader.detectors.base import Detector, register
from trader.detectors.ob_taught import ObZones
from trader.detectors.taught import Zone, step_zone
from trader.engine.context import StockContext
from trader.models.candle import Timeframe
from trader.models.evidence import Direction, Evidence

_DEFAULTS = {"tf": "5m", "depth_atr": 0.5, "sl_atr_floor": 0.15}
_ALL = 10 ** 9


@register
class Propulsion2Detector(Detector):
    name = "propulsion2"

    def __init__(self, params: dict):
        super().__init__({**_DEFAULTS, **params})
        self._obz = ObZones(Decimal(str(self.params["depth_atr"])))
        self._kids: list[Zone] = []
        self._n = 0

    def on_session_end(self) -> None:
        self._obz.zones = [z for z in self._obz.zones if z.alive]
        self._kids = [k for k in self._kids if k.alive]

    def detect(self, ctx: StockContext) -> list[Evidence]:
        tf = Timeframe(self.params["tf"])
        window = ctx.candles.last(_ALL, tf)
        out: list[Evidence] = []
        for i in range(self._n, len(window)):
            c = window[i]
            events = self._obz.step(c.ts, c.open, c.high, c.low, c.close)
            j = self._obz.tape.i
            for k in self._kids:                 # parent death cascades FIRST:
                if k.alive and not k.meta["parent"].alive:
                    k.alive = False              # the killing bar can't fire kids
            for k in self._kids:
                if (step_zone(k, j, c.high, c.low, c.close, self._obz.tape.atr,
                              self._obz.depth) == "retest"
                        and i == len(window) - 1):
                    out.append(self._evidence(ctx, tf, k))
            for ev, z in events:                 # birth: parent's first armed
                if ev != "retest" or z.kind != "OB" or not z.alive:
                    continue                     # retest, parent still alive
                d = z.dir
                if not ((c.close > z.hi and c.close > c.open) if d == 1
                        else (c.close < z.lo and c.close < c.open)):
                    continue                     # must close away, directional body
                lo, hi = sorted((c.open, c.close))
                self._kids.append(Zone("PRP", d, lo, hi, c.ts, j, j,
                                       id=f"PRP{d:+d}@{c.ts.isoformat()}",
                                       meta={"parent": z}))
        self._n = len(window)
        return out

    def _evidence(self, ctx: StockContext, tf: Timeframe, k: Zone) -> Evidence:
        atr = ctx.atr(tf)
        floor = Decimal(str(self.params["sl_atr_floor"])) * atr if atr else Decimal(0)
        up = k.dir == 1
        return Evidence(
            detector=self.name,
            direction=Direction.LONG if up else Direction.SHORT,
            strength=0.8, zone=(k.lo, k.hi), ts=ctx.now, ttl_candles=4,
            meta={"event": "PROPULSION2", "sl": str(k.lo if up else k.hi),
                  "sl_floor": str(floor), "parent": k.meta["parent"].id})
