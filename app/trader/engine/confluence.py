"""ConfluenceEngine: the decision core (06-CONFLUENCE-ENGINE-DEEP §1-§2).

Fuses the self-windowed evidence into spatially clustered, direction-netted
ScoredZones, then multiplies in cross-TF alignment and session context:

  CLUSTER  zones merge when overlapping or gapped <= merge_atr x ATR(M5);
           same-detector duplicates keep best strength. Directional mass =
           sum(enabled_weight x strength) per side; the losing side subtracts
           at 0.8x; NEUTRAL members feed 0.5 x weight x strength to the
           winner's pool; weightless volume adds a flat +3 booster instead.
           timestats contributes NO cluster mass at all (audit 5
           single-count: it is the global time multiplier below, and must
           not also pad the pool of whatever cluster its candle lands in).
  ALIGN    D1 regime veto (MARKDOWN kills LONG, MARKUP kills SHORT); M15
           trend agreement: oppose 0 / agree 1 / NEUTRAL 0.8. htf_phase and
           m15_trend are ARGUMENTS -- the orchestrator supplies them, the
           engine stays pure.
  CONTEXT  time (latest live timestats strength, default 0.5) x template
           (matched play 1.0 / off-template 0.5 / RANGE_PIN 1.0 when the zone
           fades a range edge else 0.5 -- discipline moves to SIZE, pipeline
           halves qty on RANGE_PIN days / UNCLASSIFIED 0) x obviousness
           (unswept obvious level in zone 0.85,
           swept+reclaimed 1.15; obvious = ROUND kind or touches >= 3) x index
           (axiom 11: zone opposing a non-NEUTRAL ctx.index trend with
           strength >= 0.5 is halved, else 1.0).

final = raw x align x time x template x obviousness x index, capped 100, 1dp.
Zones with distinct winning detectors < min_zone_detectors are unarmable
(final forced 0) but still returned, members intact, for the journal.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from trader.config import Settings
from trader.engine.context import StockContext, live_evidence
from trader.models.evidence import Direction, Evidence
from trader.models.level import LevelKind, LevelState
from trader.models.candle import Timeframe

_DEFAULTS = {"merge_atr": 0.25, "min_zone_detectors": 3, "opposition": 0.8,
             "neutral_pool": 0.5, "volume_boost": 3.0, "time_default": 0.5}
_SWEPT = (LevelState.SWEPT, LevelState.RECLAIMED)
_OR_EDGES = (LevelKind.OPEN_RANGE_H, LevelKind.OPEN_RANGE_L)


@dataclass(frozen=True)
class ScoredZone:
    zone: tuple[Decimal, Decimal]
    direction: Direction
    members: list[tuple[str, str, float]]   # (detector, event, strength)
    distinct: int                            # winning-direction detectors
    raw: float                               # netted mass (+volume booster)
    final: float                             # raw x all multipliers, 0-100
    mults: dict[str, float]                  # journal decomposition


class ConfluenceEngine:
    def __init__(self, settings: Settings, params: dict | None = None):
        p = {**_DEFAULTS, **(params or {})}
        self.weights = settings.enabled_weights()
        self.merge_atr = Decimal(str(p["merge_atr"]))
        self.min_detectors = int(p["min_zone_detectors"])
        self.opp, self.pool_f = p["opposition"], p["neutral_pool"]
        self.vol_boost, self.time_default = p["volume_boost"], p["time_default"]

    def score(self, ctx: StockContext, evidence: list[Evidence],
              htf_phase: tuple[str, float], m15_trend: Direction,
              ) -> list[ScoredZone]:
        live = live_evidence(evidence, ctx.now)
        gap = self.merge_atr * (ctx.atr(Timeframe.M5) or Decimal(0))
        stats = [e for e in live if e.detector == "timestats"]
        time_mult = (max(stats, key=lambda e: (e.ts, e.strength)).strength if stats
                     else self.time_default)
        play = self._play(ctx, m15_trend)
        zones = [self._score_zone(lo, hi, evs, ctx, htf_phase, m15_trend,
                                  time_mult, play)
                 for lo, hi, evs in self._cluster(live, gap)]
        return sorted(zones, key=lambda z: (-z.final, -z.raw, z.zone[0]))

    def _cluster(self, evidence, gap):
        out: list[list] = []
        for e in sorted(evidence, key=lambda e: (min(e.zone), max(e.zone))):
            lo, hi = min(e.zone), max(e.zone)
            if out and lo <= out[-1][1] + gap:
                out[-1][1] = max(out[-1][1], hi)
                out[-1][2].append(e)
            else:
                out.append([lo, hi, [e]])
        return out

    def _score_zone(self, lo, hi, evs, ctx, htf, m15, time_mult, play):
        best: dict[str, Evidence] = {}
        for e in evs:                        # same detector: best strength only
            if e.detector not in best or e.strength > best[e.detector].strength:
                best[e.detector] = e
        mass, pool = {Direction.LONG: 0.0, Direction.SHORT: 0.0}, 0.0
        for det, e in best.items():
            if det in ("volume", "timestats"):   # volume: flat booster below;
                continue                         # timestats: time mult ONLY
            w = self.weights.get(det, 0.0) * e.strength
            if e.direction is Direction.NEUTRAL:
                pool += self.pool_f * w
            else:
                mass[e.direction] += w
        long_m, short_m = mass[Direction.LONG], mass[Direction.SHORT]
        if long_m == short_m:
            dirn = Direction.NEUTRAL         # contested dead-even: unarmable
        else:
            dirn = Direction.LONG if long_m > short_m else Direction.SHORT
        raw = max(0.0, max(long_m, short_m) - self.opp * min(long_m, short_m)
                  + pool)
        if "volume" in best:
            raw += self.vol_boost
        distinct = 0 if dirn is Direction.NEUTRAL else sum(
            1 for d, e in best.items()
            if d not in ("volume", "timestats") and e.direction is dirn)
        mults = {"align": self._align(dirn, htf, m15), "time": time_mult,
                 "template": self._template_mult(dirn, ctx.day.template, play,
                                                 lo, hi, ctx),
                 "obviousness": self._obviousness(lo, hi, ctx),
                 "index": self._index_mult(dirn, ctx.index)}
        final = 0.0
        if distinct >= self.min_detectors:
            prod = raw
            for m in mults.values():
                prod *= m
            final = round(min(prod, 100.0), 1)
        members = [(d, e.meta.get("event", ""), e.strength)
                   for d, e in sorted(best.items())]
        return ScoredZone((lo, hi), dirn, members, distinct, raw, final, mults)

    @staticmethod
    def _index_mult(dirn, idx) -> float:
        """Axiom 11: fading a strong index trend costs half the score."""
        return 0.5 if (idx is not None and idx.trend is not Direction.NEUTRAL
                       and dirn.value == -idx.trend.value
                       and idx.strength >= 0.5) else 1.0

    @staticmethod
    def _align(dirn, htf, m15) -> float:
        if ((htf[0] == "MARKDOWN" and dirn is Direction.LONG)
                or (htf[0] == "MARKUP" and dirn is Direction.SHORT)):
            return 0.0                       # D1 regime veto
        if m15 is Direction.NEUTRAL:
            return 0.8
        return 1.0 if m15 is dirn else 0.0

    @staticmethod
    def _play(ctx, m15) -> Direction | None:
        """Template play direction: TREND follows M15; TRAP_REVERSAL plays
        away from the swept opening-range edge."""
        if ctx.day.template == "TREND":
            return m15
        if ctx.day.template == "TRAP_REVERSAL":
            for lv in ctx.levels:
                if (lv.symbol == ctx.symbol and lv.kind in _OR_EDGES
                        and any(s in _SWEPT for _, s in lv.state_history)):
                    return (Direction.LONG if lv.kind is LevelKind.OPEN_RANGE_L
                            else Direction.SHORT)
        return None

    def _template_mult(self, dirn, template, play, lo, hi, ctx) -> float:
        if template == "UNCLASSIFIED":
            return 0.0
        if template == "RANGE_PIN":     # fade edges full score, half SIZE
            return 1.0 if self._fades_edge(dirn, lo, hi, ctx) else 0.5
        return 1.0 if play is dirn and play is not Direction.NEUTRAL else 0.5

    @staticmethod
    def _fades_edge(dirn, lo, hi, ctx) -> bool:
        """RANGE_PIN design table: "fade edges half-size or skip". A zone
        within 1xATR of a range edge (OR_H/OR_L level or the session
        high/low) pointing AWAY from that edge is the legitimate range fade:
        full score here, the pipeline takes the discipline out of SIZE."""
        atr = ctx.atr(Timeframe.M5) or Decimal(0)
        edges = [(lv.zone, Direction.SHORT if lv.kind is LevelKind.OPEN_RANGE_H
                  else Direction.LONG) for lv in ctx.levels
                 if lv.symbol == ctx.symbol and lv.kind in _OR_EDGES]
        if today := (ctx.candles.today(Timeframe.M5) if ctx.candles else []):
            dh, dl = max(c.high for c in today), min(c.low for c in today)
            edges += [((dh, dh), Direction.SHORT), ((dl, dl), Direction.LONG)]
        return any(fade is dirn
                   and max(min(z) - hi, lo - max(z), Decimal(0)) <= atr
                   for z, fade in edges)

    @staticmethod
    def _obviousness(lo, hi, ctx) -> float:
        obvious = [lv for lv in ctx.levels
                   if lv.symbol == ctx.symbol
                   and min(lv.zone) <= hi and max(lv.zone) >= lo
                   and (lv.kind is LevelKind.ROUND or lv.touches >= 3)]
        states = [{s for _, s in lv.state_history} for lv in obvious]
        if any(LevelState.RECLAIMED in st for st in states):
            return 1.15                      # trap sprung: crowd already burned
        if any(not (st & set(_SWEPT)) for st in states):
            return 0.85                      # pretty and untouched = bait
        return 1.0
