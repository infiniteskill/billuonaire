"""Journal-derived performance report, GROSS (price R) and NET (after costs)
kept separate -- flat brokerage swamps small notionals, so both must show.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path
from statistics import mean, pstdev

from trader.store.journal import Journal

D = Decimal
_SIGN = {"LONG": 1, "SHORT": -1}
MIN_DAYS_FOR_CI = 10


@dataclass(frozen=True)
class Trade:
    symbol: str
    day: date
    template: str
    reason: str        # exit reason (trade_close)
    gross: Decimal     # price PnL, no costs
    net: Decimal       # journaled realized (costs included)
    gross_r: float
    net_r: float


@dataclass
class Report:
    totals: dict = field(default_factory=dict)
    per_template: dict = field(default_factory=dict)
    per_symbol: dict = field(default_factory=dict)
    per_exit: dict = field(default_factory=dict)
    per_gate: dict = field(default_factory=dict)      # gate -> skip count
    per_day: list = field(default_factory=list)       # (day_iso, n, net_r)
    day_stats: dict = field(default_factory=dict)     # mean/std/n_days
    notes: list = field(default_factory=list)


def _days(root: Path, start: date | None, end: date | None) -> list[date]:
    ds = sorted(date.fromisoformat(p.stem) for p in root.glob("*.jsonl"))
    return [d for d in ds if (start is None or d >= start)
            and (end is None or d <= end)]


def _pf(vals: list[Decimal | float]) -> float | None:
    up, dn = sum(v for v in vals if v > 0), -sum(v for v in vals if v < 0)
    return float(up / dn) if dn else None


def _row(ts: list[Trade]) -> dict:
    return {"n": len(ts), "wr": sum(1 for t in ts if t.net > 0) / len(ts),
            "gross_r": sum(t.gross_r for t in ts),
            "net_r": sum(t.net_r for t in ts),
            "net_pnl": sum((t.net for t in ts), D(0))}


def _by(trades: list[Trade], key) -> dict:
    out: dict[str, list[Trade]] = {}
    for t in trades:
        out.setdefault(key(t), []).append(t)
    return {k: _row(v) for k, v in sorted(out.items())}


def _max_dd(rs: list[float]) -> float:
    eq = peak = dd = 0.0
    for r in rs:
        eq += r
        peak = max(peak, eq)
        dd = max(dd, peak - eq)
    return dd


def compute(journal_dir: Path, start: date | None = None,
            end: date | None = None) -> Report:
    """Read day JSONLs in [start, end] (None = unbounded) into a Report."""
    root = Path(journal_dir)
    j = Journal(root)
    trades, per_gate, per_day = [], {}, []
    for day in _days(root, start, end):
        tmpl: dict[str, str] = {}
        open_: dict[str, tuple[dict, str]] = {}
        fills: dict[str, list] = {}
        n0 = len(trades)
        for e in j.read(day):
            sym, k = e.get("symbol"), e["kind"]
            if k == "verdict":
                tmpl[sym] = e.get("template") or "-"
            elif k == "skip":
                per_gate[e["gate"]] = per_gate.get(e["gate"], 0) + 1
            elif k == "trade_open":
                open_[sym], fills[sym] = (e, tmpl.get(sym, "-")), []
            elif k == "trade_partial" and sym in open_:
                fills[sym].append((e["qty"], D(e["price"])))
            elif k == "trade_close" and sym in open_:
                (o, template), part = open_.pop(sym), fills.pop(sym)
                p0, qty, sign = D(o["price"]), o["qty"], _SIGN[o["direction"]]
                rest = qty - sum(q for q, _ in part)
                gross = sum((q * (p - p0) for q, p in part
                             + [(rest, D(e["exit_price"]))]), D(0)) * sign
                risk = abs(p0 - D(o["stop"])) * qty
                trades.append(Trade(sym, day, template, e["reason"], gross,
                                    D(e["pnl"]), float(gross / risk) if risk
                                    else 0.0, e["r"]))
        per_day.append((day.isoformat(), len(trades) - n0,
                        float(sum(t.net_r for t in trades[n0:]))))

    n = len(trades)
    wins = sum(1 for t in trades if t.net > 0)
    rep = Report(
        totals={"trades": n, "wins": wins,
                "losses": sum(1 for t in trades if t.net < 0),
                "wr": wins / n if n else 0.0,
                "gross_r": float(sum(t.gross_r for t in trades)),
                "net_r": float(sum(t.net_r for t in trades)),
                "gross_pnl": sum((t.gross for t in trades), D(0)),
                "net_pnl": sum((t.net for t in trades), D(0)),
                "pf_gross": _pf([t.gross for t in trades]),
                "pf_net": _pf([t.net for t in trades]),
                "expectancy_r": mean(t.net_r for t in trades) if n else 0.0,
                "max_dd_r": _max_dd([t.net_r for t in trades])},
        per_template=_by(trades, lambda t: t.template),
        per_symbol=_by(trades, lambda t: t.symbol),
        per_exit=_by(trades, lambda t: t.reason),
        per_gate=per_gate, per_day=per_day)
    daily = [r for _, _, r in per_day]
    rep.day_stats = {"mean": mean(daily) if daily else 0.0,
                     "std": pstdev(daily) if daily else 0.0,
                     "n_days": len(daily)}
    if len(daily) < MIN_DAYS_FOR_CI:
        rep.notes.append(f"n_days={len(daily)}<{MIN_DAYS_FOR_CI}: CIs unreliable")
    return rep
