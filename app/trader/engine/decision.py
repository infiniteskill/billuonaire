"""decision.py — the taught DECISION TREE (doc 33): a TF-invariant synthesizer
that consumes the detector Evidence stream + ctx.levels and outputs a single
{take, direction, entry, sl, target, grade, reasons} decision.

It is NOT a detector -- it REASONS over what the detectors emitted, applying the
taught top-down AND-chain:
  node 0/1  premium_discount permits a side (price AT an extreme, not mid) -> bias
  node 2    a same-direction decisional zone (OB/FVG/breaker/mitigation) exists -> entry object
  node 3    htf_nest refines the entry (CE of the innermost nested tier, tight SL)
  node 4    runway: a far opposite extreme/pool gives the target (no runway -> skip)
  node 5    grade = confirmation count (BOS + sweep + nest_depth + maturity)
  take iff every REQUIRED gate (extreme, zone, runway) passes AND grade >= min_grade.

Required gates are hard skips; bonuses only raise the grade. Entry/SL come from the
nested tier when present (tightest), else the decisional zone; SL is the zone's far
(outer) edge per meta.sl. Fully explainable via reasons[]."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from trader.engine.context import StockContext
from trader.models.evidence import Direction, Evidence
from trader.models.level import LevelKind

_ZONE_EVENTS = frozenset({"OB_RETEST", "BRK_RETEST", "MIT_RETEST", "FVG",
                          "FVG_N_RETEST", "FVG_CE_HOLD", "IFVG", "IFVG_RETEST"})
_ZONE_DETS = frozenset({"ob_taught", "fvg", "fvg_n", "fvg_cb", "mitigation",
                        "breaker", "breaker_msb", "propulsion2"})
_BOS_EVENTS = frozenset({"BOS", "CHOCH"})


def _mid(zone: tuple[Decimal, Decimal]) -> Decimal:
    return (zone[0] + zone[1]) / 2


@dataclass
class Decision:
    take: bool
    direction: Direction | None
    entry: Decimal | None
    sl: Decimal | None
    target: Decimal | None
    grade: int
    reasons: list[str] = field(default_factory=list)


def _runway(ctx: StockContext, d: Direction, entry: Decimal) -> Decimal | None:
    """Nearest FAR opposite extreme in the trade direction = the target draw."""
    kind = LevelKind.EXT_H if d is Direction.LONG else LevelKind.EXT_L
    long = d is Direction.LONG
    cands = [_mid(lv.zone) for lv in ctx.levels if lv.kind is kind
             and ((_mid(lv.zone) > entry) if long else (_mid(lv.zone) < entry))]
    if not cands:
        return None
    return min(cands) if long else max(cands)


def decide(ctx: StockContext, evidence: list[Evidence], min_grade: int = 2) -> Decision:
    # node 0/1 -- premium/discount permits a side (AT an extreme, never mid)
    pd = next((e for e in evidence if e.detector == "premium_discount"), None)
    permit = pd.meta.get("permits") if pd else None
    if not permit:
        return Decision(False, None, None, None, None, 0, ["no extreme (p/d mid/absent)"])
    d = Direction.LONG if permit == "LONG" else Direction.SHORT
    reasons = [f"extreme:{pd.meta['side']}"]

    # node 2 -- a same-direction decisional zone (the entry object)
    z = next((e for e in evidence if e.detector in _ZONE_DETS and e.direction is d
              and e.meta.get("event") in _ZONE_EVENTS), None)
    if z is None:
        return Decision(False, d, None, None, None, 0, reasons + ["no decisional zone"])
    entry = _mid(z.zone)
    sl = (Decimal(z.meta["sl"]) if z.meta.get("sl")
          else (z.zone[0] if d is Direction.LONG else z.zone[1]))
    reasons.append(f"zone:{z.detector}:{z.meta.get('event')}")

    grade = 0
    if any(e.detector == "structure" and e.direction is d
           and e.meta.get("event") in _BOS_EVENTS for e in evidence):
        grade += 1; reasons.append("bos")
    if any(e.detector == "sweep" for e in evidence):
        grade += 1; reasons.append("sweep")

    # node 3 -- htf_nest refines the entry (CE of innermost tier, tighter SL)
    nests = [e for e in evidence if e.detector == "htf_nest" and e.direction is d]
    if nests:
        n = max(nests, key=lambda e: e.meta.get("nest_depth", 0))
        entry, sl = Decimal(n.meta["ce"]), Decimal(n.meta["sl"])
        grade += 1 + int(n.meta.get("nest_depth", 0))
        reasons.append(f"nest:{n.meta['nest_depth']}")

    mats = [e.meta["maturity"] for e in evidence
            if e.detector == "compression" and e.meta.get("maturity") is not None]
    if mats and max(mats) >= 0.5:
        grade += 1; reasons.append(f"maturity:{max(mats)}")

    # node 4 -- runway (required): a far opposite extreme = the target
    target = _runway(ctx, d, entry)
    if target is None:
        return Decision(False, d, entry, sl, None, grade, reasons + ["no runway"])
    reasons.append("runway")

    take = grade >= min_grade
    reasons.append("take" if take else f"grade {grade}<{min_grade}")
    return Decision(take, d, entry, sl, target, grade, reasons)
