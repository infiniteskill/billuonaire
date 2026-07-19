"""tune_report — train vs validation funnels at frozen configs + composite tier."""
import sys, json
import numpy as np, pandas as pd

SCR = "/tmp/claude-1000/-home-doom-Public-PROJECT-2026-trader/a013584c-0930-4f6c-921b-e4ea05cde0a4/scratchpad"
sys.path.insert(0, SCR)

ep = pd.read_parquet(f"{SCR}/tune_full.parquet")
fz = json.load(open(f"{SCR}/tune_frozen.json"))
CONS = ["OB", "FVG", "IFVG", "BRK", "MIT", "PRP"]

ep["cell"] = ep.tt * 2 + ep.half
ep["cellb"] = ep.tb * 2 + ep.half
TR = (ep.half == 0) & np.where(ep.t0 >= 0, ep.tt == 0, ep.tb == 0)
VA = ~((ep.half == 0) & np.where(ep.t0 >= 0, ep.tt == 0, ep.tb == 0))
VCELLS = [1, 2, 3, 4, 5]


def fun(sub):
    z = sub.groupby(["sym", "zid"]).agg(r=("t0", "max"))
    e = sub[sub.t0 >= 0]; v = e[e.nn > 0]
    lift = v.resp - v.null
    t = lift.mean() / (lift.std(ddof=1) / np.sqrt(len(lift))) if len(lift) > 2 else np.nan
    return dict(det=len(z), retp=100 * (z.r >= 0).mean() if len(z) else np.nan,
                neps=len(e), resp=100 * e.resp.mean() if len(e) else np.nan,
                r2=100 * e.r2.mean() if len(e) else np.nan,
                blow=100 * e.blow.mean() if len(e) else np.nan,
                null=100 * v.null.mean() if len(v) else np.nan,
                lift=100 * lift.mean() if len(v) else np.nan, npair=len(v), t=t)


def cells_lift(sub):
    out = []
    for c in VCELLS:
        e = sub[(sub.t0 >= 0) & (sub.cell == c) & (sub.nn > 0)]
        out.append(100 * (e.resp - e.null).mean() if len(e) else np.nan)
    return out


def row(name, mask):
    a, b = fun(ep[mask & TR]), fun(ep[mask & VA])
    cl = cells_lift(ep[mask])
    of = "OVERFIT" if (np.isfinite(a["lift"]) and np.isfinite(b["lift"])
                       and a["lift"] > 0 and b["lift"] < 0.7 * a["lift"]) else ""
    print(f"{name:14s} TR: det={a['det']:6d} ret%={a['retp']:5.1f} n={a['neps']:6d} "
          f"resp={a['resp']:5.2f} 2R={a['r2']:5.2f} blow={a['blow']:5.2f} "
          f"null={a['null']:5.2f} lift={a['lift']:+5.2f} t={a['t']:+.1f}")
    print(f"{'':14s} VA: det={b['det']:6d} ret%={b['retp']:5.1f} n={b['neps']:6d} "
          f"resp={b['resp']:5.2f} 2R={b['r2']:5.2f} blow={b['blow']:5.2f} "
          f"null={b['null']:5.2f} lift={b['lift']:+5.2f} t={b['t']:+.1f} "
          f"cells={['%+.1f' % x for x in cl]} {of}")
    return a, b, cl


print("== frozen:", fz)
print("\n===== per-tool funnels at FROZEN config (train t1h0 vs validation 5 cells) =====")
row("OB", ep.ty.eq("OB"))
row("FVG-N merged", ep.ty.eq("FVG"))
row("BAND(zigzag)", ep.ty.eq("BAND"))
row("PRP all", ep.ty.eq("PRP"))
row("PRP live-par", ep.ty.eq("PRP") & (ep.plive != 0))
row("PRP orphan", ep.ty.eq("PRP") & (ep.plive == 0))
row("IFVG", ep.ty.eq("IFVG"))
row("BRK", ep.ty.eq("BRK"))
row("MIT", ep.ty.eq("MIT"))
row("ALL cons", ep.ty.isin(CONS))
print("\n-- break-depth second-life episodes (frozen D=%.1f) --" % fz["death"])
row("2nd-life", ep.ty.isin(CONS) & (ep.life > 0))
row("1st-life", ep.ty.isin(CONS) & (ep.life == 0))

print("\n===== stack tiers (dedup nst, tol=%.2f) train vs validation =====" % fz["stack_tol"])
col = "nst0" if fz["stack_tol"] == 0 else "nst25"
E = ep[(ep.t0 >= 0) & (ep.nn > 0) & ep.ty.isin(CONS)]
for name, m in [("nst=1", E[col] == 1), ("nst=2", E[col] == 2), ("nst=3", E[col] == 3),
                ("nst>=4", E[col] >= 4), ("nst>=6", E[col] >= 6)]:
    tr = E[m & TR.reindex(E.index)]; va = E[m & VA.reindex(E.index)]
    cl = [100 * (E[m & (E.cell == c)].resp - E[m & (E.cell == c)].null).mean() for c in VCELLS]
    print(f"{name:8s} TR n={len(tr):6d} resp={100*tr.resp.mean():5.2f} lift={100*(tr.resp-tr.null).mean():+5.2f} | "
          f"VA n={len(va):6d} resp={100*va.resp.mean():5.2f} lift={100*(va.resp-va.null).mean():+5.2f} "
          f"cells={['%+.1f' % x for x in cl]}")
print("-- old fragment-counting comparison (nso0) --")
for name, m in [("nso=1-3", E.nso0 <= 3), ("nso>=4", E.nso0 >= 4)]:
    tr = E[m & TR.reindex(E.index)]; va = E[m & VA.reindex(E.index)]
    print(f"{name:8s} TR n={len(tr):6d} lift={100*(tr.resp-tr.null).mean():+5.2f} | "
          f"VA n={len(va):6d} lift={100*(va.resp-va.null).mean():+5.2f}")

print("\n===== sweep-aligned birth (diagnostic, UNDERPOWERED at train) =====")
for W in (2, 3, 5):
    m = (E.swb >= 0) & (E.swb <= W)
    tr = E[m & TR.reindex(E.index)]; va = E[m & VA.reindex(E.index)]
    print(f"W={W} TR n={len(tr):5d} lift={100*(tr.resp-tr.null).mean():+5.2f} | "
          f"VA n={len(va):5d} lift={100*(va.resp-va.null).mean():+5.2f}")

print("\n===== PO3 validation =====")
po = pd.read_parquet(f"{SCR}/tune_po3.parquet")
po["cell"] = po.tt * 2 + po.half
for ci, tag in [(2, "CHOSEN body<.5 wick>.5"), (0, "taught body<.35 wick>.5")]:
    s = po[po.cfg == ci]
    tr = s[(s.half == 0) & (s.tt == 0)]; va = s[~((s.half == 0) & (s.tt == 0))]
    cl = [100 * (s[(s.cell == c) & (s.nn > 0)].resp - s[(s.cell == c) & (s.nn > 0)].null).mean()
          for c in VCELLS]
    trv = tr[tr.nn > 0]; vav = va[va.nn > 0]
    print(f"{tag}: TR n={len(tr)} resp={100*tr.resp.mean():.2f} lift={100*(trv.resp-trv.null).mean():+.2f} | "
          f"VA n={len(va)} resp={100*va.resp.mean():.2f} lift={100*(vav.resp-vav.null).mean():+.2f} "
          f"cells={['%+.1f' % x for x in cl]}")

print("\n===== COMPOSITE top tier (validation cells only) =====")
top = E[(E[col] >= fz["stack_min"]) & (E.plive != 0)]
va_top = top[VA.reindex(top.index)]
tr_top = top[TR.reindex(top.index)]
cl = [100 * (top[top.cell == c].resp - top[top.cell == c].null).mean() for c in VCELLS]
print(f"grade gates: type in {CONS}, nst{'' if fz['stack_tol']==0 else '25'}>="
      f"{fz['stack_min']}, parent-alive (PRP), OB dist<={fz['ob_maxd']}, death D={fz['death']}")
mask_top = E.index.isin(top.index)
ztop = ep.loc[E.index[mask_top]]
print(f"TR  n={len(tr_top):6d} resp={100*tr_top.resp.mean():5.2f} "
      f"lift={100*(tr_top.resp-tr_top.null).mean():+5.2f}")
print(f"VAL n={len(va_top):6d} resp={100*va_top.resp.mean():5.2f} "
      f"2R={100*va_top.r2.mean():5.2f} blow={100*va_top.blow.mean():5.2f} "
      f"null={100*va_top.null.mean():5.2f} "
      f"lift={100*(va_top.resp-va_top.null).mean():+5.2f} cells={['%+.1f' % x for x in cl]}")
lift = va_top.resp - va_top.null
print(f"VAL t={lift.mean()/(lift.std(ddof=1)/np.sqrt(len(lift))):+.2f}")
# trades/quarter: full-universe quarter equivalents in validation cells
q1, q2, q3 = 3.94, 3.93, 3.87
qe = 0.5 * q1 + q2 + q3
print(f"validation top-tier episodes={len(va_top)}, quarter-equivalents={qe:.2f} "
      f"-> trades/quarter (138 syms) = {len(va_top)/qe:.0f}")
print(f"+ sweep-aligned bonus (W={fz['sweep_w']}): "
      f"n={len(va_top[(va_top.swb >= 0) & (va_top.swb <= fz['sweep_w'])])}")
