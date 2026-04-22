"""
api.py - Complete fixed version
- Regenerates signals if missing (survives Render restarts)
- Equity curve updates every 3s from Alpaca directly
- Trade log fetches ALL filled orders
- WebSocket broadcasts full state
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

app = FastAPI(title='Quant Trading Engine', version='1.0.0')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


class ConnectionManager:
    def __init__(self):
        self.active: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)
        logger.info(f'WebSocket client connected. Total: {len(self.active)}')

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, data: dict):
        dead = []
        for ws in self.active:
            try:
                await ws.send_text(json.dumps(data, default=str))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


def regenerate_signals():
    """
    Regenerate signals and regimes from bar store.
    Called whenever portfolio.signals is empty — survives Render restarts.
    """
    try:
        from main import portfolio, execution, bar_store
        from src.config import SYMBOLS, WARMUP_BARS
        from src.regime import detect_regime, regime_to_dict, Regime
        from src.signals import momentum_signal, mean_reversion_signal, signal_to_dict, _flat_signal

        for symbol in SYMBOLS:
            if not bar_store.has_enough_data(symbol, WARMUP_BARS):
                continue
            df = bar_store.get(symbol)
            if df is None:
                continue
            try:
                regime_result = detect_regime(df)
                portfolio.update_regime(symbol, regime_to_dict(regime_result))
                current_pos = execution.net_position(symbol)
                if regime_result.regime == Regime.TRENDING:
                    sig = momentum_signal(df, symbol, current_pos)
                elif regime_result.regime == Regime.RANGING:
                    sig = mean_reversion_signal(df, symbol, current_pos)
                else:
                    sig = _flat_signal(
                        symbol,
                        float(df['close'].iloc[-1]),
                        'flat',
                        'Volatile regime'
                    )
                portfolio.update_signal(symbol, signal_to_dict(sig))
            except Exception as e:
                logger.warning(f'Signal regen failed for {symbol}: {e}')
    except Exception as e:
        logger.error(f'regenerate_signals failed: {e}')


def build_snapshot():
    """Build full portfolio snapshot with fresh data from Alpaca."""
    from main import portfolio, execution

    # Always refresh equity from Alpaca
    account = execution.get_account()
    if account:
        portfolio.update_equity(
            account.get('equity', portfolio.equity),
            account.get('cash', portfolio.cash),
        )

    # Regenerate signals if missing (e.g. after Render restart)
    if not portfolio.signals or not portfolio.regimes:
        regenerate_signals()

    # Fresh positions and trades from Alpaca
    positions = execution.get_positions()
    trades    = execution.get_recent_trades(limit=50)

    snap = portfolio.snapshot()
    snap['positions'] = positions
    snap['trade_log'] = trades
    return snap


async def broadcast_loop():
    """Push live snapshot to all WebSocket clients every 3 seconds."""
    while True:
        try:
            if manager.active:
                snap = build_snapshot()
                await manager.broadcast(snap)
        except Exception as e:
            logger.error(f'Broadcast error: {e}')
        await asyncio.sleep(3)


@app.on_event('startup')
async def start_broadcast():
    asyncio.create_task(broadcast_loop())


# ── REST endpoints ────────────────────────────────────────────────────────────

@app.get('/health')
def health():
    return {
        'status':    'ok',
        'timestamp': datetime.now().isoformat(),
        'service':   'quant-trading-engine',
    }


@app.get('/snapshot')
def snapshot():
    return build_snapshot()


@app.get('/metrics')
def metrics():
    from main import portfolio, execution
    account = execution.get_account()
    if account:
        portfolio.update_equity(
            account.get('equity', portfolio.equity),
            account.get('cash', portfolio.cash),
        )
    return portfolio.metrics()


@app.get('/positions')
def positions():
    from main import execution
    return execution.get_positions()


@app.get('/signals')
def signals():
    from main import portfolio
    if not portfolio.signals:
        regenerate_signals()
    return portfolio.signals


@app.get('/regimes')
def regimes():
    from main import portfolio
    if not portfolio.regimes:
        regenerate_signals()
    return portfolio.regimes


@app.get('/trades')
def trades():
    from main import execution
    return execution.get_recent_trades(limit=50)


@app.get('/equity-curve')
def equity_curve():
    from main import portfolio
    return portfolio.equity_curve_list()


# ── WebSocket endpoint ────────────────────────────────────────────────────────

@app.websocket('/ws')
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Send full snapshot immediately on connect
        snap = build_snapshot()
        await websocket.send_text(json.dumps(snap, default=str))

        # Keep connection alive
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info('WebSocket client disconnected')
