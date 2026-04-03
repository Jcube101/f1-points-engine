import React, { useState, useCallback } from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App'
import WarmupScreen from './components/WarmupScreen'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
})

function Root() {
  const [ready, setReady] = useState(false)
  const handleReady = useCallback(() => setReady(true), [])

  if (!ready) {
    return <WarmupScreen onReady={handleReady} />
  }

  return (
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  )
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>
)
