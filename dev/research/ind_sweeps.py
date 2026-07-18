"""Faithful LuxAlgo 'Market Structure with Inducements & Sweeps' port.
swings(len): fractal confirmed len bars after the pivot (long=CHoCH pivots,
short=IDM pivots). CHoCH = close crosses last confirmed swing -> os flips,
resets trailing max/min. IDM = price sweeps the short-swing extreme in the
CHoCH direction (inducement grab). BOS = close then breaks the trailing
max/min established since the CHoCH -> only fires after IDM has been swept.
"""
import sys
sys.path.insert(0, "/tmp/claude-1000/-home-doom-Public-PROJECT-2026-trader/cafd7565-a8b2-42b9-9d06-48e002e5af54/scratchpad")
from h2hlib import report


def swings(H, L, ln):
    n = len(H)
    top = [None] * n; topx = [None] * n
    btm = [None] * n; btmx = [None] * n
    os_ = 0; cur_topx = None; cur_btmx = None
    for i in range(n):
        prev = os_
        if i >= ln:
            w_h = H[i - ln + 1:i + 1]; w_l = L[i - ln + 1:i + 1]
            upper = max(w_h); lower = min(w_l)
            hlen = H[i - ln]; llen = L[i - ln]
            os_ = 0 if hlen > upper else (1 if llen < lower else prev)
        if os_ == 0 and prev != 0:
            top[i] = H[i - ln]; cur_topx = i - ln
        if os_ == 1 and prev != 1:
            btm[i] = L[i - ln]; cur_btmx = i - ln
        topx[i] = cur_topx; btmx[i] = cur_btmx
    return top, topx, btm, btmx


def simulate(m5, ln, shortLen=3):
    """Port of the Pine script's per-bar state machine. Returns
    (idm_events, bos_events), each a list of (bar_index, direction)."""
    H = [float(c.high) for c in m5]; L = [float(c.low) for c in m5]; C = [float(c.close) for c in m5]
    top, topx, btm, btmx = swings(H, L, ln)
    stop, stopx, sbtm, sbtmx = swings(H, L, shortLen)
    os = 0; top_crossed = False; btm_crossed = False
    maxv = minv = None; topy = btmy = None
    stop_crossed = False; sbtm_crossed = False
    stopy = sbtmy = None
    idm_events = []; bos_events = []
    for i in range(len(m5)):
        prev_os = os
        if top[i] is not None: topy = top[i]; top_crossed = False
        if btm[i] is not None: btmy = btm[i]; btm_crossed = False
        if topy is not None and C[i] > topy and not top_crossed:
            os = 1; top_crossed = True
        if btmy is not None and C[i] < btmy and not btm_crossed:
            os = 0; btm_crossed = True
        if os != prev_os:
            maxv = H[i]; minv = L[i]
            stop_crossed = False; sbtm_crossed = False
        if stop[i] is not None: stopy = stop[i]
        if sbtm[i] is not None: sbtmy = sbtm[i]
        # Bullish IDM / BOS
        if sbtmy is not None and L[i] < sbtmy and not sbtm_crossed and os == 1 and sbtmy != btmy:
            sbtm_crossed = True
            idm_events.append((i, 1))
        if maxv is not None and C[i] > maxv and sbtm_crossed and os == 1:
            bos_events.append((i, 1))
            sbtm_crossed = False
        # Bearish IDM / BOS
        if stopy is not None and H[i] > stopy and not stop_crossed and os == 0 and stopy != topy:
            stop_crossed = True
            idm_events.append((i, -1))
        if minv is not None and C[i] < minv and stop_crossed and os == 0:
            bos_events.append((i, -1))
            stop_crossed = False
        if maxv is not None: maxv = max(H[i], maxv)
        if minv is not None: minv = min(L[i], minv)
    return idm_events, bos_events


def mk_idm(ln):
    return lambda m5, atrs: simulate(m5, ln)[0]


def mk_bos(ln):
    return lambda m5, atrs: simulate(m5, ln)[1]


report("IDM_entry_len50", mk_idm(50))
report("BOS_after_IDM_len50", mk_bos(50))
report("IDM_entry_len20", mk_idm(20))
