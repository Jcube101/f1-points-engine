/**
 * WarmupScreen — shown while the backend is cold-starting (Render free tier).
 *
 * Retries /health every 3 seconds. Once the backend responds it calls onReady()
 * which causes the parent to unmount this screen and render the real app.
 * No technical error messages are ever surfaced to the user.
 */
import { useEffect, useRef, useState } from 'react'

interface Props {
  onReady: () => void
}

export default function WarmupScreen({ onReady }: Props) {
  const [dots, setDots] = useState('.')
  const [elapsed, setElapsed] = useState(0)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const dotRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const startRef = useRef(Date.now())

  useEffect(() => {
    let cancelled = false

    async function probe() {
      try {
        const res = await fetch('/health', { signal: AbortSignal.timeout(4000) })
        if (res.ok && !cancelled) {
          onReady()
          return
        }
      } catch {
        // still warming up — ignore
      }
    }

    // First probe immediately
    probe()

    // Then every 3 s
    intervalRef.current = setInterval(() => {
      probe()
      setElapsed(Math.floor((Date.now() - startRef.current) / 1000))
    }, 3000)

    // Animate the dots
    dotRef.current = setInterval(() => {
      setDots(d => (d.length >= 3 ? '.' : d + '.'))
    }, 500)

    return () => {
      cancelled = true
      if (intervalRef.current) clearInterval(intervalRef.current)
      if (dotRef.current) clearInterval(dotRef.current)
    }
  }, [onReady])

  return (
    <div className="fixed inset-0 bg-gray-950 flex flex-col items-center justify-center px-6 text-center">
      {/* Track + car animation */}
      <div className="w-full max-w-xs mb-10 relative">
        {/* Track */}
        <div className="h-2 bg-gray-800 rounded-full overflow-hidden relative">
          <div className="absolute inset-0 rounded-full bg-gradient-to-r from-gray-800 via-gray-700 to-gray-800" />
          {/* Racing line */}
          <div className="absolute top-1/2 -translate-y-1/2 left-0 right-0 h-px bg-gray-600 opacity-50" />
        </div>

        {/* Car */}
        <div
          className="absolute -top-3.5 text-2xl"
          style={{ animation: 'carRun 2s linear infinite' }}
          aria-hidden
        >
          🏎️
        </div>

        {/* Finish line stripes */}
        <div className="absolute right-0 top-0 h-2 w-4 flex overflow-hidden rounded-r-full" aria-hidden>
          {[...Array(4)].map((_, i) => (
            <div key={i} className={`flex-1 ${i % 2 === 0 ? 'bg-white' : 'bg-gray-900'}`} />
          ))}
        </div>
      </div>

      {/* Heading */}
      <h1 className="text-2xl font-bold text-white mb-3">
        Starting the engine{dots}
      </h1>

      {/* Sub-text */}
      <p className="text-gray-400 text-sm max-w-xs leading-relaxed">
        This can take up to 30 seconds on first load
        {elapsed >= 10 ? ` (${elapsed}s)` : ''}.
        <br />
        Thanks for your patience!
      </p>

      {/* Tyre spin indicators */}
      <div className="flex gap-3 mt-8" aria-hidden>
        {[0, 150, 300].map(delay => (
          <div
            key={delay}
            className="w-4 h-4 rounded-full border-2 border-red-600 border-t-transparent"
            style={{ animation: `spin 0.9s linear infinite`, animationDelay: `${delay}ms` }}
          />
        ))}
      </div>

      <style>{`
        @keyframes carRun {
          0%   { left: -5%; }
          100% { left: 100%; }
        }
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}
