"""Calibration v1: journal-derived per-detector precision + capped weight
suggestions. PRINT ONLY -- analyze() reads journals and returns a report;
nothing here ever mutates config.

Precision proxy (honest attribution, not causality -- journals carry no
per-zone counterfactual): every verdict entry journals the top zone's
``members`` [(detector, event, strength), ...]. A trade is linked to the
LAST verdict journaled for its symbol before its trade_open entry (arm and
trigger happen on that closed M5; entries are appended in stream order).

    precision(d) = d's member appearances in verdicts linked to trades that
                   closed net-positive (journaled pnl > 0, costs included)
                 / d's member appearances across ALL journaled verdicts

The denominator spans every verdict zone (traded or not), so precision
rewards detectors whose evidence shows up when it MATTERS rather than
everywhere. Verdicts without a ``members`` field (pre-phase-5 journals)
contribute nothing.

Suggestions: redistribute the eligible detectors' current weight mass by
precision share, then cap the move at +/-``cap`` (10%) of the current
weight. A detector below ``min_samples`` (30) member appearances is
"insufficient data": no suggestion, current weight stands.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path

from trader.store.journal import Journal

MIN_SAMPLES = 30
CAP = 0.10


@dataclass
class CalibrationReport:
    n_verdicts: int = 0
    n_trades: int = 0                 # closed trades linked to a verdict
    n_wins: int = 0                   # of those, net-positive
    rows: dict = field(default_factory=dict)         # det -> {appearances, wins, precision}
    weights: dict = field(default_factory=dict)      # current config weights (enabled)
    suggestions: dict = field(default_factory=dict)  # det -> suggested weight
    insufficient: list = field(default_factory=list)
    min_samples: int = MIN_SAMPLES


def _days(root: Path, start: date | None, end: date | None) -> list[date]:
    ds = sorted(date.fromisoformat(p.stem) for p in root.glob("*.jsonl"))
    return [d for d in ds if (start is None or d >= start)
            and (end is None or d <= end)]


def analyze(journal_dir: Path, start: date | None = None,
            end: date | None = None, weights: dict | None = None,
            min_samples: int = MIN_SAMPLES, cap: float = CAP) -> CalibrationReport:
    """Fold journal days in [start, end] into a CalibrationReport (see module
    docstring for the precision proxy). Never writes anything."""
    root = Path(journal_dir)
    j = Journal(root)
    rep = CalibrationReport(weights=dict(weights or {}), min_samples=min_samples)
    total: dict[str, int] = {}
    wins: dict[str, int] = {}
    for day in _days(root, start, end):
        last: dict[str, list] = {}    # symbol -> latest verdict members
        open_: dict[str, list] = {}   # symbol -> members linked at trade_open
        for e in j.read(day):
            sym, kind = e.get("symbol"), e["kind"]
            if kind == "verdict":
                rep.n_verdicts += 1
                last[sym] = e.get("members") or []
                for det, *_ in last[sym]:
                    total[det] = total.get(det, 0) + 1
            elif kind == "trade_open":
                open_[sym] = last.get(sym, [])
            elif kind == "trade_close" and sym in open_:
                rep.n_trades += 1
                members = open_.pop(sym)
                if Decimal(e["pnl"]) > 0:
                    rep.n_wins += 1
                    for det, *_ in members:
                        wins[det] = wins.get(det, 0) + 1
    for det, n in sorted(total.items()):
        rep.rows[det] = {"appearances": n, "wins": wins.get(det, 0),
                         "precision": wins.get(det, 0) / n}
    elig = {d: w for d, w in rep.weights.items()
            if total.get(d, 0) >= min_samples}
    rep.insufficient = [d for d in rep.weights if d not in elig]
    prec_sum = sum(rep.rows[d]["precision"] for d in elig)
    mass = sum(elig.values())
    for d, w in elig.items():
        share = rep.rows[d]["precision"] / prec_sum * mass if prec_sum else w
        rep.suggestions[d] = round(min(max(share, w * (1 - cap)),
                                       w * (1 + cap)), 2)
    return rep
