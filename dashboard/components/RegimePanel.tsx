import { Regime } from '@/lib/types';

interface Props {
  regimes: Record<string, Regime>;
  signals: Record<string, any>;
}

export function RegimePanel({ regimes, signals }: Props) {
  const symbols = Object.keys(regimes);

  return (
    <div style={{ padding: '8px 0' }}>
      {symbols.length === 0 && (
        <div style={{ padding: '12px 14px', color: 'var(--text-muted)', fontFamily: 'IBM Plex Mono', fontSize: 12 }}>
          Waiting for data...
        </div>
      )}
      {symbols.map(sym => {
        const r   = regimes[sym];
        const sig = signals[sym];
        const dir = sig?.direction ?? 0;

        return (
          <div key={sym} style={{
            padding: '10px 14px',
            borderBottom: '1px solid var(--border)',
            display: 'flex',
            alignItems: 'center',
            gap: 10,
          }}>
            {/* Symbol */}
            <div style={{
              fontFamily: 'IBM Plex Mono',
              fontWeight: 600,
              fontSize: 13,
              width: 52,
              color: 'var(--text-primary)',
            }}>{sym}</div>

            {/* Regime badge */}
            <span className={`badge badge-${r.regime}`}>{r.regime}</span>

            {/* Direction */}
            <div style={{
              fontFamily: 'IBM Plex Mono',
              fontSize: 12,
              color: dir > 0 ? 'var(--green)' : dir < 0 ? 'var(--red)' : 'var(--text-muted)',
              width: 40,
            }}>
              {dir > 0 ? '▲ LONG' : dir < 0 ? '▼ SHORT' : '— FLAT'}
            </div>

            {/* ADX */}
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ color: 'var(--text-muted)', fontFamily: 'IBM Plex Mono', fontSize: 10 }}>ADX</span>
                <div style={{
                  flex: 1,
                  height: 3,
                  background: 'var(--bg-secondary)',
                  borderRadius: 2,
                  overflow: 'hidden',
                }}>
                  <div style={{
                    height: '100%',
                    width: `${Math.min(100, r.adx)}%`,
                    background: r.adx > 25 ? 'var(--blue)' : 'var(--text-muted)',
                    borderRadius: 2,
                    transition: 'width 0.3s ease',
                  }} />
                </div>
                <span style={{ color: 'var(--text-secondary)', fontFamily: 'IBM Plex Mono', fontSize: 11, width: 28 }}>
                  {r.adx.toFixed(1)}
                </span>
              </div>
            </div>

            {/* Strategy */}
            {sig && (
              <div style={{
                fontFamily: 'IBM Plex Mono',
                fontSize: 10,
                color: 'var(--text-muted)',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
              }}>
                {sig.strategy}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
