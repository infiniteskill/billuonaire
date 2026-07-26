"""viz_export.py — dump what our detectors ACTUALLY draw, for visual inspection.

Every number this project produced was mediated by code nobody ever looked at with
their eyes. This exports every zone, level and pivot in ABSOLUTE time+price -- never
bar indices -- which is what lets a box found on 1h render in the same place on the
5m series, the way a hand-drawn box does.

Two passes:

  PROD   the real production path (Orchestrator over 1m bars, the same one
         derive_tradebook uses). This is what the system genuinely does today:
         every structural detector runs on 5m and nothing else.

  GRID   extra instances of every tf-parameterised detector, one per timeframe
         the CandleStore can actually build, running alongside the real feed.
         Their output is recorded but never returned to the pipeline, so trading
         behaviour is unchanged. This answers "what would we see on 1h?".

The store derives only M5/M15/H1/D1. 30m and 2h -- the two timeframes the user
actually marks order blocks and FVGs on -- cannot be computed at all, so those
grid columns stay empty. That is the finding, not a bug in this tool. (Feeding
resampled 30m bars in as M1 does not work around it: the store audits each M5
bucket for its full 5 M1 bars and treats a 1-bar bucket as a feed gap, so
detectors never run.)

Usage: python3 tools/viz_export.py <SYM> <data_dir> <out.json> [profile.json]
"""
import json
import os
import sys
from datetime import timedelta
from pathlib import Path

import pandas as pd

ROOT = Path("/home/doom/Public/PROJECT/2026/trader")
sys.path.insert(0, str(ROOT / "app"))
from trader.config import check_detector_deps, load_settings  # noqa: E402
from trader.engine.pipeline import Orchestrator  # noqa: E402
from trader.feed.file import FileFeed  # noqa: E402

SYM, DATA, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
PROFILE = Path(sys.argv[4]) if len(sys.argv) > 4 else ROOT / "runs/validate/stage2_profile/config.json"
TAUGHT = ["extremes", "swings", "liquidity", "sweep", "structure", "wyckoff",
          "orderblock", "fvg", "compression", "ob_taught", "fvg_n", "propulsion2",
          "premium_discount", "htf_nest"]
# session-scoped detectors read today()/prev_day()/D1 directly and are meaningless
# when the series is not really 1m, so the grid pass leaves them out
PER_TF = [d for d in TAUGHT if d not in ("liquidity", "htf_nest", "premium_discount")]
TF_PARAM = {"extremes": "timeframes", "swings": "timeframes"}     # list-valued
STORE_TFS = ["5m", "15m", "1h", "1d"]      # all the CandleStore can derive
SESSION_OPEN = (9, 15)
DISPLAY = {"5m": 5, "15m": 15, "30m": 30, "1h": 60, "2h": 120, "1d": 0}   # 0 = session
TF_MIN = {"5m": 5, "15m": 15, "30m": 30, "1h": 60, "2h": 120, "1d": 375}
PIVOT = {"EXT_H", "EXT_L", "SWING_H", "SWING_L"}


def resample(df, minutes):
    """Session-anchored OHLC. Wall-clock resampling would misalign every bucket
    because the NSE session opens at 09:15, not on the hour."""
    t = df.ts
    om = SESSION_OPEN[0] * 60 + SESSION_OPEN[1]
    mins = t.dt.hour * 60 + t.dt.minute - om
    kf = t.dt.normalize() if minutes == 0 else \
        t.dt.normalize() + pd.to_timedelta((mins // minutes) * minutes + om, unit="m")
    g = df.groupby(kf)
    out = pd.DataFrame({"open": g.open.first(), "high": g.high.max(),
                        "low": g.low.min(), "close": g.close.last(),
                        "volume": g.volume.sum()}).reset_index()
    out.columns = ["ts", "open", "high", "low", "close", "volume"]
    return out


def rows(d):
    return [[int(r.ts.timestamp()), float(r.open), float(r.high), float(r.low),
             float(r.close), int(r.volume)] for r in d.itertuples()]


def reason(det, meta):
    """One human-readable line per drawing -- the 'why' the chart shows on hover."""
    bits = []
    for k in ("event", "kind", "gate_mode", "sweep", "ext", "master", "live", "up"):
        if k in meta and meta[k] not in (None, False, ""):
            bits.append(k if meta[k] is True else f"{k}={meta[k]}")
    for k in ("disp_atr", "depth_atr", "min_gap_atr", "rank_atr", "distance_atr"):
        if isinstance(meta.get(k), (int, float)):
            bits.append(f"{k}={meta[k]:.2f}")
    return f"{det}: " + (", ".join(bits) if bits else "no meta")


df = pd.read_csv(f"{DATA}/{SYM}.csv", parse_dates=["ts"])
TZ = df.ts.dt.tz                                   # Candle requires tz-aware; the
if TZ is not None:                                 # grid pass re-applies it on write
    df["ts"] = df.ts.dt.tz_localize(None)          # one naive clock for analysis
m1 = df.set_index("ts").sort_index()

seen, levels = {}, []


def record(evs, tf_tag):
    for e in evs:
        if not e.zone:
            continue
        lo, hi = sorted(float(x) for x in e.zone)
        k = (e.detector, tf_tag, round(lo, 2), round(hi, 2))
        if k in seen:
            seen[k]["n"] += 1
            continue
        seen[k] = {"det": e.detector, "tf": tf_tag, "lo": lo, "hi": hi,
                   "dir": e.direction.name, "strength": float(e.strength),
                   "born": int(e.ts.timestamp()), "n": 1,
                   "why": reason(e.detector, e.meta)}


def tip(kind, born, tf):
    """A pivot Level carries born = the BAR OPEN of the bar that made it, and a zone
    that is a body-to-wick BAND, not the extreme. Drawn literally, a 1h pivot lands
    up to an hour left of its own wick and halfway down the candle -- 'almost right'.
    Resolve the true tip from the 1m tape inside that bar."""
    b = born.replace(tzinfo=None) if born.tzinfo else born
    w = m1.loc[b:b + timedelta(minutes=TF_MIN.get(tf or "", 5)) - timedelta(seconds=1)]
    if not len(w):
        return None, None
    if kind.endswith("_H"):
        return float(w.high.max()), int(w.high.idxmax().timestamp())
    return float(w.low.min()), int(w.low.idxmin().timestamp())


def take_levels(pipe, force_tf=None):
    for lv in pipe.levels:
        lo, hi = sorted(float(x) for x in lv.zone)
        end = None
        for ts, st in lv.state_history:            # a box stops extending when
            if st.name in ("MITIGATED", "DEAD", "INVERTED", "SWEPT"):  # price answers
                end = int(ts.timestamp()); break
        tf = force_tf or (lv.tf.value if lv.tf else None)
        rec = {"id": f"{force_tf or ''}{lv.id}", "kind": lv.kind.name, "lo": lo, "hi": hi,
               "born": int(lv.born.timestamp()), "end": end, "tf": tf,
               "state": lv.state.name, "touches": lv.touches,
               "history": [[int(t.timestamp()), st.name] for t, st in lv.state_history]}
        if lv.kind.name in PIVOT:
            px, pts = tip(lv.kind.name, lv.born, tf)
            if px is not None:
                rec["px"], rec["pts"] = px, pts
        levels.append(rec)


def build(enabled, params_patch, data_dir, jdir):
    global s_params
    s = load_settings(PROFILE)
    s_params = s.detectors.params
    s.detectors.enabled = list(enabled)
    for k, v in params_patch.items():
        s.detectors.params.setdefault(k, {}).update(v)
    check_detector_deps(s.detectors.enabled)
    o = Orchestrator(s, FileFeed(Path(data_dir), s.market_spec()), [SYM],
                     index_symbol=None, max_qty=1, journal_dir=jdir)
    return o, o.pipelines[SYM]


# ---- one pass over the real 1m feed -----------------------------------------
# live_master is default-off in production (rejected as a TRADING change), but with
# it off the still-forming extreme never emits -- the newest high/low on any chart
# has no marker. An inspection tool must show it.
# swings/extremes take a timeframe LIST, so widen them here; every other structural
# detector takes a single `tf` and production only ever instantiates it once, on 5m.
patch = {"extremes": {"live_master": True, "timeframes": STORE_TFS},
         "swings": {"timeframes": STORE_TFS}}
orch, pipe = build(TAUGHT, patch, DATA, ROOT / "runs/validate/viz_work")

EXTRA = []
for name in PER_TF:
    if TF_PARAM.get(name):
        continue                       # already multi-tf via its list param
    inst = next((d for d in pipe.registry.detectors if d.name == name), None)
    if inst is None:
        continue
    base = dict(s_params.get(name, {}))
    EXTRA += [(t, type(inst)({**base, "tf": t})) for t in STORE_TFS if t != "5m"]

_orig = pipe.registry.run_all


def tap(ctx):
    evs = _orig(ctx)
    record(evs, "5m")                  # production: everything lands on 5m
    for t, d in EXTRA:                 # comparison only, never returned
        try:
            record(d.detect(ctx), t)
        except Exception:
            pass
    return evs


pipe.registry.run_all = tap
orch.run()
take_levels(pipe)
print(f"pass done: {len(seen)} zones, {len(levels)} levels, "
      f"{len(EXTRA)} extra detector instances")

zones = sorted(seen.values(), key=lambda z: z["born"])
for z in zones:
    z["end"] = None                                  # evidence zones extend to now

out = {"symbol": SYM, "last_ts": int(df.ts.max().timestamp()),
       "candles": {name: rows(resample(df, m)) for name, m in DISPLAY.items()},
       "zones": zones, "levels": levels}
blob = json.dumps(out, separators=(",", ":"))
Path(OUT).write_text(blob)
# self-contained page: file:// cannot fetch a sibling .json (CORS), so inline it
tpl = (ROOT / "tools/viz/chart_template.html").read_text()
html = Path(OUT).with_suffix(".html")
html.write_text(tpl.replace("__SYMBOL__", SYM).replace("__DATA__", blob))
print(f"\n{SYM}: {len(df)} 1m bars -> {OUT} ({os.path.getsize(OUT)/1e6:.1f} MB)")
print(f"CHART: {html}")
print("  display tfs: " + ", ".join(f"{k}={len(v)}" for k, v in out["candles"].items()))

grid = {}
for z in zones:
    grid.setdefault(z["det"], {})[z["tf"]] = grid.setdefault(z["det"], {}).get(z["tf"], 0) + 1
for lv in levels:
    k = lv["kind"]
    grid.setdefault(k, {})[lv["tf"]] = grid.setdefault(k, {}).get(lv["tf"], 0) + 1
cols = ["5m", "15m", "30m", "1h", "2h", "1d", None]
print(f"\n{'feature':20}" + "".join(f"{str(c or 'ses'):>7}" for c in cols))
for k in sorted(grid):
    print(f"{k:20}" + "".join(f"{grid[k].get(c,'-'):>7}" for c in cols))
