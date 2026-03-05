# CLAUDE.md — F1 Points Engine

> This file is read by Claude Code at the start of every session.
> It contains everything you need to understand the project, run it, and contribute correctly.
> Always read this file fully before writing any code.

---

## What This Project Is

F1 Points Engine is an open source web app that helps F1 fans win their fantasy leagues and understand championship battles. It has three main audiences:

1. **Fantasy players** — team optimizer, live race points tracker, chip strategy advisor
2. **F1 fans** — WDC/WCC standings with a championship simulator (Phase 3)
3. **Developers** — clean, well-documented codebase designed to be learned from

---

## Current Phase

**Phase 1 + Phase 2 Intelligence Layer** are complete and stable. See `ROADMAP.MD` for what is in scope.
Do not build Phase 3 features unless explicitly instructed.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React + Vite + TypeScript + Tailwind CSS |
| State | React Query (server) + Zustand (UI) |
| Charts | Recharts |
| Backend | FastAPI (Python 3.11+) |
| Database | SQLite via SQLAlchemy |
| Optimizer | PuLP |
| Scheduler | APScheduler |
| HTTP client | httpx (async) |
| Real-time | WebSocket via FastAPI |
| Deployment | Railway (single service: FastAPI serves built React app) |

---

## How to Run the Project

### Docker (preferred)
```bash
docker-compose up
```
Frontend: http://localhost:5173
Backend API: http://localhost:8000
API docs: http://localhost:8000/docs

### Manual

**Backend**
```bash
cd backend
pip install -r requirements.txt
python seed.py          # Run once to populate DB
uvicorn main:app --reload --port 8000
```

**Frontend**
```bash
cd frontend
npm install
npm run dev
```

---

## Project Structure (key files)

```
backend/core/scoring.py          ← ALL fantasy scoring logic. Never put scoring math elsewhere.
backend/core/optimizer.py        ← PuLP team optimizer (max points + best value)
backend/core/chip_advisor.py     ← Rule-based chip recommendations
backend/core/expected_points.py  ← xP calculation (rolling avg + circuit weighting)
backend/core/config.py           ← CURRENT_SEASON, scoring tables, budget cap
backend/data/openf1_client.py    ← OpenF1 API wrapper (live race data)
backend/data/ergast_client.py    ← Ergast/Jolpica API wrapper (historical + calendar)
backend/data/fantasy_validator.py ← Cross-check scores vs official F1 Fantasy API
backend/scheduler/live_poller.py  ← Polls OpenF1 every 30s during race sessions
backend/seed.py                  ← One-time DB seeding: 2026 drivers/constructors,
                                    2025+2026 calendars, 2025 season results (generated),
                                    xP scores, circuit profiles. Run: python backend/seed.py
backend/api/routes/transfers.py  ← Phase 2: Transfer Planner endpoint
frontend/src/pages/              ← One file per page/route
frontend/src/components/         ← Reusable UI components (incl. BottomNav, LiveTicker,
                                    TeammateModal)
frontend/src/hooks/              ← useTeam (Zustand), useLiveRace (WS), useOptimizer
frontend/src/lib/types.ts        ← All shared TypeScript types defined here
frontend/src/lib/api.ts          ← All backend API calls (fetchDrivers, fetchWDC, etc.)
frontend/tailwind.config.ts      ← xs breakpoint (390px), scrollbar-none utility
```

---

## Coding Rules — Follow These Exactly

### General
- All API responses must follow: `{ success: bool, data: any, error?: string }`
- Never inline scoring math in route handlers — always call `scoring.py` functions
- All scoring and xP functions must have docstrings explaining inputs, outputs, and the rule being implemented
- SQLAlchemy `create_all()` on startup — no migration system needed
- No authentication required — this is a single-user local tool

### Python / Backend
- Python 3.11+
- Use `httpx` for all async HTTP calls (not `requests`)
- Use `async/await` throughout FastAPI routes
- Handle OpenF1 API downtime gracefully: return last known state, log warning, never crash
- `scoring.py` functions should be pure (no DB calls, no side effects)

### TypeScript / Frontend
- Use Zustand for UI state only (selected team, active chip, UI toggles)
- Use React Query for all server data fetching and caching
- Define all shared types in `frontend/src/lib/types.ts` — do not define inline types in components
- Use Tailwind utility classes only — no CSS modules, no styled-components
- No Redux
- Minimum tap target: 44×44px — use `min-h-[44px]` or larger on all interactive elements
- Use `xs:` breakpoint (390px) for iPhone 14 baseline; `sm:` (640px) for tablet/desktop split
- Use `scrollbar-none` utility class on horizontally scrollable containers
- `overflow-x-hidden` on root; no horizontal overflow on any page at 390px

### Mobile Layout Conventions
- **Navigation**: `BottomNav` (mobile, `sm:hidden`) + top `Navbar` (desktop, `hidden sm:block`)
- **Sticky elements**: bottom nav is `fixed bottom-0 h-14 z-50`; mobile content footers use `fixed bottom-14 z-40`
- **Main padding**: `pb-20 sm:pb-6` on `<main>` to clear the bottom nav
- **Single-column cards**: `grid grid-cols-1 sm:grid-cols-2` for driver/constructor cards
- **Chart scrolling**: wrap Recharts in `overflow-x-auto` > `min-w-[480px]` div

### Data & Seeding
- Seed script (`backend/seed.py`) seeds both seasons in one run — idempotent (safe to re-run)
- 2026 roster: 22 drivers across 11 constructors (includes Cadillac; Sauber renamed Audi)
  - Key assignments: Colapinto→Alpine, Perez/Bottas→Cadillac, Hulkenberg/Bortoleto→Audi, Lawson/Lindblad→Racing Bulls
  - `arvid_lindblad` (not ayumu) — Swedish, Racing Bulls
- 2025-only drivers (price=0, not on 2026 grid): `yuki_tsunoda` (TSU), `jack_doohan` (DOO) — seeded in DB to preserve 2025 race results
- 2025 results: deterministically generated with `random.Random(42)` — strength profiles in `DRIVER_STRENGTH_2025`
- Mid-season swap: `get_2025_constructor(code, round_num)` in seed.py handles LAW/TSU — LAW at Red Bull rounds 1–2, TSU at Red Bull rounds 3–24
- Driver prices should match official 2026 F1 Fantasy opening prices (see `DRIVER_PRICES` in seed.py)
- Season is controlled by `CURRENT_SEASON` in `backend/core/config.py` (currently 2026)
- API endpoints that return season-specific data accept `?season=` query param (default: CURRENT_SEASON)

---

## Data Sources

| Source | Used For | Auth |
|--------|----------|------|
| OpenF1 API (openf1.org) | Live race data: positions, laps, pit stops | None required |
| Ergast API (ergast.com/mrd) | Calendar, historical results, standings | None required |
| F1 Fantasy API (fantasy.formula1.com) | Post-race score validation only | None required (public feeds) |

**Important**: The F1 Fantasy API is unofficial and undocumented. Use it only in `fantasy_validator.py` for post-race validation. Never use it as a primary data source.

---

## Fantasy Scoring Quick Reference

See `SPEC.md` for full scoring tables. Key rules:

- GP qualifying: P1=10pts down to P10=1pt. No time/DSQ = –5
- Sprint: P1=8pts down to P8=1pt. DNF = –10
- Race: P1=25pts standard F1 scale. DNF = –20
- All sessions: +1 per position gained, –1 per position lost, +1 per overtake
- Race only: +10 fastest lap, +10 Driver of the Day
- Constructor pit bonuses: fastest pit +5, sub-2s +20, new record +15 extra
- DRS Boost: 2× driver total (doubles negatives). Extra DRS: 3×
- No Negative chip: floor all negatives to 0

---

## Expected Points (xP) — Key Concept

xP replaces raw points averages everywhere. It is the F1 equivalent of xG in FPL.

```
xP = weighted_avg(last_3_races) × circuit_type_multiplier × teammate_gap_factor
```

- Last 3 races weighted: 50% most recent, 30% previous, 20% oldest
- Circuit types: street / power / balanced — each driver has a historical multiplier per type
- Teammate gap: if driver consistently outqualifies teammate, slight qualifying xP boost

xP is shown on driver cards and used as the optimizer's projected score input.

---

## WebSocket Behaviour

- Endpoint: `ws://localhost:8000/ws/live`
- Active only during race sessions (qualifying, sprint, race)
- Pushes updates every 30 seconds with full driver/constructor fantasy points breakdown
- If OpenF1 is unreachable: push last known state with `"stale": true` flag
- Session type is auto-detected from OpenF1 session data

---

## Score Validation

After each race weekend:
1. `fantasy_validator.py` fetches official scores from F1 Fantasy API
2. Compares to our computed scores from `scoring.py`
3. Stores diff in `ScoreValidation` table
4. `GET /api/validation/latest` exposes this for the frontend
5. Any discrepancy > 0 points logs a warning with driver, race, and delta

Target: 100% match with official scores. Discrepancies reveal scoring rule bugs.

---

## Adding New Features

1. Check `ROADMAP.md` — is it in Phase 2 or later? Don't build ahead of schedule.
2. Add backend route in `backend/api/routes/`, register in `backend/main.py`
3. Add TypeScript types in `frontend/src/lib/types.ts`
4. Add API call in `frontend/src/lib/api.ts`
5. Build page or component — ensure it works at 390px (mobile-first)
6. Test: does the seed data make it work end-to-end?

## Deployment

### Railway (production)
`railway.toml` + root `Dockerfile` — single service. FastAPI serves the built React app
as static files (`frontend/dist/`) from `/`, API from `/api/*`, WebSocket at `/ws/live`.

```bash
# Simulate Railway build locally:
./build.sh
```

### Docker (local dev)
```bash
docker-compose up   # frontend :5173, backend :8000
```

The `STATIC_DIR` check in `backend/main.py` switches between dev mode (API only) and
production mode (serves React SPA) automatically.

---

## Common Tasks

**Re-seed the database (fresh start)**
```bash
rm -f f1_engine.db
python backend/seed.py
```

**Start backend (dev)**
```bash
uvicorn backend.main:app --reload --port 8000
```

**Start frontend (dev)**
```bash
cd frontend && npm run dev
```

**Build frontend (production)**
```bash
cd frontend && npm run build   # output → frontend/dist/
```

**Check API docs**
Visit http://localhost:8000/docs (FastAPI auto-generates this)

**Verify key endpoints after seeding**
```bash
curl http://localhost:8000/api/drivers | python3 -c "import json,sys; d=json.load(sys.stdin)['data']; print(len(d), 'drivers')"
curl "http://localhost:8000/api/races?season=2025" | python3 -c "import json,sys; d=json.load(sys.stdin)['data']; print(len(d), 'races')"
curl "http://localhost:8000/api/standings/value?season=2025" | python3 -c "import json,sys; d=json.load(sys.stdin)['data']; print(d[0]['code'], d[0]['xp'])"
curl "http://localhost:8000/api/standings/progression?season=2025" | python3 -c "import json,sys; d=json.load(sys.stdin)['data']; print(len(d), 'rounds,', len([k for k in d[-1] if k not in ('round','round_name')]), 'drivers in final round')"
curl "http://localhost:8000/api/drivers/circuit-fit?circuit_type=street" | python3 -c "import json,sys; d=json.load(sys.stdin)['data']; print(d[0]['driver_code'], d[0]['fit_score'])"
curl "http://localhost:8000/api/drivers/1/form" | python3 -c "import json,sys; d=json.load(sys.stdin)['data']; print(d['flag'], d['delta'])"
curl "http://localhost:8000/api/constructors/1/teammates" | python3 -c "import json,sys; d=json.load(sys.stdin)['data']; print(d['driver_1']['code'], 'vs', d['driver_2']['code'])"
curl "http://localhost:8000/api/transfers/plan?drivers=VER,NOR" | python3 -c "import json,sys; d=json.load(sys.stdin)['data']; print(len(d), 'transfer moves')"
```

**Manually trigger score validation**
```bash
curl -X POST http://localhost:8000/api/validation/run
```

**Run backend tests**
```bash
cd backend && pytest
```

---

## Phase 2 Intelligence Layer — Key Concepts

### Form vs Luck Detector
- `GET /api/drivers/{id}/form` — last 5 races with per-race xP (computed from 3 preceding races)
- `_form_flag(actual_avg, xp)`: ratio > 1.2 → overperforming, < 0.8 → underperforming, else on_form
- Frontend: 🔴 Sell signal badge (overperforming), 🟢 Buy signal badge (underperforming) on DriverCard
- Tap-to-expand sparkline (Recharts AreaChart) — lazy-fetched with `enabled: expanded`

### Circuit Intelligence
- `DriverCircuitProfile` table: driver × circuit_type (street/power/balanced) → avg_points, races_counted
- Seeded by `seed_circuit_profiles(db)` — idempotent delete-and-rebuild
- `GET /api/drivers/circuit-fit?circuit_type=` — ranked by avg_points, normalised 0–10 fit_score
- `GET /api/races/upcoming-difficulty?drivers=&season=` — next 5 races with per-driver fit scores
- Frontend: circuit fit badge on DriverCard; "Fixture View" tab on Standings page (colour-coded tiles)

### Differential Finder
- Threshold: top-30% xP percentile AND price < $12M → `is_differential = true`
- ⚡ badge on DriverCard, "Show Differentials Only" toggle in TeamBuilder

### Teammate Comparison
- `GET /api/constructors/{id}/teammates` — H2H stats for both drivers in a team
- `GET /api/drivers/{id}/vs-teammate` — same from driver perspective
- Frontend: "Compare Teammates" button on ConstructorCard → TeammateModal (bottom-sheet on mobile)
- TeammateModal: side-by-side stat table with winner highlighted green + Recharts BarChart

### Transfer Planner
- `GET /api/transfers/plan?drivers=&constructors=&season=` — 3-race plan
- Weakest driver by circuit xP → best in-budget replacement (≥15% better, ±$500K flex)
- Chip suggestion if ≥2 underperformers
- Frontend: collapsible "Transfer Planner" section in TeamBuilder (lazy-fetched when opened)

---

*CLAUDE.md version: 1.3 | Project: f1-points-engine | Season: F1 2026*
