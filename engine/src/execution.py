"""
execution.py
------------
Order execution and position management via Alpaca.

Handles:
  - Submitting bracket orders (entry + stop + take profit)
  - Cancelling open orders
  - Querying positions and account
  - Order status tracking
"""

import logging
from datetime import datetime
from typing import Optional, Dict, List
from dataclasses import dataclass, field

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import (
    MarketOrderRequest,
    StopLossRequest,
    TakeProfitRequest,
    GetOrdersRequest,
)
from alpaca.trading.enums import (
    OrderSide, TimeInForce, OrderStatus, QueryOrderStatus
)

from src.config import ALPACA_API_KEY, ALPACA_SECRET_KEY

logger = logging.getLogger(__name__)


@dataclass
class Trade:
    id:          str
    symbol:      str
    side:        str       # 'buy' or 'sell'
    qty:         int
    entry_price: float
    stop_price:  float
    take_profit: float
    strategy:    str
    regime:      str
    timestamp:   datetime
    status:      str = 'open'
    exit_price:  float = 0.0
    pnl:         float = 0.0


class ExecutionEngine:
    """
    Manages order execution and position tracking via Alpaca.
    """

    def __init__(self):
        self.client    = TradingClient(
            ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=True
        )
        self.trades:   Dict[str, Trade] = {}   # order_id → Trade
        self.positions:Dict[str, int]   = {}   # symbol → net qty

    # ── Account info ──────────────────────────────────────────────────────────

    def get_account(self) -> dict:
        """Get current account state."""
        try:
            acc = self.client.get_account()
            return {
                'equity':       float(acc.equity),
                'cash':         float(acc.cash),
                'buying_power': float(acc.buying_power),
                'pnl_today':    float(acc.equity) - float(acc.last_equity),
                'pnl_pct':     (float(acc.equity) - float(acc.last_equity)) / float(acc.last_equity) * 100,
            }
        except Exception as e:
            logger.error(f'get_account failed: {e}')
            return {}

    def get_positions(self) -> Dict[str, dict]:
        """Get all open positions."""
        try:
            positions = self.client.get_all_positions()
            result = {}
            for pos in positions:
                result[pos.symbol] = {
                    'symbol':    pos.symbol,
                    'qty':       float(pos.qty),
                    'side':      pos.side.value,
                    'avg_entry': float(pos.avg_entry_price),
                    'market_val':float(pos.market_value),
                    'unrealized_pnl': float(pos.unrealized_pl),
                    'unrealized_pct': float(pos.unrealized_plpc) * 100,
                    'current_price':  float(pos.current_price),
                }
            self.positions = {s: int(float(p['qty']) * (1 if p['side'] == 'long' else -1))
                              for s, p in result.items()}
            return result
        except Exception as e:
            logger.error(f'get_positions failed: {e}')
            return {}

    # ── Order submission ──────────────────────────────────────────────────────

    def submit_bracket_order(self,
                              symbol:      str,
                              direction:   int,
                              qty:         int,
                              stop_price:  float,
                              take_profit: float,
                              strategy:    str = 'unknown',
                              regime:      str = 'unknown') -> Optional[Trade]:
        """
        Submit a bracket order: market entry + stop loss + take profit.
        This is the safest order type — stops are set at the exchange level.
        """
        if direction == 0 or qty <= 0:
            return None

        side = OrderSide.BUY if direction == 1 else OrderSide.SELL

        try:
            request = MarketOrderRequest(
                symbol=symbol,
                qty=qty,
                side=side,
                time_in_force=TimeInForce.DAY,
                order_class='bracket',
                stop_loss=StopLossRequest(stop_price=round(stop_price, 2)),
                take_profit=TakeProfitRequest(limit_price=round(take_profit, 2)),
            )
            order = self.client.submit_order(request)

            # Get fill price (market order fills immediately in paper trading)
            entry_price = float(order.filled_avg_price or 0)

            trade = Trade(
                id=str(order.id),
                symbol=symbol,
                side='buy' if direction == 1 else 'sell',
                qty=qty,
                entry_price=entry_price,
                stop_price=stop_price,
                take_profit=take_profit,
                strategy=strategy,
                regime=regime,
                timestamp=datetime.now(),
                status='open',
            )
            self.trades[str(order.id)] = trade
            self.positions[symbol] = qty if direction == 1 else -qty

            logger.info(
                f'ORDER SUBMITTED: {side.value} {qty} {symbol} @ market '
                f'stop={stop_price:.2f} tp={take_profit:.2f} id={order.id}'
            )
            return trade

        except Exception as e:
            logger.error(f'Order submission failed for {symbol}: {e}')
            return None

    def close_position(self, symbol: str) -> bool:
        """Close all positions in a symbol."""
        try:
            self.client.close_position(symbol)
            if symbol in self.positions:
                self.positions[symbol] = 0
            logger.info(f'Closed position: {symbol}')
            return True
        except Exception as e:
            logger.error(f'Close position failed for {symbol}: {e}')
            return False

    def close_all_positions(self):
        """Emergency close all — called by kill switch."""
        try:
            self.client.close_all_positions(cancel_orders=True)
            self.positions = {}
            logger.critical('ALL POSITIONS CLOSED (kill switch)')
        except Exception as e:
            logger.error(f'close_all_positions failed: {e}')

    def cancel_all_orders(self):
        """Cancel all open orders."""
        try:
            self.client.cancel_orders()
            logger.info('All orders cancelled.')
        except Exception as e:
            logger.error(f'cancel_all_orders failed: {e}')

    # ── Trade history ─────────────────────────────────────────────────────────

    def get_recent_trades(self, limit: int = 50) -> List[dict]:
        """Get recent filled orders from Alpaca."""
        try:
            request = GetOrdersRequest(
                status=QueryOrderStatus.CLOSED,
                limit=limit,
            )
            orders = self.client.get_orders(request)
            result = []
            for o in orders:
                if o.filled_avg_price:
                    result.append({
                        'id':          str(o.id),
                        'symbol':      o.symbol,
                        'side':        o.side.value,
                        'qty':         float(o.filled_qty or 0),
                        'price':       float(o.filled_avg_price),
                        'status':      o.status.value,
                        'timestamp':   o.filled_at.isoformat() if o.filled_at else '',
                    })
            return result
        except Exception as e:
            logger.error(f'get_recent_trades failed: {e}')
            return []

    def net_position(self, symbol: str) -> int:
        """Get net position for a symbol (+qty = long, -qty = short, 0 = flat)."""
        return self.positions.get(symbol, 0)
