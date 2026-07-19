"""tune_lib — parametrized SURVIVOR tools for the ARMORED sweep.

Survivors tuned: zigzag extremes (leg floor + band), taught-OB (box/join/maxdist),
FVG-N (burst span + min gap), break-depth zone-death law, overlap stacking
(merge tol + min stack), sweep-aligned birth window, entry reference, PO3 gate,
parent-linked propulsion (linkage enforced, no free knobs).

USER-SPECIFIED MERGE RULE: same-direction gaps whose candle windows overlap or are
contiguous (share a bar, or start the bar after the previous window ends) belong to
ONE displacement burst and are merged into ONE FVG, box = union of the fragments.
Stack counting de-dups by structure id: merged FVG = one member, PRP child shares
its parent's id (fragments/children can never inflate a stack).

Respect race, null method (time-local path-clean matched levels, 5 draws), splice
guard, 70-bar windows: identical to ts2_lib (ZONES run)."""
import sys, zlib
import numpy as np, pandas as pd

RES = "/home/doom/Public/PROJECT/2026/trader/dev/research"
if RES not in sys.path: sys.path.insert(0, RES)
from tob_lib import zigzag, first_true
from ext_zigzag import wilder_atr

PARQ = "/home/doom/Public/PROJECT/2026/trader/runs/artifacts-data/l4_h1.parquet"
H_RACE, H_FILL, NULLS = 70, 70, 5
B1, B2 = pd.Timestamp("2024-07-27 18:30"), pd.Timestamp("2025-07-22 18:30")  # thirds (UTC)

BASE = dict(pct=.047, band="wick", ob_box="full", ob_join=0.0, ob_maxd=np.inf,
            fvg_mmax=3, fvg_q=0.10, death=0.0, inset=0.0)

COLS = ["sym", "half", "ty", "dir", "zid", "sid", "born", "evi", "evts", "dist", "m",
        "life", "arm", "t0", "ts0", "resp", "r2", "blow", "null", "null2", "nn",
        "plive", "swb", "nst0", "nst25", "nso0", "nso25"]


def load(half=None):
    df = pd.read_parquet(PARQ)
    syms = sorted(df["symbol"].unique())
    if half is not None:
        syms = [s for s in syms if zlib.crc32(s.encode()) % 2 == half]
    return df, syms


def to_naive(ts):
    v = pd.DatetimeIndex(ts)
    return (v.tz_convert("UTC").tz_localize(None) if v.tz is not None else v).values


def sym_K(atr, C, pct):
    with np.errstate(invalid="ignore"):
        atrp = np.nanmedian(atr / C)
    return float(np.clip(pct / atrp, 3.0, 14.0)) if atrp > 0 else 6.0


# ---------------- detectors ----------------
def ob_clusters(O, H, L, C, atr, a, b, d, prev_idx, box, join):
    out = []
    opp = (C < O) if d == 1 else (C > O)
    i = a
    while i < b:
        if i != a and not opp[i]:
            i += 1; continue
        s = i
        if i == a:
            while s - 1 > prev_idx and s > a - 5 and opp[s - 1]: s -= 1
        lo, hi, j = L[s:i + 1].min(), H[s:i + 1].max(), i
        while j + 1 < b:
            nb = j + 1
            tol = join * atr[nb] if np.isfinite(atr[nb]) else 0.0
            if d == 1 and (L[nb] > hi + tol or C[nb] > hi): break
            if d == -1 and (H[nb] < lo - tol or C[nb] < lo): break
            lo, hi, j = min(lo, L[nb]), max(hi, H[nb]), nb
        brk = next((t for t in range(j + 1, min(len(C), b + 21))
                    if (C[t] > hi if d == 1 else C[t] < lo)), None)
        if brk is not None:
            if box == "body":
                blo = float(np.minimum(O[s:j + 1], C[s:j + 1]).min())
                bhi = float(np.maximum(O[s:j + 1], C[s:j + 1]).max())
            else:
                blo, bhi = float(lo), float(hi)
            if bhi > blo:
                out.append(dict(lo=blo, hi=bhi, born=int(s), brk=int(brk)))
        i = j + 1
    return out


def fvg_zones(O, H, L, C, atr, conf, cfg):
    """all m=1..mmax wick gaps -> same-burst merge -> pivot-anchored dist.
    Returns (merged zones, fragments with grp id)."""
    n = len(C); mmax, q = cfg["fvg_mmax"], cfg["fvg_q"]
    raw = []
    for m in range(1, mmax + 1):
        if n < m + 2: continue
        sw = np.lib.stride_tricks.sliding_window_view(C, m)
        mn, mx = sw.min(1), sw.max(1)
        i_arr = np.arange(m + 1, n); a_arr = i_arr - m - 1
        for d in (1, -1):
            if d == 1:
                lo, hi = H[a_arr], L[i_arr]
                ok = (hi > lo) & (mn[a_arr + 1] > H[a_arr])
            else:
                lo, hi = H[i_arr], L[a_arr]
                ok = (hi > lo) & (mx[a_arr + 1] < L[a_arr])
            ok &= (i_arr >= 14) & np.isfinite(atr[i_arr])
            if q > 0: ok &= (hi - lo) > q * atr[i_arr]
            for k in np.where(ok)[0]:
                raw.append(dict(dir=d, a=int(a_arr[k]), i=int(i_arr[k]),
                                lo=float(lo[k]), hi=float(hi[k])))
    out = []
    for d in (1, -1):
        fr = sorted((r for r in raw if r["dir"] == d), key=lambda r: (r["a"], r["i"]))
        cur = None
        for r in fr:
            if cur is not None and r["a"] <= cur["i"] + 1:   # overlap/contiguous window
                cur["i"] = max(cur["i"], r["i"]); cur["lo"] = min(cur["lo"], r["lo"])
                cur["hi"] = max(cur["hi"], r["hi"]); cur["nf"] += 1
            else:
                if cur is not None: out.append(cur)
                cur = dict(dir=d, a=r["a"], i=r["i"], lo=r["lo"], hi=r["hi"], nf=1)
            r["grp"] = len(out)  # index of merged zone (current)
        if cur is not None: out.append(cur)
    Z = []
    for gidx, gz in enumerate(out):
        d = gz["dir"]; born = gz["a"] + 1; ev = gz["i"]; dist = np.nan
        side = "L" if d == 1 else "H"
        p = next((p for p in reversed(conf) if p.side == side and p.idx <= born), None)
        if p is not None:
            dist = float((max(0.0, gz["lo"] - p.price) if d == 1
                          else max(0.0, p.price - gz["hi"])) / atr[p.idx])
            ev = max(ev, p.confirm_idx)
        Z.append(dict(ty="FVG", dir=d, lo=gz["lo"], hi=gz["hi"], born=born, evi=ev,
                      dist=dist, m=gz["nf"], p0=-1, pex=np.nan, par=-1, gidx=gidx))
    return Z, out, raw


def band_zones(O, H, L, C, atr, piv, mode):
    """lesson-13 pivot bands (wick: cluster while wicks reach running highest body
    edge; atr: 0.5*ATR cluster). Causal (bars <= confirm). Fade direction."""
    n = len(C); Z = []
    for j, p in enumerate(piv):
        if p.confirm_idx is None: continue
        lo_b = piv[j - 1].idx if j else 0
        hi_b = min(piv[j + 1].idx if j < len(piv) - 1 else n - 1, p.confirm_idx)
        if mode == "wick":
            if p.side == "H":
                bt = max(O[p.idx], C[p.idx]); s = e = p.idx
                while s - 1 > lo_b and H[s - 1] >= bt: s -= 1; bt = max(bt, O[s], C[s])
                while e + 1 < hi_b and H[e + 1] >= bt: e += 1; bt = max(bt, O[e], C[e])
                lo, hi = bt, p.price
            else:
                bt = min(O[p.idx], C[p.idx]); s = e = p.idx
                while s - 1 > lo_b and L[s - 1] <= bt: s -= 1; bt = min(bt, O[s], C[s])
                while e + 1 < hi_b and L[e + 1] <= bt: e += 1; bt = min(bt, O[e], C[e])
                lo, hi = p.price, bt
        else:
            half = 0.5 * atr[p.idx]; s = e = p.idx
            if p.side == "H":
                while s - 1 > lo_b and H[s - 1] >= p.price - half: s -= 1
                while e + 1 < hi_b and H[e + 1] >= p.price - half: e += 1
                lo, hi = float(H[s:e + 1].min()), p.price
            else:
                while s - 1 > lo_b and L[s - 1] <= p.price + half: s -= 1
                while e + 1 < hi_b and L[e + 1] <= p.price + half: e += 1
                lo, hi = p.price, float(L[s:e + 1].max())
        if hi > lo:
            Z.append(dict(ty="BAND", dir=-1 if p.side == "H" else 1, lo=float(lo),
                          hi=float(hi), born=p.idx, evi=p.confirm_idx, dist=0.0,
                          m=0, p0=p.idx, pex=np.nan, par=-1, gidx=-1))
    return Z


def sweep_bars(piv, H, L, C, n):
    """pool penetration that closes back inside -> sweep (bar, reversal dir)."""
    out = []
    for p in piv:
        if p.confirm_idx is None or p.confirm_idx + 1 >= n: continue
        s = p.confirm_idx + 1
        if p.side == "H":
            r = first_true(H[s:] >= p.price)
            if r is not None and C[s + r] < p.price: out.append((s + r, -1))
        else:
            r = first_true(L[s:] <= p.price)
            if r is not None and C[s + r] > p.price: out.append((s + r, 1))
    return sorted(out)


# ---------------- life/death + episodes ----------------
def kill_bar(z, H, L, C, atr, D, n):
    """first close through far edge by >= D*ATR (D=0: any close-through)."""
    d, lo, hi = z["dir"], z["lo"], z["hi"]
    s = z["evi"] + 1
    if s >= n: return n
    if D <= 0:
        r = first_true(C[s:] < lo if d == 1 else C[s:] > hi)
    else:
        r = first_true((C[s:] < lo - D * atr[s:]) if d == 1
                       else (C[s:] > hi + D * atr[s:]))
    return n if r is None else s + r


def race(H, L, C, d, E, a, t0, far, n):
    """(resp, r2, blow): 1x fav-vs-1x adverse (tie=adverse), 2x fav before 1x adverse,
    close-through-far before 1x fav."""
    end = min(n, t0 + H_RACE)
    hs, ls, cs = H[t0:end], L[t0:end], C[t0:end]
    f1 = first_true(hs >= E + a) if d == 1 else first_true(ls <= E - a)
    f2 = first_true(hs >= E + 2 * a) if d == 1 else first_true(ls <= E - 2 * a)
    ad = first_true(ls <= E - a) if d == 1 else first_true(hs >= E + a)
    blow = False
    if far is not None:
        bi = first_true(cs < far) if d == 1 else first_true(cs > far)
        blow = bi is not None and (f1 is None or bi <= f1)
    if f1 is None and ad is None: return None, None, blow
    resp = 1 if (ad is None or (f1 is not None and f1 < ad)) else 0
    r2 = int(f2 is not None and (ad is None or f2 < ad))
    return resp, r2, blow


def zone_lives(z, O, H, L, C, atr, D, inset, n, kb):
    """armed first retest per LIFE. Life k+1 = re-arm after a shallow (< D deep)
    violation while the zone is still alive under the break-depth law.
    Returns [(t0, arm, life, E)]."""
    d, lo, hi = z["dir"], z["lo"], z["hi"]
    E0 = hi if d == 1 else lo
    eps, s, life = [], z["evi"] + 1, 0
    while s < n and life <= 4:
        r = first_true(L[s:] > hi if d == 1 else H[s:] < lo)
        if r is None: break
        arm = s + r
        if arm >= kb or arm + 1 >= n: break
        E = E0 - d * inset * atr[arm] if inset else E0
        r = first_true(L[arm + 1:] <= E if d == 1 else H[arm + 1:] >= E)
        if r is None: break
        t0 = arm + 1 + r
        if t0 > kb: break
        eps.append((t0, arm, life, E))
        r = first_true(C[t0:] < lo if d == 1 else C[t0:] > hi)  # any-depth violation
        if r is None: break
        v = t0 + r
        if v >= kb: break
        s, life = v + 1, life + 1
    return eps


def null_rates(sym, ty, t0, arm, E, d, H, L, C, atr, spl, n):
    """ts2 matched null: same signed ATR-distance-from-price level, anchor drawn in
    [arm, t0], path-clean; returns (mean resp, mean r2, ndraws)."""
    aab = atr[arm]
    if not (np.isfinite(aab) and aab > 0): return np.nan, np.nan, 0
    Dd = d * (C[arm] - E) / aab
    rng = np.random.default_rng(zlib.crc32(f"{sym}|{ty}|{t0}|{E:.4f}".encode()))
    W = (t0 - arm) + H_FILL
    acc, acc2 = [], []
    for _ in range(NULLS):
        u = int(rng.integers(arm, t0 + 1))
        au = atr[u]
        if not np.isfinite(au) or au <= 0: continue
        Ep = C[u] - d * Dd * au
        if Ep <= 0 or (L[u] <= Ep if d == 1 else H[u] >= Ep): continue
        rr = first_true(L[u + 1:u + 1 + W] <= Ep if d == 1 else H[u + 1:u + 1 + W] >= Ep)
        if rr is None: continue
        tt = u + 1 + rr
        at2 = atr[tt]
        if not np.isfinite(at2) or at2 <= 0: continue
        if len(spl) and ((spl >= u) & (spl <= min(n - 1, tt + H_RACE))).any(): continue
        nr, nr2, _ = race(H, L, C, d, Ep, at2, tt, None, n)
        if nr is not None: acc.append(nr); acc2.append(nr2)
    return ((np.mean(acc), np.mean(acc2), len(acc)) if acc else (np.nan, np.nan, 0))


# ---------------- per-symbol driver ----------------
def run_symbol(g, sym, cfg, tools, stack=False):
    """tools subset of {OB, FVG, BAND, FLIP, PRP}. One row per zone-life-episode;
    zones never retested get one row with t0=-1."""
    O, H, L, C = (g[c].values for c in ("open", "high", "low", "close"))
    n = len(C); ts = to_naive(g["ts"])
    atr = wilder_atr(g)
    K = sym_K(atr, C, cfg["pct"])
    piv = zigzag(g, K, atr)
    conf = [p for p in piv if p.confirm_idx is not None]
    spl = np.where(np.abs(O[1:] / np.where(C[:-1] > 0, C[:-1], np.nan) - 1) > 0.2)[0] + 1
    half = zlib.crc32(sym.encode()) % 2
    D, inset = cfg["death"], cfg["inset"]

    Z, frags = [], []
    if "OB" in tools:
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
                              m=0, p0=p0.idx, pex=pex, par=-1, gidx=-1))
    if "FVG" in tools:
        fz, merged, raw = fvg_zones(O, H, L, C, atr, conf, cfg)
        base = len(Z); Z += fz
        frags = [dict(dir=r["dir"], lo=r["lo"], hi=r["hi"], i=r["i"],
                      z=base + r["grp"]) for r in raw]
    if "BAND" in tools:
        Z += band_zones(O, H, L, C, atr, piv, cfg["band"])

    for idx, z in enumerate(Z):
        z["kb"] = kill_bar(z, H, L, C, atr, D, n)
        z["sid"] = idx

    if "FLIP" in tools:
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
            kids.append(dict(ty=fy, dir=-z["dir"], lo=z["lo"], hi=z["hi"], born=t,
                             evi=t, dist=np.nan, m=0, p0=-1, pex=np.nan, par=-1, gidx=-1))
        for z in kids:
            z["kb"] = kill_bar(z, H, L, C, atr, D, n); z["sid"] = len(Z); Z.append(z)
    if "PRP" in tools:
        kids = []
        for idx, z in enumerate(Z):
            if z["ty"] != "OB": continue
            lv = zone_lives(z, O, H, L, C, atr, D, 0.0, n, z["kb"])
            if not lv: continue
            t0 = lv[0][0]; d = z["dir"]
            ok = (C[t0] > z["hi"] and C[t0] > O[t0]) if d == 1 \
                else (C[t0] < z["lo"] and C[t0] < O[t0])
            if ok and H[t0] > L[t0]:
                kids.append(dict(ty="PRP", dir=d, lo=float(L[t0]), hi=float(H[t0]),
                                 born=t0, evi=t0, dist=z["dist"], m=0, p0=z["p0"],
                                 pex=np.nan, par=idx, gidx=-1))
        for z in kids:
            z["kb"] = kill_bar(z, H, L, C, atr, D, n)
            z["sid"] = Z[z["par"]]["sid"]  # child shares parent's structure id
            Z.append(z)

    sw = sweep_bars(piv, H, L, C, n)
    swu = np.array([b for b, d in sw if d == 1], int)
    swd = np.array([b for b, d in sw if d == -1], int)

    if stack:
        st = [z for z in Z if z["ty"] != "BAND"]
        zlo = np.array([z["lo"] for z in st]); zhi = np.array([z["hi"] for z in st])
        zdir = np.array([z["dir"] for z in st]); zev = np.array([z["evi"] for z in st])
        zkb = np.array([z["kb"] for z in st]); zsid = np.array([z["sid"] for z in st])
        zisf = np.array([z["ty"] == "FVG" for z in st])
        flo = np.array([f["lo"] for f in frags]); fhi = np.array([f["hi"] for f in frags])
        fdir = np.array([f["dir"] for f in frags], int)
        fev = np.array([f["i"] for f in frags], int)
        fkb = np.array([Z[f["z"]]["kb"] for f in frags], int)

    rows = []
    for zid, z in enumerate(Z):
        d, lo, hi = z["dir"], z["lo"], z["hi"]
        far = lo if d == 1 else hi
        base = (sym, half, z["ty"], d, zid, z["sid"], z["born"], z["evi"],
                ts[min(z["evi"], n - 1)], z["dist"], z["m"])
        arr = swu if d == 1 else swd
        j = np.searchsorted(arr, z["born"], side="right") - 1
        swb = int(z["born"] - arr[j]) if j >= 0 else -1
        lv = zone_lives(z, O, H, L, C, atr, D, inset, n, z["kb"])
        keep = []
        for (t0, arm, life, E) in lv:
            a = atr[t0]
            if not np.isfinite(a) or a <= 0: continue
            if len(spl) and ((spl >= z["born"]) & (spl <= min(n - 1, t0 + H_RACE))).any(): continue
            resp, r2, blow = race(H, L, C, d, E, a, t0, far, n)
            if resp is None: continue
            keep.append((t0, arm, life, E, resp, r2, blow))
        if not keep:
            rows.append(base + (-1, -1, -1, ts[0], np.nan, np.nan, np.nan, np.nan, np.nan,
                                0, -1, swb, 0, 0, 0, 0))
            continue
        for (t0, arm, life, E, resp, r2, blow) in keep:
            plive = int(Z[z["par"]]["kb"] > t0) if z["par"] >= 0 else -1
            nl, nl2, nn = null_rates(sym, z["ty"], t0, arm, E, d, H, L, C, atr, spl, n)
            ns0 = ns25 = no0 = no25 = 0
            if stack:
                for tol_i, tol in enumerate((0.0, 0.25)):
                    t_ = tol * atr[t0]
                    ov = (np.minimum(zhi, hi) - np.maximum(zlo, lo)) > -t_
                    m1 = (zdir == d) & (zev <= t0) & (zkb >= t0) & ov
                    new = len(np.unique(zsid[m1]))
                    old = int((m1 & ~zisf).sum())  # fragments replace merged FVGs
                    if len(flo):
                        mf = ((fdir == d) & (fev <= t0) & (fkb >= t0)
                              & ((np.minimum(fhi, hi) - np.maximum(flo, lo)) > -t_))
                        old += int(mf.sum())
                    if tol_i == 0: ns0, no0 = new, old
                    else: ns25, no25 = new, old
            rows.append(base + (life, arm, t0, ts[t0], float(resp), float(r2),
                                float(blow), nl, nl2, nn, plive, swb, ns0, ns25, no0, no25))
    return rows
