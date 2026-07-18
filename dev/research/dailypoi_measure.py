"""Measure daily-POI anchoring: hit-edge, net expectancy, holdout money scan."""
import zlib
import numpy as np
import pandas as pd
from pathlib import Path

SP = Path("/tmp/claude-1000/-home-doom-Public-PROJECT-2026-trader/a013584c-0930-4f6c-921b-e4ea05cde0a4/scratchpad")
OUT = Path("/home/doom/Public/PROJECT/2026/trader/runs/long60/DAILYPOI.md")

sig = pd.read_parquet(SP / "signals60.parquet",
                      columns=["detector", "symbol", "session", "direction", "entry", "hit", "b_hit"])
sig = sig.reset_index().rename(columns={"index": "sig_id"})
tags = pd.read_parquet(SP / "dailypoi_tags.parquet")
sig = sig.merge(tags, on="sig_id", validate="1:1")
assert len(sig) == 300153

cfgmeta = pd.read_parquet(SP / "cfgmeta60.parquet")
CFG_T1 = int(cfgmeta[(cfgmeta.k == 1.5) & (cfgmeta.scheme == "fixed_t1")].cfg.iloc[0])
CFG_T3 = int(cfgmeta[(cfgmeta.k == 1.5) & (cfgmeta.scheme == "fixed_t3")].cfg.iloc[0])
cfg_name = {int(r.cfg): f"k{r.k:g}_{r.scheme}" for r in cfgmeta.itertuples()}

# ---- splits
sessions = sorted(sig.session.unique())
first_half = set(sessions[: len(sessions) // 2 + 1])          # 29 sessions
sig["t_half"] = sig.session.map(lambda s: 0 if s in first_half else 1)
sig["s_half"] = sig.symbol.map(lambda s: zlib.crc32(s.encode()) % 2)
sig["hit01"] = sig.hit.map({"hit": 1.0, "loss": 0.0})          # undecided -> NaN
sig["fresh"] = sig.in_daily_poi & (sig.poi_age_days <= 10)
sig["old"] = sig.in_daily_poi & (sig.poi_age_days > 10)
sig["edge_only"] = sig.in_daily_poi & ~sig.deep

DETS = sorted(sig.detector.unique())


def hit_edge(df):
    d = df.dropna(subset=["hit01"])
    if len(d) == 0:
        return (0, np.nan, np.nan, np.nan)
    return (len(d), d.hit01.mean(), d.b_hit.mean(), d.hit01.mean() - d.b_hit.mean())


# ================= Table 1: sample accounting =================
lines = []
lines.append("# DAILY-POI ANCHORING — top-down SMC test (60d, 300,153 signals)\n")
lines.append("Daily zones built CAUSALLY from yfinance 2y daily bars (bars strictly before each "
             "signal's session; invalidation also only from prior closes). Rules: OB = last "
             "opposite-color daily candle within 5 bars before a body>=1.5xATR14 displacement, "
             "zone = candle range, dies on daily close beyond far edge; FVG = 3-candle gap "
             ">=0.3xATR14, dies when filled (close beyond far edge); SWING = 2-2 fractal level "
             "(confirmed 2 bars later), dies on close beyond it. A signal is in-POI if its entry "
             "is inside a live direction-consistent zone +/- 0.25xdaily-ATR14.\n")

nh = sig.has_daily.mean()
frac = sig.in_daily_poi.mean()
lines.append("## Sample accounting\n")
lines.append(f"- daily bars matched: {nh:.1%} of signals ({sig.has_daily.sum():,}); "
             f"in-POI: **{frac:.1%}** ({sig.in_daily_poi.sum():,})")
tv = sig[sig.in_daily_poi].poi_type.value_counts()
lines.append(f"- by primary type: {dict(tv)}; overlaps: in_ob={sig.in_ob.sum():,} "
             f"in_fvg={sig.in_fvg.sum():,} in_swing={sig.in_swing.sum():,}")
lines.append(f"- fresh (age<=10 trading days): {sig.fresh.sum():,}; old: {sig.old.sum():,}; "
             f"deep-inside raw zone: {sig.deep.sum():,}; edge-band only: {sig.edge_only.sum():,}\n")

lines.append("| detector | n | n in-POI | % in-POI |")
lines.append("|---|---|---|---|")
for d in DETS + ["ALL"]:
    g = sig if d == "ALL" else sig[sig.detector == d]
    lines.append(f"| {d} | {len(g):,} | {g.in_daily_poi.sum():,} | {g.in_daily_poi.mean():.1%} |")

# ================= Table 2: hit-edge in vs out =================
lines.append("\n## Hit-edge (hit% vs parquet baseline b_hit; decided signals only)\n")
lines.append("| detector | n in | hit% in | edge in | n out | hit% out | edge out | d(edge) |")
lines.append("|---|---|---|---|---|---|---|---|")
pooled_rows = {}
for d in DETS + ["ALL"]:
    g = sig if d == "ALL" else sig[sig.detector == d]
    ni, hi_, bi, ei = hit_edge(g[g.in_daily_poi])
    no, ho, bo, eo = hit_edge(g[~g.in_daily_poi])
    lines.append(f"| {d} | {ni:,} | {hi_:.1%} | {ei:+.1%} | {no:,} | {ho:.1%} | {eo:+.1%} | "
                 f"{(ei - eo):+.1%} |")
    if d == "ALL":
        pooled_rows["hit"] = (ni, hi_, ei, no, ho, eo)

# by POI sub-condition, pooled
lines.append("\n| condition (pooled) | n | hit% | b_hit | edge |")
lines.append("|---|---|---|---|---|")
conds = [("out-of-POI", ~sig.in_daily_poi), ("in-POI (any)", sig.in_daily_poi),
         ("in OB", sig.in_ob), ("in FVG", sig.in_fvg), ("in SWING", sig.in_swing),
         ("fresh (<=10d)", sig.fresh), ("old (>10d)", sig.old),
         ("deep-inside", sig.deep), ("edge-band only", sig.edge_only)]
for name, m in conds:
    n, h_, b_, e_ = hit_edge(sig[m])
    lines.append(f"| {name} | {n:,} | {h_:.1%} | {b_:.1%} | {e_:+.1%} |")

# ================= net expectancy =================
res = pd.read_parquet(SP / "res60.parquet", columns=["sig_id", "cfg", "net_R"])
meta_cols = {}
for c in ["t_half", "s_half"]:
    meta_cols[c] = sig[c].to_numpy(np.int8)
det_codes = {d: i for i, d in enumerate(DETS)}
det_arr = sig.detector.map(det_codes).to_numpy(np.int8)
flag_arrs = {name: m.to_numpy(bool) for name, m in conds if name != "out-of-POI"}
inpoi_arr = sig.in_daily_poi.to_numpy(bool)

sid = res.sig_id.to_numpy()
res["det"] = det_arr[sid]
res["t_half"] = meta_cols["t_half"][sid]
res["s_half"] = meta_cols["s_half"][sid]
res["in_poi"] = inpoi_arr[sid]

lines.append("\n## Net expectancy (mean net_R, realistic costs) at k=1.5 fixed_t1 / fixed_t3\n")
lines.append("| detector | cfg | n in | net_R in | n out | net_R out | d |")
lines.append("|---|---|---|---|---|---|---|")
for cfg, tag in [(CFG_T1, "fixed_t1"), (CFG_T3, "fixed_t3")]:
    sub = res[res.cfg == cfg]
    for d in DETS + ["ALL"]:
        g = sub if d == "ALL" else sub[sub.det == det_codes[d]]
        gi, go = g[g.in_poi], g[~g.in_poi]
        lines.append(f"| {d} | k1.5 {tag} | {len(gi):,} | {gi.net_R.mean():+.4f} | "
                     f"{len(go):,} | {go.net_R.mean():+.4f} | "
                     f"{gi.net_R.mean() - go.net_R.mean():+.4f} |")
        if d == "ALL":
            pooled_rows[tag] = (len(gi), gi.net_R.mean(), len(go), go.net_R.mean())

# sub-conditions at the two headline cfgs
lines.append("\n| condition (pooled) | cfg | n | net_R |")
lines.append("|---|---|---|---|")
for cfg, tag in [(CFG_T1, "fixed_t1"), (CFG_T3, "fixed_t3")]:
    sub = res[res.cfg == cfg]
    for name, m in conds:
        arr = m.to_numpy(bool)
        g = sub[arr[sub.sig_id.to_numpy()]]
        lines.append(f"| {name} | k1.5 {tag} | {len(g):,} | {g.net_R.mean():+.4f} |")

# ================= holdout money scan =================
lines.append("\n## Money scan: (detector x condition x cfg), n>=200, holdout-stable?\n")
lines.append("Stable = mean net_R > 0 overall AND in both temporal halves AND both "
             "crc32(symbol)%2 halves. Scanned all 28 cfgs x 8 detectors(+ALL) x 8 conditions.\n")

scan_conds = [("in_poi", inpoi_arr)] + [(n.replace(" ", "_"), a) for n, a in flag_arrs.items()
                                        if n != "in-POI (any)"]
winners = []
near = []
sid_all = res.sig_id.to_numpy()
for cname, arr in scan_conds:
    subm = res[arr[sid_all]]
    grp = subm.groupby(["det", "cfg"], observed=True)
    stats = grp.net_R.agg(["size", "mean"])
    splits = subm.groupby(["det", "cfg", "t_half"], observed=True).net_R.mean().unstack()
    ssplits = subm.groupby(["det", "cfg", "s_half"], observed=True).net_R.mean().unstack()
    # pooled across detectors
    pstats = subm.groupby("cfg").net_R.agg(["size", "mean"])
    pt = subm.groupby(["cfg", "t_half"]).net_R.mean().unstack()
    ps = subm.groupby(["cfg", "s_half"]).net_R.mean().unstack()
    for (dcode, cfg), row in stats.iterrows():
        if row["size"] < 200:
            continue
        t0, t1 = splits.loc[(dcode, cfg)]
        s0, s1 = ssplits.loc[(dcode, cfg)]
        cell = (DETS[dcode], cname, cfg_name[cfg], int(row["size"]), row["mean"], t0, t1, s0, s1)
        if row["mean"] > 0 and min(t0, t1, s0, s1) > 0:
            winners.append(cell)
        elif row["mean"] > 0:
            near.append(cell)
    for cfg, row in pstats.iterrows():
        if row["size"] < 200:
            continue
        t0, t1 = pt.loc[cfg]
        s0, s1 = ps.loc[cfg]
        cell = ("ALL", cname, cfg_name[cfg], int(row["size"]), row["mean"], t0, t1, s0, s1)
        if row["mean"] > 0 and min(t0, t1, s0, s1) > 0:
            winners.append(cell)
        elif row["mean"] > 0:
            near.append(cell)

hdr = "| detector | condition | cfg | n | net_R | T1 | T2 | S0 | S1 |"


def fmt(c):
    return (f"| {c[0]} | {c[1]} | {c[2]} | {c[3]:,} | {c[4]:+.4f} | {c[5]:+.3f} | {c[6]:+.3f} "
            f"| {c[7]:+.3f} | {c[8]:+.3f} |")


if winners:
    winners.sort(key=lambda c: -c[4])
    lines.append(f"**{len(winners)} HOLDOUT-STABLE NET-POSITIVE cells found:**\n")
    lines.append(hdr)
    lines.append("|---|---|---|---|---|---|---|---|---|")
    lines += [fmt(c) for c in winners[:40]]
else:
    lines.append("**NO holdout-stable net-positive cell found.**\n")
if near:
    near.sort(key=lambda c: -c[4])
    lines.append(f"\nNet-positive overall but NOT holdout-stable ({len(near)} cells, top 15):\n")
    lines.append(hdr)
    lines.append("|---|---|---|---|---|---|---|---|---|")
    lines += [fmt(c) for c in near[:15]]

# out-of-POI control scan (does removing the filter also show positives? context)
subm = res[~inpoi_arr[sid_all]]
octl = []
for (dcode, cfg), row in subm.groupby(["det", "cfg"]).net_R.agg(["size", "mean"]).iterrows():
    if row["size"] >= 200 and row["mean"] > 0:
        octl.append((DETS[dcode], cfg_name[cfg], int(row["size"]), row["mean"]))
lines.append(f"\nControl: out-of-POI net-positive (det,cfg) cells (any, no holdout req): "
             f"{len(octl)}"
             + (" — " + "; ".join(f"{a} {b} n={c} {d:+.3f}" for a, b, c, d in octl[:8]) if octl else ""))

with open(SP / "dailypoi_result_cache.txt", "w") as f:
    f.write("\n".join(lines))
print("\n".join(lines))
