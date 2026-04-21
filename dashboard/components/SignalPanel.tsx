import { Signal } from '@/lib/types';

interface Props {
  signals: Record<string, Signal>;
}

export function SignalPanel({ signals }: Props) {
  const items = Object.values(signals);

  if (items.length === 0) {
    return (
      <div style={{ padding: '12px 14px', color: 'var(--text-muted)', fontFamily: 'IBM Plex Mono', fontSize: 12 }}>
        Waiting for signals...
      </div>
    );
  }

  return (
    <div>
      {items.map(sig => (
        <div key={sig.symbol} style={{
          padding: '10px 14px',
          borderBottom: '1px solid var(--border)',
        }}>
          {/* Header row */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
            <span style={{ fontFamily: 'IBM Plex Mono', fontWeight: 600, fontSize: 13 }}>
              {sig.symbol}
            </span>
            <span style={{
              fontFamily: 'IBM Plex Mono',
              fontSize: 12,
              color: sig.direction > 0 ? 'var(--green)' :
                     sig.direction < 0 ? 'var(--red)' : 'var(--text-muted)',
            }}>
              {sig.direction > 0 ? '▲ LONG' : sig.direction < 0 ? '▼ SHORT' : '— FLAT'}
            </span>
            <span style={{
              fontFamily: 'IBM Plex Mono', fontSize: 10,
              color: 'var(--text-muted)', textTransform: 'uppercase',
            }}>
              {sig.strategy}
            </span>

            {/* Strength bar */}
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: 6 }}>
              <div style={{
                flex: 1, height: 3,
                background: 'var(--bg-secondary)',
                borderRadius: 2, overflow: 'hidden',
              }}>
                <div style={{
                  height: '100%',
                  width: `${sig.strength * 100}%`,
                  background: sig.direction > 0 ? 'var(--green)' :
                               sig.direction < 0 ? 'var(--red)' : 'var(--text-muted)',
                  transition: 'width 0.3s ease',
                }} />
              </div>
              <span style={{ color: 'var(--text-muted)', fontFamily: 'IBM Plex Mono', fontSize: 10, width: 28 }}>
                {(sig.strength * 100).toFixed(0)}%
              </span>
            </div>
          </div>

          {/* Reason */}
          <div style={{ color: 'var(--text-muted)', fontSize: 11, fontFamily: 'IBM Plex Mono', marginBottom: 6 }}>
            {sig.reason}
          </div>

          {/* Key indicators */}
          <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap' }}>
            {Object.entries(sig.indicators).slice(0, 5).map(([k, v]) => (
              <div key={k} style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                <span style={{ color: 'var(--text-muted)', fontFamily: 'IBM Plex Mono', fontSize: 10, textTransform: 'uppercase' }}>
                  {k}
                </span>
                <span style={{ color: 'var(--text-secondary)', fontFamily: 'IBM Plex Mono', fontSize: 11 }}>
                  {typeof v === 'number' ? v.toFixed(3) : v}
                </span>
              </div>
            ))}

            {/* Stop / TP */}
            {sig.stop_price > 0 && (
              <div style={{ display: 'flex', gap: 4 }}>
                <span style={{ color: 'var(--red)', fontFamily: 'IBM Plex Mono', fontSize: 10 }}>STOP</span>
                <span style={{ color: 'var(--text-secondary)', fontFamily: 'IBM Plex Mono', fontSize: 11 }}>
                  ${sig.stop_price.toFixed(2)}
                </span>
              </div>
            )}
            {sig.take_profit > 0 && (
              <div style={{ display: 'flex', gap: 4 }}>
                <span style={{ color: 'var(--green)', fontFamily: 'IBM Plex Mono', fontSize: 10 }}>TP</span>
                <span style={{ color: 'var(--text-secondary)', fontFamily: 'IBM Plex Mono', fontSize: 11 }}>
                  ${sig.take_profit.toFixed(2)}
                </span>
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
