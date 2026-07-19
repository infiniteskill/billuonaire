"""Extremes detector ("extremes"): EXTREME-SWING structure anchors.

Port of the validated research prototype (dev/research/ext_zigzag.py +
dev/research/tune_lib.py; frozen config runs/taught/TUNE.md; taught lessons
1 + 13 in dev/plan/30-LESSONS.md):

- Percent-leg zigzag: a pivot is valid only when leg_in AND leg_out each
  reach the leg floor -- ``leg_pct`` percent of price, default 6.0 (TUNE
  frozen; 4.7 is the taught fallback). Realized exactly as research sym_K:
  threshold K*ATR(14, Wilder) with K = clip(leg_pct / median(ATR/close),
  3, 14).
- Alternation enforced (never two same-side pivots in a row): a
  higher-high/lower-low before the reversal leg completes REPLACES the
  pending pivot -- the deepest extreme wins.
- Confirmation is LATE by nature: a pivot exists only once the reversal leg
  from its extreme reaches the floor. detect() recomputes the causal zigzag
  over all CLOSED candles each tick; the batch state at ``now`` equals the
  incremental state, so nothing is emitted before its confirm bar.
- Pivot band (lesson 13, wick-beyond-bodies): top band = highest open/close
  of the pivot cluster .. wick high, the cluster joining neighbours whose
  highs reach the running body top (bars bounded by neighbour pivots and
  the confirm bar -- causal); mirror at lows.
- Rank (meta): rank_atr = min(leg_in, leg_out) / ATR(pivot bar); master =
  the window max-high / min-low confirmed pivot so far, else major.

Infrastructure detector like swings.py: writes EXT_H/EXT_L Levels onto
``ctx.levels`` (born = pivot bar ts, zone = wick band) and always returns
[]. A previously emitted pivot whose id disappears from the recompute
(replaced by a deeper extreme) is marked DEAD.
"""

from __future__ import annotations

from dataclasses import dataclass

from trader.detectors.base import Detector, register
from trader.engine.context import StockContext
from trader.models.candle import Timeframe
from trader.models.evidence import Evidence
from trader.models.level import TERMINAL, Level, LevelKind, LevelState

_DEFAULT_LEG_PCT = 6.0            # TUNE frozen floor; 4.7 = taught fallback
_DEFAULT_TIMEFRAMES = ("1h",)     # store derives M5/M15/H1/D1; no 30m exists
_ATR_PERIOD = 14
_ALL = 10 ** 9
_KIND = {"H": LevelKind.EXT_H, "L": LevelKind.EXT_L}
_EXT = frozenset(_KIND.values())


@dataclass
class _Piv:
    idx: int
    price: float
    side: str                     # "H" | "L"
    confirm_idx: int | None = None
    boundary: bool = False        # leg_in truncated by window start
    pending: bool = False         # reversal leg not yet at the floor


def _wilder_atr(h, l, c, n=_ATR_PERIOD):
    """ATR(n), Wilder smoothing, warm-up backfilled (research verbatim)."""
    tr = [h[0] - l[0]] + [max(h[i] - l[i], abs(h[i] - c[i - 1]),
                              abs(l[i] - c[i - 1])) for i in range(1, len(h))]
    if len(tr) < n:
        return None
    a = sum(tr[:n]) / n
    atr = [a] * n
    for t in tr[n:]:
        a = (a * (n - 1) + t) / n
        atr.append(a)
    return atr


def _leg_K(atr, c, pct):
    """K = clip(pct / median(ATR/close), 3, 14) -- research sym_K verbatim."""
    r = sorted(a / x for a, x in zip(atr, c) if x > 0)
    if not r:
        return 6.0
    m = len(r) // 2
    med = r[m] if len(r) % 2 else (r[m - 1] + r[m]) / 2
    return min(max(pct / med, 3.0), 14.0) if med > 0 else 6.0


def _zigzag(h, l, k):
    """Causal leg-floor zigzag (ext_zigzag.zigzag + tob_lib guard, kept in
    the validated two-branch shape): pivot confirmed when the reversal leg
    reaches k[i]; alternation with replacement of the unconfirmed pivot."""
    n = len(h)
    piv: list[_Piv] = []
    imax = imin = 0
    i, state, pend = 1, None, 0
    while i < n:                  # init: first leg from the running extremes
        if h[i] > h[imax]:
            imax = i
        if l[i] < l[imin]:
            imin = i
        if h[i] - l[imin] >= k[i] and imin < i:
            piv.append(_Piv(imin, l[imin], "L", confirm_idx=i, boundary=True))
            state, j0 = "up", imin + 1
            pend = max(range(j0, i + 1), key=h.__getitem__) if j0 <= i else i
            break
        if h[imax] - l[i] >= k[i] and imax < i:
            piv.append(_Piv(imax, h[imax], "H", confirm_idx=i, boundary=True))
            state, j0 = "down", imax + 1
            pend = min(range(j0, i + 1), key=l.__getitem__) if j0 <= i else i
            break
        i += 1
    if state is None:
        return []
    last, last_conf = piv[-1], True
    i += 1
    while i < n:
        if state == "up":         # last pivot LOW; pend = running HIGH
            if h[i] > h[pend]:
                pend = i
            if l[i] < last.price:     # lower low before the HIGH confirms
                if h[pend] - l[i] >= k[i] and pend > last.idx:
                    p = _Piv(pend, h[pend], "H", confirm_idx=i)
                    piv.append(p)
                    last, last_conf, state, pend = p, True, "down", i
                else:                 # replacement: LOW moves to the deeper low
                    last.idx, last.price, last.confirm_idx = i, l[i], None
                    last_conf, pend = False, i
            else:
                if not last_conf and h[i] - last.price >= k[i]:
                    last.confirm_idx, last_conf = i, True
                if h[pend] - l[i] >= k[i] and pend > last.idx:
                    p = _Piv(pend, h[pend], "H", confirm_idx=i)
                    piv.append(p)
                    last, last_conf, state = p, True, "down"
                    j0 = pend + 1
                    pend = min(range(j0, i + 1), key=l.__getitem__) if j0 <= i else i
        else:                     # mirror: last pivot HIGH; pend = running LOW
            if l[i] < l[pend]:
                pend = i
            if h[i] > last.price:
                if h[i] - l[pend] >= k[i] and pend > last.idx:
                    p = _Piv(pend, l[pend], "L", confirm_idx=i)
                    piv.append(p)
                    last, last_conf, state, pend = p, True, "up", i
                else:
                    last.idx, last.price, last.confirm_idx = i, h[i], None
                    last_conf, pend = False, i
            else:
                if not last_conf and last.price - l[i] >= k[i]:
                    last.confirm_idx, last_conf = i, True
                if h[i] - l[pend] >= k[i] and pend > last.idx:
                    p = _Piv(pend, l[pend], "L", confirm_idx=i)
                    piv.append(p)
                    last, last_conf, state = p, True, "up"
                    j0 = pend + 1
                    pend = max(range(j0, i + 1), key=h.__getitem__) if j0 <= i else i
        i += 1
    if pend > last.idx:           # trailing running extreme: leg_out incomplete
        piv.append(_Piv(pend, h[pend] if state == "up" else l[pend],
                        "H" if state == "up" else "L", pending=True))
    for p in piv:
        if p.confirm_idx is None and not p.pending:
            p.pending = True
    return piv


def _band(o, h, l, c, piv, j):
    """Lesson-13 wick-beyond-bodies band (tune_lib band_zones mode='wick'):
    cluster joins neighbours whose extreme reaches the running body edge,
    bounded by neighbour pivots and the confirm bar (causal)."""
    p = piv[j]
    lo_b = piv[j - 1].idx if j else 0
    hi_b = min(piv[j + 1].idx if j < len(piv) - 1 else len(c) - 1, p.confirm_idx)
    s = e = p.idx
    if p.side == "H":
        bt = max(o[p.idx], c[p.idx])
        while s - 1 > lo_b and h[s - 1] >= bt:
            s -= 1
            bt = max(bt, o[s], c[s])
        while e + 1 < hi_b and h[e + 1] >= bt:
            e += 1
            bt = max(bt, o[e], c[e])
        return bt, p.price
    bt = min(o[p.idx], c[p.idx])
    while s - 1 > lo_b and l[s - 1] <= bt:
        s -= 1
        bt = min(bt, o[s], c[s])
    while e + 1 < hi_b and l[e + 1] <= bt:
        e += 1
        bt = min(bt, o[e], c[e])
    return p.price, bt


@register
class ExtremesDetector(Detector):
    name = "extremes"

    def detect(self, ctx: StockContext) -> list[Evidence]:
        pct = float(self.params.get("leg_pct", _DEFAULT_LEG_PCT)) / 100.0
        for tf_value in self.params.get("timeframes", _DEFAULT_TIMEFRAMES):
            tf = Timeframe(tf_value)
            candles = ctx.candles.last(_ALL, tf)
            if len(candles) > _ATR_PERIOD:
                self._sync(ctx, tf, candles, pct)
        return []  # always -- infrastructure detector, no Evidence

    def _sync(self, ctx: StockContext, tf: Timeframe, candles, pct) -> None:
        o, h, l, c = ([float(getattr(cd, f)) for cd in candles]
                      for f in ("open", "high", "low", "close"))
        atr = _wilder_atr(h, l, c)
        K = _leg_K(atr, c, pct)
        piv = _zigzag(h, l, [K * a for a in atr])
        conf = [p for p in piv if p.confirm_idx is not None]
        highs = [p for p in conf if p.side == "H"]
        lows = [p for p in conf if p.side == "L"]
        masters = {id(max(highs, key=lambda p: p.price)) if highs else None,
                   id(min(lows, key=lambda p: p.price)) if lows else None}
        n = len(c)
        seen = set()
        by_id = {lv.id: lv for lv in ctx.levels}
        for j, p in enumerate(piv):
            if p.confirm_idx is None:
                continue
            leg_in = abs(p.price - piv[j - 1].price) if j else None
            if j < len(piv) - 1:          # next pivot may be the trailing extreme
                leg_out = abs(piv[j + 1].price - p.price)
            elif p.idx + 1 < n:           # to the running extreme at window end
                leg_out = (p.price - min(l[p.idx + 1:]) if p.side == "H"
                           else max(h[p.idx + 1:]) - p.price)
            else:
                leg_out = None
            legs = [x for x in (leg_in, leg_out) if x is not None]
            kind = _KIND[p.side]
            born = candles[p.idx].ts
            lid = f"{ctx.symbol}-{kind.name}-{tf.value}-{born.isoformat()}"
            seen.add(lid)
            lo_z, hi_z = _band(o, h, l, c, piv, j)
            zone = (ctx.spec.quantize(lo_z), ctx.spec.quantize(hi_z))
            meta = {"rank_atr": min(legs) / atr[p.idx] if legs else None,
                    "master": id(p) in masters, "leg_in": leg_in,
                    "leg_out": leg_out, "boundary": p.boundary}
            if lv := by_id.get(lid):      # live anchor: band/rank/master evolve
                lv.zone = zone
                lv.meta.update(meta)
            else:
                ctx.levels.append(Level(id=lid, symbol=ctx.symbol, kind=kind,
                                        zone=zone, born=born, tf=tf, meta=meta))
        for lv in ctx.levels:             # replaced pivot: id vanished -> retract
            if (lv.kind in _EXT and lv.tf is tf and lv.id not in seen
                    and lv.state not in TERMINAL and lv.born >= candles[0].ts):
                lv.record_state(ctx.now, LevelState.DEAD)
