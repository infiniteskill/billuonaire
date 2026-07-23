"""y5sim.py — real 5m fill-through path-sim for the RECENT taught trades.

For trades resolved to >= 2026-05-04, Yahoo still serves native 5m. This is the
ONLY window free data gives onto the taught edge's dominant lever: does the TINY
structural stop survive to target on the real intrabar path (gap-aware)?

Per trade: find the 5m bar that first triggers the drawn entry (price reaches
entry in the trade direction) on/after the resolved date; then walk 5m bars —
  open beyond SL  -> stopped AT OPEN (gap-through, the fill-through killer)
  else SL hit intrabar (assumed BEFORE target, conservative) -> -1R
  else target hit intrabar -> +R(target)
Report first-hit, R, bars held, max adverse (R) before exit.
"""
import sys, json
from pathlib import Path
import pandas as pd
sys.path.insert(0, '/home/doom/Public/PROJECT/2026/trader/tools')
from yvalidate import hist

TR = json.loads(Path('/home/doom/Public/PROJECT/2026/trader/tools/ytrades.json').read_text())
RES = {r['id']: r for r in json.load(open('/home/doom/Public/PROJECT/2026/trader/runs/validate/results.json'))}

def sim(t, date, hold_bars=800):
    d = hist(t['stock'], '5m')
    ts = pd.Timestamp(date)
    d = d[(d.index >= ts - pd.Timedelta(days=2)) & (d.index <= ts + pd.Timedelta(days=40))]
    if len(d) < 20: return {'id': t['id'], 'err': 'thin 5m'}
    e, sl, tgt = t['entry'], t['sl'], t['target']
    long = t['dir'] == 'long'
    risk = abs(e - sl); rew = abs(tgt - e)
    # entry trigger: price reaches entry in dir
    trig = d[(d.low <= e) if long else (d.high >= e)]
    if not len(trig): return {'id': t['id'], 'err': 'entry never touched in window'}
    i0 = d.index.get_loc(trig.index[0])
    path = d.iloc[i0+1:i0+1+hold_bars]
    mae = 0.0
    for _, b in path.iterrows():
        # gap-through stop at open
        if (long and b.open <= sl) or (not long and b.open >= sl):
            return _r(t, e, sl, tgt, 'STOP_GAP', b.name, i0, d, mae, long, risk)
        adv = (e - b.low) if long else (b.high - e)
        mae = max(mae, adv / risk)
        hit_sl = (b.low <= sl) if long else (b.high >= sl)
        hit_tg = (b.high >= tgt) if long else (b.low <= tgt)
        if hit_sl:  # stop-before-target (conservative)
            return _r(t, e, sl, tgt, 'STOP', b.name, i0, d, mae, long, risk)
        if hit_tg:
            return _r(t, e, sl, tgt, 'TARGET', b.name, i0, d, mae, long, risk)
    return _r(t, e, sl, tgt, 'TIMEOUT', path.index[-1] if len(path) else None, i0, d, mae, long, risk)

def _r(t, e, sl, tgt, outcome, exit_ts, i0, d, mae, long, risk):
    R = {'TARGET': round(abs(tgt-e)/risk, 1), 'STOP': -1.0, 'STOP_GAP': None,
         'TIMEOUT': None}[outcome]
    entry_ts = d.index[i0]
    bars = None
    if exit_ts is not None:
        bars = d.index.get_loc(exit_ts) - i0
    return {'id': t['id'], 'stock': t['stock'], 'dir': t['dir'],
            'entry_bar': str(entry_ts), 'outcome': outcome, 'R': R,
            'bars_held': bars, 'mae_R': round(mae, 2),
            'risk_pt': round(risk, 2), 'rr_target': round(abs(tgt-e)/risk, 1)}

def main():
    out = []
    for t in TR:
        r = RES.get(t['id'], {})
        res = r.get('resolved')
        if not res or res.split('-', 1)[1] < '2026-05-04':
            continue
        date = res.split('-', 1)[1]
        out.append(sim(t, date))
    print(json.dumps(out, indent=1, default=str))

if __name__ == '__main__':
    main()
