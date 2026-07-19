#!/usr/bin/env python
"""h1grid step 3: aggregate trade results into the cell grid + gauntlet.

Cell = tf x ztype x flag-subset x geometry (k, exit-cfg). excess = mean net_R
minus mean matched-null net_R. Gauntlet: pooled excess>0 AND excess>0 in all 3
temporal thirds AND in both crc32(symbol)%2 halves => ALIVE.
Outputs h1grid_cells.csv + console tables.
"""
import numpy as np
import pandas as pd

SCRATCH = "/tmp/claude-1000/-home-doom-Public-PROJECT-2026-trader/a013584c-0930-4f6c-921b-e4ea05cde0a4/scratchpad"
SUBSETS = [("none", []), ("F1", ["F1"]), ("F1+F2", ["F1", "F2"]),
           ("F1+F3", ["F1", "F3"]), ("F1+F2+F3", ["F1", "F2", "F3"]), ("F4", ["F4"])]
GEOMS = ["k1.5/2R/10s", "k1.5/1.5R/5s", "k2.5/2R/10s", "k2.5/1.5R/5s"]

frames = []
for tf in ("h1", "h2"):
    d = pd.read_parquet(f"{SCRATCH}/h1grid_res_{tf}.parquet")
    nb = pd.read_parquet(f"{SCRATCH}/h1grid_nullb_{tf}.parquet")
    d = d.merge(nb, on=["symbol", "entry_ts", "dir", "geom"], how="left")
    d["tf"] = tf
    frames.append(d)
res = pd.concat(frames, ignore_index=True)
res = res[res.nullB_R.notna()].reset_index(drop=True)
res["ts"] = pd.to_datetime(res.entry_ts, utc=True)
t0, t1 = res.ts.min(), res.ts.max()
edges = [t0 + (t1 - t0) * f for f in (1 / 3, 2 / 3)]
res["third"] = np.where(res.ts < edges[0], 0, np.where(res.ts < edges[1], 1, 2))
span_years = (t1 - t0).days / 365.25

rows = []
for (tf, zt, geom), g in res.groupby(["tf", "ztype", "geom"]):
    for sname, flags in SUBSETS:
        m = np.ones(len(g), bool)
        for f in flags:
            m &= g[f].values
        s = g[m]
        if len(s) < 30:
            rows.append(dict(tf=tf, ztype=zt, subset=sname, geom=GEOMS[geom],
                             n=len(s), alive=False, note="n<30"))
            continue
        ex = s.net_R.mean() - s.null_R.mean()
        exB = s.net_R.mean() - s.nullB_R.mean()
        thirds = [s[s.third == k] for k in range(3)]
        tex = [t.net_R.mean() - t.null_R.mean() if len(t) >= 10 else np.nan
               for t in thirds]
        texB = [t.net_R.mean() - t.nullB_R.mean() if len(t) >= 10 else np.nan
                for t in thirds]
        halves = [s[s.symhalf == h] for h in (0, 1)]
        hex_ = [h.net_R.mean() - h.null_R.mean() if len(h) >= 10 else np.nan
                for h in halves]
        hexB = [h.net_R.mean() - h.nullB_R.mean() if len(h) >= 10 else np.nan
                for h in halves]
        alive = (ex > 0 and all(np.isfinite(v) and v > 0 for v in tex)
                 and all(np.isfinite(v) and v > 0 for v in hex_))
        aliveB = (exB > 0 and all(np.isfinite(v) and v > 0 for v in texB)
                  and all(np.isfinite(v) and v > 0 for v in hexB))
        rows.append(dict(
            tf=tf, ztype=zt, subset=sname, geom=GEOMS[geom], n=len(s),
            net_R=round(s.net_R.mean(), 4), null_R=round(s.null_R.mean(), 4),
            excess=round(ex, 4), nullB_R=round(s.nullB_R.mean(), 4),
            excessB=round(exB, 4),
            ex_y1=round(tex[0], 4), ex_y2=round(tex[1], 4), ex_y3=round(tex[2], 4),
            ex_h0=round(hex_[0], 4), ex_h1=round(hex_[1], 4),
            exB_y1=round(texB[0], 4), exB_y2=round(texB[1], 4),
            exB_y3=round(texB[2], 4),
            exB_h0=round(hexB[0], 4), exB_h1=round(hexB[1], 4),
            trades_q=round(len(s) / (span_years * 4), 1), alive=alive,
            aliveB=aliveB, note=""))

cells = pd.DataFrame(rows)
cells.to_csv(f"{SCRATCH}/h1grid_cells.csv", index=False)
full = cells[cells.note == ""]
print(f"cells examined: {len(cells)} (evaluable n>=30: {len(full)})")
print(f"span years: {span_years:.2f}")
print(f"\nALIVE (month-null): {full.alive.sum()}  ALIVE-B (time-local null): "
      f"{full.aliveB.sum()}  ALIVE both: {(full.alive & full.aliveB).sum()}")
print(f"pooled excess>0: {(full.excess > 0).sum()} of {len(full)}; "
      f"excessB>0: {(full.excessB > 0).sum()}; "
      f"net_R>0: {(full.net_R > 0).sum()}")
print(f"\nexcess distribution: mean={full.excess.mean():.4f} "
      f"med={full.excess.median():.4f} min={full.excess.min():.4f} "
      f"max={full.excess.max():.4f}")
SHOW = ["tf", "ztype", "subset", "geom", "n", "net_R", "null_R", "excess",
        "nullB_R", "excessB", "ex_y1", "ex_y2", "ex_y3", "ex_h0", "ex_h1",
        "trades_q", "alive", "aliveB"]
print("\n=== TOP 15 BY EXCESS (month-null) ===")
print(full.sort_values("excess", ascending=False).head(15)[SHOW].to_string(index=False))
print("\n=== TOP 15 BY EXCESS-B (time-local null) ===")
print(full.sort_values("excessB", ascending=False).head(15)[SHOW].to_string(index=False))
print("\n=== per tf x ztype (subset=none, best geom by excess) ===")
base = full[full.subset == "none"]
idx = base.groupby(["tf", "ztype"]).excess.idxmax()
print(base.loc[idx][SHOW].to_string(index=False))
print("\n=== net_R vs nulls pooled per tf ===")
print(res.groupby("tf")[["net_R", "null_R", "nullB_R"]].mean())
if (full.alive & full.aliveB).any():
    print("\n=== SURVIVORS OF BOTH NULLS ===")
    print(full[full.alive & full.aliveB][SHOW].to_string(index=False))
