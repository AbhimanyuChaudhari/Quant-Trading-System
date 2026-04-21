import { Trade } from '@/lib/types';

interface Props {
  trades: Trade[];
}

export function TradeLog({ trades }: Props) {
  const recent = [...trades].reverse().slice(0, 20);

  if (recent.length === 0) {
    return (
      <div style={{ padding: '20px 14px', color: 'var(--text-muted)', fontFamily: 'IBM Plex Mono', fontSize: 12, textAlign: 'center' }}>
        No trades yet
      </div>
    );
  }

  return (
    <table className="data-table">
      <thead>
        <tr>
          <th>Time</th>
          <th>Symbol</th>
          <th>Side</th>
          <th style={{ textAlign: 'right' }}>Qty</th>
          <th style={{ textAlign: 'right' }}>Price</th>
          <th>Strategy</th>
          <th>Regime</th>
        </tr>
      </thead>
      <tbody>
        {recent.map((t, i) => {
          const ts = new Date(t.timestamp);
          const timeStr = ts.getHours().toString().padStart(2,'0') + ':' +
                          ts.getMinutes().toString().padStart(2,'0') + ':' +
                          ts.getSeconds().toString().padStart(2,'0');
          return (
            <tr key={t.id || i}>
              <td style={{ color: 'var(--text-muted)' }}>{timeStr}</td>
              <td style={{ fontWeight: 600 }}>{t.symbol}</td>
              <td>
                <span style={{
                  color: t.side === 'buy' ? 'var(--green)' : 'var(--red)',
                  textTransform: 'uppercase',
                  fontSize: 11,
                }}>
                  {t.side}
                </span>
              </td>
              <td style={{ textAlign: 'right' }}>{t.qty}</td>
              <td style={{ textAlign: 'right' }}>${typeof t.price === 'number' ? t.price.toFixed(2) : '—'}</td>
              <td style={{ color: 'var(--text-muted)', fontSize: 11 }}>{t.strategy || '—'}</td>
              <td>
                <span className={`badge badge-${t.regime || 'unknown'}`}>
                  {t.regime || '—'}
                </span>
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
