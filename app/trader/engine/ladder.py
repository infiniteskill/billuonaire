"""Ladder gate: the research-validated elimination ladder (runs/long60/
FACTS.md) grading the OB/FVG zone behind a signal. Rungs are cumulative:

  1  prior-session, first touch: the zone was born on an EARLIER session
     (born_session == Level.born.date(), the idiom _carry_over already uses)
     AND the touch firing the signal is its first -- no level transition
     recorded before the current bar (levels lifecycle: state was ACTIVE).
  2  +H1 nested: the zone band overlaps a LIVE same-direction H1 zone.
     H1 FVG: 3-candle wick gap (bull c3.low > c1.high, bear mirrored).
     H1 OB: simplified LuxAlgo (ob_lux.py) -- a swing pivot confirmed by
     ``SIZE`` trailing bars failing to exceed it, a close crossing back over
     it anchors the OB at the leg's extreme bar. Documented simplifications
     vs ob_lux: no volatility high/low swap, no quality score, no overlap
     dedupe -- rung 2 only needs zone geometry. An H1 zone dies when a later
     H1 close crosses beyond its far edge, or at 5 weekday sessions of age.
  3  +sweep-aligned: the zone was born within ``SWEEP_BARS`` M5 bars after an
     aligned EQ-pool sweep. Fractal swings 5-left/5-right on M5; pool = >=2
     same-side swings within 0.25 x ATR(14, M5); sweep = wick beyond the pool
     extreme with close back inside (pool consumed; a CLOSE beyond instead
     breaks the pool). Highs-sweep aligns bear zones, lows-sweep bull zones.

Self-contained by design: liquidity.py's EQH/EQL pools cluster by relative
pct tolerance over config-strength swings and only exist when those
detectors are enabled -- the measured ladder definition must hold regardless
of detector config, so the trackers here own their state. Incremental
cursors over the full closed-candle continuum (ob_lux.py pattern): every
per-bar decision depends only on bars <= it, so a restart that re-feeds the
store rebuilds this state identically. Detachable: the pipeline constructs a
Ladder only when settings.ladder.enabled; disabled = pre-ladder behavior."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from trader.models.candle import Timeframe
from trader.models.evidence import Direction
from trader.models.level import TERMINAL, Level, LevelKind

_ALL = 10 ** 9    # "all closed candles" sentinel for CandleView.last
_M5 = timedelta(minutes=5)
_BULL = frozenset({LevelKind.OB_BULL, LevelKind.FVG_BULL})
_BEAR = frozenset({LevelKind.OB_BEAR, LevelKind.FVG_BEAR})


def sessions_old(born, ref) -> int:
    """Weekday sessions strictly after ``born`` up to ``ref`` (holiday-blind:
    an NSE holiday counts as a session, so a stale zone prunes a touch early
    -- conservative, and stateless across restarts)."""
    if ref is None or ref <= born:
        return 0
    return sum((born + timedelta(days=i)).weekday() < 5
               for i in range(1, (ref - born).days + 1))


@dataclass
class H1Zone:
    lo: Decimal
    hi: Decimal
    bull: bool
    born: datetime


class Ladder:
    """Per-symbol rung state: H1-zone tracker + M5 EQ-pool sweep tracker.
    ``update(ctx)`` once per closed M5 bar; ``grade`` at gate time."""

    MAX_AGE = 5                   # H1 zone age cap, weekday sessions
    SIZE = 5                      # fractal / pivot arm: 5-left/5-right
    EQ_ATR = Decimal("0.25")      # pool tolerance x ATR(14, M5)
    SWEEP_BARS = 3                # zone born <= this many M5 bars after sweep

    def __init__(self):
        self.h1_zones: list[H1Zone] = []
        self.sweeps: list[tuple[datetime, bool]] = []   # (bar ts, swept highs?)
        self.swing_hi: list[Decimal] = []               # confirmed fractal swings
        self.swing_lo: list[Decimal] = []
        self._h1_n = self._m5_n = 0                     # consumed-bar cursors
        self._swH = self._swL = None                    # live H1 pivot (price, idx)
        self._swHc = self._swLc = True                  # confirmed (none pending)
        self._trs: deque[Decimal] = deque(maxlen=14)    # rolling M5 TR window
        self._tr_sum = Decimal(0)

    # ------------------------------------------------------------- update

    def update(self, ctx) -> None:
        h1 = ctx.candles.last(_ALL, Timeframe.H1)
        for i in range(self._h1_n, len(h1)):
            self._h1_bar(h1, i)
        self._h1_n = len(h1)
        m5 = ctx.candles.last(_ALL, Timeframe.M5)
        for i in range(self._m5_n, len(m5)):
            self._m5_bar(m5, i)
        self._m5_n = len(m5)
        sd = ctx.day.session_date
        self.h1_zones = [z for z in self.h1_zones
                         if sessions_old(z.born.date(), sd) < self.MAX_AGE]
        self.sweeps = [s for s in self.sweeps
                       if sessions_old(s[0].date(), sd) <= self.MAX_AGE]

    def _h1_bar(self, h1, i) -> None:
        c = h1[i]
        self.h1_zones = [z for z in self.h1_zones      # far-edge close kill
                         if not (c.close < z.lo if z.bull else c.close > z.hi)]
        if i >= 2:                                     # 3-candle wick-valid FVG
            c1 = h1[i - 2]
            if c.low > c1.high:
                self.h1_zones.append(H1Zone(c1.high, c.low, True, c.ts))
            if c.high < c1.low:
                self.h1_zones.append(H1Zone(c.high, c1.low, False, c.ts))
        if i >= self.SIZE:                             # pivot arm (trailing fail)
            p = i - self.SIZE
            seg = h1[p + 1:i + 1]
            if h1[p].high > max(b.high for b in seg):
                self._swH, self._swHc = (h1[p].high, p), False
            if h1[p].low < min(b.low for b in seg):
                self._swL, self._swLc = (h1[p].low, p), False
        C, Cp = c.close, h1[i - 1].close if i else None
        if (self._swH and not self._swHc and C > self._swH[0]
                and (Cp is None or Cp <= self._swH[0])):
            self._swHc = True                          # bull OB: leg's lowest bar
            j = min(range(self._swH[1], i + 1), key=lambda k: h1[k].low)
            self.h1_zones.append(H1Zone(h1[j].low, h1[j].high, True, h1[j].ts))
        if (self._swL and not self._swLc and C < self._swL[0]
                and (Cp is None or Cp >= self._swL[0])):
            self._swLc = True                          # bear OB: leg's highest bar
            j = max(range(self._swL[1], i + 1), key=lambda k: h1[k].high)
            self.h1_zones.append(H1Zone(h1[j].low, h1[j].high, False, h1[j].ts))

    def _m5_bar(self, m5, i) -> None:
        c = m5[i]
        if i:                                          # rolling TR(14) -> ATR
            p = m5[i - 1]
            tr = max(c.high - c.low, abs(c.high - p.close), abs(c.low - p.close))
            if len(self._trs) == self._trs.maxlen:
                self._tr_sum -= self._trs[0]
            self._trs.append(tr)
            self._tr_sum += tr
        j = i - self.SIZE                              # fractal confirm at j
        if j >= self.SIZE:
            win = m5[j - self.SIZE:j] + m5[j + 1:i + 1]
            if all(m5[j].high > b.high for b in win):
                self.swing_hi.append(m5[j].high)
            if all(m5[j].low < b.low for b in win):
                self.swing_lo.append(m5[j].low)
        if len(self._trs) == self._trs.maxlen:
            atr = self._tr_sum / self._trs.maxlen
            self._sweep_side(self.swing_hi, c, atr, True)
            self._sweep_side(self.swing_lo, c, atr, False)
        self.swing_hi[:] = [v for v in self.swing_hi if v >= c.close][-30:]
        self.swing_lo[:] = [v for v in self.swing_lo if v <= c.close][-30:]

    def _sweep_side(self, swings, c, atr, highs: bool) -> None:
        tol = self.EQ_ATR * atr
        groups, cur = [], []                           # anchor-chain clustering
        for v in sorted(swings):                       # (liquidity._create_eq)
            if cur and v - cur[0] <= tol:
                cur.append(v)
            else:
                if len(cur) >= 2:
                    groups.append(cur)
                cur = [v]
        if len(cur) >= 2:
            groups.append(cur)
        for g in groups:
            ext = max(g) if highs else min(g)
            if (c.high > ext and c.close < ext) if highs \
                    else (c.low < ext and c.close > ext):
                self.sweeps.append((c.ts, highs))      # wick beyond, close back
                for v in g:
                    swings.remove(v)                   # pool consumed

    # -------------------------------------------------------------- grade

    def grade(self, ctx, direction: Direction, cluster) -> int:
        """Best rung among live same-direction OB/FVG zone levels overlapping
        the scoring cluster; 0 when none backs it (non-zone signals have no
        ladder grade)."""
        kinds = _BULL if direction is Direction.LONG else _BEAR
        last = ctx.candles.last(1, Timeframe.M5) if ctx.candles else []
        bar = last[-1].ts if last else ctx.now         # transitions AT bar = this touch
        cands = [lv for lv in ctx.levels
                 if lv.kind in kinds and lv.state not in TERMINAL
                 and min(lv.zone) <= max(cluster) and min(cluster) <= max(lv.zone)]
        return max((self._rung(lv, ctx.day.session_date, bar) for lv in cands),
                   default=0)

    def _rung(self, lv: Level, session, bar: datetime) -> int:
        if (lv.born.date() >= session
                or any(ts < bar for ts, _ in lv.state_history)):
            return 0                                   # born today / already retested
        bull = lv.kind in _BULL
        if not any(z.bull is bull and z.lo <= max(lv.zone)
                   and min(lv.zone) <= z.hi for z in self.h1_zones):
            return 1
        if any(hs is not bull and timedelta(0) <= lv.born - ts
               <= self.SWEEP_BARS * _M5 for ts, hs in self.sweeps):
            return 3                                   # highs->bear, lows->bull
        return 2
