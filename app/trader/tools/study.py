"""Detector-accuracy study: does each detector's evidence predict price?

Drives the REAL Orchestrator/SymbolPipeline flow (store -> levels -> detect
-> extend, session resets included) with every registered detector enabled,
tapping each stock pipeline's ``registry.run_all`` to log EVERY Evidence
with a market snapshot (bar, close, ATR). Outcomes come post-run from the
final M5 series:

- fwd@6/12/24: close-to-close move in DIRECTION units of ATR (NEUTRAL:
  absolute move), None past EOD;
- MFE/MAE: in-direction max favorable/adverse excursion over the next 24
  bars, EOD-truncated (NEUTRAL: up/down excursion);
- hit: MFE >= 1*ATR before MAE >= 1*ATR walking bar by bar; both crossing in
  the same bar counts as loss (conservative). Ternary hit/loss/undecided
  (window or EOD exhausted); NEUTRAL evidence is "na".

Baseline per evidence: 20 bars sampled (with replacement, crc32-seeded by
symbol|ts|detector|event -> deterministic) from the same session's same
30-min bucket, same outcome calc with each bar's own ATR. Detector edge =
hit_rate - baseline hit_rate.
"""

from __future__ import annotations

import random
import shutil
import zlib
from decimal import Decimal
from pathlib import Path

import numpy as np
import pandas as pd

from trader.config import Settings
from trader.detectors.base import REGISTRY
from trader.detectors.timestats import bucket_index
from trader.engine.pipeline import Orchestrator
from trader.models.candle import Candle, Timeframe

_HORIZONS, _WINDOW, _BUCKET_MIN, _K, _PERIOD = (6, 12, 24), 24, 30, 20, 14
_COLS = ["symbol", "session", "ts", "detector", "event", "direction",
         "strength", "zone_lo", "zone_hi", "price", "atr",
         "fwd6", "fwd12", "fwd24", "mfe", "mae", "hit", "b_hit", "b_fwd12"]


def atr_series(m5: list[Candle]) -> list[Decimal | None]:
    """Trailing ATR(14) per bar (SMA of TR over bars i-13..i), matching
    ``StockContext.atr`` at that bar's close; None until 15 bars exist."""
    trs = [max(c.high - c.low, abs(c.high - p.close), abs(c.low - p.close))
           for p, c in zip(m5, m5[1:])]
    return [sum(trs[i - _PERIOD:i]) / _PERIOD if i >= _PERIOD else None
            for i in range(len(m5))]


def outcome(m5: list[Candle], i: int, d: int, atr: Decimal) -> dict:
    """Forward outcomes for a signal at bar i in direction d (1/-1/0)."""
    ref, day = m5[i].close, m5[i].ts.date()
    win = [c for c in m5[i + 1:i + 1 + _WINDOW] if c.ts.date() == day]
    f = lambda v: float(v / atr)                                # noqa: E731
    out = {}
    for k in _HORIZONS:
        ok = i + k < len(m5) and m5[i + k].ts.date() == day
        mv = m5[i + k].close - ref if ok else None
        out[f"fwd{k}"] = None if mv is None else f(abs(mv) if d == 0 else mv * d)
    up = [max(c.high - ref, Decimal(0)) for c in win] or [Decimal(0)]
    dn = [max(ref - c.low, Decimal(0)) for c in win] or [Decimal(0)]
    fav, adv = (dn, up) if d < 0 else (up, dn)      # NEUTRAL: up/down excursion
    out["mfe"], out["mae"] = f(max(fav)), f(max(adv))
    hit = "na" if d == 0 else "undecided"
    for c in win if d else []:
        fv = c.high - ref if d > 0 else ref - c.low
        av = ref - c.low if d > 0 else c.high - ref
        if av >= atr:
            hit = "loss"; break                                 # noqa: E702
        if fv >= atr:
            hit = "hit"; break                                  # noqa: E702
    out["hit"] = hit
    return out


def baseline(m5, atrs, i: int, d: int, spec, key: str):
    """(hit_rate, mean fwd12) over _K seeded random same-session,
    same-30-min-bucket bars, each scored with its own ATR."""
    day, b = m5[i].ts.date(), bucket_index(m5[i].ts, spec, _BUCKET_MIN)
    cands = [j for j, c in enumerate(m5)
             if j != i and c.ts.date() == day and atrs[j] is not None
             and bucket_index(c.ts, spec, _BUCKET_MIN) == b]
    if not cands:
        return None, None
    rng = random.Random(zlib.crc32(key.encode()))
    outs = [outcome(m5, j, d, atrs[j])
            for j in (rng.choice(cands) for _ in range(_K))]
    hits = [o["hit"] for o in outs if o["hit"] != "na"]
    fwds = [o["fwd12"] for o in outs if o["fwd12"] is not None]
    return (sum(h == "hit" for h in hits) / len(hits) if hits else None,
            sum(fwds) / len(fwds) if fwds else None)


def _tap(pipe, sink: list) -> None:
    """Wrap the pipeline's registry.run_all to log every Evidence with its
    closed-M5 bar + ATR snapshot; behavior is otherwise untouched."""
    orig = pipe.registry.run_all

    def run_all(ctx):
        evs = orig(ctx)
        if evs:
            c5, atr = ctx.candles.last(1, Timeframe.M5)[-1], ctx.atr(Timeframe.M5)
            sink.extend((pipe.symbol, c5, atr, e) for e in evs)
        return evs

    pipe.registry.run_all = run_all


def run_study(settings: Settings, feed, symbols: list[str],
              index: str | None, out_dir: Path,
              enable_only: list[str] | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run the study; write out_dir/evidence.parquet (csv fallback) +
    summary.csv; return (evidence df, per-(detector,event) summary df).

    ``enable_only``: measure EXACTLY this detector set (in this order) instead
    of force-enabling every registered detector. Use it to avoid cross-detector
    contamination via shared ``ctx.levels`` (e.g. ob_lux + orderblock both
    writing OB_* levels doubles the pool); the enabled set IS saved next to the
    output for provenance. None -> the legacy all-detectors behavior."""
    out_dir = Path(out_dir)
    s = settings.model_copy(deep=True)
    if enable_only is not None:
        unknown = [n for n in enable_only if n not in REGISTRY]
        if unknown:
            raise ValueError(f"unknown detector(s): {unknown}; known: {sorted(REGISTRY)}")
        s.detectors.enabled = list(enable_only)
    else:
        s.detectors.enabled += [n for n in sorted(REGISTRY)
                                if n not in s.detectors.enabled]
    work = out_dir / "work"                       # scratch journal, wiped
    shutil.rmtree(work, ignore_errors=True)
    orch = Orchestrator(s, feed, symbols, index_symbol=index, max_qty=1,
                        journal_dir=work)
    taps: list = []
    for pipe in orch.pipelines.values():
        _tap(pipe, taps)
    orch.run()
    spec = s.market_spec()
    m5s = {sym: orch.store._data.get(sym, {}).get(Timeframe.M5, [])
           for sym in symbols}
    atrs = {sym: atr_series(m5) for sym, m5 in m5s.items()}
    pos = {sym: {c.ts: j for j, c in enumerate(m5)} for sym, m5 in m5s.items()}
    rows = []
    for sym, c5, atr, e in taps:
        i = pos[sym].get(c5.ts)
        ev = e.meta.get("event", "")
        row = dict(symbol=sym, session=c5.ts.date().isoformat(),
                   ts=c5.ts.isoformat(), detector=e.detector, event=ev,
                   direction=e.direction.name, strength=float(e.strength),
                   zone_lo=float(e.zone[0]), zone_hi=float(e.zone[1]),
                   price=float(c5.close), atr=None if atr is None else float(atr),
                   fwd6=None, fwd12=None, fwd24=None, mfe=None, mae=None,
                   hit="na", b_hit=None, b_fwd12=None)
        if i is not None and atr is not None:
            row |= outcome(m5s[sym], i, e.direction.value, atr)
            row["b_hit"], row["b_fwd12"] = baseline(
                m5s[sym], atrs[sym], i, e.direction.value, spec,
                f"{sym}|{c5.ts.isoformat()}|{e.detector}|{ev}")
        rows.append(row)
    df = pd.DataFrame(rows, columns=_COLS)
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        df.to_parquet(out_dir / "evidence.parquet", index=False)
    except Exception:
        df.to_csv(out_dir / "evidence.csv", index=False)
    sdf = summarize(df)
    sdf.to_csv(out_dir / "summary.csv", index=False)
    return df, sdf


def _terciles(g: pd.DataFrame) -> str:
    """Edge per strength tercile (weak/mid/strong), '-' when unsplittable."""
    if len(g) < 3 or g["strength"].nunique() < 2:
        return "-"
    q = g.sort_values(["strength", "ts"], kind="mergesort")
    parts = [q.iloc[ix] for ix in np.array_split(np.arange(len(q)), 3)]
    return "/".join(
        f"{(p['hit'] == 'hit').mean() - p['b_hit'].mean():+.2f}"
        if p["b_hit"].notna().any() else "-" for p in parts)


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    """Per-(detector, event): n, hit%, baseline%, edge, mean fwd12/MFE/MAE
    (ATR units), edge by strength tercile. Sorted by edge desc, NEUTRAL-only
    groups (hit 'na') last with edge NaN."""
    rows = []
    for (det, ev), g in df[df["atr"].notna()].groupby(["detector", "event"]):
        d = g[g["hit"] != "na"]                   # directional evidence only
        hit = (d["hit"] == "hit").mean() if len(d) else np.nan
        base = d["b_hit"].mean() if len(d) else np.nan
        rows.append(dict(
            detector=det, event=ev, n=len(g), hit=hit, base=base,
            edge=hit - base, fwd12=g["fwd12"].mean(), mfe=g["mfe"].mean(),
            mae=g["mae"].mean(), edge_by_strength=_terciles(d)))
    return (pd.DataFrame(rows, columns=["detector", "event", "n", "hit", "base",
                                        "edge", "fwd12", "mfe", "mae",
                                        "edge_by_strength"])
            .sort_values(["edge", "detector", "event"], ascending=[False, True, True],
                         na_position="last").reset_index(drop=True))
