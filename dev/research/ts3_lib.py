"""ts3_lib — taught-spec LIQUIDITY tools (lessons 5/15/16): pools v2, sweeps, voids, PO3 coils."""
import sys, zlib, inspect
import numpy as np, pandas as pd
sys.path.insert(0, '/home/doom/Public/PROJECT/2026/trader/dev/research')
import ext_zigzag
from ext_zigzag import wilder_atr, Pivot

# reuse ext_zigzag.zigzag verbatim + guard for the empty-slice edge case (pivot confirms
# on the running-extreme bar itself -> j0 > i). Repo file stays untouched.
_src = inspect.getsource(ext_zigzag.zigzag)
_src = _src.replace("pend = j0 + int(np.argmin(l[j0:i + 1]))",
                    "pend = (j0 + int(np.argmin(l[j0:i + 1]))) if j0 <= i else i")
_src = _src.replace("pend = j0 + int(np.argmax(h[j0:i + 1]))",
                    "pend = (j0 + int(np.argmax(h[j0:i + 1]))) if j0 <= i else i")
_ns = dict(np=np, pd=pd, Pivot=Pivot)
exec(compile(_src, '<ts3 patched zigzag>', 'exec'), _ns)
zigzag = _ns['zigzag']

PARQ = '/home/doom/Public/PROJECT/2026/trader/runs/artifacts-data/l4_h1.parquet'
K, PCT = 6, 0.047          # H1: threshold = max(6*ATR, 4.7% price) — lesson-1 percent-leg floor
EQTOL = 0.25               # x ATR — pool band width / EQH-EQL cluster tolerance
CMPM, CMPK = 14, 2.6       # coil: 14-bar range < 2.6*ATR (~p5-10 of r14/ATR, measured)
NCK = 4.0                  # null coil windows require r14 >= 4.0*ATR (~median)
VTRAV, VEFF = 2.0, 0.6     # void: run travel >= 2*ATR, efficiency >= 0.6
NNULL = 5


def load():
    df = pd.read_parquet(PARQ).sort_values(['symbol', 'ts'])
    return {s: g.reset_index(drop=True) for s, g in df.groupby('symbol')}


def segments(g):
    c, o = g['close'].values, g['open'].values
    j = np.where(np.abs(o[1:] / c[:-1] - 1) > 0.20)[0] + 1
    cuts = [0, *j, len(g)]
    return [(a, b) for a, b in zip(cuts[:-1], cuts[1:]) if b - a >= 300]


def prep(g, a, b):
    d = g.iloc[a:b].reset_index(drop=True)
    atr = wilder_atr(d)
    eff = np.maximum(atr, PCT * d['close'].values / K)
    return d, atr, zigzag(d, K, eff)


def episodes(mask):
    """count False->True transitions and their start indices."""
    m = np.asarray(mask, bool)
    if not len(m): return 0, np.array([], int)
    st = np.nonzero(m & ~np.concatenate(([False], m[:-1])))[0]
    return len(st), st


def race(h, l, c, atr, t0, cap=100, amul=1.0):
    """first-crossing race from close[t0]: +1 up-first, -1 down-first, 0 undecided/tie. (dir, bars)"""
    a = amul * atr[t0]; c0 = c[t0]
    hh, ll = h[t0 + 1:t0 + 1 + cap], l[t0 + 1:t0 + 1 + cap]
    up, dn = np.nonzero(hh >= c0 + a)[0], np.nonzero(ll <= c0 - a)[0]
    iu = up[0] if len(up) else 10**9
    idn = dn[0] if len(dn) else 10**9
    if iu == idn: return 0, -1
    return (1, iu + 1) if iu < idn else (-1, idn + 1)


def null_bars(rng, t0, lo, hi, w=70, excl=3, n=NNULL):
    cand = np.arange(max(lo, t0 - w), min(hi, t0 + w))
    cand = cand[np.abs(cand - t0) > excl]
    if not len(cand): return np.array([], int)
    return rng.choice(cand, size=n, replace=len(cand) < n)


# ---------------- POOLS v2 (lesson 5) ----------------
def build_pools(d, atr, piv, nseg):
    h, l, c = d['high'].values, d['low'].values, d['close'].values
    plist = [(p.idx, p.price, p.side) for p in piv]
    out = []
    for p in piv:
        if p.pending or p.confirm_idx is None or p.idx < 14: continue
        b, P, sd = p.confirm_idx, p.price, p.side
        tol = EQTOL * atr[p.idx]
        eq = sum(1 for i2, pr2, s2 in plist if s2 == sd and i2 < p.idx and abs(pr2 - P) <= tol)
        # historical holds (approach-and-respect episodes since last historical penetration)
        s0 = max(14, p.idx - 250)
        if sd == 'H':
            pre_pen = np.nonzero(h[s0:p.idx] >= P)[0]
            s1 = s0 + pre_pen[-1] + 1 if len(pre_pen) else s0
            hist, _ = episodes(h[s1:p.idx] >= P - tol)
        else:
            pre_pen = np.nonzero(l[s0:p.idx] <= P)[0]
            s1 = s0 + pre_pen[-1] + 1 if len(pre_pen) else s0
            hist, _ = episodes(l[s1:p.idx] <= P + tol)
        # forward life: first penetration = death
        if sd == 'H':
            w = h[b + 1:nseg]; pen = np.nonzero(w >= P)[0]
        else:
            w = l[b + 1:nseg]; pen = np.nonzero(w <= P)[0]
        death = b + 1 + pen[0] if len(pen) else -1
        upto = pen[0] if len(pen) else len(w)
        if death >= 0:
            dtyp = 'sweep' if ((c[death] < P) if sd == 'H' else (c[death] > P)) else 'break'
        else:
            dtyp = 'eos'
        near = (w[:upto] >= P - tol) if sd == 'H' else (w[:upto] <= P + tol)
        ntch, tst = episodes(near)
        # first approach event: close within 3*ATR of level
        cc, aa = c[b + 1:b + 1 + upto], atr[b + 1:b + 1 + upto]
        dist = (P - cc) / aa if sd == 'H' else (cc - P) / aa
        ap = np.nonzero(dist <= 3.0)[0]
        t_app = b + 1 + ap[0] if len(ap) else -1
        d_app = float(dist[ap[0]]) if len(ap) else np.nan
        out.append(dict(pividx=p.idx, birth=b, P=P, side=sd, tol=tol, eq=eq, hist=hist,
                        death=death, dtyp=dtyp, touches=ntch, touch_bars=(b + 1 + tst).tolist(),
                        d_atr=abs(P - c[b]) / atr[b], t_app=t_app, d_app=d_app))
    return out


# ---------------- VOIDS (lesson 16) ----------------
def build_voids(d, atr, nseg):
    o, h, l, c = d['open'].values, d['high'].values, d['low'].values, d['close'].values
    sgn = np.sign(c - o)
    out, i = [], 14
    while i < nseg:
        if sgn[i] == 0: i += 1; continue
        j = i
        while j + 1 < nseg and sgn[j + 1] == sgn[i]: j += 1
        dirn = int(sgn[i])
        trav = (c[j] - o[i]) * dirn
        rng_ = h[i:j + 1].max() - l[i:j + 1].min()
        ok = trav >= VTRAV * atr[j] and (
            (j > i and trav / rng_ >= VEFF) or
            (j == i and (c[i] - o[i]) * dirn >= 0.7 * (h[i] - l[i])))
        if ok:
            lo_, hi_ = (o[i], c[j]) if dirn > 0 else (c[j], o[i])
            nf = 0
            for m in range(max(i, 15), j + 1):
                if m + 1 >= nseg: break
                if dirn > 0 and l[m + 1] > h[m - 1]: nf += 1
                if dirn < 0 and h[m + 1] < l[m - 1]: nf += 1
            out.append(dict(s=i, e=j, dirn=dirn, lo=lo_, hi=hi_,
                            trav_atr=trav / atr[j], nfvg=nf))
        i = j + 1
    return out


def build_fvgs(d, nseg):
    """plain 3-candle gaps; m = middle bar index."""
    h, l = d['high'].values, d['low'].values
    out = []
    for m in range(15, nseg - 1):
        if l[m + 1] > h[m - 1]:
            out.append(dict(m=m, dirn=1, far=h[m - 1], near=l[m + 1], gap=l[m + 1] - h[m - 1]))
        elif h[m + 1] < l[m - 1]:
            out.append(dict(m=m, dirn=-1, far=l[m - 1], near=h[m + 1], gap=l[m - 1] - h[m + 1]))
    return out


# ---------------- PO3 coils (lesson 15) ----------------
def build_coils(d, atr, nseg):
    h, l = d['high'].values, d['low'].values
    hs = pd.Series(h).rolling(CMPM).max().values
    ls = pd.Series(l).rolling(CMPM).min().values
    r14 = hs - ls
    comp = r14 <= CMPK * atr
    comp[:14 + CMPM] = False
    onsets, last = [], -10**9
    for t in range(1, nseg):
        if comp[t] and not comp[t - 1] and t - last >= CMPM:
            onsets.append(dict(t=t, top=hs[t], bot=ls[t])); last = t
    return onsets, comp, r14, hs, ls


def coil_outcome(h, l, c, atr, t, top, bot, nseg, cap=100, kk=12):
    """wait for wick break of an edge, then race: close back inside (rev) vs close beyond edge+1ATR (cont)."""
    end = min(nseg, t + 1 + cap)
    up = np.nonzero(h[t + 1:end] > top)[0]
    dn = np.nonzero(l[t + 1:end] < bot)[0]
    iu = up[0] if len(up) else 10**9
    idn = dn[0] if len(dn) else 10**9
    if iu == idn: return None
    tb = t + 1 + min(iu, idn)
    side = 1 if iu < idn else -1
    edge = top if side > 0 else bot
    a = atr[tb]
    for q in range(tb, min(nseg, tb + kk + 1)):
        if side > 0:
            if c[q] >= edge + a: return dict(tb=tb, side=side, res='cont', lag=q - tb)
            if c[q] <= edge: return dict(tb=tb, side=side, res='rev', lag=q - tb)
        else:
            if c[q] <= edge - a: return dict(tb=tb, side=side, res='cont', lag=q - tb)
            if c[q] >= edge: return dict(tb=tb, side=side, res='rev', lag=q - tb)
    return dict(tb=tb, side=side, res='und', lag=-1)


def crc(sym): return zlib.crc32(sym.encode()) % 2
