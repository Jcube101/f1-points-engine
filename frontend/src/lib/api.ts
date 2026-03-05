// API client for F1 Points Engine backend
import axios from 'axios'
import type {
  Driver, Constructor, Race, RaceResult, OptimizedTeam,
  FantasyPointsBreakdown, ChipRecommendation,
  WDCStanding, WCCStanding, ValueLeaderboardEntry,
  ScoreValidationEntry, ProgressionRound,
  DriverForm, CircuitFitEntry, UpcomingRaceDifficulty,
  TeammateComparison, TransferMove, ApiResponse,
} from './types'

const BASE_URL = '/api'

const http = axios.create({ baseURL: BASE_URL })

// ─── Drivers ────────────────────────────────────────────────────────────────

export async function fetchDrivers(): Promise<Driver[]> {
  const res = await http.get<ApiResponse<Driver[]>>('/drivers')
  return res.data.data
}

export async function fetchDriver(id: number): Promise<Driver> {
  const res = await http.get<ApiResponse<Driver>>(`/drivers/${id}`)
  return res.data.data
}

// ─── Constructors ────────────────────────────────────────────────────────────

export async function fetchConstructors(): Promise<Constructor[]> {
  const res = await http.get<ApiResponse<Constructor[]>>('/constructors')
  return res.data.data
}

// ─── Races ───────────────────────────────────────────────────────────────────

export async function fetchRaces(season = 2026): Promise<Race[]> {
  const res = await http.get<ApiResponse<Race[]>>('/races', { params: { season } })
  return res.data.data
}

export async function fetchRaceResults(raceId: number): Promise<RaceResult[]> {
  const res = await http.get<ApiResponse<RaceResult[]>>(`/races/${raceId}/results`)
  return res.data.data
}

// ─── Team Optimizer ──────────────────────────────────────────────────────────

export async function optimizeTeam(budget?: number): Promise<{ max_points: OptimizedTeam; best_value: OptimizedTeam }> {
  const res = await http.post<ApiResponse<{ max_points: OptimizedTeam; best_value: OptimizedTeam }>>('/team/optimize', { budget })
  return res.data.data
}

// ─── Points ──────────────────────────────────────────────────────────────────

export async function calculatePoints(payload: {
  driver_ids: number[]
  constructor_ids: number[]
  race_id: number
  drs_boost_driver_id?: number | null
  no_negative?: boolean
}): Promise<{ total: number; breakdown: FantasyPointsBreakdown[] }> {
  const res = await http.post<ApiResponse<{ total: number; breakdown: FantasyPointsBreakdown[] }>>('/points/calculate', payload)
  return res.data.data
}

export async function fetchLeaderboard(): Promise<{ drivers: ValueLeaderboardEntry[]; constructors: unknown[] }> {
  const res = await http.get<ApiResponse<{ drivers: ValueLeaderboardEntry[]; constructors: unknown[] }>>('/points/leaderboard')
  return res.data.data
}

// ─── Chips ───────────────────────────────────────────────────────────────────

export async function fetchChipRecommendation(payload: {
  race_id: number
  chips_remaining: string[]
  team_value: number
  transfers_banked: number
  races_completed: number
  wet_weather_forecast?: boolean
}): Promise<ChipRecommendation> {
  const res = await http.post<ApiResponse<ChipRecommendation>>('/chips/recommend', payload)
  return res.data.data
}

// ─── Standings ───────────────────────────────────────────────────────────────

export async function fetchWDC(season = 2026): Promise<WDCStanding[]> {
  const res = await http.get<ApiResponse<WDCStanding[]>>('/standings/wdc', { params: { season } })
  return res.data.data
}

export async function fetchWCC(season = 2026): Promise<WCCStanding[]> {
  const res = await http.get<ApiResponse<WCCStanding[]>>('/standings/wcc', { params: { season } })
  return res.data.data
}

export async function fetchValueLeaderboard(season = 2026): Promise<ValueLeaderboardEntry[]> {
  const res = await http.get<ApiResponse<ValueLeaderboardEntry[]>>('/standings/value', { params: { season } })
  return res.data.data
}

export async function fetchProgression(season = 2026): Promise<ProgressionRound[]> {
  const res = await http.get<ApiResponse<ProgressionRound[]>>('/standings/progression', { params: { season } })
  return res.data.data
}

// ─── Validation ──────────────────────────────────────────────────────────────

export async function fetchValidation(): Promise<ScoreValidationEntry[]> {
  const res = await http.get<ApiResponse<ScoreValidationEntry[]>>('/validation/latest')
  return res.data.data
}

export async function runValidation(): Promise<unknown> {
  const res = await http.post<ApiResponse<unknown>>('/validation/run')
  return res.data.data
}

// ─── Live ────────────────────────────────────────────────────────────────────

export async function fetchLiveStatus(): Promise<{ is_live: boolean; session_type: string | null; session_key?: number }> {
  const res = await http.get<ApiResponse<{ is_live: boolean; session_type: string | null }>>('/live/status')
  return res.data.data
}

// ─── Phase 2: Intelligence Layer ─────────────────────────────────────────────

export async function fetchDriverForm(driverId: number): Promise<DriverForm> {
  const res = await http.get<ApiResponse<DriverForm>>(`/drivers/${driverId}/form`)
  return res.data.data
}

export async function fetchCircuitFit(circuitType: string): Promise<CircuitFitEntry[]> {
  const res = await http.get<ApiResponse<CircuitFitEntry[]>>('/drivers/circuit-fit', { params: { circuit_type: circuitType } })
  return res.data.data
}

export async function fetchUpcomingDifficulty(driverCodes: string[]): Promise<UpcomingRaceDifficulty[]> {
  const res = await http.get<ApiResponse<UpcomingRaceDifficulty[]>>('/races/upcoming-difficulty', {
    params: { drivers: driverCodes.join(',') },
  })
  return res.data.data
}

export async function fetchTeammateComparison(constructorId: number): Promise<TeammateComparison | null> {
  const res = await http.get<ApiResponse<TeammateComparison | null>>(`/constructors/${constructorId}/teammates`)
  return res.data.data
}

export async function fetchVsTeammate(driverId: number): Promise<TeammateComparison | null> {
  const res = await http.get<ApiResponse<TeammateComparison | null>>(`/drivers/${driverId}/vs-teammate`)
  return res.data.data
}

export async function fetchTransferPlan(driverCodes: string[], constructorCodes: string[]): Promise<TransferMove[]> {
  const res = await http.get<ApiResponse<TransferMove[]>>('/transfers/plan', {
    params: { drivers: driverCodes.join(','), constructors: constructorCodes.join(',') },
  })
  return res.data.data
}
