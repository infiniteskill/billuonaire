"""fvg_n detector ("fvg_n"): generalized MERGED fair-value gaps -- the frozen
TUNE.md config (lesson 2, runs/taught/{ZONES,TUNE}.md; strict-3 fvg_cb stays
untouched for parity history, m=1 is this detector's special case).

A displacement burst of 1..mmax(=6 frozen) middle candles whose flanking
WICKS do not overlap leaves a gap (bull: right flank low > left flank high,
every middle CLOSING beyond the near flank wick; bear mirror); min gap 0
(any size -- frozen q=0). MERGE RULE (user-specified "continuous gaps = ONE
FVG", frozen as ts2_lib.fvg_n_extra DEDUP, not union): a new fragment whose
candle window AND band overlap an existing live same-direction FVG zone is
DROPPED -- the existing zone already represents that displacement; the box
does NOT grow. Smaller-m/strict-3 fragments are seen first (per ending bar
m ascends from 1), so they are the kept representatives. This keeps a
multi-candle burst as one zone without a staircase rally chain-merging into
one mega-void (the bug a growing-union rule produces).

Lifecycle = taught.step_zone (BREAK-DEPTH LAW: close through the far edge
by >= 0.5xATR(14) kills, shallower closes = second life). A killed gap
flips to an iFVG: opposite direction, same box, same law, one generation
(an iFVG's own deep break just kills it). Evidence (one-shot) on the first
armed retest: continuation of the birth impulse (bull gap -> LONG on
refill; iFVG opposite), edge entry (zone = the box), ttl 6, strength 0.6,
meta {"event","sl","sl_floor"} with sl = the zone's far edge raw (the
executor applies the floor, as propulsion_block).

CONTINUUM + INCREMENTAL: consumes the full closed-candle history via a
consumed-bar cursor (ob_lux pattern); Evidence only from the latest closed
bar -- historical steps build state silently. ``on_session_end`` prunes
dead zones (memory bound); live zones carry (zones live for weeks)."""

from __future__ import annotations

from collections import deque
from decimal import Decimal

from trader.detectors.base import Detector, register
from trader.detectors.taught import Tape, Zone, step_zone
from trader.engine.context import StockContext
from trader.models.candle import Timeframe
from trader.models.evidence import Direction, Evidence

_DEFAULTS = {"tf": "5m", "mmax": 6, "depth_atr": 0.5, "sl_atr_floor": 0.15,
             "merge_chain": False,   # union adjacent same-dir gaps into one region
             "merge_max_bars": 0,    # 0 = 2*mmax; cap on the merged displacement run
             "min_gap_atr": 0.0}   # birth needs gap >= min_gap_atr*ATR (0 = off)
_EVENT = {"FVG": "FVG_N_RETEST", "IFVG": "IFVG_RETEST"}
_ALL = 10 ** 9


class FvgZones:
    """Incremental merged-FVG tracker; tf-agnostic (fed closed bars)."""

    def __init__(self, mmax: int = 6, depth: Decimal = Decimal("0.5"),
                 min_gap: Decimal = Decimal(0)):
        self.mmax, self.depth, self.min_gap = mmax, depth, min_gap
        self.tape = Tape()
        self.zones: list[Zone] = []
        self._bars: deque = deque(maxlen=mmax + 2)   # (h, l, c)
        self.merge_chain = False                     # set by the detector from params
        self.merge_max_bars = 2 * mmax               # cap on a merged run

    def step(self, ts, o, h, l, c) -> list[tuple[str, Zone]]:
        i = self.tape.step(h, l, c)
        self._bars.append((h, l, c))
        events, flips = [], []
        for z in self.zones:
            ev = step_zone(z, i, h, l, c, self.tape.atr, self.depth)
            if ev == "kill" and z.kind == "FVG":
                flips.append(Zone("IFVG", -z.dir, z.lo, z.hi, ts, i, i))
            if ev:
                events.append((ev, z))
        self.zones += flips
        for m in range(1, min(self.mmax, i - 1) + 1):
            A, B = self._bars[-(m + 2)], self._bars[-1]
            mids = list(self._bars)[-(m + 1):-1]
            for d, lo, hi, burst in (
                (1, A[0], B[1], all(x[2] > A[0] for x in mids)),
                (-1, B[0], A[1], all(x[2] < A[1] for x in mids)),
            ):
                if burst and hi > lo:
                    self._keep(d, lo, hi, i - m - 1, i, ts)
        return events

    def _keep(self, d, lo, hi, a, b, ts) -> None:
        if self.min_gap and self.tape.atr and (hi - lo) < self.min_gap * self.tape.atr:
            return                                       # sub-size gap -> not a taught FVG
        # dedup (ts2_lib.fvg_n_extra): a fragment overlapping an existing live
        # same-dir FVG in window AND band.
        for z in self.zones:
            if not (z.alive and z.kind == "FVG" and z.dir == d
                    and a <= z.b and z.a <= b           # window overlap
                    and min(hi, z.hi) > max(lo, z.lo)):  # band overlap
                continue
            if not self.merge_chain:
                return                                   # keep-first, box never grows
            # MERGE: the trader draws one region where consecutive displacement
            # candles each leave a gap -- "these gaps can be 3 candle or multiples
            # means broder gap region". Keep-first splits that into adjacent
            # fragments, which is why hand-drawn boxes matched on one edge and fell
            # ~5 pts short on the other (23 Jun bottom exact/top short, 07 May top
            # exact/bottom short). Grow the existing box to the union instead.
            # BOUNDED: each union pushes z.b forward, so an uncapped chain keeps
            # "overlapping in window" and runs away across a whole session -- the
            # 29 Jun box went from an exact 1148.0-1152.6 to a 19-point 1160.7-1180.0
            # region that way. A gap region is a consecutive displacement RUN, so cap
            # the merged span; beyond that it is a different move.
            if max(b, z.b) - min(a, z.a) > self.merge_max_bars:
                return                                   # too far apart: keep-first
            z.lo, z.hi = min(z.lo, lo), max(z.hi, hi)
            z.a, z.b = min(z.a, a), max(z.b, b)
            return
        self.zones.append(Zone("FVG", d, lo, hi, ts, a, b))


@register
class FvgNDetector(Detector):
    name = "fvg_n"

    def __init__(self, params: dict):
        super().__init__({**_DEFAULTS, **params})
        self._z = FvgZones(int(self.params["mmax"]),
                           Decimal(str(self.params["depth_atr"])),
                           Decimal(str(self.params["min_gap_atr"])))
        self._z.merge_chain = bool(self.params["merge_chain"])
        if int(self.params["merge_max_bars"]):
            self._z.merge_max_bars = int(self.params["merge_max_bars"])
        self._n = 0

    def on_session_end(self) -> None:
        self._z.zones = [z for z in self._z.zones if z.alive]  # memory bound

    def detect(self, ctx: StockContext) -> list[Evidence]:
        tf = Timeframe(self.params["tf"])
        window = ctx.candles.last(_ALL, tf)
        out: list[Evidence] = []
        for i in range(self._n, len(window)):
            c = window[i]
            events = self._z.step(c.ts, c.open, c.high, c.low, c.close)
            if i == len(window) - 1:
                out = [self._evidence(ctx, tf, z)
                       for ev, z in events if ev == "retest"]
        self._n = len(window)
        return out

    def _evidence(self, ctx: StockContext, tf: Timeframe, z: Zone) -> Evidence:
        atr = ctx.atr(tf)
        floor = Decimal(str(self.params["sl_atr_floor"])) * atr if atr else Decimal(0)
        up = z.dir == 1
        return Evidence(
            detector=self.name,
            direction=Direction.LONG if up else Direction.SHORT,
            strength=0.6, zone=(z.lo, z.hi), ts=ctx.now, ttl_candles=6,
            # ts is ctx.now -- when this evidence last RE-FIRED, which can be days
            # after the gap formed. A gap is drawn from its own candles rightward
            # until price returns, so the birth bar and the span are what a consumer
            # actually needs; carry them explicitly.
            meta={"event": _EVENT[z.kind], "sl": str(z.lo if up else z.hi),
                  "sl_floor": str(floor), "born": z.born.isoformat(),
                  "span": int(z.b - z.a) + 1, "tf": tf.value})
