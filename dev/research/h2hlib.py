"""Shared head-to-head measurement lib. Import this; write a detector fn that
returns events [(bar_index, direction)]; call report(name, detector_fn).
Guarantees identical methodology across all concept tests:
 - M1 CSV -> N-min session-anchored bars (multi-TF via TF list)
 - study.outcome/baseline scoring (hit = MFE>=1ATR before MAE>=1ATR vs random
   same-session same-30min-bucket baseline)
 - holdout: temporal (validate days) + cross-sectional (unseen stock-set B)
"""
import sys, glob, os, random, statistics as st
from decimal import Decimal
sys.path.insert(0, "/home/doom/Public/PROJECT/2026/trader/app")
import pandas as pd
from trader.models.candle import Candle, Timeframe
from trader.tools.study import atr_series, outcome, baseline
from trader.config import load_settings
from pathlib import Path

DATA = "/home/doom/Public/PROJECT/2026/trader/data/real"
SPEC = load_settings(Path("/home/doom/Public/PROJECT/2026/trader/runs/full20/config.json")).market_spec()

def load_tf(path, mins):
    df = pd.read_csv(path); df["ts"] = pd.to_datetime(df["ts"], utc=True).dt.tz_convert("Asia/Kolkata")
    sym = os.path.basename(path)[:-4]; out=[]; sec=mins*60
    for _, g in df.groupby(df.ts.dt.date):
        g=g.sort_values("ts"); o0=g.ts.iloc[0]; bk={}
        for _, r in g.iterrows(): bk.setdefault(int((r.ts-o0).total_seconds()//sec),[]).append(r)
        for b in sorted(bk):
            rs=bk[b]; ts=o0+pd.Timedelta(minutes=mins*b)
            out.append(Candle(sym,Timeframe.M5,ts.to_pydatetime(),Decimal(str(rs[0].open)),
                Decimal(str(max(x.high for x in rs))),Decimal(str(min(x.low for x in rs))),
                Decimal(str(rs[-1].close)),int(sum(x.volume for x in rs))))
    return sym,out

def _rows(m5, atrs, events, tag):
    out=[]
    for i,dr in events:
        if i>=len(atrs) or atrs[i] is None or dr==0: continue
        o=outcome(m5,i,dr,atrs[i])
        if o["hit"]=="na": continue
        b,_=baseline(m5,atrs,i,dr,SPEC,f"{tag}|{m5[i].symbol}|{m5[i].ts.isoformat()}")
        if b is None: continue
        out.append((m5[i].ts.date(), m5[i].symbol, 1.0 if o["hit"]=="hit" else 0.0, b))
    return out

def _edge(rows):
    return (len(rows), round(100*(st.mean(r[2] for r in rows)-st.mean(r[3] for r in rows)),1)) if rows else (0,0.0)

def report(name, detector_fn, tfs=(5,10,15), skip_index=True):
    """detector_fn(m5:list[Candle], atrs:list) -> [(bar_index, direction)]"""
    files=sorted(glob.glob(f"{DATA}/*.csv"))
    for mins in tfs:
        allrows=[]; syms=[]
        for f in files:
            sym,m5=load_tf(f,mins)
            if skip_index and sym=="NIFTY": continue
            if len(m5)<20: continue
            syms.append(sym); atrs=atr_series(m5)
            allrows+=_rows(m5,atrs,detector_fn(m5,atrs),name)
        days=sorted({r[0] for r in allrows}); cut=days[len(days)//2] if days else None
        val=[r for r in allrows if cut and r[0]>=cut]
        rr=random.Random(42); sh=syms[:]; rr.shuffle(sh); A=set(sh[:len(sh)//2])
        xb=[r for r in allrows if r[1] not in A]
        print(f"M{mins:<2d} {name:28s} ALL {_edge(allrows)}  val {_edge(val)}  x-B {_edge(xb)}")
