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
**Primary goal**: Help F1 fans win their fantasy leagues through data-driven team selection and chip strategy advice — while also serving regular F1 fans with championship standings and a title odds simulator
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
- **Optimizer**: PuLP (linear programming for team optimization)
- **HTTP client**: httpx (async)

### Database
- **Primary**: SQLite via SQLAlchemy — zero setup, runs locally out of the box

### Deployment
- Docker + docker-compose for local dev
- Production: self-hosted on a Raspberry Pi 5 (8GB) — FastAPI on port 8011 behind a Cloudflare Tunnel at https://f1.job-joseph.com, always-on with no cold starts
- README also documents deployment to Railway, Render, and Fly.io as managed-platform alternatives
- Scheduled maintenance uses two **systemd timers**: `f1-sync.service` + `f1-sync.timer` (Tuesday 00:30 UTC / 06:00 IST, `Persistent=true`) runs `backend/scripts/sync_results.py` to ingest new race results post-weekend and reverify the last 3 already-synced rounds for post-race FIA amendments; `check-sync-drift.service` + `check-sync-drift.timer` (daily) runs `backend/scripts/check_sync_drift.py --fix` as a faster safety net for a completed round still missing real data.

### Data Sources
- **Race data**: Ergast/Jolpica API (http://ergast.com/mrd/) — calendar, historical results, standings
- **All fantasy scoring is computed locally** using the rules engine in `backend/core/scoring.py`

> **Removed**: this project originally also polled the OpenF1 API (https://openf1.org) for a
> live, in-session fantasy points tracker (a WebSocket-driven "Live Race" page, formerly
> its own feature section here). OpenF1 moved real-time/live session data behind a paid
> subscription (OAuth2, ~€9.90/mo) — the free tier now only covers historical data — so the
> live tracker was removed rather than left permanently broken. Historical race data
> continues to come from Ergast/Jolpica only.

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
│   │       └── standings.py     # F1 WDC + WCC standings
│   ├── core/
│   │   ├── scoring.py           # ALL fantasy scoring logic lives here
│   │   ├── optimizer.py         # PuLP team optimizer
│   │   ├── chip_advisor.py      # Rule-based chip recommendations
│   │   ├── expected_points.py   # xP: rolling avg points with circuit weighting
│   │   └── config.py
│   ├── data/
│   │   ├── ergast_client.py
│   │   └── models.py
│   └── db/
│       └── database.py
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
│       │   ├── Standings.tsx        # WDC + WCC + Fantasy value leaderboard
│       │   └── ChipAdvisor.tsx
│       ├── components/
│       │   ├── DriverCard.tsx
│       │   ├── ConstructorCard.tsx
│       │   ├── TeamSummary.tsx
│       │   ├── PointsTable.tsx
│       │   ├── ChipRecommendation.tsx
│       │   ├── ValueRankings.tsx    # Points per $M table
│       │   ├── Navbar.tsx
│       │   └── BottomNav.tsx
│       ├── hooks/
│       │   ├── useTeam.ts
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

Projected points = `xP` score from `expected_points.py` (see Feature 4).

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

---

## Feature 3: Chip Advisor

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

## Feature 4: Expected Points (xP)

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

## Feature 5: Standings (WDC + WCC + Fantasy Value)

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
| GET | /api/standings/progression | Cumulative fantasy pts per driver per round (DB-sourced, all 24 rounds) |
| GET | /api/standings/value | Fantasy value leaderboard (xP per $M) |
| POST | /api/simulator/title-odds | Monte Carlo title-odds simulation (real WDC baseline) |
| GET | /api/sync/status | Post-race sync status (last_sync, rounds_in_db, next_round, status) |

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
2. Features: team optimizer, chip advisor, standings
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
- Never inline scoring math in route handlers

## Mobile Requirements (Phase 1 complete)

- Primary target: 390px wide screen (iPhone 14 baseline) — `xs` breakpoint in Tailwind
- Bottom navigation bar on mobile (5 tabs with SVG icons); full horizontal navbar on sm+ screens
- All tap targets minimum 44×44px; minimum 14px body font; no horizontal overflow
- `overflow-x-hidden` on root; `-webkit-tap-highlight-color: transparent`
- Team Builder: single-column cards, sticky footer with DRS pills + budget bar + optimize button
- Standings: chart in `overflow-x-auto` wrapper with `min-w-[480px]`, sticky first table column
- Chip Advisor: full-width on mobile (`md:grid-cols-2` collapses to 1 col), 52px minimum action button, prominent confidence badge

---

## Definition of Done

A first-time reviewer should be able to:
1. Run `docker-compose up` and have the app working in under 2 minutes
2. See a team builder with real driver names, prices, and a working optimizer
3. Get a chip recommendation with a plain-English reason
4. See WDC and WCC standings with a points progression chart
5. Read the README and understand the project in under 5 minutes

---

## Phase 2: Intelligence Layer API Spec

### Form vs Luck
- `GET /api/drivers/{id}/form` → `{ flag, actual_avg, xp_avg, delta, history: [{round, race_name, circuit_type, actual, xp}] }`
- `GET /api/drivers` → now includes `form_status`, `form_delta`, `circuit_fit_score`, `circuit_fit_type`, `is_differential` per driver

### Circuit Intelligence
- `GET /api/drivers/circuit-fit?circuit_type=street|power|balanced` → `[{ driver_id, driver_code, driver_name, team_name, circuit_type, avg_points, races_counted, fit_score }]`
- `GET /api/races/upcoming-difficulty?drivers=VER,NOR&season=2025` → `[{ round, race_name, circuit_type, date, driver_fits: Record<code, score> }]`

### Teammate Comparison
- `GET /api/constructors/{id}/teammates` → `{ constructor_id, driver_1: TeammateStats, driver_2: TeammateStats, h2h_qualifying_races }`
- `GET /api/drivers/{id}/vs-teammate` → same shape

### Transfer Planner
- `GET /api/transfers/plan?drivers=VER,NOR&constructors=RBR&season=2025` → `[{ race, round, date, circuit_type, drop, add, budget_delta, chip_alternative, reasoning }]`
- `add` may be null if no valid replacement found within budget

All responses: `{ success: bool, data: any, error?: string }`

---

*Spec version: 2.2 | Project: f1-points-engine | Season: F1 2026*
