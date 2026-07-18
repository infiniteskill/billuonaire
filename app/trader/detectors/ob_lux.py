"""ob_lux detector ("ob_lux"): the validated LuxAlgo internal Order Block,
ported faithfully from the measured winner (scratchpad luxob.py). A swing
pivot high/low is confirmed once ``size`` trailing bars fail to exceed it; a
later close crossing back over that pivot level is a structure break. The OB
is the bar within [pivot, break] with the lowest (bull) / highest (bear)
"parsed" extreme, where a bar whose range >= ``hv_atr_mult`` * THAT BAR'S OWN
trailing ATR (per-bar, exactly ``atr_series``/``ctx.atr``'s formula,
maintained as a rolling TR(14) window -- NOT the single current
``ctx.atr(tf)``: a uniform "current" ATR would retroactively reclassify early
bars as ATR drifts and silently flip an already-decided anchor; the parity
gate caught that exact bug) has its high/low swapped first before the
argmin/argmax search picks
the anchor -- LuxAlgo's volatility-as-volume proxy (the validated rule has no
real volume term to port; a range-vs-ATR spike is untrusted as the true wick
and excluded from the leg-extreme search). The swap only steers which bar WINS
the search: the recorded zone is always the winning bar's own raw sorted
(low, high) -- swapping low/high cancels out under sorted(), so vol-adj
never changes zone geometry. Creates an OB_BULL/OB_BEAR Level born at the
winning bar's ts; mitigation is LevelEngine's job (as in ``orderblock``).

CONTINUUM + INCREMENTAL: consumes the FULL continuous closed-candle history
(``ctx.candles.last(_ALL, tf)``, the inducement.py sentinel) -- never
session-scoped -- stepping only NEWLY-closed bars (``self._n`` cursor +
persistent swing/ATR/parsed-extreme state, inducement.py's FSM pattern).
Every per-bar decision (hv swap, pivot, confirm, anchor) depends only on bars
<= that bar, so stepping is bit-for-bit the same run as rescanning from bar 0
every tick (the parity gate proves it on real data). That full pass is the
VALIDATED behavior: luxob.py::lux_ob_events ran one long multi-day series, so
swing/leg structure (and the OBs it derives) carries across days; a leg
starting day 1 may confirm day 2. ``_quality``/``_anchor`` persist across
sessions to match (bounded: keyed by level-id / leg indices, which are
absolute into the append-only history).

Quality = min(overshoot / ATR, 1.0), overshoot = how far the confirming
close broke past the pivot level. The source has no strength score of its
own (it is a boolean event detector for offline study); this is the port's
0..1 proxy for break conviction.

Evidence (ttl 6, strength = quality) is emitted when the latest closed
candle's close sits inside an ACTIVE/TESTED OB zone: OB_BULL -> LONG,
OB_BEAR -> SHORT. Overlapping same-kind OBs dedupe on creation, keeping the
higher quality one -- only against an ACTIVE rival; a TESTED/MITIGATED/etc.
level is never evicted."""

from __future__ import annotations

from collections import deque
from datetime import datetime
from decimal import Decimal

from trader.detectors.base import Detector, register
from trader.engine.context import StockContext
from trader.models.candle import Candle, Timeframe
from trader.models.evidence import Direction, Evidence
from trader.models.level import Level, LevelKind, LevelState

_DEFAULTS = {"tf": "5m", "size": 5, "hv_atr_mult": 2.0}
_LIVE = (LevelState.ACTIVE, LevelState.TESTED)
_OB_KINDS = (LevelKind.OB_BULL, LevelKind.OB_BEAR)
_ALL = 10 ** 9    # "all closed candles" sentinel for CandleView.last


@register
class ObLuxDetector(Detector):
    name = "ob_lux"

    def __init__(self, params: dict):
        super().__init__({**_DEFAULTS, **params})
        self._quality: dict[str, float] = {}          # level_id -> quality
        self._emitted: set[tuple[str, datetime]] = set()  # (level_id, ts)
        self._anchor: dict[tuple[int, int, bool], int] = {}  # (pivot_idx, confirm_idx, take_max) -> winning idx
        self._decided: set[str] = set()  # level_ids ever run through _upsert's create-or-reject decision
        self._size = int(self.params["size"])
        self._hv_mult = Decimal(str(self.params["hv_atr_mult"]))
        # Incremental scan state (continuum FSM, never session-reset): cursor
        # of consumed closed bars, per-bar parsed extremes, rolling TR(14)
        # window (per-bar trailing ATR), live swing-pivot state.
        self._n = 0
        self._pH: list[Decimal] = []; self._pL: list[Decimal] = []
        self._trs: deque[Decimal] = deque(maxlen=14); self._tr_sum = Decimal(0)
        self._swH = self._swL = None   # (level, pivot_idx) of the live pivot
        self._swHc = self._swLc = True  # confirmed flags (True = none pending)

    def on_session_end(self) -> None:
        # Continuum: _quality/_anchor/_decided describe levels/legs that carry
        # across days -- they PERSIST (bounded by their level-id / leg keys),
        # so carried zones keep their real quality (no 0.5 fallback) and an
        # overlap-evicted OB never comes back once its rival ages past ACTIVE
        # (_decided blocks it). Prune only the ts-keyed emit dedupe by age: an
        # old bar is never again the latest close, but day 1's last bar stays
        # it until day 2's first.
        if self._emitted:
            newest = max(ts for _, ts in self._emitted)
            self._emitted = {k for k in self._emitted if k[1] == newest}

    def detect(self, ctx: StockContext) -> list[Evidence]:
        tf = Timeframe(self.params["tf"])
        window = ctx.candles.last(_ALL, tf)  # full continuum (validated behavior)
        n = len(window)
        if n <= self._size:
            return []  # cursor untouched: these bars are consumed once n > size
        for i in range(self._n, n):
            self._step(ctx, tf, window, i)
        self._n = n
        return self._evidence(ctx, window[-1])

    def _step(self, ctx: StockContext, tf: Timeframe, window: list[Candle], i: int) -> None:
        """Consume the single newly-closed bar ``i``: extend the rolling-TR
        trailing ATR (``ctx.atr``'s exact formula: SMA of the last 14 TRs;
        None until 15 bars) and the parsed-extreme series, advance the
        swing-pivot state, upsert any OB this bar's close confirms. State
        after stepping 0..i is identical to a full rescan of 0..i."""
        c = window[i]
        if i:
            p = window[i - 1]
            tr = max(c.high - c.low, abs(c.high - p.close), abs(c.low - p.close))
            if len(self._trs) == self._trs.maxlen:
                self._tr_sum -= self._trs[0]
            self._trs.append(tr); self._tr_sum += tr
        atr = self._tr_sum / self._trs.maxlen if i >= self._trs.maxlen else None
        hv = atr is not None and c.high - c.low >= self._hv_mult * atr
        self._pH.append(c.low if hv else c.high)
        self._pL.append(c.high if hv else c.low)
        size = self._size
        if i >= size:
            p = i - size
            seg = window[p + 1:i + 1]
            if window[p].high > max(b.high for b in seg):
                self._swH, self._swHc = (window[p].high, p), False
            if window[p].low < min(b.low for b in seg):
                self._swL, self._swLc = (window[p].low, p), False
        C, Cp = c.close, window[i - 1].close if i else None
        if self._swH and not self._swHc and C > self._swH[0] and (i == 0 or Cp <= self._swH[0]):
            self._swHc = True
            idx = self._anchor_idx(self._swH[1], i, self._pL, False)  # decided once, never re-flips w/ ATR drift
            lo, hi = sorted((self._pL[idx], self._pH[idx]))
            self._upsert(ctx, window[idx].ts, tf, LevelKind.OB_BULL, lo, hi,
                        self._quality_of(C - self._swH[0], atr))
        if self._swL and not self._swLc and C < self._swL[0] and (i == 0 or Cp >= self._swL[0]):
            self._swLc = True
            idx = self._anchor_idx(self._swL[1], i, self._pH, True)
            lo, hi = sorted((self._pL[idx], self._pH[idx]))
            self._upsert(ctx, window[idx].ts, tf, LevelKind.OB_BEAR, lo, hi,
                        self._quality_of(self._swL[0] - C, atr))

    @staticmethod
    def _quality_of(overshoot: Decimal, atr: Decimal | None) -> float:
        """min(overshoot / ATR, 1.0); 0.5 fallback when the confirm bar has no
        ATR yet (bar index < period) -- matches the codebase's existing
        no-ATR-yet convention (e.g. carried-zone quality in pipeline.py)."""
        if atr is None or atr <= 0:
            return 0.5
        return min(float(overshoot / atr), 1.0)

    def _anchor_idx(self, pivot_idx: int, confirm_idx: int, arr: list, take_max: bool) -> int:
        key = (pivot_idx, confirm_idx, take_max)
        if key not in self._anchor:
            fn = max if take_max else min
            self._anchor[key] = fn(range(pivot_idx, confirm_idx + 1), key=lambda j: arr[j])
        return self._anchor[key]

    def _upsert(self, ctx: StockContext, born: datetime, tf: Timeframe,
                kind: LevelKind, lo: Decimal, hi: Decimal, q: float) -> None:
        level_id = f"{ctx.symbol}-{self.name}-{kind.name}-{tf.value}-{born.isoformat()}"
        if any(lv.id == level_id for lv in ctx.levels):
            self._quality[level_id] = q  # lazy re-derive after restart
            return
        # Already created-then-evicted (or rejected) once: a LATER confirm
        # event can anchor to this same bar + kind (identical level_id) --
        # without this guard, a level whose overlap-evicting rival later ages
        # off ACTIVE (mitigated/tested/evicted itself) would be silently
        # RECREATED, duplicating a zone the dedupe rule already resolved. The
        # reference's `obs` list has no such resurrection (append-only, one
        # entry per confirm event, ever) -- caught by the parity gate
        # (test_ob_lux.py).
        if level_id in self._decided:
            return
        self._decided.add(level_id)
        # Only an ACTIVE rival may be replaced -- a TESTED/MITIGATED/etc. level
        # carries real state (touches/history) and must survive an anchor-id
        # mismatch (e.g. a fresh instance rescanning under drifted ATR).
        rival = next((lv for lv in ctx.levels if lv.kind is kind
                      and lv.state is LevelState.ACTIVE
                      and lv.zone[0] <= hi and lo <= lv.zone[1]), None)
        if rival is not None:  # overlap: keep the higher quality OB
            if q <= self._quality.get(rival.id, 0.5):
                return
            ctx.levels.remove(rival)
            self._quality.pop(rival.id, None)
        self._quality[level_id] = q
        ctx.levels.append(Level(id=level_id, symbol=ctx.symbol, kind=kind,
                                zone=(lo, hi), born=born, tf=tf))

    def _evidence(self, ctx: StockContext, last: Candle) -> list[Evidence]:
        out = []
        for lv in ctx.levels:
            key = (lv.id, last.ts)
            if (lv.kind not in _OB_KINDS or lv.state not in _LIVE
                    or not lv.zone[0] <= last.close <= lv.zone[1]
                    or key in self._emitted):
                continue
            self._emitted.add(key)
            out.append(Evidence(
                detector=self.name,
                direction=Direction.LONG if lv.kind is LevelKind.OB_BULL
                else Direction.SHORT,
                strength=self._quality.get(lv.id, 0.5), zone=lv.zone, ts=ctx.now,
                ttl_candles=6, meta={"level_id": lv.id, "event": "OB_RETEST"},
            ))
        return out
