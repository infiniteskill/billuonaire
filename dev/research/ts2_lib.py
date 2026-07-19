"""ts2: taught ZONE toolkit — FVG-N, flip split (BRK/MIT sweep test), propulsion,
rejection bands, overlap stacking — plus respect-race episodes vs path-clean
time-local matched-level nulls (H1GRID null-B lesson)."""
import sys, zlib
import numpy as np

sys.path.insert(0, "/home/doom/Public/PROJECT/2026/trader/dev/research")
from tob_lib import zigzag, sym_K, ob_clusters, first_true
from ext_zigzag import wilder_atr
from dgrid_lib import fvg_cb

NMID, H_FILL, H_RACE, NULLS = 5, 70, 70, 5


def thr_arr(H, L):
    n = len(H); r = np.zeros(n); r[2:] = (H[2:] - L[2:]) / L[2:]
    return np.cumsum(r) / np.arange(1, n + 1)


def fvg_n_extra(O, H, L, C, f3, nmax=NMID):
    """Generalized N-candle wick gaps, m=2..nmax middles (burst = every middle
    closes beyond the near flank wick; same adaptive size threshold as fvg_cb).
    Deduped: kept only where no accepted gap (strict-3 or smaller-m) with an
    overlapping candle window AND overlapping band exists. Strict-3 = m=1 case."""
    n = len(H); thr = thr_arr(H, L)
    acc = {1: [], -1: []}
    for z in f3: acc[z["dir"]].append((z["born_i"] - 1, z["ev_i"], z["lo"], z["hi"]))
    out = []
    for m in range(2, nmax + 1):
        if n < m + 2: break
        sw = np.lib.stride_tricks.sliding_window_view(C, m)
        mn, mx = sw.min(1), sw.max(1)
        i_arr = np.arange(m + 1, n); a_arr = i_arr - m - 1
        for d in (1, -1):
            if d == 1:
                lo, hi = H[a_arr], L[i_arr]
                ok = (hi > lo) & ((hi - lo) / lo > thr[i_arr]) & (mn[i_arr - m] > lo)
            else:
                lo, hi = H[i_arr], L[a_arr]
                ok = (hi > lo) & ((hi - lo) / lo > thr[i_arr]) & (mx[i_arr - m] < hi)
            ok &= i_arr >= 14
            for k in np.where(ok)[0]:
                a, i, l_, h_ = int(a_arr[k]), int(i_arr[k]), float(lo[k]), float(hi[k])
                if any(i2 >= a and a2 <= i and min(h2, h_) > max(l2, l_)
                       for a2, i2, l2, h2 in acc[d]): continue
                acc[d].append((a, i, l_, h_))
                out.append(dict(dir=d, lo=l_, hi=h_, born_i=a + 1, ev_i=i, m=m))
    return out


def base_zones(O, H, L, C, atr, df):
    """OB (taught clusters + pivot distance), FVG3/FVGN (pivot-anchored dist),
    REJ (wick band at confirmed pivots, sweep-tagged)."""
    K = sym_K(atr, C); piv = zigzag(df, K, atr)
    conf = [p for p in piv if p.confirm_idx is not None]
    Z = []
    def add(ty, d, lo, hi, born, ev, dist, p0=-1, pex=np.nan, m=0, new=0, par=-1, swp=-1):
        Z.append(dict(ty=ty, dir=d, lo=float(lo), hi=float(hi), born=int(born), ev=int(ev),
                      dist=dist, p0=p0, pex=pex, m=m, new=new, par=par, swp=swp))
    for j in range(len(piv) - 1):
        p0, p1 = piv[j], piv[j + 1]
        if p0.confirm_idx is None: continue
        d = 1 if p0.side == "L" else -1
        pex = piv[j - 1].price if j else np.nan
        for cl in ob_clusters(O, H, L, C, p0.idx, p1.idx, d, piv[j - 1].idx if j else -1):
            dist = (max(0.0, cl["lo"] - p0.price) if d == 1
                    else max(0.0, p0.price - cl["hi"])) / atr[p0.idx]
            add("OB", d, cl["lo"], cl["hi"], cl["born_i"], max(cl["brk"], p0.confirm_idx),
                float(dist), p0=p0.idx, pex=pex)
    f3 = fvg_cb(O, H, L, C)
    for z in f3: z["m"] = 1
    for z in f3 + fvg_n_extra(O, H, L, C, f3):
        side = "L" if z["dir"] == 1 else "H"
        p = next((p for p in reversed(conf) if p.side == side and p.idx <= z["born_i"]), None)
        dist, ev = np.nan, z["ev_i"]
        if p is not None:
            dist = float((max(0.0, z["lo"] - p.price) if z["dir"] == 1
                          else max(0.0, p.price - z["hi"])) / atr[p.idx])
            ev = max(ev, p.confirm_idx)
        add("FVG3" if z["m"] == 1 else "FVGN", z["dir"], z["lo"], z["hi"], z["born_i"], ev,
            dist, m=z["m"], new=int(z["m"] > 1))
    for k, p in enumerate(piv):
        if p.confirm_idx is None: continue
        pex = piv[k - 2].price if k >= 2 else np.nan
        if p.side == "H":
            lo, hi, d = max(O[p.idx], C[p.idx]), H[p.idx], -1
            swp = int(p.price > pex) if np.isfinite(pex) else -1
        else:
            lo, hi, d = L[p.idx], min(O[p.idx], C[p.idx]), 1
            swp = int(p.price < pex) if np.isfinite(pex) else -1
        if hi > lo:
            add("REJ", d, lo, hi, p.idx, p.confirm_idx, 0.0, p0=p.idx, pex=pex, swp=swp)
    return Z


def flip_i_of(z, C, n):
    s = z["ev"] + 1
    if s >= n: return n
    r = first_true(C[s:] < z["lo"] if z["dir"] == 1 else C[s:] > z["hi"])
    return n if r is None else s + r


def first_touch(z, H, L, C, n):
    """Arm (price fully leaves box; dead if closed through first) then first touch.
    Returns (touch_bar, arm_bar) or (None, None)."""
    d, lo, hi = z["dir"], z["lo"], z["hi"]
    s = z["ev"] + 1
    if s >= n: return None, None
    brk = first_true(C[s:] < lo if d == 1 else C[s:] > hi)
    left = first_true(L[s:] > hi if d == 1 else H[s:] < lo)
    if left is None or (brk is not None and brk < left): return None, None
    s2 = s + left + 1
    if s2 >= n: return None, None
    r = first_true(L[s2:] <= hi if d == 1 else H[s2:] >= lo)
    return (None, None) if r is None else (s2 + r, s + left)


def race(H, L, C, d, E, a, t0, far, n):
    """1xATR favorable-vs-adverse race from edge E at touch bar t0 (tie=adverse).
    Returns (respect|None, fav_offset, blow)."""
    end = min(n, t0 + H_RACE)
    hs, ls = H[t0:end], L[t0:end]
    F, A = E + d * a, E - d * a
    fav = first_true(hs >= F) if d == 1 else first_true(ls <= F)
    adv = first_true(ls <= A) if d == 1 else first_true(hs >= A)
    blow = False
    if far is not None:
        bi = first_true(C[t0:end] < far) if d == 1 else first_true(C[t0:end] > far)
        blow = bi is not None and (fav is None or bi <= fav)
    if fav is None and adv is None: return None, None, blow
    if adv is None or (fav is not None and fav < adv): return 1, fav, blow
    return 0, fav, blow


def run_symbol(df, sym):
    O, H, L, C = (df[c].values for c in ("open", "high", "low", "close"))
    n = len(C); ts = df["ts"].values
    atr = wilder_atr(df)
    Z = base_zones(O, H, L, C, atr, df)
    for z in Z: z["flip"] = flip_i_of(z, C, n)
    kids = []
    for idx, z in enumerate(Z):
        t = z["flip"]
        if t < n:  # flip family: violated zone -> BRK (birth swing swept prior ext) / MIT / IFVG
            fz = None
            if z["ty"] == "OB" and z["p0"] >= 0 and np.isfinite(z["pex"]):
                ext = H[z["p0"]:t + 1].max() if z["dir"] == 1 else L[z["p0"]:t + 1].min()
                swept = ext > z["pex"] if z["dir"] == 1 else ext < z["pex"]
                fz = "BRK" if swept else "MIT"
            elif z["ty"] in ("FVG3", "FVGN"):
                fz = "IFVG"
            if fz:
                kids.append(dict(ty=fz, dir=-z["dir"], lo=z["lo"], hi=z["hi"], born=t, ev=t,
                                 dist=np.nan, p0=-1, pex=np.nan, m=0, new=0, par=-1, swp=-1))
        if z["ty"] == "OB":  # propulsion: first tap that closes back outside, directional body
            t0p, _ = first_touch(z, H, L, C, n)
            if t0p is not None:
                d = z["dir"]
                ok = (C[t0p] > z["hi"] and C[t0p] > O[t0p]) if d == 1 \
                    else (C[t0p] < z["lo"] and C[t0p] < O[t0p])
                if ok and H[t0p] > L[t0p]:
                    kids.append(dict(ty="PRP", dir=d, lo=float(L[t0p]), hi=float(H[t0p]),
                                     born=t0p, ev=t0p, dist=z["dist"], p0=z["p0"], pex=np.nan,
                                     m=0, new=0, par=idx, swp=-1))
    for z in kids: z["flip"] = flip_i_of(z, C, n)
    Z += kids
    zlo = np.array([z["lo"] for z in Z]); zhi = np.array([z["hi"] for z in Z])
    zdir = np.array([z["dir"] for z in Z]); zev = np.array([z["ev"] for z in Z])
    zfl = np.array([z["flip"] for z in Z])
    spl = np.where(np.abs(O[1:] / np.where(C[:-1] > 0, C[:-1], np.nan) - 1) > 0.2)[0] + 1
    half = zlib.crc32(sym.encode()) % 2
    rows, unres = [], 0
    for z in Z:
        t0, ab = first_touch(z, H, L, C, n)
        if t0 is None: continue
        a = atr[t0]
        if not np.isfinite(a) or a <= 0: continue
        if len(spl) and ((spl >= z["born"]) & (spl <= min(n - 1, t0 + H_RACE))).any(): continue
        d, lo, hi = z["dir"], z["lo"], z["hi"]
        E, far = (hi, lo) if d == 1 else (lo, hi)
        resp, favb, blow = race(H, L, C, d, E, a, t0, far, n)
        if resp is None: unres += 1; continue
        depth = np.nan
        if resp == 1 and hi > lo:
            pen = (hi - L[t0:t0 + favb + 1].min()) if d == 1 else (H[t0:t0 + favb + 1].max() - lo)
            depth = float(pen / (hi - lo))
        stk = ((zdir == d) & (zev <= t0) & (zfl >= t0)
               & (np.minimum(zhi, hi) > np.maximum(zlo, lo)))
        nst = int(stk.sum())
        plive = int(Z[z["par"]]["flip"] > t0) if z["par"] >= 0 else -1
        null, nn = np.nan, 0
        aab = atr[ab]
        if np.isfinite(aab) and aab > 0:  # matched null: same sym, time-local anchor in
            D = d * (C[ab] - E) / aab     # [arm, touch], same ATR-distance-from-price level
            rng = np.random.default_rng(zlib.crc32(f"{sym}|{z['ty']}|{t0}|{E:.4f}".encode()))
            W = (t0 - ab) + H_FILL
            acc = []
            for _ in range(NULLS):
                u = int(rng.integers(ab, t0 + 1))
                au = atr[u]
                if not np.isfinite(au) or au <= 0: continue
                Ep = C[u] - d * D * au
                if Ep <= 0 or (L[u] <= Ep if d == 1 else H[u] >= Ep): continue  # path-clean
                rr = first_true(L[u + 1:u + 1 + W] <= Ep if d == 1 else H[u + 1:u + 1 + W] >= Ep)
                if rr is None: continue
                tt = u + 1 + rr
                at2 = atr[tt]
                if not np.isfinite(at2) or at2 <= 0: continue
                if len(spl) and ((spl >= u) & (spl <= min(n - 1, tt + H_RACE))).any(): continue
                nresp, _, _ = race(H, L, C, d, Ep, at2, tt, None, n)
                if nresp is not None: acc.append(nresp)
            if acc: null, nn = float(np.mean(acc)), len(acc)
        rows.append((sym, half, z["ty"], d, t0, ts[t0], z["dist"], nst, t0 - z["ev"],
                     resp, int(blow), depth, z["m"], z["new"], plive, z["swp"], null, nn))
    counts = {}
    for z in Z: counts[z["ty"]] = counts.get(z["ty"], 0) + 1
    return rows, counts, unres


COLS = ["sym", "half", "ty", "dir", "t0", "ts0", "dist", "nst", "wait",
        "resp", "blow", "depth", "m", "new", "plive", "swp", "null", "nn"]
