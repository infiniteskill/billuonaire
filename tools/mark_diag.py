"""mark_diag.py — WHY the ground-truth gate fails, per mark.

ground_truth.py says 68% WRONG_PRICE, which lumps two very different failures:
  ZONE_MISS   -- no emitted zone even contains the user's entry price. Detection gap.
  TGT_WRONG   -- a zone DOES contain their entry, but we priced a different target,
                 so the strict entry+target match rejects it. Targeting gap.
  GRADE_LOW   -- zone + target both there, but graded below the trading cut.
Only the first is a detector problem; the other two are cheap to fix. This prints
the decomposition plus, for each mark, the best zone we actually had.

Usage: python3 tools/mark_diag.py <tradebook.csv> <data_dir> [tol_pct] [days] [cut]
"""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path("/home/doom/Public/PROJECT/2026/trader")
TB, DATA = sys.argv[1], sys.argv[2]
TOL = float(sys.argv[3]) if len(sys.argv) > 3 else 1.5
DAYS = int(sys.argv[4]) if len(sys.argv) > 4 else 3
CUT = int(sys.argv[5]) if len(sys.argv) > 5 else 5

DATED = ROOT / "tools/ytrades_dated.json"                   # real years, see mark_year.py
if DATED.exists():
    marks = json.loads(DATED.read_text())
else:
    marks = [dict(m, year=2026) for m in
             json.loads((ROOT / "tools/ytrades.json").read_text()) if m["month"] <= 7]
have = {p.stem for p in Path(DATA).glob("*.csv")}
tb = pd.read_csv(TB)
tb["ts"] = pd.to_datetime(tb["ts"]).dt.tz_localize(None)
tb = tb[(tb["mode"] == "eod") & tb.zone_lo.notna()]
DM = {"short": "SHORT", "long": "LONG"}

rows = []
SPAN = (tb.ts.min(), tb.ts.max())
for m in sorted(marks, key=lambda x: (x["year"], x["month"], x["day"])):
    sym, want, e, tg = m["stock"], DM[m["dir"]], m["entry"], m["target"]
    d = pd.Timestamp(f'{m["year"]}-{m["month"]:02d}-{m["day"]:02d}')
    if sym not in have:
        rows.append((m["id"], sym, "NO_DATA", "", "", "")); continue
    if not (SPAN[0] - pd.Timedelta(days=DAYS) <= d <= SPAN[1] + pd.Timedelta(days=DAYS)):
        rows.append((m["id"], sym, "OUT_OF_TAPE", "", "", "")); continue
    near = tb[(tb.sym == sym) & ((tb.ts - d).abs() <= pd.Timedelta(days=DAYS))
              & (tb["dir"] == want)]
    if not len(near):
        rows.append((m["id"], sym, "NO_SIGNAL", "", "", "")); continue
    lo = near[["zone_lo", "zone_hi"]].min(axis=1)
    hi = near[["zone_lo", "zone_hi"]].max(axis=1)
    inz = near[(lo <= e) & (e <= hi)]                       # zone brackets their entry
    if not len(inz):
        gap = ((near.entry - e).abs() / e * 100).min()
        # distance from their entry to the nearest zone EDGE, in that zone's own
        # heights: <1H means we drew the right shelf slightly off, >>1H means we
        # were looking somewhere else entirely.
        gh = ((lo - e).clip(lower=0) + (e - hi).clip(lower=0)) / (hi - lo).clip(lower=1e-9)
        rows.append((m["id"], sym, "ZONE_MISS", f"{len(near)} sigs",
                     f"nearest {gap:.2f}% off", f"{gh.min():.1f}H")); continue
    ok_t = inz[(inz.target - tg).abs() / e * 100 <= TOL]
    if not len(ok_t):
        b = inz.loc[inz.grade.idxmax()]
        rr_u = abs(tg - e) / max(abs(e - m["sl"]), 1e-9)
        rr_s = abs(b.target - b.entry) / max(abs(b.entry - b.sl), 1e-9)
        rows.append((m["id"], sym, "TGT_WRONG", f"g{int(b.grade)} in-zone",
                     f"tgt {b.target:.0f} vs want {tg:.0f}",
                     f"rr {rr_s:.1f} vs {rr_u:.1f}")); continue
    b = ok_t.loc[ok_t.grade.idxmax()]
    rows.append((m["id"], sym, "FULL_MATCH" if b.grade >= CUT else "GRADE_LOW",
                 f"g{int(b.grade)}", f"{b.entry:.1f}", str(b.ts)[5:16]))

r = pd.DataFrame(rows, columns=["mark", "sym", "verdict", "found", "detail", "extra"])
print(r.to_string(index=False))
t = r[~r.verdict.isin(["NO_DATA", "OUT_OF_TAPE"])]
print(f"\nTESTABLE {len(t)}")
for v, c in t.verdict.value_counts().items():
    print(f"  {v:12} {c:3}  ({100*c/len(t):.0f}%)")
reach = t.verdict.isin(["FULL_MATCH", "GRADE_LOW", "TGT_WRONG"]).sum()
print(f"\nZONE REACHABLE (entry price inside an emitted zone, right dir): "
      f"{reach}/{len(t)} ({100*reach/len(t):.0f}%)")
