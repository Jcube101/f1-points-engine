# F1 Points Engine

F1 Points Engine is an open-source fantasy F1 tool that helps you win your fantasy league through data-driven team selection, live race tracking, and chip strategy advice. It implements the full F1 Fantasy scoring ruleset locally, computes Expected Points (xP) per driver using a rolling weighted average with circuit-type multipliers, runs linear programming to optimise your team within the $100M budget cap — and now includes a full Phase 2 Intelligence Layer with circuit fit scores, form analysis, differential picks, teammate comparison, and a 3-race transfer planner.

---

## Features

### Phase 1 — Core Fantasy Tool ✅

| Feature | What it does |
|---|---|
| **Team Optimizer** | Picks the mathematically best 5-driver + 2-constructor team within budget using PuLP ILP (Max Points mode) or value-weighted greedy (Best Value mode) |
| **Live Race Tracker** | Streams real-time fantasy points from OpenF1 every 30 seconds via WebSocket — your team highlighted, fastest lap indicator, positions gained. Tap any row for full points breakdown |
| **Chip Advisor** | Rule-based chip recommendations (street circuit → No Negative, banked transfers → Wildcard) with confidence rating and plain-English explanation |
| **Standings** | F1 WDC + WCC standings with 2025/2026 season toggle; scrollable fantasy points progression chart; fantasy value leaderboard ranked by xP per $M |
| **Score Validator** | Cross-checks our computed scores against the official F1 Fantasy API after each race and reports any discrepancies |
| **Expected Points (xP)** | Rolling weighted average (50/30/20%) × circuit-type multiplier × teammate gap factor — shown on every driver card and used by the optimizer |

### Phase 2 — Intelligence Layer ✅

| Feature | What it does |
|---|---|
| **Form vs Luck Detector** | Compares actual fantasy points vs xP over the last 5 races. 🔴 Sell signal (overperforming, regression risk) or 🟢 Buy signal (underperforming, bounce-back candidate). Expandable sparkline on each driver card showing actual vs xP trend |
| **Circuit Intelligence** | Per-driver performance history by circuit type (street / power / balanced). Circuit fit score (0–10) badge on every driver card. Fixture View tab on Standings shows the next 5 races colour-coded green/amber/red by fit |
| **Differential Finder** | Flags drivers in the top 30% xP but priced under $12M with a ⚡ badge. "Show Differentials Only" toggle in Team Builder to find low-ownership picks |
| **Teammate Comparison** | Head-to-head qualifying and fantasy stats for both drivers in a constructor. "Compare Teammates" button on every constructor card opens a modal with a stat table and bar chart |
| **Transfer Planner** | Plans transfers 3 races ahead — identifies the weakest driver for each upcoming circuit type, suggests the best in-budget replacement, flags if a chip is a better call. Collapsible section in Team Builder |

### Phase 3 — Championship Simulator & Help ✅

| Feature | What it does |
|---|---|
| **Race Calendar Fix** | 2026 calendar corrected to local venue race-day dates (23 rounds, no Emilia Romagna). Sprint weekends re-tagged: Miami, Canada, Britain, Netherlands, Singapore. `seed_races()` now updates existing rows, not just inserts |
| **Title Race — Live Standings** | Championship Standings section with WDC points bar chart (top 10, team-coloured). Auto-updates via OpenF1 API |
| **Title Race — Monte Carlo Simulator** | `POST /api/simulator/title-odds` runs 10,000 simulations of remaining season using each driver's last 5 race results weighted by recency (50/30/20%). Results cached 1 hour. Frontend shows horizontal win-probability bars + plain-English scenario summary |
| **Pace Sliders** | Interactive 0.5×–1.5× pace multipliers for top 5 drivers. Debounced (350ms) re-simulation for instant "what-if" exploration |
| **Help Page** | Accordion FAQ with 6 sections: Getting Started, Scoring Rules, Chips & Strategy, Team Optimizer, Intelligence Features, Title Race Calculator. Smooth CSS transitions, mobile-friendly |

### Mobile-First UI ✅

- 390px iPhone 14 baseline — bottom navigation bar, sticky budget tracker, swipeable DRS pills
- All tap targets ≥44px, no horizontal overflow, minimum 14px body font
- TeammateModal opens as a bottom sheet on mobile, centred dialog on desktop
- Fixture View and sparklines scroll horizontally on narrow screens

---

## Screenshot

> _Screenshot placeholder — add a screenshot of the Dashboard after first run_
>
> ![F1 Points Engine Dashboard](docs/screenshot-placeholder.png)

---

## Quickstart (Docker)

```bash
git clone https://github.com/Jcube101/f1-points-engine.git
cd f1-points-engine
docker-compose up
```

Open **http://localhost:5173** — the seed script runs automatically on first boot.

> **Requirements**: Docker Desktop (or Docker Engine + Compose v2). No Python or Node needed locally.

---

## Manual Setup

### Backend

**Requirements**: Python 3.11+

```bash
# 1. Install dependencies
pip install -r backend/requirements.txt

# 2. Seed the database
#    Populates all 2026 drivers/constructors, 2025+2026 calendars,
#    2025 race results, xP scores, and circuit profiles
python backend/seed.py

# 3. Start the API server
uvicorn backend.main:app --reload --port 8000
```

API docs: **http://localhost:8000/docs**

### Frontend

**Requirements**: Node.js 18+

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** — Vite proxies `/api` and `/ws` to port 8000.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./f1_engine.db` | SQLite path — swap for Postgres URL in production |
| `PORT` | `8000` | Backend HTTP port (Railway sets this automatically) |
| `VITE_API_URL` | `http://localhost:8000` | Backend URL used by the frontend build |

---

## How Scoring Works

All fantasy scoring lives in `backend/core/scoring.py` — pure functions with full docstrings:

| Session | Key rules |
|---|---|
| **Qualifying** | P1=10 pts → P10=1 pt. No time/DSQ/NC = −5. +1/position gained, +1/overtake, +5 fastest lap |
| **Sprint** | P1=8 pts → P8=1 pt. DNF = −10. +1/position gained, +1/overtake |
| **Race** | P1=25 pts (standard F1 scale). DNF = −20. +1/position gained, +1/overtake, +10 fastest lap, +10 Driver of the Day |
| **Constructor** | Sum of both drivers + Q2 bonus (+3 each) + Q3 bonus (+5 each) + fastest pit (+5) + sub-2s pit (+20) + new record (+15) − DSQ (−20/driver) |
| **DRS Boost** | Selected driver ×2 (doubles negatives). Extra DRS: ×3 |
| **No Negative** | Floor all driver/constructor totals to 0 |
| **Autopilot** | System applies ×2 to the highest-scoring driver post-race |

**Expected Points (xP)**:
```
xP = weighted_avg(last_3_races) × circuit_type_multiplier × teammate_gap_factor
```
Weights: 50% most recent, 30% previous, 20% oldest. Circuit types: `street` / `power` / `balanced`.

---

## API Reference

### Core

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/drivers` | All drivers with price, xP, value score, and Phase 2 fields (`form_status`, `circuit_fit_score`, `is_differential`) |
| GET | `/api/constructors` | All constructors with driver list |
| GET | `/api/races?season=` | Race calendar for a season |
| GET | `/api/races/{id}/results` | All results for a specific race |
| POST | `/api/team/optimize` | Max-points + best-value team within budget |
| POST | `/api/points/calculate` | Fantasy points for a custom team + race |
| GET | `/api/points/leaderboard` | Driver value rankings (xP per $M) |
| POST | `/api/chips/recommend` | Chip strategy recommendation with confidence |
| GET | `/api/standings/wdc?season=` | Drivers Championship |
| GET | `/api/standings/wcc?season=` | Constructors Championship |
| GET | `/api/standings/value?season=` | Fantasy value leaderboard |
| GET | `/api/standings/progression?season=` | Cumulative fantasy points per driver per round |
| GET | `/api/validation/latest` | Our scores vs official F1 Fantasy API |
| WS | `/ws/live` | Real-time race fantasy point updates (every 30s) |

### Phase 2 — Intelligence Layer

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/drivers/{id}/form` | Last 5 races: actual pts vs xP, flag (overperforming / underperforming / on_form), delta, sparkline history |
| GET | `/api/drivers/circuit-fit?circuit_type=` | Drivers ranked by circuit fit score (0–10) for `street`, `power`, or `balanced` |
| GET | `/api/drivers/{id}/vs-teammate` | Head-to-head stats vs the driver's teammate |
| GET | `/api/constructors/{id}/teammates` | Full H2H breakdown for both drivers in a constructor |
| GET | `/api/races/upcoming-difficulty?drivers=&season=` | Next 5 races with per-driver circuit fit tiles |
| GET | `/api/transfers/plan?drivers=&constructors=` | 3-race transfer plan: drop, add, budget delta, chip suggestion, reasoning |

### Phase 3 — Title Race Simulator

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/simulator/title-odds` | Run 10,000 Monte Carlo simulations of remaining season; body: `{ season, simulations, pace_multipliers }` |

All responses use `{ "success": true, "data": ... }` envelope.

Full interactive docs: **http://localhost:8000/docs**

---

## Database Schema

Tables created automatically by SQLAlchemy `create_all()` on startup:

| Table | Description |
|---|---|
| `constructors` | 11 teams (2026 grid, including Cadillac and Audi) |
| `drivers` | 24 drivers (22 active + TSU + DOO retained for 2025 history, `price=0`) |
| `races` | 47 races (24 rounds 2025 + 23 rounds 2026, corrected local-venue dates) |
| `race_results` | Qualifying pos, race pos, sprint pos, DNF/DSQ/fastest lap per driver per race |
| `fantasy_points` | Computed fantasy point totals per driver per race |
| `driver_circuit_profiles` | Per-driver average pts by circuit type (street / power / balanced) — 60 rows |
| `score_validations` | Our computed scores vs official F1 Fantasy API |

Seed counts after `python backend/seed.py`:
```
constructors:           11
drivers:                24   (22 active + 2 retired/2025-only)
races:                  47   (24 in 2025 + 23 in 2026)
race_results:          576
fantasy_points:        576
driver_circuit_profiles: 60
```

---

## Project Structure

```
f1-points-engine/
├── backend/
│   ├── main.py                    # FastAPI app, WebSocket, static file serving
│   ├── seed.py                    # DB seeder — idempotent, safe to re-run
│   ├── requirements.txt
│   ├── core/
│   │   ├── scoring.py             # All fantasy scoring logic (pure functions)
│   │   ├── optimizer.py           # PuLP ILP team optimizer
│   │   ├── chip_advisor.py        # Rule-based chip recommendations
│   │   ├── expected_points.py     # xP calculation + circuit multipliers
│   │   └── config.py              # CURRENT_SEASON, scoring tables, budget cap
│   ├── data/
│   │   ├── models.py              # SQLAlchemy ORM models (all DB tables)
│   │   ├── openf1_client.py       # Live race data (OpenF1 API)
│   │   ├── ergast_client.py       # Calendar + historical results (Ergast/Jolpica)
│   │   └── fantasy_validator.py   # Post-race score validation
│   ├── api/routes/
│   │   ├── drivers.py             # /api/drivers — includes Phase 2 form + circuit fit
│   │   ├── constructors.py        # /api/constructors + teammate comparison
│   │   ├── races.py               # /api/races + upcoming difficulty
│   │   ├── transfers.py           # /api/transfers/plan (Phase 2)
│   │   ├── standings.py           # WDC, WCC, value, progression
│   │   ├── team.py                # /api/team/optimize
│   │   ├── chips.py               # /api/chips/recommend
│   │   ├── points.py              # /api/points/calculate + leaderboard
│   │   ├── simulator.py           # /api/simulator/title-odds (Phase 3)
│   │   └── validation.py          # /api/validation
│   ├── db/
│   │   └── database.py            # SQLAlchemy engine + session + init_db()
│   ├── scheduler/
│   │   └── live_poller.py         # APScheduler: polls OpenF1 every 30s
│   └── tests/                     # Pytest test suite (175 tests)
│       ├── conftest.py            # In-memory test DB + seeded fixtures
│       ├── test_scoring.py        # Unit tests — scoring.py (44 tests)
│       ├── test_expected_points.py # Unit tests — expected_points.py (22 tests)
│       ├── test_api_drivers.py    # Integration tests — driver endpoints
│       ├── test_api_constructors.py
│       ├── test_api_races.py
│       ├── test_api_standings.py
│       ├── test_api_team.py
│       ├── test_api_chips.py
│       └── test_api_transfers.py
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── Dashboard.tsx
│       │   ├── TeamBuilder.tsx    # Differentials toggle, Transfer Planner
│       │   ├── LiveRace.tsx
│       │   ├── Standings.tsx      # Fixture View tab (Phase 2)
│       │   ├── TitleRace.tsx      # Monte Carlo simulator + standings (Phase 3)
│       │   ├── Help.tsx           # Accordion FAQ (Phase 3)
│       │   └── ChipAdvisor.tsx
│       ├── components/
│       │   ├── DriverCard.tsx     # Form badges, circuit fit, ⚡ differential, sparkline
│       │   ├── ConstructorCard.tsx # Compare Teammates button
│       │   ├── TeammateModal.tsx  # Bottom-sheet comparison modal (Phase 2)
│       │   ├── TeamSummary.tsx
│       │   ├── BottomNav.tsx
│       │   └── LiveTicker.tsx
│       ├── hooks/
│       │   ├── useTeam.ts         # Zustand — selected drivers/constructors
│       │   ├── useLiveRace.ts     # WebSocket live points
│       │   └── useOptimizer.ts    # Team optimizer call
│       └── lib/
│           ├── types.ts           # All shared TypeScript interfaces
│           └── api.ts             # All backend API calls
├── TEST_PLAN.MD                   # 9-step validation guide
├── LEARNINGS.MD                   # 26 development learnings
├── ROADMAP.MD                     # Phased feature roadmap
├── SPEC.MD                        # Full project specification
├── CLAUDE.MD                      # Claude Code context file
├── railway.toml                   # Railway deployment config
├── build.sh                       # Railway build + start script
└── docker-compose.yml             # Local dev
```

---

## Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run the full suite
python -m pytest backend/tests/ -v

# Run a single file
python -m pytest backend/tests/test_scoring.py -v
```

**175 tests, 0 failures.** See [TEST_PLAN.MD](TEST_PLAN.MD) for the complete validation guide including manual smoke tests and a data integrity checklist.

---

## Deploy to Railway

F1 Points Engine deploys as a **single Railway service** — FastAPI serves both the API and the pre-built React frontend.

1. **Fork** this repository on GitHub
2. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo** → select your fork
3. Railway auto-detects `railway.toml` and runs `build.sh` on deploy
4. Click the generated URL — the full app is live

```
build.sh:
  1. cd frontend && npm install && npm run build   # React → frontend/dist/
  2. python backend/seed.py                         # seeds DB on first boot
  3. uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

| Railway variable | Notes |
|---|---|
| `DATABASE_URL` | Leave blank for SQLite (resets each deploy). Set a Postgres URL for persistence. |
| `PORT` | Set automatically — do not override. |

---

## Roadmap

See [ROADMAP.MD](ROADMAP.MD) for the full phased plan.

- **Phase 1** ✅ — Team optimizer, live race tracker, chip advisor, standings, score validator, xP engine
- **Phase 2** ✅ — Circuit intelligence, differential finder, form vs luck detector, teammate comparison, transfer planner
- **Phase 3** ✅ — Calendar date fixes, Monte Carlo title odds simulator with pace sliders, Help FAQ page

---

## Contributing

PRs are welcome. For small fixes — open a PR directly. For new features or architectural changes — open an issue first.

```bash
git checkout -b feature/my-feature

# Verify everything works
python backend/seed.py
python -m pytest backend/tests/ -q
cd frontend && npm run build

# Push + open PR against main
```

**Code style:** Python — add docstrings to any scoring/xP functions. TypeScript — no `any` without a comment. All API responses must use `{ success, data }` envelope.

---

## License

MIT — see [LICENSE](LICENSE).

```
Copyright (c) 2025 F1 Points Engine contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
```
