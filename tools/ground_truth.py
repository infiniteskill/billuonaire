"""ground_truth.py — THE ADMISSIBILITY GATE (2026-07-26 process fix).

Before any aggregate number is believed, the pipeline must reproduce the USER's
OWN marked trades: right symbol, right DIRECTION, right place, right time.
A system that cannot reproduce known-good trades makes no admissible statistics.
(Written after phantom-fills + p/d direction-flip + zone/entry-mismatch all passed
12 downstream batteries undetected — every one of them shared the same generator.)

Marks: tools/ytrades.json {stock, month, day, dir, entry, sl, target, swept, era}.
Year is not stored; month<=7 => 2026 (user-confirmed), price disambiguates outliers.

Usage: python3 tools/ground_truth.py <tradebook.csv> <data_dir> [tol_pct] [days]
"""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path("/home/doom/Public/PROJECT/2026/trader")
TB, DATA = sys.argv[1], sys.argv[2]
TOL = float(sys.argv[3]) if len(sys.argv) > 3 else 3.0     # entry price tolerance %
DAYS = int(sys.argv[4]) if len(sys.argv) > 4 else 3        # date tolerance

marks = [m for m in json.loads((ROOT / "tools/ytrades.json").read_text())
         if m["month"] <= 7]                                # 2026 half
have = {p.stem for p in Path(DATA).glob("*.csv")}
tb = pd.read_csv(TB)
tb["ts"] = pd.to_datetime(tb["ts"]).dt.tz_localize(None)
tb = tb[tb["mode"] == "eod"]

DM = {"short": "SHORT", "long": "LONG"}
rows = []
for m in sorted(marks, key=lambda x: (x["month"], x["day"])):
    sym, want = m["stock"], DM[m["dir"]]
    d = pd.Timestamp(f'2026-{m["month"]:02d}-{m["day"]:02d}')
    if sym not in have:
        rows.append((m["id"], sym, want, str(d.date()), "NO_DATA", "", "", ""))
        continue
    near = tb[(tb.sym == sym) & ((tb.ts - d).abs() <= pd.Timedelta(days=DAYS))]
    px = near[(near.entry - m["entry"]).abs() / m["entry"] * 100 <= TOL]
    same = px[px["dir"] == want]
    opp = px[px["dir"] != want]
    if len(same):
        b = same.loc[same.grade.idxmax()]
        rows.append((m["id"], sym, want, str(d.date()), "MATCH",
                     f'g{int(b.grade)}', f'{b.entry:.1f}', str(b.ts)[5:16]))
    elif len(opp):
        b = opp.loc[opp.grade.idxmax()]
        rows.append((m["id"], sym, want, str(d.date()), "WRONG_DIR",
                     f'{b["dir"]} g{int(b.grade)}', f'{b.entry:.1f}', str(b.ts)[5:16]))
    elif len(near):
        rows.append((m["id"], sym, want, str(d.date()), "WRONG_PRICE",
                     f'{len(near)} sigs', f'{near.entry.min():.0f}-{near.entry.max():.0f}', ""))
    else:
        rows.append((m["id"], sym, want, str(d.date()), "NO_SIGNAL", "", "", ""))

r = pd.DataFrame(rows, columns=["mark", "sym", "want", "date", "verdict",
                                "found", "entry", "at"])
print(r.to_string(index=False))
tested = r[r.verdict != "NO_DATA"]
n = len(tested)
print(f"\nTESTABLE {n} of {len(marks)} 2026 marks (rest: symbol not in {Path(DATA).name})")
for v in ["MATCH", "WRONG_DIR", "WRONG_PRICE", "NO_SIGNAL"]:
    c = int((tested.verdict == v).sum())
    print(f"  {v:12} {c:3}  ({100*c/max(n,1):.0f}%)")
print(f"\nGATE: {'PASS' if (tested.verdict == 'MATCH').mean() >= 0.5 else 'FAIL'}"
      f" (>=50% of testable marks reproduced with correct direction)")
