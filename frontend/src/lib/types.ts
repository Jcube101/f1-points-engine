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

export interface ApiResponse<T> {
  success: boolean
  data: T
  error?: string
}
