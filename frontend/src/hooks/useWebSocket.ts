import { useEffect, useRef, useCallback, useState } from 'react';
import { WSEvent } from '../types';

export function useWebSocket(
  gameId: number | null,
  viewer: 'normal' | 'god' = 'normal',
  onEvent?: (event: WSEvent) => void
) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnects = 5;
  const [connected, setConnected] = useState(false);
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  const connect = useCallback(() => {
    if (!gameId) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const url = `${protocol}//${host}/ws/game/${gameId}?viewer=${viewer}`;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      reconnectAttempts.current = 0;
    };

    ws.onmessage = (msg) => {
      try {
        const event: WSEvent = JSON.parse(msg.data);
        onEventRef.current?.(event);
      } catch {}
    };

    ws.onclose = () => {
      setConnected(false);
      if (reconnectAttempts.current < maxReconnects) {
        const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 10000);
        reconnectAttempts.current++;
        setTimeout(connect, delay);
      }
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [gameId, viewer]);

  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close();
    };
  }, [connect]);

  return { connected };
}
