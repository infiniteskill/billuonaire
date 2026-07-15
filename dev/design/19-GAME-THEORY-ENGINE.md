# 🎮 GAME THEORY ENGINE

> **Service**: `game-theory-engine`
> **Purpose**: Model the market as an adversarial game
> **Philosophy**: Think like the HUNTER, not the HUNTED

---

## 🎯 THE GAME

```
╔═══════════════════════════════════════════════════════════════════════╗
║   The market is NOT random. It's a GAME.                              ║
║   THEY need your stops. THEY create fake moves.                       ║
║   But WE can learn to THINK like them.                                ║
╚═══════════════════════════════════════════════════════════════════════╝
```

---

## 📊 PLAYER MODELS

```python
from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Optional
from decimal import Decimal

class MarketPlayer(Enum):
    RETAIL_FOMO = "RETAIL_FOMO"
    SMART_MONEY = "SMART_MONEY"
    MARKET_MAKER = "MARKET_MAKER"
    HFT = "HFT"
    FII = "FII"
    DII = "DII"


class GameTheoryEngine:
    """Model market as multi-player game"""
    
    def predict_liquidity_hunt(self, market_state: Dict) -> Dict:
        """Where will they hunt stops next?"""
        
        targets = []
        
        # Equal lows = obvious stops
        for level in market_state.get('equal_lows', []):
            targets.append({
                'level': level,
                'type': 'EQUAL_LOWS',
                'probability': 0.8,
            })
        
        # PDL/PDH
        if market_state.get('pdl'):
            targets.append({
                'level': market_state['pdl'],
                'type': 'PDL',
                'probability': 0.7,
            })
        
        return {'targets': targets, 'strategy': 'Wait for sweep, then trade reversal'}
    
    def find_trapped_traders(self, candles: List, price: Decimal) -> Dict:
        """Find where traders are trapped (losing positions)"""
        
        trapped = {'longs': [], 'shorts': []}
        current = float(price)
        
        for c in candles[-50:]:
            if float(c.high) > current * 1.01:
                trapped['longs'].append(float(c.high))
            if float(c.low) < current * 0.99:
                trapped['shorts'].append(float(c.low))
        
        return trapped
    
    def calculate_optimal_response(self, state: Dict) -> Dict:
        """What should WE do given game state?"""
        
        hunt = self.predict_liquidity_hunt(state)
        
        if hunt['targets'] and hunt['targets'][0]['probability'] > 0.7:
            return {
                'action': 'WAIT_FOR_SWEEP',
                'rationale': 'Hunt likely. Wait for completion.',
                'direction': 'OPPOSITE_OF_HUNT'
            }
        
        return {'action': 'WAIT', 'rationale': 'No clear edge'}
```

---

## ✅ ACCEPTANCE CRITERIA

- [ ] Predict liquidity hunt targets
- [ ] Find trapped traders
- [ ] Calculate optimal response
- [ ] Think like the HUNTER
