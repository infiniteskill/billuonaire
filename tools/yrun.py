"""yrun.py — resolve each taught trade's YEAR then validate on real Yahoo data.

Charts show only DD/MM. resolve_year() lists candidate years where the stock
traded at the drawn entry in the drawn month, constrained to the drawn price
ERA. Each candidate is validated on daily; the winner = the year whose real
structure matches (swept extreme + moved to target). Recent (>= 2026-05-04)
trades are ALSO validated on 5m (the fine edge). Writes runs/validate/REPORT.md.
"""
import sys, json
from pathlib import Path
import pandas as pd
sys.path.insert(0, '/home/doom/Public/PROJECT/2026/trader/tools')
from yvalidate import resolve_year, validate, hist

TRADES = json.loads(Path('/home/doom/Public/PROJECT/2026/trader/tools/ytrades.json').read_text())
FIVE_MIN_FROM = pd.Timestamp('2026-05-04')
H1_FROM = pd.Timestamp('2023-08-10')

def score(v):
    """Rank a candidate-year daily validation: does it look like the setup?"""
    if 'error' in v: return -9
    s = 0
    s += 2 if v.get('swept_ok') else 0
    s += 3 if v.get('target_reached') else 0
    s += min(v.get('mfe_R') or 0, 10) * 0.3
    return round(s, 2)

def candidates(t):
    """Year candidates constrained to the drawn price era."""
    lo, hi = t['era']
    cy = resolve_year(t['stock'], t['month'], t['entry'], t.get('day'))
    return {y: v for y, v in cy.items() if lo <= v[1] <= hi} or cy

def run_one(t):
    cy = candidates(t)
    if not cy:
        return {**t, 'resolved': None, 'note': 'no year matches era', 'best': None}
    scored = []
    for y, (dt, cl) in sorted(cy.items()):
        v = validate(t['stock'], dt, t['dir'], t['entry'], t.get('sl'),
                     t.get('target'), t.get('swept'), tf='1d')
        scored.append((score(v), y, dt, v))
    scored.sort(reverse=True)
    best_score, by, bdate, bv = scored[0]
    row = {'id': t['id'], 'stock': t['stock'], 'dir': t['dir'],
           'drawn': f"{t['day']:02d}/{t['month']:02d}", 'entry': t['entry'],
           'cand_years': sorted(cy), 'resolved': f"{by}-{bdate}", 'score': best_score,
           'swept_ok': bv.get('swept_ok'), 'sweep_poke_atr': bv.get('sweep_poke_atr'),
           'range_pct': bv.get('range_pct'), 'contracting': bv.get('contracting'),
           'target_reached': bv.get('target_reached'), 'target_hit': bv.get('target_hit'),
           'mfe_pct': bv.get('mfe_pct'), 'mfe_R': bv.get('mfe_R'),
           'mae_atr': bv.get('mae_atr'), 'sl_breach_daily': bv.get('sl_breach_daily')}
    # fine TF if recent enough
    bts = pd.Timestamp(bdate)
    if bts >= FIVE_MIN_FROM:
        try:
            v5 = validate(t['stock'], bdate, t['dir'], t['entry'], t.get('sl'),
                          t.get('target'), t.get('swept'), tf='5m', lookback=8, forward=15)
            row['fine'] = '5m'; row['fine_swept'] = v5.get('swept_ok')
            row['fine_target'] = v5.get('target_reached'); row['fine_mfe_R'] = v5.get('mfe_R')
            row['fine_sl_breach'] = v5.get('sl_breach_daily')
        except Exception as e:
            row['fine'] = f'5m-err:{e}'
    elif bts >= H1_FROM:
        try:
            v1 = validate(t['stock'], bdate, t['dir'], t['entry'], t.get('sl'),
                          t.get('target'), t.get('swept'), tf='1h', lookback=15, forward=40)
            row['fine'] = '1h'; row['fine_swept'] = v1.get('swept_ok')
            row['fine_target'] = v1.get('target_reached'); row['fine_mfe_R'] = v1.get('mfe_R')
        except Exception as e:
            row['fine'] = f'1h-err:{e}'
    else:
        row['fine'] = 'daily-only(pre-2023-08)'
    return row

def main():
    rows = [run_one(t) for t in TRADES]
    print(json.dumps(rows, indent=1, default=str))

if __name__ == '__main__':
    main()
