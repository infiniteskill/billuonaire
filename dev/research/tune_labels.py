"""tune_labels — score frozen-config detection against user hand-drawn HDFCBANK
labels (f)-(k). Tolerance: ±1.5% price on box edges, ±4 days on birth.
Also: composite grade ladder (stack + parent + pivot-near + sweep-aligned)."""
import sys, json
import numpy as np, pandas as pd

SCR = "/tmp/claude-1000/-home-doom-Public-PROJECT-2026-trader/a013584c-0930-4f6c-921b-e4ea05cde0a4/scratchpad"
sys.path.insert(0, SCR)
import tune_lib as T
from tune_lib import (zigzag, wilder_atr, sym_K, ob_clusters, fvg_zones,
                      kill_bar, zone_lives, first_true)

fz = json.load(open(f"{SCR}/tune_frozen.json"))

# ---------- composite grade ladder ----------
ep = pd.read_parquet(f"{SCR}/tune_full.parquet")
ep["cell"] = ep.tt * 2 + ep.half
CONS = ["OB", "FVG", "IFVG", "BRK", "MIT", "PRP"]
E = ep[(ep.t0 >= 0) & (ep.nn > 0) & ep.ty.isin(CONS)].copy()
E["g_stack"] = (E.nst0 >= fz["stack_min"]).astype(int)
E["g_par"] = (E.plive != 0).astype(int)   # non-PRP =1 (plive=-1), orphan PRP =0
E["g_dist"] = (E.dist.notna() & (E.dist <= 2.0)).astype(int)
E["g_swp"] = ((E.swb >= 0) & (E.swb <= fz["sweep_w"])).astype(int)
E["grade"] = E.g_stack + E.g_par + E.g_dist + E.g_swp
TRm = (E.half == 0) & (E.tt == 0)
print("===== composite grade ladder (stack+parent+pivot-near+sweep-aligned) =====")
for gmin in (0, 1, 2, 3, 4):
    m = E.grade == gmin
    tr, va = E[m & TRm], E[m & ~TRm]
    cl = [100 * (va[va.cell == c].resp - va[va.cell == c].null).mean()
          for c in (1, 2, 3, 4, 5)]
    print(f"grade={gmin}: TR n={len(tr):6d} lift={100*(tr.resp-tr.null).mean():+5.2f} | "
          f"VA n={len(va):6d} resp={100*va.resp.mean():5.2f} r2={100*va.r2.mean():5.2f} "
          f"blow={100*va.blow.mean():5.2f} lift={100*(va.resp-va.null).mean():+5.2f} "
          f"cells={['%+.1f' % x for x in cl]}")
for lab, m in [("g>=2", E.grade >= 2), ("g>=3", E.grade >= 3)]:
    tr, va = E[m & TRm], E[m & ~TRm]
    lift = va.resp - va.null
    t = lift.mean() / (lift.std(ddof=1) / np.sqrt(len(lift)))
    cl = [100 * (va[va.cell == c].resp - va[va.cell == c].null).mean() for c in (1, 2, 3, 4, 5)]
    print(f"{lab}: TR n={len(tr)} lift={100*(tr.resp-tr.null).mean():+.2f} | VA n={len(va)} "
          f"resp={100*va.resp.mean():.2f} r2={100*va.r2.mean():.2f} blow={100*va.blow.mean():.2f} "
          f"lift={100*lift.mean():+.2f} t={t:+.1f} cells={['%+.1f' % x for x in cl]} "
          f"-> trades/q={len(va)/9.77:.0f}")

# ---------- HDFCBANK label check ----------
df = pd.read_parquet(T.PARQ)
g = df[df.symbol == "HDFCBANK"].sort_values("ts").reset_index(drop=True)
O, H, L, C = (g[c].values for c in ("open", "high", "low", "close"))
n = len(C); ts = pd.DatetimeIndex(T.to_naive(g.ts))
atr = wilder_atr(g)


def build(maxd):
    cfg = dict(fz, ob_maxd=maxd)
    K = sym_K(atr, C, cfg["pct"])
    piv = zigzag(g, K, atr)
    conf = [p for p in piv if p.confirm_idx is not None]
    Z = []
    for j in range(len(piv) - 1):
        p0, p1 = piv[j], piv[j + 1]
        if p0.confirm_idx is None: continue
        d = 1 if p0.side == "L" else -1
        pex = piv[j - 1].price if j else np.nan
        for cl in ob_clusters(O, H, L, C, atr, p0.idx, p1.idx, d,
                              piv[j - 1].idx if j else -1, cfg["ob_box"], cfg["ob_join"]):
            dist = (max(0.0, cl["lo"] - p0.price) if d == 1
                    else max(0.0, p0.price - cl["hi"])) / atr[p0.idx]
            if dist > cfg["ob_maxd"]: continue
            Z.append(dict(ty="OB", dir=d, lo=cl["lo"], hi=cl["hi"], born=cl["born"],
                          evi=max(cl["brk"], p0.confirm_idx), dist=float(dist),
                          p0=p0.idx, pex=pex, par=-1))
    fvz, _, _ = fvg_zones(O, H, L, C, atr, conf, cfg)
    Z += fvz
    for idx, z in enumerate(Z):
        z["kb"] = kill_bar(z, H, L, C, atr, cfg["death"], n)
    kids = []
    for idx, z in enumerate(Z):
        if z["kb"] < n and z["ty"] == "OB" and np.isfinite(z.get("pex", np.nan)):
            t = z["kb"]
            ext = H[z["p0"]:t + 1].max() if z["dir"] == 1 else L[z["p0"]:t + 1].min()
            fy = "BRK" if (ext > z["pex"] if z["dir"] == 1 else ext < z["pex"]) else "MIT"
            kids.append(dict(ty=fy, dir=-z["dir"], lo=z["lo"], hi=z["hi"], born=t,
                             evi=t, dist=np.nan, par=idx))
        if z["ty"] == "OB":
            lv = zone_lives(z, O, H, L, C, atr, cfg["death"], 0.0, n, z["kb"])
            if lv:
                t0 = lv[0][0]; d = z["dir"]
                ok = (C[t0] > z["hi"] and C[t0] > O[t0]) if d == 1 \
                    else (C[t0] < z["lo"] and C[t0] < O[t0])
                if ok and H[t0] > L[t0]:
                    kids.append(dict(ty="PRP", dir=d, lo=float(L[t0]), hi=float(H[t0]),
                                     born=t0, evi=t0, dist=z["dist"], par=idx))
    return Z + kids


LAB = [("f", "OB", -1, 1005.0, 1012.5, "2025-10-21"),
       ("g", "OB", 1, 910.0, 920.0, "2026-01-27"),
       ("h", "OB", 1, 946.0, 954.0, "2025-09-30"),
       ("i", "OB", 1, 975.0, 980.0, "2025-10-16"),
       ("j", "PRP", 1, 982.0, 990.0, "2025-10-20"),
       ("k", "BRK", -1, 969.5, 974.5, "2025-09-18")]

for tag, maxd in (("FROZEN maxd=2", fz["ob_maxd"]), ("no-cap diagnostic", np.inf)):
    Z = build(maxd)
    print(f"\n===== HDFCBANK labels vs {tag} =====")
    for lid, lty, ld, llo, lhi, lborn in LAB:
        t_lab = pd.Timestamp(lborn)
        tol = 0.015 * (llo + lhi) / 2
        tys = {"OB": ["OB"], "PRP": ["PRP"], "BRK": ["BRK", "MIT"]}[lty]
        best = None
        for z in Z:
            if z["ty"] not in tys or z["dir"] != ld: continue
            bt = ts[min(z["born"], n - 1)]
            dd = abs((bt - t_lab).days)
            if dd > 4: continue
            e_lo, e_hi = abs(z["lo"] - llo), abs(z["hi"] - lhi)
            ov = min(z["hi"], lhi) - max(z["lo"], llo)
            score = (0 if (e_lo <= tol and e_hi <= tol) else (1 if ov > 0 else 2), dd)
            if best is None or score < best[0]: best = (score, z, bt)
        if best is None:
            print(f"({lid}) {lty} {ld:+d} [{llo}-{lhi}] {lborn}: MISS")
        else:
            (sc, z, bt) = best
            verdict = "FOUND" if sc[0] == 0 else ("PARTIAL" if sc[0] == 1 else "MISS")
            extra = ""
            if z["ty"] == "PRP" and z.get("par", -1) >= 0:
                p = Z[z["par"]]
                extra = f" parent={p['ty']}[{p['lo']:.1f}-{p['hi']:.1f}] born {ts[p['born']].date()}"
            print(f"({lid}) {lty} {ld:+d} [{llo}-{lhi}] {lborn}: {verdict} -> "
                  f"{z['ty']} [{z['lo']:.1f}-{z['hi']:.1f}] born {bt.date()} "
                  f"dist={z.get('dist', np.nan):.2f}{extra}")
