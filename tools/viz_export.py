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

The store now derives M5/M15/M30/H1/H2/D1. 30m and 2h -- the two timeframes the
user actually marks order blocks and FVGs on -- were absent from the Timeframe enum
entirely, so no detector could ever see them; they were added and verified bit-exact
against an independent resample.

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
TF_PARAM = {"extremes": "timeframes", "swings": "timeframes"}  # list-valued
STORE_TFS = ["5m", "15m", "30m", "1h", "2h", "1d"]   # all the store derives
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
    for k in ("event", "kind", "side", "gate_mode", "sweep", "ext", "master",
              "live", "up", "crossed", "count", "vol"):
        if k in meta and meta[k] not in (None, False, ""):
            bits.append(k if meta[k] is True else f"{k}={meta[k]}")
    for k in ("prom_pct", "prom", "degree", "sym", "left", "right"):
        if k in meta:
            bits.append(f"{k}={meta[k]}")
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
        tf = e.meta.get("tf") or tf_tag        # multi-tf detectors tag their own
        det = e.detector + (f'/{e.meta["variant"]}' if e.meta.get("variant") else "")
        k = (det, tf, round(lo, 2), round(hi, 2))
        if k in seen:
            seen[k]["n"] += 1
            continue
        # a detector that knows its own pivot bar reports it; use that rather than
        # ctx.now, which is merely when the evidence was last re-emitted
        born = e.meta.get("born")
        born = int(pd.Timestamp(born).timestamp()) if born else int(e.ts.timestamp())
        rec = {"det": det, "tf": tf, "lo": lo, "hi": hi,
               "dir": e.direction.name, "strength": float(e.strength),
               "born": born, "n": 1, "why": reason(e.detector, e.meta)}
        if e.meta.get("px") is not None:
            rec["px"], rec["pts"] = float(e.meta["px"]), born
        seen[k] = rec


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

# extremes with the K floor released, as a comparison row. Computed offline rather
# than as a second detector instance: extremes writes LEVELS keyed on
# symbol-kind-tf-born, so a second instance would collide with production's own
# level ids instead of sitting beside them.
def _kf0_rows():
    from trader.detectors.extremes import _wilder_atr, _leg_K, _zigzag
    cnt = df.groupby(df.ts.dt.date).size()
    good = set(cnt[cnt == 375].index)                 # what the store keeps
    dd = df[df.ts.dt.date.isin(good)]
    om = SESSION_OPEN[0] * 60 + SESSION_OPEN[1]
    for tf, mins in DISPLAY.items():
        t = dd.ts
        mm = t.dt.hour * 60 + t.dt.minute - om
        key = t.dt.normalize() if mins == 0 else \
            t.dt.normalize() + pd.to_timedelta((mm // mins) * mins + om, unit="m")
        g = dd.groupby(key)
        h, lo_, c = list(g.high.max()), list(g.low.min()), list(g.close.last())
        ts = list(g.high.max().index)
        if len(c) < 30:
            continue
        atr = _wilder_atr(h, lo_, c)
        K = _leg_K(atr, c, 0.02, 0.0)                 # floor released
        for pv in _zigzag(h, lo_, [K * a for a in atr]):
            if pv.confirm_idx is None:
                continue
            px = float(pv.price)
            yield {"det": "extremes_kfloor0", "tf": tf,
                   "lo": px, "hi": px, "px": px,
                   "pts": int(ts[pv.idx].timestamp()),
                   "born": int(ts[pv.idx].timestamp()), "end": None,
                   "dir": "SHORT" if pv.side == "H" else "LONG", "n": 1,
                   "why": f"extremes k_floor=0: {pv.side} leg={100*K*atr[-1]/c[-1]:.2f}% "
                          f"(production floors K at 3.0 above 30m)"}


kf0 = list(_kf0_rows())
for z in kf0:
    seen[(z["det"], z["tf"], round(z["lo"], 2), round(z["hi"], 2))] = z
print(f"comparison rows (extremes k_floor=0): {len(kf0)}")

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
