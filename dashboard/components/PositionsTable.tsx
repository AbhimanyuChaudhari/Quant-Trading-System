import { Position } from '@/lib/types';

interface Props {
  positions: Record<string, Position>;
}

export function PositionsTable({ positions }: Props) {
  const items = Object.values(positions);

  if (items.length === 0) {
    return (
      <div style={{ padding: '20px 14px', color: 'var(--text-muted)', fontFamily: 'IBM Plex Mono', fontSize: 12, textAlign: 'center' }}>
        No open positions
      </div>
    );
  }

  return (
    <table className="data-table">
      <thead>
        <tr>
          <th>Symbol</th>
          <th>Side</th>
          <th style={{ textAlign: 'right' }}>Qty</th>
          <th style={{ textAlign: 'right' }}>Entry</th>
          <th style={{ textAlign: 'right' }}>Current</th>
          <th style={{ textAlign: 'right' }}>P&L</th>
          <th style={{ textAlign: 'right' }}>P&L %</th>
        </tr>
      </thead>
      <tbody>
        {items.map(p => (
          <tr key={p.symbol}>
            <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{p.symbol}</td>
            <td>
              <span style={{
                color: p.side === 'long' ? 'var(--green)' : 'var(--red)',
                textTransform: 'uppercase',
                fontSize: 11,
              }}>
                {p.side}
              </span>
            </td>
            <td style={{ textAlign: 'right' }}>{p.qty}</td>
            <td style={{ textAlign: 'right' }}>${p.avg_entry.toFixed(2)}</td>
            <td style={{ textAlign: 'right' }}>${p.current_price.toFixed(2)}</td>
            <td style={{
              textAlign: 'right',
              color: p.unrealized_pnl >= 0 ? 'var(--green)' : 'var(--red)',
            }}>
              {p.unrealized_pnl >= 0 ? '+' : ''}{p.unrealized_pnl.toFixed(2)}
            </td>
            <td style={{
              textAlign: 'right',
              color: p.unrealized_pct >= 0 ? 'var(--green)' : 'var(--red)',
            }}>
              {p.unrealized_pct >= 0 ? '+' : ''}{p.unrealized_pct.toFixed(2)}%
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
