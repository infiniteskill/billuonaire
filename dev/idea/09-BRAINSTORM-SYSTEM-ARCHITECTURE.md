# 🧠 BRAINSTORM: RADAR System Architecture Decisions

> **Critical Questions**: Platform type, data source, visualization, real-time capabilities, and user interaction model.

---

## 🎯 Context

We're building RADAR - a manipulation detection and projection system. Before implementation, we need to decide:

1. **Data Source**: How do we get market data?
2. **Visualization**: How do we display results and projections?
3. **Platform**: Web, desktop, or CLI?
4. **Real-time**: Can it analyze live data?
5. **Projection Display**: How to show future predictions?
6. **Multi-Symbol**: Can it switch between stocks?
7. **Screen Reading**: Can it read TradingView/Kite?

---

## 📊 DIMENSION 1: Data Source Architecture

### Option A: jugaad-data + jugaad-trader (FREE)

**Description**: Use `jugaad-data` for historical data from NSE, `jugaad-trader` for live quotes and order execution (requires Zerodha account).

```python
# Historical data
from jugaad_data.nse import stock_df
df = stock_df(symbol="NIFTY 50", from_date=date(2025,1,1), to_date=date(2025,1,30))

# Live data
from jugaad_data.nse import NSELive
n = NSELive()
quote = n.stock_quote("RELIANCE")
```

✅ **Pros:**
- FREE (no API subscription)
- Official NSE data
- Historical + live quotes
- Can execute trades via Zerodha
- Python-native integration

❌ **Cons:**
- NSE website sometimes blocks requests
- Intraday data limited (need to build from EOD)
- No tick-level data
- Rate limiting issues
- Manual session refresh for trading

📊 **Effort:** Low | **Cost:** ₹0

---

### Option B: Kite Connect API (PAID)

**Description**: Official Zerodha API with WebSocket streaming, tick data, and order execution.

```python
from kiteconnect import KiteConnect, KiteTicker
kite = KiteConnect(api_key="xxx")
kite.set_access_token("xxx")

# WebSocket for live ticks
ticker = KiteTicker("xxx", access_token)
ticker.on_ticks = on_ticks_callback
```

✅ **Pros:**
- Real-time tick data (WebSocket)
- Reliable, official API
- Full order management
- Historical minute/second data
- No rate limiting issues

❌ **Cons:**
- Costs ₹2,000/month
- Requires active Zerodha account
- API key renewal needed
- Vendor lock-in

📊 **Effort:** Medium | **Cost:** ₹2,000/month

---

### Option C: TradingView Webhook + Pine Script (HYBRID)

**Description**: Use Pine Script for on-chart analysis, webhook alerts to Python backend for advanced logic.

```pine
// Pine Script generates alert
if sweep_detected
    alert("SWEEP:NIFTY:BULLISH:19500", alert.freq_once_per_bar)

// Webhook sends to Python
// Python processes and returns analysis
```

✅ **Pros:**
- Visual on TradingView (familiar)
- Multiple symbols easy
- Chart-based analysis
- Free tier available
- Data is TradingView's problem

❌ **Cons:**
- Pine Script limited for complex logic
- Two-way sync is complex
- TradingView Pro needed for alerts
- Depends on TradingView uptime
- Can't draw projections on chart (read-only)

📊 **Effort:** High | **Cost:** ₹1,500/month (TradingView Pro)

---

### Option D: Screen Capture + OCR (UNCONVENTIONAL)

**Description**: Capture screen showing Kite/TradingView, use OCR to extract price data.

```python
import pyautogui
import pytesseract

screenshot = pyautogui.screenshot(region=(x,y,w,h))
text = pytesseract.image_to_string(screenshot)
# Parse price from text
```

✅ **Pros:**
- Works with ANY platform (Kite, TradingView, etc.)
- Zero API cost
- Uses existing tools
- Can "see" what you see

❌ **Cons:**
- Slow (screenshot + OCR = 500ms+)
- Fragile (UI changes break it)
- Error-prone (OCR mistakes)
- Can't get historical data
- CPU intensive

📊 **Effort:** Very High | **Cost:** ₹0

---

### 💡 Recommendation: Hybrid A + B

**Start with `jugaad-data` (FREE)**, upgrade to Kite Connect when the system proves valuable.

```
PHASE 1: jugaad-data for historical + daily analysis
PHASE 2: Add Kite Connect for real-time streaming
PHASE 3: Optional TradingView webhook for alerts
```

---

## 📊 DIMENSION 2: Platform Architecture

### Option A: CLI (Terminal-Based)

**Description**: Pure Python CLI application with rich terminal output.

```
$ python radar.py analyze NIFTY --date 2025-01-31

╭─ RADAR Analysis: NIFTY - 2025-01-31 ─────────────────────╮
│                                                          │
│  HTF Bias: BEARISH (Weekly down, Daily ranging)         │
│  Current Phase: POST-HUNT (sweep at 9:47)               │
│  Kill Zone: INACTIVE (next at 1:30 PM)                  │
│                                                          │
│  ═══════════════════════════════════ PDH (22,450)       │
│  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 4H OB Zone          │
│  ◆ PRICE NOW: 22,380                                     │
│  ─────────────────────────────────── PDL (22,250)       │
│                                                          │
│  Signal: WAIT for 1H OB retest at 22,340                │
│                                                          │
╰──────────────────────────────────────────────────────────╯
```

✅ **Pros:**
- Fast to develop (1-2 weeks)
- Runs anywhere (server, laptop)
- No frontend complexity
- Easy to automate/script
- Low resource usage

❌ **Cons:**
- No visual charts
- Not intuitive for non-technical
- Can't overlay on price chart
- Limited interactivity

📊 **Effort:** Low | **Best For:** MVP, power users

---

### Option B: Web Dashboard (FastAPI + React/Vue)

**Description**: Full web application with interactive charts, real-time updates.

```
┌────────────────────────────────────────────────────────────┐
│  🔍 RADAR Dashboard                    NIFTY ▼  │ LIVE 🟢 │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ┌─────────────────────────────────────┐  ┌─────────────┐ │
│  │                                     │  │ HTF Context │ │
│  │      [Interactive Chart]            │  │             │ │
│  │                                     │  │ W: BEARISH  │ │
│  │   Historical + Projected Lines     │  │ D: RANGING  │ │
│  │   ───────  ······ (future)         │  │ 4H: BULLISH │ │
│  │                                     │  │             │ │
│  │   Color-coded zones                │  │ ──────────  │ │
│  │   🔴 Hunt Zone                     │  │ Kill Zone:  │ │
│  │   🟢 Entry Zone                    │  │ ⚠️ 1:30 PM  │ │
│  │   🟡 Caution Zone                  │  │             │ │
│  │                                     │  │             │ │
│  └─────────────────────────────────────┘  └─────────────┘ │
│                                                            │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ Signal: LONG setup forming. Entry: 22,340 SL: 22,280│  │
│  └─────────────────────────────────────────────────────┘  │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

✅ **Pros:**
- Visual, intuitive
- Interactive charts
- Real-time WebSocket updates
- Works on any device (browser)
- Easy symbol switching
- Professional appearance

❌ **Cons:**
- More development time (4-6 weeks)
- Need to serve/host
- Frontend skills required
- More to maintain

📊 **Effort:** High | **Best For:** Final product

---

### Option C: Desktop App (PyQt/Tauri)

**Description**: Native desktop application with full OS integration.

✅ **Pros:**
- Fast native performance
- Can control other windows
- Overlay on existing charts
- Offline capable
- No server needed

❌ **Cons:**
- Complex development
- Platform-specific issues
- Distribution is hard
- No mobile support

📊 **Effort:** Very High | **Best For:** Advanced users

---

### Option D: Overlay Mode (Screen Overlay)

**Description**: Transparent overlay that sits on top of your TradingView/Kite.

```
┌──────────────────────────────────────────────────────────┐
│                                                          │
│  [Your TradingView Window]                              │
│                                                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │ RADAR OVERLAY (semi-transparent)               │    │
│  │                                                 │    │
│  │  HTF: ↘ BEARISH                                │    │
│  │  Phase: HUNTING                                 │    │
│  │  ───────────── PDH overlay line ──────────────│    │
│  │  Kill Zone: ⚠️ ACTIVE                          │    │
│  │                                                 │    │
│  │  Signal: WAIT                                  │    │
│  └─────────────────────────────────────────────────┘    │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

✅ **Pros:**
- Works WITH your existing chart
- No context switching
- Sees what you see
- Minimal disruption

❌ **Cons:**
- Complex to build
- OS-specific APIs
- Transparency handling
- May conflict with apps

📊 **Effort:** Very High | **Best For:** Power traders

---

### 💡 Recommendation: A → B Progression

```
PHASE 1 (Week 1-4): CLI
- Fast MVP
- Validate logic works
- Text-based analysis

PHASE 2 (Week 4-8): Web Dashboard
- Add visual charts
- Real-time updates
- Symbol switching

PHASE 3 (Future): Overlay Mode
- If needed for workflow
```

---

## 📊 DIMENSION 3: Visualization Architecture

### The Core Question: How to Show Projections?

You want to see:
1. **Historical data** (solid lines)
2. **Current price** (live)
3. **Projected scenarios** (dotted/colored)
4. **Probability zones** (shaded areas)

---

### Option A: Static Chart Generation (matplotlib/plotly)

**Description**: Generate chart images with projections, refresh periodically.

```python
import plotly.graph_objects as go

fig = go.Figure()

# Historical (solid)
fig.add_trace(go.Candlestick(x=dates, open=opens, high=highs, low=lows, close=closes))

# Projection (dotted)
fig.add_trace(go.Scatter(x=future_dates, y=projected_high, 
                         line=dict(dash='dot', color='green')))
fig.add_trace(go.Scatter(x=future_dates, y=projected_low, 
                         line=dict(dash='dot', color='red')))

# Probability zone (shaded)
fig.add_vrect(x0=zone_start, x1=zone_end, fillcolor="green", opacity=0.2)

fig.write_html("analysis.html")
```

```
Chart Display:
                                      ╱╲      
                                     ╱  ╲     ← Bullish projection (68%)
                                    ╱    ╲    
═══════════════╔═══════════════════╗      
Historical     ║ PROJECTION ZONE   ║══════════════════
━━━━━━━━━━━━━━━╚═══════════════════╝      
                                    ╲    ╱    
                                     ╲  ╱     ← Bearish projection (32%)
                                      ╲╱      
```

✅ **Pros:**
- Simple to implement
- Rich visualization (candlesticks, zones)
- Export to HTML/PNG
- Works offline

❌ **Cons:**
- Not real-time
- Manual refresh needed
- Static (no interaction)

📊 **Effort:** Low

---

### Option B: Interactive Web Chart (TradingView Lightweight Charts / Apache ECharts)

**Description**: Embed real-time interactive chart in web dashboard.

```javascript
// TradingView Lightweight Charts
const chart = createChart(document.getElementById('chart'));

const candleSeries = chart.addCandlestickSeries();
candleSeries.setData(historicalData);

// Add projection line
const projectionSeries = chart.addLineSeries({
    color: 'rgba(0, 255, 0, 0.5)',
    lineStyle: LineStyle.Dashed,
});
projectionSeries.setData(projectionData);

// Add zones
chart.addAreaSeries({...}); // Probability zones
```

✅ **Pros:**
- Real-time updates
- Zoom/pan/interact
- Professional look
- Responsive
- Symbol switching easy

❌ **Cons:**
- Requires web setup
- More development
- JavaScript/frontend work

📊 **Effort:** Medium

---

### Option C: Generate Pine Script (Export to TradingView)

**Description**: RADAR generates Pine Script code that you paste into TradingView.

```python
# RADAR generates this Pine Script
pine_code = """
//@version=5
indicator("RADAR Projections", overlay=true)

// Historical levels (RADAR calculated)
hline(22450, "PDH", color=color.red, linestyle=line.style_solid)
hline(22250, "PDL", color=color.green, linestyle=line.style_solid)

// OB Zone
box.new(bar_index[10], 22380, bar_index, 22400, bgcolor=color.new(color.blue, 80))

// Projection paths
// ... generated based on analysis
"""
print(pine_code)  # User copies to TradingView
```

✅ **Pros:**
- Uses TradingView's charting
- Familiar interface
- No chart development
- Professional visuals

❌ **Cons:**
- Manual copy-paste step
- Can't update in real-time
- One-way (no feedback)
- Limited by Pine Script

📊 **Effort:** Low (Pine generation), High (live sync)

---

### Option D: Dual-Window Mode

**Description**: RADAR in one window, TradingView in another. RADAR shows textual + small chart.

```
┌─────────────────────────┬─────────────────────────┐
│                         │                         │
│    [TradingView]        │      [RADAR]            │
│                         │                         │
│  Your normal chart      │  Analysis Panel         │
│  (unchanged)            │  + Mini projection      │
│                         │    chart                │
│                         │  + Signals              │
│                         │  + Alerts               │
│                         │                         │
└─────────────────────────┴─────────────────────────┘
```

✅ **Pros:**
- Best of both worlds
- TradingView for detail
- RADAR for analysis
- No integration needed

❌ **Cons:**
- Two windows to manage
- Context switching
- Screen real estate

📊 **Effort:** Low (no TradingView integration)

---

### 💡 Recommendation: B + D

**Build web dashboard with interactive charts** (Option B) that can work **side-by-side with TradingView** (Option D).

```
RADAR Dashboard:
├── Interactive lightweight chart (projections visible)
├── Symbol switcher dropdown
├── Real-time analysis panel
└── Signal alerts

User opens both RADAR and TradingView side-by-side
- TradingView for detail/execution
- RADAR for analysis/projections
```

---

## 📊 DIMENSION 4: Real-Time & Multi-Symbol

### The Questions:
1. Can we switch symbols instantly?
2. Can we analyze in real-time?
3. Can we predict on historical data?

---

### Real-Time Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     REAL-TIME SYSTEM                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐     │
│  │ DATA FEED   │      │   RADAR     │      │  FRONTEND   │     │
│  │             │      │   CORE      │      │             │     │
│  │ Kite/jugaad │─────▶│             │─────▶│  Dashboard  │     │
│  │ WebSocket   │ tick │  Analyze    │ event│  WebSocket  │     │
│  │ or polling  │      │  Detect     │      │  Update     │     │
│  │             │      │  Project    │      │             │     │
│  └─────────────┘      └─────────────┘      └─────────────┘     │
│                                                                  │
│  LATENCY TARGET: < 500ms from tick to UI update                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Multi-Symbol Switching

```python
class SymbolManager:
    def __init__(self):
        self.active_symbol = None
        self.cached_analysis = {}  # Cache per symbol
        
    async def switch_symbol(self, new_symbol: str) -> Analysis:
        """Instant symbol switch with cached analysis"""
        
        if new_symbol in self.cached_analysis:
            cached = self.cached_analysis[new_symbol]
            if cached.is_fresh():  # < 30 seconds old
                return cached
        
        # Load data for new symbol
        data = await self.data_loader.load(new_symbol)
        
        # Run full analysis
        analysis = self.radar_core.analyze(data)
        
        # Cache it
        self.cached_analysis[new_symbol] = analysis
        
        self.active_symbol = new_symbol
        return analysis
    
    def get_available_symbols(self) -> List[str]:
        return [
            "NIFTY 50",
            "BANKNIFTY",
            "RELIANCE",
            "TCS",
            "INFY",
            # ... configurable list
        ]
```

### Historical Replay Mode

```python
class HistoricalReplay:
    """Replay historical data to test projections"""
    
    def __init__(self, symbol: str, start_date: date, end_date: date):
        self.data = load_historical(symbol, start_date, end_date)
        self.current_bar = 0
    
    def step_forward(self, bars: int = 1) -> Analysis:
        """Advance time and re-analyze"""
        self.current_bar += bars
        
        # Get data up to current bar (simulating "now")
        visible_data = self.data[:self.current_bar]
        
        # Run RADAR analysis (doesn't see future)
        analysis = radar_core.analyze(visible_data)
        
        # Get actual future bars for comparison
        actual_future = self.data[self.current_bar:self.current_bar+20]
        
        return {
            "analysis": analysis,
            "projection": analysis.projected_scenarios,
            "actual_outcome": actual_future,  # For learning
            "accuracy": calculate_accuracy(analysis.projection, actual_outcome)
        }
    
    def run_full_backtest(self) -> BacktestResults:
        """Run through entire period, measure projection accuracy"""
        results = []
        while self.current_bar < len(self.data) - 20:
            result = self.step_forward(1)
            results.append(result)
        return aggregate_results(results)
```

---

## 📊 DIMENSION 5: Screen Reading (Can We Read TradingView?)

### Option A: DON'T Read Screen - Use Data API

**Description**: Get data from API, ignore what's on screen.

✅ **Pros:**
- Reliable, structured data
- Fast, no OCR
- Works in background

❌ **Cons:**
- Need separate data feed
- May differ from chart display

📊 **Recommendation:** This is the RIGHT approach

---

### Option B: Screen Capture + OCR

**Description**: Capture screen region, extract numbers.

```python
import mss
import pytesseract
import cv2

def read_price_from_screen(region):
    with mss.mss() as sct:
        img = sct.grab(region)
        # Convert to grayscale
        gray = cv2.cvtColor(np.array(img), cv2.COLOR_BGR2GRAY)
        # OCR
        text = pytesseract.image_to_string(gray, config='--psm 7 digits')
        return float(text.strip())
```

✅ **Pros:**
- Works with any platform
- Sees exactly what you see

❌ **Cons:**
- Slow (300-500ms per capture)
- Error-prone (OCR mistakes)
- Fragile (UI changes break it)
- Can't get historical data

📊 **Verdict:** NOT recommended as primary source. Use as fallback only.

---

### Option C: Browser Automation (Read TradingView DOM)

**Description**: Control browser, extract data from TradingView's DOM.

```python
from playwright import sync_api

with sync_api.sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto("https://www.tradingview.com/chart/...")
    
    # Extract price from DOM element
    price = page.query_selector(".lastPrice").inner_text()
```

✅ **Pros:**
- More reliable than OCR
- Can interact with page
- Gets structured data

❌ **Cons:**
- Complex setup
- TradingView may block
- Breaks on UI updates
- Resource heavy

📊 **Verdict:** Possible but fragile. API is better.

---

### 💡 Final Recommendation

```
DON'T try to read the screen.

USE API data (jugaad-data / Kite Connect).
DISPLAY your own chart alongside TradingView.
KEEP analysis separate from chart viewing.

Screen reading is:
- Slow (OCR latency)
- Fragile (UI changes)
- Unnecessary (API gives same data)
- Complex (OS-specific)
```

---

## 🏆 FINAL ARCHITECTURE RECOMMENDATION

### Stack Summary

| Dimension | Recommendation | Rationale |
|-----------|----------------|-----------|
| **Data Source** | jugaad-data → Kite Connect | Free start, paid upgrade |
| **Platform** | CLI → Web Dashboard | Fast MVP, professional final |
| **Visualization** | TradingView Lightweight Charts | Interactive, real-time |
| **Real-Time** | WebSocket streaming | Low latency |
| **Multi-Symbol** | Dropdown + cache | Instant switching |
| **Historical** | Replay mode | Test projections |
| **Screen Reading** | NO | Use API instead |

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         RADAR SYSTEM v1.0                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        DATA LAYER                                    │   │
│  │                                                                      │   │
│  │   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐           │   │
│  │   │ jugaad-data  │   │ Kite Connect │   │ CSV Import   │           │   │
│  │   │ (FREE)       │   │ (PAID)       │   │ (Manual)     │           │   │
│  │   │              │   │              │   │              │           │   │
│  │   │ Historical + │   │ Real-time    │   │ Backup       │           │   │
│  │   │ Live quotes  │   │ WebSocket    │   │              │           │   │
│  │   └──────┬───────┘   └──────┬───────┘   └──────┬───────┘           │   │
│  │          └──────────────────┴──────────────────┘                    │   │
│  │                             │                                        │   │
│  └─────────────────────────────┼────────────────────────────────────────┘   │
│                                │                                             │
│  ┌─────────────────────────────▼────────────────────────────────────────┐   │
│  │                        RADAR CORE (Python)                            │   │
│  │                                                                       │   │
│  │   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │   │
│  │   │ Candle   │  │ Swing    │  │ Sweep    │  │ OB/FVG   │            │   │
│  │   │ Processor│  │ Detector │  │ Detector │  │ Finder   │            │   │
│  │   └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘            │   │
│  │        └─────────────┴─────────────┴─────────────┘                   │   │
│  │                             │                                         │   │
│  │   ┌──────────────────────────────────────────────────────────┐      │   │
│  │   │              MULTI-SCALE CONTEXT ENGINE                   │      │   │
│  │   └──────────────────────────┬───────────────────────────────┘      │   │
│  │                              │                                        │   │
│  │   ┌───────────┐  ┌───────────┴───────────┐  ┌───────────┐           │   │
│  │   │ Time      │  │ Confluence   │ Entry  │  │ Projection│           │   │
│  │   │ Learner   │  │ Scorer       │ Calc   │  │ Engine    │           │   │
│  │   └───────────┘  └───────────────────────┘  └───────────┘           │   │
│  │                              │                                        │   │
│  └──────────────────────────────┼───────────────────────────────────────┘   │
│                                 │                                            │
│  ┌──────────────────────────────▼───────────────────────────────────────┐   │
│  │                        FRONTEND (Web)                                 │   │
│  │                                                                       │   │
│  │   ┌─────────────────────────────────────────────────────────────┐   │   │
│  │   │                     FastAPI Backend                          │   │   │
│  │   │  /api/symbols  /api/analyze/{symbol}  /ws/live/{symbol}    │   │   │
│  │   └─────────────────────────────────────────────────────────────┘   │   │
│  │                                │                                      │   │
│  │   ┌─────────────────────────────────────────────────────────────┐   │   │
│  │   │                   React/Vue Dashboard                        │   │   │
│  │   │                                                              │   │   │
│  │   │  ┌──────────────────────┐  ┌───────────────────────────┐    │   │   │
│  │   │  │ TradingView          │  │ Analysis Panel            │    │   │   │
│  │   │  │ Lightweight Charts   │  │                           │    │   │   │
│  │   │  │                      │  │ HTF Context               │    │   │   │
│  │   │  │ - Historical (solid) │  │ Kill Zone Status          │    │   │   │
│  │   │  │ - Projected (dotted) │  │ Current Signal            │    │   │   │
│  │   │  │ - Zones (shaded)     │  │ Projection Probabilities  │    │   │   │
│  │   │  │                      │  │                           │    │   │   │
│  │   │  └──────────────────────┘  └───────────────────────────┘    │   │   │
│  │   │                                                              │   │   │
│  │   │  ┌─────────────────────────────────────────────────────┐    │   │   │
│  │   │  │ Symbol: [NIFTY ▼]  │ Mode: [Live 🟢 / Replay 🔄]   │    │   │   │
│  │   │  └─────────────────────────────────────────────────────┘    │   │   │
│  │   └─────────────────────────────────────────────────────────────┘   │   │
│  │                                                                       │   │
│  └───────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 🗓️ Revised Implementation Timeline

| Week | Phase | Deliverable |
|------|-------|-------------|
| 1-2 | **Core + CLI** | Analysis engine, CLI output |
| 3-4 | **Data Integration** | jugaad-data, multi-symbol |
| 5-6 | **Web Backend** | FastAPI, WebSocket |
| 6-7 | **Web Frontend** | Charts, dashboard |
| 8 | **Replay Mode** | Historical testing |
| 9-10 | **Polish** | Alerts, caching, UX |

---

## ❓ Decisions Needed

1. **Start CLI or Web?**
   - CLI first (faster) or
   - Web from start (more work, better UX)?

2. **Kite Connect now or later?**
   - Start with jugaad-data (free) or
   - Get Kite Connect immediately (₹2,000/month)?

3. **Chart library preference?**
   - TradingView Lightweight Charts (recommended)
   - Apache ECharts
   - Plotly.js
   - D3.js (hard mode)

4. **Projection display style?**
   - Multiple paths (bullish/bearish/neutral)
   - Single path with confidence band
   - Probability zones only

5. **Ready to start implementation?**
