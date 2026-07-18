"""Faithful LuxAlgo internal Order Block, measured head-to-head vs ours.
Reuses the study's outcome/baseline scoring for apples-to-apples edge."""
import sys, glob, os
from decimal import Decimal
from datetime import datetime
from collections import defaultdict
sys.path.insert(0, "/home/doom/Public/PROJECT/2026/trader/app")
import pandas as pd
from trader.models.candle import Candle, Timeframe
from trader.tools.study import atr_series, outcome, baseline
from trader.config import load_settings
from pathlib import Path

DATA = "/home/doom/Public/PROJECT/2026/trader/data/real"
spec = load_settings(Path("/home/doom/Public/PROJECT/2026/trader/runs/full20/config.json")).market_spec()

def load_m5(path):
    df = pd.read_csv(path)
    df["ts"] = pd.to_datetime(df["ts"], utc=True).dt.tz_convert("Asia/Kolkata")
    sym = os.path.basename(path)[:-4]
    out = []
    for day, g in df.groupby(df.ts.dt.date):
        g = g.sort_values("ts")
        open0 = g.ts.iloc[0]  # 09:15
        buckets = {}
        for _, r in g.iterrows():
            b = int((r.ts - open0).total_seconds() // 300)
            buckets.setdefault(b, []).append(r)
        for b in sorted(buckets):
            rows = buckets[b]
            ts = open0 + pd.Timedelta(minutes=5*b)
            out.append(Candle(sym, Timeframe.M5, ts.to_pydatetime(),
                Decimal(str(rows[0].open)), Decimal(str(max(x.high for x in rows))),
                Decimal(str(min(x.low for x in rows))), Decimal(str(rows[-1].close)),
                int(sum(x.volume for x in rows))))
    return sym, out

def lux_ob_events(m5, atrs, size=5):
    """Return list of (bar_index, direction) OB-retest events, LuxAlgo internal OB."""
    n = len(m5)
    H=[float(c.high) for c in m5]; L=[float(c.low) for c in m5]; C=[float(c.close) for c in m5]
    # volatility-adjusted parsed series
    pH=[0.0]*n; pL=[0.0]*n
    for j in range(n):
        a = atrs[j]
        hv = a is not None and (H[j]-L[j]) >= 2*float(a)
        pH[j] = L[j] if hv else H[j]
        pL[j] = H[j] if hv else L[j]
    # swing pivots via leg(size): pivot at bar (i-size)
    swH=None; swHc=False; swL=None; swLc=False; trend=0  # level,baridx tuples
    swHlvl=swHidx=swLlvl=swLidx=None
    obs=[]  # dict: lo,hi,bias,mitig,touched
    events=[]
    for i in range(n):
        # detect pivot confirmed at bar p=i-size (needs window i-size .. i)
        if i>=size:
            p=i-size
            win_h=max(H[p+1:i+1]); win_l=min(L[p+1:i+1])
            if H[p] > win_h:      # new bearish leg -> swing HIGH at p
                swHlvl=H[p]; swHidx=p; swHc=False
            if L[p] < win_l:      # new bullish leg -> swing LOW at p
                swLlvl=L[p]; swLidx=p; swLc=False
        # structure breaks (crossover close)
        if swHlvl is not None and not swHc and C[i]>swHlvl and (i==0 or C[i-1]<=swHlvl):
            swHc=True; trend=1
            seg=range(swHidx,i+1); idx=min(seg,key=lambda j:pL[j])
            obs.append(dict(lo=pL[idx],hi=pH[idx],bias=1,mitig=False,touched=False,born=i))
        if swLlvl is not None and not swLc and C[i]<swLlvl and (i==0 or C[i-1]>=swLlvl):
            swLc=True; trend=-1
            seg=range(swLidx,i+1); idx=max(seg,key=lambda j:pH[j])
            obs.append(dict(lo=pL[idx],hi=pH[idx],bias=-1,mitig=False,touched=False,born=i))
        # mitigation + retest on THIS bar for existing obs (born before i)
        for ob in obs:
            if ob["mitig"] or ob["born"]>=i: continue
            if ob["bias"]==1 and L[i] < ob["lo"]: ob["mitig"]=True; continue
            if ob["bias"]==-1 and H[i] > ob["hi"]: ob["mitig"]=True; continue
            # retest = candle range overlaps zone, first touch
            if not ob["touched"] and L[i] <= ob["hi"] and H[i] >= ob["lo"]:
                ob["touched"]=True
                events.append((i, ob["bias"]))
    return events

def score(m5, atrs, events):
    hits=[]; bases=[]
    for i,dirn in events:
        if atrs[i] is None: continue
        o = outcome(m5, i, dirn, atrs[i])
        if o["hit"]=="na": continue
        b,_ = baseline(m5, atrs, i, dirn, spec, f"LUXOB|{m5[i].symbol}|{m5[i].ts.isoformat()}")
        if b is None: continue
        hits.append(1.0 if o["hit"]=="hit" else 0.0); bases.append(b)
    import statistics as st
    if not hits: return (0,0,0,0)
    return (len(hits), 100*st.mean(hits), 100*st.mean(bases), 100*(st.mean(hits)-st.mean(bases)))

def score_rows(m5, atrs, events, sym):
    rows=[]
    for i,dirn in events:
        if atrs[i] is None: continue
        o = outcome(m5, i, dirn, atrs[i])
        if o["hit"]=="na": continue
        b,_ = baseline(m5, atrs, i, dirn, spec, f"LUXOB|{sym}|{m5[i].ts.isoformat()}")
        if b is None: continue
        rows.append((m5[i].ts.date(), sym, 1.0 if o["hit"]=="hit" else 0.0, b))
    return rows

def edge(rows):
    if not rows: return (0,0.0)
    import statistics as st
    return (len(rows), 100*(st.mean(r[2] for r in rows)-st.mean(r[3] for r in rows)))

for size in (5, 8):
    allrows=[]
    syms=[]
    for f in sorted(glob.glob(f"{DATA}/*.csv")):
        sym,m5 = load_m5(f)
        if sym=="NIFTY": continue
        syms.append(sym)
        atrs=atr_series(m5)
        allrows += score_rows(m5, atrs, lux_ob_events(m5, atrs, size), sym)
    days=sorted({r[0] for r in allrows})
    cut=days[len(days)//2]
    der=[r for r in allrows if r[0] < cut]; val=[r for r in allrows if r[0] >= cut]
    import random as rnd
    rr=rnd.Random(42); shuf=syms[:]; rr.shuffle(shuf); A=set(shuf[:len(shuf)//2])
    xa=[r for r in allrows if r[1] in A]; xb=[r for r in allrows if r[1] not in A]
    n,e=edge(allrows)
    print(f"LuxAlgo OB size={size}: ALL n={n} edge={e:+.1f}% | temporal der {edge(der)} val {edge(val)} | x-sect A {edge(xa)} B {edge(xb)}")
