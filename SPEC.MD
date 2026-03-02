# F1 Points Engine – Full Project Specification

> **Project name**: f1-points-engine
> **GitHub repo**: https://github.com/[your-username]/f1-points-engine
> This document is the single source of truth for building the F1 Points Engine.
> It is designed to be handed directly to Claude Code to build the full project.
> Every architectural decision has been pre-decided. Do not ask clarifying questions — build exactly what is described here.
> Refer to the phased roadmap at the bottom to understand what is in scope for Phase 1 vs later phases.

---

## Project Overview

**Name**: F1 Points Engine
**Type**: Open source web application
**Primary goal**: Help F1 fans win their fantasy leagues through data-driven team selection, live points tracking, and chip strategy advice — while also serving regular F1 fans with championship standings and a title odds simulator
**Target users**:
- F1 Fantasy players who want to win their leagues
- Regular F1 fans interested in championship standings and "what if" scenarios
**Open source style**: GitHub repository with a comprehensive README

---

## Tech Stack

### Frontend
- **Framework**: React (Vite)
- **Styling**: Tailwind CSS
- **Charts**: Recharts
- **State management**: React Query (server state) + Zustand (UI state)
- **Language**: TypeScript

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **Scheduler**: APScheduler (poll OpenF1 during race weekends)
- **Optimizer**: PuLP (linear programming for team optimization)
- **HTTP client**: httpx (async)

### Database
- **Primary**: SQLite via SQLAlchemy — zero setup, runs locally out of the box
- **Cache**: In-memory (Python dict) for live race data

### Deployment
- Docker + docker-compose for local dev
- README must document deployment to Railway, Render, and Fly.io

### Data Sources
- **Primary race data**: OpenF1 API (https://openf1.org) — free, no auth, real-time lap data
- **Historical/schedule data**: Ergast API (http://ergast.com/mrd/)
- **Fantasy score validation**: Unofficial F1 Fantasy API (https://fantasy.formula1.com/feeds/) — used only as a post-race validation layer to cross-check our computed scores against the official ones. Not used as primary source.
- **All fantasy scoring is computed locally** using the rules engine in `backend/core/scoring.py`

---

## Project Structure

```
f1-points-engine/
├── CLAUDE.md                    # Claude Code instructions (always read first)
├── README.md
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   ├── seed.py                  # Run once to populate DB with calendar + drivers
│   ├── api/
│   │   └── routes/
│   │       ├── drivers.py
│   │       ├── constructors.py
│   │       ├── races.py
│   │       ├── team.py
│   │       ├── points.py
│   │       ├── chips.py
│   │       ├── live.py
│   │       ├── standings.py     # F1 WDC + WCC standings
│   │       └── validation.py    # Cross-check vs official F1 Fantasy scores
│   ├── core/
│   │   ├── scoring.py           # ALL fantasy scoring logic lives here
│   │   ├── optimizer.py         # PuLP team optimizer
│   │   ├── chip_advisor.py      # Rule-based chip recommendations
│   │   ├── expected_points.py   # xP: rolling avg points with circuit weighting
│   │   └── config.py
│   ├── data/
│   │   ├── openf1_client.py
│   │   ├── ergast_client.py
│   │   ├── fantasy_validator.py # Fetches official scores for validation
│   │   └── models.py
│   ├── db/
│   │   └── database.py
│   └── scheduler/
│       └── live_poller.py       # Polls OpenF1 every 30s during race sessions
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── pages/
│       │   ├── Dashboard.tsx
│       │   ├── TeamBuilder.tsx
│       │   ├── LiveRace.tsx
│       │   ├── Standings.tsx        # WDC + WCC + Fantasy value leaderboard
│       │   ├── ChipAdvisor.tsx
│       │   └── ScoreValidator.tsx   # Shows our score vs official score diff
│       ├── components/
│       │   ├── DriverCard.tsx
│       │   ├── ConstructorCard.tsx
│       │   ├── TeamSummary.tsx
│       │   ├── PointsTable.tsx
│       │   ├── ChipRecommendation.tsx
│       │   ├── LiveTicker.tsx
│       │   ├── ValueRankings.tsx    # Points per $M table
│       │   └── Navbar.tsx
│       ├── hooks/
│       │   ├── useTeam.ts
│       │   ├── useLiveRace.ts
│       │   └── useOptimizer.ts
│       └── lib/
│           ├── api.ts
│           └── types.ts
```

---

## Feature 1: Team Builder + Optimizer

### Team rules
- Exactly 5 drivers + 2 constructors
- Total price ≤ $100,000,000
- Minimum price per asset: $3,000,000
- No duplicates

### Optimizer (`backend/core/optimizer.py`)
Use PuLP to solve two objectives, returned together from `POST /api/team/optimize`:

**Max Points Team**: Maximize projected fantasy points within $100M budget.
**Best Value Team**: Rank all assets by `xP_per_million = expected_points / price`, greedily select within budget.

Projected points = `xP` score from `expected_points.py` (see Feature 5).

### UI (TeamBuilder.tsx)
- Driver + constructor cards showing price, team, xP, value score — single column on mobile
- Manual pick or "Optimize" button (full-width sticky footer on mobile)
- Real-time budget tracker — sticky bar at bottom on mobile, always visible while scrolling
- Toggle between Max Points / Best Value modes
- DRS Boost selector — horizontally scrollable pill row (not a dropdown) on mobile
- Differential flag: highlight drivers with high xP but likely low ownership

---

## Feature 2: Fantasy Scoring Engine

### `backend/core/scoring.py` — implement as pure functions with docstrings

#### Qualifying (GP weekends)

| Position | Points |
|----------|--------|
| 1st | 10 |
| 2nd | 9 |
| 3rd | 8 |
| 4th | 7 |
| 5th | 6 |
| 6th | 5 |
| 7th | 4 |
| 8th | 3 |
| 9th | 2 |
| 10th | 1 |
| 11–20 | 0 |
| No time / DSQ / NC | –5 |

Bonuses: +1 per position gained vs grid, –1 per position lost, +1 per overtake, +5 fastest lap.
Constructors: sum of both drivers + Q2 bonus (+3 each) + Q3 bonus (+5 each).

#### Sprint Race

| Position | Points |
|----------|--------|
| 1st | 8 |
| 2nd | 7 |
| 3rd | 6 |
| 4th | 5 |
| 5th | 4 |
| 6th | 3 |
| 7th | 2 |
| 8th | 1 |
| 9–20 | 0 |
| DNF / DSQ / NC | –10 |

Bonuses: +1 per position gained, –1 per position lost, +1 per overtake. No fastest lap.

#### Grand Prix Race

| Position | Points |
|----------|--------|
| 1st | 25 |
| 2nd | 18 |
| 3rd | 15 |
| 4th | 12 |
| 5th | 10 |
| 6th | 8 |
| 7th | 6 |
| 8th | 4 |
| 9th | 2 |
| 10th | 1 |
| 11–20 | 0 |
| DNF / DSQ / NC | –20 |

Driver bonuses: +1 per position gained, –1 per position lost, +1 per overtake, +10 fastest lap, +10 Driver of the Day.
Constructor bonuses: fastest pit stop +5, sub-2.0s pit +20, new pit record +15 additional, –20 per DSQ driver.

#### Chips effect on scoring
- Regular DRS Boost: selected driver total × 2 (doubles negatives too)
- Extra DRS Boost: selected driver total × 3
- No Negative chip: any negative driver/constructor total is floored to 0
- Autopilot: system applies 2× to the highest-scoring driver post-race

### Scoring Validation (`backend/data/fantasy_validator.py`)
After each race weekend, fetch official fantasy scores from the F1 Fantasy API and compare them to our computed scores. Store the diff in a `ScoreValidation` table. Expose via `GET /api/validation/latest` so the frontend can show a "Score accuracy" panel. Target: 100% match. Any discrepancy triggers a logged warning with the driver, race, and delta.

---

## Feature 3: Live Race Points Tracker

### OpenF1 endpoints to use
- `GET https://api.openf1.org/v1/sessions` — current/upcoming session
- `GET https://api.openf1.org/v1/position` — lap-by-lap positions
- `GET https://api.openf1.org/v1/laps` — fastest lap tracking
- `GET https://api.openf1.org/v1/pit` — pit stop duration
- `GET https://api.openf1.org/v1/drivers` — driver metadata

### Polling (`backend/scheduler/live_poller.py`)
- Poll every 30 seconds during active race sessions
- No polling on non-race days
- Detect session type from OpenF1 → apply correct scoring rules automatically
- Push updates via WebSocket at `/ws/live`
- Graceful degradation: if OpenF1 is unavailable, return last known state, do not crash

### WebSocket message format
```json
{
  "session_type": "race | qualifying | sprint",
  "lap": 23,
  "total_laps": 57,
  "timestamp": "2026-03-08T14:32:00Z",
  "drivers": [
    {
      "driver_id": "VER",
      "name": "Max Verstappen",
      "position": 1,
      "fantasy_points": 31,
      "breakdown": {
        "race_position_points": 25,
        "positions_gained": 2,
        "overtakes": 3,
        "fastest_lap": false,
        "drs_boost_applied": false
      }
    }
  ],
  "constructors": []
}
```

### UI (LiveRace.tsx)
- Ranked table of all drivers + constructors with live fantasy points
- Mobile condensed view: driver code (3 letters) + position + fantasy points; tap row to expand full breakdown
- Highlight user's selected team (stored in localStorage)
- Session progress bar — sticky at top of screen (Lap X of Y, or Q1/Q2/Q3 indicator)
- Delta indicators: ▲/▼ + colour for accessibility (not colour alone)
- Auto-updates via WebSocket, no manual refresh needed

---

## Feature 4: Chip Advisor

### `backend/core/chip_advisor.py` — rule-based, priority ordered

| Condition | Recommended Chip | Confidence |
|-----------|-----------------|------------|
| Street circuit + historical DNF rate > 20% | No Negative | High |
| Wet weather forecast | No Negative | High |
| User has 3+ banked transfers | Wildcard | Medium |
| >4 races in + team value < $98M | Wildcard | Medium |
| High-value race (home GP for top driver) | Extra DRS Boost | Medium |
| >8 races in + Limitless unused | Limitless | Low |
| None of the above | Hold chips | — |

Response must include: recommended chip, confidence (Low/Medium/High), plain-English reason, list of alternatives with reasons.

`POST /api/chips/recommend` — body: `{ race_id, chips_remaining[], team_value, transfers_banked, races_completed }`

---

## Feature 5: Expected Points (xP)

### `backend/core/expected_points.py`

xP is the F1 equivalent of xG in FPL — it smooths out lucky/unlucky results to give a truer picture of a driver's expected fantasy points.

**Formula**:
```
xP = weighted_avg(last_3_race_points) × circuit_type_multiplier × teammate_gap_factor
```

- `weighted_avg`: most recent race weighted highest (0.5 / 0.3 / 0.2)
- `circuit_type_multiplier`: each circuit tagged as street / power / balanced. Apply per-driver historical performance multiplier on that circuit type
- `teammate_gap_factor`: if driver consistently outqualifies teammate, boost their qualifying xP slightly

xP is shown on every driver card and used as the optimizer's projected score. It replaces raw points averages everywhere in the UI.

---

## Feature 6: Standings (WDC + WCC + Fantasy Value)

### `backend/api/routes/standings.py`

Three standings tables, all on the Standings page:

**F1 Drivers Championship (WDC)**: Current season points, wins, podiums. Fetched from Ergast, updated post-race.

**F1 Constructors Championship (WCC)**: Team points, updated post-race.

**Fantasy Value Leaderboard**: All drivers + constructors ranked by `xP_per_million`. Columns: name, team, price, total fantasy points, xP, value score, price trend (↑↓ since last race).

This page is the entry point for non-fantasy F1 fans. It should be visually strong — use Recharts to show championship points progression over the season as a line chart.

---

## Database Models (`backend/data/models.py`)

```python
Driver: id, name, code, team_id, price, nationality, image_url
Constructor: id, name, code, color_hex, price
Race: id, name, circuit, country, date, session_type, round_number, season, circuit_type (street|power|balanced)
RaceResult: id, race_id, driver_id, constructor_id, qualifying_pos, race_pos, sprint_pos, dnf, dsq, fastest_lap, driver_of_day, pit_duration_ms, positions_gained_quali, positions_gained_race, overtakes, q2_reached, q3_reached
FantasyPoints: id, race_id, driver_id, qualifying_pts, sprint_pts, race_pts, total_pts, xp_score
ScoreValidation: id, race_id, driver_id, our_score, official_score, delta, validated_at
```

---

## API Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/drivers | All drivers with price, xP, value score |
| GET | /api/constructors | All constructors |
| GET | /api/races | 2026 race calendar |
| GET | /api/races/{id}/results | Results for a race |
| POST | /api/team/optimize | Returns max_points + best_value teams |
| POST | /api/points/calculate | Fantasy points for a given team + race |
| GET | /api/points/leaderboard | Driver + constructor value rankings |
| POST | /api/chips/recommend | Chip strategy recommendation |
| GET | /api/standings/wdc | Driver championship standings |
| GET | /api/standings/wcc | Constructor championship standings |
| GET | /api/validation/latest | Our score vs official score diff |
| GET | /api/live/status | Is a session currently live? |
| WS | /ws/live | WebSocket: live race point updates |

All responses: `{ success: bool, data: any, error?: string }`

---

## Seed Script (`backend/seed.py`)

On first run:
1. Fetch 2026 race calendar from Ergast → seed `races` table
2. Fetch driver + constructor list → seed with placeholder prices ($10–20M range)
3. Fetch 2025 season results → compute + store fantasy points as historical baseline
4. Compute initial xP scores for all drivers

Run with: `python backend/seed.py`

---

## CLAUDE.md Requirements

The repo must include a `CLAUDE.md` at root. See separate CLAUDE.md file.

---

## README Requirements

1. What this is (one paragraph)
2. Features: team optimizer, live tracker, chip advisor, standings, score validator
3. Screenshot placeholder
4. Quickstart: `docker-compose up` → open localhost:5173
5. Manual setup: backend + frontend separately
6. Environment variables (document .env.example)
7. How scoring works (link to scoring section)
8. Roadmap (link to ROADMAP.md)
9. Contributing: "PRs welcome. Open an issue first for large changes."
10. License: MIT

---

## Constraints for Claude Code

- No authentication — single-user local tool
- No DB migrations — SQLAlchemy `create_all()` on startup
- No Redux — Zustand only
- No CSS modules — Tailwind only
- All scoring logic in `backend/core/scoring.py` only
- Write docstrings on all scoring + xP functions
- Provide working seed data so app is usable immediately after setup
- WebSocket must degrade gracefully if OpenF1 is down
- Never inline scoring math in route handlers

## Mobile Requirements (Phase 1 complete)

- Primary target: 390px wide screen (iPhone 14 baseline) — `xs` breakpoint in Tailwind
- Bottom navigation bar on mobile (5 tabs with SVG icons); full horizontal navbar on sm+ screens
- All tap targets minimum 44×44px; minimum 14px body font; no horizontal overflow
- `overflow-x-hidden` on root; `-webkit-tap-highlight-color: transparent`
- Team Builder: single-column cards, sticky footer with DRS pills + budget bar + optimize button
- Live Race: sticky session progress bar, tap-to-expand rows, ▲/▼ delta text for accessibility
- Standings: chart in `overflow-x-auto` wrapper with `min-w-[480px]`, sticky first table column, top-5 with "Show all" toggle
- Chip Advisor: full-width on mobile (`md:grid-cols-2` collapses to 1 col), 52px minimum action button, prominent confidence badge

---

## Definition of Done

A first-time reviewer should be able to:
1. Run `docker-compose up` and have the app working in under 2 minutes
2. See a team builder with real driver names, prices, and a working optimizer
3. Click "Live Race" during a race weekend and see live fantasy points
4. Get a chip recommendation with a plain-English reason
5. See WDC and WCC standings with a points progression chart
6. See a score validation panel showing our accuracy vs the official game
7. Read the README and understand the project in under 5 minutes

---

*Spec version: 2.0 | Project: f1-points-engine | Season: F1 2026*
