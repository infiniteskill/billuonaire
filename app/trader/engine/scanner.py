"""Scanner: per-symbol stock-fit score used by `watch --auto`.

fit() blends five 0-1 components into a 0-100 score. Missing/insufficient
data yields a neutral 0.5 component (no real prior yet, so we don't punish).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from statistics import mean, pstdev

from trader.models.candle import Candle, Timeframe
from trader.models.market import MarketSpec
from trader.store.candles import CandleStore

_WEIGHTS = {"cleanliness": .25, "energy": .20, "liquidity": .20,
            "setup": .20, "context": .15}
_NEUTRAL = 0.5
_ATR_WINDOW = 5


def _all(store: CandleStore, symbol: str, tf: Timeframe,
        spec: MarketSpec) -> list[Candle]:
    """Every closed candle of tf for symbol (view pushed far into the future)."""
    far = datetime.now(spec.tzinfo) + timedelta(days=3650)
    return store.view(symbol, far).last(10_000, tf)


def has_data(symbol: str, store: CandleStore, spec: MarketSpec) -> bool:
    """True iff the store holds any D1 candle for symbol (used by --auto)."""
    return bool(_all(store, symbol, Timeframe.D1, spec))


def _cov_inv(values: list[float]) -> float | None:
    """1 - coefficient of variation, clamped [0,1]; None if <2 samples or mean 0."""
    if len(values) < 2 or mean(values) == 0:
        return None
    return max(0.0, min(1.0, 1 - pstdev(values) / mean(values)))


def _rolling_atr(d1: list[Candle], window: int = _ATR_WINDOW) -> list[float]:
    """Rolling mean-range ATR series over D1 candles (trailing window)."""
    ranges = [float(c.range) for c in d1]
    return [mean(ranges[max(0, i - window + 1): i + 1]) for i in range(len(ranges))]


def _cleanliness(d1: list[Candle], m5: list[Candle]) -> float:
    parts = []
    if len(d1) >= 2:
        avg_range = mean(float(c.range) for c in d1)
        gaps = sum(1 for i in range(1, len(d1))                  # gap freq
                  if avg_range and abs(float(d1[i].open - d1[i - 1].close)) > avg_range)
        parts.append(1 - gaps / (len(d1) - 1))
    swing = _cov_inv([float(c.range) for c in m5])                # swing-size stddev
    atr_stab = _cov_inv(_rolling_atr(d1))                          # ATR stability
    parts += [v for v in (swing, atr_stab) if v is not None]
    return mean(parts) if parts else _NEUTRAL


def _energy(d1: list[Candle]) -> float:
    """D1 ATR% of price, peaking at 1.0 at 2.5%, 0 at/outside 1%-4%."""
    if not d1 or float(d1[-1].close) == 0:
        return _NEUTRAL
    atr_pct = _rolling_atr(d1)[-1] / float(d1[-1].close) * 100
    if atr_pct <= 1 or atr_pct >= 4:
        return 0.0
    return (atr_pct - 1) / 1.5 if atr_pct <= 2.5 else (4 - atr_pct) / 1.5


def _liquidity(m5: list[Candle], qty_notional: float | None) -> float:
    """Avg M5 notional vs qty_notional; >=20x is full liquidity."""
    if not m5 or not qty_notional:
        return _NEUTRAL
    avg_notional = mean(float(c.volume) * float(c.close) for c in m5)
    return min(1.0, avg_notional / qty_notional / 20)


def _setup(d1: list[Candle]) -> float:
    """Fraction of the last 20 D1 candles making a new 5-day high/low
    (liquidity-draw proxy in place of untapped-level counting)."""
    window = d1[-20:]
    if len(window) < 6:
        return _NEUTRAL
    hits = sum(1 for i in range(5, len(window))
              if window[i].high > max(p.high for p in window[i - 5:i])
              or window[i].low < min(p.low for p in window[i - 5:i]))
    return hits / (len(window) - 5)


def fit(symbol: str, store: CandleStore, spec: MarketSpec,
       qty_notional: float | None = None) -> dict:
    """Stock-fit score (0-100) + its five 0-1 components (see module docstring)."""
    d1, m5 = _all(store, symbol, Timeframe.D1, spec), _all(store, symbol, Timeframe.M5, spec)
    components = {
        "cleanliness": _cleanliness(d1, m5),
        "energy": _energy(d1),
        "liquidity": _liquidity(m5, qty_notional),
        "setup": _setup(d1),
        "context": _NEUTRAL,
    }
    score = sum(components[k] * w for k, w in _WEIGHTS.items()) * 100
    return {"score": score, "components": components}
