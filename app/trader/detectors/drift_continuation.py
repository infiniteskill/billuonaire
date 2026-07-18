"""Drift-continuation detector ("drift_continuation"): the missed-class
coverage fix from the recall audit (runs/long60/RECALL.md Table C /
dev/plan/artifacts/recall-audit.md). 58% of trend-continuation run-starts
are invisible to the 7 pullback/reversion-shaped v2 tools; the missed runs'
measured profile: already drifting in-direction (+0.24 ATR 6-bar pre-drift
vs -0.28 for caught runs), starting HIGH in the recent range (-1.35 vs
-1.96 ATR below the 6-bar extreme), 2.75x more often fresh 12-bar
breakouts, volume-neutral. This detector fires on exactly that quiet
continuation shape:

  - 6-bar drift >= drift_min_atr*ATR in direction d (close[now]-close[now-6])
  - close within ext_prox_atr*ATR of the prior 12-bar extreme in d
    (near the highs for LONG; a break of it trivially qualifies)
  - NO cross-bar adverse leg >= adverse_max_atr*ATR inside the last 6 bars
    (a prior bar's favorable extreme to a later bar's adverse extreme --
    shallow/no pullback; deep pullbacks are the existing tools' turf)
  - strength scales with drift magnitude, +0.25 bonus when the close is a
    fresh 12-bar breakout (beyond the prior extreme).

Pure signal-emitter (no Levels), entry = close of the just-closed bar,
sl = the recent 6-bar adverse extreme (min low for LONG / max high for
SHORT); the 0.15*ATR SL floor is annotated (meta["sl_floor"]) for the
executor -- same meta contract as compression_fade. All thresholds are in
ATR units, so no ATR (warmup) => no signal.

CONTINUUM: the window is ``ctx.candles.last(N)`` -- continuous multi-day
history, never session-scoped. Per-tick dedupe is by closed-bar ts;
on_session_end prunes the dedupe set only (keeps the newest ts, since only
the still-current closed bar can recur across the boundary).

NOT enabled in any config: a coverage instrument for the recall gap, not a
validated edge (RECALL.md verdict 4 -- the binding constraint is post-cost
extraction, not signal coverage)."""

from __future__ import annotations

from decimal import Decimal

from trader.detectors.base import Detector, register
from trader.engine.context import StockContext
from trader.models.candle import Timeframe
from trader.models.evidence import Direction, Evidence

_DEFAULTS = {"tf": "5m", "drift_bars": 6, "ext_bars": 12,
             "drift_min_atr": 0.5, "ext_prox_atr": 0.65,
             "adverse_max_atr": 0.75, "zone_atr": 0.1, "sl_atr_floor": 0.15}


@register
class DriftContinuationDetector(Detector):
    name = "drift_continuation"

    def __init__(self, params: dict):
        super().__init__({**_DEFAULTS, **params})
        self._emitted: set = set()   # closed-bar ts already fired

    def on_session_end(self) -> None:
        # ts-keyed continuum dedupe: only the newest ts can still be the
        # just-closed bar after the boundary, so keeping it alone is safe.
        self._emitted = set(sorted(self._emitted)[-1:])

    def detect(self, ctx: StockContext) -> list[Evidence]:
        p = self.params
        tf = Timeframe(p["tf"])
        n, db = int(p["ext_bars"]) + 1, int(p["drift_bars"])
        w = ctx.candles.last(n, tf)
        atr = ctx.atr(tf)
        if len(w) < n or not atr or (j := w[-1]).ts in self._emitted:
            return []
        a = float(atr)
        drift = float(j.close - w[-db - 1].close) / a
        if abs(drift) < float(p["drift_min_atr"]):
            return []
        d = Direction.LONG if drift > 0 else Direction.SHORT
        prior, tail, sgn = w[:-1], w[-db:], drift > 0
        ext = max(c.high for c in prior) if sgn else min(c.low for c in prior)
        if float(ext - j.close if sgn else j.close - ext) / a > float(p["ext_prox_atr"]):
            return []
        run, leg = None, 0.0   # cross-bar pullback: prior extreme -> later bar
        for c in tail:
            if run is not None:
                leg = max(leg, run - float(c.low) if sgn else float(c.high) - run)
            e = float(c.high if sgn else c.low)
            run = e if run is None else (max(run, e) if sgn else min(run, e))
        if leg >= float(p["adverse_max_atr"]) * a:
            return []
        self._emitted.add(j.ts)
        fresh = j.close > ext if sgn else j.close < ext
        s = min(1.0, max(0.0, min(0.75, (abs(drift) - float(p["drift_min_atr"])) / 2))
                + (0.25 if fresh else 0.0))
        sl = min(c.low for c in tail) if sgn else max(c.high for c in tail)
        band = Decimal(str(p["zone_atr"])) * atr
        meta = {"event": "DRIFT_CONT", "sl": str(sl),
                "sl_floor": str(Decimal(str(p["sl_atr_floor"])) * atr)}
        return [Evidence(detector=self.name, direction=d, strength=s,
                         zone=(j.close - band, j.close + band), ts=ctx.now,
                         ttl_candles=3, meta=meta)]
