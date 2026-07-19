"""asm_sim -- economic R-sim for the ASSEMBLED taught system.

Edge entry (frozen: limit at the proximal edge, gap-aware fill), zone-height stop
(far edge; fallback 1.5xATR when the box is degenerate/deep-gapped), targets 1:1
and 2R, plus a slow-trail runner. Gap-through fills at the actual open, stop-first
conservatism on every bar incl. the fill bar. Delivery costs + sizing identical to
dgrid_lib (STT 0.1% both legs, exch 0.004%, DP Rs15/sell, slip 2bp/leg, R0=Rs500
risk on a Rs1L 0.5% account, CAP notional ceiling).
"""
import sys
import numpy as np
sys.path.insert(0, "/home/doom/Public/PROJECT/2026/trader/dev/research")
from dgrid_lib import R0, CAP, SLIP, STT, EXCH, DP

ATR_FALLBACK = 1.5   # fallback stop = 1.5xATR (lesson-9 zone-height stop is primary)
THIN = 0.25          # zone thinner than THIN*ATR -> use ATR fallback stop


def _acct(fp, ex, d, sd):
    """(netR, grossR) for one round trip; costs charged on both legs in R units."""
    qty = min(R0 / sd, CAP / fp)
    Rr = qty * sd
    gross = d * (ex - fp) * qty / Rr
    net = gross - ((SLIP + STT + EXCH) * qty * (fp + ex) + DP) / Rr
    return float(net), float(gross)


def _walk(O, H, L, C, t0, d, fp, stop, tgt, N):
    """Gap-aware stop-first walk to fixed target. Returns (exit_px, win, exit_bar)."""
    last = min(t0 + N, len(C)) - 1
    for b in range(t0, last + 1):
        o = O[b]
        if b > t0:
            if d * (o - stop) <= 0: return o, False, b
            if d * (o - tgt) >= 0: return o, True, b
        if d == 1:
            if L[b] <= stop: return stop, False, b
            if H[b] >= tgt: return tgt, True, b
        else:
            if H[b] >= stop: return stop, False, b
            if L[b] <= tgt: return tgt, True, b
    return C[last], False, last


def _trail(O, H, L, C, t0, d, fp, stop0, R, N):
    """Slow-trail runner: no fixed target; once +1R favorable is reached, ratchet a
    trailing stop 1R behind the running peak CLOSE (1R close-chandelier). Rides the
    tail; exits on intrabar breach of the (trailing) stop or the horizon. Returns
    (exit_px, exit_bar, peakR)."""
    last = min(t0 + N, len(C)) - 1
    stop = stop0; peak = fp
    for b in range(t0, last + 1):
        o = O[b]
        if b > t0 and d * (o - stop) <= 0:
            return o, b, d * (peak - fp) / R
        if d == 1:
            if L[b] <= stop: return stop, b, d * (peak - fp) / R
            peak = max(peak, C[b])
        else:
            if H[b] >= stop: return stop, b, d * (peak - fp) / R
            peak = min(peak, C[b])
        if d * (peak - fp) >= R:                    # engage/ratchet after +1R
            ns = peak - d * R
            stop = max(stop, ns) if d == 1 else min(stop, ns)
    return C[last], last, d * (peak - fp) / R


def econ(O, H, L, C, atr, t0, d, E, F, N):
    """Full R-outcome bundle for one episode entering at proximal edge E, far edge F.
    Returns dict or None (unfillable). Keys: fp, sd, zh_stop(bool), and per policy
    (t1/t2/tr): net, gross, win."""
    n = len(C); a = atr[t0]; o0 = O[t0]
    if not (np.isfinite(a) and a > 0): return None
    fp = min(o0, E) if d == 1 else max(o0, E)       # edge limit, gap-aware
    if fp <= 0: return None
    zh = abs(E - F)
    zh_stop = True
    if not np.isfinite(zh) or zh < THIN * a:
        sd = ATR_FALLBACK * a; stop = fp - d * sd; zh_stop = False
    else:
        stop = F; sd = abs(fp - stop)
        if sd <= 0 or d * (fp - stop) <= 0:          # deep gap past far edge
            sd = ATR_FALLBACK * a; stop = fp - d * sd; zh_stop = False
    R = sd
    out = dict(fp=fp, sd=sd, zh_stop=zh_stop)
    for name, tgtR in (("t1", 1.0), ("t2", 2.0)):
        tgt = fp + d * tgtR * R
        ex, win, _ = _walk(O, H, L, C, t0, d, fp, stop, tgt, N)
        net, gross = _acct(fp, ex, d, sd)
        out[name] = (net, gross, win)
    ex, _, peakR = _trail(O, H, L, C, t0, d, fp, stop, R, N)
    net, gross = _acct(fp, ex, d, sd)
    out["tr"] = (net, gross, peakR)
    # apples-to-apples baseline geometry: edge entry, 1.5xATR stop, 2R target
    sda = ATR_FALLBACK * a; stopa = fp - d * sda; tgta = fp + d * 2.0 * sda
    ex, win, _ = _walk(O, H, L, C, t0, d, fp, stopa, tgta, N)
    net, gross = _acct(fp, ex, d, sda)
    out["t2a"] = (net, gross, win)
    return out
