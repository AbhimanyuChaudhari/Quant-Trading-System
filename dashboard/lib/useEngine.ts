import { useState, useEffect, useRef, useCallback } from 'react';
import { Snapshot } from './types';

const ENGINE_URL = process.env.NEXT_PUBLIC_ENGINE_URL || 'http://localhost:8000';
const WS_URL     = ENGINE_URL.replace('http', 'ws') + '/ws';

export function useEngine() {
  const [snapshot, setSnapshot]   = useState<Snapshot | null>(null);
  const [connected, setConnected] = useState(false);
  const [error, setError]         = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const retryRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        setError(null);
      };

      ws.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data) as Snapshot;
          setSnapshot(data);
        } catch {
          console.error('Failed to parse snapshot');
        }
      };

      ws.onclose = () => {
        setConnected(false);
        // Retry after 3s
        retryRef.current = setTimeout(connect, 3000);
      };

      ws.onerror = () => {
        setError('Cannot connect to engine. Is it running?');
        ws.close();
      };

    } catch (e) {
      setError('WebSocket connection failed');
    }
  }, []);

  useEffect(() => {
    connect();
    return () => {
      if (wsRef.current) wsRef.current.close();
      if (retryRef.current) clearTimeout(retryRef.current);
    };
  }, [connect]);

  // Fallback: poll REST if WebSocket fails
  useEffect(() => {
    if (connected) return;
    const interval = setInterval(async () => {
      try {
        const res  = await fetch(`${ENGINE_URL}/snapshot`);
        const data = await res.json() as Snapshot;
        setSnapshot(data);
        setError(null);
      } catch {
        // engine not running yet
      }
    }, 3000);
    return () => clearInterval(interval);
  }, [connected]);

  return { snapshot, connected, error };
}
