"""Taught-OB library: user's order-block spec on H1.

Spec (verbatim rules):
- Extreme swing = ATR-zigzag pivot (ext_zigzag), per-symbol K calibrated to a
  ~4.7% two-sided leg floor (TF/vol-invariant).
- OB = opposite-direction candle OR consolidation cluster (consecutive bars with
  overlapping ranges) that pauses a leg; box = FULL hi-lo of the cluster.
- Power = nearness to swing pivot, in ATR (0 = at pivot).
- FVG = 3-candle wick gap (fvg_cb rule). Broken zone flips (IOB breaker / IFVG).
- Zone tradeable only once its anchoring pivot is CONFIRMED (causal gate).
- Trade = first revisit after price has LEFT the zone. Fade direction.
"""
import sys, zlib
import numpy as np, pandas as pd

sys.path.insert(0, "/home/doom/Public/PROJECT/2026/trader/dev/research")
import inspect
import ext_zigzag
from ext_zigzag import wilder_atr
from dgrid_lib import fvg_cb, R0, CAP, SLIP, STT, EXCH, DP

# ext_zigzag.zigzag crashes when a pivot confirms on its own extreme bar
# (empty argmin/argmax slice). Source-patch the guard in; repo file untouched.
_src = inspect.getsource(ext_zigzag.zigzag)
_src = _src.replace("pend = j0 + int(np.argmax(h[j0:i + 1]))",
                    "pend = (j0 + int(np.argmax(h[j0:i + 1]))) if j0 <= i else i")
_src = _src.replace("pend = j0 + int(np.argmin(l[j0:i + 1]))",
                    "pend = (j0 + int(np.argmin(l[j0:i + 1]))) if j0 <= i else i")
_ns = dict(vars(ext_zigzag))
exec(_src, _ns)
zigzag = _ns["zigzag"]

PCT_LEG = 0.047          # taught leg floor
K_LO, K_HI = 3.0, 14.0
SL_ATR, TGT_R = 1.5, 2.0 # stop 1.5xATR, target 2R
H_FILL = 70              # fill window: 10 sessions x 7 H1 bars
H_TRADE = 70             # time stop: 10 sessions from fill
FLIP_SCAN = True


def first_true(mask):
    """Index of first True in bool array, else None."""
    if not len(mask): return None
    i = int(np.argmax(mask))
    return i if mask[i] else None


def sym_K(atr, C):
    with np.errstate(invalid="ignore"):
        atrp = np.nanmedian(atr / C)
    return float(np.clip(PCT_LEG / atrp, K_LO, K_HI)) if atrp > 0 else 6.0


def ob_clusters(O, H, L, C, a, b, d, prev_idx):
    """Opposite-candle pause clusters inside leg a->b (d=+1 up-leg => demand OBs).
    Cluster: seed opposite candle (or pivot bar a, extended back through
    consecutive opposite candles), extend forward while ranges overlap and no
    close beyond the box in leg direction. Break bar = continuation close."""
    out = []
    opp = (C < O) if d == 1 else (C > O)
    i = a
    while i < b:
        if i != a and not opp[i]:
            i += 1; continue
        s = i
        if i == a:                       # pivot-anchored: sweep back through flush
            while s - 1 > prev_idx and s > a - 5 and opp[s - 1]: s -= 1
        lo, hi, j = L[s:i + 1].min(), H[s:i + 1].max(), i
        while j + 1 < b:
            nb = j + 1
            if d == 1 and (L[nb] > hi or C[nb] > hi): break
            if d == -1 and (H[nb] < lo or C[nb] < lo): break
            lo, hi, j = min(lo, L[nb]), max(hi, H[nb]), nb
        # continuation break: first close beyond box in leg direction
        brk = next((t for t in range(j + 1, min(len(C), b + 21))
                    if (C[t] > hi if d == 1 else C[t] < lo)), None)
        if brk is not None and hi > lo:
            out.append(dict(lo=float(lo), hi=float(hi), born_i=int(s),
                            end_i=int(j), brk=int(brk)))
        i = j + 1
    return out


def detect(df):
    """Full taught detection for one symbol. Returns (zones, meta)."""
    O, H, L, C = (df[c].values for c in ("open", "high", "low", "close"))
    n = len(df)
    atr = wilder_atr(df)
    K = sym_K(atr, C)
    piv = zigzag(df, K, atr)
    conf = [p for p in piv if p.confirm_idx is not None]
    zones = []
    # ---- taught OBs per leg
    for j in range(len(piv) - 1):
        p0, p1 = piv[j], piv[j + 1]
        if p0.confirm_idx is None: continue
        d = 1 if p0.side == "L" else -1
        prev_idx = piv[j - 1].idx if j else -1
        for cl in ob_clusters(O, H, L, C, p0.idx, p1.idx, d, prev_idx):
            a0 = atr[p0.idx]
            dist = (max(0.0, cl["lo"] - p0.price) if d == 1
                    else max(0.0, p0.price - cl["hi"])) / a0
            zones.append(dict(type="OB", dir=d, lo=cl["lo"], hi=cl["hi"],
                              born_i=cl["born_i"], ev_i=max(cl["brk"], p0.confirm_idx),
                              piv_i=p0.idx, piv_px=p0.price, dist_atr=float(dist)))
    # ---- taught FVGs (wick rule), anchored to last same-side confirmed pivot
    for z in fvg_cb(O, H, L, C):
        side = "L" if z["dir"] == 1 else "H"
        p = next((p for p in reversed(conf)
                  if p.side == side and p.idx <= z["born_i"]), None)
        if p is None: continue
        dist = (max(0.0, z["lo"] - p.price) if z["dir"] == 1
                else max(0.0, p.price - z["hi"])) / atr[p.idx]
        zones.append(dict(type="FVG", dir=z["dir"], lo=z["lo"], hi=z["hi"],
                          born_i=z["born_i"], ev_i=max(z["ev_i"], p.confirm_idx),
                          piv_i=p.idx, piv_px=p.price, dist_atr=float(dist)))
    # ---- flips: close beyond distal edge -> breaker (IOB) / iFVG
    if FLIP_SCAN:
        flips = []
        for z in zones:
            d, lo, hi = z["dir"], z["lo"], z["hi"]
            s = z["ev_i"] + 1
            r = first_true(C[s:] < lo if d == 1 else C[s:] > hi)
            t = None if r is None else s + r
            z["flip_i"] = t
            if t is None: continue
            nd = -d
            side = "L" if nd == 1 else "H"
            p = next((p for p in reversed(conf)
                      if p.side == side and p.idx < t and p.confirm_idx <= t), None)
            fz = dict(type="IOB" if z["type"] == "OB" else "IFVG", dir=nd,
                      lo=lo, hi=hi, born_i=t, ev_i=t, dist_atr=np.nan,
                      piv_i=p.idx if p else -1,
                      piv_px=p.price if p else np.nan, flip_i=None)
            flips.append(fz)
        zones += flips
    # ---- overlap grade: same-dir different-type box intersection, both live
    if zones:
        zlo = np.array([z["lo"] for z in zones]); zhi = np.array([z["hi"] for z in zones])
        zd = np.array([z["dir"] for z in zones]); zev = np.array([z["ev_i"] for z in zones])
        zty = np.array([z["type"] for z in zones])
        zfl = np.array([z.get("flip_i") if z.get("flip_i") is not None else n + 1
                        for z in zones])
        for k, z in enumerate(zones):
            m = ((zd == z["dir"]) & (zty != z["type"]) & (zev <= z["ev_i"])
                 & (zfl > z["ev_i"]) & (np.minimum(zhi, z["hi"]) > np.maximum(zlo, z["lo"])))
            z["n_ov"] = int(m.sum())
    meta = dict(K=K, n_piv=len(piv), n_conf=len(conf),
                atrp=float(np.nanmedian(atr / C)))
    return zones, atr, H, L, C, O, meta


def sim(O, H, L, C, atr, tf, d, ent):
    """Gap-aware 2R/1.5ATR sim from fill bar tf at price ent. Stop-first
    (conservative) on every bar incl. fill bar. Returns (netR, grossR, win, exit_bar)."""
    n = len(C)
    a = atr[tf]
    if np.isnan(a) or a <= 0 or ent <= 0: return np.nan, np.nan, False, tf
    sd = SL_ATR * a
    stop, tgt = ent - d * sd, ent + d * TGT_R * sd
    last = min(tf + H_TRADE, n) - 1
    ex, exb, win = None, last, False
    for b in range(tf, last + 1):
        o = O[b]
        if b > tf:
            if d * (o - stop) <= 0: ex, exb = o, b; break
            if d * (o - tgt) >= 0: ex, exb, win = o, b, True; break
        if d == 1:
            if L[b] <= stop: ex, exb = stop, b; break
            if H[b] >= tgt: ex, exb, win = tgt, b, True; break
        else:
            if H[b] >= stop: ex, exb = stop, b; break
            if L[b] <= tgt: ex, exb, win = tgt, b, True; break
    if ex is None: ex = C[last]
    qty = min(R0 / sd, CAP / ent)
    Rr = qty * sd
    gross = d * (ex - ent) * qty / Rr
    net = gross - ((SLIP + STT + EXCH) * qty * (ent + ex) + DP) / Rr
    return float(net), float(gross), win, exb


def episodes(zones, O, H, L, C, atr, ts):
    """First-revisit episode per zone: arm (price fully leaves box), first touch,
    depth, and three limit policies EDGE/CE/OTE (gap-aware fills, cancel on
    distal break before fill or window end)."""
    n = len(C); out = []
    for z in zones:
        d, lo, hi = z["dir"], z["lo"], z["hi"]
        edge = hi if d == 1 else lo
        s = z["ev_i"] + 1
        if s >= n: continue
        broken = C[s:] < lo if d == 1 else C[s:] > hi
        left = L[s:] > hi if d == 1 else H[s:] < lo
        b1, a1 = first_true(broken), first_true(left)
        if a1 is None or (b1 is not None and b1 < a1): continue  # broken pre-arm
        s2 = s + a1 + 1
        r = first_true(L[s2:] <= hi if d == 1 else H[s2:] >= lo)
        if r is None: continue
        t0 = s2 + r
        ep = dict(type=z["type"], dir=d, lo=lo, hi=hi, t0=t0, ts0=ts[t0],
                  born_i=z["born_i"], dist_atr=z["dist_atr"], n_ov=z["n_ov"],
                  wait_bars=t0 - z["ev_i"])
        # OTE level: 0.705 retrace of the leg, causal running extreme to t0
        a = z["piv_i"]
        if a >= 0:
            ext = H[a:t0 + 1].max() if d == 1 else L[a:t0 + 1].min()
            ote = ext - 0.705 * (ext - z["piv_px"]) if d == 1 \
                else ext + 0.705 * (z["piv_px"] - ext)
        else:
            ote = np.nan
        ce = (lo + hi) / 2
        for name, lvl in (("EDGE", edge), ("CE", ce), ("OTE", ote)):
            tf = fp = None
            if not np.isnan(lvl):
                for t in range(t0, min(n, t0 + H_FILL)):
                    hit = L[t] <= lvl if d == 1 else H[t] >= lvl
                    if hit:
                        fp = min(O[t], lvl) if d == 1 else max(O[t], lvl)
                        tf = t; break
                    if (C[t] < lo if d == 1 else C[t] > hi): break  # broken, cancel
            if tf is None:
                ep[f"{name}_fill"] = False
                ep[f"{name}_net"] = np.nan; ep[f"{name}_gross"] = np.nan
                ep[f"{name}_win"] = False
            else:
                net, gross, win, exb = sim(O, H, L, C, atr, tf, d, fp)
                ep[f"{name}_fill"] = not np.isnan(net)
                ep[f"{name}_net"], ep[f"{name}_gross"] = net, gross
                ep[f"{name}_win"] = win
                if name == "EDGE": ep["exit_b"] = exb
        # depth: max penetration into box during EDGE trade span (descriptive)
        span_end = ep.get("exit_b", min(n - 1, t0 + H_TRADE))
        pen = (hi - L[t0:span_end + 1].min()) if d == 1 \
            else (H[t0:span_end + 1].max() - lo)
        ep["depth"] = float(pen / (hi - lo)) if hi > lo else np.nan
        if np.isnan(ote) or hi <= lo:
            ep["ote_pos"] = np.nan
        else:  # OTE penetration fraction from proximal edge (<0 outside, >1 beyond)
            ep["ote_pos"] = float((hi - ote) / (hi - lo)) if d == 1 \
                else float((ote - lo) / (hi - lo))
        out.append(ep)
    return out


def run_symbol(df, sym):
    zones, atr, H, L, C, O, meta = detect(df)
    ts = df["ts"].values
    eps = episodes(zones, O, H, L, C, atr, ts)
    for z in zones: z["sym"] = sym
    for e in eps: e["sym"] = sym; e["half"] = zlib.crc32(sym.encode()) % 2
    return zones, eps, meta
