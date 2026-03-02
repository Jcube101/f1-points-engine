# F1 Points Engine

F1 Points Engine is an open-source fantasy F1 tool that helps you win your fantasy league through data-driven team selection, live race tracking, and chip strategy advice. It implements the full F1 Fantasy scoring ruleset locally (qualifying, sprint, grand prix, all bonuses and chip effects), computes Expected Points (xP) per driver using a rolling weighted average with circuit-type multipliers, and uses linear programming to optimise your team within the $100M budget cap — no spreadsheets, no guesswork.

---

## Features

| Feature | What it does |
|---|---|
| **Team Optimizer** | Picks the mathematically best 5-driver + 2-constructor team within budget using PuLP ILP (Max Points) or a greedy value ranker (Best Value) |
| **Live Race Tracker** | Streams real-time fantasy points from OpenF1 every 30 seconds via WebSocket — shows your team highlighted, fastest lap, positions gained. Tap any row for full breakdown |
| **Chip Advisor** | Rule-based recommendations (street circuit → No Negative, banked transfers → Wildcard) with confidence rating and plain-English reason |
| **Standings** | F1 WDC + WCC standings (2025 + 2026 season toggle) with a scrollable points progression chart, plus a fantasy value leaderboard ranked by xP per $M |
| **Score Validator** | Cross-checks our computed scores against the official F1 Fantasy API after each race and shows any discrepancies |
| **Mobile-first UI** | Designed for 390px screens (iPhone 14 baseline) — bottom navigation bar, sticky budget tracker, swipeable DRS pills, expandable live rows, and horizontally scrollable charts |

---

## Screenshot

> _Screenshot placeholder — add a screenshot of the Dashboard here after first run_
>
> ![F1 Points Engine Dashboard](docs/screenshot-placeholder.png)

---

## Quickstart (Docker)

The fastest way to get running — one command, no setup:

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

# 2. Seed the database (runs once — populates drivers, races, and initial fantasy points)
python backend/seed.py

# 3. Start the API server
uvicorn backend.main:app --reload --port 8000
```

API docs available at **http://localhost:8000/docs**

### Frontend

**Requirements**: Node.js 18+

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** — the Vite dev server proxies `/api` and `/ws` to port 8000.

---

## Environment Variables

Copy `.env.example` to `.env` and edit as needed:

```bash
cp .env.example .env
```

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./f1_engine.db` | SQLite path (swap for Postgres URL in production) |
| `PORT` | `8000` | Backend HTTP port (Railway sets this automatically) |
| `VITE_API_URL` | `http://localhost:8000` | Backend URL used by the frontend build |

See `.env.example` for the full list.

---

## How Scoring Works

All fantasy scoring is computed locally by `backend/core/scoring.py` — a set of pure functions with no side effects, fully documented:

- **Qualifying**: P1=10 pts down to P10=1 pt, DNF/DSQ/NC = −5, bonuses for positions gained and overtakes
- **Sprint**: P1=8 pts down to P8=1 pt, DNF = −10
- **Race**: P1=25 pts, standard F1 table, −20 for DNF, +10 fastest lap, +10 Driver of the Day
- **Constructors**: sum of both drivers + Q2/Q3 bonus + pit stop bonuses
- **Chips**: DRS Boost (×2), Extra DRS (×3), No Negative (floor to 0), Autopilot (auto-apply ×2 to top scorer)

**Expected Points (xP)** — `backend/core/expected_points.py`:
```
xP = weighted_avg(last_3_race_pts) × circuit_type_multiplier × teammate_gap_factor
```
Weights: most recent race 50%, previous 30%, oldest 20%. Circuit types: street, power, balanced.

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/drivers` | All drivers with price, xP, value score |
| GET | `/api/constructors` | All constructors |
| GET | `/api/races` | Season race calendar |
| POST | `/api/team/optimize` | Returns max-points + best-value teams |
| POST | `/api/points/calculate` | Fantasy points for a custom team + race |
| GET | `/api/points/leaderboard` | Driver value rankings (xP per $M) |
| POST | `/api/chips/recommend` | Chip strategy recommendation |
| GET | `/api/standings/wdc` | Drivers Championship standings |
| GET | `/api/standings/wcc` | Constructors Championship standings |
| GET | `/api/validation/latest` | Our scores vs official F1 Fantasy API |
| WS | `/ws/live` | Real-time race fantasy point updates |

Full interactive docs: **http://localhost:8000/docs**

---

## Deploy to Railway

F1 Points Engine deploys as a **single Railway service** — the backend serves both the API and the pre-built React frontend.

### Steps

1. **Fork** this repository on GitHub
2. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo** → select your fork
3. Railway auto-detects the `railway.toml` and runs `build.sh` on deploy
4. Once deployed, click the generated URL — the full app is live

### What happens at deploy time

```
build.sh runs:
  1. cd frontend && npm install && npm run build   # builds React → frontend/dist/
  2. python backend/seed.py                         # seeds DB on first boot
  3. uvicorn backend.main:app --host 0.0.0.0 --port $PORT  # starts server
```

The FastAPI backend serves the React app as static files from `/` and the API from `/api/*`.

### Environment variables on Railway

Set these in your Railway service's **Variables** tab if needed:

| Variable | Notes |
|---|---|
| `DATABASE_URL` | Leave blank to use SQLite (fine for personal use). Set a Postgres URL for persistence across deploys. |
| `PORT` | Set automatically by Railway — do not override. |

> Railway gives each deploy a fresh filesystem, so SQLite data resets on each deploy. For persistent data, attach a Railway Postgres plugin and set `DATABASE_URL`.

---

## Project Structure

```
f1-points-engine/
├── backend/
│   ├── main.py              # FastAPI app + WebSocket
│   ├── seed.py              # One-time DB seeder
│   ├── requirements.txt
│   ├── core/
│   │   ├── scoring.py       # All fantasy scoring logic (pure functions)
│   │   ├── optimizer.py     # PuLP team optimizer
│   │   ├── chip_advisor.py  # Chip recommendations
│   │   └── expected_points.py
│   ├── data/
│   │   ├── openf1_client.py
│   │   ├── ergast_client.py
│   │   └── fantasy_validator.py
│   └── api/routes/          # REST endpoints
├── frontend/
│   └── src/
│       ├── pages/           # Dashboard, TeamBuilder, LiveRace, Standings, ...
│       ├── components/      # DriverCard, TeamSummary, LiveTicker, BottomNav, ...
│       └── hooks/           # useTeam (Zustand), useLiveRace (WebSocket), useOptimizer
├── railway.toml             # Railway deployment config
├── build.sh                 # Railway build + start script
└── docker-compose.yml       # Local dev
```

---

## Mobile Experience

The app is optimised for use during race weekends on your phone (390px iPhone 14 baseline):

- **Bottom navigation bar** on mobile (Home · Team · Live · Standings · Chips); full top navbar on desktop
- **Team Builder**: cards stack single-column; sticky footer shows DRS pills + budget + Optimize button
- **Live Race**: sticky session/lap progress bar; tap any row to expand full points breakdown; accessible delta indicators (▲/▼ + colour)
- **Standings**: championship chart is horizontally scrollable; tables have sticky first column; top-5 default with "Show all" toggle
- **Chip Advisor**: full-width recommendation card, prominent confidence badge, 52px minimum action button

All tap targets are ≥44px. No horizontal overflow. Font minimum 14px.

---

## Roadmap

See [ROADMAP.md](ROADMAP.MD) for the full phased plan:

- **Phase 1** ✅ — Team optimizer, live race tracker, chip advisor, standings, score validator
- **Mobile UI** ✅ — Full mobile-first redesign: bottom nav, sticky footers, expandable rows
- **Phase 2** 🔜 — Circuit intelligence, differential finder, form vs luck detector, transfer planner
- **Phase 3** 🔮 — Championship simulator with Monte Carlo odds, scenario builder, season replay

---

## Contributing

PRs are welcome! For small fixes (typos, bug fixes, style tweaks) — go ahead and open a PR directly. For larger changes (new features, architectural changes, new data sources) — **please open an issue first** so we can discuss the approach before you invest the time.

### Development workflow

```bash
# Fork → clone → create a branch
git checkout -b feature/my-feature

# Make changes, run the app locally to verify
python backend/seed.py
uvicorn backend.main:app --reload --port 8000 &
cd frontend && npm run dev

# Commit + push + open PR against main
```

**Code style**: Python — follow existing patterns, add docstrings to any scoring/xP functions. TypeScript — no `any` types without a comment explaining why.

---

## License

MIT — see [LICENSE](LICENSE) for details. Use it, fork it, build on it.

```
MIT License

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
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
