"""Measure NESTED FRACTAL CONFLUENCE levels -> runs/long60/NESTED.md."""
import zlib
import numpy as np
import pandas as pd
from pathlib import Path

SP = Path("/tmp/claude-1000/-home-doom-Public-PROJECT-2026-trader/a013584c-0930-4f6c-921b-e4ea05cde0a4/scratchpad")
OUT = Path("/home/doom/Public/PROJECT/2026/trader/runs/long60/NESTED.md")

sig = pd.read_parquet(SP / "signals60.parquet",
                      columns=["detector", "symbol", "session", "direction", "hit", "b_hit"])
sig = sig.reset_index().rename(columns={"index": "sig_id"})
flags = pd.read_parquet(SP / "nested_flags.parquet")
sig = sig.merge(flags, on="sig_id", validate="1:1")
assert len(sig) == 300153

cfgmeta = pd.read_parquet(SP / "cfgmeta60.parquet")
CFG_T1 = int(cfgmeta[(cfgmeta.k == 1.5) & (cfgmeta.scheme == "fixed_t1")].cfg.iloc[0])
CFG_T3 = int(cfgmeta[(cfgmeta.k == 1.5) & (cfgmeta.scheme == "fixed_t3")].cfg.iloc[0])
cfg_name = {int(r.cfg): f"k{r.k:g}_{r.scheme}" for r in cfgmeta.itertuples()}

res = pd.read_parquet(SP / "res60.parquet", columns=["sig_id", "cfg", "net_R"])
net1 = np.full(len(sig), np.nan, np.float64)
net3 = np.full(len(sig), np.nan, np.float64)
r1 = res[res.cfg == CFG_T1]
r3 = res[res.cfg == CFG_T3]
net1[r1.sig_id.to_numpy()] = r1.net_R.to_numpy()
net3[r3.sig_id.to_numpy()] = r3.net_R.to_numpy()
sig["net1"], sig["net3"] = net1, net3
sig["win"] = sig.net1 > 0
sig["hit01"] = sig.hit.map({"hit": 1.0, "loss": 0.0})

sessions = sorted(sig.session.unique())
first_half = set(sessions[: len(sessions) // 2 + 1])
sig["t_half"] = sig.session.map(lambda s: 0 if s in first_half else 1).astype(np.int8)
sig["s_half"] = sig.symbol.map(lambda s: zlib.crc32(s.encode()) % 2).astype(np.int8)

d = sig.direction.to_numpy()
agree_h = sig.h1_dir.to_numpy() == d
agree_d = sig.daily_dir.to_numpy() == d
l1 = sig.l1.to_numpy()
l2 = sig.l2.to_numpy()
in_h1z = sig.in_h1z.to_numpy()

LEVELS = [
    ("L0 any signal", np.ones(len(sig), bool)),
    ("L1 in daily zone", l1),
    ("L2 L1+H1 zone nested in daily", l2),
    ("L3 L2+all dirs agree", l2 & agree_h & agree_d),
    ("L3relaxed L2+(h1|daily dir)", l2 & (agree_h | agree_d)),
    ("CTRL L2' H1 zone only", in_h1z),
    ("CTRL L3' dirs only", agree_h & agree_d),
    ("CTRL L1+dirs (no H1 zone)", l1 & agree_h & agree_d),
    ("CTRL H1zone+dirs (no daily)", in_h1z & agree_h & agree_d),
]
liq_away = sig.liq_away.to_numpy()
liq_into = sig.liq_into.to_numpy()
swept = sig.swept_rec.to_numpy()
l2_liq = sig.l2_liq.to_numpy()
LIQ = [
    ("L1_liq_away (unswept pool, targets away)", liq_away),
    ("L1_liq_into (unswept pool, targets into)", liq_into),
    ("L1_swept (pool swept<=6 H1 bars, reclaim dir)", swept),
    ("L2_liq (L1_swept + H1 zone on pool)", l2_liq),
    ("L3_liq (L2_liq + h1_dir agrees)", l2_liq & agree_h),
    ("X1 dailyL1 & L1_swept", l1 & swept),
    ("X2 dailyL2 & L1_swept", l2 & swept),
    ("X3 X2 & all dirs agree (full model)", l2 & swept & agree_h & agree_d),
    ("X4 dailyL2 & L2_liq", l2 & l2_liq),
    ("X5 dailyL1 & liq_away", l1 & liq_away),
    ("X6 dailyL2 & liq_away", l2 & liq_away),
]

base = sig
w0 = base.win.mean()
h0 = base.hit01.mean()


def row(name, m):
    g = sig[m]
    n = len(g)
    if n == 0:
        return f"| {name} | 0 | - | - | - | - | - | - |"
    w = g.win.mean()
    gd = g.dropna(subset=["hit01"])
    hp = gd.hit01.mean() if len(gd) else np.nan
    edge = hp - gd.b_hit.mean() if len(gd) else np.nan
    return (f"| {name} | {n:,} | {w:.1%} | {(w - w0) * 100:+.1f}pp | {hp:.1%} | {edge:+.1%} | "
            f"{g.net1.mean():+.4f} | {g.net3.mean():+.4f} |")


HDR = ("| level | n | win% (k1.5 t1) | d vs L0 | hit% | hit-edge | netR t1 | netR t3 |\n"
       "|---|---|---|---|---|---|---|---|")

lines = ["# NESTED FRACTAL CONFLUENCE — daily zone > H1 OB/FVG > M5 signal (+ liquidity-pool nest)\n"]
lines.append(
    "**The bar to clear:** base win ~49% at 1:1 (decided-only hit%; net win%(k1.5 fixed_t1)="
    f"{w0:.1%} on all 300,153 signals); breakeven at adequate capital ~55%; every prior "
    "conditioning gave <=+2pp. The nest must deliver **>=+6pp holdout-stable** to matter.\n")
lines.append(
    "Build (leak-free; for each signal only bars with end<=ts): H1 = session-anchored 5m "
    "aggregation, 15:15 stub merged into 14:15 bar (6 bars/session). H1 zones: OB = last "
    "opposite-color H1 candle within 5 bars before body>=1.5xATR14(H1) displacement, dies on H1 "
    "close beyond far edge; FVG = 3-candle gap >=0.3xATR14(H1), dies when a later H1 wick fully "
    "fills the gap. Daily zones: exact dailypoi_build rules (L1 parity with dailypoi_tags = "
    "100%). Zone-in-zone: H1 zone midpoint inside matched daily zone +/-0.25xdailyATR; signal "
    "inside H1 zone +/-0.25xH1ATR, direction-consistent. Directions: close>SMA20 (daily bars "
    "strictly before session; closed H1 bars only; m5 = signal direction). Liquidity pools: "
    "unswept H1 2-2 fractal swings, equal-H/L clusters (<=0.15xATR_H1, level=extreme), PDH/PDL, "
    "prior-week H/L; sweeps/reclaims detected on closed 5m bars; L1_swept window = 6 H1 bars; "
    "pool proximity = 0.5xATR_H1 (H1 ATR used, documented choice).\n")

lines.append("## Funnel — daily-zone nest (pooled)\n")
lines.append(HDR)
for name, m in LEVELS:
    lines.append(row(name, m))

lines.append("\n## Funnel — liquidity-pool nest + cross (pooled)\n")
lines.append(HDR)
for name, m in LIQ:
    lines.append(row(name, m))

# per-detector L3 (and L2)
DETS = sorted(sig.detector.unique())
lines.append("\n## Per-detector: L2 / L3 (daily nest)\n")
lines.append("| detector | n L2 | win L2 | n L3 | win L3 | d L3 vs det-L0 | netR t1 L3 |")
lines.append("|---|---|---|---|---|---|---|")
det_arr = sig.detector.to_numpy()
for det in DETS:
    dm = det_arr == det
    dw0 = sig.win[dm].mean()
    g2, g3 = sig[dm & l2], sig[dm & l2 & agree_h & agree_d]
    w2 = f"{g2.win.mean():.1%}" if len(g2) else "-"
    w3 = f"{g3.win.mean():.1%}" if len(g3) else "-"
    d3 = f"{(g3.win.mean() - dw0) * 100:+.1f}pp" if len(g3) else "-"
    n1 = f"{g3.net1.mean():+.4f}" if len(g3) else "-"
    lines.append(f"| {det} | {len(g2):,} | {w2} | {len(g3):,} | {w3} | {d3} | {n1} |")

# holdout cells
lines.append("\n## Holdout cells (temporal half x crc32(symbol)%2) — win% at k1.5 fixed_t1\n")
lines.append("| cell | n L0 | win L0 | n L3 | win L3 | d | n L3rlx | win L3rlx | d | n X3 | win X3 | d |")
lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
l3 = l2 & agree_h & agree_d
l3r = l2 & (agree_h | agree_d)
x3 = l2 & swept & agree_h & agree_d
for th in (0, 1):
    for sh in (0, 1):
        cm = (sig.t_half.to_numpy() == th) & (sig.s_half.to_numpy() == sh)
        c0 = sig.win[cm]
        parts = [f"| T{th}S{sh} | {cm.sum():,} | {c0.mean():.1%} "]
        for mm in (l3, l3r, x3):
            g = sig.win[cm & mm]
            if len(g):
                parts.append(f"| {len(g):,} | {g.mean():.1%} | {(g.mean() - c0.mean()) * 100:+.1f}pp ")
            else:
                parts.append("| 0 | - | - ")
        lines.append("".join(parts) + "|")

# money scan: all 28 cfgs x (levels+liq) x detectors(+ALL), n>=200
lines.append("\n## Money scan (all 28 cfgs x level x detector, n>=200)\n")
lines.append("Positive = mean net_R>0 overall; stable = also >0 in both temporal and both symbol halves.\n")
sid = res.sig_id.to_numpy()
res_det = det_arr[sid]
res_t = sig.t_half.to_numpy()[sid]
res_s = sig.s_half.to_numpy()[sid]
winners, near = [], []
ALLM = LEVELS[1:] + LIQ
for lname, m in ALLM:
    rm = m[sid]
    sub = res[rm]
    if not len(sub):
        continue
    sub = sub.assign(det=res_det[rm], t=res_t[rm], s=res_s[rm])
    for scope, gsub in [("ALL", sub)] + [(dd, sub[sub.det == dd]) for dd in DETS]:
        st = gsub.groupby("cfg").net_R.agg(["size", "mean"])
        tt = gsub.groupby(["cfg", "t"]).net_R.mean().unstack()
        ss = gsub.groupby(["cfg", "s"]).net_R.mean().unstack()
        for cfg, rr in st.iterrows():
            if rr["size"] < 200 or rr["mean"] <= 0:
                continue
            t0, t1 = (tt.loc[cfg] if cfg in tt.index else (np.nan, np.nan))
            s0, s1 = (ss.loc[cfg] if cfg in ss.index else (np.nan, np.nan))
            cell = (scope, lname, cfg_name[int(cfg)], int(rr["size"]), rr["mean"], t0, t1, s0, s1)
            if min(t0, t1, s0, s1) > 0:
                winners.append(cell)
            else:
                near.append(cell)

MHDR = ("| scope | level | cfg | n | net_R | T0 | T1 | S0 | S1 |\n"
        "|---|---|---|---|---|---|---|---|---|")


def fmt(c):
    return (f"| {c[0]} | {c[1]} | {c[2]} | {c[3]:,} | {c[4]:+.4f} | {c[5]:+.3f} | {c[6]:+.3f} | "
            f"{c[7]:+.3f} | {c[8]:+.3f} |")


if winners:
    winners.sort(key=lambda c: -c[4])
    lines.append(f"**{len(winners)} HOLDOUT-STABLE net-positive cells:**\n\n" + MHDR)
    lines += [fmt(c) for c in winners[:40]]
else:
    lines.append("**NO holdout-stable net-positive cell (n>=200) at any cfg.**")
if near:
    near.sort(key=lambda c: -c[4])
    lines.append(f"\nNet-positive overall but NOT holdout-stable ({len(near)} cells, top 12):\n\n" + MHDR)
    lines += [fmt(c) for c in near[:12]]

with open(SP / "nested_result_cache.txt", "w") as f:
    f.write("\n".join(lines))
print("\n".join(lines))
