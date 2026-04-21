"""
signals.py
----------
Signal generation — momentum and mean reversion.

The active strategy is chosen by the regime detector:
  TRENDING  → MomentumSignal
  RANGING   → MeanReversionSignal
  VOLATILE  → FlatSignal (no new positions)

Signal values:
  +1 = long
  -1 = short
   0 = flat / no signal
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Optional

from src.config import (
    MOM_FAST_MA, MOM_SLOW_MA, MOM_RSI_PERIOD,
    MOM_RSI_OVERBOUGHT, MOM_RSI_OVERSOLD,
    MR_ZSCORE_WINDOW, MR_ENTRY_Z, MR_EXIT_Z,
    MR_BB_PERIOD, MR_BB_STD,
    WARMUP_BARS,
)


@dataclass
class Signal:
    symbol:     str
    direction:  int       # +1, -1, 0
    strategy:   str       # 'momentum', 'mean_reversion', 'flat'
    strength:   float     # 0-1 confidence
    price:      float     # current price
    stop_price: float     # suggested stop loss
    take_profit:float     # suggested take profit
    reason:     str       # human-readable explanation
    indicators: dict      # all indicator values for dashboard


# ── RSI ───────────────────────────────────────────────────────────────────────

def compute_rsi(close: np.ndarray, period: int = 14) -> float:
    """Compute RSI from close prices. Returns latest value."""
    if len(close) < period + 1:
        return 50.0
    delta = np.diff(close)
    gain  = np.where(delta > 0, delta, 0)
    loss  = np.where(delta < 0, -delta, 0)

    avg_gain = gain[-period:].mean()
    avg_loss = loss[-period:].mean()

    if avg_loss == 0:
        return 100.0
    rs  = avg_gain / avg_loss
    return float(100 - (100 / (1 + rs)))


# ── ATR ───────────────────────────────────────────────────────────────────────

def compute_atr(df: pd.DataFrame, period: int = 14) -> float:
    """Compute ATR. Returns latest value."""
    high  = df['high'].values
    low   = df['low'].values
    close = df['close'].values

    tr = np.maximum(
        high[1:] - low[1:],
        np.maximum(
            np.abs(high[1:] - close[:-1]),
            np.abs(low[1:]  - close[:-1])
        )
    )
    if len(tr) < period:
        return float(tr.mean()) if len(tr) > 0 else 0.01
    return float(tr[-period:].mean())


# ── Momentum Signal ───────────────────────────────────────────────────────────

def momentum_signal(df: pd.DataFrame, symbol: str,
                     current_position: int = 0) -> Signal:
    """
    Momentum strategy:
    - Long  when fast MA > slow MA AND RSI not overbought
    - Short when fast MA < slow MA AND RSI not oversold
    - Exit  when MA cross reverses

    Uses dual MA crossover as the primary signal with RSI as a filter.
    """
    if len(df) < WARMUP_BARS:
        return _flat_signal(symbol, df['close'].iloc[-1], 'momentum', 'Warming up')

    close    = df['close'].values
    price    = float(close[-1])
    atr_val  = compute_atr(df)
    rsi_val  = compute_rsi(close, MOM_RSI_PERIOD)

    # Moving averages
    fast_ma  = float(close[-MOM_FAST_MA:].mean())
    slow_ma  = float(close[-MOM_SLOW_MA:].mean())
    ma_diff  = fast_ma - slow_ma
    ma_diff_prev = float(close[-MOM_FAST_MA-1:-1].mean()) - float(close[-MOM_SLOW_MA-1:-1].mean())

    # Crossover detection
    crossed_up   = ma_diff > 0 and ma_diff_prev <= 0
    crossed_down = ma_diff < 0 and ma_diff_prev >= 0

    direction = 0
    reason    = ''
    strength  = 0.0

    if current_position == 0:
        # New entry
        if ma_diff > 0 and rsi_val < MOM_RSI_OVERBOUGHT:
            direction = 1
            strength  = min(1.0, abs(ma_diff) / (price * 0.001))
            reason    = f'Fast MA > Slow MA, RSI={rsi_val:.1f}'
        elif ma_diff < 0 and rsi_val > MOM_RSI_OVERSOLD:
            direction = -1
            strength  = min(1.0, abs(ma_diff) / (price * 0.001))
            reason    = f'Fast MA < Slow MA, RSI={rsi_val:.1f}'

    elif current_position == 1:
        # Managing long position
        if crossed_down or rsi_val > MOM_RSI_OVERBOUGHT:
            direction = 0   # exit
            reason    = f'MA cross down or RSI overbought ({rsi_val:.1f})'
        else:
            direction = 1   # hold
            strength  = min(1.0, abs(ma_diff) / (price * 0.001))
            reason    = f'Holding long, RSI={rsi_val:.1f}'

    elif current_position == -1:
        # Managing short position
        if crossed_up or rsi_val < MOM_RSI_OVERSOLD:
            direction = 0   # exit
            reason    = f'MA cross up or RSI oversold ({rsi_val:.1f})'
        else:
            direction = -1  # hold
            strength  = min(1.0, abs(ma_diff) / (price * 0.001))
            reason    = f'Holding short, RSI={rsi_val:.1f}'

    stop   = price - direction * atr_val * 2.0 if direction != 0 else price
    tp     = price + direction * atr_val * 3.0 if direction != 0 else price

    return Signal(
        symbol=symbol, direction=direction, strategy='momentum',
        strength=round(strength, 3), price=price,
        stop_price=round(stop, 4), take_profit=round(tp, 4),
        reason=reason,
        indicators={
            'fast_ma':  round(fast_ma, 4),
            'slow_ma':  round(slow_ma, 4),
            'rsi':      round(rsi_val, 2),
            'atr':      round(atr_val, 4),
            'ma_diff':  round(ma_diff, 4),
        }
    )


# ── Mean Reversion Signal ─────────────────────────────────────────────────────

def mean_reversion_signal(df: pd.DataFrame, symbol: str,
                            current_position: int = 0) -> Signal:
    """
    Mean reversion strategy:
    - Long  when z-score < -entry_z (price below mean → expect reversion up)
    - Short when z-score > +entry_z (price above mean → expect reversion down)
    - Exit  when |z-score| < exit_z (price returned to mean)

    Uses Bollinger Bands + z-score for entry/exit signals.
    """
    if len(df) < WARMUP_BARS:
        return _flat_signal(symbol, df['close'].iloc[-1], 'mean_reversion', 'Warming up')

    close   = df['close'].values
    price   = float(close[-1])
    atr_val = compute_atr(df)
    rsi_val = compute_rsi(close, MOM_RSI_PERIOD)

    # Z-score
    window     = min(MR_ZSCORE_WINDOW, len(close))
    roll_mean  = float(close[-window:].mean())
    roll_std   = float(close[-window:].std())
    zscore     = (price - roll_mean) / (roll_std + 1e-10)

    # Bollinger Bands
    bb_period  = min(MR_BB_PERIOD, len(close))
    bb_mean    = float(close[-bb_period:].mean())
    bb_std     = float(close[-bb_period:].std())
    bb_upper   = bb_mean + MR_BB_STD * bb_std
    bb_lower   = bb_mean - MR_BB_STD * bb_std

    direction = 0
    reason    = ''
    strength  = min(1.0, abs(zscore) / MR_ENTRY_Z)

    if current_position == 0:
        if zscore < -MR_ENTRY_Z and rsi_val < 40:
            direction = 1
            reason    = f'Z={zscore:.2f} (oversold), RSI={rsi_val:.1f}'
        elif zscore > MR_ENTRY_Z and rsi_val > 60:
            direction = -1
            reason    = f'Z={zscore:.2f} (overbought), RSI={rsi_val:.1f}'

    elif current_position == 1:
        if zscore > -MR_EXIT_Z:
            direction = 0
            reason    = f'Mean reversion complete, Z={zscore:.2f}'
        else:
            direction = 1
            reason    = f'Holding long MR, Z={zscore:.2f}'

    elif current_position == -1:
        if zscore < MR_EXIT_Z:
            direction = 0
            reason    = f'Mean reversion complete, Z={zscore:.2f}'
        else:
            direction = -1
            reason    = f'Holding short MR, Z={zscore:.2f}'

    stop = price - direction * atr_val * 2.0 if direction != 0 else price
    tp   = price + direction * atr_val * 3.0 if direction != 0 else price

    return Signal(
        symbol=symbol, direction=direction, strategy='mean_reversion',
        strength=round(strength, 3), price=price,
        stop_price=round(stop, 4), take_profit=round(tp, 4),
        reason=reason,
        indicators={
            'zscore':    round(zscore, 4),
            'roll_mean': round(roll_mean, 4),
            'roll_std':  round(roll_std, 4),
            'bb_upper':  round(bb_upper, 4),
            'bb_lower':  round(bb_lower, 4),
            'rsi':       round(rsi_val, 2),
            'atr':       round(atr_val, 4),
        }
    )


# ── Flat signal ───────────────────────────────────────────────────────────────

def _flat_signal(symbol: str, price: float,
                  strategy: str, reason: str) -> Signal:
    return Signal(
        symbol=symbol, direction=0, strategy=strategy,
        strength=0.0, price=price,
        stop_price=price, take_profit=price,
        reason=reason, indicators={}
    )


def signal_to_dict(s: Signal) -> dict:
    """Serialize Signal for API/WebSocket."""
    return {
        'symbol':      s.symbol,
        'direction':   s.direction,
        'strategy':    s.strategy,
        'strength':    s.strength,
        'price':       s.price,
        'stop_price':  s.stop_price,
        'take_profit': s.take_profit,
        'reason':      s.reason,
        'indicators':  s.indicators,
    }
