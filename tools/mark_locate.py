"""mark_locate.py — DATE THE USER'S MARKS BY PRICE, NOT BY ASSUMPTION.

ytrades.json stores month+day read off each chart, but never the YEAR.
ground_truth.py assumed month<=7 => 2026 and used that date to look for a
matching signal. That assumption is wrong for most marks: HAVELLS "H_jan_short"
has entry 1207 while HAVELLS on 2026-01-20 traded 1337-1454, and "H_old_short"
(entry 1910, era 1700-2010) is outside the 2026 tape's 1124-1515 entirely.
So the gate has been scoring the detector against dates where the trade did not
happen -- its FAIL verdict is not evidence about the detector.

This dates each mark by its price fingerprint instead: find the session(s) where
the entry was actually tradeable, the swept level had just been taken, and price
then ran to the target before the stop. Marks whose episode is not in the tape at
all are UNTESTABLE, not failures.

Usage: python3 tools/mark_locate.py <data_dir> [lookahead_days] [sweep_lookback_days]
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("/home/doom/Public/PROJECT/2026/trader")
DATA = sys.argv[1]
AHEAD = int(sys.argv[2]) if len(sys.argv) > 2 else 5
BACK = int(sys.argv[3]) if len(sys.argv) > 3 else 3

marks = json.loads((ROOT / "tools/ytrades.json").read_text())
have = {p.stem for p in Path(DATA).glob("*.csv")}
CACHE = {}


def bars(sym):
    if sym not in CACHE:
        d = pd.read_csv(f"{DATA}/{sym}.csv", parse_dates=["ts"])
        ts = d.ts.dt.tz_localize(None) if d.ts.dt.tz else d.ts
        CACHE[sym] = (ts.dt.normalize().values, d.high.values, d.low.values)
    return CACHE[sym]


def locate(m):
    """Sessions where this exact trade was physically takeable, best first."""
    day, hi, lo = bars(m["stock"])
    days = np.unique(day)
    long = m["dir"] == "long"
    e, sl, tg, sw = m["entry"], m["sl"], m["target"], m.get("swept")
    out = []
    for k, d0 in enumerate(days):
        w = day == d0
        if not (lo[w].min() <= e <= hi[w].max()):
            continue
        # sweep: the level that got taken out just before entry
        sw_ok = None
        if sw is not None:
            b = day >= days[max(0, k - BACK)]
            b &= day <= d0
            sw_ok = bool(hi[b].max() >= sw) if not long else bool(lo[b].min() <= sw)
        # resolution: after entry is first touched, target before stop?
        f = np.flatnonzero(w & (lo <= e) & (e <= hi))
        if not len(f):
            continue
        seg = (day >= d0) & (day <= days[min(len(days) - 1, k + AHEAD)])
        seg = np.flatnonzero(seg)
        seg = seg[seg >= f[0]]
        won = None
        for x in seg:
            if (lo[x] <= sl) if long else (hi[x] >= sl):
                won = False; break
            if (hi[x] >= tg) if long else (lo[x] <= tg):
                won = True; break
        out.append((str(pd.Timestamp(d0).date()), sw_ok, won))
    # best = swept confirmed and target reached
    out.sort(key=lambda r: (-(r[1] is True), -(r[2] is True)))
    return out


rows = []
for m in marks:
    sym = m["stock"]
    if sym not in have:
        rows.append((m["id"], sym, m["dir"], f'{m["month"]:02d}-{m["day"]:02d}',
                     "NO_DATA", "", "", "")); continue
    cand = locate(m)
    if not cand:
        era = m.get("era")
        rows.append((m["id"], sym, m["dir"], f'{m["month"]:02d}-{m["day"]:02d}',
                     "NOT_IN_TAPE", f'era {era[0]}-{era[1]}' if era else "",
                     f'entry {m["entry"]}', "")); continue
    d, sw, won = cand[0]
    assumed = f'2026-{m["month"]:02d}-{m["day"]:02d}'
    rows.append((m["id"], sym, m["dir"], f'{m["month"]:02d}-{m["day"]:02d}',
                 "LOCATED", f"{len(cand)} cand", d,
                 f'{"date OK" if d == assumed else "DATE WRONG"}'
                 f'{" swept" if sw else ""}{" hitTGT" if won else ""}'))

r = pd.DataFrame(rows, columns=["mark", "sym", "dir", "chart_md", "status",
                                "info", "best_date", "note"])
print(r.to_string(index=False))
print(f"\n{'':-<70}")
for v, c in r.status.value_counts().items():
    print(f"  {v:12} {c:3}")
loc = r[r.status == "LOCATED"]
if len(loc):
    ok = loc.note.str.startswith("date OK").sum()
    print(f"\nOf {len(loc)} located marks, assumed-2026 date was right for {ok} "
          f"({100*ok/len(loc):.0f}%). The rest were scored on the wrong session.")
