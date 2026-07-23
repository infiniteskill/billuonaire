"""yanalyze.py — multidimensional read of the 30 taught trades on REAL data.

User's own words for what they trade: EXTREMES (never mid premium/discount),
sweep retail liquidity first, then valid reversal block + retest; and they
gauge TRENDING vs RANGING. This script measures exactly those axes per trade
from cached Yahoo data and asks: what SITUATION made the best trades?

Per trade, around the resolved entry date, on DAILY (HTF eagle context) + the
finest available LTF (5m/1h):
  regime      = ADX(14) + range-containment -> TREND_UP / TREND_DOWN / RANGE
  entry_pos   = (entry-lo)/(hi-lo) over the pre-entry swing window
                -> PREMIUM (>=.66) / MID (.34-.66) / DISCOUNT (<=.34)
  extreme_ok  = short at PREMIUM  OR long at DISCOUNT  (the user's claim)
  htf_align   = trade dir vs daily trend -> CONTINUATION / REVERSAL / RANGE_FADE
  perf        = mfe_pct, mfe_R (from results.json)
Then groups by (regime, setup_type, extreme_ok) to see what performed.
"""
import sys, json
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, '/home/doom/Public/PROJECT/2026/trader/tools')
from yvalidate import hist

TR = json.loads(Path('/home/doom/Public/PROJECT/2026/trader/tools/ytrades.json').read_text())
RES = {r['id']: r for r in json.load(open('/home/doom/Public/PROJECT/2026/trader/runs/validate/results.json'))}

def adx(d, n=14):
    up = d.high.diff(); dn = -d.low.diff()
    plus = np.where((up > dn) & (up > 0), up, 0.0)
    minus = np.where((dn > up) & (dn > 0), dn, 0.0)
    pc = d.close.shift()
    tr = np.maximum(d.high - d.low, np.maximum((d.high - pc).abs(), (d.low - pc).abs()))
    atr = pd.Series(tr).ewm(alpha=1/n, adjust=False).mean().values
    pdi = 100 * pd.Series(plus).ewm(alpha=1/n, adjust=False).mean().values / (atr + 1e-9)
    mdi = 100 * pd.Series(minus).ewm(alpha=1/n, adjust=False).mean().values / (atr + 1e-9)
    dx = 100 * np.abs(pdi - mdi) / (pdi + mdi + 1e-9)
    return pd.Series(dx).ewm(alpha=1/n, adjust=False).mean().values, pdi, mdi

def regime(d, i, n=40):
    """Classify regime at bar i using ADX + net drift over the prior n bars."""
    a, pdi, mdi = adx(d)
    win = d.iloc[max(0, i-n):i+1]
    adxv = float(a[i]) if a[i] == a[i] else 0.0
    drift = (win.close.iloc[-1] - win.close.iloc[0]) / (win.close.iloc[0] + 1e-9)
    # containment: fraction of closes inside the 20-80 pct band = ranginess
    lo, hi = win.close.quantile(.2), win.close.quantile(.8)
    contain = float(((win.close >= lo) & (win.close <= hi)).mean())
    if adxv >= 22 and abs(drift) > 0.03:
        reg = 'TREND_UP' if drift > 0 else 'TREND_DOWN'
    else:
        reg = 'RANGE'
    return {'adx': round(adxv, 1), 'drift_pct': round(100*drift, 1),
            'contain': round(contain, 2), 'regime': reg}

def pos_in_range(d, i, entry, n=40):
    """Premium/discount location of entry within the pre-entry swing window."""
    win = d.iloc[max(0, i-n):i+1]
    lo, hi = float(win.low.min()), float(win.high.max())
    if hi <= lo: return None, None
    p = (entry - lo) / (hi - lo)
    tag = 'PREMIUM' if p >= 0.66 else 'DISCOUNT' if p <= 0.34 else 'MID'
    return round(p, 2), tag

def setup_type(reg, direction):
    d = 1 if direction == 'long' else -1
    if reg == 'RANGE': return 'RANGE_FADE'
    trend = 1 if reg == 'TREND_UP' else -1
    return 'CONTINUATION' if trend == d else 'REVERSAL'

def analyze(t):
    r = RES.get(t['id'], {})
    res = r.get('resolved')
    if not res: return {**{'id': t['id']}, 'err': 'no year'}
    date = res.split('-', 1)[1]
    d = hist(t['stock'], '1d')
    i = d.index.get_indexer([pd.Timestamp(date)], method='nearest')[0]
    reg = regime(d, i)
    p, ptag = pos_in_range(d, i, t['entry'])
    stype = setup_type(reg['regime'], t['dir'])
    extreme_ok = (t['dir'] == 'short' and ptag == 'PREMIUM') or \
                 (t['dir'] == 'long' and ptag == 'DISCOUNT')
    # finest LTF regime available
    ltf = None
    for tf in ('5m', '1h'):
        try:
            dl = hist(t['stock'], tf)
            j = dl.index.get_indexer([pd.Timestamp(date)], method='nearest')[0]
            if abs((dl.index[j] - pd.Timestamp(date)).days) <= 5:
                ltf = {'tf': tf, **regime(dl, j, n=60)}; break
        except Exception:
            pass
    return {'id': t['id'], 'stock': t['stock'], 'dir': t['dir'], 'resolved': res,
            'd_regime': reg['regime'], 'd_adx': reg['adx'], 'd_drift%': reg['drift_pct'],
            'contain': reg['contain'], 'entry_pos': p, 'pd_tag': ptag,
            'extreme_ok': extreme_ok, 'setup_type': stype,
            'ltf_regime': (ltf['regime'] if ltf else None), 'ltf_tf': (ltf['tf'] if ltf else None),
            'ltf_adx': (ltf['adx'] if ltf else None),
            'swept_ok': r.get('swept_ok'), 'poke_atr': r.get('sweep_poke_atr'),
            'range_pct': r.get('range_pct'), 'contracting': r.get('contracting'),
            'mfe_pct': r.get('mfe_pct'), 'mfe_R': r.get('mfe_R'),
            'target_reached': r.get('target_reached')}

def main():
    rows = [analyze(t) for t in TR]
    print(json.dumps(rows, indent=1, default=str))

if __name__ == '__main__':
    main()
