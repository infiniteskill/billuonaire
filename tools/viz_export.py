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

import numpy as np
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
    e = epoch(d.ts)
    return [[int(t), float(r.open), float(r.high), float(r.low),
             float(r.close), int(r.volume)] for t, r in zip(e, d.itertuples())]


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


def epoch(series):
    """TRUE epoch seconds.

    df.ts is tz-naive IST, and BOTH numpy's astype(datetime64) and pandas'
    Timestamp.timestamp() read a naive value as UTC. Writing those numbers out makes
    the browser -- which renders an epoch in the viewer's local zone -- show every
    candle, pivot and zone 5:30 LATE, which is why the chart read "08 Jul 19:15" for
    a market that closes at 15:30. Localise to the source zone first."""
    v = series.dt.tz_localize(TZ) if TZ is not None else series
    return v.apply(lambda t: int(t.timestamp())).to_numpy()


# per-timeframe bar timestamps, so a zone's left edge can step back in BARS
TF_TS = {name: epoch(resample(df, mins).ts) for name, mins in DISPLAY.items()}


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
        # a gap is drawn from the FIRST of its candles. Step back in BARS, never in
        # wall-clock: sessions are not continuous, so subtracting span*tf minutes
        # lands before the open (a 30m gap at 09:45 became 08:45) or in the previous
        # night. TF_TS holds each timeframe's own bar timestamps.
        span = int(e.meta.get("span") or 1)
        formed = born                       # last candle of the gap
        arr = TF_TS.get(tf)
        if span > 1 and arr is not None and len(arr):
            i = int(np.searchsorted(arr, born, side="right")) - 1
            born = int(arr[max(0, i - (span - 1))])
        rec = {"det": det, "tf": tf, "lo": lo, "hi": hi,
               "dir": e.direction.name, "strength": float(e.strength),
               "born": born, "formed": formed, "n": 1,
               "why": reason(e.detector, e.meta)}
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
def _alt_rows():
    """extremes under alternative thresholds, as comparison rows.

    Computed offline rather than as extra detector instances: extremes writes LEVELS
    keyed symbol-kind-tf-born, so a second instance would collide with production's
    own level ids instead of sitting beside them."""
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
        variants = [("kfloor0", [_leg_K(atr, c, 0.02, 0.0) * a for a in atr],
                     "k_floor=0 (ATR mode, floor released)")]
        for pc in (2.0, 3.0, 4.0):                    # threshold_mode=pct
            variants.append((f"pct{pc:g}", [pc / 100 * x for x in c],
                             f"threshold_mode=pct, leg_pct={pc:g}"))
        # the chosen config: SWING structure (3%) plus INTERNAL structure (2%).
        # Emitted as one row because that is how it will run -- leg_pct is a list
        # and both scales contribute to the same level set.
        variants.append(("swing3int2", None, "leg_pct=[3,2]: swing + internal"))
        for tag, thr, why in variants:
            if thr is None:                           # union of both scales
                pv_all, seen_k = [], set()
                for pc in (3.0, 2.0):
                    for q in _zigzag(h, lo_, [pc / 100 * x for x in c]):
                        if q.confirm_idx is None:
                            continue
                        k = (q.side, q.idx)
                        if k not in seen_k:
                            seen_k.add(k); pv_all.append(q)
                iterable = pv_all
            else:
                iterable = _zigzag(h, lo_, thr)
            for pv in iterable:
                if pv.confirm_idx is None:
                    continue
                px = float(pv.price)
                yield {"det": f"extremes_{tag}", "tf": tf, "lo": px, "hi": px,
                       "px": px, "pts": int(ts[pv.idx].timestamp()),
                       "born": int(ts[pv.idx].timestamp()), "end": None,
                       "dir": "SHORT" if pv.side == "H" else "LONG", "n": 1,
                       "why": f"{pv.side} · {why}"}


alt = list(_alt_rows())
for z in alt:
    seen[(z["det"], z["tf"], round(z["lo"], 2), round(z["hi"], 2))] = z
import collections as _co
print("comparison rows:", dict(_co.Counter(z["det"] for z in alt)))

# LEFT of the swing = iFVG, RIGHT of the swing = FVG (user's rule). This is a
# RELATION between a gap and an extreme, not a property of the gap, so it is applied
# here rather than inside the detector. Verified against five hand-drawn boxes: the
# 29 Jun box scored a 9-point MISS when the nearest gap was chosen across both sides
# (it picked the left/iFVG at 1157.0-1160.8) and is exact to 0.4 once restricted to
# the right side.
# Geometrically: price rallies INTO a swing high (bullish gaps on the way up = the
# LEFT side), then falls AWAY from it (bearish gaps = the RIGHT side). So the test is
# whether the gap's direction points AWAY from the most recent extreme. After an
# EXT_H the leg is down, so SHORT gaps are the live FVGs and LONG gaps are the
# inverted ones; after an EXT_L it mirrors.
_EXT = sorted(((l["born"], l["kind"]) for l in levels
               if l["kind"].startswith("EXT")), key=lambda x: x[0])
_EXT_TS = [t for t, _ in _EXT]


def _side_of_swing(z):
    if not _EXT_TS:
        return None
    i = int(np.searchsorted(_EXT_TS, z.get("formed", z["born"]), side="right")) - 1
    if i < 0:
        return None
    away = "SHORT" if _EXT[i][1] == "EXT_H" else "LONG"
    return "right" if z["dir"] == away else "left"


for z in seen.values():
    if z["det"] in ("fvg_n", "fvg"):
        z["side"] = _side_of_swing(z)
        if z["side"]:
            z["det"] = f'{z["det"]}/{"FVG" if z["side"] == "right" else "iFVG"}'

zones = sorted(seen.values(), key=lambda z: z["born"])

# WHEN DOES PRICE COME BACK? A zone is drawn extended into the future only until
# price returns to it -- that first touch is the mitigation, and it is the same
# unvisited/visited filter that decides whether a setup is still live. Evidence
# zones carry no lifecycle of their own (they are re-emitted per tick and never
# tracked), so resolve it here from the 1m tape.
_ts = epoch(df.ts)
_hi = df.high.values.astype(float)
_lo = df.low.values.astype(float)
_SEARCH = 30 * 375                                   # ~30 sessions is plenty


def _first_touch(formed, lo, hi, tf="5m"):
    """First bar AFTER the gap completes whose range re-enters it."""
    i = int(np.searchsorted(_ts, formed + 60 * TF_MIN.get(tf, 5), side="left"))
    j = min(len(_ts), i + _SEARCH)
    if i >= j:
        return None
    inside = (_lo[i:j] <= hi) & (_hi[i:j] >= lo)
    k = int(inside.argmax())
    return int(_ts[i + k]) if inside[k] else None


for z in zones:
    # Search from AFTER the gap completes, never from its first candle: the middle
    # candle of a 3-bar gap lies inside the gap by construction, so searching from
    # the left edge finds the gap touching itself and every box collapses to a
    # sliver instead of extending to where price actually came back.
    z["end"] = _first_touch(z.get("formed", z["born"]), z["lo"], z["hi"], z["tf"])
    z["filled"] = z["end"] is not None
n_open = sum(1 for z in zones if not z["filled"])
print(f"zones: {len(zones)} | still UNVISITED (price never returned): {n_open}")

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
