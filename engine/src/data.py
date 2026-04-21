"""
data.py - Fixed for alpaca-py >= 0.13
"""

import logging
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional
import asyncio

import pandas as pd
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.data.live import StockDataStream

from src.config import (
    ALPACA_API_KEY, ALPACA_SECRET_KEY,
    SYMBOLS, LOOKBACK_BARS, BAR_TIMEFRAME
)

logger = logging.getLogger(__name__)


class BarStore:
    def __init__(self, max_bars: int = LOOKBACK_BARS):
        self.max_bars = max_bars
        self._bars: Dict[str, pd.DataFrame] = {}

    def update(self, symbol: str, bar: dict):
        row = pd.DataFrame([bar])
        if symbol not in self._bars or self._bars[symbol].empty:
            self._bars[symbol] = row
        else:
            self._bars[symbol] = pd.concat(
                [self._bars[symbol], row], ignore_index=True
            ).tail(self.max_bars)

    def get(self, symbol: str) -> Optional[pd.DataFrame]:
        return self._bars.get(symbol)

    def has_enough_data(self, symbol: str, min_bars: int) -> bool:
        df = self._bars.get(symbol)
        return df is not None and len(df) >= min_bars

    def latest(self, symbol: str) -> Optional[dict]:
        df = self._bars.get(symbol)
        if df is not None and not df.empty:
            return df.iloc[-1].to_dict()
        return None

    def all_symbols(self) -> List[str]:
        return list(self._bars.keys())

    def snapshot(self) -> dict:
        return {sym: self.latest(sym) for sym in self._bars}


def fetch_historical_bars(symbols: List[str],
                           n_bars: int = LOOKBACK_BARS) -> Dict[str, pd.DataFrame]:
    client = StockHistoricalDataClient(ALPACA_API_KEY, ALPACA_SECRET_KEY)

    tf_map = {
        '1Min':  TimeFrame(1,  TimeFrameUnit.Minute),
        '5Min':  TimeFrame(5,  TimeFrameUnit.Minute),
        '15Min': TimeFrame(15, TimeFrameUnit.Minute),
        '1Hour': TimeFrame(1,  TimeFrameUnit.Hour),
        '1Day':  TimeFrame(1,  TimeFrameUnit.Day),
    }
    tf = tf_map.get(BAR_TIMEFRAME, TimeFrame(5, TimeFrameUnit.Minute))
    days_back = max(10, n_bars // 78 + 5)
    start = datetime.now() - timedelta(days=days_back)

    logger.info(f'Fetching historical bars for {symbols}...')
    result = {}

    for symbol in symbols:
        try:
            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=tf,
                start=start,
            )
            bars_response = client.get_stock_bars(request)
            df = bars_response.df

            # Flatten MultiIndex
            if isinstance(df.index, pd.MultiIndex):
                df = df.reset_index()
                if 'symbol' in df.columns:
                    df = df[df['symbol'] == symbol].drop(columns=['symbol'], errors='ignore')
            else:
                df = df.reset_index()

            df.columns = [c.lower() for c in df.columns]
            if 'timestamp' in df.columns:
                df = df.rename(columns={'timestamp': 'ts'})

            df['symbol'] = symbol
            df = df.tail(n_bars).reset_index(drop=True)
            result[symbol] = df
            logger.info(f'  {symbol}: {len(df)} bars loaded')

        except Exception as e:
            logger.warning(f'  {symbol}: failed — {e}')

    return result


class MarketDataStream:
    def __init__(self, bar_store: BarStore):
        self.bar_store    = bar_store
        self._callbacks: List[Callable] = []
        self._stream      = None
        self._running     = False

    def register_callback(self, fn: Callable):
        self._callbacks.append(fn)

    async def _on_bar(self, bar):
        try:
            symbol = bar.symbol
            bar_dict = {
                'ts':     bar.timestamp,
                'open':   float(bar.open),
                'high':   float(bar.high),
                'low':    float(bar.low),
                'close':  float(bar.close),
                'volume': float(bar.volume),
                'vwap':   float(bar.vwap) if hasattr(bar, 'vwap') and bar.vwap else float(bar.close),
                'symbol': symbol,
            }
            self.bar_store.update(symbol, bar_dict)
            logger.debug(f'Bar: {symbol} close={bar_dict["close"]:.2f}')

            for cb in self._callbacks:
                try:
                    if asyncio.iscoroutinefunction(cb):
                        await cb(symbol, bar_dict)
                    else:
                        cb(symbol, bar_dict)
                except Exception as e:
                    logger.error(f'Callback error: {e}')
        except Exception as e:
            logger.error(f'Bar handler error: {e}')

    async def start(self, symbols: List[str] = SYMBOLS):
        self._stream  = StockDataStream(ALPACA_API_KEY, ALPACA_SECRET_KEY)
        self._running = True
        self._stream.subscribe_bars(self._on_bar, *symbols)
        logger.info(f'Starting WebSocket stream for {symbols}')
        try:
            await self._stream._run_forever()
        except Exception as e:
            logger.error(f'Stream error: {e}')
            self._running = False

    async def stop(self):
        if self._stream and self._running:
            self._stream.stop()
            self._running = False

    @property
    def is_running(self) -> bool:
        return self._running


def is_market_open() -> bool:
    from alpaca.trading.client import TradingClient
    try:
        client = TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=True)
        clock  = client.get_clock()
        return clock.is_open
    except Exception:
        now = datetime.now()
        if now.weekday() >= 5:
            return False
        market_open  = now.replace(hour=9,  minute=30, second=0)
        market_close = now.replace(hour=16, minute=0,  second=0)
        return market_open <= now <= market_close