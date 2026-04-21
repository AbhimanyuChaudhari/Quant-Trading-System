"""
risk.py
-------
Risk management layer.

Responsibilities:
  - Position sizing (Kelly / fixed fractional)
  - Stop-loss and take-profit enforcement
  - Maximum drawdown kill switch
  - Maximum concurrent positions check
  - Daily loss limit

Every order goes through the risk manager before execution.
If risk says no → no trade.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from src.config import (
    MAX_POSITION_PCT,
    MAX_PORTFOLIO_RISK,
    STOP_LOSS_ATR,
    TAKE_PROFIT_ATR,
    MAX_DRAWDOWN_KILL,
    MAX_OPEN_POSITIONS,
)

logger = logging.getLogger(__name__)


@dataclass
class RiskDecision:
    approved:       bool
    qty:            int      # shares to trade
    stop_price:     float
    take_profit:    float
    reason:         str


class RiskManager:
    """
    Central risk manager.
    All position sizing and risk checks go through here.
    """

    def __init__(self):
        self.peak_equity     = None
        self.daily_loss      = 0.0
        self.daily_loss_limit= 0.05   # 5% daily loss limit
        self._killed         = False

    # ── Main entry point ──────────────────────────────────────────────────────

    def evaluate(self,
                  symbol:          str,
                  direction:       int,
                  signal_strength: float,
                  current_price:   float,
                  atr:             float,
                  account_equity:  float,
                  open_positions:  dict) -> RiskDecision:
        """
        Evaluate whether a trade should be taken and at what size.

        Parameters
        ----------
        symbol          : ticker
        direction       : +1 long, -1 short, 0 flat
        signal_strength : 0-1 from signal generator
        current_price   : current market price
        atr             : current ATR for stop placement
        account_equity  : total portfolio value
        open_positions  : dict of symbol → position

        Returns RiskDecision with approved flag and sizing.
        """
        if direction == 0:
            return RiskDecision(approved=False, qty=0,
                                stop_price=0, take_profit=0,
                                reason='No signal')

        # ── Kill switch ───────────────────────────────────────────────────────
        if self._killed:
            return RiskDecision(approved=False, qty=0,
                                stop_price=0, take_profit=0,
                                reason='Kill switch active — max drawdown hit')

        # ── Already in this position ──────────────────────────────────────────
        if symbol in open_positions and open_positions[symbol] != 0:
            return RiskDecision(approved=False, qty=0,
                                stop_price=0, take_profit=0,
                                reason=f'Already have position in {symbol}')

        # ── Max concurrent positions ──────────────────────────────────────────
        n_open = sum(1 for v in open_positions.values() if v != 0)
        if n_open >= MAX_OPEN_POSITIONS:
            return RiskDecision(approved=False, qty=0,
                                stop_price=0, take_profit=0,
                                reason=f'Max positions reached ({MAX_OPEN_POSITIONS})')

        # ── Daily loss limit ──────────────────────────────────────────────────
        if self.daily_loss / (account_equity + 1e-10) > self.daily_loss_limit:
            return RiskDecision(approved=False, qty=0,
                                stop_price=0, take_profit=0,
                                reason='Daily loss limit hit')

        # ── Position sizing ───────────────────────────────────────────────────
        qty = self._position_size(
            direction, signal_strength, current_price, atr, account_equity
        )

        if qty <= 0:
            return RiskDecision(approved=False, qty=0,
                                stop_price=0, take_profit=0,
                                reason='Position size too small')

        # ── Stop and take profit ──────────────────────────────────────────────
        stop_dist = STOP_LOSS_ATR  * atr
        tp_dist   = TAKE_PROFIT_ATR * atr

        stop_price  = current_price - direction * stop_dist
        take_profit = current_price + direction * tp_dist

        logger.info(
            f'Risk APPROVED: {symbol} dir={direction} qty={qty} '
            f'stop={stop_price:.2f} tp={take_profit:.2f}'
        )

        return RiskDecision(
            approved=True,
            qty=qty,
            stop_price=round(stop_price, 2),
            take_profit=round(take_profit, 2),
            reason=f'Approved: {qty} shares, stop={stop_price:.2f}',
        )

    # ── Position sizing ───────────────────────────────────────────────────────

    def _position_size(self, direction: int, strength: float,
                        price: float, atr: float,
                        equity: float) -> int:
        """
        Fixed fractional position sizing with ATR-based risk.

        Risk per trade = equity × MAX_PORTFOLIO_RISK
        Stop distance  = ATR × STOP_LOSS_ATR
        Shares         = risk_amount / stop_distance

        Capped at MAX_POSITION_PCT of equity.
        """
        if atr <= 0 or price <= 0:
            return 0

        risk_amount  = equity * MAX_PORTFOLIO_RISK * strength
        stop_dist    = atr * STOP_LOSS_ATR
        shares_risk  = risk_amount / stop_dist

        # Cap at max position size
        max_shares   = (equity * MAX_POSITION_PCT) / price
        shares       = min(shares_risk, max_shares)

        return max(1, int(shares))

    # ── Drawdown tracking ─────────────────────────────────────────────────────

    def update_equity(self, equity: float):
        """
        Update peak equity and check kill switch.
        Called after each P&L update.
        """
        if self.peak_equity is None:
            self.peak_equity = equity

        if equity > self.peak_equity:
            self.peak_equity = equity

        drawdown = (self.peak_equity - equity) / self.peak_equity
        if drawdown >= MAX_DRAWDOWN_KILL:
            self._killed = True
            logger.critical(
                f'KILL SWITCH ACTIVATED — drawdown={drawdown*100:.1f}% '
                f'(limit={MAX_DRAWDOWN_KILL*100:.0f}%)'
            )

    def update_daily_pnl(self, pnl: float):
        """Track daily realized P&L."""
        self.daily_loss += min(0, pnl)

    def reset_daily(self):
        """Reset daily counters at market open."""
        self.daily_loss = 0.0
        logger.info('Daily risk counters reset.')

    @property
    def is_killed(self) -> bool:
        return self._killed

    def status(self) -> dict:
        return {
            'killed':          self._killed,
            'peak_equity':     self.peak_equity,
            'daily_loss':      round(self.daily_loss, 2),
            'daily_loss_limit':self.daily_loss_limit,
        }
