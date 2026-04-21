"""
api.py
------
FastAPI server — serves portfolio state to the dashboard.

Endpoints:
  GET  /health              → system health check
  GET  /snapshot            → full portfolio snapshot
  GET  /metrics             → performance metrics only
  GET  /positions           → current positions
  GET  /signals             → latest signals per symbol
  GET  /regimes             → current regime per symbol
  GET  /trades              → recent trade log
  GET  /equity-curve        → equity curve history
  WS   /ws                  → real-time WebSocket updates
"""

import asyncio
import json
import logging
from typing import List
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

app = FastAPI(title='Quant Trading Engine', version='1.0.0')

# Allow dashboard (localhost:3000 or Vercel) to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],   # restrict to your Vercel domain in production
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


# ── WebSocket connection manager ──────────────────────────────────────────────

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
                await ws.send_text(json.dumps(data))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


# ── Background broadcast task ─────────────────────────────────────────────────

async def broadcast_loop():
    """Push portfolio snapshot to all connected WebSocket clients every 2s."""
    from main import portfolio, execution
    while True:
        try:
            if manager.active:
                positions = execution.get_positions()
                snapshot  = portfolio.snapshot()
                snapshot['positions'] = positions
                await manager.broadcast(snapshot)
        except Exception as e:
            logger.error(f'Broadcast error: {e}')
        await asyncio.sleep(2)


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
    from main import portfolio, execution
    positions = execution.get_positions()
    snap = portfolio.snapshot()
    snap['positions'] = positions
    return snap


@app.get('/metrics')
def metrics():
    from main import portfolio
    return portfolio.metrics()


@app.get('/positions')
def positions():
    from main import execution
    return execution.get_positions()


@app.get('/signals')
def signals():
    from main import portfolio
    return portfolio.signals


@app.get('/regimes')
def regimes():
    from main import portfolio
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
        # Send initial snapshot on connect
        from main import portfolio, execution
        positions = execution.get_positions()
        snap = portfolio.snapshot()
        snap['positions'] = positions
        await websocket.send_text(json.dumps(snap))

        # Keep connection alive
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info('WebSocket client disconnected')
