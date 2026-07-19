"""Verify taught-OB detection vs user's hand-drawn HEROMOTOCO zones (Jan-Apr 2026)."""
import numpy as np, pandas as pd
from tob_lib import run_symbol, detect

DATA = "/home/doom/Public/PROJECT/2026/trader/runs/artifacts-data/l4_h1.parquet"
df = pd.read_parquet(DATA)
h = df[df.symbol == "HEROMOTOCO"].sort_values("ts").reset_index(drop=True)
zones, eps, meta = run_symbol(h, "HEROMOTOCO")
ts = h["ts"]
print(f"HEROMOTOCO: K={meta['K']:.2f} atr%={meta['atrp']*100:.2f} "
      f"pivots={meta['n_piv']} zones={len(zones)}")

TARGETS = [  # id, dir, lo, hi, born window, revisit window, types
    ("a", 1, 5300, 5350, ("2026-01-08", "2026-01-31"), ("2026-02-12", "2026-02-24"),
     ("OB", "IFVG", "FVG", "IOB")),
    ("b", -1, 5720, 5800, ("2026-02-01", "2026-02-14"), ("2026-03-08", "2026-03-20"),
     ("OB", "IFVG", "FVG", "IOB")),
    ("c", 1, 5430, 5480, ("2026-03-05", "2026-03-13"), (None, None),
     ("OB", "IFVG", "FVG", "IOB")),
]
TOL = 0.015

ep_by_key = {}
for e in eps:
    ep_by_key.setdefault((e["type"], e["dir"], round(e["lo"], 2), round(e["hi"], 2),
                          e["born_i"]), e)

def zrow(z):
    e = ep_by_key.get((z["type"], z["dir"], round(z["lo"], 2), round(z["hi"], 2),
                       z["born_i"]))
    rv = f"{e['ts0']}" if e else "none"
    ev_ts = ts.iloc[z["ev_i"]]
    return (f"  {z['type']:4s} d={z['dir']:+d} box=[{z['lo']:.1f},{z['hi']:.1f}] "
            f"born={ts.iloc[z['born_i']]:%Y-%m-%d %H:%M} ev={ev_ts:%m-%d %H:%M} "
            f"dist={z['dist_atr']:.2f}ATR ov={z['n_ov']} revisit={str(rv)[:16]}")

for tid, d, tlo, thi, (b0, b1), (r0, r1), types in TARGETS:
    print(f"\n### target ({tid}): dir={d:+d} band {tlo}-{thi} born {b0}..{b1}")
    b0p = pd.Timestamp(b0, tz="Asia/Kolkata") - pd.Timedelta(days=4)
    b1p = pd.Timestamp(b1, tz="Asia/Kolkata") + pd.Timedelta(days=4, hours=23)
    cands = []
    for z in zones:
        if z["dir"] != d or z["type"] not in types: continue
        bts = ts.iloc[z["born_i"]]
        if not (b0p <= bts <= b1p): continue
        # edge distance from target band to zone box (0 if overlap)
        gap = max(0.0, max(tlo - z["hi"], z["lo"] - thi)) / tlo
        if gap > TOL: continue
        inter = min(thi, z["hi"]) - max(tlo, z["lo"])
        cands.append((gap, -inter, z))
    cands.sort(key=lambda x: (x[0], x[1]))
    if not cands:
        print("  NO CANDIDATES in window+tolerance")
    for gap, _, z in cands[:8]:
        print(zrow(z) + f"  gap={gap*100:.2f}%")

# context: pivots + all zones born Jan-Apr for eyeballing
print("\n### pivots Jan-Apr 2026")
from ext_zigzag import wilder_atr, zigzag
atr = wilder_atr(h); K = meta["K"]
for p in zigzag(h, K, atr):
    t = ts.iloc[p.idx]
    if pd.Timestamp("2026-01-01", tz="Asia/Kolkata") <= t <= pd.Timestamp("2026-04-15", tz="Asia/Kolkata"):
        ct = ts.iloc[p.confirm_idx] if p.confirm_idx is not None else None
        print(f"  {p.side} {t:%Y-%m-%d %H:%M} {p.price:7.1f} conf={ct} "
              f"{'pending' if p.pending else ''}")
