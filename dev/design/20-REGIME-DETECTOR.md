# 📊 REGIME DETECTOR SERVICE

> **Service**: `regime-detector`
> **Purpose**: Detect current market regime and adapt strategy
> **Key Insight**: A strategy that works in trends FAILS in ranges

---

## 🎯 MARKET REGIMES

```python
from enum import Enum
from dataclasses import dataclass
from typing import Dict, List
import numpy as np

class MarketRegime(Enum):
    STRONG_UPTREND = "STRONG_UPTREND"
    WEAK_UPTREND = "WEAK_UPTREND"
    STRONG_DOWNTREND = "STRONG_DOWNTREND"
    WEAK_DOWNTREND = "WEAK_DOWNTREND"
    TIGHT_RANGE = "TIGHT_RANGE"
    WIDE_RANGE = "WIDE_RANGE"
    EXPLOSIVE = "EXPLOSIVE"
    CHOPPY = "CHOPPY"
    EXPIRY_WEEK = "EXPIRY_WEEK"


@dataclass
class RegimeAnalysis:
    regime: MarketRegime
    confidence: float
    duration: int  # Candles in this regime
    strategy_adjustments: Dict[str, float]
    recommended_approach: str
    dangerous_actions: List[str]


class RegimeDetector:
    """Detect and adapt to market regimes"""
    
    def detect(self, candles: List) -> RegimeAnalysis:
        prices = np.array([float(c.close) for c in candles])
        
        # Calculate ADX for trend strength
        adx = self._calculate_adx(candles)
        
        # Calculate Hurst exponent
        hurst = self._calculate_hurst(prices)
        
        # Calculate ATR percentile
        atr = self._calculate_atr(candles)
        atr_pct = self._atr_percentile(atr, candles)
        
        # Determine regime
        if adx > 25 and hurst > 0.6:
            regime = MarketRegime.STRONG_UPTREND if prices[-1] > prices[-20] else MarketRegime.STRONG_DOWNTREND
        elif adx < 20 and hurst < 0.5:
            regime = MarketRegime.CHOPPY if atr_pct > 0.7 else MarketRegime.TIGHT_RANGE
        elif atr_pct > 0.9:
            regime = MarketRegime.EXPLOSIVE
        else:
            regime = MarketRegime.WEAK_UPTREND if prices[-1] > prices[-20] else MarketRegime.WEAK_DOWNTREND
        
        return RegimeAnalysis(
            regime=regime,
            confidence=self._calculate_conf(adx, hurst),
            duration=self._count_duration(candles, regime),
            strategy_adjustments=self._get_adjustments(regime),
            recommended_approach=self._get_approach(regime),
            dangerous_actions=self._get_dangers(regime)
        )
    
    def _get_adjustments(self, regime: MarketRegime) -> Dict:
        adjustments = {
            MarketRegime.STRONG_UPTREND: {'size': 1.0, 'stop': 1.0, 'target': 1.5, 'reversals': 0.5},
            MarketRegime.CHOPPY: {'size': 0.5, 'stop': 1.5, 'target': 0.7, 'reversals': 1.0},
            MarketRegime.EXPLOSIVE: {'size': 0.3, 'stop': 2.0, 'target': 2.0, 'reversals': 0.0},
            MarketRegime.TIGHT_RANGE: {'size': 0.0, 'wait': True},  # DON'T TRADE
        }
        return adjustments.get(regime, {'size': 1.0})
    
    def _get_dangers(self, regime: MarketRegime) -> List[str]:
        dangers = {
            MarketRegime.STRONG_UPTREND: ["Don't short", "Don't fade highs", "Don't use tight stops"],
            MarketRegime.CHOPPY: ["Don't trend follow", "Don't add to winners", "Don't expect continuation"],
            MarketRegime.EXPLOSIVE: ["Don't use normal size", "Don't use close stops"],
            MarketRegime.TIGHT_RANGE: ["Don't trade - wait for breakout"],
        }
        return dangers.get(regime, [])
    
    def _calculate_hurst(self, prices: np.ndarray) -> float:
        """H > 0.5 = trending, H < 0.5 = mean-reverting"""
        if len(prices) < 20:
            return 0.5
        
        lags = range(2, min(20, len(prices)//2))
        rs_values = []
        
        for lag in lags:
            chunks = [prices[i:i+lag] for i in range(0, len(prices)-lag, lag)]
            for chunk in chunks:
                if len(chunk) > 1:
                    mean, std = np.mean(chunk), np.std(chunk)
                    if std > 0:
                        cumsum = np.cumsum(chunk - mean)
                        R = np.max(cumsum) - np.min(cumsum)
                        rs_values.append(R / std)
        
        if not rs_values:
            return 0.5
        
        return float(np.clip(np.mean(rs_values) / 10, 0, 1))
```

---

## ✅ ACCEPTANCE CRITERIA

- [ ] Detect 8+ regime types
- [ ] Calculate ADX for trend strength
- [ ] Calculate Hurst for persistence
- [ ] Provide strategy adjustments per regime
- [ ] Warn about dangerous actions
