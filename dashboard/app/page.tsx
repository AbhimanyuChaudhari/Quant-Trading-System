'use client';

import { useEngine } from '@/lib/useEngine';
import { MetricCard } from '@/components/MetricCard';
import { EquityChart } from '@/components/EquityChart';
import { RegimePanel } from '@/components/RegimePanel';
import { PositionsTable } from '@/components/PositionsTable';
import { TradeLog } from '@/components/TradeLog';
import { SignalPanel } from '@/components/SignalPanel';

export default function Dashboard() {
  const { snapshot, connected, error } = useEngine();
  const m = snapshot?.metrics;

  const fmtDollar = (v: number) =>
    '$' + Math.abs(v).toLocaleString('en', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

  const fmtPct = (v: number) =>
    (v >= 0 ? '+' : '') + v.toFixed(3) + '%';

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-primary)' }}>

      {/* ── Top bar ─────────────────────────────────────────────────────── */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 16px', height: 44,
        borderBottom: '1px solid var(--border)',
        background: 'var(--bg-secondary)',
        position: 'sticky', top: 0, zIndex: 100,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            fontFamily: 'IBM Plex Mono', fontWeight: 600, fontSize: 13,
            color: 'var(--text-primary)', letterSpacing: '0.05em',
          }}>
            QUANT//SYS
          </div>
          <div style={{ color: 'var(--border-bright)', fontSize: 12 }}>|</div>
          <div style={{ fontFamily: 'IBM Plex Mono', fontSize: 11, color: 'var(--text-muted)' }}>
            PAPER TRADING
          </div>
          <div style={{ fontFamily: 'IBM Plex Mono', fontSize: 11, color: 'var(--text-muted)' }}>
            AAPL · MSFT · SPY · QQQ
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {/* Connection status */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span className={connected ? 'dot-live' : ''} style={{
              display: 'inline-block', width: 6, height: 6, borderRadius: '50%',
              background: connected ? 'var(--green)' : 'var(--text-muted)',
              boxShadow: connected ? '0 0 6px var(--green)' : 'none',
            }} />
            <span style={{ fontFamily: 'IBM Plex Mono', fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
              {connected ? 'LIVE' : error ? 'DISCONNECTED' : 'CONNECTING...'}
            </span>
          </div>

          {/* Timestamp */}
          {snapshot?.timestamp && (
            <div style={{ fontFamily: 'IBM Plex Mono', fontSize: 10, color: 'var(--text-muted)' }}>
              {new Date(snapshot.timestamp).toLocaleTimeString()}
            </div>
          )}
        </div>
      </div>

      {/* ── Error banner ─────────────────────────────────────────────────── */}
      {error && (
        <div style={{
          background: 'var(--red-dim)', borderBottom: '1px solid var(--red)',
          padding: '8px 16px',
          fontFamily: 'IBM Plex Mono', fontSize: 11, color: 'var(--red)',
        }}>
          ⚠ {error} — Start the engine: <code>python main.py</code>
        </div>
      )}

      <div style={{ padding: '12px 16px', display: 'flex', flexDirection: 'column', gap: 12 }}>

        {/* ── Metric cards ─────────────────────────────────────────────────── */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 8 }}>
          <MetricCard
            label="Portfolio Value"
            value={m ? fmtDollar(m.equity) : '$100,000.00'}
            sub={m ? `Cash: ${fmtDollar(m.cash)}` : 'Awaiting data'}
            highlight
          />
          <MetricCard
            label="Total P&L"
            value={m ? (m.pnl_total >= 0 ? '+' : '') + fmtDollar(m.pnl_total) : '$0.00'}
            sub={m ? fmtPct(m.pnl_pct) : '0.000%'}
            positive={m ? m.pnl_total >= 0 : null}
          />
          <MetricCard
            label="Sharpe Ratio"
            value={m ? m.sharpe_ratio.toFixed(3) : '—'}
            sub="Annualized"
            positive={m ? m.sharpe_ratio > 0 : null}
          />
          <MetricCard
            label="Max Drawdown"
            value={m ? m.max_drawdown_pct.toFixed(3) + '%' : '0.000%'}
            sub={m ? `Peak: ${fmtDollar(m.peak_equity)}` : '—'}
            positive={m ? m.max_drawdown_pct > -5 : null}
          />
          <MetricCard
            label="Win Rate"
            value={m ? m.win_rate_pct.toFixed(1) + '%' : '—'}
            sub={m ? `${m.n_trades} trades` : '0 trades'}
            positive={m ? m.win_rate_pct >= 50 : null}
          />
        </div>

        {/* ── Equity chart + Regime panel ──────────────────────────────────── */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: 12 }}>

          {/* Equity chart */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">Equity Curve</span>
              {m && (
                <span style={{
                  fontFamily: 'IBM Plex Mono', fontSize: 11,
                  color: m.pnl_total >= 0 ? 'var(--green)' : 'var(--red)',
                }}>
                  {m.pnl_total >= 0 ? '+' : ''}{fmtDollar(m.pnl_total)} ({fmtPct(m.pnl_pct)})
                </span>
              )}
            </div>
            <div style={{ height: 200, padding: '8px 4px 4px' }}>
              <EquityChart
                data={snapshot?.equity_curve || []}
                initialEquity={m?.initial_equity || 100000}
              />
            </div>
          </div>

          {/* Regime panel */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">Market Regime</span>
              <span style={{ fontFamily: 'IBM Plex Mono', fontSize: 10, color: 'var(--text-muted)' }}>
                ADX · TREND · VOL
              </span>
            </div>
            <RegimePanel
              regimes={snapshot?.regimes || {}}
              signals={snapshot?.signals || {}}
            />
          </div>
        </div>

        {/* ── Positions + Signals ──────────────────────────────────────────── */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>

          {/* Positions */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">Open Positions</span>
              <span style={{ fontFamily: 'IBM Plex Mono', fontSize: 10, color: 'var(--text-muted)' }}>
                {Object.keys(snapshot?.positions || {}).length} active
              </span>
            </div>
            <PositionsTable positions={snapshot?.positions || {}} />
          </div>

          {/* Signals */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">Live Signals</span>
              <span style={{ fontFamily: 'IBM Plex Mono', fontSize: 10, color: 'var(--text-muted)' }}>
                MOMENTUM · MEAN-REV
              </span>
            </div>
            <SignalPanel signals={snapshot?.signals || {}} />
          </div>
        </div>

        {/* ── Trade log ────────────────────────────────────────────────────── */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">Trade Log</span>
            <span style={{ fontFamily: 'IBM Plex Mono', fontSize: 10, color: 'var(--text-muted)' }}>
              {snapshot?.trade_log?.length || 0} total trades
            </span>
          </div>
          <TradeLog trades={snapshot?.trade_log || []} />
        </div>

        {/* ── Footer ───────────────────────────────────────────────────────── */}
        <div style={{
          textAlign: 'center', padding: '8px',
          fontFamily: 'IBM Plex Mono', fontSize: 10,
          color: 'var(--text-muted)',
          borderTop: '1px solid var(--border)',
        }}>
          PAPER TRADING ONLY · NOT FINANCIAL ADVICE · Abhimanyu Chaudhari · MS FinTech, NJIT
        </div>
      </div>
    </div>
  );
}
