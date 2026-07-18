#!/usr/bin/env python
"""Forward-accrual: refresh data/long5m with the trailing 60 days of native 5m
NSE candles (yfinance's max for 5m) and MERGE with existing rows, so the
dataset grows ~20 sessions/month past the rolling window instead of losing
the tail. Run weekly: app/.venv/bin/python tools/accrue5m.py

Prices are RAW (auto_adjust=False) so a merge can never splice
differently-adjusted bases; the flip side is that a real split/bonus is a
genuine discontinuity, so every merged file is splice-checked
(trader.tools.doctor.splices) and hits are shouted -- history is never
silently adjusted. Trim or refetch a flagged file before research.
"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))
from trader.tools.doctor import splices  # noqa: E402
from trader.tools.fetch import to_filefeed  # noqa: E402

import pandas as pd  # noqa: E402
import yfinance as yf  # noqa: E402

OUT = ROOT / "data" / "long5m"


def main(out: Path = OUT, pause: float = 0.6) -> int:
    out.mkdir(parents=True, exist_ok=True)
    syms = sorted(p.stem for p in out.glob("*.csv")) or ["RELIANCE", "NIFTY"]
    ok = fail = 0
    for s in syms:
        tk = "^NSEI" if s == "NIFTY" else f"{s}.NS"
        try:
            raw = yf.Ticker(tk).history(period="60d", interval="5m", auto_adjust=False)
            new = to_filefeed(raw)
            if len(new) < 500:
                raise RuntimeError(f"thin: {len(new)} rows")
            f = out / f"{s}.csv"
            if f.exists():  # merge: old rows outside the new window survive
                old = pd.read_csv(f, dtype=str)
                new = (pd.concat([old, new.astype(str)])
                       .drop_duplicates("ts", keep="last").sort_values("ts")
                       .reset_index(drop=True))
            new.to_csv(f, index=False)
            ok += 1
            print(f"OK {s} -> {len(new)} rows", flush=True)
            for ts, pct in splices(new):
                print(f"SPLICE WARNING {s} @ {ts}: close->open jump {pct}% -- "
                      "probable split/bonus; research across this boundary is "
                      "invalid (history NOT auto-adjusted)", flush=True)
        except Exception as e:  # one symbol failing must not kill the batch
            fail += 1
            print(f"FAIL {s}: {e}", flush=True)
        time.sleep(pause)
    print(f"DONE ok={ok} fail={fail}")
    return fail


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
