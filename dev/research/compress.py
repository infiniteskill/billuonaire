"""Compression candle (close near open + 2-sided wicks = coiled energy) as a
timing signal; break-of-compression as entry; filtered by HTF direction (sniper)."""
import sys, glob, os, random, statistics as st
from decimal import Decimal
sys.path.insert(0,"/home/doom/Public/PROJECT/2026/trader/dev")  # dummy
sys.path.insert(0,"/tmp/claude-1000/-home-doom-Public-PROJECT-2026-trader/cafd7565-a8b2-42b9-9d06-48e002e5af54/scratchpad")
from h2hlib import load_tf, DATA, SPEC
sys.path.insert(0,"/home/doom/Public/PROJECT/2026/trader/app")
from trader.tools.study import atr_series, outcome, baseline

def is_compress(c):
    rng=float(c.high-c.low)
    if rng<=0: return False
    body=abs(float(c.close-c.open)); uw=float(c.high-max(c.open,c.close)); lw=float(min(c.open,c.close)-c.low)
    return body<=0.35*rng and uw>=0.2*rng and lw>=0.2*rng

def events(m5, atrs, htf_filter=False):
    """After a compression candle, next bar breaking its high=LONG / low=SHORT.
    htf_filter: only take breaks aligned with the 12-bar drift direction."""
    H=[float(c.high) for c in m5]; L=[float(c.low) for c in m5]; C=[float(c.close) for c in m5]; ev=[]
    for i in range(1,len(m5)-1):
        if not is_compress(m5[i]): continue
        hi,lo=H[i],L[i]
        for j in range(i+1,min(i+4,len(m5))):   # break within 3 bars
            drift = C[j-1]-C[max(0,j-13)] if j>=1 else 0
            if H[j]>hi:
                if not htf_filter or drift>0: ev.append((j,1))
                break
            if L[j]<lo:
                if not htf_filter or drift<0: ev.append((j,-1))
                break
    return ev

def expansion_test(m5, atrs):
    """Non-directional: is the 6-bar range after a compression candle bigger than
    a random bar's, in ATR units? Returns (n, mean_ratio_compress, mean_ratio_rand)."""
    rc=[]; rr=[]
    for i in range(len(m5)-6):
        a=atrs[i]
        if a is None: continue
        rng=(max(float(c.high) for c in m5[i+1:i+7])-min(float(c.low) for c in m5[i+1:i+7]))/float(a)
        (rc if is_compress(m5[i]) else rr).append(rng)
    return (len(rc), round(st.mean(rc),2) if rc else 0, round(st.mean(rr),2) if rr else 0)

def score(m5,atrs,ev,tag):
    out=[]
    for i,dr in ev:
        if atrs[i] is None: continue
        o=outcome(m5,i,dr,atrs[i])
        if o["hit"]=="na": continue
        b,_=baseline(m5,atrs,i,dr,SPEC,f"{tag}|{m5[i].symbol}|{m5[i].ts.isoformat()}")
        if b is None: continue
        out.append((m5[i].ts.date(),m5[i].symbol,1.0 if o["hit"]=="hit" else 0.0,b))
    return out
def ed(r): return (len(r),round(100*(st.mean(x[2] for x in r)-st.mean(x[3] for x in r)),1)) if r else (0,0.0)

files=sorted(glob.glob(f"{DATA}/*.csv"))
for mins in (5,10,15):
    cache={f:load_tf(f,mins) for f in files}
    # expansion
    exc=0; ec=[]; er=[]
    for f in files:
        sym,m5=cache[f]
        if sym=="NIFTY": continue
        atrs=atr_series(m5); n,mc,mr=expansion_test(m5,atrs)
        if n: ec.append(mc); er.append(mr); exc+=n
    print(f"M{mins} EXPANSION: after-compress 6-bar range {round(st.mean(ec),2)}xATR vs random {round(st.mean(er),2)}xATR (n_compress~{exc})")
    for filt,name in ((False,"compress_break"),(True,"compress_break+HTFdir")):
        allrows=[]; syms=[]
        for f in files:
            sym,m5=cache[f]
            if sym=="NIFTY": continue
            syms.append(sym); atrs=atr_series(m5)
            allrows+=score(m5,atrs,events(m5,atrs,filt),name)
        days=sorted({r[0] for r in allrows}); cut=days[len(days)//2] if days else None
        val=[r for r in allrows if cut and r[0]>=cut]
        rr=random.Random(42); sh=syms[:]; rr.shuffle(sh); A=set(sh[:len(sh)//2]); xb=[r for r in allrows if r[1] not in A]
        print(f"   {name:22s} ALL {ed(allrows)} val {ed(val)} x-B {ed(xb)}")
    print()
