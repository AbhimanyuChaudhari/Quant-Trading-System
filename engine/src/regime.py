"""
regime.py
---------
Market regime detection.

Three regimes:
  TRENDING   — ADX > threshold, strong directional move
  RANGING    — ADX < threshold, price oscillating
  VOLATILE   — realized vol spike, reduce exposure

The regime determines which signal to use:
  TRENDING  → momentum strategy
  RANGING   → mean reversion strategy
  VOLATILE  → reduce size or go flat
"""

import numpy as np
import pandas as pd
from enum import Enum
from dataclasses import dataclass
from typing import Optional

from src.config import (
    REGIME_ADX_PERIOD,
    REGIME_ADX_THRESHOLD,
    REGIME_VOL_WINDOW,
)


class Regime(Enum):
    TRENDING  = 'trending'
    RANGING   = 'ranging'
    VOLATILE  = 'volatile'
    UNKNOWN   = 'unknown'


@dataclass
class RegimeResult:
    regime:    Regime
    adx:       float
    adx_plus:  float   # +DI
    adx_minus: float   # -DI
    vol_ratio: float   # current vol / historical vol
    trend_dir: int     # +1 = up trend, -1 = down trend, 0 = neutral
    confidence:float   # 0-1


# ── ADX computation ───────────────────────────────────────────────────────────

def compute_adx(df: pd.DataFrame, period: int = REGIME_ADX_PERIOD) -> pd.DataFrame:
    """
    Average Directional Index (ADX) with +DI and -DI.

    ADX measures trend strength (not direction).
    +DI > -DI = uptrend, -DI > +DI = downtrend.
    ADX > 25 = strong trend, ADX < 20 = no trend.
    """
    high  = df['high'].values
    low   = df['low'].values
    close = df['close'].values
    n     = len(df)

    # True Range
    tr    = np.zeros(n)
    dm_plus  = np.zeros(n)
    dm_minus = np.zeros(n)

    for i in range(1, n):
        hl = high[i]  - low[i]
        hc = abs(high[i]  - close[i-1])
        lc = abs(low[i]   - close[i-1])
        tr[i] = max(hl, hc, lc)

        up   = high[i]  - high[i-1]
        down = low[i-1] - low[i]

        dm_plus[i]  = up   if (up > down and up > 0)   else 0
        dm_minus[i] = down if (down > up and down > 0)  else 0

    # Smoothed using Wilder's method
    def wilder_smooth(arr, p):
        result = np.zeros(len(arr))
        result[p] = arr[1:p+1].sum()
        for i in range(p+1, len(arr)):
            result[i] = result[i-1] - result[i-1]/p + arr[i]
        return result

    atr_smooth  = wilder_smooth(tr,       period)
    dmp_smooth  = wilder_smooth(dm_plus,  period)
    dmm_smooth  = wilder_smooth(dm_minus, period)

    # Directional indicators
    with np.errstate(divide='ignore', invalid='ignore'):
        di_plus  = np.where(atr_smooth > 0, 100 * dmp_smooth / atr_smooth, 0)
        di_minus = np.where(atr_smooth > 0, 100 * dmm_smooth / atr_smooth, 0)
        dx       = np.where(
            (di_plus + di_minus) > 0,
            100 * np.abs(di_plus - di_minus) / (di_plus + di_minus),
            0
        )

    # ADX = smoothed DX
    adx = np.zeros(n)
    adx[2*period] = dx[period:2*period+1].mean()
    for i in range(2*period+1, n):
        adx[i] = (adx[i-1] * (period-1) + dx[i]) / period

    result = df.copy()
    result['adx']      = adx
    result['di_plus']  = di_plus
    result['di_minus'] = di_minus
    result['tr']       = tr
    return result


# ── Volatility regime ─────────────────────────────────────────────────────────

def compute_vol_ratio(df: pd.DataFrame, window: int = REGIME_VOL_WINDOW) -> float:
    """
    Compare recent volatility to historical volatility.
    Ratio > 1.5 = elevated volatility regime.
    """
    returns = df['close'].pct_change().dropna()
    if len(returns) < window * 2:
        return 1.0

    recent_vol = returns.iloc[-window//2:].std()
    hist_vol   = returns.iloc[-window:].std()

    return float(recent_vol / (hist_vol + 1e-10))


# ── Main regime detector ──────────────────────────────────────────────────────

def detect_regime(df: pd.DataFrame,
                   adx_period: int     = REGIME_ADX_PERIOD,
                   adx_threshold: float= REGIME_ADX_THRESHOLD,
                   vol_threshold: float= 1.8) -> RegimeResult:
    """
    Detect current market regime from OHLCV bar data.

    Priority:
        1. If vol_ratio > vol_threshold → VOLATILE (override)
        2. If ADX > adx_threshold → TRENDING
        3. Otherwise → RANGING
    """
    if len(df) < adx_period * 2 + 5:
        return RegimeResult(
            regime=Regime.UNKNOWN,
            adx=0, adx_plus=0, adx_minus=0,
            vol_ratio=1.0, trend_dir=0, confidence=0.0
        )

    df_adx  = compute_adx(df, adx_period)
    adx     = float(df_adx['adx'].iloc[-1])
    di_plus = float(df_adx['di_plus'].iloc[-1])
    di_minus= float(df_adx['di_minus'].iloc[-1])
    vol_ratio = compute_vol_ratio(df)

    # Trend direction
    trend_dir = 0
    if di_plus > di_minus:
        trend_dir = 1    # uptrend
    elif di_minus > di_plus:
        trend_dir = -1   # downtrend

    # Regime classification
    if vol_ratio > vol_threshold:
        regime = Regime.VOLATILE
        confidence = min(1.0, (vol_ratio - vol_threshold) / vol_threshold)
    elif adx > adx_threshold:
        regime = Regime.TRENDING
        confidence = min(1.0, (adx - adx_threshold) / adx_threshold)
    else:
        regime = Regime.RANGING
        confidence = min(1.0, (adx_threshold - adx) / adx_threshold)

    return RegimeResult(
        regime=regime,
        adx=round(adx, 2),
        adx_plus=round(di_plus, 2),
        adx_minus=round(di_minus, 2),
        vol_ratio=round(vol_ratio, 3),
        trend_dir=trend_dir,
        confidence=round(confidence, 3),
    )


def regime_to_dict(r: RegimeResult) -> dict:
    """Serialize RegimeResult for API/WebSocket."""
    return {
        'regime':     r.regime.value,
        'adx':        r.adx,
        'di_plus':    r.adx_plus,
        'di_minus':   r.adx_minus,
        'vol_ratio':  r.vol_ratio,
        'trend_dir':  r.trend_dir,
        'confidence': r.confidence,
    }
