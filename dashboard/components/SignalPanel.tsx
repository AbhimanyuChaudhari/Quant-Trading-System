import { Signal } from '@/lib/types';

interface Props {
  signals: Record<string, Signal>;
}

export function SignalPanel({ signals }: Props) {
  const items = Object.values(signals);

  if (items.length === 0) {
    return (
      <div style={{ padding: '16px 14px', color: 'var(--text-muted)', fontFamily: 'IBM Plex Mono', fontSize: 11, textAlign: 'center' }}>
        Generating signals after warmup...
      </div>
    );
  }

  return (
    <div style={{ overflowY: 'auto', maxHeight: '220px' }}>
      {items.map(sig => (
        <div key={sig.symbol} style={{
          padding: '8px 14px',
          borderBottom: '1px solid var(--border)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
            <span style={{ fontFamily: 'IBM Plex Mono', fontWeight: 600, fontSize: 12, width: 48 }}>
              {sig.symbol}
            </span>
            <span style={{
              fontFamily: 'IBM Plex Mono', fontSize: 11,
              color: sig.direction > 0 ? 'var(--green)' :
                     sig.direction < 0 ? 'var(--red)' : 'var(--text-muted)',
              width: 52,
            }}>
              {sig.direction > 0 ? '▲ LONG' : sig.direction < 0 ? '▼ SHORT' : '— FLAT'}
            </span>
            <span style={{
              fontFamily: 'IBM Plex Mono', fontSize: 10,
              color: 'var(--text-muted)', textTransform: 'uppercase',
              width: 80,
            }}>
              {sig.strategy}
            </span>

            {/* Strength bar */}
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: 4 }}>
              <div style={{
                flex: 1, height: 3,
                background: 'var(--bg-secondary)', borderRadius: 2, overflow: 'hidden',
              }}>
                <div style={{
                  height: '100%',
                  width: `${sig.strength * 100}%`,
                  background: sig.direction > 0 ? 'var(--green)' :
                               sig.direction < 0 ? 'var(--red)' : 'var(--text-muted)',
                  transition: 'width 0.3s ease',
                }} />
              </div>
              <span style={{
                color: 'var(--text-muted)', fontFamily: 'IBM Plex Mono',
                fontSize: 10, width: 28,
              }}>
                {(sig.strength * 100).toFixed(0)}%
              </span>
            </div>

            {/* Price */}
            <span style={{
              fontFamily: 'IBM Plex Mono', fontSize: 11,
              color: 'var(--text-secondary)', width: 60, textAlign: 'right',
            }}>
              ${sig.price?.toFixed(2)}
            </span>
          </div>

          {/* Reason */}
          <div style={{
            color: 'var(--text-muted)', fontSize: 10,
            fontFamily: 'IBM Plex Mono', paddingLeft: 56,
          }}>
            {sig.reason}
          </div>
        </div>
      ))}
    </div>
  );
}
