"""tune_sweep — ARMORED stage driver.
TRAIN = temporal third 1 (touch ts) ∩ crc32(sym)%2==0. Knob selection on train only.
Usage: tune_sweep.py A|B|C|D|E|G|full
Stages freeze knobs into tune_frozen.json sequentially: A pct(+band) -> B OB ->
C FVG -> D death -> E stack / F sweep-window / G inset (from D/E builds) -> full."""
import sys, json, time
from multiprocessing import Pool
import numpy as np, pandas as pd

SCR = "/tmp/claude-1000/-home-doom-Public-PROJECT-2026-trader/a013584c-0930-4f6c-921b-e4ea05cde0a4/scratchpad"
sys.path.insert(0, SCR)
import tune_lib as T

FZ = f"{SCR}/tune_frozen.json"

def frozen():
    try: return json.load(open(FZ))
    except FileNotFoundError: return dict(T.BASE)

def save_frozen(d):
    json.dump(d, open(FZ, "w"), indent=1); print("FROZEN:", d)

_G = {}

def _work(sym):
    g = _G["df"][_G["df"].symbol == sym].sort_values("ts").reset_index(drop=True)
    out = []
    for ci, (cfg, tools, stack) in enumerate(_G["cfgs"]):
        out += [(ci,) + r for r in T.run_symbol(g, sym, cfg, tools, stack)]
    return out

def run_stage(name, cfgs, half=0, procs=8):
    df, syms = T.load(half)
    _G["df"], _G["cfgs"] = df, cfgs
    t0 = time.time()
    with Pool(procs) as p:
        res = p.map(_work, syms, chunksize=2)
    rows = [r for sub in res for r in sub]
    ep = pd.DataFrame(rows, columns=["cfg"] + T.COLS)
    for c in ("evts", "ts0"):
        ep[c] = pd.to_datetime(ep[c])
    ep["tb"] = np.where(ep.evts < T.B1, 0, np.where(ep.evts < T.B2, 1, 2))   # birth third
    ep["tt"] = np.where(ep.ts0 < T.B1, 0, np.where(ep.ts0 < T.B2, 1, 2))    # touch third
    ep.to_parquet(f"{SCR}/tune_ep_{name}.parquet")
    print(f"stage {name}: {len(syms)} syms, {len(cfgs)} cfgs, {len(ep)} rows, "
          f"{time.time()-t0:.0f}s")
    return ep

def funnel(ep, tycol=None):
    """birth-attributed detected; touch-attributed episode stages."""
    has = ep.t0 >= 0
    det = len(ep[["sym", "zid"]].drop_duplicates()) if tycol is None else len(ep)
    zdet = ep.groupby(["sym", "zid"]).agg(r=("t0", "max"))
    ret = float((zdet.r >= 0).mean())
    e = ep[has]
    v = e[e.nn > 0]
    lift = (v.resp - v.null)
    t = lift.mean() / (lift.std(ddof=1) / np.sqrt(len(lift))) if len(lift) > 2 else np.nan
    return dict(det=len(zdet), retp=100 * ret, neps=len(e),
                resp=100 * e.resp.mean() if len(e) else np.nan,
                r2=100 * e.r2.mean() if len(e) else np.nan,
                blow=100 * e.blow.mean() if len(e) else np.nan,
                null=100 * v.null.mean() if len(v) else np.nan,
                lift=100 * lift.mean() if len(v) else np.nan,
                npair=len(v), t=t)

def train_mask(ep):
    return (ep.half == 0) & np.where(ep.t0 >= 0, ep.tt == 0, ep.tb == 0)

def report(ep, cfgs, label, by_ty=False):
    print(f"\n===== {label} (TRAIN cell t1∩half0) =====")
    out = []
    for ci, (cfg, tools, stack) in enumerate(cfgs):
        sub = ep[(ep.cfg == ci) & train_mask(ep)]
        tys = sorted(sub.ty.unique()) if by_ty else [None]
        for ty in tys:
            s = sub[sub.ty == ty] if ty else sub
            f = funnel(s)
            f.update(cfg=ci, ty=ty or "ALL", **{k: v for k, v in cfg.items()})
            out.append(f)
    r = pd.DataFrame(out)
    print(r.to_string(float_format=lambda x: f"{x:.2f}"))
    return r


if __name__ == "__main__":
    stage = sys.argv[1]
    fz = frozen()

    if stage == "A":
        P = (.035, .047, .060)
        cfgs = [(dict(T.BASE, pct=p, band=b), ("BAND",), False)
                for p in P for b in ("wick", "atr")]
        cfgs += [(dict(T.BASE, pct=p), ("OB",), False) for p in P]
        ep = run_stage("A", cfgs)
        r = report(ep, cfgs, "A zigzag: 6 band cfgs + 3 OB-anchor checks")
        r.to_csv(f"{SCR}/tune_res_A.csv", index=False)
        ob = r[r.ty.eq("ALL") & (r.cfg >= 6)]
        best = ob.loc[ob.lift.idxmax()]
        band = r[r.cfg < 6].loc[r[r.cfg < 6].lift.idxmax()]
        fz.update(pct=float(best.pct), band=str(band.band))
        save_frozen(fz)

    elif stage == "B":
        grid = [(bx, jn, mx) for bx in ("full", "body") for jn in (0.0, 0.25)
                for mx in (2.0, 6.0, np.inf)]
        cfgs = [(dict(fz, ob_box=bx, ob_join=jn, ob_maxd=mx), ("OB",), False)
                for bx, jn, mx in grid]
        ep = run_stage("B", cfgs)
        r = report(ep, cfgs, "B taught-OB: 12 cfgs")
        r.to_csv(f"{SCR}/tune_res_B.csv", index=False)
        el = r[r.npair >= 300]
        best = el.loc[el.lift.idxmax()]
        fz.update(ob_box=str(best.ob_box), ob_join=float(best.ob_join),
                  ob_maxd=float(best.ob_maxd))
        save_frozen(fz)

    elif stage == "C":
        grid = [(m, q) for m in (1, 3, 6) for q in (0.0, 0.10, 0.25)]
        cfgs = [(dict(fz, fvg_mmax=m, fvg_q=q), ("FVG",), False) for m, q in grid]
        ep = run_stage("C", cfgs)
        r = report(ep, cfgs, "C FVG-N (merged bursts): 9 cfgs")
        r.to_csv(f"{SCR}/tune_res_C.csv", index=False)
        el = r[r.npair >= 300]
        best = el.loc[el.lift.idxmax()]
        fz.update(fvg_mmax=int(best.fvg_mmax), fvg_q=float(best.fvg_q))
        save_frozen(fz)

    elif stage == "D":
        cfgs = [(dict(fz, death=D), ("OB", "FVG", "FLIP", "PRP"), False)
                for D in (0.0, 0.5, 1.0)]
        ep = run_stage("D", cfgs)
        r = report(ep, cfgs, "D break-depth death law: 3 cfgs")
        r.to_csv(f"{SCR}/tune_res_D.csv", index=False)
        print("\n-- second-life episodes only (train) --")
        sl = ep[(ep.life > 0) & train_mask(ep)]
        for ci in sorted(sl.cfg.unique()):
            s = sl[sl.cfg == ci]; v = s[s.nn > 0]
            print(f"cfg{ci} D={cfgs[ci][0]['death']}: n={len(s)} resp={s.resp.mean():.3f} "
                  f"null={v.null.mean():.3f} lift={(v.resp-v.null).mean():+.3f}")
        el = r[r.npair >= 300]
        best = el.loc[el.lift.idxmax()]
        fz.update(death=float(best.death))
        save_frozen(fz)

    elif stage == "E":
        cfgs = [(dict(fz), ("OB", "FVG", "FLIP", "PRP"), True)]
        ep = run_stage("E", cfgs)
        tm = train_mask(ep) & (ep.t0 >= 0)
        e = ep[tm & (ep.nn > 0)]
        print("\n===== E stack grading (train): tol x minstack; dedup nst =====")
        rows = []
        for tol, col in ((0.0, "nst0"), (0.25, "nst25")):
            for S in (2, 3, 4):
                hi = e[e[col] >= S]; lo = e[e[col] < S]
                rows.append(dict(tol=tol, S=S, n_hi=len(hi),
                                 lift_hi=100 * (hi.resp - hi.null).mean(),
                                 resp_hi=100 * hi.resp.mean(),
                                 lift_lo=100 * (lo.resp - lo.null).mean(),
                                 sep=100 * ((hi.resp - hi.null).mean() - (lo.resp - lo.null).mean())))
        r = pd.DataFrame(rows); print(r.to_string(float_format=lambda x: f"{x:.2f}"))
        r.to_csv(f"{SCR}/tune_res_E.csv", index=False)
        print("\n-- stack-law recheck old(frag) vs new(dedup) counting, train --")
        for col in ("nso0", "nst0"):
            for b in ((1, 1), (2, 2), (3, 3), (4, 99)):
                m = (e[col] >= b[0]) & (e[col] <= b[1])
                s = e[m]
                print(f"{col} {b}: n={len(s)} resp={100*s.resp.mean():.1f} "
                      f"lift={100*(s.resp-s.null).mean():+.2f}")
        best = r[r.n_hi >= 300].sort_values("lift_hi").iloc[-1]
        fz.update(stack_tol=float(best.tol), stack_min=int(best.S))
        save_frozen(fz)
        print("\n===== F sweep-aligned birth window (train, same build) =====")
        rows = []
        for W in (2, 3, 5):
            al = e[(e.swb >= 0) & (e.swb <= W)]; un = e[~((e.swb >= 0) & (e.swb <= W))]
            rows.append(dict(W=W, n_al=len(al), resp_al=100 * al.resp.mean(),
                             lift_al=100 * (al.resp - al.null).mean(),
                             lift_un=100 * (un.resp - un.null).mean()))
        rf = pd.DataFrame(rows); print(rf.to_string(float_format=lambda x: f"{x:.2f}"))
        rf.to_csv(f"{SCR}/tune_res_F.csv", index=False)
        bw = rf[rf.n_al >= 200]
        if len(bw):
            fz.update(sweep_w=int(bw.sort_values("lift_al").iloc[-1].W)); save_frozen(fz)

    elif stage == "G":
        cfgs = [(dict(fz, inset=0.1), ("OB", "FVG", "FLIP", "PRP"), False)]
        ep = run_stage("G", cfgs)
        r = report(ep, cfgs, "G entry ref: edge+0.1ATR inside (vs stage-D edge cfg)")
        r.to_csv(f"{SCR}/tune_res_G.csv", index=False)
        d = pd.read_parquet(f"{SCR}/tune_ep_D.parquet")
        ci = [i for i, (c, _, _) in enumerate([(dict(fz, death=D), 0, 0)
              for D in (0.0, 0.5, 1.0)]) if c["death"] == fz["death"]][0]
        base = d[(d.cfg == ci) & train_mask(d)]
        f0 = funnel(base)
        print(f"edge (inset=0): lift={f0['lift']:.2f} resp={f0['resp']:.2f} "
              f"retp={f0['retp']:.1f} npair={f0['npair']}")
        ins = float(r.iloc[0].lift) > f0["lift"]
        fz.update(inset=0.1 if ins else 0.0)
        save_frozen(fz)

    elif stage == "full":
        cfgs = [(dict(fz), ("OB", "FVG", "FLIP", "PRP", "BAND"), True)]
        df, syms = T.load(None)
        _G["df"], _G["cfgs"] = df, cfgs
        t0 = time.time()
        with Pool(8) as p:
            res = p.map(_work, syms, chunksize=2)
        ep = pd.DataFrame([r for sub in res for r in sub], columns=["cfg"] + T.COLS)
        for c in ("evts", "ts0"): ep[c] = pd.to_datetime(ep[c])
        ep["tb"] = np.where(ep.evts < T.B1, 0, np.where(ep.evts < T.B2, 1, 2))
        ep["tt"] = np.where(ep.ts0 < T.B1, 0, np.where(ep.ts0 < T.B2, 1, 2))
        ep.to_parquet(f"{SCR}/tune_full.parquet")
        print(f"full: {len(ep)} rows {time.time()-t0:.0f}s")
