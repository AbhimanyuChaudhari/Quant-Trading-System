"""
portfolio.py
------------
Portfolio state tracking — P&L, equity curve, performance metrics.
All state lives here and gets served to the dashboard via the API.
"""

import logging
from datetime import datetime
from typing import List, Dict
from collections import deque
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class EquityPoint:
    timestamp: str
    equity:    float
    cash:      float
    pnl:       float


class Portfolio:
    """
    Tracks portfolio state in memory.
    Updated on every bar and trade event.
    """

    def __init__(self, initial_equity: float = 100_000):
        self.initial_equity  = initial_equity
        self.equity          = initial_equity
        self.cash            = initial_equity
        self.peak_equity     = initial_equity

        # Rolling equity curve (last 500 points)
        self.equity_curve: deque = deque(maxlen=500)
        self.equity_curve.append(EquityPoint(
            timestamp=datetime.now().isoformat(),
            equity=initial_equity,
            cash=initial_equity,
            pnl=0.0,
        ))

        # Trade log
        self.trade_log: List[dict] = []

        # Current signals per symbol
        self.signals:  Dict[str, dict] = {}
        self.regimes:  Dict[str, dict] = {}

    # ── Updates ───────────────────────────────────────────────────────────────

    def update_equity(self, equity: float, cash: float):
        """Update equity from account snapshot."""
        self.equity = equity
        self.cash   = cash

        if equity > self.peak_equity:
            self.peak_equity = equity

        pnl = equity - self.initial_equity
        self.equity_curve.append(EquityPoint(
            timestamp=datetime.now().isoformat(),
            equity=round(equity, 2),
            cash=round(cash, 2),
            pnl=round(pnl, 2),
        ))

    def record_trade(self, trade: dict):
        """Add a completed trade to the log."""
        self.trade_log.append(trade)
        if len(self.trade_log) > 200:
            self.trade_log = self.trade_log[-200:]

    def update_signal(self, symbol: str, signal: dict):
        self.signals[symbol] = {**signal, 'updated_at': datetime.now().isoformat()}

    def update_regime(self, symbol: str, regime: dict):
        self.regimes[symbol] = {**regime, 'updated_at': datetime.now().isoformat()}

    # ── Metrics ───────────────────────────────────────────────────────────────

    def metrics(self) -> dict:
        """Compute live performance metrics."""
        import numpy as np

        pnl_total  = self.equity - self.initial_equity
        pnl_pct    = pnl_total / self.initial_equity * 100
        drawdown   = (self.peak_equity - self.equity) / self.peak_equity * 100

        # Sharpe from equity curve
        if len(self.equity_curve) > 10:
            equities = [p.equity for p in self.equity_curve]
            returns  = np.diff(equities) / np.array(equities[:-1])
            returns  = returns[returns != 0]
            if len(returns) > 1 and returns.std() > 0:
                sharpe = (returns.mean() / returns.std()) * np.sqrt(252 * 78)
            else:
                sharpe = 0.0
        else:
            sharpe = 0.0

        # Win rate
        closed = [t for t in self.trade_log if t.get('pnl') is not None]
        n_wins  = sum(1 for t in closed if t.get('pnl', 0) > 0)
        win_rate = (n_wins / len(closed) * 100) if closed else 0.0

        return {
            'equity':         round(self.equity, 2),
            'cash':           round(self.cash, 2),
            'initial_equity': round(self.initial_equity, 2),
            'pnl_total':      round(pnl_total, 2),
            'pnl_pct':        round(pnl_pct, 4),
            'peak_equity':    round(self.peak_equity, 2),
            'max_drawdown_pct':round(drawdown, 4),
            'sharpe_ratio':   round(sharpe, 3),
            'n_trades':       len(closed),
            'win_rate_pct':   round(win_rate, 2),
        }

    # ── Serialization ─────────────────────────────────────────────────────────

    def equity_curve_list(self) -> List[dict]:
        return [
            {'timestamp': p.timestamp, 'equity': p.equity,
             'cash': p.cash, 'pnl': p.pnl}
            for p in self.equity_curve
        ]

    def snapshot(self) -> dict:
        """Full state snapshot for dashboard."""
        return {
            'metrics':      self.metrics(),
            'equity_curve': self.equity_curve_list(),
            'signals':      self.signals,
            'regimes':      self.regimes,
            'trade_log':    self.trade_log[-50:],
            'timestamp':    datetime.now().isoformat(),
        }
