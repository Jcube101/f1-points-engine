# F1 Points Engine — Test & Validation Plan

> This document is the step-by-step guide for validating the entire F1 Points Engine codebase.
> Run through it top to bottom before any release, after any major refactor, or when onboarding a new contributor.

---

## Overview

The validation plan is split into four layers:

| Layer | What it covers | Tool |
|-------|---------------|------|
| 1. Unit tests | Pure scoring + xP logic (no DB, no network) | `pytest` |
| 2. Integration tests | All API endpoints via in-memory SQLite DB | `pytest` + FastAPI TestClient |
| 3. Manual smoke tests | Real running app after seeding | `curl` |
| 4. Frontend build validation | TypeScript types + Vite bundle | `npm run build` |

---

## Step 1 — Install dependencies

```bash
# Backend
pip install pytest pytest-asyncio httpx sqlalchemy fastapi pulp

# Frontend
cd frontend && npm install
```

---

## Step 2 — Run the automated test suite

```bash
# From the repo root:
python -m pytest backend/tests/ -v
```

### Expected: 175 tests pass, 0 failures

### Test file index

| File | What it tests |
|------|--------------|
| `test_scoring.py` | All pure fantasy scoring functions in `core/scoring.py` |
| `test_expected_points.py` | xP calculation: weighted_average, circuit_type_multiplier, teammate_gap_factor, calculate_xp, xp_per_million |
| `test_api_core.py` | Health endpoint + `{ success, data }` response envelope on all routes |
| `test_api_drivers.py` | `GET /api/drivers`, `/api/drivers/{id}`, `/api/drivers/{id}/form`, `/api/drivers/circuit-fit`, `/api/drivers/{id}/vs-teammate` |
| `test_api_constructors.py` | `GET /api/constructors`, `/api/constructors/{id}/teammates` |
| `test_api_races.py` | `GET /api/races`, `/api/races/{id}/results`, `/api/races/upcoming-difficulty` |
| `test_api_standings.py` | WDC, WCC, value leaderboard, season progression |
| `test_api_team.py` | `POST /api/team/optimize` — both modes, budget constraint |
| `test_api_chips.py` | `POST /api/chips/recommend` — schema, confidence, edge cases |
| `test_api_transfers.py` | `GET /api/transfers/plan` — structure, nullability, chip field |

### Run a single test file

```bash
python -m pytest backend/tests/test_scoring.py -v
```

### Run a specific test class

```bash
python -m pytest backend/tests/test_scoring.py::TestRacePositionPoints -v
```

---

## Step 3 — Seed the real database

```bash
python backend/seed.py
```

### What gets seeded

| Table | Rows | Notes |
|-------|------|-------|
| `constructors` | 11 | All 2026 F1 teams |
| `drivers` | 22 | 2026 grid — includes Cadillac, Audi, correct LIN/Lindblad |
| `drivers` (2025-only) | 2 | TSU + DOO, price=0, 2025 results preserved |
| `races` | 48 | 24 rounds × 2 seasons (2025 + 2026) |
| `race_results` | ~576 | 24 drivers × 24 rounds (2025 only) |
| `fantasy_points` | ~576 | Matching race_results |
| `driver_circuit_profiles` | 60 | 20 active drivers × 3 circuit types |

### Verify seed counts

```bash
python3 - <<'EOF'
import sqlite3
conn = sqlite3.connect("f1_engine.db")
cur = conn.cursor()
for table in ["constructors","drivers","races","race_results","fantasy_points","driver_circuit_profiles"]:
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    print(f"{table}: {cur.fetchone()[0]}")
conn.close()
EOF
```

**Expected:**
```
constructors: 11
drivers: 24          ← 22 active + 2 retired (TSU, DOO)
races: 48
race_results: 576
fantasy_points: 576
driver_circuit_profiles: 60
```

---

## Step 4 — Start the backend

```bash
uvicorn backend.main:app --reload --port 8000
```

---

## Step 5 — Manual API smoke tests

Run each `curl` in a separate terminal (backend must be running).

### 5.1 Core

```bash
# Health check
curl http://localhost:8000/health
# Expected: {"status":"ok"}

# API root
curl http://localhost:8000/
# Expected: {"message":"F1 Points Engine API v1.0","docs":"/docs"}
```

### 5.2 Drivers

```bash
# All drivers — check count and Phase 2 fields
curl -s http://localhost:8000/api/drivers | python3 -c "
import json, sys
d = json.load(sys.stdin)['data']
print(f'{len(d)} drivers')
print('Phase 2 fields on first driver:', {k: d[0].get(k) for k in ['form_status','circuit_fit_score','is_differential']})
"

# Single driver
curl -s http://localhost:8000/api/drivers/1 | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['success'], d['data']['code'])"

# Form history (driver 1 = VER)
curl -s http://localhost:8000/api/drivers/1/form | python3 -c "
import json, sys
d = json.load(sys.stdin)['data']
print('flag:', d['flag'], '| delta:', d['delta'], '| history entries:', len(d['history']))
"

# Circuit fit — street circuits
curl -s "http://localhost:8000/api/drivers/circuit-fit?circuit_type=street" | python3 -c "
import json, sys
d = json.load(sys.stdin)['data']
print('Top 3 street drivers:')
for e in d[:3]: print(f\"  {e['driver_code']}: fit_score={e['fit_score']}\")
"

# vs-teammate
curl -s http://localhost:8000/api/drivers/1/vs-teammate | python3 -c "
import json, sys
d = json.load(sys.stdin)['data']
print(f\"{d['driver_1']['code']} vs {d['driver_2']['code']}, h2h_races={d['h2h_qualifying_races']}\")
"
```

### 5.3 Constructors

```bash
# All constructors
curl -s http://localhost:8000/api/constructors | python3 -c "
import json, sys
d = json.load(sys.stdin)['data']
print(f'{len(d)} constructors')
print('First:', d[0]['name'], '— drivers:', [dr['code'] for dr in d[0]['drivers']])
"

# Teammate comparison (constructor 1)
curl -s http://localhost:8000/api/constructors/1/teammates | python3 -c "
import json, sys
d = json.load(sys.stdin)['data']
if d: print(f\"{d['driver_1']['code']} avg={d['driver_1']['avg_fantasy_pts']:.1f} vs {d['driver_2']['code']} avg={d['driver_2']['avg_fantasy_pts']:.1f}\")
"
```

### 5.4 Races

```bash
# Calendar
curl -s "http://localhost:8000/api/races?season=2025" | python3 -c "
import json, sys
d = json.load(sys.stdin)['data']
print(f'{len(d)} races in 2025')
print('Circuit types:', set(r['circuit_type'] for r in d))
"

# Results for race 1
curl -s http://localhost:8000/api/races/1/results | python3 -c "
import json, sys
d = json.load(sys.stdin)['data']
print(f'{len(d)} results for race 1')
print('First result:', d[0]['driver_code'], 'quali:', d[0]['qualifying_pos'], 'race:', d[0]['race_pos'])
"

# Upcoming difficulty (shows next 5 races for current season)
curl -s "http://localhost:8000/api/races/upcoming-difficulty?drivers=VER,LEC,NOR" | python3 -c "
import json, sys
d = json.load(sys.stdin)['data']
for r in d: print(f\"R{r['round']} {r['race_name']} ({r['circuit_type']}): VER={r['driver_fits'].get('VER','?')}\")
"
```

### 5.5 Standings

```bash
# Fantasy value leaderboard (2025)
curl -s "http://localhost:8000/api/standings/value?season=2025" | python3 -c "
import json, sys
d = json.load(sys.stdin)['data']
print('Top 5 value drivers:')
for e in d[:5]: print(f\"  {e['code']}: xP={e['xp']:.1f}, value={e['value_score']:.2f}\")
"

# Fantasy points progression
curl -s "http://localhost:8000/api/standings/progression?season=2025" | python3 -c "
import json, sys
d = json.load(sys.stdin)['data']
print(f'{len(d)} rounds, {len([k for k in d[-1] if k not in (\"round\",\"round_name\")])} drivers tracked')
print('Final round leader:', max(((k,v) for k,v in d[-1].items() if k not in (\"round\",\"round_name\")), key=lambda x: x[1]))
"
```

### 5.6 Transfer Planner

```bash
# Plan for a team with VER, LEC, NOR, PIA, RUS
curl -s "http://localhost:8000/api/transfers/plan?drivers=VER,LEC,NOR,PIA,RUS&constructors=RBR,FER" | python3 -c "
import json, sys
d = json.load(sys.stdin)['data']
print(f'{len(d)} transfer moves planned:')
for m in d:
    add = m['add']['code'] if m['add'] else 'none'
    print(f\"  R{m['round']} {m['race']}: DROP {m['drop']['code']} → ADD {add} (budget: {m['budget_delta']/1e6:+.1f}M)\")
    if m['chip_alternative']: print(f\"    Chip tip: {m['chip_alternative']}\")
"
```

### 5.7 Team Optimizer

```bash
# Optimize a team
curl -s -X POST http://localhost:8000/api/team/optimize \
  -H "Content-Type: application/json" \
  -d '{"budget": 100000000}' | python3 -c "
import json, sys
d = json.load(sys.stdin)['data']['max_points']
print('Max Points team:')
print('  Drivers:', [dr['code'] for dr in d['drivers']])
print('  Constructor:', [c['code'] for c in d['constructors']])
print(f\"  Total xP: {d['total_xp']:.1f}, Cost: \${d['total_price']/1e6:.1f}M, Feasible: {d['feasible']}\")
"
```

### 5.8 Chip Advisor

```bash
curl -s -X POST http://localhost:8000/api/chips/recommend \
  -H "Content-Type: application/json" \
  -d '{"race_id": 6, "chips_remaining": ["drs_boost","no_negative","wildcard"], "team_value": 98000000, "transfers_banked": 2, "races_completed": 5}' \
  | python3 -c "import json,sys; d=json.load(sys.stdin)['data']; print(d['chip'], '-', d['confidence'], ':', d['reason'][:80])"
```

---

## Step 6 — Frontend build validation

```bash
cd frontend && npm run build
```

**Expected:** TypeScript compilation succeeds, Vite produces `dist/` with no errors.
Bundle size warning (>500 kB) is expected — it's Recharts + React. Not a failure.

---

## Step 7 — Frontend dev server smoke test

```bash
# Terminal 1: backend
uvicorn backend.main:app --reload --port 8000

# Terminal 2: frontend
cd frontend && npm run dev
```

Open http://localhost:5173 and manually verify:

| Page | Check |
|------|-------|
| **Home / Dashboard** | Races remaining shows correctly; next race countdown |
| **Team Builder — Drivers tab** | Form badges (🔴/🟢) visible on overperforming/underperforming drivers; ⚡ on differentials |
| **Team Builder — Driver card expand** | Tap "Show form trend" → sparkline loads with actual vs xP lines |
| **Team Builder — Constructors tab** | "Compare Teammates" button visible on each card |
| **Team Builder — Teammate Modal** | Opens on button click; stat table shows green winner highlights; bar chart renders |
| **Team Builder — Differentials toggle** | "Show Differentials Only" checkbox filters to ⚡ drivers only |
| **Team Builder — Transfer Planner** | "Transfer Planner" section expands; after selecting a team, plan loads with drop/add/reasoning |
| **Team Builder — Optimize** | Runs optimizer; "Load Team" populates the selection |
| **Standings — Fixture View tab** | Shows next 5 races with colour-coded driver tiles (green ≥7, amber ≥4, red <4) |
| **Standings — WDC tab** | Championship table + progression chart renders |
| **Standings — Fantasy Value tab** | Sorted leaderboard renders |
| **Live Race** | Shows "No active session" or live data depending on race calendar |
| **Chip Advisor** | Recommendation card + confidence badge renders |

### Mobile check (390px)

Resize browser to 390px width and verify:
- [ ] Bottom nav visible (5 tabs)
- [ ] DriverCard badges don't overflow at narrow width
- [ ] TeammateModal opens as bottom sheet (not centered)
- [ ] Fixture View tiles scroll horizontally
- [ ] Transfer Planner readable at 390px

---

## Step 8 — Data integrity checks

```bash
python3 - <<'EOF'
import sqlite3
conn = sqlite3.connect("f1_engine.db")
cur = conn.cursor()

# 1. No driver without a constructor
cur.execute("SELECT COUNT(*) FROM drivers d LEFT JOIN constructors c ON d.team_id = c.id WHERE c.id IS NULL AND d.price > 0")
orphan_drivers = cur.fetchone()[0]
print(f"Orphan drivers (no constructor): {orphan_drivers} — expected 0")

# 2. All 3 circuit types represented in circuit profiles
cur.execute("SELECT circuit_type, COUNT(DISTINCT driver_id) FROM driver_circuit_profiles GROUP BY circuit_type")
for row in cur.fetchall():
    print(f"Circuit profiles — {row[0]}: {row[1]} drivers")

# 3. Fantasy points match race results count
cur.execute("SELECT COUNT(*) FROM fantasy_points WHERE total_pts = 0 AND race_id IN (SELECT id FROM races WHERE season=2025)")
zero_pts = cur.fetchone()[0]
print(f"Zero-total fantasy points rows in 2025: {zero_pts} — expected 0 (if all seeded)")

# 4. Check 2025-only drivers have price=0
cur.execute("SELECT code, price FROM drivers WHERE code IN ('TSU','DOO')")
for row in cur.fetchall():
    print(f"{row[0]} price: {row[1]} — expected 0")

conn.close()
EOF
```

---

## Step 9 — Regression checklist after changes

Run this checklist after any edit to `backend/`:

- [ ] `python -m pytest backend/tests/ -q` — all 175 pass
- [ ] `python backend/seed.py` — exits cleanly, prints seeded row counts
- [ ] `curl http://localhost:8000/api/drivers | python3 -c "import json,sys; print(len(json.load(sys.stdin)['data']), 'drivers')"` — returns 22
- [ ] `curl http://localhost:8000/api/drivers/circuit-fit?circuit_type=street` — returns sorted list
- [ ] `curl http://localhost:8000/api/transfers/plan?drivers=VER,LEC` — returns ≤3 moves

Run this checklist after any edit to `frontend/`:

- [ ] `cd frontend && npm run build` — TypeScript clean compile
- [ ] Driver card badges render at 390px without overflow
- [ ] TeammateModal bottom-sheet opens/closes on mobile viewport

---

## Continuous Integration (future)

When a CI pipeline is added (GitHub Actions), the recommended workflow is:

```yaml
# .github/workflows/test.yml
- run: pip install pytest pytest-asyncio fastapi sqlalchemy pulp httpx
- run: python -m pytest backend/tests/ -v
- run: cd frontend && npm ci && npm run build
```

---

*Test Plan version: 1.0 | Project: f1-points-engine | Tests: 175 passing*
