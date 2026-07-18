"""RR-aware dry-run: for each seek-destroy signal, SL = just beyond the destroy
extreme (tiny), then how far does it run? win% at R=2/3/5/10, mean max-R, expectancy.
This is the metric that matches 1:10-1:30 trading. Signals: real-breaker,
compression-fade, swing-sweep-reclaim. Holdout temporal + cross-sectional."""
import sys, glob, random, statistics as st
sys.path.insert(0,"/tmp/claude-1000/-home-doom-Public-PROJECT-2026-trader/cafd7565-a8b2-42b9-9d06-48e002e5af54/scratchpad")
from h2hlib import load_tf, DATA
sys.path.insert(0,"/home/doom/Public/PROJECT/2026/trader/app")
from trader.tools.study import atr_series

def rr_outcome(m5, entry_i, dr, sl, atr, horizon=80):
    """entry at close[entry_i]; sl price; returns max-R reached before SL hit
    (R = risk = |entry-sl|). If SL hit at bar k, max-R is whatever peaked before k."""
    e=float(m5[entry_i].close); risk=abs(e-sl)
    if risk<=0 or risk < 0.15*float(atr): risk=0.15*float(atr)  # floor tiny SL at 0.15ATR (realistic)
    maxfav=0.0
    for j in range(entry_i+1, min(entry_i+horizon, len(m5))):
        hi=float(m5[j].high); lo=float(m5[j].low)
        adv = (e-lo) if dr==1 else (hi-e)   # adverse toward SL
        fav = (hi-e) if dr==1 else (e-lo)   # favorable
        maxfav=max(maxfav, fav/risk)
        # SL hit? adverse beyond risk (close-based would be softer; use wick=strict)
        slhit = (lo<=sl) if dr==1 else (hi>=sl)
        if slhit: return maxfav, True
    return maxfav, False

def real_breaker(m5, N=5):
    """Failed break of a swing level = seek-destroy breaker. swing low broken (close
    below) then reclaimed (close back above) within K bars => LONG on reclaim, SL below
    the break extreme. Mirror swing-high."""
    H=[float(c.high) for c in m5]; L=[float(c.low) for c in m5]; C=[float(c.close) for c in m5]; n=len(m5); ev=[]
    for q in range(N,n-N):
        # confirmed swing low at q
        if all(L[q]<L[k] for k in range(q-N,q)) and all(L[q]<=L[k] for k in range(q+1,q+N+1)):
            for i in range(q+N, min(q+N+15,n)):
                if C[i]<L[q]:  # break below
                    lowext=min(L[i-1:i+1])
                    for j in range(i+1,min(i+6,n)):
                        lowext=min(lowext,L[j])
                        if C[j]>L[q]:  # reclaim
                            ev.append((j,1,lowext)); break
                    break
        if all(H[q]>H[k] for k in range(q-N,q)) and all(H[q]>=H[k] for k in range(q+1,q+N+1)):
            for i in range(q+N,min(q+N+15,n)):
                if C[i]>H[q]:
                    hiext=max(H[i-1:i+1])
                    for j in range(i+1,min(i+6,n)):
                        hiext=max(hiext,H[j])
                        if C[j]<H[q]:
                            ev.append((j,-1,hiext)); break
                    break
    return ev

def compress_fade(m5):
    def isc(c):
        r=float(c.high-c.low)
        if r<=0: return False
        b=abs(float(c.close-c.open)); uw=float(c.high-max(c.open,c.close)); lw=float(min(c.open,c.close)-c.low)
        return b<=0.35*r and uw>=0.2*r and lw>=0.2*r
    H=[float(c.high) for c in m5]; L=[float(c.low) for c in m5]; ev=[]
    for i in range(1,len(m5)-1):
        if not isc(m5[i]): continue
        for j in range(i+1,min(i+4,len(m5))):
            if H[j]>H[i]: ev.append((j,-1,H[j])); break   # fade high-break SHORT, SL above break high
            if L[j]<L[i]: ev.append((j,1,L[j])); break
    return ev

SIGS={"real_breaker":real_breaker, "compress_fade":compress_fade}
files=sorted(glob.glob(f"{DATA}/*.csv"))
for mins in (2,5):
    cache={f:load_tf(f,mins) for f in files}
    for name,fn in SIGS.items():
        recs=[]  # (day, sym, maxR, slhit)
        for f in files:
            sym,m5=cache[f]
            if sym=="NIFTY" or len(m5)<30: continue
            atrs=atr_series(m5)
            for tup in fn(m5):
                i,dr,ext = tup
                if i>=len(atrs) or atrs[i] is None: continue
                mr,slhit=rr_outcome(m5,i,dr,ext,atrs[i])
                recs.append((m5[i].ts.date(),sym,mr,slhit))
        def stats(rs):
            if not rs: return "n=0"
            n=len(rs); mr=[r[2] for r in rs]
            w=lambda R: sum(1 for x in mr if x>=R)/n*100
            exp=lambda R: (w(R)/100)*R-(1-w(R)/100)*1   # expectancy R at target R, SL=1R
            return (f"n={n} meanMaxR={st.mean(mr):.1f} medMaxR={st.median(mr):.1f} "
                    f"win@2R={w(2):.0f}% @3R={w(3):.0f}% @5R={w(5):.0f}% @10R={w(10):.0f}% "
                    f"exp@3R={exp(3):+.2f} exp@5R={exp(5):+.2f}")
        days=sorted({r[0] for r in recs}); cut=days[len(days)//2] if days else None
        val=[r for r in recs if cut and r[0]>=cut]
        print(f"M{mins} {name:14s} ALL  {stats(recs)}")
        print(f"        {'':14s} val  {stats(val)}")
    print()
