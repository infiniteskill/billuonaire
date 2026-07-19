#!/usr/bin/env python3
"""Strict, causal, same-lineage SMC event study.

All inputs are read-only.  Every output is written below this file's
``output/`` directory.  Definitions and selection rules are frozen in
PREREGISTRATION.json.
"""
from __future__ import annotations

import argparse
import json
import math
import zlib
from dataclasses import asdict, dataclass
from datetime import time
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DATA = ROOT / "data" / "long5m"
OUT = HERE / "output"
TICK = 0.05
COSTS_BPS = (0, 3, 6, 10, 15)
EPS = 1e-10


@dataclass
class Root:
    id: str
    kind: str
    side: int                 # +1 high-side liquidity, -1 low-side liquidity
    level: float
    available_idx: int        # known after this raw M5 bar
    expiry_idx: int
    prominence: float
    important: bool
    first_sweep_idx: int | None = None


@dataclass
class Prepared:
    symbol: str
    bars: pd.DataFrame
    h1: pd.DataFrame
    atr5: np.ndarray
    atrh1: np.ndarray
    m5_swings: list[dict]
    h1_swings: list[dict]
    roots: list[Root]
    invalid_rows: int


def atr_sma(high: np.ndarray, low: np.ndarray, close: np.ndarray, n: int = 14) -> np.ndarray:
    prev = np.roll(close, 1)
    tr = np.maximum(high - low, np.maximum(np.abs(high - prev), np.abs(low - prev)))
    if len(tr):
        tr[0] = high[0] - low[0]
    return pd.Series(tr).rolling(n, min_periods=n).mean().to_numpy(float)


def strict_swings(high: np.ndarray, low: np.ndarray, atr: np.ndarray,
                  wing: int = 2) -> list[dict]:
    """Strict N/N fractals; availability is pivot+N, never pivot time."""
    out: list[dict] = []
    for m in range(wing, len(high) - wing):
        conf = m + wing
        a = atr[conf]
        if (high[m] > max(high[m - wing:m])
                and high[m] > max(high[m + 1:m + wing + 1])):
            prom = (high[m] - np.min(low[m:conf + 1])) / a if np.isfinite(a) and a > 0 else np.nan
            out.append({"side": 1, "pivot": m, "conf": conf,
                        "level": float(high[m]), "prominence": float(prom)})
        if (low[m] < min(low[m - wing:m])
                and low[m] < min(low[m + 1:m + wing + 1])):
            prom = (np.max(high[m:conf + 1]) - low[m]) / a if np.isfinite(a) and a > 0 else np.nan
            out.append({"side": -1, "pivot": m, "conf": conf,
                        "level": float(low[m]), "prominence": float(prom)})
    return sorted(out, key=lambda x: (x["conf"], x["pivot"], x["side"]))


def _parse_ts(series: pd.Series) -> pd.Series:
    return (pd.to_datetime(series, utc=True)
              .dt.tz_convert("Asia/Kolkata")
              .dt.tz_localize(None))


def prepare(path: Path) -> Prepared:
    symbol = path.stem
    raw = pd.read_csv(path)
    raw["ts"] = _parse_ts(raw["ts"])
    for c in ("open", "high", "low", "close", "volume"):
        raw[c] = pd.to_numeric(raw[c], errors="coerce")
    finite = np.isfinite(raw[["open", "high", "low", "close"]]).all(axis=1)
    valid = (finite & (raw["low"] <= raw[["open", "close"]].min(axis=1))
             & (raw["high"] >= raw[["open", "close"]].max(axis=1))
             & (raw["high"] >= raw["low"]) & (raw["close"] > 0))
    invalid_rows = int((~valid).sum())
    b = raw.loc[valid].sort_values("ts").drop_duplicates("ts", keep="last").reset_index(drop=True)
    tod = b["ts"].dt.time
    b = b.loc[(tod >= time(9, 15)) & (tod <= time(15, 25))].reset_index(drop=True)
    b["idx"] = np.arange(len(b), dtype=int)
    b["session"] = b["ts"].dt.strftime("%Y-%m-%d")
    b["week_key"] = (b["ts"].dt.isocalendar().year.astype(int) * 100
                     + b["ts"].dt.isocalendar().week.astype(int))
    minute = b["ts"].dt.hour * 60 + b["ts"].dt.minute - (9 * 60 + 15)
    b["h1_bucket"] = np.minimum((minute // 60).astype(int), 5)

    h, l, c = (b[x].to_numpy(float) for x in ("high", "low", "close"))
    atr5 = atr_sma(h, l, c)
    b["atr5"] = atr5

    h1 = (b.groupby(["session", "h1_bucket"], sort=True)
            .agg(open=("open", "first"), high=("high", "max"),
                 low=("low", "min"), close=("close", "last"),
                 start_idx=("idx", "min"), end_idx=("idx", "max"),
                 ts=("ts", "last"))
            .reset_index())
    hh, hl, hc = (h1[x].to_numpy(float) for x in ("high", "low", "close"))
    atrh1 = atr_sma(hh, hl, hc)
    h1["atr"] = atrh1

    # V2 feasibility amendment: H1 remains strict 2/2; internal M5 MSS uses
    # strict 1/1 pivots because v1 produced zero entries before payoff.
    m5_swings = strict_swings(h, l, atr5, wing=1)
    h1_swings = strict_swings(hh, hl, atrh1)
    roots: list[Root] = []
    h1_end = h1["end_idx"].to_numpy(int)
    for n, sw in enumerate(h1_swings):
        avail = int(h1_end[sw["conf"]])
        prom = sw["prominence"]
        roots.append(Root(
            id=f"{symbol}-H1{'H' if sw['side'] == 1 else 'L'}-{n}",
            kind="H1H" if sw["side"] == 1 else "H1L",
            side=int(sw["side"]), level=float(sw["level"]),
            available_idx=avail, expiry_idx=len(b) - 1,
            prominence=prom,
            important=bool(np.isfinite(prom) and prom >= 0.75),
        ))

    sess = (b.groupby("session", sort=True)
             .agg(first=("idx", "min"), last=("idx", "max"),
                  high=("high", "max"), low=("low", "min"),
                  week=("week_key", "first"))
             .reset_index())
    for j in range(1, len(sess)):
        cur, prev = sess.iloc[j], sess.iloc[j - 1]
        for tag, side, level in (("PDH", 1, prev.high), ("PDL", -1, prev.low)):
            roots.append(Root(
                id=f"{symbol}-{tag}-{cur.session}", kind=tag, side=side,
                level=float(level), available_idx=int(cur["first"]) - 1,
                expiry_idx=int(cur["last"]), prominence=np.nan, important=True,
            ))

    weeks = list(dict.fromkeys(sess["week"].astype(int).tolist()))
    for wi in range(1, len(weeks)):
        prev_w, cur_w = weeks[wi - 1], weeks[wi]
        prev = sess[sess.week == prev_w]
        cur = sess[sess.week == cur_w]
        if prev.empty or cur.empty:
            continue
        first, last = int(cur["first"].min()), int(cur["last"].max())
        for tag, side, level in (("PWH", 1, prev.high.max()), ("PWL", -1, prev.low.min())):
            roots.append(Root(
                id=f"{symbol}-{tag}-{cur_w}", kind=tag, side=side,
                level=float(level), available_idx=first - 1, expiry_idx=last,
                prominence=np.nan, important=True,
            ))
    return Prepared(symbol, b, h1, atr5, atrh1, m5_swings, h1_swings, roots, invalid_rows)


def _root_sweeps(p: Prepared) -> list[dict]:
    b = p.bars
    hi, lo, cl = (b[x].to_numpy(float) for x in ("high", "low", "close"))
    sessions = b["session"].to_numpy(str)
    out: list[dict] = []
    for r in p.roots:
        start = max(r.available_idx + 1, 0)
        end = min(r.expiry_idx, len(b) - 1)
        for i in range(start, end + 1):
            swept = hi[i] >= r.level + TICK - EPS if r.side == 1 else lo[i] <= r.level - TICK + EPS
            if not swept:
                continue
            r.first_sweep_idx = i
            last = min(i + 3, end)
            reclaim = None
            for j in range(i, last + 1):
                if sessions[j] != sessions[i]:
                    break
                if (cl[j] < r.level if r.side == 1 else cl[j] > r.level):
                    reclaim = j
                    break
            if reclaim is not None:
                extreme = float(np.max(hi[i:reclaim + 1]) if r.side == 1
                                else np.min(lo[i:reclaim + 1]))
                out.append({
                    "root_id": r.id, "root_kind": r.kind, "root_side": r.side,
                    "root_level": r.level, "root_prominence": r.prominence,
                    "root_important": r.important, "sweep_idx": i,
                    "reclaim_idx": reclaim, "sweep_extreme": extreme,
                    "direction": -r.side,
                })
            break                              # first sweep consumes this pool
    return out


def _latest_unbroken_h1_swing(p: Prepared, side: int, known_by: int) -> dict | None:
    """Newest target swing known before the root episode and not yet broken."""
    c = p.h1["close"].to_numpy(float)
    for sw in reversed(p.h1_swings):
        if sw["side"] != side or sw["conf"] > known_by:
            continue
        a, z = sw["conf"] + 1, known_by + 1
        prior = c[a:z]
        broken = bool(np.any(prior > sw["level"])) if side == 1 else bool(np.any(prior < sw["level"]))
        if not broken:
            return sw
    return None


def _structure_and_parents(p: Prepared, roots: list[dict]) -> tuple[list[dict], dict]:
    h1 = p.h1
    ho, hh, hl, hc = (h1[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    hend = h1["end_idx"].to_numpy(int)
    parents: list[dict] = []
    funnel = {"root_reclaims": len(roots), "h1_structure_breaks": 0,
              "parent_fvg": 0, "parent_ob": 0}
    for e in roots:
        j0 = int(np.searchsorted(hend, e["reclaim_idx"], side="left"))
        if j0 >= len(h1) - 1:
            continue
        d = int(e["direction"])
        target_side = 1 if d == 1 else -1
        sw = _latest_unbroken_h1_swing(p, target_side, j0)
        if sw is None:
            continue
        broke_at = None
        for j in range(j0 + 1, min(j0 + 9, len(h1))):
            a = p.atrh1[j]
            rng = hh[j] - hl[j]
            if not np.isfinite(a) or a <= 0 or rng <= 0:
                continue
            crossed = (hc[j] >= sw["level"] + 0.05 * a if d == 1
                       else hc[j] <= sw["level"] - 0.05 * a)
            body = abs(hc[j] - ho[j])
            loc = (hc[j] - hl[j]) / rng if d == 1 else (hh[j] - hc[j]) / rng
            if crossed and body >= 0.60 * a and loc >= 0.65:
                broke_at = j
                break
        if broke_at is None:
            continue
        j = broke_at
        funnel["h1_structure_breaks"] += 1
        base = {
            **e, "h1_reclaim_bucket": j0, "h1_break_idx": j,
            "h1_break_end_idx": int(hend[j]), "h1_break_swing_level": float(sw["level"]),
            "h1_break_swing_pivot": int(sw["pivot"]), "h1_break_swing_conf": int(sw["conf"]),
            "h1_break_atr": float(p.atrh1[j]),
            "lineage_id": f"{e['root_id']}|H1B{j}",
        }
        fvg = None
        if j >= 2:
            if d == 1 and hl[j] - hh[j - 2] >= 0.10 * p.atrh1[j]:
                fvg = (float(hh[j - 2]), float(hl[j]))
            elif d == -1 and hl[j - 2] - hh[j] >= 0.10 * p.atrh1[j]:
                fvg = (float(hh[j]), float(hl[j - 2]))
        if fvg is not None:
            parents.append({**base, "parent_type": "FVG", "parent_lo": fvg[0],
                            "parent_hi": fvg[1], "parent_origin_h1": j - 1,
                            "parent_primary": True})
            funnel["parent_fvg"] += 1

        ob_idx = None
        for k in range(j - 1, j0 - 1, -1):
            opposite = hc[k] < ho[k] if d == 1 else hc[k] > ho[k]
            if opposite:
                ob_idx = k
                break
        if ob_idx is not None:
            parents.append({
                **base, "parent_type": "OB",
                "parent_lo": float(hl[ob_idx]), "parent_hi": float(hh[ob_idx]),
                "parent_origin_h1": int(ob_idx), "parent_primary": fvg is None,
            })
            funnel["parent_ob"] += 1
    return parents, funnel


def _parent_first_revisit(p: Prepared, parent: dict, max_bars: int = 90) -> dict | None:
    b = p.bars
    lo, hi, cl = (b[x].to_numpy(float) for x in ("low", "high", "close"))
    d = int(parent["direction"])
    zlo, zhi = parent["parent_lo"], parent["parent_hi"]
    start = parent["h1_break_end_idx"] + 1
    for i in range(start, min(start + max_bars, len(b))):
        invalid = cl[i] < zlo if d == 1 else cl[i] > zhi
        overlap = lo[i] <= zhi and hi[i] >= zlo
        if invalid:
            return None                       # invalidation precedes usable touch
        if overlap:
            return {**parent, "parent_touch_idx": i,
                    "parent_delay_actual": i - parent["h1_break_end_idx"]}
    return None


def _latest_unbroken_m5_swing(p: Prepared, side: int, before: int,
                              parent_confirm: int, revisit: int) -> dict | None:
    c = p.bars["close"].to_numpy(float)
    for sw in reversed(p.m5_swings):
        recent_enough = (sw["pivot"] > parent_confirm
                         or sw["pivot"] >= revisit - 24)
        if sw["side"] != side or sw["conf"] >= before or not recent_enough:
            continue
        prior = c[sw["conf"] + 1:before]
        broken = bool(np.any(prior > sw["level"])) if side == 1 else bool(np.any(prior < sw["level"]))
        if not broken:
            return sw
    return None


def _children(p: Prepared, parent: dict) -> list[dict]:
    b = p.bars
    o, h, l, c = (b[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    r = int(parent["parent_touch_idx"])
    d = int(parent["direction"])
    p_lo, p_hi = parent["parent_lo"], parent["parent_hi"]
    for j in range(r + 1, min(r + 13, len(b))):
        if b.session.iloc[j] != b.session.iloc[r]:
            break
        a = p.atr5[j]
        rng = h[j] - l[j]
        if not np.isfinite(a) or a <= 0 or rng <= 0:
            continue
        # Parent must remain structurally live through M5 confirmation.
        if (c[j] < p_lo if d == 1 else c[j] > p_hi):
            return []
        target_side = 1 if d == 1 else -1
        sw = _latest_unbroken_m5_swing(
            p, target_side, j, int(parent["h1_break_end_idx"]), r)
        if sw is None:
            continue
        crossed = (c[j] >= sw["level"] + 0.05 * a if d == 1
                   else c[j] <= sw["level"] - 0.05 * a)
        loc = (c[j] - l[j]) / rng if d == 1 else (h[j] - c[j]) / rng
        if not (crossed and abs(c[j] - o[j]) >= 0.60 * a and loc >= 0.65):
            continue
        base = {
            **parent, "m5_mss_idx": j, "m5_mss_swing_level": float(sw["level"]),
            "m5_mss_swing_pivot": int(sw["pivot"]), "m5_mss_swing_conf": int(sw["conf"]),
            "m5_mss_atr": float(a), "mss_id": f"{parent['lineage_id']}|M5B{j}",
        }
        found: list[dict] = []
        fvg = None
        if j - 2 >= r:
            if d == 1 and l[j] - h[j - 2] >= 0.10 * a:
                fvg = (float(h[j - 2]), float(l[j]))
            elif d == -1 and l[j - 2] - h[j] >= 0.10 * a:
                fvg = (float(h[j]), float(l[j - 2]))
        if fvg is not None and p_lo <= (fvg[0] + fvg[1]) / 2 <= p_hi:
            found.append({**base, "child_type": "FVG", "child_lo": fvg[0],
                          "child_hi": fvg[1], "child_origin_idx": j - 1,
                          "child_primary": True})

        ob_idx = None
        for k in range(j - 1, r - 1, -1):
            opposite = c[k] < o[k] if d == 1 else c[k] > o[k]
            if opposite:
                ob_idx = k
                break
        if ob_idx is not None:
            z = (float(l[ob_idx]), float(h[ob_idx]))
            if p_lo <= sum(z) / 2 <= p_hi:
                found.append({**base, "child_type": "OB", "child_lo": z[0],
                              "child_hi": z[1], "child_origin_idx": int(ob_idx),
                              "child_primary": fvg is None})
        return found                              # first valid MSS only
    return []


def _child_fill(p: Prepared, child: dict) -> dict | None:
    b = p.bars
    h, l, c = (b[x].to_numpy(float) for x in ("high", "low", "close"))
    j, d = int(child["m5_mss_idx"]), int(child["direction"])
    zlo, zhi = child["child_lo"], child["child_hi"]
    entry = (zlo + zhi) / 2
    for i in range(j + 1, min(j + 7, len(b))):
        if b.session.iloc[i] != b.session.iloc[j]:
            break
        invalid = c[i] < zlo if d == 1 else c[i] > zhi
        crosses = l[i] <= entry <= h[i]
        if invalid:
            return None
        if crosses:
            if b.ts.iloc[i].time() > time(14, 45):
                return None
            return {**child, "fill_idx": i, "entry": float(entry),
                    "child_delay_actual": i - j,
                    "session": b.session.iloc[i], "ts": b.ts.iloc[i]}
    return None


def _opposing_target(p: Prepared, fill: dict) -> tuple[float, str] | None:
    d, entry, i = int(fill["direction"]), float(fill["entry"]), int(fill["fill_idx"])
    wanted_side = 1 if d == 1 else -1
    candidates = []
    for r in p.roots:
        if r.side != wanted_side or r.available_idx >= i or r.expiry_idx < i:
            continue
        # A sweep on the fill bar is still an eligible target; earlier is not.
        if r.first_sweep_idx is not None and r.first_sweep_idx < i:
            continue
        if (d == 1 and r.level > entry) or (d == -1 and r.level < entry):
            candidates.append(r)
    if not candidates:
        return None
    target = min(candidates, key=lambda r: abs(r.level - entry))
    return float(target.level), target.id


def _session_end_idx(b: pd.DataFrame, i: int) -> int:
    session = b.session.iloc[i]
    idx = b.index[(b.session == session) & (b.index >= i)]
    return int(idx.max())


def simulate(p: Prepared, fill: dict, stop: float, target: float,
             cost_bps: float, target_first: bool = False) -> dict | None:
    b = p.bars
    d, i, entry = int(fill["direction"]), int(fill["fill_idx"]), float(fill["entry"])
    dist = d * (entry - stop)
    if dist <= 0:
        return None
    end = _session_end_idx(b, i)
    o = b.open.to_numpy(float)
    h = b.high.to_numpy(float)
    l = b.low.to_numpy(float)
    c = b.close.to_numpy(float)
    exit_px, exit_kind, exit_i = c[end], "eod", end
    ambiguous = False
    for k in range(i, end + 1):
        sh = l[k] <= stop if d == 1 else h[k] >= stop
        th = h[k] >= target if d == 1 else l[k] <= target
        if sh and th:
            ambiguous = True
        if sh and (not th or not target_first):
            if k > i and ((d == 1 and o[k] < stop) or (d == -1 and o[k] > stop)):
                exit_px = o[k]                    # adverse gap-through
            else:
                exit_px = stop
            exit_kind, exit_i = "stop", k
            break
        if th:
            exit_px, exit_kind, exit_i = target, "target", k
            break
    gross_r = d * (exit_px - entry) / dist
    net_r = gross_r - (cost_bps / 10000.0) * entry / dist
    path_hi = h[i:end + 1]
    path_lo = l[i:end + 1]
    mfe = ((np.max(path_hi) - entry) if d == 1 else (entry - np.min(path_lo))) / dist
    mae = ((entry - np.min(path_lo)) if d == 1 else (np.max(path_hi) - entry)) / dist
    return {
        "stop": float(stop), "stop_dist": float(dist), "target": float(target),
        "target_r": float(d * (target - entry) / dist),
        "exit_px": float(exit_px), "exit_kind": exit_kind, "exit_idx": int(exit_i),
        "gross_r": float(gross_r), "net_r": float(net_r),
        "mfe_r": float(mfe), "mae_r": float(mae), "ambiguous": bool(ambiguous),
    }


def _trade_row(p: Prepared, fill: dict) -> dict | None:
    tgt = _opposing_target(p, fill)
    if tgt is None:
        return None
    target, target_id = tgt
    d, entry, i = int(fill["direction"]), float(fill["entry"]), int(fill["fill_idx"])
    a = p.atr5[i]
    if not np.isfinite(a) or a <= 0:
        return None
    child_far = fill["child_lo"] if d == 1 else fill["child_hi"]
    sweep_far = float(fill["sweep_extreme"])
    stops = {
        "child": float(child_far - d * 0.10 * a),
        "sweep": float(sweep_far - d * 0.10 * a),
    }
    row = {**fill, "symbol": p.symbol, "target": target, "target_id": target_id}
    any_valid = False
    for sk, raw_stop in stops.items():
        dist = d * (entry - raw_stop)
        if dist < 0.25 * a:
            raw_stop = entry - d * 0.25 * a
            dist = 0.25 * a
        if dist <= 0 or dist > 4.0 * a:
            row[f"valid_{sk}"] = False
            continue
        primary = simulate(p, fill, raw_stop, target, 6, target_first=False)
        optimistic = simulate(p, fill, raw_stop, target, 6, target_first=True)
        if primary is None:
            row[f"valid_{sk}"] = False
            continue
        any_valid = True
        row[f"valid_{sk}"] = True
        for key, value in primary.items():
            row[f"{key}_{sk}"] = value
        row[f"net_r_opt_{sk}"] = optimistic["net_r"] if optimistic else np.nan
        for cbps in COSTS_BPS:
            sim = simulate(p, fill, raw_stop, target, cbps, target_first=False)
            row[f"net_r_{cbps}bps_{sk}"] = sim["net_r"] if sim else np.nan
    return row if any_valid else None


def process_symbol(path: Path) -> tuple[list[dict], dict, dict]:
    p = prepare(path)
    root_events = _root_sweeps(p)
    parents, funnel = _structure_and_parents(p, root_events)
    funnel.update({
        "symbol": p.symbol, "roots": len(p.roots),
        "root_sweeps": sum(r.first_sweep_idx is not None for r in p.roots),
        "important_root_reclaims": sum(e["root_important"] for e in root_events),
        "parent_first_revisits": 0, "m5_mss": 0, "children": 0,
        "child_fills": 0, "targeted_trades": 0,
    })
    rows: list[dict] = []
    seen_mss = set()
    for parent in parents:
        revisit = _parent_first_revisit(p, parent)
        if revisit is None:
            continue
        funnel["parent_first_revisits"] += 1
        children = _children(p, revisit)
        if children:
            mss = children[0]["mss_id"]
            if mss not in seen_mss:
                seen_mss.add(mss)
                funnel["m5_mss"] += 1
        funnel["children"] += len(children)
        for child in children:
            filled = _child_fill(p, child)
            if filled is None:
                continue
            funnel["child_fills"] += 1
            row = _trade_row(p, filled)
            if row is not None:
                funnel["targeted_trades"] += 1
                rows.append(row)
    audit = {
        "symbol": p.symbol, "bars": len(p.bars), "h1_bars": len(p.h1),
        "invalid_rows": p.invalid_rows, "m5_swings": len(p.m5_swings),
        "h1_swings": len(p.h1_swings), "roots": len(p.roots),
        "root_events": len(root_events), "parents": len(parents),
    }
    return rows, funnel, audit


def _policies() -> list[dict]:
    return json.loads((HERE / "PREREGISTRATION.json").read_text())["candidate_policies_dev_only"]


def apply_policy(candidates: pd.DataFrame, policy: dict) -> pd.DataFrame:
    if candidates.empty:
        return candidates.copy()
    q = candidates.copy()
    if policy["root"] == "important_or_PD_PW":
        q = q[q.root_important]
    psel = policy["parent"]
    if psel == "FVG_then_OB":
        q = q[q.parent_primary]
    else:
        q = q[q.parent_type == psel]
    csel = policy["child"]
    if csel == "FVG_then_OB":
        q = q[q.child_primary]
    else:
        q = q[q.child_type == csel]
    q = q[(q.parent_delay_actual >= int(policy["parent_delay"]))
          & (q.child_delay_actual >= int(policy["child_delay"]))]
    stop = policy["stop"]
    q = q[q[f"valid_{stop}"].fillna(False)]
    q = q[q[f"target_r_{stop}"] >= float(policy["min_target_r"])]
    if q.empty:
        return q
    # No outcome-dependent ranking: earliest causal fill, deterministic IDs.
    q = (q.sort_values(["session", "symbol", "fill_idx", "root_id",
                        "parent_type", "child_type"])
           .drop_duplicates(["symbol", "session"], keep="first")
           .copy())
    standard = {
        "stop": f"stop_{stop}", "stop_dist": f"stop_dist_{stop}",
        "target_r": f"target_r_{stop}", "exit_kind": f"exit_kind_{stop}",
        "gross_r": f"gross_r_{stop}", "net_r": f"net_r_{stop}",
        "mfe_r": f"mfe_r_{stop}", "mae_r": f"mae_r_{stop}",
        "ambiguous": f"ambiguous_{stop}", "net_r_opt": f"net_r_opt_{stop}",
    }
    for out, src in standard.items():
        q[out] = q[src]
    for bps in COSTS_BPS:
        q[f"net_r_{bps}bps"] = q[f"net_r_{bps}bps_{stop}"]
    q["policy"] = policy["name"]
    return q


def basic_metrics(q: pd.DataFrame, col: str = "net_r") -> dict:
    if q.empty:
        return {
            "n": 0, "mean_net_r": np.nan, "median_net_r": np.nan,
            "win_pct": np.nan, "profit_factor": np.nan, "mean_gross_r": np.nan,
            "mfe_mae_ratio": np.nan, "ambiguous_pct": np.nan, "max_drawdown_r": np.nan,
        }
    x = q[col].to_numpy(float)
    pos, neg = x[x > 0].sum(), -x[x < 0].sum()
    curve = np.cumsum(x)
    peak = np.maximum.accumulate(np.r_[0.0, curve])
    dd = peak[1:] - curve
    return {
        "n": int(len(q)), "mean_net_r": float(np.mean(x)),
        "median_net_r": float(np.median(x)), "win_pct": float(np.mean(x > 0) * 100),
        "profit_factor": float(pos / neg) if neg > 0 else (math.inf if pos > 0 else np.nan),
        "mean_gross_r": float(q.gross_r.mean()),
        "mfe_mae_ratio": float(q.mfe_r.mean() / q.mae_r.mean()) if q.mae_r.mean() > 0 else np.nan,
        "ambiguous_pct": float(q.ambiguous.mean() * 100),
        "max_drawdown_r": float(np.max(dd)) if len(dd) else 0.0,
    }


def block_bootstrap_ci(q: pd.DataFrame, col: str = "net_r",
                       reps: int = 2000, seed: int = 240719) -> tuple[float, float]:
    if q.empty or q.session.nunique() < 2:
        return np.nan, np.nan
    groups = [g[col].to_numpy(float) for _, g in q.groupby("session", sort=True)]
    rng = np.random.default_rng(seed)
    means = np.empty(reps)
    for k in range(reps):
        picked = rng.integers(0, len(groups), len(groups))
        means[k] = np.concatenate([groups[j] for j in picked]).mean()
    return tuple(float(x) for x in np.quantile(means, [0.025, 0.975]))


def add_split_columns(df: pd.DataFrame, sessions: list[str]) -> tuple[pd.DataFrame, dict]:
    q = df.copy()
    cut_n = int(math.ceil(0.60 * len(sessions)))
    dev_sessions, hold_sessions = sessions[:cut_n], sessions[cut_n:]
    cut = dev_sessions[-1]
    q["time_dev"] = q.session <= cut
    q["symbol_fold"] = q.symbol.map(lambda s: zlib.crc32(s.encode()) % 3)
    q["symbol_dev"] = q.symbol_fold < 2
    mid = len(dev_sessions) // 2
    early_dev = set(dev_sessions[:mid])
    q["dev_time_half"] = np.where(q.session.isin(early_dev), 0, 1)
    return q, {
        "sessions": len(sessions), "time_cut": cut,
        "dev_sessions": dev_sessions, "holdout_sessions": hold_sessions,
        "symbol_holdout_rule": "crc32(symbol)%3 == 2",
    }


def development_selection(candidates: pd.DataFrame, sessions: list[str]) -> tuple[dict, pd.DataFrame]:
    rows = []
    policies = _policies()
    for policy in policies:
        q = apply_policy(candidates, policy)
        q, _ = add_split_columns(q, sessions)
        d = q[q.time_dev & q.symbol_dev]
        cells = {
            "TDEV0": d[d.dev_time_half == 0],
            "TDEV1": d[d.dev_time_half == 1],
            "SDEV0": d[d.symbol_fold == 0],
            "SDEV1": d[d.symbol_fold == 1],
        }
        row = {"policy": policy["name"], **basic_metrics(d)}
        for name, x in cells.items():
            row[f"n_{name}"] = len(x)
            row[f"net_{name}"] = x.net_r.mean() if len(x) else np.nan
        row["qualifies"] = bool(
            len(d) >= 80 and all(len(x) > 0 and x.net_r.mean() > 0 for x in cells.values()))
        rows.append(row)
    table = pd.DataFrame(rows)
    winners = table[table.qualifies].sort_values(
        ["mean_net_r", "n"], ascending=[False, False])
    if winners.empty:
        selected = next(p for p in policies if p["name"] == "P0_PRIMARY")
        reason = "No policy met the preregistered development feasibility gate; froze P0_PRIMARY."
    else:
        name = winners.iloc[0].policy
        selected = next(p for p in policies if p["name"] == name)
        reason = "Highest development mean net_R among policies passing every preregistered gate."
    return {"selected": selected, "reason": reason,
            "holdout_inspected_for_selection": False}, table


def evaluation(selected: pd.DataFrame, sessions: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    q, split = add_split_columns(selected, sessions)
    cells = {
        "ALL": q,
        "DEV_JOINT": q[q.time_dev & q.symbol_dev],
        "TIME_HOLDOUT_ALL_SYMBOLS": q[~q.time_dev],
        "SYMBOL_HOLDOUT_ALL_TIME": q[~q.symbol_dev],
        "JOINT_HOLDOUT": q[(~q.time_dev) & (~q.symbol_dev)],
        "TDEV_SDEV0": q[q.time_dev & (q.symbol_fold == 0)],
        "TDEV_SDEV1": q[q.time_dev & (q.symbol_fold == 1)],
        "THOLD_SDEV": q[(~q.time_dev) & q.symbol_dev],
    }
    metric_rows = []
    cost_rows = []
    for name, x in cells.items():
        m = {"cell": name, **basic_metrics(x)}
        lo, hi = block_bootstrap_ci(x)
        m["bootstrap_ci_lo"], m["bootstrap_ci_hi"] = lo, hi
        m["sessions"] = int(x.session.nunique()) if len(x) else 0
        m["symbols"] = int(x.symbol.nunique()) if len(x) else 0
        m["optimistic_mean_net_r"] = float(x.net_r_opt.mean()) if len(x) else np.nan
        m["direction_flip_mfe_mae_ratio"] = (
            float(x.mae_r.mean() / x.mfe_r.mean())
            if len(x) and x.mfe_r.mean() > 0 else np.nan)
        metric_rows.append(m)
        for bps in COSTS_BPS:
            cm = basic_metrics(x, f"net_r_{bps}bps")
            cost_rows.append({"cell": name, "cost_bps": bps,
                              "n": cm["n"], "mean_net_r": cm["mean_net_r"],
                              "win_pct": cm["win_pct"],
                              "profit_factor": cm["profit_factor"]})
    return pd.DataFrame(metric_rows), pd.DataFrame(cost_rows)


def assert_lineage(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"rows": 0, "assertions": "vacuous"}
    checks = {
        "sweep_before_reclaim": bool((df.sweep_idx <= df.reclaim_idx).all()),
        "reclaim_before_h1_break_close": bool((df.reclaim_idx < df.h1_break_end_idx).all()),
        "parent_touch_after_confirm": bool((df.parent_touch_idx > df.h1_break_end_idx).all()),
        "mss_after_parent_touch": bool((df.m5_mss_idx > df.parent_touch_idx).all()),
        "m5_swing_confirmed_before_mss": bool((df.m5_mss_swing_conf < df.m5_mss_idx).all()),
        "child_fill_after_mss": bool((df.fill_idx > df.m5_mss_idx).all()),
        "positive_delays": bool(((df.parent_delay_actual >= 1)
                                 & (df.child_delay_actual >= 1)).all()),
        "nested_child_mid": bool((((df.child_lo + df.child_hi) / 2 >= df.parent_lo)
                                  & ((df.child_lo + df.child_hi) / 2 <= df.parent_hi)).all()),
    }
    if not all(checks.values()):
        raise AssertionError(f"lineage invariant failure: {checks}")
    return {"rows": len(df), **checks}


def _fmt(x, digits=3) -> str:
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "NA"
    return f"{x:.{digits}f}" if isinstance(x, (float, np.floating)) else str(x)


def write_report(funnel: pd.DataFrame, selection: dict, dev: pd.DataFrame,
                 metrics: pd.DataFrame, costs: pd.DataFrame, split: dict,
                 audits: pd.DataFrame, invariant: dict) -> None:
    sums = funnel.select_dtypes(include=[np.number]).sum()
    sel = selection["selected"]["name"]
    lines = [
        "# Researcher A — strict ordered SMC lineage study",
        "",
        f"Frozen policy: **{sel}**. {selection['reason']}",
        "",
        "## Data and causal audit",
        "",
        f"- Symbols: {audits.symbol.nunique()}, bars: {int(audits.bars.sum()):,}, "
        f"H1 bars: {int(audits.h1_bars.sum()):,}; invalid OHLC rows dropped: "
        f"{int(audits.invalid_rows.sum()):,}.",
        f"- Time cut: `{split['time_cut']}`; {len(split['dev_sessions'])} development "
        f"sessions / {len(split['holdout_sessions'])} untouched time-holdout sessions.",
        f"- Lineage assertions: {json.dumps(invariant, sort_keys=True)}",
        "- Primary execution: resting child-CE limit, stop-first ambiguity, adverse "
        "gap-through stop, no favorable target-gap fill, same-session EOD exit, 6 bps round trip.",
        "",
        "## Full recognizer funnel (all parent/child variants before policy filtering)",
        "",
        "| stage | count |",
        "|---|---:|",
    ]
    stage_order = [
        "roots", "root_sweeps", "root_reclaims", "important_root_reclaims",
        "h1_structure_breaks", "parent_fvg", "parent_ob",
        "parent_first_revisits", "m5_mss", "children", "child_fills", "targeted_trades",
    ]
    for k in stage_order:
        lines.append(f"| {k} | {int(sums.get(k, 0)):,} |")
    lines += [
        "",
        "## Development-only policy selection",
        "",
        "| policy | n | mean net R | TDEV0 | TDEV1 | SDEV0 | SDEV1 | qualifies |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for _, r in dev.iterrows():
        lines.append(
            f"| {r.policy} | {int(r.n)} | {_fmt(r.mean_net_r)} | "
            f"{_fmt(r.net_TDEV0)} | {_fmt(r.net_TDEV1)} | "
            f"{_fmt(r.net_SDEV0)} | {_fmt(r.net_SDEV1)} | {bool(r.qualifies)} |")
    lines += [
        "",
        "## Frozen-policy evaluation",
        "",
        "| cell | n | net R | 95% session-bootstrap CI | gross R | win% | PF | "
        "MFE/MAE | optimistic net R |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in metrics.iterrows():
        lines.append(
            f"| {r.cell} | {int(r.n)} | {_fmt(r.mean_net_r)} | "
            f"[{_fmt(r.bootstrap_ci_lo)}, {_fmt(r.bootstrap_ci_hi)}] | "
            f"{_fmt(r.mean_gross_r)} | {_fmt(r.win_pct,1)} | "
            f"{_fmt(r.profit_factor)} | {_fmt(r.mfe_mae_ratio)} | "
            f"{_fmt(r.optimistic_mean_net_r)} |")
    joint = metrics[metrics.cell == "JOINT_HOLDOUT"].iloc[0]
    success = bool(
        joint.n >= 40 and joint.mean_net_r > 0
        and np.isfinite(joint.bootstrap_ci_lo) and joint.bootstrap_ci_lo > 0)
    lines += [
        "",
        "## Decision",
        "",
        f"Preregistered profitability gate passed: **{success}**.",
        "",
        "A cell with fewer than 40 joint-holdout trades is inconclusive by rule. "
        "A non-positive untouched holdout or confidence lower bound fails the "
        "profitable-strategy claim; an optimistic target-first result cannot rescue it.",
        "",
        "## Reproduction",
        "",
        "```bash",
        "PYTHONDONTWRITEBYTECODE=1 app/.venv/bin/python "
        "dev/CODEX/researcher_a/strict_smc_study.py",
        "```",
        "",
        "See `PREREGISTRATION.json`, `recognizer_audit.md`, `output/candidates.parquet`, "
        "`output/selected_trades.parquet`, `output/metrics.csv`, and "
        "`output/cost_sensitivity.csv` for the full audit trail.",
    ]
    (HERE / "REPORT.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", help="comma-separated debug subset")
    ap.add_argument("--max-symbols", type=int)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    paths = sorted(DATA.glob("*.csv"))
    paths = [p for p in paths if p.stem != "NIFTY"]
    if args.symbols:
        wanted = set(args.symbols.split(","))
        paths = [p for p in paths if p.stem in wanted]
    if args.max_symbols:
        paths = paths[:args.max_symbols]

    rows, funnels, audits = [], [], []
    for n, path in enumerate(paths, 1):
        r, f, a = process_symbol(path)
        rows.extend(r); funnels.append(f); audits.append(a)
        if n % 10 == 0 or n == len(paths):
            print(f"processed {n}/{len(paths)} symbols; candidates={len(rows)}", flush=True)

    candidates = pd.DataFrame(rows)
    if candidates.empty:
        # Keep the downstream preregistered selection/evaluation machinery
        # executable even when a debug subset produces no complete lineage.
        candidates = pd.DataFrame(columns=["session", "symbol"])
    funnel_df, audit_df = pd.DataFrame(funnels), pd.DataFrame(audits)
    invariant = assert_lineage(candidates)
    all_sessions = sorted({
        s for p in paths
        for s in pd.read_csv(p, usecols=["ts"])["ts"].str.slice(0, 10).unique()
    })
    split_stub = add_split_columns(
        candidates[["session", "symbol"]].copy() if not candidates.empty
        else pd.DataFrame(columns=["session", "symbol"]),
        all_sessions,
    )[1]
    selection, dev_table = development_selection(candidates, all_sessions)
    selected = apply_policy(candidates, selection["selected"])
    metrics, costs = evaluation(selected, all_sessions)

    # Persist only beneath Researcher A.
    candidates.to_parquet(OUT / "candidates.parquet", index=False)
    selected.to_parquet(OUT / "selected_trades.parquet", index=False)
    funnel_df.to_csv(OUT / "funnel_by_symbol.csv", index=False)
    audit_df.to_csv(OUT / "data_audit.csv", index=False)
    dev_table.to_csv(OUT / "development_policy_selection.csv", index=False)
    metrics.to_csv(OUT / "metrics.csv", index=False)
    costs.to_csv(OUT / "cost_sensitivity.csv", index=False)
    (OUT / "selection.json").write_text(json.dumps(selection, indent=2))
    (OUT / "split.json").write_text(json.dumps(split_stub, indent=2))
    (OUT / "lineage_invariants.json").write_text(json.dumps(invariant, indent=2))
    write_report(funnel_df, selection, dev_table, metrics, costs,
                 split_stub, audit_df, invariant)
    print(f"selected={selection['selected']['name']} candidates={len(candidates)} "
          f"trades={len(selected)}")
    print(metrics.to_string(index=False))


if __name__ == "__main__":
    main()
