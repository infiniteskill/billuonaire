#!/usr/bin/env python3
"""Independent, causal strict-SMC recognizer and payoff audit.

All outputs are written below this script's directory. Source application,
research, run, and data trees are read-only inputs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DATA = ROOT / "data" / "long5m"
OUT = HERE / "artifacts"

TICK = 0.05
ATR_N = 14
SWING_N = 2
DISP_ATR = 0.8
DISP_BODY_FRAC = 0.60
DISP_CLOSE_FRAC = 0.25
FVG_ATR = 0.10
SWEEP_TO_DISP = 3
FILL_TTL = 6
STOP_BUFFER_ATR = 0.25
MIN_STOP_ATR = 1.0
MAX_STOP_ATR = 2.0
MIN_TARGET_R = 1.5
ENTRY_START = 11 * 60
ENTRY_END_EXCLUSIVE = 14 * 60 + 30
SQUAREOFF = 15 * 60 + 10

CAPITAL = 100_000.0
RISK_BUDGET = CAPITAL * 0.005
NOTIONAL_CAP = CAPITAL * 5.0
BROKERAGE = 20.0
STT = 0.025 / 100
EXCHANGE = 0.00297 / 100
ADVERSE = 5 / 10_000
MAX_COST_REWARD = 0.15

DEV_END = "2026-06-15"
VAL_END = "2026-07-01"
TREES = ("A_SWEEP_DISP_FVG_CE", "B_A_PLUS_MSS", "C_B_PLUS_PD")
BOOT_REPS = 2_000
SEED = 20260719


def qnearest(x: float) -> float:
    return math.floor(x / TICK + 0.5) * TICK


def qfloor(x: float) -> float:
    return math.floor((x + 1e-10) / TICK) * TICK


def qceil(x: float) -> float:
    return math.ceil((x - 1e-10) / TICK) * TICK


def known_at(ts: pd.Timestamp) -> str:
    return (ts + pd.Timedelta(minutes=5)).isoformat()


def symbol_fold(symbol: str) -> int:
    return int(hashlib.sha256(symbol.encode()).hexdigest()[:8], 16) % 5


def leg_cost(price: float, qty: int, sell: bool) -> float:
    return BROKERAGE + ((STT if sell else 0.0) + EXCHANGE) * price * qty


@dataclass
class Swing:
    event_id: str
    symbol: str
    kind: str
    pivot_idx: int
    available_idx: int
    price: float
    pivot_ts: str
    available_ts: str
    status: str = "ACTIVE"
    terminal_idx: int | None = None
    terminal_ts: str | None = None


def load_symbol(path: Path) -> pd.DataFrame:
    d = pd.read_csv(path)
    d["ts"] = pd.to_datetime(d["ts"], utc=True).dt.tz_convert("Asia/Kolkata")
    for c in ("open", "high", "low", "close"):
        d[c] = pd.to_numeric(d[c], errors="raise")
    d["session"] = d.ts.dt.strftime("%Y-%m-%d")
    d["minute"] = d.ts.dt.hour * 60 + d.ts.dt.minute
    prev = d.close.shift(1)
    tr = pd.concat(
        [(d.high - d.low), (d.high - prev).abs(), (d.low - prev).abs()], axis=1
    ).max(axis=1, skipna=False)
    d["atr"] = tr.rolling(ATR_N, min_periods=ATR_N).mean()
    daily = d.groupby("session").agg(day_hi=("high", "max"), day_lo=("low", "min"))
    daily["prev_hi"] = daily.day_hi.shift(1)
    daily["prev_lo"] = daily.day_lo.shift(1)
    daily["prev_mid"] = (daily.prev_hi + daily.prev_lo) / 2
    return d.join(daily[["prev_hi", "prev_lo", "prev_mid"]], on="session")


def candidate_swings(symbol: str, d: pd.DataFrame) -> list[Swing]:
    h, l, ts = d.high.to_numpy(), d.low.to_numpy(), d.ts
    out: list[Swing] = []
    for p in range(SWING_N, len(d) - SWING_N):
        ah = np.r_[h[p - SWING_N:p], h[p + 1:p + SWING_N + 1]]
        al = np.r_[l[p - SWING_N:p], l[p + 1:p + SWING_N + 1]]
        a = p + SWING_N
        if np.all(h[p] > ah):
            out.append(Swing(
                f"{symbol}:SWING_H:{p}", symbol, "SWING_H", p, a, float(h[p]),
                ts.iloc[p].isoformat(), known_at(ts.iloc[a]),
            ))
        if np.all(l[p] < al):
            out.append(Swing(
                f"{symbol}:SWING_L:{p}", symbol, "SWING_L", p, a, float(l[p]),
                ts.iloc[p].isoformat(), known_at(ts.iloc[a]),
            ))
    return out


def event_row(event_id: str, symbol: str, event_type: str, idx: int,
              d: pd.DataFrame, **kwargs) -> dict:
    row = {
        "event_id": event_id, "symbol": symbol, "event_type": event_type,
        "bar_idx": idx, "bar_ts": d.ts.iloc[idx].isoformat(),
        "known_at": known_at(d.ts.iloc[idx]), "session": d.session.iloc[idx],
    }
    row.update(kwargs)
    return row


def build_states(symbol: str, d: pd.DataFrame, events: list[dict]):
    swings = candidate_swings(symbol, d)
    add_at: dict[int, list[Swing]] = defaultdict(list)
    for s in swings:
        add_at[s.available_idx].append(s)
        events.append(event_row(
            s.event_id, symbol, "SWING_CONFIRM", s.available_idx, d,
            kind=s.kind, pivot_idx=s.pivot_idx, pivot_ts=s.pivot_ts,
            available_idx=s.available_idx, price=s.price,
        ))
    active = {"SWING_H": [], "SWING_L": []}
    selected_sweeps, all_sweeps = [], []
    h, l, c = (d[x].to_numpy(float) for x in ("high", "low", "close"))
    for i in range(len(d)):
        before = {k: list(v) for k, v in active.items()}
        swept_here: dict[int, list[dict]] = defaultdict(list)
        for kind in ("SWING_H", "SWING_L"):
            keep = []
            for s in active[kind]:
                if kind == "SWING_H":
                    swept, broken = h[i] > s.price and c[i] < s.price, c[i] > s.price
                    direction, extreme, opp = -1, h[i], before["SWING_L"]
                else:
                    swept, broken = l[i] < s.price and c[i] > s.price, c[i] < s.price
                    direction, extreme, opp = 1, l[i], before["SWING_H"]
                if swept or broken:
                    s.status = "SWEPT" if swept else "BROKEN"
                    s.terminal_idx, s.terminal_ts = i, known_at(d.ts.iloc[i])
                    et = "SWEEP" if swept else "SWING_BREAK"
                    eid = f"{symbol}:{et}:{s.event_id}:{i}"
                    mss_parent = max(opp, key=lambda z: z.pivot_idx) if opp else None
                    events.append(event_row(
                        eid, symbol, et, i, d, direction=direction if swept else 0,
                        parent_id=s.event_id, parent_kind=s.kind, level=s.price,
                        extreme=float(extreme), parent_available_idx=s.available_idx,
                        mss_parent_id=mss_parent.event_id if mss_parent else None,
                        mss_level=mss_parent.price if mss_parent else np.nan,
                    ))
                    if swept:
                        sw = {
                            "event_id": eid, "symbol": symbol, "idx": i,
                            "session": d.session.iloc[i], "direction": direction,
                            "parent": s, "extreme": float(extreme),
                            "mss_parent": mss_parent,
                        }
                        all_sweeps.append(sw)
                        swept_here[direction].append(sw)
                else:
                    keep.append(s)
            active[kind] = keep
        for xs in swept_here.values():
            selected_sweeps.append(max(xs, key=lambda x: x["parent"].pivot_idx))
        # Do not allow the confirmation bar to retroactively sweep its new pivot.
        for s in add_at.get(i, []):
            active[s.kind].append(s)
    return swings, all_sweeps, selected_sweeps


def displacement_direction(i: int, d: pd.DataFrame) -> int:
    if i < 1 or not np.isfinite(d.atr.iloc[i]):
        return 0
    o, h, l, c, atr = (float(d[x].iloc[i]) for x in ("open", "high", "low", "close", "atr"))
    rng, body = h - l, abs(c - o)
    if rng <= 0 or body < DISP_ATR * atr or body / rng < DISP_BODY_FRAC:
        return 0
    if c > o and (h - c) / rng <= DISP_CLOSE_FRAC and c > float(d.high.iloc[i - 1]):
        return 1
    if c < o and (c - l) / rng <= DISP_CLOSE_FRAC and c < float(d.low.iloc[i - 1]):
        return -1
    return 0


def form_lineages(symbol: str, d: pd.DataFrame, selected_sweeps: list[dict],
                  events: list[dict]) -> list[dict]:
    by_dir = {z: [s for s in selected_sweeps if s["direction"] == z] for z in (-1, 1)}
    consumed: set[str] = set()
    lineages = []
    for i in range(1, len(d) - 1):
        direction = displacement_direction(i, d)
        if not direction:
            continue
        candidates = [s for s in by_dir[direction]
                      if s["event_id"] not in consumed
                      and 0 <= i - s["idx"] <= SWEEP_TO_DISP
                      and s["session"] == d.session.iloc[i]]
        parent = max(candidates, key=lambda s: (s["idx"], s["parent"].pivot_idx)) \
            if candidates else None
        deid = f"{symbol}:DISP:{direction}:{i}"
        events.append(event_row(
            deid, symbol, "DISPLACEMENT", i, d, direction=direction,
            parent_id=parent["event_id"] if parent else None,
            body_atr=abs(float(d.close.iloc[i] - d.open.iloc[i])) / float(d.atr.iloc[i]),
            body_fraction=abs(float(d.close.iloc[i] - d.open.iloc[i])) /
                          float(d.high.iloc[i] - d.low.iloc[i]),
        ))
        if parent is None:
            continue
        k = i + 1
        if len({d.session.iloc[i - 1], d.session.iloc[i], d.session.iloc[k]}) != 1:
            continue
        if not np.isfinite(d.atr.iloc[k]) or d.atr.iloc[k] <= 0:
            continue
        if direction == 1:
            lo, hi = float(d.high.iloc[i - 1]), float(d.low.iloc[k])
        else:
            lo, hi = float(d.high.iloc[k]), float(d.low.iloc[i - 1])
        if hi <= lo or hi - lo < FVG_ATR * float(d.atr.iloc[k]):
            continue
        consumed.add(parent["event_id"])
        fvg_id = f"{symbol}:FVG:{direction}:{k}:{parent['event_id']}"
        mss_parent = parent["mss_parent"]
        mss = bool(mss_parent and (
            float(d.close.iloc[i]) > mss_parent.price if direction == 1
            else float(d.close.iloc[i]) < mss_parent.price
        ))
        events.append(event_row(
            fvg_id, symbol, "FVG_CONFIRM", k, d, direction=direction,
            parent_id=deid, sweep_parent_id=parent["event_id"],
            swing_parent_id=parent["parent"].event_id,
            mss_parent_id=mss_parent.event_id if mss_parent else None,
            mss=mss, zone_lo=lo, zone_hi=hi,
            gap_atr=(hi - lo) / float(d.atr.iloc[k]),
        ))
        lineages.append({
            "lineage_id": fvg_id, "symbol": symbol, "direction": direction,
            "sweep_idx": parent["idx"], "sweep_event_id": parent["event_id"],
            "swing_parent_id": parent["parent"].event_id,
            "swing_available_idx": parent["parent"].available_idx,
            "sweep_extreme": parent["extreme"], "disp_idx": i,
            "disp_event_id": deid, "fvg_idx": k, "fvg_event_id": fvg_id,
            "mss": mss, "mss_parent_id": mss_parent.event_id if mss_parent else None,
            "zone_lo": lo, "zone_hi": hi, "atr": float(d.atr.iloc[k]),
            "session": d.session.iloc[k],
        })
    return lineages


def active_target(swings: list[Swing], direction: int, entry: float, risk: float,
                  entry_idx: int) -> Swing | None:
    kind = "SWING_H" if direction == 1 else "SWING_L"
    cands = []
    for s in swings:
        active_at_open = s.available_idx < entry_idx and (
            s.terminal_idx is None or s.terminal_idx >= entry_idx
        )
        beyond = s.price > entry if direction == 1 else s.price < entry
        if s.kind == kind and active_at_open and beyond \
                and abs(s.price - entry) >= MIN_TARGET_R * risk:
            cands.append(s)
    return min(cands, key=lambda s: abs(s.price - entry)) if cands else None


def simulate_path(d: pd.DataFrame, entry_idx: int, direction: int, entry: float,
                  stop: float, target: float, qty: int) -> dict:
    session = d.session.iloc[entry_idx]
    candidates = d.index[(d.session == session) & (d.minute <= SQUAREOFF) &
                         (d.index >= entry_idx)].to_numpy()
    if not len(candidates):
        return {}
    end = int(candidates[-1])
    kind, exit_idx, base = "time", end, float(d.close.iloc[end])
    for x in range(entry_idx, end + 1):
        if direction == 1:
            sh, th = float(d.low.iloc[x]) <= stop, float(d.high.iloc[x]) >= target
        else:
            sh, th = float(d.high.iloc[x]) >= stop, float(d.low.iloc[x]) <= target
        if sh:
            kind, exit_idx = "stop", x
            op = float(d.open.iloc[x])
            base = op if ((op <= stop) if direction == 1 else (op >= stop)) else stop
            break
        if th:
            kind, exit_idx, base = "target", x, target
            break
    exit_price = qnearest(base if kind == "target" else base * (1 - direction * ADVERSE))
    entry_cost = leg_cost(entry, qty, sell=direction == -1)
    exit_cost = leg_cost(exit_price, qty, sell=direction == 1)
    gross = (exit_price - entry) * direction * qty
    costs = entry_cost + exit_cost
    actual_risk = qty * abs(entry - stop)
    return {
        "exit_idx": exit_idx, "exit_ts": d.ts.iloc[exit_idx].isoformat(),
        "exit_kind": kind, "exit_price": exit_price, "qty": qty,
        "gross_rupees": gross, "costs_rupees": costs, "net_rupees": gross - costs,
        "gross_R": gross / actual_risk, "net_R": (gross - costs) / actual_risk,
        "win": gross - costs > 0,
    }


def make_trade(d: pd.DataFrame, swings: list[Swing], lin: dict,
               events: list[dict]) -> list[dict]:
    direction, k = lin["direction"], lin["fvg_idx"]
    lo, hi, ce = lin["zone_lo"], lin["zone_hi"], (lin["zone_lo"] + lin["zone_hi"]) / 2
    touch_idx, ce_reached, invalid_reason = None, False, None
    for j in range(k + 1, min(k + FILL_TTL, len(d) - 1) + 1):
        if d.session.iloc[j] != d.session.iloc[k]:
            break
        if (direction == 1 and float(d.high.iloc[j]) < lo) or \
                (direction == -1 and float(d.low.iloc[j]) > hi):
            invalid_reason = "GAP_THROUGH_FVG"
            break
        overlap = float(d.low.iloc[j]) <= hi and float(d.high.iloc[j]) >= lo
        if overlap:
            touch_idx = j
            ce_reached = float(d.low.iloc[j]) <= ce <= float(d.high.iloc[j])
            invalid_reason = None if ce_reached else "SHALLOW_FIRST_TOUCH"
            break
    if touch_idx is not None:
        events.append(event_row(
            f"{lin['lineage_id']}:TOUCH", lin["symbol"], "FVG_FIRST_TOUCH", touch_idx, d,
            direction=direction, parent_id=lin["fvg_event_id"], fresh=True,
            ce_reached=ce_reached, invalid_reason=invalid_reason,
        ))
    if touch_idx is None or not ce_reached:
        return []
    minute = int(d.minute.iloc[touch_idx])
    if not ENTRY_START <= minute < ENTRY_END_EXCLUSIVE:
        return []
    atr, entry = lin["atr"], qnearest(ce)
    raw_stop = lin["sweep_extreme"] - STOP_BUFFER_ATR * atr if direction == 1 \
        else lin["sweep_extreme"] + STOP_BUFFER_ATR * atr
    risk = abs(entry - raw_stop)
    if risk < MIN_STOP_ATR * atr:
        raw_stop = entry - MIN_STOP_ATR * atr if direction == 1 else entry + MIN_STOP_ATR * atr
    stop = qfloor(raw_stop) if direction == 1 else qceil(raw_stop)
    risk = abs(entry - stop)
    if risk <= 0 or risk > MAX_STOP_ATR * atr:
        return []
    tgt = active_target(swings, direction, entry, risk, touch_idx)
    if tgt is None:
        return []
    target = qnearest(tgt.price)
    target_r = abs(target - entry) / risk
    qty = int(min(RISK_BUDGET // risk, NOTIONAL_CAP // entry))
    if qty < 1:
        return []
    expected_reward = abs(target - entry) * qty
    est_cost = 2 * BROKERAGE + (STT + 2 * EXCHANGE) * entry * qty
    cost_gate = est_cost <= MAX_COST_REWARD * expected_reward
    result = simulate_path(d, touch_idx, direction, entry, stop, target, qty)
    if not result:
        return []
    pmid = float(d.prev_mid.iloc[touch_idx]) if np.isfinite(d.prev_mid.iloc[touch_idx]) else np.nan
    pd_fav = bool(np.isfinite(pmid) and (entry <= pmid if direction == 1 else entry >= pmid))
    base = {
        **lin, "entry_idx": touch_idx, "entry_ts": d.ts.iloc[touch_idx].isoformat(),
        "entry_known_after_fvg": touch_idx > k, "first_touch": True,
        "entry": entry, "stop": stop, "risk_pts": risk, "risk_atr": risk / atr,
        "target": target, "target_R": target_r, "target_parent_id": tgt.event_id,
        "prev_mid": pmid, "pd_fav": pd_fav, "cost_gate": cost_gate,
        "cost_reward_est": est_cost / expected_reward, **result,
    }
    rows = []
    for tree in TREES:
        if tree == "B_A_PLUS_MSS" and not lin["mss"]:
            continue
        if tree == "C_B_PLUS_PD" and not (lin["mss"] and pd_fav):
            continue
        rows.append({**base, "tree": tree})
    return rows


def scan_symbol(path: Path):
    symbol, d, events = path.stem, load_symbol(path), []
    swings, sweeps, selected = build_states(symbol, d, events)
    lineages = form_lineages(symbol, d, selected, events)
    trades = []
    for lin in lineages:
        trades.extend(make_trade(d, swings, lin, events))
    return d, swings, sweeps, lineages, events, trades


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def recognizer_audit(e: pd.DataFrame, l: pd.DataFrame, t: pd.DataFrame) -> dict:
    return {
        "event_id_duplicate_excess": int(e.event_id.duplicated().sum()) if len(e) else 0,
        "lineage_id_duplicate_excess": int(l.lineage_id.duplicated().sum()) if len(l) else 0,
        "tree_trade_key_duplicate_excess": int(t.duplicated(
            ["tree", "symbol", "lineage_id", "entry_idx"]).sum()) if len(t) else 0,
        "bad_swing_order": int((e.loc[e.event_type.eq("SWING_CONFIRM"), "available_idx"] <=
                                 e.loc[e.event_type.eq("SWING_CONFIRM"), "pivot_idx"]).sum()) if len(e) else 0,
        "bad_lineage_order": int((~((l.swing_available_idx < l.sweep_idx) &
                                     (l.sweep_idx <= l.disp_idx) &
                                     (l.disp_idx < l.fvg_idx))).sum()) if len(l) else 0,
        "reused_sweep_parent_excess": int(l.sweep_event_id.duplicated().sum()) if len(l) else 0,
        "bad_entry_order": int((~t.entry_known_after_fvg).sum()) if len(t) else 0,
        "nonfresh_entry": int((~t.first_touch).sum()) if len(t) else 0,
        "wrong_direction": int((~t.direction.isin([-1, 1])).sum()) if len(t) else 0,
        "cost_gate_pass_rows": int(t.cost_gate.sum()) if len(t) else 0,
        "events_by_type": e.event_type.value_counts().sort_index().to_dict() if len(e) else {},
        "tree_rows": t.tree.value_counts().reindex(TREES, fill_value=0).to_dict() if len(t) else {},
    }


def run_scan() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in DATA.glob("*.csv") if p.stem != "NIFTY")
    events, lineages, trades, manifest = [], [], [], []
    swing_n = sweep_n = 0
    for z, path in enumerate(files, 1):
        d, swings, sweeps, lins, evs, trs = scan_symbol(path)
        events.extend(evs); lineages.extend(lins); trades.extend(trs)
        swing_n += len(swings); sweep_n += len(sweeps)
        manifest.append({"symbol": path.stem, "rows": len(d),
                         "first": d.ts.iloc[0].isoformat(), "last": d.ts.iloc[-1].isoformat(),
                         "sha256": sha256(path)})
        if z % 20 == 0 or z == len(files):
            print(f"scan {z}/{len(files)} events={len(events)} lineages={len(lineages)} trades={len(trades)}", flush=True)
    edf, ldf, tdf = pd.DataFrame(events), pd.DataFrame(lineages), pd.DataFrame(trades)
    edf.to_parquet(OUT / "recognizer_events.parquet", index=False)
    ldf.to_parquet(OUT / "lineages.parquet", index=False)
    tdf.to_parquet(OUT / "trades_raw.parquet", index=False)
    pd.DataFrame(manifest).to_csv(OUT / "input_manifest.csv", index=False)
    audit = recognizer_audit(edf, ldf, tdf)
    audit.update({"symbols": len(files), "swings": swing_n, "sweeps": sweep_n,
                  "lineages": len(ldf), "raw_tree_rows": len(tdf),
                  "python": sys.version, "platform": platform.platform(),
                  "pandas": pd.__version__, "numpy": np.__version__,
                  "script_sha256": sha256(Path(__file__)),
                  "prereg_sha256": sha256(HERE / "PREREGISTRATION.md")})
    (OUT / "recognizer_audit.json").write_text(json.dumps(audit, indent=2))
    print(json.dumps(audit, indent=2))


def add_partitions(t: pd.DataFrame) -> pd.DataFrame:
    x = t.copy()
    x["fold"] = x.symbol.map(symbol_fold)
    x["date_stage"] = np.where(x.session <= DEV_END, "DEV",
                               np.where(x.session <= VAL_END, "VAL", "TEST"))
    return x


def slice_mask(t: pd.DataFrame, name: str) -> np.ndarray:
    if name == "ALL": return np.ones(len(t), bool)
    if name == "DEV": return (t.date_stage.eq("DEV") & t.fold.isin([0, 1, 2])).to_numpy()
    if name == "VALIDATION": return (t.date_stage.eq("VAL") & t.fold.eq(3)).to_numpy()
    if name == "FINAL": return (t.date_stage.eq("TEST") & t.fold.eq(4)).to_numpy()
    if name == "CHRONO_DEV": return t.date_stage.eq("DEV").to_numpy()
    if name == "CHRONO_VAL": return t.date_stage.eq("VAL").to_numpy()
    if name == "CHRONO_TEST": return t.date_stage.eq("TEST").to_numpy()
    if name == "SYMBOL_DEV": return t.fold.isin([0, 1, 2]).to_numpy()
    if name == "SYMBOL_VAL": return t.fold.eq(3).to_numpy()
    if name == "SYMBOL_TEST": return t.fold.eq(4).to_numpy()
    raise KeyError(name)


SLICES = ("DEV", "VALIDATION", "FINAL", "CHRONO_DEV", "CHRONO_VAL",
          "CHRONO_TEST", "SYMBOL_DEV", "SYMBOL_VAL", "SYMBOL_TEST", "ALL")


def bootstrap_group(g: pd.DataFrame, key: str, rng: np.random.Generator) -> np.ndarray:
    a = g.groupby(key).net_R.agg(["sum", "count"]).to_numpy(float)
    if not len(a): return np.full(BOOT_REPS, np.nan)
    out = np.empty(BOOT_REPS)
    for r in range(BOOT_REPS):
        z = rng.integers(0, len(a), len(a))
        out[r] = a[z, 0].sum() / a[z, 1].sum()
    return out


def max_drawdown(g: pd.DataFrame) -> float:
    daily = g.groupby("session").net_R.sum().sort_index().cumsum().to_numpy(float)
    if not len(daily): return np.nan
    wealth = np.r_[0.0, daily]
    return float(np.max(np.maximum.accumulate(wealth) - wealth))


def summarize(g: pd.DataFrame, seed_offset: int) -> dict:
    if g.empty: return {"n": 0}
    rng = np.random.default_rng(SEED + seed_offset)
    boots = [bootstrap_group(g, k, rng) for k in ("symbol", "session", "cluster")]
    lows = [float(np.nanpercentile(b, 2.5)) for b in boots]
    highs = [float(np.nanpercentile(b, 97.5)) for b in boots]
    ps = [float((b <= 0).mean()) for b in boots]
    pos, neg = g.loc[g.net_R > 0, "net_R"].sum(), -g.loc[g.net_R < 0, "net_R"].sum()
    return {"n": len(g), "symbols": g.symbol.nunique(), "sessions": g.session.nunique(),
            "mean_gross_R": g.gross_R.mean(), "mean_net_R": g.net_R.mean(),
            "median_net_R": g.net_R.median(), "win_rate": g.win.mean(),
            "profit_factor": pos / neg if neg > 0 else np.inf,
            "mean_rupees": g.net_rupees.mean(), "sum_rupees": g.net_rupees.sum(),
            "mean_cost_R": (g.costs_rupees / (g.qty * g.risk_pts)).mean(),
            "long_net_R": g.loc[g.direction.eq(1), "net_R"].mean(),
            "short_net_R": g.loc[g.direction.eq(-1), "net_R"].mean(),
            "cluster_ci_low": min(lows), "cluster_ci_high": max(highs),
            "cluster_p_one_sided": max(ps),
            "max_daily_drawdown_R_units": max_drawdown(g)}


def holm_adjust(p: list[float]) -> list[float]:
    n, out, running = len(p), np.ones(len(p)), 0.0
    for rank, idx in enumerate(np.argsort(np.nan_to_num(p, nan=1.0))):
        val = min(1.0, (n - rank) * (p[idx] if np.isfinite(p[idx]) else 1.0))
        running = max(running, val); out[idx] = running
    return out.tolist()


def run_evaluate(include_final: bool) -> None:
    t = add_partitions(pd.read_parquet(OUT / "trades_raw.parquet"))
    t = t[t.cost_gate].sort_values(["tree", "symbol", "session", "entry_idx"])
    t = t.drop_duplicates(["tree", "symbol", "session"], keep="first").reset_index(drop=True)
    t["cluster"] = t.symbol + "|" + t.session
    t.to_parquet(OUT / "trades_main.parquet", index=False)
    allowed = [s for s in SLICES if include_final or s not in ("FINAL", "CHRONO_TEST")]
    rows = []
    for si, sl in enumerate(allowed):
        m = slice_mask(t, sl)
        for ti, tree in enumerate(TREES):
            rows.append({"slice": sl, "tree": tree,
                         **summarize(t[(t.tree == tree) & m], si * 10 + ti)})
    out = pd.DataFrame(rows)
    for _, idx in out.groupby("slice").groups.items():
        out.loc[idx, "holm_p"] = holm_adjust(out.loc[idx, "cluster_p_one_sided"].tolist())
    suffix = "final" if include_final else "pre_final"
    out.to_csv(OUT / f"evaluation_{suffix}.csv", index=False)
    print(out.to_string(index=False))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=("scan", "evaluate-pre-final", "evaluate-final"))
    a = p.parse_args()
    if a.command == "scan": run_scan()
    elif a.command == "evaluate-pre-final": run_evaluate(False)
    else: run_evaluate(True)


if __name__ == "__main__":
    main()
