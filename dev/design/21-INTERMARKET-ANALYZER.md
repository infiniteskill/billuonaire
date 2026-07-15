# 🌐 INTERMARKET ANALYZER

> **Service**: `intermarket-analyzer`
> **Purpose**: Analyze correlations and global context
> **Key Insight**: NIFTY doesn't trade in isolation

---

## 🎯 CORRELATION ANALYSIS

```python
from dataclasses import dataclass
from typing import Dict, List, Optional
from decimal import Decimal
import numpy as np

@dataclass
class GlobalContext:
    """Complete global market context"""
    
    # Pre-market indicators
    sgx_nifty: Optional[float] = None
    sgx_nifty_change: Optional[float] = None
    
    # Global markets
    dow_futures: Optional[float] = None
    nasdaq_futures: Optional[float] = None
    
    # Asian context
    nikkei_change: Optional[float] = None
    hang_seng_change: Optional[float] = None
    
    # Risk indicators
    india_vix: Optional[float] = None
    vix_percentile: Optional[float] = None
    
    # Dollar strength
    dxy: Optional[float] = None
    usdinr: Optional[float] = None
    
    # Commodities
    crude_oil: Optional[float] = None
    gold: Optional[float] = None
    
    # FII/DII
    fii_net: Optional[float] = None  # Positive = buying
    dii_net: Optional[float] = None
    
    # Calculated
    global_sentiment: str = "NEUTRAL"
    risk_mode: str = "NEUTRAL"


class IntermarketAnalyzer:
    """Analyze correlations between markets"""
    
    # Known correlations
    CORRELATIONS = {
        'NIFTY_BANKNIFTY': 0.85,
        'NIFTY_SGX': 0.95,
        'NIFTY_DOW': 0.60,
        'NIFTY_VIX': -0.70,
        'NIFTY_DXY': -0.40,
    }
    
    def get_global_context(self) -> GlobalContext:
        """Gather all global context"""
        
        ctx = GlobalContext()
        
        # Would fetch real data from APIs
        ctx.sgx_nifty = self._get_sgx_nifty()
        ctx.india_vix = self._get_india_vix()
        ctx.fii_net = self._get_fii_dii()['fii']
        ctx.dii_net = self._get_fii_dii()['dii']
        
        # Calculate sentiment
        ctx.global_sentiment = self._calculate_sentiment(ctx)
        ctx.risk_mode = self._determine_risk_mode(ctx)
        
        return ctx
    
    def _calculate_sentiment(self, ctx: GlobalContext) -> str:
        """Calculate overall global sentiment"""
        
        score = 0
        
        # SGX indication
        if ctx.sgx_nifty_change:
            score += ctx.sgx_nifty_change * 10
        
        # DOW impact
        if ctx.dow_futures:
            score += ctx.dow_futures * 5
        
        # VIX (inverse)
        if ctx.india_vix:
            if ctx.india_vix > 20:
                score -= 2
            elif ctx.india_vix < 14:
                score += 2
        
        # FII flow
        if ctx.fii_net:
            if ctx.fii_net > 500:
                score += 3
            elif ctx.fii_net < -500:
                score -= 3
        
        if score > 3:
            return "BULLISH"
        elif score < -3:
            return "BEARISH"
        return "NEUTRAL"
    
    def _determine_risk_mode(self, ctx: GlobalContext) -> str:
        """Risk-on or Risk-off environment?"""
        
        # Risk-off indicators
        if ctx.india_vix and ctx.india_vix > 22:
            return "RISK_OFF"
        
        if ctx.gold and ctx.gold > 0.5:  # Gold up > 0.5%
            return "RISK_OFF"
        
        if ctx.dxy and ctx.dxy > 0.3:  # Dollar strengthening
            return "RISK_OFF"
        
        return "RISK_ON"
    
    def check_divergence(self, nifty_direction: str, ctx: GlobalContext) -> Optional[str]:
        """Check for divergence between correlated markets"""
        
        divergences = []
        
        # NIFTY vs BANKNIFTY
        banknifty_dir = self._get_banknifty_direction()
        if nifty_direction != banknifty_dir:
            divergences.append("NIFTY/BANKNIFTY divergence")
        
        # NIFTY vs SGX
        if ctx.sgx_nifty_change:
            sgx_dir = "BULLISH" if ctx.sgx_nifty_change > 0 else "BEARISH"
            if nifty_direction != sgx_dir:
                divergences.append("Diverging from SGX indication")
        
        if divergences:
            return " | ".join(divergences)
        return None
    
    def get_correlation_edge(self, ctx: GlobalContext) -> Optional[Dict]:
        """Find trading edge from correlations"""
        
        # If SGX strongly bullish but NIFTY hasn't moved
        if ctx.sgx_nifty_change and ctx.sgx_nifty_change > 0.5:
            return {
                'edge': 'SGX_LEAD',
                'direction': 'LONG',
                'confidence': 0.7,
                'rationale': 'SGX indicating gap up potential'
            }
        
        # If FII strongly buying
        if ctx.fii_net and ctx.fii_net > 1000:
            return {
                'edge': 'FII_FLOW',
                'direction': 'LONG',
                'confidence': 0.6,
                'rationale': 'Strong FII buying - institutional support'
            }
        
        return None
```

---

## ✅ ACCEPTANCE CRITERIA

- [ ] Track all major correlated markets
- [ ] Calculate global sentiment
- [ ] Detect risk-on/risk-off
- [ ] Identify divergences
- [ ] Find correlation-based edges
