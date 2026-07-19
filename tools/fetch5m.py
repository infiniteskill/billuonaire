"""Fetch native 5m NSE candles, 60 trailing days (yfinance max for 5m), into
FileFeed CSV schema at data/long5m/. Reuses trader.tools.fetch.to_filefeed."""
import sys, time
from pathlib import Path
sys.path.insert(0, "/home/doom/Public/PROJECT/2026/trader/app")
from trader.tools.fetch import to_filefeed, CSV_COLUMNS
import yfinance as yf

OUT = Path("/home/doom/Public/PROJECT/2026/trader/data/long5m"); OUT.mkdir(parents=True, exist_ok=True)
src = Path("/home/doom/Public/PROJECT/2026/trader/data/wide")
syms = sorted(p.stem for p in src.glob("*.csv"))
ok = fail = 0
for s in syms:
    out = OUT / f"{s}.csv"
    if out.exists(): continue
    tk = "^NSEI" if s == "NIFTY" else f"{s}.NS"
    try:
        raw = yf.Ticker(tk).history(period="60d", interval="5m", auto_adjust=False)
        df = to_filefeed(raw)
        if len(df) < 500: raise RuntimeError(f"thin: {len(df)} rows")
        df.to_csv(out, index=False)
        ok += 1; print(f"OK {s} {len(df)}", flush=True)
    except Exception as e:
        fail += 1; print(f"FAIL {s}: {e}", flush=True)
    time.sleep(0.6)
print(f"DONE ok={ok} fail={fail} total_csvs={len(list(OUT.glob('*.csv')))}", flush=True)
