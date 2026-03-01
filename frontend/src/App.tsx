import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Navbar from './components/Navbar'
import Dashboard from './pages/Dashboard'
import TeamBuilder from './pages/TeamBuilder'
import LiveRace from './pages/LiveRace'
import Standings from './pages/Standings'
import ChipAdvisor from './pages/ChipAdvisor'
import ScoreValidator from './pages/ScoreValidator'

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-950">
        <Navbar />
        <main className="container mx-auto px-4 py-6">
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/team" element={<TeamBuilder />} />
            <Route path="/live" element={<LiveRace />} />
            <Route path="/standings" element={<Standings />} />
            <Route path="/chips" element={<ChipAdvisor />} />
            <Route path="/validation" element={<ScoreValidator />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
