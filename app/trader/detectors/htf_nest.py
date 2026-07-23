"""htf_nest detector ("htf_nest"): the taught multi-TF NESTING refine (node 5).
Generalises ladder._rung (single H1<-M5 overlap) to a full TF ladder.

For each base-tf decisional zone (OB/FVG Level, ACTIVE/TESTED) it counts how
many HIGHER-tf SAME-DIRECTION decisional zones CONTAIN it (overlap) -> nest_depth
= number of distinct higher TFs a parent lives on. When nest_depth >= min_depth
it emits ONE Evidence (deduped per base zone): the LTF entry nested inside the
HTF zone(s) -- the taught "5m OB inside the 2H OB" (t28-30). direction = the base
zone direction; entry = CE (mid) of the base; SL = the base's far (outer) edge;
strength scales with depth. Higher nest_depth = deeper HTF agreement = higher
conviction. TFs limited to the enum (5m/15m/1h/1d); 2H/30m/10m marks await the
Timeframe extension (dev/plan/41-TOOLS/_GAPS G2)."""
from __future__ import annotations

from decimal import Decimal

from trader.detectors.base import Detector, register
from trader.engine.context import StockContext
from trader.models.candle import Timeframe
from trader.models.evidence import Direction, Evidence
from trader.models.level import LevelKind, LevelState

_BULL = frozenset({LevelKind.OB_BULL, LevelKind.FVG_BULL})
_BEAR = frozenset({LevelKind.OB_BEAR, LevelKind.FVG_BEAR})
_DEC = _BULL | _BEAR
_ACTIVE = (LevelState.ACTIVE, LevelState.TESTED)
_DEFAULTS = {"base_tf": "5m", "min_depth": 1, "ttl": 6,
             "htf_order": ["5m", "15m", "1h", "1d"]}


def _lohi(z) -> tuple[Decimal, Decimal]:
    return (min(z), max(z))


def _overlaps(a, b) -> bool:
    alo, ahi = _lohi(a)
    blo, bhi = _lohi(b)
    return alo <= bhi and blo <= ahi


@register
class HtfNestDetector(Detector):
    name = "htf_nest"

    def __init__(self, params: dict):
        super().__init__({**_DEFAULTS, **params})
        self._seen: set = set()  # base zone ids already emitted

    def on_session_end(self) -> None:
        self._seen.clear()

    def detect(self, ctx: StockContext) -> list[Evidence]:
        base_tf = Timeframe(self.params["base_tf"])
        rank = {Timeframe(t): i for i, t in enumerate(self.params["htf_order"])}
        zones = [lv for lv in ctx.levels
                 if lv.kind in _DEC and lv.state in _ACTIVE and lv.tf in rank]
        out: list[Evidence] = []
        for b in zones:
            if b.tf is not base_tf or b.id in self._seen:
                continue
            bull = b.kind in _BULL
            br = rank[b.tf]
            tiers = {z.tf for z in zones
                     if rank.get(z.tf, -1) > br and (z.kind in _BULL) == bull
                     and _overlaps(z.zone, b.zone)}
            if len(tiers) < int(self.params["min_depth"]):
                continue
            self._seen.add(b.id)
            lo, hi = _lohi(b.zone)
            out.append(Evidence(
                detector=self.name,
                direction=Direction.LONG if bull else Direction.SHORT,
                strength=min(1.0, len(tiers) / 3), zone=(lo, hi),
                ts=ctx.now, ttl_candles=int(self.params["ttl"]),
                meta={"event": "NEST", "nest_depth": len(tiers),
                      "tiers": sorted(t.value for t in tiers),
                      "ce": str((lo + hi) / 2),                # entry = mid
                      "sl": str(lo if bull else hi)}))         # SL = base far edge
        return out
