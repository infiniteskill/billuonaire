import importlib.util, sys
spec = importlib.util.spec_from_file_location("cp", "/tmp/claude-1000/-home-doom-Public-PROJECT-2026-trader/a013584c-0930-4f6c-921b-e4ea05cde0a4/scratchpad/chartpar_run_lib.py")
# reuse functions by re-defining minimal bits instead
sys.path.insert(0, "/tmp/claude-1000/-home-doom-Public-PROJECT-2026-trader/a013584c-0930-4f6c-921b-e4ea05cde0a4/scratchpad")
import datetime as dt
from datetime import timedelta

exec(open("/tmp/claude-1000/-home-doom-Public-PROJECT-2026-trader/a013584c-0930-4f6c-921b-e4ea05cde0a4/scratchpad/chartpar_run.py").read().split("# =====")[0])

df = load_tf("HINDUNILVR", 30)
atr = atr_series(df)
sw = fractal_swings(df, 5)
USER_SW = [
    ("SH ~2225 mid-Jun",  "SWING_H", (2216, 2234), dt.date(2026,6,10), dt.date(2026,6,20)),
    ("SH ~2245 early-Jul","SWING_H", (2233, 2257), dt.date(2026,6,30), dt.date(2026,7,8)),
    ("SL ~2085 early-Jun","SWING_L", (2077, 2093), dt.date(2026,6,1),  dt.date(2026,6,9)),
    ("SL ~2100 17-Jul",   "SWING_L", (2087, 2113), dt.date(2026,7,15), dt.date(2026,7,17)),
]
for m in (2.0, 2.5, 3.0, 3.5, 4.0):
    surv = [s for s in sw if atr[s["i"]] and swing_prominence(s, df) >= m * atr[s["i"]]]
    kept_user = 0
    for name, kind, band, d0, d1 in USER_SW:
        hits = [s for s in surv if s["kind"] == kind and band[0] <= s["px"] <= band[1]
                and d0 - timedelta(days=4) <= s["ts"].date() <= d1 + timedelta(days=4)]
        if hits: kept_user += 1
    print(f"prom>={m}ATR: total={len(surv)}  user-marks kept={kept_user}/4")
