# F1 Points Engine — Development Learnings

> A living record of the non-obvious decisions, bugs, and patterns discovered while building this project.
> Every entry is specific — general advice belongs in the README or CLAUDE.md.
> When you fix a bug or discover an unexpected behaviour, add it here.

---

## Backend — FastAPI & Routing

### L-001 · Route ordering: static paths before parametrized ones

**Context:** Adding `GET /api/drivers/circuit-fit` alongside `GET /api/drivers/{driver_id}`.

**Problem:** FastAPI evaluates routes in declaration order. If `/{driver_id: int}` were declared first and the type annotation was `str`, `/circuit-fit` would match it. With `int` typing, FastAPI correctly rejects non-integer strings — but declaration order still matters for `str`-typed params.

**Rule:** Always declare static path segments (`/circuit-fit`, `/upcoming-difficulty`) **before** parametrized segments (`/{driver_id}`) in the same router. This is defensive and clear.

```python
# CORRECT — static routes first
@router.get("/circuit-fit")
async def get_circuit_fit(...): ...

@router.get("/{driver_id}")
async def get_driver(...): ...
```

---

### L-002 · `{ success, data }` envelope — don't return HTTP 404 from route handlers

**Context:** Designing error responses for unknown resource IDs.

**Decision:** This codebase returns `{ "success": false, "error": "...", "data": null }` with HTTP 200 instead of raising `HTTPException(404)`. This keeps the response shape consistent for the frontend, which always expects a JSON envelope.

**Implication for tests:** Test for `r.json()["success"] is False`, not `r.status_code == 404`. The test suite had five failures from this assumption before being corrected.

**Trade-off:** Purists prefer HTTP 404 (more RESTful). The envelope approach is simpler for a single-user app where the frontend controls all callers.

---

### L-003 · FastAPI `lifespan` vs `on_event` — `init_db()` must import every model

**Context:** `init_db()` in `database.py` calls `Base.metadata.create_all(bind=engine)`.

**Problem:** `create_all()` only creates tables for models that have been **imported** (and therefore registered with `Base.metadata`) at call time. If a new model is added to `models.py` but not imported inside `init_db()`, its table silently never gets created.

**Root cause discovered:** When `DriverCircuitProfile` was added to `models.py`, it was missing from the import list inside `init_db()`. The table existed in tests (because the test conftest imports all models) but would be absent in a fresh production startup.

**Fix:** Always keep the import list in `init_db()` in sync with all models:

```python
def init_db():
    from backend.data.models import (  # noqa: F401
        Driver, Constructor, Race, RaceResult,
        FantasyPoints, ScoreValidation, DriverCircuitProfile,  # ← keep this updated
    )
    Base.metadata.create_all(bind=engine)
```

---

### L-004 · Idempotent seeding with delete-then-insert

**Context:** `seed_circuit_profiles()` and other seed functions need to be safe to re-run.

**Pattern:** Delete all rows first, commit, then re-insert. This is simpler than upsert (merge) for a development seed script.

```python
def seed_circuit_profiles(db):
    db.query(DriverCircuitProfile).delete()
    db.commit()
    # ... re-insert all rows ...
    db.commit()
```

**Warning:** Order matters — delete child rows before parent rows if foreign keys are enforced (SQLite doesn't enforce FK by default but Postgres does).

---

### L-005 · Two-pass algorithm required for percentile thresholds

**Context:** Computing the Differential Finder flag (`is_differential = top-30% xP AND price < $12M`).

**Problem:** You can't compute "top 30%" in a single pass over the driver list because you don't know the threshold until all values are collected.

**Solution:** Two passes — collect all values first, sort to find the threshold, then apply:

```python
# Pass 1: collect
sorted_xps = sorted(r["xp"] for r in raw)
threshold_idx = max(0, len(sorted_xps) - len(sorted_xps) // 3 - 1)
top30_threshold = sorted_xps[threshold_idx] if sorted_xps else 0

# Pass 2: apply
is_differential = r["xp"] >= top30_threshold and d.price < 12_000_000
```

---

### L-006 · Per-race xP must be computed dynamically for form history

**Context:** `GET /api/drivers/{id}/form` computes actual vs xP for the last 5 races.

**Problem:** The `xp_score` column in `FantasyPoints` is only populated at the end of the season (via a bulk calculation). For historical races, it's often `0.0` or `None`.

**Solution:** For each of the last 5 races, dynamically compute xP from the 3 **preceding** race results:

```python
for i, fp in enumerate(last_5):
    preceding = [p.total_pts for p in sorted_fps if p.race.round_number < fp.race.round_number][-3:]
    xp = calculate_xp(preceding, driver.code, fp.race.circuit_type)
    # compare fp.total_pts vs xp
```

This gives a true "expected vs actual" comparison rather than a misleading `0 vs actual`.

---

### L-007 · `_form_flag` is ratio-based, not delta-based

**Context:** Determining if a driver is overperforming, underperforming, or on_form.

**Why ratio, not delta:** A delta of +10 pts means something very different for a driver averaging 5 pts vs one averaging 40 pts. A 20% deviation from expectation is meaningful regardless of scale.

```python
def _form_flag(actual_avg: float, xp: float) -> str:
    if xp <= 0:
        return "on_form"
    ratio = actual_avg / xp
    if ratio > 1.2:   # scoring 20%+ above expectation → regression risk
        return "overperforming"
    if ratio < 0.8:   # scoring 20%+ below expectation → bounce-back candidate
        return "underperforming"
    return "on_form"
```

---

## Backend — SQLAlchemy

### L-008 · SQLite in-memory databases require `StaticPool` in tests

**Context:** The test suite uses `sqlite:///:memory:` for a fast, isolated test DB.

**Problem:** By default, SQLAlchemy creates a new connection for each `SessionLocal()` call. SQLite in-memory databases are **per-connection** — a new connection sees an empty database. This means:
- `_create_tables()` creates tables on connection A
- `seed_test_db` seeds data on connection B (sees the tables, fine)
- A request uses `override_get_db` which creates connection C (sees an **empty** DB)

**Fix:** Use `StaticPool` to force all sessions to share one connection:

```python
from sqlalchemy.pool import StaticPool

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # ← critical for in-memory test DBs
)
```

---

### L-009 · `Query.get()` is a legacy SQLAlchemy API

**Context:** Several routes use `db.query(Model).get(primary_key)`.

**Issue:** This triggers `LegacyAPIWarning` in SQLAlchemy 2.x. The preferred API is `db.get(Model, primary_key)` or `db.query(Model).filter_by(id=pk).first()`.

**Not a breaking change** — the tests pass — but worth upgrading when refactoring routes to avoid future deprecation errors.

---

### L-010 · Seeding order matters: circuit profiles depend on FantasyPoints

**Context:** `seed_circuit_profiles()` aggregates `FantasyPoints.total_pts` grouped by `Race.circuit_type`.

**Rule:** Always call `seed_circuit_profiles()` **after** `seed_fantasy_points()` and `seed_races()` are committed. In `seed.py`, function call order is the dependency graph.

---

## Frontend — React & TypeScript

### L-011 · Always read a file before editing it with the Edit tool

**Context:** The Edit tool requires the file to have been read in the current session before any edit can be applied.

**Pattern:** Even if you only need to read 5 lines to confirm context, do it. `Read(file, limit=5)` is enough to unblock the edit.

**Failure mode:** `"File has not been read yet"` error — the edit is rejected entirely, wasting a round trip.

---

### L-012 · React Query `enabled` flag for lazy/on-demand fetching

**Context:** DriverCard sparkline — don't fetch form data until the user expands the card.

**Pattern:**

```typescript
const [expanded, setExpanded] = useState(false)

const { data: formData } = useQuery({
  queryKey: ['driverForm', driver.id],
  queryFn: () => fetchDriverForm(driver.id),
  enabled: expanded,   // ← only fires when true
})
```

This prevents N × API calls on initial page load (one per driver card visible).

---

### L-013 · Nullable fields from backend — use optional chaining in TypeScript

**Context:** `TransferMove.add` can be `null` when no valid replacement is found within budget.

**Problem:** TypeScript's strict null checks catch `move.add.code` as a compile error when `add: ... | null`.

**Fix:** Use optional chaining with nullish coalescing:

```typescript
<span>{move.add?.code ?? 'N/A'}</span>
```

**General rule:** When a backend field is typed as `T | null` in the TypeScript interface, always use `?.` and `?? fallback` at the call site. Don't suppress the error with `!` (non-null assertion).

---

### L-014 · Recharts inside horizontally scrollable containers

**Context:** Sparklines and fixture charts need to be readable on mobile (390px) without shrinking.

**Pattern:**

```tsx
<div className="overflow-x-auto -mx-1">
  <div className="min-w-[260px] px-1">
    <ResponsiveContainer width="100%" height={100}>
      <AreaChart ...>
```

- `overflow-x-auto` enables horizontal scrolling on the outer container
- `min-w-[Npx]` prevents the chart from collapsing below a readable size
- `ResponsiveContainer width="100%"` fills the inner container correctly
- `-mx-1 px-1` cancels the parent's padding at the edges

---

### L-015 · Mobile bottom-sheet modal pattern

**Context:** TeammateModal — full-screen on desktop, slides up from bottom on mobile.

**Pattern:**

```tsx
{/* Backdrop */}
<div className="fixed inset-0 bg-black/60 z-40" onClick={onClose} />

{/* Sheet */}
<div className="fixed z-50 bottom-0 left-0 right-0 sm:inset-0 sm:flex sm:items-center sm:justify-center sm:p-4">
  <div className="bg-gray-900 rounded-t-2xl sm:rounded-2xl ...">
    {/* Handle visible only on mobile */}
    <div className="flex justify-center pt-3 sm:hidden">
      <div className="w-10 h-1 bg-gray-600 rounded-full" />
    </div>
    ...
  </div>
</div>
```

Key points:
- Backdrop closes modal on tap (mobile-friendly)
- `bottom-0 left-0 right-0` on mobile → `inset-0 flex items-center` on sm+
- `rounded-t-2xl sm:rounded-2xl` — square bottom on mobile, fully rounded on desktop
- Escape key closes via `useEffect` with `keydown` listener

---

### L-016 · Sticky footer padding — `pb-44 sm:pb-0` pattern

**Context:** TeamBuilder mobile layout — content scrolls behind the sticky footer.

**Architecture:**
- BottomNav: `fixed bottom-0 h-14 z-50` (56px)
- TeamBuilder mobile footer: `fixed bottom-14 z-40` (~100px tall when DRS pills + budget bar + button)
- Content must scroll above both: `pb-44 sm:pb-0` (176px bottom padding on mobile, none on desktop)

**Rule:** Any page with a mobile-only sticky footer above BottomNav needs `pb-44 sm:pb-0` on the scroll container.

---

### L-017 · `Constructor.code` is optional in the type — always provide a fallback

**Context:** Transfer Planner needs constructor codes to pass to the backend.

**Problem:** `Constructor` has `code?: string` (optional). When mapping selected constructors to codes:

```typescript
// WRONG — can produce undefined entries
const codes = team.constructors.map(c => c.code)

// CORRECT — graceful fallback
const codes = team.constructors.map(c => c.code ?? c.name.substring(0, 3).toUpperCase())
```

---

### L-018 · `Record<string, unknown>` from JSON requires explicit casting

**Context:** `UpcomingRaceDifficulty.driver_fits` typed as `Record<string, number>` but TypeScript infers JSON values as `unknown`.

**Problem:** `.entries()` returns `[string, unknown][]`. Arithmetic on `unknown` values fails type check.

**Fix:** Cast at point of use:

```typescript
for (const [code, score] of Object.entries(race.driver_fits)) {
    const s = score as number   // ← explicit cast required
    const color = s >= 7 ? 'green' : ...
}
```

---

## Tooling & Workflow

### L-019 · `gh` CLI doesn't work with local git proxy

**Context:** The development environment uses a local git proxy (`http://127.0.0.1:52679/git/...`) instead of pointing directly to `github.com`.

**Problem:** `gh pr create` attempts to call `api.github.com` with the proxy's credentials, which returns HTTP 401.

**Workaround:** Push the branch with `git push -u origin <branch>` (which works through the proxy), then create the PR manually on GitHub via the URL printed in the push output.

---

### L-020 · Edit tool replaces entire class definitions if the old_string includes the class line

**Context:** Editing `models.py` to insert `DriverCircuitProfile` before `ScoreValidation`.

**Bug:** When the `old_string` included `class ScoreValidation(Base):` as the **start** of the match, the replacement text accidentally omitted `__tablename__ = "score_validations"`, wiping the table name.

**Result:** `ScoreValidation` rows would be written to an unnamed/default table, causing silent data corruption.

**Prevention:**
1. Keep `old_string` as small as possible — match only the insertion point, not the surrounding class
2. After any models.py edit, verify `__tablename__` is still present: `grep __tablename__ backend/data/models.py`
3. Run `python -c "from backend.data.models import ScoreValidation; print(ScoreValidation.__tablename__)"` to confirm

---

### L-021 · Pytest session-scope fixture ordering and `autouse`

**Context:** Test conftest with `session`-scoped `seed_test_db` (autouse) and `client` fixtures.

**Rule:** `autouse=True, scope="session"` fixtures are guaranteed to run before any test in the session, but their ordering relative to other session fixtures is determined by the dependency graph. To guarantee `seed_test_db` runs before `client` starts receiving requests, make `client` depend on `seed_test_db` explicitly if ordering matters.

**In practice:** With `StaticPool` (L-008), all sessions share the same connection, so data seeded by `seed_test_db` is immediately visible to `client`. The `autouse` + `scope="session"` combination was sufficient.

---

### L-022 · `npm run build` (`tsc && vite build`) is the frontend's primary type checker

**Context:** No vitest or Jest is configured in this project.

**What it catches:** All TypeScript type errors across the entire frontend, including:
- Nullable field accesses (`move.add.code` when `add: T | null`)
- Missing required props on components
- Incorrect return types on API functions

**What it doesn't catch:** Runtime behaviour, component rendering, user interactions.

**Recommendation for future:** Add `vitest` for component unit tests and React Testing Library for interaction tests. This project currently relies on `npm run build` for static analysis and manual testing for runtime.

---

### L-023 · Commit early, commit often — feature branch per phase

**Strategy used:** One branch per phase (`claude/phase2-intelligence-hsmUW`), with a single squash-friendly commit at the end of the phase.

**Trade-off:**
- Fewer, larger commits → cleaner history on main
- Less granular rollback capability during development

**Better practice for future phases:** Commit after each of the 5 features is individually complete, not just at the end. This makes bisecting easier if a regression is introduced.

---

## Data & Domain Knowledge

### L-024 · Mid-season driver swaps need special handling in seed data

**Context:** In 2025, Liam Lawson drove for Red Bull in rounds 1–2, then Yuki Tsunoda took over from round 3.

**Solution:** `get_2025_constructor(code, round_num)` in `seed.py` routes LAW to Red Bull for rounds 1–2 and TSU for rounds 3–24. Both drivers must exist in the DB with their correct constructors.

**Lesson:** Real F1 data has mid-season changes. Any data model that assumes one driver per seat per season will need patching.

---

### L-025 · 2025-only drivers must be preserved with `price=0`

**Context:** TSU (Tsunoda) and DOO (Doohan) were on the 2025 grid but not the 2026 grid.

**Problem:** Their race results are needed for historical standings and form data. Deleting them would break foreign key relationships across `race_results` and `fantasy_points`.

**Solution:** Keep them in the `drivers` table with `price=0`. The frontend filters `price > 0` for the Team Builder, so they never appear as selectable picks.

---

### L-026 · Circuit types drive xP calculations — tag every race correctly

**Context:** `Race.circuit_type` (`street | power | balanced`) feeds into the xP multiplier for each driver.

**Impact of wrong tags:**
- A driver tagged as strong on `street` circuits will get inflated xP on a `balanced` race tagged as `street`
- This cascades into wrong differential flags, wrong transfer recommendations, and wrong fixture view scores

**Rule:** When seeding races, always cross-check the circuit type against the F1 calendar. Monaco, Singapore, Baku, Jeddah = street. Monza, Spa, Silverstone = power. Most others = balanced.

---

*LEARNINGS.MD version: 1.0 | Entries: 26 | Last updated: March 2026*
