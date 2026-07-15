# 🌐 Web Dashboard Service Design

> **Service**: `web-dashboard`
> **Purpose**: Real-time visualization and control interface
> **Stack**: React + TradingView Lightweight Charts

---

## 🎯 Features

1. **Live Chart** with all indicators overlaid
2. **Signal Panel** with active and historical signals
3. **Context Panel** showing kill zones, phases, risk
4. **Prediction Overlay** with projected candles
5. **Failure Dashboard** for learning review
6. **Manipulation Alerts** real-time warnings
7. **System Health** monitoring

---

## 📐 Pages & Components

### Page 1: Main Dashboard

```
┌─────────────────────────────────────────────────────────────────────────┐
│  🎯 RADAR Dashboard          NIFTY 50  22,456.75 (+0.42%)    🟢 LIVE   │
├─────────────────┬───────────────────────────────────────────────────────┤
│                 │                                                        │
│   CONTEXT       │              📈 CHART                                  │
│   ──────────    │                                                        │
│   Phase: 🟡 M   │   [TradingView Lightweight Chart with:]               │
│   Bias: 📈 BUY  │   - OHLC candles                                      │
│   Time: 11:30   │   - Swing points marked                               │
│   Zone: ✅ SAFE │   - Order blocks (rectangles)                         │
│   Risk: 32/100  │   - FVGs (shaded areas)                               │
│                 │   - Liquidity levels (dotted lines)                   │
│   ──────────    │   - Fibonacci OTE zone (shaded 61.8-79%)              │
│   KILL ZONES    │   - Projected candles (dashed, different color)      │
│   🔴 9:15-10:30 │   - Signal entry zones (highlighted)                  │
│   🟡 13:30-14:00│                                                        │
│   🔴 14:45-15:30│                                                        │
│                 │                                                        │
├─────────────────┼───────────────────────────────────────────────────────┤
│   ACTIVE SIGNALS                                                         │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │  🟢 LONG  22,380-22,400  Conf: 78%  R:R 2.5  ⏰ 45min ago       │   │
│   │     Entry: OB + Sweep + HTF Aligned                              │   │
│   │     SL: 22,340  TP1: 22,480  TP2: 22,550                        │   │
│   └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Page 2: Predictions View

```
┌─────────────────────────────────────────────────────────────────────────┐
│  🔮 Predictions              NIFTY 50                       Next Day    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   [Chart with historical candles + projected candles concatenated]       │
│                                                                          │
│   ══════════════════════════════════════════════════════════════════    │
│   │ Actual Data (solid)  │  PROJECTED (dashed, with confidence bands) │  │
│   ══════════════════════════════════════════════════════════════════    │
│                                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│   SCENARIOS                                                              │
│   ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐      │
│   │ 🟢 BULLISH       │  │ 🔴 BEARISH       │  │ ⚪ NEUTRAL       │      │
│   │ Prob: 58%        │  │ Prob: 28%        │  │ Prob: 14%        │      │
│   │ Target: 22,580   │  │ Target: 22,280   │  │ Range: ±50pts    │      │
│   │ Based on: Sweep  │  │ Based on: HTF    │  │ Based on: Low    │      │
│   └──────────────────┘  └──────────────────┘  │ confluence       │      │
│                                                └──────────────────┘      │
└─────────────────────────────────────────────────────────────────────────┘
```

### Page 3: Pre-Market Analysis

```
┌─────────────────────────────────────────────────────────────────────────┐
│  🌅 Pre-Market Analysis       For: 2025-02-01 (Tomorrow)                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   KEY LEVELS                    GLOBAL CONTEXT                           │
│   ──────────                    ──────────────                           │
│   PDH: 22,520     🔴            SGX Nifty: 22,480 (+30)                 │
│   PDL: 22,340     🟢            DOW: +0.5%                               │
│   PWH: 22,650     🔴            VIX: 14.2 (Low)                          │
│   PWL: 22,180     🟢            FII/DII: FII -500cr, DII +800cr         │
│   OR: 22,500                                                             │
│                                                                          │
│   SCENARIOS                                                              │
│   ──────────                                                             │
│   📈 Gap Up (60%): If opens above 22,500, watch for PDH test           │
│   📉 Gap Down (25%): If opens below 22,400, PDL sweep likely            │
│   ➡️ Flat (15%): Opening range trade, wait for sweep                    │
│                                                                          │
│   WATCH FOR                                                              │
│   ─────────                                                              │
│   ⚠️  PDL sweep if gap down - LONG opportunity                          │
│   ⚠️  PDH rejection if gap up - potential SHORT                         │
│   ⚠️  Unfilled FVG at 22,380 - magnet level                             │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Page 4: Failure Dashboard

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ❌ Failure Analysis          This Week: 8 Failures                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   FAILURE BREAKDOWN              TOP LESSONS THIS WEEK                   │
│   ─────────────────              ────────────────────                    │
│   🔴 Stop Hunt: 3                1. Avoid entries in kill zone           │
│   🟡 Wrong Phase: 2              2. Wait for sweep before OB entry       │
│   🟠 Weak Structure: 2           3. Check HTF resistance more carefully │
│   ⚪ Volatility: 1                                                       │
│                                                                          │
│   RECENT FAILURES                                                        │
│   ───────────────                                                        │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │ Jan 30, 10:15 - LONG stopped at 22,340                          │   │
│   │ Root Cause: GOT_STOPPED_HUNTED                                   │   │
│   │ What We Missed: PDL had 3 equal lows - obvious target            │   │
│   │ Lesson: Don't long with stops below equal lows                   │   │
│   │ [View Full Forensics] [Apply to Decision Tree]                   │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│   DECISION TREE EVOLUTION                                                │
│   ───────────────────────                                                │
│   Version: 47 (started at v1)                                            │
│   Nodes Added: 23                                                        │
│   Accuracy Improvement: +12% (from 55% to 67%)                          │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Page 5: Signal History

```
┌─────────────────────────────────────────────────────────────────────────┐
│  📚 Signal History            NIFTY 50     Last 30 Days                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   STATS           │  Win Rate: 67%  │  Profit Factor: 2.1  │  Signals: 45│
│                                                                          │
│   ┌────────┬────────┬────────┬────────┬────────┬────────┬────────┐      │
│   │ Date   │ Dir    │ Entry  │ Exit   │ P/L    │ Pattern │ Time   │      │
│   ├────────┼────────┼────────┼────────┼────────┼────────┼────────┤      │
│   │ Jan 31 │ 🟢LONG │ 22,380 │ 22,485 │ +105   │ Sweep+OB│ 11:15  │      │
│   │ Jan 31 │ 🔴SHORT│ 22,520 │ 22,540 │ -20    │ PDH test│ 09:45  │ ❌   │
│   │ Jan 30 │ 🟢LONG │ 22,290 │ 22,410 │ +120   │ PWL swp │ 11:30  │      │
│   │ ...    │ ...    │ ...    │ ...    │ ...    │ ...     │ ...    │      │
│   └────────┴────────┴────────┴────────┴────────┴────────┴────────┘      │
│                                                                          │
│   PERFORMANCE BY PATTERN                                                 │
│   ──────────────────────                                                 │
│   Sweep + OB:      78% win rate (23 signals)                            │
│   FVG Entry:       62% win rate (13 signals)                            │
│   PDH/PDL Break:   55% win rate (9 signals)                             │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 Chart Components

### TradingView Lightweight Charts Integration

```typescript
// chart.tsx
import { createChart, IChartApi, ISeriesApi } from 'lightweight-charts';

interface ChartProps {
  candles: Candle[];
  projectedCandles?: Candle[];
  orderBlocks?: OrderBlock[];
  fvgs?: FairValueGap[];
  swings?: SwingPoint[];
  signals?: Signal[];
  fibLevels?: FibonacciLevel[];
}

export const RadarChart: React.FC<ChartProps> = ({
  candles,
  projectedCandles,
  orderBlocks,
  fvgs,
  swings,
  signals,
  fibLevels
}) => {
  const chartRef = useRef<IChartApi>();
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'>>();
  const projectedSeriesRef = useRef<ISeriesApi<'Candlestick'>>();
  
  useEffect(() => {
    // Create chart
    chartRef.current = createChart(containerRef.current, {
      layout: {
        background: { color: '#0a0a0a' },
        textColor: '#d1d5db',
      },
      grid: {
        vertLines: { color: '#1f2937' },
        horzLines: { color: '#1f2937' },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
      },
    });
    
    // Candlestick series for actual data
    candleSeriesRef.current = chartRef.current.addCandlestickSeries({
      upColor: '#10b981',
      downColor: '#ef4444',
      borderVisible: false,
      wickUpColor: '#10b981',
      wickDownColor: '#ef4444',
    });
    
    // Projected candles (different style)
    if (projectedCandles) {
      projectedSeriesRef.current = chartRef.current.addCandlestickSeries({
        upColor: 'rgba(16, 185, 129, 0.5)',
        downColor: 'rgba(239, 68, 68, 0.5)',
        borderVisible: true,
        borderUpColor: '#10b981',
        borderDownColor: '#ef4444',
      });
    }
  }, []);
  
  // Add Order Blocks as rectangles
  useEffect(() => {
    for (const ob of orderBlocks) {
      const color = ob.type === 'BULLISH' 
        ? 'rgba(16, 185, 129, 0.2)' 
        : 'rgba(239, 68, 68, 0.2)';
      
      chartRef.current.addRect({
        point1: { time: ob.formation_time, price: ob.low },
        point2: { time: 'now', price: ob.high },
        color: color,
        borderColor: color,
      });
    }
  }, [orderBlocks]);
  
  // Add FVGs as shaded areas
  useEffect(() => {
    for (const fvg of fvgs) {
      const color = fvg.type === 'BULLISH'
        ? 'rgba(59, 130, 246, 0.15)'
        : 'rgba(244, 63, 94, 0.15)';
      
      // Draw FVG zone
    }
  }, [fvgs]);
  
  // Add Fibonacci OTE zone
  useEffect(() => {
    if (fibLevels) {
      // OTE zone (61.8% to 79%)
      const oteZone = {
        low: fibLevels.find(f => f.level === 0.618),
        high: fibLevels.find(f => f.level === 0.79),
      };
      
      if (oteZone.low && oteZone.high) {
        // Shade OTE zone in gold/yellow
        chartRef.current.addRect({
          point1: { time: 'start', price: oteZone.low.price },
          point2: { time: 'end', price: oteZone.high.price },
          color: 'rgba(245, 158, 11, 0.15)',
        });
      }
    }
  }, [fibLevels]);
  
  return <div ref={containerRef} className="w-full h-[600px]" />;
};
```

---

## 🎨 Design System

```css
/* globals.css */
:root {
  /* Dark theme colors */
  --bg-primary: #0a0a0a;
  --bg-secondary: #111111;
  --bg-tertiary: #1a1a1a;
  
  /* Text */
  --text-primary: #ffffff;
  --text-secondary: #9ca3af;
  --text-muted: #6b7280;
  
  /* Semantic colors */
  --bullish: #10b981;
  --bullish-muted: rgba(16, 185, 129, 0.2);
  --bearish: #ef4444;
  --bearish-muted: rgba(239, 68, 68, 0.2);
  --neutral: #6b7280;
  
  /* Risk levels */
  --risk-low: #10b981;
  --risk-medium: #f59e0b;
  --risk-high: #f97316;
  --risk-extreme: #ef4444;
  
  /* Special */
  --ote-zone: rgba(245, 158, 11, 0.15);
  --ob-bullish: rgba(16, 185, 129, 0.2);
  --ob-bearish: rgba(239, 68, 68, 0.2);
  --fvg-bullish: rgba(59, 130, 246, 0.15);
  --fvg-bearish: rgba(244, 63, 94, 0.15);
  --sweep-highlight: rgba(168, 85, 247, 0.3);
}
```

---

## 🔌 WebSocket Events

```typescript
// Real-time updates via WebSocket
interface WebSocketEvents {
  // Candle updates
  'candle.new': {
    symbol: string;
    timeframe: string;
    candle: Candle;
  };
  
  // Signal events
  'signal.new': {
    signal: Signal;
  };
  
  'signal.triggered': {
    signalId: string;
    triggerPrice: number;
  };
  
  'signal.outcome': {
    signalId: string;
    outcome: 'TARGET_HIT' | 'STOPPED' | 'EXPIRED';
    pnl: number;
  };
  
  // Context updates
  'context.phase.changed': {
    oldPhase: string;
    newPhase: string;
  };
  
  'context.killzone.entered': {
    zoneName: string;
    dangerLevel: number;
  };
  
  // Alerts
  'alert.new': {
    type: string;
    severity: string;
    message: string;
  };
  
  // Detection events
  'detection.sweep': {
    direction: string;
    level: number;
    quality: number;
  };
  
  'detection.ob.new': {
    type: string;
    high: number;
    low: number;
  };
}
```

---

## ✅ Acceptance Criteria

- [ ] Live chart with TradingView integration
- [ ] Order blocks displayed as rectangles
- [ ] FVGs displayed as shaded areas
- [ ] Fibonacci OTE zone highlighted
- [ ] Projected candles concatenated to actual
- [ ] Real-time signal updates via WebSocket
- [ ] Kill zone indicators in sidebar
- [ ] Phase and risk level display
- [ ] Signal history with filters
- [ ] Failure dashboard with lessons
- [ ] Pre-market analysis page
- [ ] Dark theme, professional design
