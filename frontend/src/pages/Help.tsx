import { useState } from 'react'

interface Section {
  title: string
  content: string
}

const FAQ: Section[] = [
  {
    title: 'Getting Started',
    content:
      'F1 Points Engine is a fantasy F1 companion app for the 2026 season. Start by visiting the Dashboard to see the next race countdown, then head to Team Builder to pick your 5 drivers and 2 constructors within a $100M budget. Your team earns fantasy points based on real-world race results each weekend.',
  },
  {
    title: 'Scoring Rules',
    content:
      'Drivers score points for qualifying position, race finish, fastest lap, Driver of the Day, overtakes, and sprint results. Constructors score based on their combined race finishes. DNFs and DSQs result in point deductions. The full breakdown is visible on each driver card — click any driver to see their last-race scoring details.',
  },
  {
    title: 'Chips & Strategy',
    content:
      "Chips are one-time boosts you can play during the season: Triple Captain doubles your captain's points, Wildcard lets you make unlimited free transfers for one gameweek, No Negative prevents negative scoring, and DRS Boost doubles a driver's race points. The Chip Advisor page recommends the best chip for each race based on circuit type, team value, and remaining rounds.",
  },
  {
    title: 'Team Optimizer',
    content:
      'The Team Builder includes an AI optimizer that finds the highest expected-points (xP) team within your budget. It offers two modes — Max Points (pure xP optimisation) and Best Value (highest xP-per-$M). Use the optimizer as a starting point, then tweak based on your own race knowledge and chip strategy.',
  },
  {
    title: 'Intelligence Features',
    content:
      'Phase 2 intelligence tools include: Form vs Luck Detector (identifies if a driver\'s recent results are skill or variance), Circuit Intelligence (avg points by circuit type), Differential Finder (high-ownership value picks), Teammate Comparison (head-to-head stats), and Transfer Planner (suggested moves for upcoming races). Access these from the driver and constructor cards.',
  },
  {
    title: 'Title Race Calculator',
    content:
      'The Title Race page runs 10,000 Monte Carlo simulations of the remaining season to estimate each driver\'s championship win probability. Simulations use each driver\'s last 5 race results weighted by recency. Use the pace sliders to model "what if" scenarios — adjusting a driver\'s pace multiplier between 0.5× and 1.5× instantly re-runs the simulation with debounced updates.',
  },
]

export default function Help() {
  const [openIndex, setOpenIndex] = useState<number | null>(0)

  return (
    <div className="max-w-2xl mx-auto space-y-4">
      <h1 className="text-2xl font-bold text-white">Help & FAQ</h1>
      <p className="text-gray-400 text-sm">Everything you need to know about F1 Points Engine.</p>

      <div className="space-y-2">
        {FAQ.map((section, i) => {
          const isOpen = openIndex === i
          return (
            <div key={i} className="bg-gray-900 rounded-xl overflow-hidden">
              <button
                onClick={() => setOpenIndex(isOpen ? null : i)}
                className="w-full flex items-center justify-between px-5 py-4 text-left"
              >
                <span className="font-semibold text-white text-sm">{section.title}</span>
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={2}
                  className={`w-4 h-4 text-gray-400 flex-shrink-0 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
                >
                  <polyline points="6 9 12 15 18 9" />
                </svg>
              </button>
              <div
                className={`overflow-hidden transition-all duration-300 ease-in-out ${
                  isOpen ? 'max-h-96 opacity-100' : 'max-h-0 opacity-0'
                }`}
              >
                <p className="px-5 pb-5 text-gray-400 text-sm leading-relaxed">{section.content}</p>
              </div>
            </div>
          )
        })}
      </div>

      <div className="text-center pt-4 text-xs text-gray-600">
        F1 Points Engine · 2026 Season · Built for fantasy F1 enthusiasts
      </div>
    </div>
  )
}
