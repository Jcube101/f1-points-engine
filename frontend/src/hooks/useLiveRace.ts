import { useState, useEffect, useRef } from 'react'
import type { LiveSnapshot } from '../lib/types'

export function useLiveRace() {
  const [snapshot, setSnapshot] = useState<LiveSnapshot | null>(null)
  const [connected, setConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    const wsUrl = `ws://${window.location.hostname}:8000/ws/live`
    let ws: WebSocket
    let reconnectTimer: ReturnType<typeof setTimeout>

    function connect() {
      try {
        ws = new WebSocket(wsUrl)
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
          // Reconnect after 10s
          reconnectTimer = setTimeout(connect, 10_000)
        }
      } catch (err) {
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
