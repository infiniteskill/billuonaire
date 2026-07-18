"""STEP 1 (long60) -- DEFINITIVE capture over data/long5m (138 stocks + NIFTY,
NATIVE 5m bars fed as M1; M5 aggregation verified IDENTITY by l60_verify.py:
store M5 == CSV rows == store M1, all fields, 1:1).

Drives the REAL Orchestrator/SymbolPipeline with the 7 parity-locked v2
detectors + non-colliding context providers (swings/liquidity/structure/
wyckoff -- the --only-equivalent set; NO orderblock/fvg/compression/breaker
level-pool twins). Per TARGET Evidence records:

  signal:  detector, event, symbol, session, ts, direction, entry (signal M5
           close), sl (meta sl, fallback zone edge), risk, atr, zone, strength
  causal context (all computed from ctx -- no lookahead; index pipeline runs
           first each ts so ctx.index is same-close): day TEMPLATE (post
           classifier.update -- what production sees), index wyckoff phase +
           alignment, premium/discount vs session dealing range, M15 trend
           (closed M15 bars only), vol regime (ATR vs trailing median),
           30-min bucket
  outcomes (post-hoc, EOD-truncated, no next-day bleed): max_r (rr50-style
           walk vs meta SL), hit/mfe/mae (study.outcome, 1ATR-symmetric,
           24-bar window), b_hit (study.baseline, 20 seeded same-session/
           same-30min-bucket/same-direction random bars)
  path:    forward 5m bars (o/h/l/c arrays) from the NEXT bar after the
           signal to session EOD -- consumed only by realistic-fill sims.

Writes signals60.parquet.
"""
from __future__ import annotations

import os
import sys
import statistics as st
import time
from datetime import timedelta
from pathlib import Path

TRADER_APP = "/home/doom/Public/PROJECT/2026/trader/app"
DATA_DIR = Path("/home/doom/Public/PROJECT/2026/trader/data/long5m")
CFG_PATH = Path("/home/doom/Public/PROJECT/2026/trader/app/config/config.json")
OUT_DIR = Path("/tmp/claude-1000/-home-doom-Public-PROJECT-2026-trader/"
               "a013584c-0930-4f6c-921b-e4ea05cde0a4/scratchpad")
WORK_DIR = OUT_DIR / "work_l60"
OUT_PATH = OUT_DIR / "signals60.parquet"

sys.path.insert(0, TRADER_APP)

import pandas as pd                                             # noqa: E402
from trader.config import load_settings                         # noqa: E402
from trader.detectors.timestats import bucket_index             # noqa: E402
from trader.engine.pipeline import Orchestrator                 # noqa: E402
from trader.feed.file import FileFeed                           # noqa: E402
from trader.models.candle import Timeframe                      # noqa: E402
from trader.tools.study import atr_series, outcome, baseline    # noqa: E402

TARGET = {"ob_lux", "fvg_cb", "compression_fade", "inducement", "bpr",
          "mitigation", "turtle_soup"}
SUPPORT = {"swings", "liquidity", "structure", "wyckoff"}
INDEX = "NIFTY"
M15_LOOK = 8
VOL_LOOK = 20
SL_ATR_FLOOR = 0.15
MIN_ROWS = 1000                       # exclude empty/thin CSVs
_M5 = timedelta(minutes=5)
_PHASE_DIR = {"MARKUP": 1, "ACCUMULATION": 1, "MARKDOWN": -1, "DISTRIBUTION": -1}


def ctx_snapshot(ctx, spec) -> dict:
    iv = ctx.index
    idx_phase = iv.phase if iv is not None else "NONE"
    tday = ctx.candles.today(Timeframe.M5)
    if tday:
        slo = float(min(c.low for c in tday)); shi = float(max(c.high for c in tday))
    else:
        slo = shi = None
    m15 = ctx.candles.last(M15_LOOK, Timeframe.M15)
    m15_atr = ctx.atr(Timeframe.M15)
    if len(m15) >= 4:
        net = float(m15[-1].close - m15[0].close)
        scale = float(m15_atr) if (m15_atr and m15_atr > 0) else \
            (sum(float(c.high - c.low) for c in m15) / len(m15) or 1.0)
        m15_net_atr = net / scale
    else:
        m15_net_atr = None
    tb = bucket_index(ctx.now, spec, 30)
    return dict(idx_phase=idx_phase, sess_lo=slo, sess_hi=shi,
                m15_net_atr=m15_net_atr, tb=tb)


def make_tap(pipe, sink, tmap, spec) -> None:
    orig_run = pipe.registry.run_all

    def run_all(ctx):
        evs = orig_run(ctx)
        tgt = [e for e in evs if e.detector in TARGET]
        if tgt:
            m5 = ctx.candles.last(1, Timeframe.M5)
            c5 = m5[-1] if m5 else None
            atr = ctx.atr(Timeframe.M5)
            if c5 is not None and atr is not None and atr > 0:
                snap = ctx_snapshot(ctx, spec)
                for e in tgt:
                    sink.append((pipe.symbol, c5, float(atr), e, snap))
        return evs

    pipe.registry.run_all = run_all

    orig_upd = pipe.classifier.update

    def update(ctx):
        t = orig_upd(ctx)
        last = ctx.candles.last(1, Timeframe.M5)
        if last:
            tmap[(pipe.symbol, last[-1].ts)] = t
        return t

    pipe.classifier.update = update


def drive():
    settings = load_settings(CFG_PATH).model_copy(deep=True)
    settings.detectors.enabled = sorted(TARGET | SUPPORT)
    syms = []
    for p in sorted(DATA_DIR.glob("*.csv")):
        if p.stem == INDEX:
            continue
        with open(p) as f:
            n = sum(1 for _ in f) - 1
        if n >= MIN_ROWS:
            syms.append(p.stem)
        else:
            print(f"EXCLUDED thin csv: {p.stem} ({n} rows)", flush=True)
    subset = os.environ.get("SUBSET")
    if subset:
        want = set(subset.split(","))
        syms = [s for s in syms if s in want]
    print(f"symbols: {len(syms)} + index {INDEX}", flush=True)
    spec = settings.market_spec()
    feed = FileFeed(DATA_DIR, spec)
    orig_events = feed.events

    def events():                                   # progress heartbeat
        t0 = time.time()
        for k, ev in enumerate(orig_events()):
            if k % 50000 == 0:
                print(f"  feed event {k}  t={time.time()-t0:.0f}s", flush=True)
            yield ev
    feed.events = events

    import shutil
    shutil.rmtree(WORK_DIR, ignore_errors=True)
    orch = Orchestrator(settings, feed, syms, index_symbol=INDEX, max_qty=1,
                        journal_dir=WORK_DIR)
    taps: list = []
    tmap: dict = {}
    for pipe in orch.pipelines.values():
        make_tap(pipe, taps, tmap, spec)
    orch.run()
    print(f"orchestrator done; raw taps={len(taps)}", flush=True)
    m5s = {s: orch.store._data.get(s, {}).get(Timeframe.M5, []) for s in syms}
    atrs = {s: atr_series(m5) for s, m5 in m5s.items()}
    pos = {s: {c.ts: j for j, c in enumerate(m5)} for s, m5 in m5s.items()}
    return taps, m5s, atrs, pos, tmap, spec


def rr_outcome(m5, i, d, entry, sl, atr) -> float:
    """Max favorable excursion in R (R = risk vs meta SL), EOD-truncated,
    walk ends the instant the SL wick is hit (strict). Mirrors rr50.py."""
    risk = max(abs(entry - sl), SL_ATR_FLOOR * atr)
    if risk <= 0:
        return 0.0
    day = m5[i].ts.date()
    max_r = 0.0
    for j in range(i + 1, len(m5)):
        cj = m5[j]
        if cj.ts.date() != day:
            break
        hi, lo = float(cj.high), float(cj.low)
        fav = (hi - entry) if d == 1 else (entry - lo)
        max_r = max(max_r, fav / risk)
        if (lo <= sl) if d == 1 else (hi >= sl):
            break
    return max_r


def vol_ratio(atrs_sym, i):
    cur = atrs_sym[i]
    prior = [float(a) for a in atrs_sym[max(0, i - VOL_LOOK):i] if a is not None]
    if cur is None or cur <= 0 or len(prior) < 5:
        return None
    med = st.median(prior)
    return float(cur) / med if med > 0 else None


def fwd_path(m5, i, session):
    """Native-5m forward path from bar i+1 to EOD (o,h,l,c float lists)."""
    o = []; h = []; l = []; cl = []
    for j in range(i + 1, len(m5)):
        b = m5[j]
        if b.ts.date() != session:
            break
        o.append(float(b.open)); h.append(float(b.high))
        l.append(float(b.low)); cl.append(float(b.close))
    return (o, h, l, cl) if o else None


def collect(taps, m5s, atrs, pos, tmap, spec) -> pd.DataFrame:
    rows = []
    t0 = time.time()
    for k, (sym, c5, atr, e, snap) in enumerate(taps):
        if k % 10000 == 0:
            print(f"  collect {k}/{len(taps)}  t={time.time()-t0:.0f}s", flush=True)
        d = e.direction.value
        if d == 0:
            continue
        i = pos[sym].get(c5.ts)
        if i is None:
            continue
        a = atrs[sym][i]
        if a is None or a <= 0:
            continue
        af = float(a)
        entry = float(c5.close)
        session = c5.ts.date()
        zlo, zhi = float(e.zone[0]), float(e.zone[1])
        sl = e.meta.get("sl")
        sl = (zlo if d == 1 else zhi) if sl is None else float(sl)
        risk = max(abs(entry - sl), SL_ATR_FLOOR * af)
        path = fwd_path(m5s[sym], i, session)
        if path is None:                    # signal on last bar of session
            continue
        o, h, l, cl = path
        max_r = rr_outcome(m5s[sym], i, d, entry, sl, af)
        oc = outcome(m5s[sym], i, d, a)
        ev = e.meta.get("event", "")
        b_hit, _ = baseline(m5s[sym], atrs[sym], i, d, spec,
                            f"{sym}|{c5.ts.isoformat()}|{e.detector}|{ev}")

        pdir = _PHASE_DIR.get(snap["idx_phase"], 0)
        wyck = "none" if pdir == 0 else ("aligned" if pdir == d else "counter")
        slo, shi = snap["sess_lo"], snap["sess_hi"]
        pd_pos = ((entry - slo) / (shi - slo)) if (slo is not None and shi is not None
                                                  and shi > slo) else None
        if pd_pos is None:
            pd_cls = "na"
        else:
            fav = (pd_pos <= 0.5) if d == 1 else (pd_pos >= 0.5)
            pd_cls = "favorable" if fav else "unfavorable"
        mn = snap["m15_net_atr"]
        if mn is None or abs(mn) < 0.5:
            htf = "flat" if mn is not None else "na"
        else:
            htf = "align" if (1 if mn > 0 else -1) == d else "counter"
        vr = vol_ratio(atrs[sym], i)
        vol = "na" if vr is None else ("expansion" if vr >= 1.0 else "contraction")
        template = tmap.get((sym, c5.ts), "NA")

        rows.append(dict(
            detector=e.detector, event=ev, symbol=sym,
            session=session.isoformat(), ts=c5.ts.isoformat(), direction=d,
            entry=entry, sl=sl, risk=risk, atr=af, zone_lo=zlo, zone_hi=zhi,
            strength=float(e.strength), max_r=max_r,
            hit=oc["hit"], b_hit=None if b_hit is None else float(b_hit),
            mfe=oc["mfe"], mae=oc["mae"],
            template=template, idx_phase=snap["idx_phase"], wyck=wyck,
            pd_pos=pd_pos, pd_cls=pd_cls, m15_net_atr=mn, htf=htf,
            vol_ratio=vr, vol=vol, tb=snap["tb"],
            n_path=len(o), po=o, ph=h, pl=l, pc=cl))
    return pd.DataFrame(rows)


def main():
    taps, m5s, atrs, pos, tmap, spec = drive()
    df = collect(taps, m5s, atrs, pos, tmap, spec)
    df.to_parquet(OUT_PATH, index=False)
    print(f"signals captured: {len(df)}  -> {OUT_PATH}")
    if len(df):
        print(df.groupby("detector").size().to_string())
        print("\ntemplate dist:\n", df["template"].value_counts().to_string())
        print("sessions:", df["session"].nunique(), df["session"].min(),
              "->", df["session"].max())
        print("symbols:", df["symbol"].nunique())


if __name__ == "__main__":
    main()
