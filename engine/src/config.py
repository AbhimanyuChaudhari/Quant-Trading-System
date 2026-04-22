"""
config.py - Updated with 20 stocks
"""

import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parents[2] / '.env')

ALPACA_API_KEY    = os.getenv('ALPACA_API_KEY', '')
ALPACA_SECRET_KEY = os.getenv('ALPACA_SECRET_KEY', '')
ALPACA_BASE_URL   = os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')

# ── 20 liquid stocks across sectors ──────────────────────────────────────────
SYMBOLS = [
    # Tech
    'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'META', 'AMD',
    # Finance
    'JPM', 'GS', 'BAC',
    # ETFs
    'SPY', 'QQQ', 'IWM',
    # Consumer
    'AMZN', 'TSLA', 'NFLX',
    # Energy / Healthcare
    'XOM', 'CVX', 'JNJ',
    # Semi / Hardware
    'INTC', 'QCOM',
]

BAR_TIMEFRAME     = '5Min'
LOOKBACK_BARS     = 100
WARMUP_BARS       = 50

REGIME_ADX_PERIOD     = 14
REGIME_ADX_THRESHOLD  = 25
REGIME_VOL_WINDOW     = 20

MOM_FAST_MA       = 10
MOM_SLOW_MA       = 30
MOM_RSI_PERIOD    = 14
MOM_RSI_OVERBOUGHT= 70
MOM_RSI_OVERSOLD  = 30

MR_ZSCORE_WINDOW  = 20
MR_ENTRY_Z        = 2.0
MR_EXIT_Z         = 0.5
MR_BB_PERIOD      = 20
MR_BB_STD         = 2.0

MAX_POSITION_PCT  = 0.10      # 10% per position (lower since more stocks)
MAX_PORTFOLIO_RISK= 0.01      # 1% risk per trade
STOP_LOSS_ATR     = 2.0
TAKE_PROFIT_ATR   = 3.0
MAX_DRAWDOWN_KILL = 0.10
MAX_OPEN_POSITIONS= 5         # allow up to 5 positions across 20 stocks

API_HOST          = os.getenv('API_HOST', '0.0.0.0')
API_PORT          = int(os.getenv('API_PORT', '8000'))

LOG_LEVEL         = 'INFO'
LOG_FILE          = 'engine.log'