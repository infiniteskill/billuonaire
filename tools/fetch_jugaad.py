"""fetch_jugaad.py — pull Kite historical OHLC via jugaad_trader (no paid API;
uses the cached web session) into the trader's FileFeed CSV schema.

Multi-year 1-minute is chunked into <=60-day windows (Kite's minute limit) and
concatenated. Run with the conda base python (has jugaad_trader + a live session).

Usage: python tools/fetch_jugaad.py <from YYYY-MM-DD> <to YYYY-MM-DD> <outdir> <interval> <SYM,SYM,...>
  interval: minute | 3minute | 5minute | 15minute | day
"""
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from jugaad_trader import Zerodha

TOKENS = json.load(open("/home/doom/Public/Research/tick/data.json"))
frm = datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
to = datetime.strptime(sys.argv[2], "%Y-%m-%d").date()
OUT = Path(sys.argv[3]); OUT.mkdir(parents=True, exist_ok=True)
interval = sys.argv[4] if len(sys.argv) > 4 else "minute"
syms = sys.argv[5].split(",")
STEP = 60 if interval == "minute" else (100 if "minute" in interval else 2000)

kite = Zerodha(); kite.set_access_token()


def fetch(sym):
    tok = TOKENS.get(sym)
    if not tok:
        print(f"SKIP {sym}: no token"); return
    out = OUT / f"{sym}.csv"
    if out.exists():
        print(f"SKIP {sym}: exists"); return
    rows, d = [], frm
    while d <= to:
        end = min(d + timedelta(days=STEP - 1), to)
        try:
            rows += kite.historical_data(tok, from_date=d, to_date=end, interval=interval)
        except Exception as e:
            print(f"  chunk fail {sym} {d}..{end}: {e}")
        d = end + timedelta(days=1); time.sleep(0.4)
    if not rows:
        print(f"EMPTY {sym}"); return
    df = pd.DataFrame(rows)
    df = df[df["date"].apply(lambda x: (x.hour*60+x.minute) >= 555 and (x.hour*60+x.minute) <= 929)]  # session-hours filter 09:15-15:29
    df["ts"] = df["date"].apply(lambda x: x.isoformat())
    df[["ts", "open", "high", "low", "close", "volume"]].to_csv(out, index=False)
    print(f"OK {sym} {len(df)} rows  {df['ts'].iloc[0][:10]}..{df['ts'].iloc[-1][:10]}")


for s in syms:
    fetch(s)
print("DONE")
