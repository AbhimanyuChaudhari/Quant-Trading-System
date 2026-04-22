import { Regime } from '@/lib/types';

interface Props {
  regimes: Record<string, Regime>;
  signals: Record<string, any>;
}

export function RegimePanel({ regimes, signals }: Props) {
  const symbols = Object.keys(regimes);

  return (
    <div style={{ overflowY: 'auto', maxHeight: '220px' }}>
      {symbols.length === 0 && (
        <div style={{ padding: '16px 14px', color: 'var(--text-muted)', fontFamily: 'IBM Plex Mono', fontSize: 11, textAlign: 'center' }}>
          Generating signals after warmup...
        </div>
      )}
      {symbols.map(sym => {
        const r   = regimes[sym];
        const sig = signals[sym];
        const dir = sig?.direction ?? 0;

        return (
          <div key={sym} style={{
            padding: '8px 14px',
            borderBottom: '1px solid var(--border)',
            display: 'flex',
            alignItems: 'center',
            gap: 8,
          }}>
            <div style={{
              fontFamily: 'IBM Plex Mono', fontWeight: 600,
              fontSize: 12, width: 48, color: 'var(--text-primary)',
              flexShrink: 0,
            }}>{sym}</div>

            <span className={`badge badge-${r.regime}`}
              style={{ fontSize: 9, padding: '1px 6px', flexShrink: 0 }}>
              {r.regime}
            </span>

            <div style={{
              fontFamily: 'IBM Plex Mono', fontSize: 11, width: 48,
              color: dir > 0 ? 'var(--green)' : dir < 0 ? 'var(--red)' : 'var(--text-muted)',
              flexShrink: 0,
            }}>
              {dir > 0 ? '▲ L' : dir < 0 ? '▼ S' : '— F'}
            </div>

            <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: 4 }}>
              <div style={{
                flex: 1, height: 3,
                background: 'var(--bg-secondary)', borderRadius: 2, overflow: 'hidden',
              }}>
                <div style={{
                  height: '100%',
                  width: `${Math.min(100, r.adx)}%`,
                  background: r.adx > 25 ? 'var(--blue)' : 'var(--text-muted)',
                  borderRadius: 2, transition: 'width 0.3s ease',
                }} />
              </div>
              <span style={{
                color: 'var(--text-muted)', fontFamily: 'IBM Plex Mono',
                fontSize: 10, width: 24, flexShrink: 0,
              }}>
                {r.adx.toFixed(0)}
              </span>
            </div>

            {sig?.reason && (
              <div style={{
                fontFamily: 'IBM Plex Mono', fontSize: 10,
                color: 'var(--text-muted)', maxWidth: 160,
                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
              }}>
                {sig.reason}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
