"""asm_daily -- ASSEMBLED taught system, DAILY POSITIONAL (dailymax, 25y, 139 syms).

Same frozen tune_lib detection on daily bars; weeks-hold R-sim (edge entry, zone-height
stop, 2R + slow-trail, delivery costs). Adds a MATCHED DRIFT NULL: per real episode, 5
random same-symbol same-direction entries with the SAME %-of-price stop (kills the ATR/
vol drift-dilution artifact, dgrid_lib null_vol), same target/horizon/costs. Excess =
real net - null net (the survivorship-robust number). Usage: asm_daily.py [nsyms]"""
import sys, json, time, zlib
from multiprocessing import Pool
import numpy as np, pandas as pd

SCR = "/tmp/claude-1000/-home-doom-Public-PROJECT-2026-trader/a013584c-0930-4f6c-921b-e4ea05cde0a4/scratchpad"
sys.path.insert(0, SCR)
sys.path.insert(0, "/home/doom/Public/PROJECT/2026/trader/dev/research")
import tune_lib as T
from tune_lib import (ob_clusters, fvg_zones, band_zones, kill_bar, zone_lives,
                      sym_K, race, wilder_atr, zigzag)
import asm_sim as S

DAILY = "/home/doom/Public/PROJECT/2026/trader/runs/artifacts-data/dailymax.parquet"
FZ = json.load(open(f"{SCR}/tune_frozen.json"))
CFG = dict(pct=FZ["pct"], band=FZ["band"], ob_box=FZ["ob_box"], ob_join=FZ["ob_join"],
           ob_maxd=np.inf, fvg_mmax=FZ["fvg_mmax"], fvg_q=FZ["fvg_q"],
           death=FZ["death"], inset=FZ["inset"])
N_TRADE = 40      # daily horizon ~ 8 trading weeks (weeks-hold positional)
NULL_DRAWS = 5

COLS = ["sym", "half", "ty", "dir", "t0", "ts0", "life", "dist", "nst0", "plive",
        "resp", "null_resp", "zh", "zh_stop",
        "t2_net", "t2_gross", "t2_win", "tr_net", "tr_gross", "tr_peakR",
        "null_t2_net", "null_tr_net", "nnull"]


def _null_net(O, H, L, C, atr, n, d, sd_pct, pool, rng):
    """matched drift null: random same-sym same-dir entry, same %-of-price stop."""
    t2, tr, m = 0.0, 0.0, 0
    for _ in range(NULL_DRAWS):
        u = int(pool[rng.integers(len(pool))])
        fp = O[u]
        if fp <= 0: continue
        sd = sd_pct * fp
        if sd <= 0: continue
        tgt = fp + d * 2.0 * sd; stop = fp - d * sd
        ex, win, _ = S._walk(O, H, L, C, u, d, fp, stop, tgt, N_TRADE)
        nt2, _ = S._acct(fp, ex, d, sd)
        ex2, _, _ = S._trail(O, H, L, C, u, d, fp, stop, sd, N_TRADE)
        ntr, _ = S._acct(fp, ex2, d, sd)
        t2 += nt2; tr += ntr; m += 1
    return (t2 / m, tr / m, m) if m else (np.nan, np.nan, 0)


def run_symbol(g, sym):
    O, H, L, C = (g[c].values for c in ("open", "high", "low", "close"))
    n = len(C); ts = T.to_naive(g["ts"])
    atr = wilder_atr(g)
    K = sym_K(atr, C, CFG["pct"]); piv = zigzag(g, K, atr)
    conf = [p for p in piv if p.confirm_idx is not None]
    spl = np.where(np.abs(O[1:] / np.where(C[:-1] > 0, C[:-1], np.nan) - 1) > 0.2)[0] + 1
    half = zlib.crc32(sym.encode()) % 2
    D, inset = CFG["death"], CFG["inset"]
    # eligible null-entry pool: valid ATR + full forward horizon
    pool = np.where(np.isfinite(atr) & (atr > 0))[0]
    pool = pool[(pool >= 20) & (pool < n - N_TRADE - 1)]
    rng = np.random.default_rng(zlib.crc32(sym.encode()) & 0xFFFFFFFF)

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

    st = [z for z in Z if z["ty"] != "BAND"]
    zlo = np.array([z["lo"] for z in st]); zhi = np.array([z["hi"] for z in st])
    zdir = np.array([z["dir"] for z in st]); zev = np.array([z["evi"] for z in st])
    zkb = np.array([z["kb"] for z in st]); zsid = np.array([z["sid"] for z in st])

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
            ov = (np.minimum(zhi, hi) - np.maximum(zlo, lo)) > 0.0
            m1 = (zdir == d) & (zev <= t0) & (zkb >= t0) & ov
            nst0 = int(len(np.unique(zsid[m1])))
            plive = int(Z[z["par"]]["kb"] > t0) if z["par"] >= 0 else -1
            nl, _, _ = T.null_rates(sym, z["ty"], t0, arm, E, d, H, L, C, atr, spl, n)
            ec = S.econ(O, H, L, C, atr, t0, d, E, far, N_TRADE)
            if ec is None: continue
            sd_pct = ec["sd"] / ec["fp"]
            n2, ntr, nn = _null_net(O, H, L, C, atr, n, d, sd_pct, pool, rng) if len(pool) else (np.nan, np.nan, 0)
            rows.append((sym, half, z["ty"], d, t0, ts[t0], life, z["dist"], nst0, plive,
                         float(resp), nl, ec["sd"], ec["zh_stop"],
                         ec["t2"][0], ec["t2"][1], ec["t2"][2],
                         ec["tr"][0], ec["tr"][1], ec["tr"][2], n2, ntr, nn))
    return rows


def _work(sym):
    g = _DF[_DF.symbol == sym].sort_values("ts").reset_index(drop=True)
    return run_symbol(g, sym)


def load_df():
    global _DF
    _DF = pd.read_parquet(DAILY).rename(columns={"date": "ts"})
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
    q = ep["ts0"].quantile([1/3, 2/3]).values           # touch-date thirds over 25y
    ep["tt"] = np.where(ep.ts0 < q[0], 0, np.where(ep.ts0 < q[1], 1, 2))
    ep.to_parquet(f"{SCR}/asm_daily_trades.parquet")
    print(f"DAILY: {len(syms)} syms, {len(ep)} episodes, {time.time()-t0:.0f}s")
    print("resp mean:", ep.resp.mean(), "null_resp:", ep.null_resp.mean())
    print("t2_win:", ep.t2_win.mean(), "t2_net:", ep.t2_net.mean(), "null_t2:", ep.null_t2_net.mean())
    print("t2 EXCESS:", ep.t2_net.mean() - ep.null_t2_net.mean())
    print("tr_net:", ep.tr_net.mean(), "null_tr:", ep.null_tr_net.mean(),
          "tr EXCESS:", ep.tr_net.mean() - ep.null_tr_net.mean())
