#!/usr/bin/env python
"""HINDUNILVR full SMC inventory across 5m/15m/30m/H1/D1.

Zone construction reuses the chartpar_run.py standalone replications of
ob_lux / fvg_cb / fractal swings (verified ports of the repo detectors).
Breaker ports the EmreKb core from app/trader/detectors/breaker_msb.py
(zz=9 zigzag flip -> fib-0.33 MSB -> swept older swing => origin-candle box).
Liquidity pools/sweeps per task spec: 2+ same-side fractal swing points
within 0.25*ATR(14,TF) = pool; sweep = wick through pool level, close back.
"""
import sys, json, bisect
import datetime as dt
import pandas as pd
from collections import deque

SCRATCH = "/tmp/claude-1000/-home-doom-Public-PROJECT-2026-trader/a013584c-0930-4f6c-921b-e4ea05cde0a4/scratchpad"
# pull atr_series / ob_lux / fvg_cb / fractal_swings / swing_prominence from chartpar
exec(open(f"{SCRATCH}/chartpar_run.py").read().split("# =====")[0])

DATA = "/home/doom/Public/PROJECT/2026/trader/data/long5m/HINDUNILVR.csv"

def load(minutes=None):
    df = pd.read_csv(DATA, parse_dates=["ts"]).set_index("ts").sort_index()
    if minutes is None:  # D1: one bar per session date
        g = df.groupby(df.index.date)
        agg = pd.DataFrame({"ts": [pd.Timestamp(d, tz=df.index.tz) for d in g.size().index],
                            "open": g.open.first().values, "high": g.high.max().values,
                            "low": g.low.min().values, "close": g.close.last().values,
                            "volume": g.volume.sum().values})
        return agg
    off = (9 * 60 + 15) % minutes  # 09:15-anchored bins
    agg = df.resample(f"{minutes}min", offset=f"{off}min", label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    ).dropna(subset=["open"]).reset_index()
    return agg

# ---------- extremes: prominence = subsequent move from swing before violation ----------
def extremes(swings, df, atr, mult=2.0):
    H, L = df.high.tolist(), df.low.tolist()
    n = len(df)
    first_atr = next((a for a in atr if a is not None), None)
    out = []
    for s in swings:
        i, px = s["i"], s["px"]
        a = atr[i] if atr[i] is not None else first_atr
        if a is None:
            continue
        if s["kind"] == "SWING_H":
            j = next((k for k in range(i + 1, n) if H[k] > px), None)
            seg = L[i + 1:(j if j is not None else n)]
            prom = px - min(seg) if seg else 0.0
        else:
            j = next((k for k in range(i + 1, n) if L[k] < px), None)
            seg = H[i + 1:(j if j is not None else n)]
            prom = max(seg) - px if seg else 0.0
        s2 = dict(s, prom=prom, atr=a, extreme=prom >= mult * a, violated=j is not None)
        out.append(s2)
    return out

# ---------- iFVG: closed beyond far edge, then retested from other side ----------
def ifvg_count(fvgs, df):
    H, L, C = df.high.tolist(), df.low.tolist(), df.close.tolist()
    n = len(df); cnt = 0; inv_only = 0
    for z in fvgs:
        bull = z["kind"] == "FVG_BULL"
        k = next((t for t in range(z["ev_i"] + 1, n)
                  if (C[t] < z["lo"] if bull else C[t] > z["hi"])), None)
        if k is None:
            continue
        inv_only += 1
        retest = any((H[t] >= z["lo"] if bull else L[t] <= z["hi"])
                     for t in range(k + 1, n))
        if retest:
            cnt += 1
    return cnt, inv_only

# ---------- breaker (EmreKb MSB core, floats; count box creations + retests) ----------
def breaker_msb(df, zz=9, fib=0.33, warm=25):
    H, L, O, C = df.high.tolist(), df.low.tolist(), df.open.tolist(), df.close.tolist()
    TS = df.ts.tolist(); n = len(df)
    trend, market = 1, 1
    hi = lo = None
    highs, lows = [], []
    l0p = h0p = None
    boxes, created, fired = [], [], []
    warm = max(warm, 14)
    for i in range(n):
        # ---- zigzag flip
        if hi is None or H[i] > hi[1]: hi = (i, H[i])
        if lo is None or L[i] < lo[1]: lo = (i, L[i])
        w0 = max(0, i - zz + 1)
        flipped = False
        if trend == 1 and L[i] <= min(L[w0:i + 1]):
            highs = (highs + [hi])[-2:]; flipped = True
        elif trend == -1 and H[i] >= max(H[w0:i + 1]):
            lows = (lows + [lo])[-2:]; flipped = True
        if flipped:
            trend = -trend
            hi, lo = (i, H[i]), (i, L[i])
        # ---- MSB + box creation
        if len(highs) == 2 and len(lows) == 2 and i >= warm:
            (h0i, h0), (h1i, h1) = highs[-1], highs[-2]
            (l0i, l0), (l1i, l1) = lows[-1], lows[-2]
            if not (l0 == l0p or h0 == h0p):
                if market == 1 and l0 < l1 and l0 < l1 - abs(h0 - l1) * fib:
                    market, l0p, h0p = -1, l0, h0
                    if h0 > h1:  # swing high swept -> bearish breaker
                        j = next((j for j in range(l1i, max(0, h1i - zz) - 1, -1)
                                  if O[j] > C[j]), None)
                        if j is not None:
                            b = dict(top=H[j], bot=L[j], d=-1, born=i, fired=False,
                                     origin_ts=TS[j], ev_ts=TS[i])
                            boxes.append(b); created.append(b)
                elif market == -1 and h0 > h1 and h0 > h1 + abs(h1 - l0) * fib:
                    market, l0p, h0p = 1, l0, h0
                    if l0 < l1:  # swing low swept -> bullish breaker
                        j = next((j for j in range(h1i, max(0, l1i - zz) - 1, -1)
                                  if O[j] < C[j]), None)
                        if j is not None:
                            b = dict(top=H[j], bot=L[j], d=1, born=i, fired=False,
                                     origin_ts=TS[j], ev_ts=TS[i])
                            boxes.append(b); created.append(b)
        # ---- box lifecycle: death first, then once-per-box later-close entry
        keep = []
        for b in boxes:
            if (b["d"] == 1 and C[i] < b["bot"]) or (b["d"] == -1 and C[i] > b["top"]):
                continue
            if not b["fired"] and i > b["born"] and (
                    b["bot"] <= C[i] < b["top"] if b["d"] == 1 else b["bot"] < C[i] <= b["top"]):
                b["fired"] = True; fired.append((i, b))
            keep.append(b)
        boxes = keep
    return created, fired

# ---------- liquidity pools + sweeps (task spec) ----------
def pools_and_sweeps(swings, df, atr, tol_mult=0.25, confirm_lag=5):
    H, L, C = df.high.tolist(), df.low.tolist(), df.close.tolist()
    n = len(df)
    first_atr = next((a for a in atr if a is not None), None)
    res = {}
    for kind, take_hi in (("EQH", True), ("EQL", False)):
        pts = sorted([s for s in swings if s["kind"] == ("SWING_H" if take_hi else "SWING_L")],
                     key=lambda s: s["px"])
        pools, cur, anchor = [], [], None
        for s in pts:
            a = atr[s["i"]] if atr[s["i"]] is not None else first_atr
            tol = tol_mult * (a or 0)
            if cur and abs(s["px"] - anchor) <= tol:
                cur.append(s)
            else:
                if len(cur) >= 2: pools.append(cur)
                cur, anchor = [s], s["px"]
        if len(cur) >= 2: pools.append(cur)
        swept = 0
        for g in pools:
            level = max(x["px"] for x in g) if take_hi else min(x["px"] for x in g)
            start = min(n, max(x["i"] for x in g) + confirm_lag + 1)
            hit = next((t for t in range(start, n)
                        if ((H[t] > level and C[t] < level) if take_hi
                            else (L[t] < level and C[t] > level))), None)
            if hit is not None:
                swept += 1
        res[kind] = (len(pools), swept)
    return res

# =====================================================================
TFS = [("5m", 5), ("15m", 15), ("30m", 30), ("H1", 60), ("D1", None)]
frames, results = {}, {}
for name, mins in TFS:
    df = load(mins)
    atr = atr_series(df)
    sw = fractal_swings(df, 5)
    ext = extremes(sw, df, atr)
    obs = ob_lux(df)
    fvgs = fvg_cb(df)
    ifvg, inv_only = ifvg_count(fvgs, df)
    brk, brk_fired = breaker_msb(df)
    liq = pools_and_sweeps(sw, df, atr)
    frames[name] = dict(df=df, atr=atr, sw=sw, ext=ext, obs=obs, fvgs=fvgs, brk=brk)
    results[name] = dict(
        bars=len(df),
        swings=len(sw), swH=sum(1 for s in sw if s["kind"] == "SWING_H"),
        swL=sum(1 for s in sw if s["kind"] == "SWING_L"),
        extremes=sum(1 for s in ext if s["extreme"]),
        fvg=len(fvgs), fvg_bull=sum(1 for z in fvgs if z["kind"] == "FVG_BULL"),
        ob=len(obs), ob_bull=sum(1 for z in obs if z["kind"] == "OB_BULL"),
        ifvg=ifvg, fvg_invalidated=inv_only,
        breaker=len(brk), breaker_retested=len(brk_fired),
        eqh_pools=liq["EQH"][0], eqh_swept=liq["EQH"][1],
        eql_pools=liq["EQL"][0], eql_swept=liq["EQL"][1],
    )
    print(name, json.dumps(results[name]))

sessions = sorted(set(t.date() for t in frames["5m"]["df"].ts))
NS = len(sessions)
print(f"sessions={NS}")

def shift(d, k):
    idx = bisect.bisect_left(sessions, d)
    idx = min(idx, NS - 1)
    return sessions[max(0, min(NS - 1, idx + k))]

# ---------- HTF -> LTF nesting ----------
m5z = frames["5m"]["obs"] + frames["5m"]["fvgs"]
def nest_map(htf_name):
    hz = frames[htf_name]["obs"] + frames[htf_name]["fvgs"]
    rows = []
    for z in hz:
        d = z["born"].date()
        lo_d, hi_d = shift(d, -2), shift(d, +2)
        full = part = 0
        for m in m5z:
            if not (lo_d <= m["born"].date() <= hi_d):
                continue
            if m["lo"] >= z["lo"] and m["hi"] <= z["hi"]:
                full += 1
            elif m["lo"] < z["hi"] and m["hi"] > z["lo"]:
                part += 1
        rows.append(dict(z=z, full=full, part=part, tot=full + part))
    return rows

def dist(rows, key="tot"):
    from collections import Counter
    c = Counter(r[key] for r in rows)
    return dict(sorted(c.items()))

nest_h1 = nest_map("H1")
nest_30 = nest_map("30m")
for tag, rows in (("H1->5m", nest_h1), ("30m->5m", nest_30)):
    tots = [r["tot"] for r in rows]
    fulls = [r["full"] for r in rows]
    parts = [r["part"] for r in rows]
    print(f"{tag}: zones={len(rows)} avg_tot={sum(tots)/len(rows):.2f} "
          f"avg_full={sum(fulls)/len(rows):.2f} avg_part={sum(parts)/len(rows):.2f} "
          f"dist={dist(rows)}")

# ---------- H1 extremes -> 5m zone within 1*ATR(5m) ----------
m5df = frames["5m"]["df"]; atr5 = frames["5m"]["atr"]
m5ts = m5df.ts.tolist()
first_atr5 = next(a for a in atr5 if a is not None)
h1ext = [s for s in frames["H1"]["ext"] if s["extreme"]]
join_time, join_any = 0, 0
join_rows = []
for s in h1ext:
    k = min(bisect.bisect_right(m5ts, s["ts"]) - 1, len(m5ts) - 1)
    a5 = atr5[k] if k >= 0 and atr5[k] is not None else first_atr5
    d0, d1 = shift(s["ts"].date(), -2), shift(s["ts"].date(), +2)
    def near(m):
        gap = max(m["lo"] - s["px"], s["px"] - m["hi"], 0.0)
        return gap <= a5
    any_hit = any(near(m) for m in m5z)
    time_hit = any(near(m) and d0 <= m["born"].date() <= d1 for m in m5z)
    join_any += any_hit; join_time += time_hit
    join_rows.append((s, time_hit, any_hit, a5))
print(f"H1 extremes={len(h1ext)} with 5m zone within 1xATR5 (+-2 sess)={join_time} "
      f"(price-only anytime={join_any})")

# ---------- dump for report ----------
out = dict(results=results, sessions=NS,
           nest_h1=dict(n=len(nest_h1),
                        avg_tot=sum(r["tot"] for r in nest_h1) / max(1, len(nest_h1)),
                        avg_full=sum(r["full"] for r in nest_h1) / max(1, len(nest_h1)),
                        avg_part=sum(r["part"] for r in nest_h1) / max(1, len(nest_h1)),
                        dist=dist(nest_h1)),
           nest_30=dict(n=len(nest_30),
                        avg_tot=sum(r["tot"] for r in nest_30) / max(1, len(nest_30)),
                        avg_full=sum(r["full"] for r in nest_30) / max(1, len(nest_30)),
                        avg_part=sum(r["part"] for r in nest_30) / max(1, len(nest_30)),
                        dist=dist(nest_30)),
           h1_ext_join=dict(n=len(h1ext), time=join_time, any=join_any))
json.dump(out, open(f"{SCRATCH}/hulinv_out.json", "w"), default=str, indent=1)

# examples: recent H1 zones (mix OB/FVG/breaker) + the extreme join detail
print("\nH1 ZONES (all, chronological):")
for z in sorted(frames["H1"]["obs"] + frames["H1"]["fvgs"], key=lambda z: z["born"]):
    print(f"  {z['det']:6s} {z['kind']:8s} [{z['lo']:.2f},{z['hi']:.2f}] born={z['born']} ev={z['ev_ts']}")
print("\nH1 BREAKERS:")
for b in frames["H1"]["brk"]:
    print(f"  {'BULL' if b['d']==1 else 'BEAR'} [{b['bot']:.2f},{b['top']:.2f}] "
          f"origin={b['origin_ts']} msb={b['ev_ts']} fired={b['fired']}")
print("\nH1 EXTREMES:")
for s, th, ah, a5 in join_rows:
    print(f"  {s['kind']:7s} {s['ts']} px={s['px']:.2f} prom={s['prom']:.1f} "
          f"atrH1={s['atr']:.1f} join_time={th} join_any={ah}")
