import { useState, useEffect, useRef } from 'react'
import type { LiveSnapshot } from '../lib/types'

/**
 * Derive the correct WebSocket URL for the current environment.
 *
 * - Development (Vite dev server, port 5173): proxy is configured in vite.config.ts
 *   so we connect to the same origin — Vite forwards /ws/* to localhost:8000.
 * - Production (Railway / any single-origin deploy): the backend serves both the
 *   React app and the WebSocket from the same host, so we again use the same origin.
 *   We auto-upgrade to wss:// when the page is served over HTTPS.
 */
function getLiveWsUrl(): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host          // e.g. "myapp.railway.app" or "localhost:5173"
  return `${protocol}//${host}/ws/live`
}

export function useLiveRace() {
  const [snapshot, setSnapshot] = useState<LiveSnapshot | null>(null)
  const [connected, setConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    let ws: WebSocket
    let reconnectTimer: ReturnType<typeof setTimeout>

    function connect() {
      try {
        ws = new WebSocket(getLiveWsUrl())
        wsRef.current = ws

        ws.onopen = () => {
          setConnected(true)
          setError(null)
        }

        ws.onmessage = (e) => {
          try {
            const data: LiveSnapshot = JSON.parse(e.data)
            setSnapshot(data)
          } catch {
            // ignore parse errors
          }
        }

        ws.onerror = () => {
          setError('WebSocket error — live data unavailable')
        }

        ws.onclose = () => {
          setConnected(false)
          // Reconnect after 10 s
          reconnectTimer = setTimeout(connect, 10_000)
        }
      } catch {
        setError('Could not connect to live feed')
      }
    }

    connect()

    return () => {
      clearTimeout(reconnectTimer)
      ws?.close()
    }
  }, [])

  return { snapshot, connected, error }
}
