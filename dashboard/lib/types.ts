export interface Metrics {
  equity: number;
  cash: number;
  initial_equity: number;
  pnl_total: number;
  pnl_pct: number;
  peak_equity: number;
  max_drawdown_pct: number;
  sharpe_ratio: number;
  n_trades: number;
  win_rate_pct: number;
}

export interface EquityPoint {
  timestamp: string;
  equity: number;
  cash: number;
  pnl: number;
}

export interface Position {
  symbol: string;
  qty: number;
  side: string;
  avg_entry: number;
  market_val: number;
  unrealized_pnl: number;
  unrealized_pct: number;
  current_price: number;
}

export interface Signal {
  symbol: string;
  direction: number;
  strategy: string;
  strength: number;
  price: number;
  stop_price: number;
  take_profit: number;
  reason: string;
  indicators: Record<string, number>;
  updated_at: string;
}

export interface Regime {
  regime: 'trending' | 'ranging' | 'volatile' | 'unknown';
  adx: number;
  di_plus: number;
  di_minus: number;
  vol_ratio: number;
  trend_dir: number;
  confidence: number;
  updated_at: string;
}

export interface Trade {
  id: string;
  symbol: string;
  side: string;
  qty: number;
  price: number;
  strategy: string;
  regime: string;
  timestamp: string;
  stop: number;
  tp: number;
}

export interface Snapshot {
  metrics: Metrics;
  equity_curve: EquityPoint[];
  signals: Record<string, Signal>;
  regimes: Record<string, Regime>;
  positions: Record<string, Position>;
  trade_log: Trade[];
  timestamp: string;
}
