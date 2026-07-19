"""Aggregate taught-OB entry-depth measurement tables."""
import numpy as np, pandas as pd

OUT = "/tmp/claude-1000/-home-doom-Public-PROJECT-2026-trader/a013584c-0930-4f6c-921b-e4ea05cde0a4/scratchpad/"
ep = pd.read_parquet(OUT + "tob_episodes.parquet")
ep["ts0"] = pd.to_datetime(ep["ts0"], utc=True)
POL = ("EDGE", "CE", "OTE")

def pol_table(d, label):
    rows = []
    for p in POL:
        f = d[d[f"{p}_fill"]]
        n, nf = len(d), len(f)
        rows.append(dict(pol=p, n_ep=n, fills=nf, fill_pct=100 * nf / n if n else np.nan,
                         hit_pct=100 * f[f"{p}_win"].mean() if nf else np.nan,
                         grossR=f[f"{p}_gross"].mean() if nf else np.nan,
                         netR=f[f"{p}_net"].mean() if nf else np.nan,
                         netR_med=f[f"{p}_net"].median() if nf else np.nan))
    t = pd.DataFrame(rows)
    print(f"\n== {label} (episodes={len(d)}) ==")
    print(t.round(3).to_string(index=False))
    return t

print(f"total episodes: {len(ep)}  syms: {ep.sym.nunique()}")
print(ep.groupby('type').size().to_string())
w = ep.wait_bars
print(f"\nwait to first revisit (bars, ~7/session): med={w.median():.0f} "
      f"p25={w.quantile(.25):.0f} p75={w.quantile(.75):.0f} "
      f">=1wk(35b): {100*(w>=35).mean():.0f}%  >=1mo(150b): {100*(w>=150).mean():.0f}%")

for t in ("OB", "FVG", "IOB", "IFVG"):
    pol_table(ep[ep.type == t], f"type={t}")

# ---- depth distribution + EDGE outcome by depth (descriptive: depth measured
# over the trade span itself -> conditioning, not a tradeable filter)
ob = ep[ep.type == "OB"].copy()
print("\n== OB penetration depth on first revisit (box fraction; >1 = through) ==")
q = ob.depth.quantile([.1, .25, .5, .75, .9]).round(2)
print(q.to_string())
bins = [-0.01, 0.25, 0.5, 0.705, 1.0, 99]
labs = ["0-.25 edge", ".25-.50", ".50-.705", ".705-1.0", ">1 through"]
ob["dbkt"] = pd.cut(ob.depth, bins, labels=labs)
g = ob[ob.EDGE_fill].groupby("dbkt", observed=True).agg(
    n=("EDGE_net", "size"), hit=("EDGE_win", lambda x: 100 * x.mean()),
    netR=("EDGE_net", "mean"))
print("\nEDGE outcome by max depth reached (descriptive):")
print(g.round(3).to_string())
print("depth share:", (ob.dbkt.value_counts(normalize=True).sort_index() * 100).round(1).to_dict())

# ---- swing-nearness (power claim): OB only, dist_atr buckets
print("\n== OB: swing-nearness rank vs outcome (EDGE policy) ==")
nb = [-0.01, 0.001, 2, 5, 999]
nl = ["0 (at pivot)", "0-2 ATR", "2-5 ATR", ">5 ATR (mid-leg)"]
ob["nbkt"] = pd.cut(ob.dist_atr, nb, labels=nl)
for p in POL:
    f = ob[ob[f"{p}_fill"]]
    g = f.groupby("nbkt", observed=True).agg(
        n=(f"{p}_net", "size"), hit=(f"{p}_win", lambda x: 100 * x.mean()),
        netR=(f"{p}_net", "mean"))
    print(f"[{p}]"); print(g.round(3).to_string())

# ---- overlap grade
print("\n== OB: overlap confluence (n_ov) vs EDGE outcome ==")
ob["ovbkt"] = pd.cut(ob.n_ov, [-1, 0, 2, 999], labels=["0", "1-2", "3+"])
g = ob[ob.EDGE_fill].groupby("ovbkt", observed=True).agg(
    n=("EDGE_net", "size"), hit=("EDGE_win", lambda x: 100 * x.mean()),
    netR=("EDGE_net", "mean"))
print(g.round(3).to_string())

# ---- holdout: temporal thirds + crc32%2 (per policy, OB and FVG)
print("\n== holdout: netR by temporal third x sym-half ==")
tq = ep.ts0.quantile([1 / 3, 2 / 3])
ep["third"] = np.where(ep.ts0 <= tq.iloc[0], "T1",
                       np.where(ep.ts0 <= tq.iloc[1], "T2", "T3"))
print("third edges:", tq.dt.date.tolist())
for t in ("OB", "FVG"):
    d = ep[ep.type == t]
    for p in POL:
        f = d[d[f"{p}_fill"]]
        cells = []
        for th in ("T1", "T2", "T3"):
            for hf in (0, 1):
                c = f[(f.third == th) & (f.half == hf)]
                cells.append(f"{th}/H{hf}: n={len(c)} hit={100*c[f'{p}_win'].mean():.1f}% "
                             f"netR={c[f'{p}_net'].mean():+.3f}")
        print(f"[{t} {p}] " + " | ".join(cells))

# ---- wait-to-revisit cut (user prototype: visits days-weeks later)
print("\n== OB EDGE by wait-to-revisit (user's 'visit after days-weeks') ==")
ob["wbkt"] = pd.cut(ob.wait_bars, [-1, 7, 35, 150, 1e9],
                    labels=["<1 sess", "1s-1wk", "1wk-1mo", ">1mo"])
for p in POL:
    f = ob[ob[f"{p}_fill"]]
    g = f.groupby("wbkt", observed=True).agg(
        n=(f"{p}_net", "size"), hit=(f"{p}_win", lambda x: 100 * x.mean()),
        gross=(f"{p}_gross", "mean"), netR=(f"{p}_net", "mean"))
    print(f"[{p}]"); print(g.round(3).to_string())

print("\n== user's prototype cell: OB, at-pivot (dist=0), wait>=1wk ==")
for wmin, tag in ((35, ">=1wk"), (150, ">=1mo")):
    c = ob[(ob.dist_atr == 0) & (ob.wait_bars >= wmin) & ob.EDGE_fill]
    print(f"dist=0 wait{tag}: n={len(c)} hit={100*c.EDGE_win.mean():.1f}% "
          f"gross={c.EDGE_gross.mean():+.3f} netR={c.EDGE_net.mean():+.3f}")
    c2 = ob[(ob.dist_atr == 0) & (ob.wait_bars >= wmin) & (ob.n_ov >= 3) & ob.EDGE_fill]
    print(f"  +overlap>=3: n={len(c2)} hit={100*c2.EDGE_win.mean():.1f}% "
          f"netR={c2.EDGE_net.mean():+.3f}")

# ---- OTE position context
op = ep[ep.type == "OB"].ote_pos.dropna()
print(f"\nOTE level position in box (0=proximal edge,1=distal): "
      f"med={op.median():.2f} p25={op.quantile(.25):.2f} p75={op.quantile(.75):.2f} "
      f"outside(<0)={100*(op<0).mean():.0f}% beyond(>1)={100*(op>1).mean():.0f}%")
