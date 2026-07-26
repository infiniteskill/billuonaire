"""mark_year.py — RECOVER THE MISSING YEAR ON EACH MARK.

ytrades.json has month+day (read off the chart's x-axis) but no year, because the
charts show only DD/MM. ground_truth.py filled the gap by assuming 2026, and
mark_locate.py proved that assumption wrong for 21 of 21 datable marks -- the T14
screenshot's axis runs 26/08..23/09 with HAVELLS near 1375, a window the Jan-Jul
2026 tape does not even contain.

Month+day is strong evidence though: only the year is missing, so one session per
candidate year has to be checked, and the entry price plus the chart's visible
price band (era) usually leaves exactly one. That is a real identification, not the
free-floating price search mark_locate had to fall back on.

Usage: python3 tools/mark_year.py <data_dir> [slack_days]
Writes tools/ytrades_dated.json when every testable mark resolves to one year.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("/home/doom/Public/PROJECT/2026/trader")
DATA = sys.argv[1]
SLACK = int(sys.argv[2]) if len(sys.argv) > 2 else 1

marks = json.loads((ROOT / "tools/ytrades.json").read_text())
have = {p.stem for p in Path(DATA).glob("*.csv")}
CACHE = {}


def bars(sym):
    if sym not in CACHE:
        d = pd.read_csv(f"{DATA}/{sym}.csv", parse_dates=["ts"])
        ts = d.ts.dt.tz_localize(None) if d.ts.dt.tz else d.ts
        CACHE[sym] = pd.DataFrame({"d": ts.dt.normalize(), "h": d.high, "l": d.low}) \
            .groupby("d").agg(h=("h", "max"), l=("l", "min"))
    return CACHE[sym]


rows, dated = [], []
for m in marks:
    sym, e = m["stock"], m["entry"]
    if sym not in have:
        rows.append((m["id"], sym, "NO_DATA", "", "")); continue
    g = bars(sym)
    yrs = sorted({d.year for d in g.index})
    hits = []
    for y in yrs:
        try:
            d0 = pd.Timestamp(year=y, month=m["month"], day=m["day"])
        except ValueError:
            continue
        w = g[(g.index >= d0 - pd.Timedelta(days=SLACK))
              & (g.index <= d0 + pd.Timedelta(days=SLACK))]
        if len(w) and w.l.min() <= e <= w.h.max():
            hits.append(y)
    era = m.get("era")
    if era and len(hits) > 1:                       # era band breaks remaining ties
        keep = []
        for y in hits:
            d0 = pd.Timestamp(year=y, month=m["month"], day=m["day"])
            w = g[(g.index >= d0 - pd.Timedelta(days=20))
                  & (g.index <= d0 + pd.Timedelta(days=20))]
            if len(w) and w.l.min() >= era[0] * 0.97 and w.h.max() <= era[1] * 1.03:
                keep.append(y)
        if keep:
            hits = keep
    if not hits:
        rows.append((m["id"], sym, "NO_YEAR", f"entry {e}",
                     f"tape {g.index.min().date()}..{g.index.max().date()}"))
    elif len(hits) == 1:
        rows.append((m["id"], sym, "DATED", str(hits[0]),
                     f'{hits[0]}-{m["month"]:02d}-{m["day"]:02d}'))
        dated.append({**m, "year": hits[0]})
    else:
        rows.append((m["id"], sym, "AMBIGUOUS", ",".join(map(str, hits)), ""))

r = pd.DataFrame(rows, columns=["mark", "sym", "status", "year", "date"])
print(r.to_string(index=False))
print(f"\n{'':-<60}")
for v, c in r.status.value_counts().items():
    print(f"  {v:10} {c:3}")
if dated:
    out = ROOT / "tools/ytrades_dated.json"
    out.write_text(json.dumps(dated, indent=1))
    print(f"\nwrote {len(dated)} dated marks -> {out}")
    print("year spread:", pd.Series([d["year"] for d in dated]).value_counts().to_dict())
