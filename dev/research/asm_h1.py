"""asm_h1 -- ASSEMBLED taught system on H1 (l4_h1, 138 syms).

Re-runs the FROZEN tune_lib detection (death=0.5 second-life, body-OB, FVG mmax6,
dedup stacking, parent-linked propulsion) and, per first-retest episode, records the
frozen composite grade components AND the economic R-outcomes (edge entry, zone-height
stop, 1:1 / 2R / slow-trail, delivery costs). Mirrors tune_lib.run_symbol's zone build
verbatim (imports its detectors) so resp/r2/nst0 reconcile with tune_full.parquet.
Usage: asm_h1.py [nsyms]"""
import sys, json, time, zlib
from multiprocessing import Pool
import numpy as np, pandas as pd

SCR = "/tmp/claude-1000/-home-doom-Public-PROJECT-2026-trader/a013584c-0930-4f6c-921b-e4ea05cde0a4/scratchpad"
sys.path.insert(0, SCR)
sys.path.insert(0, "/home/doom/Public/PROJECT/2026/trader/dev/research")
import tune_lib as T
from tune_lib import (ob_clusters, fvg_zones, band_zones, kill_bar, zone_lives,
                      sweep_bars, sym_K, race, wilder_atr, zigzag)
import asm_sim as S

FZ = json.load(open(f"{SCR}/tune_frozen.json"))
CFG = dict(pct=FZ["pct"], band=FZ["band"], ob_box=FZ["ob_box"], ob_join=FZ["ob_join"],
           ob_maxd=np.inf, fvg_mmax=FZ["fvg_mmax"], fvg_q=FZ["fvg_q"],
           death=FZ["death"], inset=FZ["inset"])
N_TRADE = 70   # H1 horizon: 10 sessions (matches tob H_TRADE)
B1, B2 = T.B1, T.B2

COLS = ["sym", "half", "ty", "dir", "born", "evi", "t0", "ts0", "life", "dist",
        "nst0", "plive", "resp", "r2", "blow", "null", "zh", "zh_stop",
        "t1_net", "t1_gross", "t1_win", "t2_net", "t2_gross", "t2_win",
        "tr_net", "tr_gross", "tr_peakR", "t2a_net", "t2a_gross", "t2a_win"]


def run_symbol(g, sym):
    O, H, L, C = (g[c].values for c in ("open", "high", "low", "close"))
    n = len(C); ts = T.to_naive(g["ts"])
    atr = wilder_atr(g)
    K = sym_K(atr, C, CFG["pct"]); piv = zigzag(g, K, atr)
    conf = [p for p in piv if p.confirm_idx is not None]
    spl = np.where(np.abs(O[1:] / np.where(C[:-1] > 0, C[:-1], np.nan) - 1) > 0.2)[0] + 1
    half = zlib.crc32(sym.encode()) % 2
    D, inset = CFG["death"], CFG["inset"]

    # ---- zones (verbatim tune_lib.run_symbol build, tools OB/FVG/BAND/FLIP/PRP) ----
    Z, frags = [], []
    for j in range(len(piv) - 1):
        p0, p1 = piv[j], piv[j + 1]
        if p0.confirm_idx is None: continue
        d = 1 if p0.side == "L" else -1
        pex = piv[j - 1].price if j else np.nan
        for cl in ob_clusters(O, H, L, C, atr, p0.idx, p1.idx, d,
                              piv[j - 1].idx if j else -1, CFG["ob_box"], CFG["ob_join"]):
            dist = (max(0.0, cl["lo"] - p0.price) if d == 1
                    else max(0.0, p0.price - cl["hi"])) / atr[p0.idx]
            Z.append(dict(ty="OB", dir=d, lo=cl["lo"], hi=cl["hi"], born=cl["born"],
                          evi=max(cl["brk"], p0.confirm_idx), dist=float(dist),
                          m=0, p0=p0.idx, pex=pex, par=-1, gidx=-1))
    fz, merged, raw = fvg_zones(O, H, L, C, atr, conf, CFG)
    base = len(Z); Z += fz
    frags = [dict(dir=r["dir"], lo=r["lo"], hi=r["hi"], i=r["i"], z=base + r["grp"]) for r in raw]
    Z += band_zones(O, H, L, C, atr, piv, CFG["band"])
    for idx, z in enumerate(Z):
        z["kb"] = kill_bar(z, H, L, C, atr, D, n); z["sid"] = idx
    kids = []
    for idx, z in enumerate(Z):
        if z["ty"] == "BAND" or z["kb"] >= n: continue
        t = z["kb"]
        if z["ty"] == "OB" and z["p0"] >= 0 and np.isfinite(z["pex"]):
            ext = H[z["p0"]:t + 1].max() if z["dir"] == 1 else L[z["p0"]:t + 1].min()
            fy = "BRK" if (ext > z["pex"] if z["dir"] == 1 else ext < z["pex"]) else "MIT"
        elif z["ty"] == "FVG":
            fy = "IFVG"
        else: continue
        kids.append(dict(ty=fy, dir=-z["dir"], lo=z["lo"], hi=z["hi"], born=t, evi=t,
                         dist=np.nan, m=0, p0=-1, pex=np.nan, par=-1, gidx=-1))
    for z in kids:
        z["kb"] = kill_bar(z, H, L, C, atr, D, n); z["sid"] = len(Z); Z.append(z)
    kids = []
    for idx, z in enumerate(Z):
        if z["ty"] != "OB": continue
        lv = zone_lives(z, O, H, L, C, atr, D, 0.0, n, z["kb"])
        if not lv: continue
        t0 = lv[0][0]; d = z["dir"]
        ok = (C[t0] > z["hi"] and C[t0] > O[t0]) if d == 1 else (C[t0] < z["lo"] and C[t0] < O[t0])
        if ok and H[t0] > L[t0]:
            kids.append(dict(ty="PRP", dir=d, lo=float(L[t0]), hi=float(H[t0]), born=t0,
                             evi=t0, dist=z["dist"], m=0, p0=z["p0"], pex=np.nan, par=idx, gidx=-1))
    for z in kids:
        z["kb"] = kill_bar(z, H, L, C, atr, D, n); z["sid"] = Z[z["par"]]["sid"]; Z.append(z)

    # ---- dedup stack arrays (tol=0) ----
    st = [z for z in Z if z["ty"] != "BAND"]
    zlo = np.array([z["lo"] for z in st]); zhi = np.array([z["hi"] for z in st])
    zdir = np.array([z["dir"] for z in st]); zev = np.array([z["evi"] for z in st])
    zkb = np.array([z["kb"] for z in st]); zsid = np.array([z["sid"] for z in st])
    zisf = np.array([z["ty"] == "FVG" for z in st])
    flo = np.array([f["lo"] for f in frags]); fhi = np.array([f["hi"] for f in frags])
    fdir = np.array([f["dir"] for f in frags], int); fev = np.array([f["i"] for f in frags], int)
    fkb = np.array([Z[f["z"]]["kb"] for f in frags], int)

    rows = []
    for z in Z:
        d, lo, hi = z["dir"], z["lo"], z["hi"]
        far = lo if d == 1 else hi
        lv = zone_lives(z, O, H, L, C, atr, D, inset, n, z["kb"])
        for (t0, arm, life, E) in lv:
            a = atr[t0]
            if not np.isfinite(a) or a <= 0: continue
            if len(spl) and ((spl >= z["born"]) & (spl <= min(n - 1, t0 + 70))).any(): continue
            resp, r2, blow = race(H, L, C, d, E, a, t0, far, n)
            if resp is None: continue
            # dedup stack (nst0)
            ov = (np.minimum(zhi, hi) - np.maximum(zlo, lo)) > 0.0
            m1 = (zdir == d) & (zev <= t0) & (zkb >= t0) & ov
            nst0 = int(len(np.unique(zsid[m1])))
            plive = int(Z[z["par"]]["kb"] > t0) if z["par"] >= 0 else -1
            # matched null respect (reuse tune_lib)
            nl, _, nn = T.null_rates(sym, z["ty"], t0, arm, E, d, H, L, C, atr, spl, n)
            # economic R-sim
            ec = S.econ(O, H, L, C, atr, t0, d, E, far, N_TRADE)
            if ec is None: continue
            rows.append((sym, half, z["ty"], d, z["born"], z["evi"], t0, ts[t0], life,
                         z["dist"], nst0, plive, float(resp), float(r2), float(blow),
                         nl, ec["sd"], ec["zh_stop"],
                         ec["t1"][0], ec["t1"][1], ec["t1"][2],
                         ec["t2"][0], ec["t2"][1], ec["t2"][2],
                         ec["tr"][0], ec["tr"][1], ec["tr"][2],
                         ec["t2a"][0], ec["t2a"][1], ec["t2a"][2]))
    return rows


def _work(sym):
    g = _DF[_DF.symbol == sym].sort_values("ts").reset_index(drop=True)
    return run_symbol(g, sym)


def load_df():
    global _DF
    _DF = pd.read_parquet(T.PARQ)
    return sorted(_DF.symbol.unique())


if __name__ == "__main__":
    syms = load_df()
    if len(sys.argv) > 1: syms = syms[:int(sys.argv[1])]
    t0 = time.time()
    with Pool(8, initializer=load_df) as p:
        res = p.map(_work, syms, chunksize=2)
    rows = [r for sub in res for r in sub]
    ep = pd.DataFrame(rows, columns=COLS)
    ep["ts0"] = pd.to_datetime(ep["ts0"])
    ep["tt"] = np.where(ep.ts0 < B1, 0, np.where(ep.ts0 < B2, 1, 2))   # touch third
    ep.to_parquet(f"{SCR}/asm_h1_trades.parquet")
    print(f"H1: {len(syms)} syms, {len(ep)} episodes, {time.time()-t0:.0f}s")
    print("zh_stop share:", ep.zh_stop.mean())
    print("resp mean:", ep.resp.mean(), "r2 mean:", ep.r2.mean())
    print("t1_win:", ep.t1_win.mean(), "t2_win:", ep.t2_win.mean())
    print("t1_net mean:", ep.t1_net.mean(), "t2_net mean:", ep.t2_net.mean(), "tr_net:", ep.tr_net.mean())
