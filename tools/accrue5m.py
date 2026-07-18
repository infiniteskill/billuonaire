#!/usr/bin/env python
"""Forward-accrual: refresh data/long5m with the trailing 60 days of native 5m
NSE candles (yfinance's max for 5m) and MERGE with existing rows, so the
dataset grows ~20 sessions/month past the rolling window instead of losing
the tail. Run weekly: app/.venv/bin/python tools/accrue5m.py
"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))
from trader.tools.fetch import to_filefeed  # noqa: E402

import pandas as pd  # noqa: E402
import yfinance as yf  # noqa: E402

OUT = ROOT / "data" / "long5m"
OUT.mkdir(parents=True, exist_ok=True)
syms = sorted(p.stem for p in OUT.glob("*.csv")) or ["RELIANCE", "NIFTY"]
ok = fail = 0
for s in syms:
    tk = "^NSEI" if s == "NIFTY" else f"{s}.NS"
    try:
        raw = yf.Ticker(tk).history(period="60d", interval="5m", auto_adjust=False)
        new = to_filefeed(raw)
        if len(new) < 500:
            raise RuntimeError(f"thin: {len(new)} rows")
        f = OUT / f"{s}.csv"
        if f.exists():  # merge: old rows outside the new window survive
            old = pd.read_csv(f, dtype=str)
            new = (pd.concat([old, new.astype(str)])
                   .drop_duplicates("ts", keep="last").sort_values("ts"))
        new.to_csv(f, index=False)
        ok += 1
        print(f"OK {s} -> {len(new)} rows", flush=True)
    except Exception as e:  # one symbol failing must not kill the batch
        fail += 1
        print(f"FAIL {s}: {e}", flush=True)
    time.sleep(0.6)
print(f"DONE ok={ok} fail={fail}")
