"""
main.py
-------
Entry point for the quant trading engine.

Starts:
  1. Historical data warmup
  2. Real-time WebSocket stream
  3. Strategy loop (runs on every new bar)
  4. FastAPI server (in background task)
"""

import asyncio
import logging
import sys
from datetime import datetime

from src.config import SYMBOLS, WARMUP_BARS, API_HOST, API_PORT
from src.data import BarStore, MarketDataStream, fetch_historical_bars, is_market_open
from src.regime import detect_regime, regime_to_dict, Regime
from src.signals import momentum_signal, mean_reversion_signal, signal_to_dict
from src.risk import RiskManager
from src.execution import ExecutionEngine
from src.portfolio import Portfolio

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('engine.log'),
    ]
)
logger = logging.getLogger(__name__)


# ── Global state ──────────────────────────────────────────────────────────────
bar_store  = BarStore(max_bars=200)
risk_mgr   = RiskManager()
execution  = ExecutionEngine()
portfolio  = Portfolio()
stream     = MarketDataStream(bar_store)


# ── Strategy loop ─────────────────────────────────────────────────────────────

async def on_new_bar(symbol: str, bar: dict):
    """Called every time a new bar arrives. This is where the strategy runs."""
    if not bar_store.has_enough_data(symbol, WARMUP_BARS):
        return

    df = bar_store.get(symbol)
    if df is None or len(df) < WARMUP_BARS:
        return

    # 1. Detect regime
    regime_result = detect_regime(df)
    portfolio.update_regime(symbol, regime_to_dict(regime_result))

    # 2. Generate signal based on regime
    current_pos = execution.net_position(symbol)

    if regime_result.regime == Regime.VOLATILE:
        if current_pos != 0:
            logger.info(f'{symbol}: VOLATILE regime — closing position')
            execution.close_position(symbol)
        return

    elif regime_result.regime == Regime.TRENDING:
        sig = momentum_signal(df, symbol, current_pos)
    else:
        sig = mean_reversion_signal(df, symbol, current_pos)

    portfolio.update_signal(symbol, signal_to_dict(sig))

    # 3. No change needed
    if sig.direction == current_pos:
        return

    # 4. Close existing position if direction changed
    if current_pos != 0 and sig.direction != current_pos:
        logger.info(f'{symbol}: Signal reversed — closing position')
        execution.close_position(symbol)
        execution.positions[symbol] = 0
        current_pos = 0

    # 5. Open new position
    if sig.direction != 0:
        account = execution.get_account()
        equity  = account.get('equity', portfolio.equity)
        risk_mgr.update_equity(equity)

        from src.signals import compute_atr
        atr_val = compute_atr(df)

        decision = risk_mgr.evaluate(
            symbol=symbol,
            direction=sig.direction,
            signal_strength=sig.strength,
            current_price=sig.price,
            atr=atr_val,
            account_equity=equity,
            open_positions=execution.positions,
        )

        if risk_mgr.is_killed:
            logger.critical('Kill switch active — closing all positions')
            execution.close_all_positions()
            return

        if decision.approved:
            trade = execution.submit_bracket_order(
                symbol=symbol,
                direction=sig.direction,
                qty=decision.qty,
                stop_price=decision.stop_price,
                take_profit=decision.take_profit,
                strategy=sig.strategy,
                regime=regime_result.regime.value,
            )
            if trade:
                portfolio.record_trade({
                    'id':        trade.id,
                    'symbol':    symbol,
                    'side':      trade.side,
                    'qty':       trade.qty,
                    'price':     trade.entry_price,
                    'strategy':  trade.strategy,
                    'regime':    trade.regime,
                    'timestamp': trade.timestamp.isoformat(),
                    'stop':      trade.stop_price,
                    'tp':        trade.take_profit,
                })
        else:
            logger.info(f'{symbol}: Risk REJECTED — {decision.reason}')

    # 6. Update portfolio equity
    account = execution.get_account()
    if account:
        portfolio.update_equity(
            account.get('equity', portfolio.equity),
            account.get('cash',   portfolio.cash),
        )


# ── Startup sequence ──────────────────────────────────────────────────────────

async def startup():
    logger.info('=' * 60)
    logger.info('  Quant Trading Engine Starting')
    logger.info(f'  Symbols: {SYMBOLS}')
    logger.info(f'  Warmup:  {WARMUP_BARS} bars')
    logger.info('=' * 60)

    # Load account state
    account = execution.get_account()
    if account:
        portfolio.initial_equity = account['equity']
        portfolio.equity         = account['equity']
        portfolio.cash           = account['cash']
        logger.info(f'Account equity: ${account["equity"]:,.2f}')
    else:
        logger.warning('Could not load account — using default equity')

    # Warmup with historical data
    logger.info('Loading historical data for warmup...')
    historical = fetch_historical_bars(SYMBOLS, n_bars=WARMUP_BARS + 20)
    for symbol, df in historical.items():
        for _, row in df.iterrows():
            bar_store.update(symbol, row.to_dict())

    bars_loaded = {s: len(bar_store.get(s)) for s in SYMBOLS if bar_store.get(s) is not None}
    logger.info(f'Warmup complete. Bars loaded: {bars_loaded}')

    # Generate initial signals for ALL symbols right now
    # This ensures dashboard shows signals immediately on startup
    logger.info('Generating initial signals...')
    for symbol in SYMBOLS:
        if not bar_store.has_enough_data(symbol, WARMUP_BARS):
            logger.debug(f'{symbol}: not enough warmup data, skipping')
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
                from src.signals import _flat_signal
                sig = _flat_signal(
                    symbol,
                    float(df['close'].iloc[-1]),
                    'flat',
                    'Volatile regime — no new trades'
                )
            portfolio.update_signal(symbol, signal_to_dict(sig))
            logger.info(f'  {symbol}: regime={regime_result.regime.value} signal={sig.direction} ({sig.strategy})')
        except Exception as e:
            logger.warning(f'  {symbol}: initial signal failed — {e}')

    # Register strategy callback for live bars
    stream.register_callback(on_new_bar)
    logger.info('Engine ready. Starting data stream...')


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    await startup()

    import uvicorn
    from api import app as fastapi_app

    # Start API server as a background task
    config = uvicorn.Config(
        app=fastapi_app,
        host=API_HOST,
        port=API_PORT,
        log_level='warning',
    )
    server = uvicorn.Server(config)
    api_task = asyncio.create_task(server.serve())

    # Give API a moment to start
    await asyncio.sleep(1)
    logger.info(f'API server running on http://{API_HOST}:{API_PORT}')

    # Start WebSocket stream (keeps engine alive)
    try:
        await stream.start(SYMBOLS)
    except Exception as e:
        logger.error(f'Stream failed: {e}')
    finally:
        api_task.cancel()
        logger.info('Engine stopped.')


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info('Engine stopped by user.')