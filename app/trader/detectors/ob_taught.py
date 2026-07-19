"""ob_taught detector ("ob_taught"): the taught order block -- lessons 3/12
+ the frozen TUNE.md config (bodies-only box, join 0, dist as GRADE not
filter; ob_lux stays untouched for parity history).

CLUSTER: a run of consecutive bars whose closes stay inside the evolving
bodies box (single opposite candle = the degenerate run). The first close
beyond the box is the continuation break: if the run holds >= 1 candle
opposite to the break direction (the pause needs counter-pressure), the
bodies hi-lo from the first opposite candle onward is the OB, born at the
break bar (bodies-only is frozen: +3.46..+3.83 vs full box; join tolerance
0 is a proven no-op). A break with no opposite candle is just trend -- the
run resets, no zone.

GRADE: pivot-distance in meta ("pivot_dist_atr"): ATR distance from the
zone's origin edge to the nearest same-side extremes pivot in ctx.levels
(SWING_L for demand / SWING_H for supply; the extremes writer must precede
this detector in config order to grade same-tick) -- absent pivots or ATR
=> params far_dist_atr (grade only, never a detection filter -- TUNE's
maxd=any re-freeze). Historic births during a catch-up scan grade against
now-time levels (grade-grade approximation, documented).

LIFECYCLE: taught.step_zone break-depth law (>= 0.5xATR close-through
kills; shallower = second life). On kill the box FLIPS (lesson 12
one-question test): the birth leg's running extreme (tracked causally from
the break bar) took the prior same-side extreme (meta "pex", the most
recent opposite-side swing at birth) => BRK, else (failure to swing, or no
extreme known) => MIT. The flipped zone -- opposite direction, same box,
parent's grade -- emits on retest from the other side under the same law
(its own deep break just kills it). Evidence (one-shot) on first armed
retest: continuation direction, edge entry, ttl 6, strength 0.7, meta
{"event","sl","sl_floor","pivot_dist_atr"}; sl = far edge raw.

CONTINUUM + INCREMENTAL: full-history cursor (ob_lux pattern), Evidence
only from the latest closed bar; ``on_session_end`` prunes dead zones."""

from __future__ import annotations

from decimal import Decimal

from trader.detectors.base import Detector, register
from trader.detectors.taught import Tape, Zone, step_zone
from trader.engine.context import StockContext
from trader.models.candle import Timeframe
from trader.models.evidence import Direction, Evidence
from trader.models.level import LevelKind

_DEFAULTS = {"tf": "5m", "depth_atr": 0.5, "sl_atr_floor": 0.15,
             "far_dist_atr": 99.0}
_EVENT = {"OB": "OB_RETEST", "BRK": "BRK_RETEST", "MIT": "MIT_RETEST"}
# extremes (zigzag) pivots are the taught anchor (lesson 1); fractal swings
# are the fallback when the extremes detector is not enabled.
_PIV = {1: (LevelKind.EXT_L, LevelKind.SWING_L),
        -1: (LevelKind.EXT_H, LevelKind.SWING_H)}
_ALL = 10 ** 9


class ObZones:
    """Incremental taught-OB tracker; tf-agnostic (fed closed bars)."""

    def __init__(self, depth: Decimal = Decimal("0.5")):
        self.depth = depth
        self.tape = Tape()
        self.zones: list[Zone] = []
        self._run: list[tuple[Decimal, Decimal, int]] = []  # (body_lo, body_hi, sign)

    def step(self, ts, o, h, l, c) -> list[tuple[str, Zone]]:
        i = self.tape.step(h, l, c)
        events, flips = [], []
        for z in self.zones:
            if z.alive and z.kind == "OB":       # birth-leg running extreme
                z.meta["ext"] = (max(z.meta["ext"], h) if z.dir == 1
                                 else min(z.meta["ext"], l))
            ev = step_zone(z, i, h, l, c, self.tape.atr, self.depth)
            if ev == "kill" and z.kind == "OB":
                pex = z.meta.get("pex")
                swept = pex is not None and (z.meta["ext"] > pex if z.dir == 1
                                             else z.meta["ext"] < pex)
                kind = "BRK" if swept else "MIT"
                flips.append(Zone(kind, -z.dir, z.lo, z.hi, ts, i, i,
                                  id=f"{kind}{-z.dir:+d}@{ts.isoformat()}",
                                  meta={"pivot_dist_atr": z.meta.get("pivot_dist_atr")}))
            if ev:
                events.append((ev, z))
        self.zones += flips
        born = self._cluster(ts, i, o, h, l, c)
        if born is not None:
            self.zones.append(born)
            events.append(("birth", born))
        return events

    def _cluster(self, ts, i, o, h, l, c) -> Zone | None:
        body = (min(o, c), max(o, c), 1 if c > o else -1 if c < o else 0)
        z = None
        if self._run:
            blo = min(b[0] for b in self._run)
            bhi = max(b[1] for b in self._run)
            if c > bhi or c < blo:                       # continuation break
                d = 1 if c > bhi else -1
                k = next((j for j, bb in enumerate(self._run) if bb[2] == -d), None)
                if k is not None:                        # pause had counter-pressure
                    sub = self._run[k:]
                    z = Zone("OB", d, min(bb[0] for bb in sub),
                             max(bb[1] for bb in sub), ts,
                             i - len(self._run) + k, i,
                             id=f"OB{d:+d}@{ts.isoformat()}",
                             meta={"ext": h if d == 1 else l})
                self._run = []
        self._run.append(body)
        return z


@register
class ObTaughtDetector(Detector):
    name = "ob_taught"

    def __init__(self, params: dict):
        super().__init__({**_DEFAULTS, **params})
        self._z = ObZones(Decimal(str(self.params["depth_atr"])))
        self._n = 0

    def on_session_end(self) -> None:
        self._z.zones = [z for z in self._z.zones if z.alive]  # memory bound

    def detect(self, ctx: StockContext) -> list[Evidence]:
        tf = Timeframe(self.params["tf"])
        window = ctx.candles.last(_ALL, tf)
        out: list[Evidence] = []
        for i in range(self._n, len(window)):
            c = window[i]
            for ev, z in self._z.step(c.ts, c.open, c.high, c.low, c.close):
                if ev == "birth":
                    self._grade(ctx, z)
                elif ev == "retest" and i == len(window) - 1:
                    out.append(self._evidence(ctx, tf, z))
        self._n = len(window)
        return out

    def _grade(self, ctx: StockContext, z: Zone) -> None:
        """Pivot-distance grade + the prior same-side extreme for the flip
        sweep test, both read from ctx.levels at birth."""
        atr = self._z.tape.atr
        edge = z.lo if z.dir == 1 else z.hi
        ext_k, sw_k = _PIV[z.dir]                       # extremes first, swings fallback
        pivs = [lv.zone[0] for lv in ctx.levels if lv.kind is ext_k] \
            or [lv.zone[0] for lv in ctx.levels if lv.kind is sw_k]
        z.meta["pivot_dist_atr"] = (
            float(min(abs(edge - p) for p in pivs) / atr) if pivs and atr
            else float(self.params["far_dist_atr"]))
        oext_k, osw_k = _PIV[-z.dir]
        opp = [lv for lv in ctx.levels if lv.kind is oext_k] \
            or [lv for lv in ctx.levels if lv.kind is osw_k]
        if opp:
            z.meta["pex"] = max(opp, key=lambda lv: lv.born).zone[0]

    def _evidence(self, ctx: StockContext, tf: Timeframe, z: Zone) -> Evidence:
        atr = ctx.atr(tf)
        floor = Decimal(str(self.params["sl_atr_floor"])) * atr if atr else Decimal(0)
        up = z.dir == 1
        return Evidence(
            detector=self.name,
            direction=Direction.LONG if up else Direction.SHORT,
            strength=0.7, zone=(z.lo, z.hi), ts=ctx.now, ttl_candles=6,
            meta={"event": _EVENT[z.kind], "sl": str(z.lo if up else z.hi),
                  "sl_floor": str(floor),
                  "pivot_dist_atr": z.meta.get("pivot_dist_atr")})
