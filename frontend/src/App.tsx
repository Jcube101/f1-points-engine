import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Navbar from './components/Navbar'
import BottomNav from './components/BottomNav'
import Dashboard from './pages/Dashboard'
import TeamBuilder from './pages/TeamBuilder'
import LiveRace from './pages/LiveRace'
import Standings from './pages/Standings'
import ChipAdvisor from './pages/ChipAdvisor'
import ScoreValidator from './pages/ScoreValidator'

export default function App() {
  return (
    <BrowserRouter>
      {/* overflow-x-hidden prevents accidental horizontal scroll on any page */}
      <div className="min-h-screen bg-gray-950 overflow-x-hidden">
        <Navbar />
        {/* pb-14 reserves space for the 56px mobile bottom nav; reset on sm+ */}
        <main className="container mx-auto px-4 py-4 pb-20 sm:py-6 sm:pb-6">
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
        {/* Mobile-only bottom navigation */}
        <BottomNav />
      </div>
    </BrowserRouter>
  )
}
