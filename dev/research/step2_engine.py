"""STEP 2-4 engine: realistic-fill outcome simulation + filters + holdout.

Realistic fills REPLICATE app/trader/execution/paper.py economics:
  entry  = next-M1-open adverse by half-spread          (limit-style, no slip)
  stop   = level-or-gap-open adverse by half+slippage   (market/stop, slips)
  target = the target level adverse by half-spread      (limit, no slip)
  EOD    = last-bar close adverse by half+slippage       (market)
Intrabar ambiguity (a bar spans both stop and target) => STOP first (conservative,
tie on index -> stop). Stop never assumes a clean fill: if the bar OPENED beyond
the stop (gap-through) it fills at the open (worse), else at the stop, then slips.

Sizing: qty = floor(1%*10L / stop_dist_rupees), capped at 5x notional leverage
(<=50L / entry). Costs = Rs20/order x2 + 0.025% sell-side STT + exchange_pct both
legs (spread already embedded in the fill). net_R = net_rupees / (1%*10L=10,000).
"""
from __future__ import annotations

import numpy as np

CAP = 1_000_000.0            # Rs 10L notional capital
RISK = 0.01 * CAP            # Rs 10,000 = 1R denominator
NOTIONAL_CAP = 5.0 * CAP     # 5x leverage cap
HALF = 2 / 10000             # half-spread
ADV = (2 + 3) / 10000        # half-spread + slippage (market fills)
BROK = 20.0                  # brokerage flat / order
STT = 0.025 / 100            # sell-side STT fraction
EXCH = 0.00297 / 100         # exchange fraction (both legs)
TICK = 0.05

# exit schemes: (name, mgmt, target_mult|None)
SCHEMES = ([(f"fixed_t{m}", "fixed", m) for m in (1, 1.5, 2, 3, 5)]
           + [(f"be1r_t{m}", "be1r", m) for m in (1.5, 2, 3, 5)]
           + [("trail", "trail", None)]
           + [(f"trail_t{m}", "trail", m) for m in (2, 3, 5)])
KS = (0.25, 0.5, 0.75, 1.0, 1.5)


def _q(x: float) -> float:
    return round(x / TICK) * TICK


def simulate(o, h, l, c, d, atr, k, mgmt, tgt_mult):
    """Return (net_R, kind) or None if unsizable. o/h/l/c are float np arrays,
    the M1 path from the entry bar (bar 0 = next M1 after signal) to EOD."""
    stop_dist = k * atr
    if stop_dist <= 0:
        return None
    entry_fill = _q(o[0] * (1 + d * HALF))
    if entry_fill <= 0:
        return None
    qty = int(min(RISK // stop_dist, NOTIONAL_CAP // entry_fill))
    if qty < 1:
        return None
    S = entry_fill - d * stop_dist
    T = entry_fill + d * tgt_mult * stop_dist if tgt_mult is not None else None
    n = len(o)
    idxs = np.arange(n)

    if mgmt == "fixed":
        stop_arr = np.full(n, S)
    elif mgmt == "be1r":
        fav = (h - entry_fill) if d == 1 else (entry_fill - l)
        reached = np.nonzero(fav >= stop_dist)[0]
        b_break = (reached[0] + 1) if reached.size else n
        stop_arr = np.where(idxs < b_break, S, entry_fill)
    else:  # trail: ratchet behind the PRIOR-bar peak (conservative, no same-bar)
        if d == 1:
            peak_prev = np.maximum.accumulate(
                np.concatenate([[-np.inf], h[:-1]]))
            stop_arr = np.maximum(S, peak_prev - stop_dist)
        else:
            trough_prev = np.minimum.accumulate(
                np.concatenate([[np.inf], l[:-1]]))
            stop_arr = np.minimum(S, trough_prev + stop_dist)

    if d == 1:
        stop_hit = l <= stop_arr
        tgt_hit = (h >= T) if T is not None else np.zeros(n, bool)
    else:
        stop_hit = h >= stop_arr
        tgt_hit = (l <= T) if T is not None else np.zeros(n, bool)

    si = int(np.argmax(stop_hit)) if stop_hit.any() else n
    ti = int(np.argmax(tgt_hit)) if tgt_hit.any() else n

    if si == n and ti == n:
        kind, idx = "eod", n - 1
    elif si <= ti:                       # tie/both same bar -> stop (conservative)
        kind, idx = "stop", si
    else:
        kind, idx = "tgt", ti

    if kind == "stop":
        lvl = stop_arr[idx]
        if d == 1:
            base = o[idx] if o[idx] <= lvl else lvl     # gap-through worse
        else:
            base = o[idx] if o[idx] >= lvl else lvl
        rate = ADV
    elif kind == "tgt":
        base, rate = T, HALF
    else:
        base, rate = c[-1], ADV
    exit_fill = _q(base * (1 - d * rate))

    cost_entry = BROK + ((STT if d == -1 else 0) + EXCH) * entry_fill * qty
    cost_exit = BROK + ((STT if d == 1 else 0) + EXCH) * exit_fill * qty
    net_rup = (exit_fill - entry_fill) * d * qty - cost_entry - cost_exit
    return net_rup / RISK, kind


def path_excursions(o, h, l, c, d, atr):
    """MFE/MAE in ATR units over the EOD path (target-independent reality)."""
    if d == 1:
        mfe = (h.max() - o[0]) / atr
        mae = (o[0] - l.min()) / atr
    else:
        mfe = (o[0] - l.min()) / atr
        mae = (h.max() - o[0]) / atr
    return float(mfe), float(mae)
