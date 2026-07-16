"""Compression detector ("compression"): coiled-energy cluster finder that
arms and drives the "leg"-scale PO3 FSM (dev/plan/06 SS5 + SS3).

Scored over the last ``window`` closed tf candles:
    contraction  mean(range last 4) / mean(range first 4) < 0.6      (0.30)
    overlap      intersection of the last 6 bodies non-empty         (0.25)
    vol_slope    linear-regression slope of volume < 0               (0.25)
    nr_cluster   >=2 of last 4 candles narrowest-of-7 or inside bars (0.20)
score >= 0.7 => box = (min low, max high) of the last 6 candles, registered
via ``ctx.day.po3["leg"].set_box`` -- only while that FSM is IDLE or
DISTRIBUTION (never clobbers an active sequence). Every detect also steps
the leg FSM with the latest candle (bos_recent = any BOS evidence within
the last 6 candles).

Evidence (deduped per (event, box ts)):
- FSM reaches DISTRIBUTION this candle => 0.85 true_direction ttl 24,
  zone=box, meta PO3_DIST, energy = box_height x expansion_factor;
- box confirmed overlapping an ACTIVE/TESTED OB/FVG level => 0.75 in the
  level's direction, meta BOX_ON_LEVEL + level_id (loaded spring)."""

from __future__ import annotations

from decimal import Decimal
from statistics import fmean

from trader.detectors.base import Detector, register
from trader.engine.context import StockContext
from trader.engine.po3 import PO3FSM
from trader.models.candle import Candle, Timeframe
from trader.models.evidence import Direction, Evidence
from trader.models.level import LevelKind, LevelState

_DEFAULTS = {"tf": "5m", "window": 12, "expansion_factor": 2.5}
_LEVEL_DIR = {LevelKind.OB_BULL: Direction.LONG, LevelKind.FVG_BULL: Direction.LONG,
              LevelKind.OB_BEAR: Direction.SHORT, LevelKind.FVG_BEAR: Direction.SHORT}


@register
class CompressionDetector(Detector):
    name = "compression"

    def __init__(self, params: dict):
        super().__init__({**_DEFAULTS, **params})
        self._seen: set = set()  # (event, box ts) already emitted

    def detect(self, ctx: StockContext) -> list[Evidence]:
        tf, w = Timeframe(self.params["tf"]), int(self.params["window"])
        candles = ctx.candles.last(w, tf)
        if not candles:
            return []
        fsm = ctx.day.po3.setdefault("leg", PO3FSM(ctx.spec))
        out = []
        if (len(candles) == w and fsm.state in ("IDLE", "DISTRIBUTION")
                and self._score(candles) >= 0.7):
            last6 = candles[-6:]
            fsm.set_box(min(c.low for c in last6), max(c.high for c in last6),
                        candles[-1].ts)
            out.extend(self._box_on_level(ctx, fsm))
        if fsm.step(candles[-1], ctx.atr(tf), self._bos_recent(ctx, tf)) == "DISTRIBUTION":
            out.extend(self._distribution(ctx, fsm))
        return out

    def _score(self, w: list[Candle]) -> float:
        first4 = fmean(c.range for c in w[:4])
        contraction = first4 > 0 and fmean(c.range for c in w[-4:]) / first4 < 0.6
        overlap = (max(min(c.open, c.close) for c in w[-6:])
                   <= min(max(c.open, c.close) for c in w[-6:]))
        x_mid, v_mean = (len(w) - 1) / 2, fmean(c.volume for c in w)
        vol = sum((i - x_mid) * (c.volume - v_mean) for i, c in enumerate(w)) < 0
        nr = sum(self._nr_or_inside(w, i) for i in range(len(w) - 4, len(w))) >= 2
        return 0.3 * contraction + 0.25 * overlap + 0.25 * vol + 0.2 * nr

    @staticmethod
    def _nr_or_inside(w: list[Candle], i: int) -> bool:
        inside = w[i].high <= w[i - 1].high and w[i].low >= w[i - 1].low
        nr7 = i >= 6 and w[i].range <= min(c.range for c in w[i - 6:i])
        return inside or nr7

    def _bos_recent(self, ctx: StockContext, tf: Timeframe) -> bool:
        recent = ctx.candles.last(6, tf)
        return bool(recent) and any(
            e.meta.get("event") == "BOS" and e.ts >= recent[0].ts
            for e in ctx.evidence_history)

    def _box_on_level(self, ctx: StockContext, fsm: PO3FSM) -> list[Evidence]:
        if ("BOX_ON_LEVEL", fsm.box_ts) in self._seen:
            return []
        lo, hi = fsm.box
        out = [Evidence(detector=self.name, direction=_LEVEL_DIR[lv.kind],
                        strength=0.75, zone=fsm.box, ts=ctx.now, ttl_candles=24,
                        meta={"event": "BOX_ON_LEVEL", "level_id": lv.id})
               for lv in ctx.levels
               if lv.kind in _LEVEL_DIR
               and lv.state in (LevelState.ACTIVE, LevelState.TESTED)
               and lv.zone[0] <= hi and lo <= lv.zone[1]]
        if out:
            self._seen.add(("BOX_ON_LEVEL", fsm.box_ts))
        return out

    def _distribution(self, ctx: StockContext, fsm: PO3FSM) -> list[Evidence]:
        if ("PO3_DIST", fsm.box_ts) in self._seen:
            return []
        self._seen.add(("PO3_DIST", fsm.box_ts))
        energy = (fsm.box[1] - fsm.box[0]) * Decimal(str(self.params["expansion_factor"]))
        return [Evidence(detector=self.name, direction=fsm.true_direction,
                         strength=0.85, zone=fsm.box, ts=ctx.now, ttl_candles=24,
                         meta={"event": "PO3_DIST", "energy": str(energy)})]
