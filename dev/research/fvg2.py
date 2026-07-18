"""Head-to-head: dedicated LuxAlgo FVG (close-beyond + auto mean-range% threshold)
vs ours (0.3xATR gap), across M5/M10/M15, with BOTH retest and CE-hold events."""
import sys, glob, os, random, statistics as st
from decimal import Decimal
sys.path.insert(0, "/home/doom/Public/PROJECT/2026/trader/app")
import pandas as pd
from trader.models.candle import Candle, Timeframe
from trader.tools.study import atr_series, outcome, baseline
from trader.config import load_settings
from pathlib import Path
DATA="/home/doom/Public/PROJECT/2026/trader/data/real"
spec=load_settings(Path("/home/doom/Public/PROJECT/2026/trader/runs/full20/config.json")).market_spec()

def load_tf(path,mins):
    df=pd.read_csv(path); df["ts"]=pd.to_datetime(df["ts"],utc=True).dt.tz_convert("Asia/Kolkata")
    sym=os.path.basename(path)[:-4]; out=[]; sec=mins*60
    for _,g in df.groupby(df.ts.dt.date):
        g=g.sort_values("ts"); o0=g.ts.iloc[0]; bk={}
        for _,r in g.iterrows(): bk.setdefault(int((r.ts-o0).total_seconds()//sec),[]).append(r)
        for b in sorted(bk):
            rs=bk[b]; ts=o0+pd.Timedelta(minutes=mins*b)
            out.append(Candle(sym,Timeframe.M5,ts.to_pydatetime(),Decimal(str(rs[0].open)),
                Decimal(str(max(x.high for x in rs))),Decimal(str(min(x.low for x in rs))),
                Decimal(str(rs[-1].close)),int(sum(x.volume for x in rs))))
    return sym,out

def gaps(m5,atrs,mode):
    H=[float(c.high) for c in m5]; L=[float(c.low) for c in m5]; C=[float(c.close) for c in m5]
    cum=0.0; z=[]
    for i in range(2,len(m5)):
        a=atrs[i]; cum+=(H[i]-L[i])/L[i] if L[i] else 0; thr=cum/(i+1)  # mean bar range %
        if a is None: continue
        if mode=="ours":
            if L[i]>H[i-2] and (L[i]-H[i-2])>=0.3*float(a): z.append((i,H[i-2],L[i],1))
            if H[i]<L[i-2] and (L[i-2]-H[i])>=0.3*float(a): z.append((i,H[i],L[i-2],-1))
        else:  # lux dedicated: gap + close[1] beyond origin + gap%>auto-thr
            if L[i]>H[i-2] and C[i-1]>H[i-2] and (L[i]-H[i-2])/H[i-2]>thr: z.append((i,H[i-2],L[i],1))
            if H[i]<L[i-2] and C[i-1]<L[i-2] and (L[i-2]-H[i])/H[i]>thr: z.append((i,H[i],L[i-2],-1))
    return z

def retest(m5,z):
    H=[float(c.high) for c in m5]; L=[float(c.low) for c in m5]; ev=[]
    for born,lo,hi,dr in z:
        for j in range(born+1,len(m5)):
            if dr==1 and L[j]<lo: break
            if dr==-1 and H[j]>hi: break
            if L[j]<=hi and H[j]>=lo: ev.append((j,dr)); break
    return ev

def cehold(m5,z):
    """close inside gap holding the CE (mid) on the gap side — our +8.8% event."""
    L=[float(c.low) for c in m5]; H=[float(c.high) for c in m5]; C=[float(c.close) for c in m5]; ev=[]
    for born,lo,hi,dr in z:
        mid=(lo+hi)/2
        for j in range(born+1,len(m5)):
            if dr==1 and C[j]<lo: break
            if dr==-1 and C[j]>hi: break
            if lo<=C[j]<=hi and ((dr==1 and C[j]>=mid) or (dr==-1 and C[j]<=mid)):
                ev.append((j,dr)); break
    return ev

def score(m5,atrs,ev,tag):
    rows=[]
    for i,dr in ev:
        if atrs[i] is None: continue
        o=outcome(m5,i,dr,atrs[i])
        if o["hit"]=="na": continue
        b,_=baseline(m5,atrs,i,dr,spec,f"{tag}|{m5[i].symbol}|{m5[i].ts.isoformat()}")
        if b is None: continue
        rows.append((m5[i].ts.date(),m5[i].symbol,1.0 if o["hit"]=="hit" else 0.0,b))
    return rows
def ed(rows): return (len(rows),round(100*(st.mean(r[2] for r in rows)-st.mean(r[3] for r in rows)),1)) if rows else (0,0.0)

for mins in (5,10,15):
    files=sorted(glob.glob(f"{DATA}/*.csv")); cache={f:load_tf(f,mins) for f in files}
    for mode in ("ours","luxded"):
        for evname,evfn in (("retest",retest),("cehold",cehold)):
            allrows=[]; syms=[]
            for f in files:
                sym,m5=cache[f]
                if sym=="NIFTY" or len(m5)<20: continue
                syms.append(sym); atrs=atr_series(m5)
                allrows+=score(m5,atrs,evfn(m5,gaps(m5,atrs,mode)),f"{mode}{evname}")
            days=sorted({r[0] for r in allrows}); cut=days[len(days)//2] if days else None
            val=[r for r in allrows if cut and r[0]>=cut]
            rr=random.Random(42); sh=syms[:]; rr.shuffle(sh); A=set(sh[:len(sh)//2]); xb=[r for r in allrows if r[1] not in A]
            print(f"M{mins:<2d} FVG {mode:7s} {evname:6s} ALL {ed(allrows)} val {ed(val)} x-B {ed(xb)}")
    print()
