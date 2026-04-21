"""
config.py
---------
Central configuration — loads from .env and defines all system constants.
"""

import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env from project root (two levels up from src/)
load_dotenv(Path(__file__).resolve().parents[2] / '.env')

# ── Alpaca credentials ────────────────────────────────────────────────────────
ALPACA_API_KEY    = os.getenv('ALPACA_API_KEY', '')
ALPACA_SECRET_KEY = os.getenv('ALPACA_SECRET_KEY', '')
ALPACA_BASE_URL   = os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')

# ── Trading universe ──────────────────────────────────────────────────────────
# Start small — 4 liquid stocks across different sectors
SYMBOLS = ['AAPL', 'MSFT', 'SPY', 'QQQ']

# ── Strategy parameters ───────────────────────────────────────────────────────
BAR_TIMEFRAME     = '5Min'    # bar aggregation window
LOOKBACK_BARS     = 100       # bars of history to keep in memory
WARMUP_BARS       = 50        # bars needed before signals are valid

# Regime detection
REGIME_ADX_PERIOD     = 14
REGIME_ADX_THRESHOLD  = 25    # ADX > 25 = trending, < 25 = ranging
REGIME_VOL_WINDOW     = 20    # rolling window for volatility regime

# Momentum signal
MOM_FAST_MA       = 10
MOM_SLOW_MA       = 30
MOM_RSI_PERIOD    = 14
MOM_RSI_OVERBOUGHT= 70
MOM_RSI_OVERSOLD  = 30

# Mean reversion signal
MR_ZSCORE_WINDOW  = 20
MR_ENTRY_Z        = 2.0       # enter when |z| > 2
MR_EXIT_Z         = 0.5       # exit when |z| < 0.5
MR_BB_PERIOD      = 20
MR_BB_STD         = 2.0

# ── Risk management ───────────────────────────────────────────────────────────
MAX_POSITION_PCT  = 0.20      # max 20% of portfolio per position
MAX_PORTFOLIO_RISK= 0.02      # max 2% portfolio loss per trade
STOP_LOSS_ATR     = 2.0       # stop = entry ± 2×ATR
TAKE_PROFIT_ATR   = 3.0       # TP = entry ± 3×ATR
MAX_DRAWDOWN_KILL = 0.10      # kill switch at 10% drawdown
MAX_OPEN_POSITIONS= 3         # max simultaneous positions

# ── FastAPI ───────────────────────────────────────────────────────────────────
API_HOST          = os.getenv('API_HOST', '0.0.0.0')
API_PORT          = int(os.getenv('API_PORT', '8000'))

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL         = 'INFO'
LOG_FILE          = 'engine.log'
