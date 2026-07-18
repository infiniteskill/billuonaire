"""trader doctor: read-only integrity audit of a FileFeed CSV data dir.

Per file: exact schema (``ts,open,high,low,close,volume``); ts parseable,
tz-aware in the market tz, strictly increasing, inside the session
[open, close); OHLC sane (low <= open/close <= high, positive, finite; tick
grid drift is a WARNING -- FileFeed re-quantizes on load); volume a
non-negative integer; cadence (every ts must sit on the file's modal
intra-session spacing grid -- guards the 5m-rows-as-M1 identity that
data/long5m relies on); close->open moves above ``jump_pct`` flagged as
probable split/bonus splices (mixed adjustment basis across a merge, or a
real corporate action -- either way research across that boundary is
invalid; history is never silently auto-adjusted, so the flag is the guard).
Per-session row counts land in the FileReport for the coverage matrix; thin
sessions (< 80% of the cadence-implied bar count) are WARNINGs.

Severity: CRITICAL = poisons research (doctor exits nonzero), WARNING =
suspicious but loadable, INFO = reporting only. Detail per code is capped
at ``_CAP`` issues + one "+N more" summary line.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd

from trader.models.market import NSE, MarketSpec

CRITICAL, WARNING, INFO = "CRITICAL", "WARNING", "INFO"
JUMP_PCT = 15.0   # default close->open % move flagged as a probable splice
_CAP = 3          # detailed issues kept per (file, code)


@dataclass(frozen=True)
class Issue:
    sev: str
    file: str
    code: str
    msg: str


@dataclass
class FileReport:
    name: str
    rows: int = 0
    cadence: int | None = None            # modal intra-session spacing, minutes
    sessions: dict = field(default_factory=dict)   # date -> row count
    issues: list[Issue] = field(default_factory=list)

    @property
    def n_crit(self) -> int:
        return sum(i.sev == CRITICAL for i in self.issues)


def splices(df: pd.DataFrame, jump_pct: float = JUMP_PCT) -> list[tuple[str, float]]:
    """(ts, pct) close->open jumps above ``jump_pct`` between consecutive
    rows of a FileFeed-schema frame -- the post-merge splice guard shared by
    ``trader fetch`` and tools/accrue5m.py."""
    if len(df) < 2:
        return []
    o = df["open"].astype(float).to_numpy()
    c = df["close"].astype(float).to_numpy()
    ts = df["ts"].to_numpy()
    pct = abs(o[1:] / c[:-1] - 1) * 100
    return [(str(ts[i + 1]), round(float(p), 1))
            for i, p in enumerate(pct) if p > jump_pct]


def check_file(path: Path, spec: MarketSpec = NSE,
               jump_pct: float = JUMP_PCT) -> FileReport:
    rep = FileReport(path.name)
    seen: Counter = Counter()
    sev_of: dict[str, str] = {}

    def flag(sev: str, code: str, msg: str) -> None:
        sev_of.setdefault(code, sev)
        if seen[code] < _CAP:
            rep.issues.append(Issue(sev, path.name, code, msg))
        seen[code] += 1

    with path.open() as fh:
        header = fh.readline().rstrip("\n")
    if header != "ts,open,high,low,close,volume":
        flag(CRITICAL, "schema", f"header {header!r}")
        return rep
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    rep.rows = len(df)
    if not rep.rows:
        flag(WARNING, "empty", "header only, no rows")
        return rep

    open_min = spec.open_t.hour * 60 + spec.open_t.minute
    prev_t = prev_close = None
    times: list[datetime] = []
    for i, row in enumerate(df.itertuples(index=False), start=2):   # csv line no
        try:
            t = datetime.fromisoformat(row.ts)
        except ValueError:
            flag(CRITICAL, "ts_parse", f"line {i}: unparseable ts {row.ts!r}")
            prev_t = prev_close = None
            continue
        if t.tzinfo is None:
            flag(CRITICAL, "ts_naive", f"line {i}: naive ts {row.ts}")
            prev_t = prev_close = None
            continue
        if t.utcoffset() != t.astimezone(spec.tzinfo).utcoffset():
            flag(CRITICAL, "ts_tz", f"line {i}: offset {t.utcoffset()} is not {spec.tz}")
        if prev_t is not None:
            if t == prev_t:
                flag(CRITICAL, "ts_dup", f"line {i}: duplicate ts {row.ts}")
            elif t < prev_t:
                flag(CRITICAL, "ts_order", f"line {i}: ts {row.ts} < previous row")
        if not spec.open_t <= t.time() < spec.close_t:
            flag(CRITICAL, "session", f"line {i}: {row.ts} outside "
                 f"[{spec.session_open},{spec.session_close})")
        try:
            o, h, lo, c = (Decimal(getattr(row, k))
                           for k in ("open", "high", "low", "close"))
            px_ok = all(x.is_finite() for x in (o, h, lo, c))
            if not px_ok:
                flag(CRITICAL, "price", f"line {i}: non-finite price")
        except InvalidOperation:
            px_ok = False
            flag(CRITICAL, "price", f"line {i}: unparseable price")
        if px_ok:
            if min(o, h, lo, c) <= 0:
                flag(CRITICAL, "price", f"line {i}: non-positive price")
            elif not lo <= min(o, c) <= max(o, c) <= h:
                flag(CRITICAL, "ohlc", f"line {i}: o={o} h={h} l={lo} c={c}")
            elif any(x % spec.tick_size for x in (o, h, lo, c)):
                flag(WARNING, "tick", f"line {i}: price off the {spec.tick_size} grid")
            if prev_close is not None and prev_close > 0:
                pct = abs(o / prev_close - 1) * 100
                if pct > jump_pct:
                    flag(CRITICAL, "splice", f"{row.ts}: close->open jump "
                         f"{pct:.1f}% (probable split/bonus splice)")
        if not row.volume.isdigit():
            flag(CRITICAL, "volume", f"line {i}: volume {row.volume!r} "
                 "not a non-negative integer")
        prev_close = c if px_ok else None
        prev_t = t
        times.append(t)
        rep.sessions[t.date()] = rep.sessions.get(t.date(), 0) + 1

    deltas = [int((b - a).total_seconds() // 60) for a, b in zip(times, times[1:])
              if b.date() == a.date() and b > a]
    if deltas:
        rep.cadence = m = Counter(deltas).most_common(1)[0][0]
        for t in times:
            if (t.hour * 60 + t.minute - open_min) % m:
                flag(CRITICAL, "cadence",
                     f"{t.isoformat()}: off the {m}-minute grid")
        expected = spec.session_minutes // m
        for d, n in rep.sessions.items():
            if n < 0.8 * expected:
                flag(WARNING, "thin_session", f"{d}: {n}/{expected} rows")
            elif n < expected:
                flag(INFO, "gap_session", f"{d}: {n}/{expected} rows")
    for code, n in seen.items():
        if n > _CAP:
            rep.issues.append(Issue(sev_of[code], path.name, code,
                                    f"... +{n - _CAP} more"))
    return rep


def run_dir(data: Path, spec: MarketSpec = NSE,
            jump_pct: float = JUMP_PCT) -> list[FileReport]:
    """Check every ``*.csv`` under ``data``; a file whose last session ends
    before the directory's newest one is additionally flagged stale."""
    reps = [check_file(p, spec, jump_pct) for p in sorted(data.glob("*.csv"))]
    last = {r.name: max(r.sessions) for r in reps if r.sessions}
    newest = max(last.values(), default=None)
    for r in reps:
        if r.name in last and last[r.name] < newest:
            r.issues.append(Issue(WARNING, r.name, "stale",
                                  f"ends {last[r.name]}, dir ends {newest}"))
    return reps
