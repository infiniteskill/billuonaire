"""derive_parallel.py — shard derive_tradebook across cores by STOCK, then merge.

The serial derive is single-threaded (one Orchestrator over all 40 stocks). Stocks are
independent (per-stock candles + firings; holdout group = crc32(sym)%2), so sharding by
stock is EXACT — the only global quantity is the median-ts time-split, which we recompute
on the MERGED tradebook. Each shard gets its own journal dir (env DERIVE_JOURNAL) + its own
tradebook CSV (env DERIVE_TB_OUT); we concat the CSVs and reproduce the derive report with
the GLOBAL split. Result is identical to the serial run (verified vs tradebook_2026.csv).

Usage: DERIVE_DATA=<dir> python3 tools/derive_parallel.py <SYM,...> <nshards> <merged_out.csv>
"""
import os
import subprocess
import sys
import zlib
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path("/home/doom/Public/PROJECT/2026/trader")
SYMS = sys.argv[1].split(",")
NSHARDS = int(sys.argv[2]) if len(sys.argv) > 2 else 8
OUT = Path(sys.argv[3]) if len(sys.argv) > 3 else ROOT / "runs/validate/tradebook_parallel.csv"
DATA = os.environ.get("DERIVE_DATA", str(ROOT / "data/wide"))
WORK = Path(os.environ.get("PAR_WORK", "/tmp/derive_par"))
WORK.mkdir(parents=True, exist_ok=True)

shards = [SYMS[i::NSHARDS] for i in range(NSHARDS)]        # round-robin = load balance
shards = [s for s in shards if s]
print(f"data={DATA}  {len(SYMS)} stocks -> {len(shards)} shards  (sizes {[len(s) for s in shards]})")

procs = []
for k, sub in enumerate(shards):
    env = {**os.environ, "DERIVE_DATA": DATA,
           "DERIVE_JOURNAL": str(WORK / f"journal_{k}"),
           "DERIVE_TB_OUT": str(WORK / f"tb_{k}.csv")}
    log = open(WORK / f"log_{k}.txt", "w")
    procs.append((k, subprocess.Popen(
        [sys.executable, str(ROOT / "tools/derive_tradebook.py"), ",".join(sub), "1"],
        env=env, stdout=log, stderr=subprocess.STDOUT), log))

fail = 0
for k, p, log in procs:
    rc = p.wait(); log.close()
    tb = WORK / f"tb_{k}.csv"
    ok = rc == 0 and tb.exists()
    print(f"  shard {k}: rc={rc} {'OK' if ok else 'FAIL'}  ({len(shards[k])} stocks)")
    fail += not ok
if fail:
    print(f"!! {fail} shard(s) failed — see {WORK}/log_*.txt"); sys.exit(1)

df = pd.concat([pd.read_csv(WORK / f"tb_{k}.csv") for k in range(len(shards))], ignore_index=True)
df.to_csv(OUT, index=False)
print(f"\nmerged {len(df)} records -> {OUT}")


def _grp(sym):
    return "A" if zlib.crc32(sym.encode()) % 2 == 0 else "B"


def stat(sub, label):
    if len(sub) == 0:
        return
    wins = (sub["R"] > 0).sum()
    print(f"  {label:14} n={len(sub):5} win%={100*wins//len(sub):3} "
          f"gross/t={sub['R'].mean():+.2f}R NET/t={sub['net'].mean():+.3f}R")


for mode in ["intrabar", "m5_close", "eod"]:
    m = df[df["mode"] == mode].copy()
    if m.empty:
        continue
    ts = m["ts"].sort_values().values
    split = ts[len(ts) // 2]                                # GLOBAL median-ts split (matches serial derive)
    m["q"] = ["late" if t >= split else "early" for t in m["ts"]]
    m["q"] = m["q"] + "/" + m["sym"].map(_grp)
    print(f"\n=== STOP_MODE={mode}  syms={len(SYMS)} (parallel) ===")
    stat(m, "ALL")
    print("by grade:")
    for g in sorted(m["grade"].unique()):
        stat(m[m["grade"] == g], f"grade {g}")
    hi = m[m["grade"] >= 4]
    print("HIGH-GRADE tier (>=4):"); stat(hi, "hi ALL")
    print("  holdout quadrants (hi tier):")
    for q in sorted(hi["q"].unique()):
        stat(hi[hi["q"] == q], "  " + q)
