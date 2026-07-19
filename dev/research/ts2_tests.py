"""ts2 tests T1-T5: respect ladder vs null, overlap monotonicity, pivot-distance
gradient, blow-through grading AUC, FVG-N recall. Holdout = temporal thirds x
crc32%2 halves; pass = same-sign lift in all 6 cells."""
import sys
import numpy as np, pandas as pd

SCR = "/tmp/claude-1000/-home-doom-Public-PROJECT-2026-trader/a013584c-0930-4f6c-921b-e4ea05cde0a4/scratchpad"
ep = pd.read_parquet(f"{SCR}/ts2_eps.parquet")
ep["ts0"] = pd.to_datetime(ep["ts0"])
if ep.ts0.dt.tz is not None: ep["ts0"] = ep.ts0.dt.tz_convert("UTC").dt.tz_localize(None)
b1, b2 = pd.Timestamp("2024-07-27 18:30"), pd.Timestamp("2025-07-22 18:30")  # IST thirds in UTC
ep["third"] = np.where(ep.ts0 < b1, 0, np.where(ep.ts0 < b2, 1, 2))
ep["cell"] = ep.third * 2 + ep.half
ep["lift"] = ep.resp - ep.null
V = ep[ep.null.notna()].copy()   # paired-null subset


def tstat(x):
    x = x[np.isfinite(x)]
    return (np.nan, 0) if len(x) < 3 else (x.mean() / (x.std(ddof=1) / np.sqrt(len(x))), len(x))


def tsym(sub):
    m = sub.groupby("sym")["lift"].mean()
    return tstat(m.values)[0]


def cells_sign(sub, fn):
    return [np.sign(fn(sub[sub.cell == c])) for c in range(6)]


def holdout(sub, fn):
    s = cells_sign(sub, fn)
    ps = np.sign(fn(sub))
    return ("PASS" if all(x == ps and x != 0 for x in s) else "FAIL"), s


def z2p(p1, n1, p0, n0):
    p = (p1 * n1 + p0 * n0) / (n1 + n0)
    se = np.sqrt(p * (1 - p) * (1 / n1 + 1 / n0))
    return (p1 - p0) / se if se > 0 else np.nan


def auc(score, y):  # P(score_pos > score_neg), ties=0.5
    s1, s0 = score[y == 1], score[y == 0]
    if not len(s1) or not len(s0): return np.nan
    r = pd.Series(np.concatenate([s1, s0])).rank().values
    return (r[:len(s1)].sum() - len(s1) * (len(s1) + 1) / 2) / (len(s1) * len(s0))


print("=" * 100)
print(f"episodes {len(ep)}  with-null {len(V)} ({len(V)/len(ep)*100:.1f}%)  "
      f"null draws/ep mean {V.nn.mean():.2f}")
print("\n================ T1: zone-type respect ladder vs matched null ================")
fam = {"OB": ["OB"], "FVG-N(all)": ["FVG3", "FVGN"], "FVG3": ["FVG3"], "FVGN": ["FVGN"],
       "IFVG": ["IFVG"], "BRK": ["BRK"], "MIT": ["MIT"], "REJ": ["REJ"], "PRP": ["PRP"]}
for name, tys in fam.items():
    s = V[V.ty.isin(tys)]
    if not len(s): continue
    ho = holdout(s, lambda x: x.lift.mean())
    t, _ = tstat(s.lift.values)
    print(f"{name:11s} n={len(s):6d} resp={s.resp.mean()*100:5.1f}% null={s.null.mean()*100:5.1f}% "
          f"lift={s.lift.mean()*100:+5.2f}pp t={t:+5.1f} t_sym={tsym(s):+5.1f} "
          f"holdout={ho[0]} cells={[f'{x:+.0f}' for x in ho[1]]}")

print("\n---- P2 breaker > mitigation (lesson 12) ----")
B, M = V[V.ty == "BRK"], V[V.ty == "MIT"]
z = z2p(B.resp.mean(), len(B), M.resp.mean(), len(M))
dif = lambda x: x[x.ty == "BRK"].resp.mean() - x[x.ty == "MIT"].resp.mean()
ho = holdout(V[V.ty.isin(["BRK", "MIT"])], dif)
print(f"BRK {B.resp.mean()*100:.1f}% (n={len(B)}) vs MIT {M.resp.mean()*100:.1f}% (n={len(M)}) "
      f"diff={dif(V)*100:+.2f}pp z={z:+.1f} lift diff={B.lift.mean()-M.lift.mean():+.4f} "
      f"holdout={ho[0]} cells={[f'{x:+.0f}' for x in ho[1]]}")

print("\n---- P3 propulsion parent-live > orphaned (lesson 14) ----")
P = V[V.ty == "PRP"]
pl, po = P[P.plive == 1], P[P.plive == 0]
if len(po) > 2:
    z = z2p(pl.resp.mean(), len(pl), po.resp.mean(), len(po))
    dif = lambda x: (x[x.plive == 1].resp.mean() - x[x.plive == 0].resp.mean()) \
        if (x.plive == 0).sum() and (x.plive == 1).sum() else 0
    ho = holdout(P, dif)
    print(f"live {pl.resp.mean()*100:.1f}% (n={len(pl)}) vs orphan {po.resp.mean()*100:.1f}% "
          f"(n={len(po)}) diff={dif(P)*100:+.2f}pp z={z:+.1f} holdout={ho[0]} "
          f"cells={[f'{x:+.0f}' for x in ho[1]]}")
else:
    print(f"orphan n={len(po)} too small")

print("\n---- P4 FVG CE terminus (lesson 2 midpoint law) ----")
G = ep[ep.ty.isin(["FVG3", "FVGN"]) & (ep.resp == 1) & (ep.depth <= 1)]
frac = ((G.depth - 0.5).abs() <= 0.15).mean()
zc = (frac - 0.30) / np.sqrt(0.30 * 0.70 / len(G))
fn = lambda x: ((x.depth - 0.5).abs() <= 0.15).mean() - 0.30
ho = holdout(G, fn)
print(f"respected in-gap terminus n={len(G)}  P(|depth-CE|<=0.15gap)={frac*100:.1f}% "
      f"vs uniform 30.0%  z={zc:+.1f} holdout={ho[0]} cells={[f'{x:+.0f}' for x in ho[1]]}")
print("terminus depth deciles:", np.round(np.percentile(G.depth, range(10, 100, 10)), 2))

print("\n================ T2: overlap monotonicity (lesson 9) ================")
V["stk"] = V.nst.clip(upper=4)
tb = V.groupby("stk").agg(n=("resp", "size"), resp=("resp", "mean"), null=("null", "mean"),
                          lift=("lift", "mean"))
print((tb * [1, 100, 100, 100]).round(2).to_string())
mono = all(np.diff(tb.resp.values) > 0)
d41 = lambda x: x[x.stk == 4].resp.mean() - x[x.stk == 1].resp.mean()
ho = holdout(V, d41)
z = z2p(V[V.stk == 4].resp.mean(), (V.stk == 4).sum(), V[V.stk == 1].resp.mean(), (V.stk == 1).sum())
print(f"monotone increase: {mono}  resp(4+)-resp(1)={d41(V)*100:+.2f}pp z={z:+.1f} "
      f"holdout={ho[0]} cells={[f'{x:+.0f}' for x in ho[1]]}")
per_cell_mono = [all(np.diff(V[V.cell == c].groupby('stk').resp.mean().values) > 0) for c in range(6)]
print("strict monotone per cell:", per_cell_mono)
xt = V.groupby(V.nst.clip(upper=10)).resp.mean()
print("extended resp% by nst:", (xt * 100).round(1).to_dict())

print("\n================ T3: pivot-distance gradient (lesson 3) ================")
for tys in (["OB"], ["FVG3", "FVGN"]):
    S = V[V.ty.isin(tys) & V.dist.notna()].copy()
    S["db"] = np.where(S.dist == 0, 0, np.where(S.dist <= 2, 1, np.where(S.dist <= 5, 2, 3)))
    tb = S.groupby("db").agg(n=("resp", "size"), resp=("resp", "mean"), null=("null", "mean"),
                             lift=("lift", "mean"))
    d03 = lambda x: x[x.db == 0].resp.mean() - x[x.db == 3].resp.mean()
    ho = holdout(S, d03)
    z = z2p(S[S.db == 0].resp.mean(), (S.db == 0).sum(), S[S.db == 3].resp.mean(), (S.db == 3).sum())
    print(f"-- {'+'.join(tys)} (0 / 0-2 / 2-5 / >5 ATR from pivot)")
    print((tb * [1, 100, 100, 100]).round(2).to_string())
    print(f"monotone decay: {all(np.diff(tb.resp.values) < 0)}  at-pivot minus mid-leg="
          f"{d03(S)*100:+.2f}pp z={z:+.1f} holdout={ho[0]} cells={[f'{x:+.0f}' for x in ho[1]]}")

print("\n================ T4: blow-through decomposition + grading AUC ================")
print(f"blow-through (violated on first touch) rate: {ep.blow.mean()*100:.1f}% "
      f"(n={len(ep)}); by type:", (ep.groupby('ty').blow.mean() * 100).round(1).to_dict())
Bw = ep[ep.blow == 1]
print(f"of blown zones: overlap==1 {(Bw.nst == 1).mean()*100:.1f}% (all eps {(ep.nst == 1).mean()*100:.1f}%), "
      f"dist>5 (mid-air) {(Bw.dist > 5).mean()*100:.1f}% (all {(ep.dist > 5).mean()*100:.1f}%), "
      f"dist not defined {(Bw.dist.isna()).mean()*100:.1f}%")
A = ep[ep.dist.notna()].copy()
A["score"] = A.dist.rank(pct=True) - A.nst.rank(pct=True)  # high = low-grade
a_all = auc(A.score.values, A.blow.values)
a_nst = auc((-ep.nst).rank(pct=True).values, ep.blow.values)
a_dst = auc(A.dist.rank(pct=True).values, A.blow.values)
cells_a = [auc(A[A.cell == c].score.values, A[A.cell == c].blow.values) for c in range(6)]
print(f"AUC(low-grade -> blow): composite={a_all:.3f} (n={len(A)}), overlap-only={a_nst:.3f}, "
      f"dist-only={a_dst:.3f}")
print(f"composite AUC per holdout cell: {[f'{x:.3f}' for x in cells_a]}  "
      f"pass(all>0.5)={all(x > 0.5 for x in cells_a)}")

print("\n================ T5: FVG-N recall + quality ================")
zc = pd.read_csv(f"{SCR}/ts2_zone_counts.csv", index_col=0).iloc[:, 0]
print("zone counts:", zc.to_dict())
print(f"recall gain: FVGN {zc.get('FVGN', 0)} extra gaps = "
      f"+{zc.get('FVGN', 0)/zc.get('FVG3', 1)*100:.0f}% over strict-3 {zc.get('FVG3', 0)}")
Gm = V[V.ty == "FVGN"]
print("per-m: ", Gm.groupby("m").agg(n=("resp", "size"), resp=("resp", "mean"),
                                     lift=("lift", "mean")).round(3).to_string())
f3v, fnv = V[V.ty == "FVG3"], V[V.ty == "FVGN"]
z = z2p(fnv.resp.mean(), len(fnv), f3v.resp.mean(), len(f3v))
print(f"respect: FVGN {fnv.resp.mean()*100:.1f}% (lift {fnv.lift.mean()*100:+.2f}pp) vs "
      f"FVG3 {f3v.resp.mean()*100:.1f}% (lift {f3v.lift.mean()*100:+.2f}pp)  diff z={z:+.1f}")
