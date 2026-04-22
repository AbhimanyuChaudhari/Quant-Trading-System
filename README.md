# Quant Trading System

A fully deployed, end-to-end algorithmic trading system with a live paper trading engine and real-time dashboard. Built with Python, FastAPI, and Next.js.

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square)
![Next.js](https://img.shields.io/badge/Next.js-16-black?style=flat-square)
![Alpaca](https://img.shields.io/badge/Alpaca-Paper%20Trading-yellow?style=flat-square)
![Render](https://img.shields.io/badge/Engine-Render-purple?style=flat-square)
![Vercel](https://img.shields.io/badge/Dashboard-Vercel-black?style=flat-square)

**[Live Dashboard →](https://quant-trading-system-psi.vercel.app)**

---

## What This Does

A regime-adaptive algorithmic trading system that runs 24/7 on paper trading. It detects market conditions in real time and switches between momentum and mean reversion strategies automatically — then executes bracket orders with ATR-based stops via Alpaca.

The live dashboard streams portfolio state, signals, positions, and trade history via WebSocket.

---

## Strategy

### Regime Detection
Uses the Average Directional Index (ADX) to classify the market into three regimes on every new bar:

| Regime | Condition | Strategy Used |
|---|---|---|
| Trending | ADX > 25 | Momentum |
| Ranging | ADX < 25 | Mean Reversion |
| Volatile | Vol ratio > 1.8× | Flat — no new trades |

### Momentum Strategy (Trending regime)
- Entry: Fast MA (10) crosses above Slow MA (30) with RSI < 70
- Exit: MA cross reverses or RSI > 70
- Direction: Long or short based on cross direction

### Mean Reversion Strategy (Ranging regime)
- Entry: Z-score > 2.0 (overbought) or Z-score < -2.0 (oversold)
- Exit: Z-score reverts to within 0.5 of mean
- Uses Bollinger Bands + RSI as confirmation filters

### Risk Management
- **Position sizing:** ATR-based fixed fractional (risk 2% of equity per trade)
- **Stop loss:** Entry ± 2× ATR (set at exchange level via bracket order)
- **Take profit:** Entry ± 3× ATR (1.5:1 reward/risk ratio)
- **Kill switch:** Automatically closes all positions at 10% portfolio drawdown
- **Max positions:** 3 concurrent positions maximum
- **Daily loss limit:** 5% daily loss limit

---

## Architecture

```
┌─────────────────────────────────────────┐
│         Python Strategy Engine          │
│  ┌──────────┐  ┌──────────┐  ┌───────┐ │
│  │ Regime   │  │ Signal   │  │ Risk  │ │
│  │ Detector │→ │ Generator│→ │ Mgr   │ │
│  └──────────┘  └──────────┘  └───┬───┘ │
│                                   ↓     │
│         FastAPI REST + WebSocket        │
└──────────────────┬──────────────────────┘
                   ↓
┌──────────────────────────────────────────┐
│         Alpaca Paper Trading             │
│   WebSocket stream ← → REST orders      │
└──────────────────────────────────────────┘
                   ↑
┌──────────────────────────────────────────┐
│      Next.js Dashboard on Vercel         │
│  Live P&L │ Positions │ Signals │ Trades │
└──────────────────────────────────────────┘
```

---

## Project Structure

```
quant-trading-system/
├── engine/                     # Python strategy engine (deployed on Render)
│   ├── src/
│   │   ├── config.py           # All parameters — symbols, thresholds, risk limits
│   │   ├── data.py             # Alpaca WebSocket stream + historical warmup
│   │   ├── regime.py           # ADX-based regime detection
│   │   ├── signals.py          # Momentum + mean reversion signal generation
│   │   ├── risk.py             # Position sizing, kill switch, daily loss limit
│   │   ├── execution.py        # Bracket order submission via Alpaca
│   │   └── portfolio.py        # P&L tracking, equity curve, metrics
│   ├── main.py                 # Engine entry point + strategy loop
│   ├── api.py                  # FastAPI REST endpoints + WebSocket
│   ├── Procfile                # Render start command
│   └── requirements.txt
│
└── dashboard/                  # Next.js frontend (deployed on Vercel)
    ├── app/
    │   ├── page.tsx            # Main dashboard page
    │   ├── layout.tsx
    │   └── globals.css         # Dark terminal theme
    ├── components/
    │   ├── EquityChart.tsx     # Canvas-based equity curve
    │   ├── RegimePanel.tsx     # ADX + regime badges per symbol
    │   ├── SignalPanel.tsx     # Live signals with indicators
    │   ├── PositionsTable.tsx  # Open positions with unrealized P&L
    │   ├── TradeLog.tsx        # Trade history with strategy + regime tags
    │   └── MetricCard.tsx      # Portfolio metric cards
    └── lib/
        ├── useEngine.ts        # WebSocket hook with REST fallback
        └── types.ts            # TypeScript interfaces
```

---

## Dashboard Features

- **Real-time equity curve** — canvas chart updates every 2 seconds via WebSocket
- **Regime indicator** — ADX progress bar + trending/ranging/volatile badge per symbol
- **Live signals** — direction, strategy, strength bar, stop/TP levels, indicator values
- **Positions table** — entry price, current price, unrealized P&L per position
- **Trade log** — every executed trade with strategy and regime tags
- **Performance metrics** — equity, P&L, Sharpe ratio, max drawdown, win rate

---

## API Endpoints

The engine exposes a REST API served by FastAPI:

| Endpoint | Description |
|---|---|
| `GET /health` | System health check |
| `GET /snapshot` | Full portfolio state |
| `GET /metrics` | Performance metrics |
| `GET /positions` | Current open positions |
| `GET /signals` | Latest signals per symbol |
| `GET /regimes` | Current regime per symbol |
| `GET /trades` | Recent trade log |
| `GET /equity-curve` | Equity curve history |
| `WS /ws` | Real-time WebSocket stream |

---

## Running Locally

```bash
# Clone
git clone https://github.com/AbhimanyuChaudhari/Quant-Trading-System.git
cd Quant-Trading-System

# Create .env in root
echo "ALPACA_API_KEY=your_key" > .env
echo "ALPACA_SECRET_KEY=your_secret" >> .env
echo "ALPACA_BASE_URL=https://paper-api.alpaca.markets" >> .env

# Engine
cd engine
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
python main.py

# Dashboard (new terminal)
cd dashboard
npm install
npm run dev
```

Open `http://localhost:3000`

---

## Universe & Timeframe

- **Symbols:** AAPL, MSFT, SPY, QQQ
- **Bar timeframe:** 5-minute bars
- **Warmup:** 50 bars (~4 hours of trading history)
- **Data source:** Alpaca IEX feed (free tier)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Strategy engine | Python 3.10 |
| Market data | Alpaca WebSocket stream |
| Order execution | Alpaca paper trading REST API |
| API server | FastAPI + uvicorn |
| Real-time updates | WebSocket |
| Frontend | Next.js 16 + TypeScript |
| Styling | CSS variables + IBM Plex Mono |
| Engine hosting | Render |
| Dashboard hosting | Vercel |

---

## Disclaimer

This system uses **paper trading only** — no real money is involved. For educational and portfolio demonstration purposes. Not financial advice.

---

## Contact

**Abhimanyu Chaudhari** — MS Financial Technologies, NJIT
[LinkedIn](http://www.linkedin.com/in/abhimanyu-chaudhari16) · [GitHub](https://github.com/AbhimanyuChaudhari) · abhimanyuchaudhari16@gmail.com
