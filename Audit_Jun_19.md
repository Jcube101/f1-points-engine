# F1 Points Engine — Codebase Audit (Jun 19)

Full review of the actual source and the seeded `f1_engine.db`, not the docs. Findings are
prioritised: **Critical** (breaks/badly misleads during a live race weekend), **Important**
(wrong data or missing/contradicted feature), **Minor** (cleanup/polish). Nothing was changed —
this is report-only.

Scope reviewed: all backend modules + routes, `seed.py`, the seeded DB, all frontend pages/
components, tests, and the `CLAUDE.md`/`SPEC.md`/`ROADMAP.md` claims.

**Positive baseline:** `backend/core/scoring.py` matches the `SPEC.md` scoring tables exactly
(quali 10→1 / −5, sprint 8→1 / −10, race 25→1 / −20, all bonuses, chip multipliers). 2026
driver→team assignments in the DB are all correct vs the announced 2026 grid. 175 backend tests
pass.

---

## 🔴 Critical — would break or badly mislead during a live race weekend

### C1. Live fantasy points omit position changes, overtakes, DOTD, and all constructor points
`backend/data/openf1_client.py:176-200` (and `:209`)

In `build_live_snapshot`, every driver is scored with `positions_gained=0` and `overtakes=0`
hard-coded, fastest-lap is the only bonus applied, and `constructors` is always returned as `[]`:
```python
bonus = race_bonus_points(0, 0, is_fastest)   # positions_gained & overtakes forced to 0
...
"constructors": [],
```
During an actual race the headline live numbers are therefore wrong — they show only base
position points (+10 for fastest lap), never the +1/position-gained, +1/overtake, or +10 DOTD that
the scoring engine supports, and constructor live points never appear at all. The expandable
breakdown in `LiveTicker.tsx:127-128` always shows `Positions + 0 / Overtakes 0`.

### C2. `stale` flag is never set true on OpenF1 downtime (and `get_stale_flag()` is broken)
`backend/data/openf1_client.py:208`, `:119-121`

`build_live_snapshot` hard-codes `"stale": False`, even though `_get()` (`:44-46`) silently falls
back to cached data when OpenF1 is unreachable. The docstring (`:134`) and `SPEC.md` both promise
`stale=True` when serving cached data. Result: if OpenF1 drops mid-race, the frontend keeps
rendering the last cached snapshot as if it were live, with no "Stale" badge
(`LiveTicker.tsx:33` is dead because the value is always false).
`get_stale_flag()` itself is also wrong — `return bool(_cache)` is `True` after the first
successful fetch forever — and is never called anywhere.

### C3. Live "total laps" is hard-coded to 57
`backend/data/openf1_client.py:206`

`"total_laps": 57,  # default; actual from race data`. The session progress bar
(`LiveTicker.tsx:21,43-55`) divides the real lap count by a constant 57, so the progress bar is
wrong for every race that isn't 57 laps (e.g. Monaco 78, Spa 44). Not a crash, but visibly wrong
on the one screen people stare at during a race.

---

## 🟠 Important — wrong data or missing/contradicted feature

### I1. Retired (price-0) drivers leak into the optimizer and value tables
`backend/api/routes/team.py:21-22`, `backend/api/routes/points.py:101`

`_build_assets` does `db.query(Driver).all()` with no `price > 0` filter. Tsunoda (TSU) and Doohan
(DOO) are seeded at price 0 to preserve 2025 history (confirmed in DB). Because they cost nothing
and still carry positive xP (verified recent pts: TSU `[1,4,22]`, DOO `[18,-1,0]`), the PuLP
`optimize_max_points` solver will preferentially pick these *free* drivers — the "Max Points Team"
can recommend retired drivers. `/api/points/leaderboard` lists them too. Fix would be to filter
`price > 0` when building assets.

### I2. `/api/constructors` shows retired drivers as current teammates
`backend/api/routes/constructors.py:18-19`

The driver list per constructor is `db.query(Driver).filter_by(team_id=c.id).all()` with no
`price > 0` filter. In the DB this makes **Racing Bulls = LAW · LIN · TSU** and
**Alpine = GAS · COL · DOO** (three drivers each). It renders straight onto the card
(`ConstructorCard.tsx:38`). The `/teammates` endpoint (`:43-48`) *does* filter `price > 0`, so the
two endpoints disagree.

### I3. Default-season views (2026) return all-zero / empty data
`backend/api/routes/standings.py:118-160` (value) and `:62-115` (progression)

`CURRENT_SEASON = 2026`, but the DB has **0 FantasyPoints rows for 2026** (only 2025 was seeded —
480 rows). `/api/standings/value` filters by 2026 race ids → every driver gets `xp=0`,
`value_score=0`. `/api/standings/progression` returns `[]`. So the default (no `?season=`) value
leaderboard and progression chart are blank/zero. (Note: `/api/drivers` avoids this because it
does *not* filter fantasy history by season — an inconsistency in itself.)

### I4. Score validation never displays current-season results
`backend/api/routes/validation.py:55` vs `:24-31`

`POST /api/validation/run` validates `db.query(Race).order_by(Race.round_number.desc()).first()` —
that's the max round across *all* seasons, i.e. 2025 round 24 (2025 has 24 rounds, 2026 has 21).
But `GET /api/validation/latest` filters `Race.season == CURRENT_SEASON` (2026). The DB already has
20 `ScoreValidation` rows (all for the 2025 race), yet `/latest` returns empty — so the
ScoreValidator page is permanently blank despite validation having run.

### I5. Phase 3 was built despite the documented scope freeze
`backend/api/routes/simulator.py`, `frontend/src/pages/TitleRace.tsx`, `App.tsx:28`, `main.py:113`

`CLAUDE.md` says "Do not build Phase 3 features unless explicitly instructed" and `ROADMAP.md:81`
marks the Championship Simulator / "Interactive Title Odds Calculator" as Phase 3 (🔮). A full
Monte-Carlo title-odds simulator endpoint, a `/title-race` route, and an interactive
pace-slider page all exist and are wired in. Either the docs are stale or this shipped ahead of
plan — worth an explicit decision.

### I6. Title-odds simulator uses 2025 fantasy points as the 2026 championship baseline
`backend/api/routes/simulator.py:163-166`

`current_pts[d.id] = sum(fp.total_pts for fp in d.fantasy_points)` sums every driver's **2025
fantasy points** and treats it as their *current 2026 championship points*, then adds simulated
real-F1 race points (`F1_PTS`, different unit) on top. The "current_points" column and win
probabilities are therefore based on the wrong number and mix two scoring systems. (Section A of
`TitleRace.tsx` shows real 2026 WDC points from Jolpica; Section B shows these bogus ones — they
won't agree.)

### I7. 2026 calendar diverges from the real 2026 calendar (Madrid GP missing)
`backend/seed.py:269-292`

The seeded 2026 calendar has 21 rounds. Removing Bahrain + Saudi Arabia is intentional (per recent
commits), but the real 2026 calendar's headline addition — the **Madrid GP (Madring)** — is absent
entirely, and Spain is still listed only at Barcelona. Net: 21 rounds vs the real 24. Flagging
because the task asked to check against the real calendar; if the fictional cancellations are
deliberate, at least Madrid should be reconciled.

---

## 🟡 Minor — cleanup / polish

### M1. Dead config constants
`backend/core/config.py:4,16-20` — `ERGAST_BASE_URL` is never used (`ergast_client.py` hard-codes
its own `ERGAST_BASE`), and `CIRCUIT_MULTIPLIERS` (all 1.0 placeholders) is never imported; the
real per-driver table lives in `expected_points.DEFAULT_CIRCUIT_MULTIPLIERS`.

### M2. Dead imports in seed
`backend/seed.py:29-32` — `get_race_calendar, get_drivers, get_constructors, get_season_results,
get_season_qualifying` are imported but never called (seeding uses the `FALLBACK_*` constants).

### M3. Dead + broken helper
`backend/data/openf1_client.py:119-121` — `get_stale_flag()` is unused and its logic is wrong (see
C2).

### M4. Seed log/docstring says "24 rounds" for 2026
`backend/seed.py:725` logs "Seeding 2026 race calendar (24 rounds)" and the module docstring
(`:6`) implies the same, but only 21 are seeded.

### M5. xP circuit-multiplier table is stale
`backend/core/expected_points.py:19-42` — includes `SAR` (Sargeant, on no current grid) and is
missing 2026 drivers `COL`, `PER`, `BOT`, `LIN` (they silently default to 1.0 via `.get`, so it
works, but the data is stale).

### M6. SQLAlchemy 2.0 deprecation: `Query.get()` used throughout
e.g. `drivers.py:212,236,293,311`, `races.py:49,58`, `validation.py:34-35`, `constructors.py:38` —
`db.query(Model).get(id)` is legacy; should be `db.get(Model, id)`. Emits deprecation warnings on
the Python 3.13 / SQLAlchemy 2.0.51 production stack.

### M7. Tap targets below the 44×44px rule (CLAUDE.md)
`DriverCard.tsx:107` (`min-h-[32px]` expand button), `ConstructorCard.tsx:54` (`min-h-[36px]`),
`TeamBuilder.tsx:103,112,214,318` (sort toggles, DRS pills, differential checkbox — `min-h-[36px]`),
`TitleRace.tsx:243-251` (range sliders, "Reset sliders" tiny text). Primary nav (`BottomNav` 56px,
`TeamBuilder` optimize 48px, main action buttons 44px) is fine, and root `overflow-x-hidden` /
global `pb-20` are correctly applied — no horizontal-overflow issues found.

### M8. Unused query param
`backend/api/routes/transfers.py:53` — `constructors` is accepted and documented but never used in
the planning logic.

### M9. Doc/impl drift in xP helpers
`backend/core/expected_points.py:98,109-110` — docstring says "±5% … 0.97 = 3% penalty" but the cap
is `min(0.05, max(-0.03, …))` (i.e. +5% / −3%, not ±5%). `weighted_average` docstring (`:54`) says
weights are "redistributed proportionally" for <3 races, but the 2-race branch hard-codes
`[0.4, 0.6]`.

### M10. Test-coverage gaps on the highest-risk runtime code
175 tests exist but cover only scoring, xP, and the drivers/races/standings/team/transfers/chips/
constructors routes. **No tests** for: the live pipeline (`openf1_client.build_live_snapshot`,
`live_poller`, `/api/live`), `fantasy_validator` + `/api/validation`, `/api/points` (calculate &
leaderboard), the Phase-3 `simulator`, `ergast_client`, or `seed.py`. The live/validation code —
exactly the code that runs during a race weekend and the source of several findings above — is the
least tested.

### M11. Dead Ergast fallback
`backend/data/ergast_client.py:19,25` — `_get` falls back to `https://ergast.com/api/f1` after
Jolpica, but Ergast was retired in 2024; the fallback can never succeed (harmless, just noise in
logs).

### M12. `/api/points/calculate` scoring fidelity
`backend/api/routes/points.py:63-73` — applies No-Negative *then* DRS ×2 (order affects negatives),
and for sprint weekends adds only `sprint_position_points` with no DNF/bonus handling. Minor vs the
full engine; only matters if this endpoint is used for exact reconciliation.

### M13. WebSocket double-remove on disconnect
`backend/main.py:47-49,60-61,132-133` — `broadcast()` removes a dead socket from
`active_connections`, then the handler's `WebSocketDisconnect` path calls `manager.disconnect()`
which does `list.remove()` again → `ValueError` if the same socket already got pruned. Edge case
when a client drops mid-broadcast during a race; use a guarded `if ws in …` / `set` to be safe.

---

## Suggested triage order

1. **C1/C2** — make live scoring actually compute gains/overtakes/DOTD/constructors and set the
   `stale` flag (core feature correctness during races).
2. **I1/I2** — add `price > 0` filters in `team._build_assets` and `constructors` (stops retired
   drivers being recommended/shown).
3. **I3/I4** — decide how default-season (2026, no data yet) value/progression/validation should
   behave, or fall the defaults back to the last season with data.
4. **I5/I6** — reconcile the Phase-3 simulator with the roadmap and fix its points baseline.
5. **I7** — reconcile the 2026 calendar (Madrid) with reality, or document the divergence.
6. Minor items as cleanup, prioritising **M10** test coverage for the live/validation paths.
