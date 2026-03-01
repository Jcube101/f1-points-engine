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

**Phase 1** is the active build. See `ROADMAP.md` for what is in scope.
Do not build Phase 2 or Phase 3 features unless explicitly instructed.

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
backend/core/scoring.py        ← ALL fantasy scoring logic. Never put scoring math elsewhere.
backend/core/optimizer.py      ← PuLP team optimizer (max points + best value)
backend/core/chip_advisor.py   ← Rule-based chip recommendations
backend/core/expected_points.py ← xP calculation (rolling avg + circuit weighting)
backend/data/openf1_client.py  ← OpenF1 API wrapper
backend/data/ergast_client.py  ← Ergast API wrapper
backend/data/fantasy_validator.py ← Cross-check scores vs official F1 Fantasy API
backend/scheduler/live_poller.py  ← Polls OpenF1 every 30s during race sessions
backend/seed.py                ← One-time DB seeding script
frontend/src/pages/            ← One file per page/route
frontend/src/components/       ← Reusable UI components
frontend/src/lib/types.ts      ← All shared TypeScript types defined here
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

### Data & Seeding
- Seed script must produce a fully working app with real driver names, prices, and historical points
- Use 2025 Ergast data as the baseline if 2026 is not yet available
- Driver prices should be realistic ($8M–$30M range for top drivers)

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

1. Check `ROADMAP.md` — is it in Phase 1?
2. Add backend route in `backend/api/routes/`
3. Register route in `backend/main.py`
4. Add TypeScript types in `frontend/src/lib/types.ts`
5. Add API call in `frontend/src/lib/api.ts`
6. Build page or component
7. Test: does the seed data make it work end-to-end?

---

## Common Tasks

**Re-seed the database**
```bash
cd backend && python seed.py
```

**Run backend tests**
```bash
cd backend && pytest
```

**Check API docs**
Visit http://localhost:8000/docs (FastAPI auto-generates this)

**Manually trigger score validation**
```bash
curl -X POST http://localhost:8000/api/validation/run
```

---

*CLAUDE.md version: 1.0 | Project: f1-points-engine*
