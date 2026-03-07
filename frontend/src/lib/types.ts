// All shared TypeScript types for F1 Points Engine
// Never define inline types in components — always use this file.

export interface Driver {
  id: number
  name: string
  code: string
  team_id: number
  team_name: string
  team_color: string
  price: number
  nationality: string
  image_url: string
  xp: number
  value_score: number
  total_fantasy_pts: number
  // Phase 2 intelligence fields (populated by GET /api/drivers)
  form_status?: 'overperforming' | 'underperforming' | 'on_form'
  form_delta?: number
  circuit_fit_score?: number
  circuit_fit_type?: string
  is_differential?: boolean
}

export interface DriverFormHistory {
  race_name: string
  round: number
  circuit_type: string
  actual: number
  xp: number
}

export interface DriverForm {
  driver_id: number
  driver_code: string
  driver_name: string
  actual_avg: number
  xp_avg: number
  delta: number
  flag: 'overperforming' | 'underperforming' | 'on_form'
  history: DriverFormHistory[]
}

export interface CircuitFitEntry {
  driver_id: number
  driver_code: string
  driver_name: string
  team_name: string
  circuit_type: string
  avg_points: number
  races_counted: number
  fit_score: number
}

export interface UpcomingRaceDifficulty {
  round: number
  race_name: string
  circuit_type: string
  date: string
  driver_fits: Record<string, number>
}

export interface TeammateStats {
  id: number
  name: string
  code: string
  price: number
  avg_fantasy_pts: number
  total_fantasy_pts: number
  avg_qualifying_pos: number
  avg_race_pos: number
  quali_h2h_wins: number
  xp: number
  pts_per_million: number
}

export interface TeammateComparison {
  constructor_id: number
  driver_1: TeammateStats
  driver_2: TeammateStats
  h2h_qualifying_races: number
}

export interface TransferMove {
  race: string
  round: number
  date: string
  circuit_type: string
  drop: { id: number; code: string; name: string; xp: number; price: number }
  add: { id: number; code: string; name: string; xp: number; price: number } | null
  budget_delta: number
  chip_alternative: string | null
  reasoning: string
}

export interface Constructor {
  id: number
  name: string
  code: string
  color_hex: string
  price: number
  drivers: { id: number; name: string; code: string }[]
  xp?: number
  value_score?: number
}

export interface Race {
  id: number
  name: string
  circuit: string
  country: string
  date: string
  round_number: number
  season: number
  session_type: string
  circuit_type: 'street' | 'power' | 'balanced'
}

export interface RaceResult {
  driver_id: number
  driver_name: string
  driver_code: string
  qualifying_pos: number | null
  race_pos: number | null
  sprint_pos: number | null
  dnf: boolean
  dsq: boolean
  fastest_lap: boolean
  driver_of_day: boolean
  positions_gained_race: number
  overtakes: number
}

export interface FantasyPointsBreakdown {
  driver_id: number
  driver_name: string
  qualifying_pts: number
  race_pts: number
  sprint_pts: number
  total: number
}

export interface TeamSelection {
  drivers: Driver[]
  constructors: Constructor[]
  drs_boost_driver_id: number | null
  no_negative: boolean
}

export interface OptimizedTeam {
  drivers: AssetResult[]
  constructors: AssetResult[]
  total_xp: number
  total_price: number
  feasible: boolean
}

export interface AssetResult {
  id: number
  name: string
  code: string
  price: number
  xp: number
  xp_per_million: number
  type: 'driver' | 'constructor'
  team_code: string
}

export interface ChipRecommendation {
  chip: string
  confidence: 'High' | 'Medium' | 'Low'
  reason: string
  alternatives: { chip: string; reason: string }[]
}

export interface WDCStanding {
  position: number
  driver_id: string
  driver_code: string
  driver_name: string
  nationality: string
  team: string
  points: number
  wins: number
}

export interface WCCStanding {
  position: number
  constructor_id: string
  constructor_name: string
  nationality: string
  points: number
  wins: number
}

export interface ValueLeaderboardEntry {
  id: number
  name: string
  code: string
  team: string
  price: number
  total_fantasy_pts: number
  xp: number
  value_score: number
  price_trend: number
}

export interface ScoreValidationEntry {
  race_name: string
  driver_name: string
  driver_code: string
  our_score: number
  official_score: number | null
  delta: number | null
  validated_at: string
}

export interface LiveDriver {
  driver_number: number
  driver_id: string
  name: string
  position: number | null
  fantasy_points: number
  breakdown: {
    race_position_points: number
    positions_gained: number
    overtakes: number
    fastest_lap: boolean
    drs_boost_applied: boolean
  }
}

export interface LiveSnapshot {
  session_type: string
  lap: number
  total_laps: number
  timestamp: string
  stale: boolean
  drivers: LiveDriver[]
  constructors: unknown[]
}

/** One round's entry in the championship points progression chart. */
export interface ProgressionRound {
  round: number
  round_name: string
  /** Cumulative fantasy points per driver, keyed by driver code (e.g. "VER", "NOR"). */
  [driverCode: string]: number | string
}

export interface ApiResponse<T> {
  success: boolean
  data: T
  error?: string
}

// ─── Title Race Simulator ────────────────────────────────────────────────────

export interface TitleOddsEntry {
  driver_code: string
  driver_name: string
  win_probability: number
  current_points: number
  simulated_avg_final: number
}

export interface TitleOddsResult {
  season: number
  simulations: number
  remaining_races: number
  odds: TitleOddsEntry[]
  scenario_summary: string
}

export interface PaceMultiplier {
  driver_code: string
  multiplier: number
}
