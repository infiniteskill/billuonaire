"""Zone-graph grading: the TUNE frozen composite (runs/taught/TUNE.md) over
whatever zone Levels live in ctx.levels -- kinds matched by NAME prefix
(OB_/FVG_ today; IFVG/BRK/MIT/PRP/EXT_ when the rebuilt detectors land), so
this layer needs no change on merge.

zone_grade(ctx, direction, band) -> ZoneGrade of a signal band:
  nst          LIVE same-side zones from DIFFERENT birth structures
               overlapping the band (EXACT overlap, frozen). Same-birth
               dedup (TUNE user correction #2 -- fragments/children never
               inflate a stack): by lv.birth_id when the detector provides
               one (a propulsion child shares its parent_id), else by
               (kind, born) chain proximity <= 2 bars of the level's TF.
  parent_ok    every propulsion-type overlap resolves a LIVE parent level;
               orphans are anti-signal (ZONES P3: -13.3pp). Vacuously True.
  depth_alive  some backing zone not closed-through >= 0.5 x ATR beyond its
               far edge since birth (lv.depth_alive when provided, else M5
               closes) -- TUNE break-depth law, second-life t=10.
  pivot_dist   ATR gap to the nearest EXT_H/EXT_L extreme level. Journal
               component ONLY, never in g (grade refinement beyond
               deep-stack is partly overfit -- TUNE composite caveat).
  g            (nst >= 4) + parent_ok + depth_alive, 0..3 (frozen formula).

context_tags(ctx, direction): journal-only demoted laws, NO gating --
premium/discount position (gate falsified, STRUCT T2), minor->major CHoCH
sequencer proxy minor_ch_recent (STRUCT T5P; the engine's structure CHoCH is
minor-grade), PO3 small-body/big-wick signature on the last closed H1/D1
candle (TUNE overfit flag 1: body < 0.5, wick > 0.5 x range)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from trader.engine.ladder import sessions_old
from trader.models.candle import Timeframe
from trader.models.evidence import Direction
from trader.models.level import TERMINAL

_ALL = 10 ** 9
_M5 = timedelta(minutes=5)
_HALF = Decimal("0.5")
_ZONE_PRE = ("OB_", "FVG_", "IFVG", "BRK", "MIT", "PRP")


def _is_zone(k) -> bool: return k.name.startswith(_ZONE_PRE)
def _is_prp(k) -> bool: return k.name.startswith("PRP")
def _is_ext(k) -> bool: return k.name.startswith("EXT_")


def _side(k) -> Direction | None:
    return (Direction.LONG if "BULL" in k.name
            else Direction.SHORT if "BEAR" in k.name else None)


@dataclass(frozen=True)
class ZoneGrade:
    nst: int
    parent_ok: bool
    depth_alive: bool
    pivot_dist: float | None

    @property
    def g(self) -> int:                     # frozen TUNE composite, 0..3
        return (self.nst >= 4) + self.parent_ok + self.depth_alive

    def parts(self) -> dict:                # journal payload
        return {"nst": self.nst, "parent_ok": self.parent_ok,
                "depth_alive": self.depth_alive, "pivot_dist": self.pivot_dist}


def zone_grade(ctx, direction: Direction, band) -> ZoneGrade:
    zs = [z for z in ctx.levels
          if _is_zone(z.kind) and z.state not in TERMINAL
          and _side(z.kind) in (direction, None)
          and min(z.zone) <= max(band) and min(band) <= max(z.zone)]
    atr = ctx.atr(Timeframe.M5) if ctx.candles else None
    return ZoneGrade(
        _nst(zs),
        all(_parent_live(z, ctx.levels) for z in zs if _is_prp(z.kind)),
        any(_depth_alive(z, ctx, atr, direction) for z in zs),
        _pivot_dist(band, ctx.levels, atr))


def _same_birth(a, b) -> bool:
    if a.kind is not b.kind:
        return False
    if Timeframe.D1 in (a.tf, b.tf):
        return sessions_old(a.born.date(), b.born.date()) <= 2
    return b.born - a.born <= timedelta(minutes=2 * (b.tf or Timeframe.M5).minutes)


def _nst(zs) -> int:
    keys, prev, pkey = set(), None, None
    for z in sorted(zs, key=lambda x: (x.kind.name, x.born)):
        k = getattr(z, "birth_id", None) or (
            getattr(z, "parent_id", None) if _is_prp(z.kind) else None)
        if k is None:                       # chain: same kind within 2 bars
            k = pkey if prev is not None and _same_birth(prev, z) else z.id
            prev, pkey = z, k
        keys.add(k)
    return len(keys)


def _parent_live(z, levels) -> bool:
    pid = getattr(z, "parent_id", None)
    return any(p.id == pid and p.state not in TERMINAL for p in levels)


def _depth_alive(z, ctx, atr, direction) -> bool:
    if (own := getattr(z, "depth_alive", None)) is not None:
        return bool(own)
    if atr is None:
        return True                         # unmeasurable: no kill evidence
    up = (_side(z.kind) or direction) is not Direction.SHORT
    far = min(z.zone) if up else max(z.zone)
    return not any((far - c.close if up else c.close - far) >= _HALF * atr
                   for c in ctx.candles.last(_ALL, Timeframe.M5)
                   if c.ts > z.born)


def _pivot_dist(band, levels, atr) -> float | None:
    gaps = [max(min(lv.zone) - max(band), min(band) - max(lv.zone), Decimal(0))
            for lv in levels if _is_ext(lv.kind) and lv.state not in TERMINAL]
    return round(float(min(gaps) / atr), 3) if gaps and atr else None


# --------------------------------------------------- journal-only tags

def context_tags(ctx, direction: Direction) -> dict:
    tags = {"minor_ch_recent": any(
        e.detector == "structure" and e.meta.get("event") == "CHOCH"
        and e.direction is direction and ctx.now - e.ts <= 50 * _M5
        for e in ctx.evidence_history)}
    for key, tf in (("po3_h1", Timeframe.H1), ("po3_d1", Timeframe.D1)):
        last = ctx.candles.last(1, tf) if ctx.candles else []
        tags[key] = bool(last) and _po3(last[-1])
    if (pos := _pd_pos(ctx)) is not None:
        tags["pd_pos"] = round(pos, 3)
        tags["pd"] = ("premium" if pos > 0.5 else
                      "discount" if pos < 0.5 else "eq")
    return tags


def _po3(c) -> bool:                        # TUNE frozen: body<0.5, wick>0.5
    return (c.range > 0 and c.body < _HALF * c.range
            and max(c.upper_wick, c.lower_wick) > _HALF * c.range)


def _ext2(levels, name):                    # last two extremes (STRUCT 2H+2L)
    return sorted((lv for lv in levels if lv.kind.name == name
                   and lv.state not in TERMINAL), key=lambda lv: lv.born)[-2:]


def _pd_pos(ctx) -> float | None:
    if ctx.candles is None or not (last := ctx.candles.last(1, Timeframe.M5)):
        return None
    hs, ls = _ext2(ctx.levels, "EXT_H"), _ext2(ctx.levels, "EXT_L")
    if hs and ls:
        hi = max(max(lv.zone) for lv in hs)
        lo = min(min(lv.zone) for lv in ls)
    else:                                   # fallback: two-session range
        bars = (ctx.candles.prev_day(Timeframe.M5)
                + ctx.candles.today(Timeframe.M5))
        if not bars:
            return None
        hi, lo = max(c.high for c in bars), min(c.low for c in bars)
    return float((last[-1].close - lo) / (hi - lo)) if hi > lo else None
