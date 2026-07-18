"""Liquidity/hunt pattern measurement: judas swing, OR-sweep, turtle soup, gap
fill/trap, round-number sweep-reclaim, draw-on-liquidity. Reuses h2hlib (load,
outcome/baseline edge scoring, temporal+cross-sectional holdout) + rr.rr_outcome
(RR-aware expectancy). detect_fn(m5,atrs,mins) -> [(bar,dir,sl)]."""
import sys, glob, random, statistics as st
SP = "/tmp/claude-1000/-home-doom-Public-PROJECT-2026-trader/cafd7565-a8b2-42b9-9d06-48e002e5af54/scratchpad"
sys.path.insert(0, SP)
from h2hlib import load_tf, DATA, SPEC
from rr import rr_outcome
sys.path.insert(0, "/home/doom/Public/PROJECT/2026/trader/app")
from trader.tools.study import atr_series, outcome, baseline

def day_idx(m5):
    d = [c.ts.date() for c in m5]; out = []; s = 0
    for i in range(1, len(d) + 1):
        if i == len(d) or d[i] != d[i - 1]: out.append((s, i)); s = i
    return out

def pivots(m5, N=3):
    H = [float(c.high) for c in m5]; L = [float(c.low) for c in m5]; hi = []; lo = []
    for q in range(N, len(m5) - N):
        if all(H[q] > H[k] for k in range(q - N, q)) and all(H[q] >= H[k] for k in range(q + 1, q + N + 1)): hi.append(q)
        if all(L[q] < L[k] for k in range(q - N, q)) and all(L[q] <= L[k] for k in range(q + 1, q + N + 1)): lo.append(q)
    return hi, lo

# 1. Judas swing: morning (first ~90min) sweep of OR(15min) hi/lo then reclaim -> reversal
def judas(m5, atrs, mins):
    ORb = max(1, 15 // mins); MOb = max(ORb + 1, 90 // mins)
    H = [float(c.high) for c in m5]; L = [float(c.low) for c in m5]; C = [float(c.close) for c in m5]
    ev = []
    for s, e in day_idx(m5):
        if e - s <= ORb: continue
        orhi, orlo = max(H[s:s + ORb]), min(L[s:s + ORb])
        end = min(e, s + MOb)
        for i in range(s + ORb, end):
            if L[i] < orlo:
                ext = L[i]
                for j in range(i + 1, min(i + 6, end)):
                    ext = min(ext, L[j])
                    if C[j] > orlo: ev.append((j, 1, ext)); break
            elif H[i] > orhi:
                ext = H[i]
                for j in range(i + 1, min(i + 6, end)):
                    ext = max(ext, H[j])
                    if C[j] < orhi: ev.append((j, -1, ext)); break
    return ev

# 2. Opening-range sweep: OR hi/lo swept LATER (after morning window) then reclaimed
def or_sweep(m5, atrs, mins):
    ORb = max(1, 15 // mins); MOb = max(ORb + 1, 90 // mins)
    H = [float(c.high) for c in m5]; L = [float(c.low) for c in m5]; C = [float(c.close) for c in m5]
    ev = []
    for s, e in day_idx(m5):
        if e - s <= ORb: continue
        orhi, orlo = max(H[s:s + ORb]), min(L[s:s + ORb])
        for i in range(max(s + ORb, s + MOb), e):
            if L[i] < orlo:
                ext = L[i]
                for j in range(i + 1, min(i + 6, e)):
                    ext = min(ext, L[j])
                    if C[j] > orlo: ev.append((j, 1, ext)); break
            elif H[i] > orhi:
                ext = H[i]
                for j in range(i + 1, min(i + 6, e)):
                    ext = max(ext, H[j])
                    if C[j] < orhi: ev.append((j, -1, ext)); break
    return ev

# 3. Turtle soup: new N-bar high/low that closes back inside (failed breakout) -> fade
def turtle_soup(m5, atrs, mins, N=20):
    H = [float(c.high) for c in m5]; L = [float(c.low) for c in m5]; C = [float(c.close) for c in m5]
    ev = []
    for i in range(N, len(m5)):
        if L[i] < min(L[i - N:i]) and C[i] > L[i - N]: ev.append((i, 1, L[i]))
        elif H[i] > max(H[i - N:i]) and C[i] < H[i - N]: ev.append((i, -1, H[i]))
    return ev

# 4. Gap fill/trap: session open gap vs prev close; fade the gap
def gap_fill(m5, atrs, mins):
    C = [float(c.close) for c in m5]; O = [float(c.open) for c in m5]
    days = day_idx(m5); ev = []
    for k in range(1, len(days)):
        s, e = days[k]; _, pe = days[k - 1]
        a = atrs[s]
        if a is None: continue
        gap = O[s] - C[pe - 1]
        if abs(gap) < 0.15 * float(a): continue
        dr = -1 if gap > 0 else 1
        ev.append((s, dr, O[s] - dr * 0.5 * float(a)))
    return ev

# 5. Round-number sweep-reclaim: nearest round (step) level pierced then reclaimed
def round_sweep(m5, atrs, mins, step=50):
    H = [float(c.high) for c in m5]; L = [float(c.low) for c in m5]; C = [float(c.close) for c in m5]
    ev = []
    for i in range(1, len(m5)):
        pc = C[i - 1]; R = round(pc / step) * step
        if R <= 0: continue
        if pc >= R and L[i] < R and C[i] > R: ev.append((i, 1, L[i]))
        elif pc < R and H[i] > R and C[i] < R: ev.append((i, -1, H[i]))
    return ev

# 6. Draw-on-liquidity: nearest untapped swing hi/lo cluster -> directional pull
def draw_events(m5, atrs, N=3, away=False):
    H = [float(c.high) for c in m5]; L = [float(c.low) for c in m5]; C = [float(c.close) for c in m5]
    hi_piv, lo_piv = pivots(m5, N); ev = []
    for s, e in day_idx(m5):
        his = sorted(q for q in hi_piv if s <= q < e); los = sorted(q for q in lo_piv if s <= q < e)
        act_hi = []; act_lo = []; hp = lp = 0
        for i in range(s, e):
            while hp < len(his) and his[hp] + N <= i: act_hi.append(H[his[hp]]); hp += 1
            while lp < len(los) and los[lp] + N <= i: act_lo.append(L[los[lp]]); lp += 1
            ups = [v for v in act_hi if v > C[i]]; dns = [v for v in act_lo if v < C[i]]
            a = atrs[i]
            if ups and dns and a is not None:
                near = 1 if (min(ups) - C[i]) < (C[i] - max(dns)) else -1
                sig = near if not away else -near
                sl = C[i] - 0.5 * float(a) if sig == 1 else C[i] + 0.5 * float(a)
                ev.append((i, sig, sl))
            act_hi = [v for v in act_hi if H[i] < v]; act_lo = [v for v in act_lo if L[i] > v]
    return ev

draw_toward = lambda m5, atrs, mins: draw_events(m5, atrs, away=False)
draw_away = lambda m5, atrs, mins: draw_events(m5, atrs, away=True)

def edge(rows):
    return (len(rows), round(100 * (st.mean(r[2] for r in rows) - st.mean(r[3] for r in rows)), 1)) if rows else (0, 0.0)

def rrstats(rows):
    if not rows: return "n=0"
    n = len(rows); mr = [r[2] for r in rows]
    w = lambda R: sum(1 for x in mr if x >= R) / n * 100
    exp = lambda R: (w(R) / 100) * R - (1 - w(R) / 100) * 1
    return f"n={n} win@3R={w(3):.0f}% win@10R={w(10):.0f}% exp@3R={exp(3):+.2f}"

def report2(name, detect_fn, tfs=(5, 10)):
    files = sorted(glob.glob(f"{DATA}/*.csv"))
    for mins in tfs:
        erows = []; rrows = []; syms = []
        for f in files:
            sym, m5 = load_tf(f, mins)
            if sym == "NIFTY" or len(m5) < 20: continue
            syms.append(sym); atrs = atr_series(m5)
            for i, dr, sl in detect_fn(m5, atrs, mins):
                if i >= len(atrs) or atrs[i] is None or dr == 0: continue
                o = outcome(m5, i, dr, atrs[i])
                if o["hit"] != "na":
                    b, _ = baseline(m5, atrs, i, dr, SPEC, f"{name}|{sym}|{m5[i].ts.isoformat()}")
                    if b is not None:
                        erows.append((m5[i].ts.date(), sym, 1.0 if o["hit"] == "hit" else 0.0, b))
                mr, slhit = rr_outcome(m5, i, dr, sl, atrs[i])
                rrows.append((m5[i].ts.date(), sym, mr, slhit))
        edays = sorted({r[0] for r in erows}); ecut = edays[len(edays) // 2] if edays else None
        eval_ = [r for r in erows if ecut and r[0] >= ecut]
        rrand = random.Random(42); sh = syms[:]; rrand.shuffle(sh); A = set(sh[:len(sh) // 2])
        exb = [r for r in erows if r[1] not in A]
        rdays = sorted({r[0] for r in rrows}); rcut = rdays[len(rdays) // 2] if rdays else None
        rval = [r for r in rrows if rcut and r[0] >= rcut]
        rxb = [r for r in rrows if r[1] not in A]
        print(f"M{mins:<2d} {name:14s} edge ALL{edge(erows)} val{edge(eval_)} xB{edge(exb)}")
        print(f"        {'':14s} RR   ALL[{rrstats(rrows)}]")
        print(f"        {'':14s}      val[{rrstats(rval)}] xB[{rrstats(rxb)}]")

if __name__ == "__main__":
    report2("judas", judas)
    report2("or_sweep", or_sweep)
    report2("turtle_soup", turtle_soup)
    report2("gap_fill", gap_fill)
    report2("round_sweep", round_sweep)
    report2("draw_toward", draw_toward)
    report2("draw_away", draw_away)
