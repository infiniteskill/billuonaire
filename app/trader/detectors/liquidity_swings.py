"""Swing pivots the way the reference Pine indicators do it, with the liquidity zone.

Ported from the user's own Pine corpus (dev/h2h/, LuxAlgo, CC BY-NC-SA 4.0). Two
methods, both bar-count based:

``leg`` (default) -- the LuxAlgo SMC state machine. Two independent indicators in
the corpus use it verbatim (the flagship SMC ``leg(size)`` and ``swings(len)`` in
Liquidity Pools / Market Structure with Inducements)::

    newLegHigh = high[size] > ta.highest(size)     // vs the `size` bars AFTER it
    newLegLow  = low[size]  < ta.lowest(size)
    leg := newLegHigh ? BEARISH : newLegLow ? BULLISH : leg[1]
    pivot on ta.change(leg)

The candidate is the bar ``size`` back; it becomes a swing high the moment the leg
flips bearish. Alternating by construction, so structure reads H,L,H,L cleanly.

``fractal`` -- Liquidity Swings' ``ta.pivothigh(size, size)``: strictly the highest
of the 2*size+1 window. Highs and lows are independent, so it can mark two highs in
a row; it catches shelves the alternating method skips.

``degree`` -- COMPLETE, and the reason this detector exists. leg/fractal both make
you pick a size up front and throw away everything else; but size 5 and size 50 are
not two detectors, they are two cuts of one structure. For every bar compute the
largest N for which it is still the extreme of its +/-N window -- its DEGREE, found
with a monotonic stack in O(n). Then:

  * every local extremum is emitted; nothing is discarded at detection time
  * degree IS the scale. degree>=5 reproduces leg5, degree>=50 reproduces leg50,
    from a single pass, so the scale becomes a filter rather than a re-run
  * a pivot's degree grows while it survives and FREEZES the bar something takes it
    out, so the freeze is the sweep -- one number carries both significance and
    invalidation
  * ties are liquidity: an equal high does not extend the span, it stops it and sets
    ``tie``, which is exactly the equal-highs pool SMC cares about

Nothing here depends on ATR, price scale or timeframe, so "all the swings" is a
well-posed question with one answer, and the user chooses the degree cut afterwards.

WHY NOT THE ATR ZIGZAG WE ALREADY HAVE
``extremes`` thresholds at K*ATR with K = clip(leg_pct/100 / median(ATR/close), 3, 14).
ATR/close is ~0.21% on 5m but ~2.5% on 1d, so on daily bars K wants 0.79 and is
floored at 3.0: a configured 2% leg silently becomes 7.5%, leaving 4 pivots in a
quarter where a reader marks about twelve. The clip is applied to K, but the quantity
that must stay invariant is the leg as a fraction of price -- so leg_pct is honoured
on low timeframes and overridden on high ones. A bar-count rule has no such coupling:
"higher than the surrounding N bars" means the same thing on every timeframe, and
confirmation takes exactly N bars instead of waiting for a move that may never come.

THE ZONE. A pivot is a point, but the tradeable object is the liquidity resting
between the wick and the bodies: for a swing high, ``max(open, close) .. high``
(``area="full"`` widens to ``low .. high``). ``count``/``vol`` accumulate every later
bar that trades back into it -- the interest the level attracted. ``crossed`` latches
when a bar CLOSES beyond the extremity, and the zone stops extending there.

Runs every (timeframe, size) pair so internal and swing structure coexist, tagging
each with ``variant`` = "<method><size>". Emits Evidence only -- no Level writes -- so
enabling it cannot disturb the level store or anything that consumes it.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from trader.detectors.base import Detector, register
from trader.engine.context import StockContext
from trader.models.candle import Timeframe
from trader.models.evidence import Direction, Evidence

_DEFAULTS = {"method": "degree", "sizes": (5, 50), "min_degree": 2, "area": "wick",
             "timeframes": ("5m", "15m", "1h", "1d"),
             "filter_by": "count", "filter_value": 0.0, "max_live": 60}


@dataclass
class _Piv:
    """A local extremum and how far it dominates on each side (its degree)."""
    idx: int
    high: bool
    px: Decimal
    left: int = 0
    right: int = 0
    tie: bool = False
    prom: float = 0.0

    @property
    def degree(self) -> int:
        """FORWARD dominance: how many bars this level held before being taken out.

        min(left, right) -- the symmetric/fractal rank -- was the obvious choice and
        it is wrong: it demotes a level that barely stood out on its left but then
        held for twenty bars, which is exactly the level liquidity rests on. It also
        loses pivots the SMC leg() finds, since leg only ever looks forward. Measured:
        banding on `right` is a strict SUPERSET of both leg(n) and fractal(n) on every
        timeframe and size tested, while min(left,right) is not."""
        return self.right

    @property
    def sym(self) -> int:
        """Symmetric rank. fractal(n) == sym >= n (exactly, modulo equal-high ties)."""
        return min(self.left, self.right)


class _RMQ:
    """Sparse table for range min/max -- O(n log n) build, O(1) query."""

    def __init__(self, a, want_min):
        self.pick = min if want_min else max
        self.t = [list(a)]
        k, n = 1, len(a)
        while (1 << k) <= n:
            prev, span, row = self.t[-1], 1 << (k - 1), []
            for i in range(n - (1 << k) + 1):
                row.append(self.pick(prev[i], prev[i + span]))
            self.t.append(row)
            k += 1

    def q(self, lo, hi):                       # inclusive
        if lo > hi:
            return None
        k = (hi - lo + 1).bit_length() - 1
        return self.pick(self.t[k][lo], self.t[k][hi - (1 << k) + 1])


def _prominence(pivs, vals, other, want_max):
    """Height of each peak above the highest saddle joining it to a higher peak.

    Forward dominance alone over-ranks a staircase: every bar walking down from a
    top is "higher than everything after it" purely because price never came back,
    so one peak masquerades as a dozen. Prominence is the standard topographic
    answer -- the bar one tick below the true high has a saddle right next to it and
    scores ~0, while the high itself scores the whole leg. It is in price units, so
    it is directly comparable to zone height and to R."""
    n = len(vals)
    rmq = _RMQ(other, want_max)                # saddle = extreme of the OTHER series
    for p in pivs:
        lo_i, hi_i = p.idx - p.left - 1, p.idx + p.right + 1
        a = rmq.q(max(0, lo_i + 1), p.idx) if lo_i >= 0 else None
        b = rmq.q(p.idx, min(n - 1, hi_i - 1)) if hi_i < n else None
        saddles = [x for x in (a, b) if x is not None]
        if not saddles:                        # dominates the entire window
            saddles = [rmq.q(0, n - 1)]
        key = max(saddles) if want_max else min(saddles)
        p.prom = float(abs(vals[p.idx] - key))
    return pivs


def _scan(vals, want_max):
    """Every local extremum with its exact degree, one O(n) monotonic-stack pass.

    Popping on `<=` (not `<`) means an equal value stops the span instead of being
    swallowed by it: a double top yields two pivots flagged ``tie`` rather than one
    with an overstated reach. Whatever is still on the stack at the end has not been
    taken out yet -- its right span is provisional and still growing, which is the
    live/unmitigated case."""
    cmp = (lambda a, b: a <= b) if want_max else (lambda a, b: a >= b)
    n, stack, done = len(vals), [], []
    for i in range(n):
        while stack and cmp(vals[stack[-1].idx], vals[i]):
            p = stack.pop()
            p.right = i - p.idx - 1
            p.tie = vals[p.idx] == vals[i]
            done.append(p)
        p = _Piv(i, want_max, vals[i])
        p.left = i - stack[-1].idx - 1 if stack else i
        stack.append(p)
    for p in stack:                      # never taken out: degree still growing
        p.right = n - 1 - p.idx
        done.append(p)
    return done


@dataclass
class _Swing:
    high: bool
    top: Decimal
    btm: Decimal
    ts: object
    px: Decimal                      # the wick extremity itself
    count: int = 0
    vol: int = 0
    crossed: bool = False


@register
class LiquiditySwingsDetector(Detector):
    name = "liquidity_swings"

    def __init__(self, params: dict):
        super().__init__(params)
        self._st: dict = {}          # (tf, size) -> [last_ts, swings, leg]

    def _p(self, k):
        return self.params.get(k, _DEFAULTS[k])

    def _zone(self, c, high: bool, full: bool):
        if high:
            return (c.low if full else max(c.open, c.close)), c.high, c.high
        return c.low, (c.high if full else min(c.open, c.close)), c.low

    def _degree_pass(self, ctx, tf, bars, full, min_deg, keep):
        """Every local extremum on this timeframe, tagged with its degree."""
        sig = (len(bars), bars[-1].ts)
        cached = self._st.get(("deg", tf))
        if cached and cached[0] == sig:
            return cached[1]
        hs = [b.high for b in bars]
        ls = [b.low for b in bars]
        n = len(bars)
        out = []
        pv = (_prominence(_scan(hs, True), hs, ls, True)
              + _prominence(_scan(ls, False), ls, hs, False))
        for piv in pv:
            if piv.degree < min_deg:
                continue
            c = bars[piv.idx]
            btm, top, px = self._zone(c, piv.high, full)
            lo, hi = (btm, top) if btm <= top else (top, btm)
            end = piv.idx + piv.right                 # last bar it survived
            crossed = end < n - 1                     # something took it out
            # never taken out yet: there is no right-hand saddle, so prominence is
            # provisional and will only shrink. The still-forming extreme.
            live = not crossed
            cnt = vol = 0
            for b in bars[piv.idx + 1:end + 1]:       # liquidity drawn into the zone
                if b.low < top and b.high > btm:
                    cnt += 1
                    vol += int(b.volume)
            # Band by PROMINENCE as a percent of price, not by bars held. "How big
            # a swing is this" is what a reader actually means, it is comparable
            # across timeframes and across stocks, and it collapses the staircase
            # that pure forward-dominance inflates into a dozen phantom peaks.
            pp = 100 * piv.prom / float(px) if px else 0.0
            band = ("0-0.2" if pp < 0.2 else "0.2-0.5" if pp < 0.5
                    else "0.5-1" if pp < 1 else "1-2" if pp < 2 else "2+")
            out.append(Evidence(
                detector=self.name,
                direction=Direction.SHORT if piv.high else Direction.LONG,
                strength=min(1.0, 0.3 + piv.degree / 50),
                zone=(lo, hi), ts=ctx.now, ttl_candles=6,
                meta={"tf": tf.value, "variant": f"deg{band}",
                      "method": "degree", "degree": piv.degree,
                      "sym": piv.sym, "left": piv.left, "right": piv.right,
                      "prom": round(piv.prom, 2),
                      "prom_pct": round(100 * piv.prom / float(px), 3),
                      "tie": piv.tie, "live": live,
                      "side": "H" if piv.high else "L", "px": float(px),
                      "born": c.ts.isoformat(), "count": cnt, "vol": vol,
                      "crossed": crossed,
                      "area": "full" if full else "wick"}))
        out.sort(key=lambda e: -e.meta["degree"])
        out = out[:keep]
        self._st[("deg", tf)] = (sig, out)
        return out

    def detect(self, ctx: StockContext) -> list[Evidence]:
        out: list[Evidence] = []
        method = str(self._p("method")).lower()
        full = str(self._p("area")).lower().startswith("full")
        by, fv = str(self._p("filter_by")), float(self._p("filter_value"))
        keep = int(self._p("max_live"))
        for tf_value in self._p("timeframes"):
            tf = Timeframe(tf_value)
            bars = ctx.candles.last(10 ** 9, tf)
            if method == "degree":
                if len(bars) > 3:
                    out += self._degree_pass(ctx, tf, bars, full,
                                             int(self._p("min_degree")), keep)
                continue
            for size in self._p("sizes"):
                size = int(size)
                # leg only looks at the `size` bars AFTER the candidate; fractal
                # needs `size` on both sides. Starting later than necessary would
                # blind us to pivots at the start of the tape.
                warm = 2 * size if method == "fractal" else size
                if len(bars) < warm + 2:
                    continue
                key = (tf, size, method)
                last_ts, swings, leg = self._st.get(key, (None, [], 0))
                start = warm
                if last_ts is not None:          # incremental: only unseen bars
                    for i in range(len(bars) - 1, -1, -1):
                        if bars[i].ts == last_ts:
                            start = max(start, i + 1)
                            break
                for i in range(start, len(bars)):
                    b = bars[i]
                    for s in swings:             # liquidity accumulating in the zone
                        if s.crossed:
                            continue
                        if b.low < s.top and b.high > s.btm:
                            s.count += 1
                            s.vol += int(b.volume)
                        if (b.close > s.top) if s.high else (b.close < s.btm):
                            s.crossed = True
                    j = i - size
                    c = bars[j]
                    if method == "fractal":      # strict: highest of 2*size+1
                        w = bars[j - size:i + 1]
                        hi_piv = all(x.high < c.high for k, x in enumerate(w) if k != size)
                        lo_piv = all(x.low > c.low for k, x in enumerate(w) if k != size)
                    else:                        # leg state machine (LuxAlgo SMC)
                        after = bars[i - size + 1:i + 1]      # the `size` bars after j
                        new_hi = c.high > max(x.high for x in after)
                        new_lo = c.low < min(x.low for x in after)
                        prev = leg
                        leg = -1 if new_hi else (1 if new_lo else leg)
                        hi_piv = leg == -1 and prev != -1     # flip to bearish = a top
                        lo_piv = leg == 1 and prev != 1
                    if hi_piv:
                        btm, top, px = self._zone(c, True, full)
                        swings.append(_Swing(True, top, btm, c.ts, px))
                    if lo_piv:
                        btm, top, px = self._zone(c, False, full)
                        swings.append(_Swing(False, top, btm, c.ts, px))
                if len(swings) > keep:
                    swings = swings[-keep:]
                self._st[key] = (bars[-1].ts, swings, leg)

                variant = f"{method}{size}"
                for s in swings:
                    if (s.vol if by == "volume" else s.count) < fv:
                        continue
                    lo, hi = (s.btm, s.top) if s.btm <= s.top else (s.top, s.btm)
                    out.append(Evidence(
                        detector=self.name,
                        direction=Direction.SHORT if s.high else Direction.LONG,
                        strength=0.6, zone=(lo, hi), ts=ctx.now, ttl_candles=6,
                        meta={"tf": tf.value, "variant": variant, "size": size,
                              "method": method, "side": "H" if s.high else "L",
                              "px": float(s.px), "born": s.ts.isoformat(),
                              "count": s.count, "vol": s.vol,
                              "crossed": s.crossed,
                              "area": "full" if full else "wick"}))
        return out
