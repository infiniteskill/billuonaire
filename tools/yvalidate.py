"""yvalidate.py — validate taught trades against real Yahoo OHLCV.

Each taught trade (hand-drawn on Kite) is checked on real data at the finest TF
Yahoo still serves for that date:
  daily  = all history (macro: swept extreme, range, target, magnitude, dir)
  1h     = back ~2023-08 (HTF zone / finer sweep)
  15m/5m = last 60d only (fine edge — tiny SL/OB/FVG) — recent trades only
Charts rarely show the YEAR, so resolve_year() pins it by (month, price era):
find the session where the stock traded at the drawn price in the drawn month;
the surrounding structure disambiguates when >1 year qualifies.

Honest limit: a 3-5pt intraday SL is INVISIBLE on daily. Daily confirms the
setup EXISTED (extreme swept, range, move to target, right direction, size) —
NOT whether the tiny structural stop held. That needs 5m, only < 60d old.
"""
import sys, json, warnings, time
from pathlib import Path
import numpy as np, pandas as pd, yfinance as yf
warnings.filterwarnings('ignore')

CACHE = Path('/home/doom/Public/PROJECT/2026/trader/data/yahoo'); CACHE.mkdir(parents=True, exist_ok=True)

def hist(sym, interval='1d', period='max'):
    """Cached Yahoo pull, lower-cased OHLCV cols, tz-naive index."""
    f = CACHE / f'{sym}_{interval}.csv'
    if f.exists():
        d = pd.read_csv(f, index_col=0, parse_dates=True)
    else:
        d = yf.Ticker(f'{sym}.NS').history(period=period, interval=interval, auto_adjust=False)
        d.columns = [c.lower() for c in d.columns]
        d = d[['open', 'high', 'low', 'close', 'volume']]
        d.to_csv(f); time.sleep(0.5)
    d.index = pd.to_datetime(d.index, utc=True).tz_localize(None)
    return d

def resolve_year(sym, month, price, day=None):
    """Return candidate sessions (date, close) where `sym` traded at `price`
    in calendar `month` — one per qualifying year. price within [low,high]."""
    d = hist(sym, '1d')
    m = d[d.index.month == month]
    hit = m[(m.low <= price) & (m.high >= price)]
    if day:  # narrow to +-4 days of drawn day-of-month
        hit = hit[abs(hit.index.day - day) <= 4]
    out = {}
    for ts, r in hit.iterrows():
        out.setdefault(ts.year, (ts.date(), float(r.close)))  # first session/yr
    return out

def _atr(d, n=14):
    pc = d.close.shift(); tr = np.maximum(d.high - d.low,
        np.maximum((d.high - pc).abs(), (d.low - pc).abs()))
    return tr.rolling(n).mean()

def validate(sym, date, direction, entry, sl=None, target=None,
             swept=None, tf='1d', lookback=40, forward=60):
    """Check the setup on real data around `date`. Returns a dict of findings.
    direction: 'long'/'short'. Prices as drawn. tf: '1d' or '1h'."""
    d = hist(sym, tf)
    ts = pd.Timestamp(date)
    d = d[(d.index >= ts - pd.Timedelta(days=lookback*2)) &
          (d.index <= ts + pd.Timedelta(days=forward*2))]
    if len(d) < 5:
        return {'sym': sym, 'date': str(date), 'error': 'no data in window'}
    i = d.index.get_indexer([ts], method='nearest')[0]
    atr = _atr(d).iloc[i]
    sgn = 1 if direction == 'long' else -1
    pre = d.iloc[max(0, i-lookback):i+1]
    post = d.iloc[i:i+forward+1]
    r = {'sym': sym, 'date': str(d.index[i].date()), 'tf': tf, 'dir': direction,
         'atr': round(float(atr), 2) if atr == atr else None,
         'bars_pre': len(pre), 'bars_post': len(post)}
    # --- range maturity before entry: width/ATR contraction + touch proxy ---
    if len(pre) >= 10:
        w = pre.high.max() - pre.low.min()
        r['range_pct'] = round(100 * w / pre.close.mean(), 1)
        r['range_atr'] = round(float(w / atr), 1) if atr == atr else None
        first_half = pre.iloc[:len(pre)//2]; second = pre.iloc[len(pre)//2:]
        r['contracting'] = bool((second.high - second.low).mean() <
                                (first_half.high - first_half.low).mean())
    # --- swept extreme: did a wick pierce `swept` then close back? ---
    if swept:
        win = d.iloc[max(0, i-lookback):i+3]
        if direction == 'short':  # sweep a high
            pierced = win[(win.high > swept) & (win.close < swept)]
        else:                     # sweep a low
            pierced = win[(win.low < swept) & (win.close > swept)]
        r['swept_ok'] = bool(len(pierced))
        if len(pierced):
            r['sweep_date'] = str(pierced.index[0].date())
            r['sweep_poke_atr'] = round(float(abs(
                (pierced.high.max() if direction=='short' else pierced.low.min()) - swept)/atr), 2) if atr==atr else None
    # --- forward outcome: MFE / MAE from entry, target reach, SL hold ---
    e = entry if entry else float(d.close.iloc[i])
    fav = (post.high - e) * sgn if direction == 'long' else (e - post.low) * sgn * sgn
    fav = ((post.high - e) if direction == 'long' else (e - post.low))
    adv = ((e - post.low) if direction == 'long' else (post.high - e))
    r['mfe_pt'] = round(float(fav.max()), 2); r['mae_pt'] = round(float(adv.max()), 2)
    r['mfe_pct'] = round(100*float(fav.max())/e, 1)
    if atr == atr and atr:
        r['mfe_atr'] = round(float(fav.max())/atr, 1); r['mae_atr'] = round(float(adv.max())/atr, 1)
    if sl:
        risk = abs(e - sl)
        r['risk_pt'] = round(risk, 2)
        r['mfe_R'] = round(float(fav.max())/risk, 1) if risk else None
        # daily SL-hold (coarse): did any post low/high breach SL before target?
        breach = post[(post.low <= sl) if direction=='long' else (post.high >= sl)]
        r['sl_breach_daily'] = str(breach.index[0].date()) if len(breach) else None
    if target:
        reach = post[(post.high >= target) if direction=='long' else (post.low <= target)]
        r['target_hit'] = str(reach.index[0].date()) if len(reach) else None
        r['target_reached'] = bool(len(reach))
    return r

if __name__ == '__main__':
    trades = json.loads(Path(sys.argv[1]).read_text())
    out = []
    for t in trades:
        try:
            out.append(validate(**t))
        except Exception as e:
            out.append({'sym': t.get('sym'), 'error': str(e)})
    print(json.dumps(out, indent=2, default=str))
