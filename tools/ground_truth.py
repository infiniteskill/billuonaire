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
TOL = float(sys.argv[3]) if len(sys.argv) > 3 else 1.5     # entry+target tolerance %
DAYS = int(sys.argv[4]) if len(sys.argv) > 4 else 3        # date tolerance

DATED = ROOT / "tools/ytrades_dated.json"                   # real years, see mark_year.py
if DATED.exists():
    marks = json.loads(DATED.read_text())
else:                                                       # legacy: assume 2026
    marks = [dict(m, year=2026) for m in
             json.loads((ROOT / "tools/ytrades.json").read_text()) if m["month"] <= 7]
have = {p.stem for p in Path(DATA).glob("*.csv")}
tb = pd.read_csv(TB)
tb["ts"] = pd.to_datetime(tb["ts"]).dt.tz_localize(None)
tb = tb[tb["mode"] == "eod"]
SPAN = (tb.ts.min(), tb.ts.max())                           # what this tape can judge

DM = {"short": "SHORT", "long": "LONG"}
rows = []
for m in sorted(marks, key=lambda x: (x["year"], x["month"], x["day"])):
    sym, want = m["stock"], DM[m["dir"]]
    d = pd.Timestamp(f'{m["year"]}-{m["month"]:02d}-{m["day"]:02d}')
    if sym not in have:
        rows.append((m["id"], sym, want, str(d.date()), "NO_DATA", "", "", ""))
        continue
    if not (SPAN[0] - pd.Timedelta(days=DAYS) <= d <= SPAN[1] + pd.Timedelta(days=DAYS)):
        rows.append((m["id"], sym, want, str(d.date()), "OUT_OF_TAPE", "", "", ""))
        continue
    near = tb[(tb.sym == sym) & ((tb.ts - d).abs() <= pd.Timedelta(days=DAYS))]
    px = near[(near.entry - m["entry"]).abs() / m["entry"] * 100 <= TOL]
    px = px[(px.target - m["target"]).abs() / m["entry"] * 100 <= TOL]   # SAME TRADE:
    same = px[px["dir"] == want]                                        # entry AND target
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
tested = r[~r.verdict.isin(["NO_DATA", "OUT_OF_TAPE"])]
n = len(tested)
print(f"\nMARKS {len(marks)} | no symbol data {int((r.verdict=='NO_DATA').sum())}"
      f" | outside this tape's {str(SPAN[0])[:10]}..{str(SPAN[1])[:10]}"
      f" {int((r.verdict=='OUT_OF_TAPE').sum())}")
print(f"TESTABLE {n}")
for v in ["MATCH", "WRONG_DIR", "WRONG_PRICE", "NO_SIGNAL"]:
    c = int((tested.verdict == v).sum())
    print(f"  {v:12} {c:3}  ({100*c/max(n,1):.0f}%)")
print(f"\nGATE: {'PASS' if (tested.verdict == 'MATCH').mean() >= 0.5 else 'FAIL'}"
      f" (>=50% of testable marks reproduced with correct direction)")
