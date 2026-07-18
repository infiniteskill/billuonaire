"""Isolate + measure 5 untested ICT structure aspects as standalone
detector_fns -> [(bar, direction, sl)]. Gap creation mirrors production
trader/detectors/fvg.py exactly (3-candle gap, zone=(c1.high,c3.low) bull /
(c3.high,c1.low) bear, gap>=0.3*ATR). iFVG/BPR/CE here are SIMPLIFIED
standalone versions (single-touch, no full LevelEngine SWEPT->RECLAIMED
chain) since that chain is the dead path that never fires in production.

Edge = hit-vs-baseline via h2hlib.report (study.outcome/baseline, temporal +
cross-sectional holdout). RR = win@R/expectancy via rr_outcome (copied from
rr.py to avoid its top-level script running on import), same holdout split.
"""
import sys, glob, random, statistics as st
SCRATCH = "/tmp/claude-1000/-home-doom-Public-PROJECT-2026-trader/cafd7565-a8b2-42b9-9d06-48e002e5af54/scratchpad"
sys.path.insert(0, SCRATCH)
from h2hlib import load_tf, DATA, report
sys.path.insert(0, "/home/doom/Public/PROJECT/2026/trader/app")
from trader.tools.study import atr_series

def rr_outcome(m5, entry_i, dr, sl, atr, horizon=80):
    e = float(m5[entry_i].close); risk = abs(e - sl)
    if risk <= 0 or risk < 0.15 * float(atr): risk = 0.15 * float(atr)
    maxfav = 0.0
    for j in range(entry_i + 1, min(entry_i + horizon, len(m5))):
        hi, lo = float(m5[j].high), float(m5[j].low)
        fav = (hi - e) if dr == 1 else (e - lo)
        maxfav = max(maxfav, fav / risk)
        if (lo <= sl) if dr == 1 else (hi >= sl): return maxfav, True
    return maxfav, False

def find_gaps(m5, atrs):
    """[(born, lo, hi, dr)] dr=1 bull (gap up) / -1 bear (gap down)."""
    H = [float(c.high) for c in m5]; L = [float(c.low) for c in m5]; z = []
    for i in range(2, len(m5)):
        a = atrs[i]
        if a is None: continue
        need = 0.3 * float(a)
        if L[i] > H[i - 2] and (L[i] - H[i - 2]) >= need: z.append((i - 1, H[i - 2], L[i], 1))
        if H[i] < L[i - 2] and (L[i - 2] - H[i]) >= need: z.append((i - 1, H[i], L[i - 2], -1))
    return z

def _arrs(m5):
    return ([float(c.open) for c in m5], [float(c.high) for c in m5],
             [float(c.low) for c in m5], [float(c.close) for c in m5])

# ---------------------------------------------------------------- 1. iFVG
def ifvg(m5, atrs):
    """Gap fully filled (close beyond far edge) then first retest into the
    zone that REJECTS (closes back on the new/filled side) => flip entry."""
    _, H, L, C = _arrs(m5); ev = []
    for born, lo, hi, dr in find_gaps(m5, atrs):
        filled = next((j for j in range(born + 1, len(m5))
                       if (C[j] < lo if dr == 1 else C[j] > hi)), None)
        if filled is None: continue
        for k in range(filled + 1, len(m5)):
            if not (L[k] <= hi and H[k] >= lo): continue
            if (C[k] < lo) if dr == 1 else (C[k] > hi):
                ev.append((k, -dr, H[k] if dr == 1 else L[k]))
            break
    return ev

# ---------------------------------------------------------------- 2. BPR
def bpr(m5, atrs):
    """Overlap of a live bull FVG x bear FVG; first close back inside the
    overlap => direction of the newer (later-born) gap."""
    _, H, L, C = _arrs(m5)
    gaps = find_gaps(m5, atrs)
    bulls = [g for g in gaps if g[3] == 1]; bears = [g for g in gaps if g[3] == -1]
    die = {}
    for g in gaps:
        born, lo, hi, dr = g
        die[g] = next((j for j in range(born + 1, len(m5))
                       if (C[j] < lo if dr == 1 else C[j] > hi)), len(m5))
    ev = []
    for bb in bulls:
        for br in bears:
            lo = max(bb[1], br[1]); hi = min(bb[2], br[2])
            if lo > hi: continue
            start = max(bb[0], br[0]) + 1; end = min(die[bb], die[br])
            newer_dr = 1 if bb[0] > br[0] else -1
            for k in range(start, end):
                if L[k] <= hi and H[k] >= lo and lo <= C[k] <= hi:
                    ev.append((k, newer_dr, lo if newer_dr == 1 else hi))
                    break
    return ev

# ---------------------------------------------------------------- 3. CE reject
def ce_reject(m5, atrs):
    """First touch of the gap's 50% CE that REJECTS (wick through CE, close
    back on the gap side) -- distinct from CE_HOLD (no wick required)."""
    _, H, L, C = _arrs(m5); ev = []
    for born, lo, hi, dr in find_gaps(m5, atrs):
        ce = (lo + hi) / 2
        for j in range(born + 1, len(m5)):
            if (C[j] < lo) if dr == 1 else (C[j] > hi): break  # died first
            if not (L[j] <= ce <= H[j]): continue
            if (C[j] > ce) if dr == 1 else (C[j] < ce):
                ev.append((j, dr, L[j] if dr == 1 else H[j]))
            break
    return ev

# ---------------------------------------------------------------- 4. Mitigation block
def mitigation_block(m5, atrs, disp_atr=1.0, lookback=3):
    """Last opposite-color candle immediately before a displacement (no
    intervening opposite candle in the lookback window) -> BODY-only zone
    (differs from OB's full-range zone); first return-touch = entry, dir =
    the displacement direction."""
    O, H, L, C = _arrs(m5); ev = []
    for sign in (1, -1):  # 1: down-candle before up-move (LONG)
        for i in range(1, len(m5) - lookback):
            down = C[i] < O[i] if sign == 1 else C[i] > O[i]
            if not down: continue
            seg = range(i + 1, i + 1 + lookback)
            if any((C[j] < O[j]) if sign == 1 else (C[j] > O[j]) for j in seg): continue
            a = atrs[i]
            if a is None: continue
            disp = max((C[j] - C[i]) * sign for j in seg)
            if disp < disp_atr * float(a): continue
            lo, hi = min(O[i], C[i]), max(O[i], C[i])
            for k in range(i + 1 + lookback, len(m5)):
                if L[k] <= hi and H[k] >= lo:
                    sl = min(L[i], L[k]) if sign == 1 else max(H[i], H[k])
                    ev.append((k, sign, sl)); break
    return ev

# ---------------------------------------------------------------- 5. Rejection/vacuum block
def rejection_block(m5, atrs, wick_frac=0.55, body_frac=0.35):
    """Candle with a dominant wick (rejection) and range>=0.5ATR; first
    retest of the candle's range -> direction = rejection direction."""
    O, H, L, C = _arrs(m5); ev = []
    for i in range(1, len(m5) - 1):
        a = atrs[i]
        if a is None: continue
        rng = H[i] - L[i]
        if rng <= 0 or rng < 0.5 * float(a): continue
        body = abs(C[i] - O[i])
        if body > body_frac * rng: continue
        uw = H[i] - max(O[i], C[i]); lw = min(O[i], C[i]) - L[i]
        if lw >= wick_frac * rng and lw > uw: dr = 1
        elif uw >= wick_frac * rng and uw > lw: dr = -1
        else: continue
        lo, hi = L[i], H[i]
        for k in range(i + 1, len(m5)):
            if L[k] <= hi and H[k] >= lo:
                ev.append((k, dr, L[i] if dr == 1 else H[i])); break
    return ev

DETS = {"iFVG": ifvg, "BPR": bpr, "CE_reject": ce_reject,
        "mitig_block": mitigation_block, "rejection_block": rejection_block}

# =============================================================== EDGE (hit vs baseline)
print("=== EDGE (n, edge%) : hit-rate minus same-bucket baseline ===")
for name, fn in DETS.items():
    report(name, lambda m5, atrs, fn=fn: [(i, d) for i, d, *_ in fn(m5, atrs)], tfs=(5, 10))

# =============================================================== RR (win@R, expectancy)
print("\n=== RR : win@R / expectancy(R=1 stop) ===")
def rrstats(rs):
    if not rs: return "n=0"
    n = len(rs); mr = [r[2] for r in rs]
    w = lambda R: sum(1 for x in mr if x >= R) / n * 100
    exp = lambda R: (w(R) / 100) * R - (1 - w(R) / 100) * 1
    return (f"n={n}{'*' if n < 50 else ' '} win@3R={w(3):.0f}% win@10R={w(10):.0f}% "
            f"exp@3R={exp(3):+.2f} exp@5R={exp(5):+.2f}")

files = sorted(glob.glob(f"{DATA}/*.csv"))
for mins in (5, 10):
    cache = {f: load_tf(f, mins) for f in files}
    for name, fn in DETS.items():
        recs = []; syms = []
        for f in files:
            sym, m5 = cache[f]
            if sym == "NIFTY" or len(m5) < 20: continue
            syms.append(sym); atrs = atr_series(m5)
            for i, dr, sl in fn(m5, atrs):
                if i >= len(atrs) or atrs[i] is None: continue
                mr, slhit = rr_outcome(m5, i, dr, sl, atrs[i])
                recs.append((m5[i].ts.date(), sym, mr, slhit))
        days = sorted({r[0] for r in recs}); cut = days[len(days) // 2] if days else None
        val = [r for r in recs if cut and r[0] >= cut]
        rr = random.Random(42); sh = syms[:]; rr.shuffle(sh); A = set(sh[:len(sh) // 2])
        xb = [r for r in recs if r[1] not in A]
        print(f"M{mins:<2d} {name:14s} ALL {rrstats(recs)}")
        print(f"        {'':14s} val {rrstats(val)}")
        print(f"        {'':14s} x-B {rrstats(xb)}")
