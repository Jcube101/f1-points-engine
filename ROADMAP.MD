# F1 Points Engine — Roadmap

## Phase 1: Core Fantasy Tool ✅ *Build this first*

Everything a fantasy player needs to compete seriously.

**Team Builder + Optimizer**
- Manual team picker with driver/constructor cards (price, form, value score)
- PuLP optimizer: Max Points team + Best Value team
- Real-time budget tracker
- DRS Boost selector

**Fantasy Scoring Engine**
- Full rules implementation: qualifying, sprint, grand prix
- All bonuses: positions gained/lost, overtakes, fastest lap, pit stops
- Chip effects: DRS Boost (2×/3×), No Negative, Wildcard, Limitless, Autopilot, Final Fix
- Score validation layer: cross-check our computed scores vs official F1 Fantasy API after each race

**Live Race Tracker**
- OpenF1 API integration (lap-by-lap position, pit stops, fastest lap)
- WebSocket push to frontend every 30 seconds during sessions
- Session-aware: auto-applies qualifying vs sprint vs race scoring rules
- Live points table with delta indicators

**Chip Advisor**
- Rule-based recommendations (street circuit → No Negative, banked transfers → Wildcard, etc.)
- Confidence rating + plain-English explanation

**Standings Page**
- F1 Drivers Championship (WDC) with points progression chart
- F1 Constructors Championship (WCC)
- Fantasy value leaderboard (points per $M)

**Expected Points (xP)**
- Rolling weighted average with circuit-type multiplier
- Shown on all driver cards, used by optimizer

---

## Phase 2: Intelligence Layer 🔜 *After Phase 1 is stable*

Turns good fantasy players into great ones. FPL-inspired analytical depth.

**Circuit Intelligence**
- Each circuit tagged: street / power / balanced / high-overtake
- Per-driver performance history on each circuit type
- "Circuit fit score" shown for each driver before each race weekend
- Upcoming fixture difficulty view: rank next 5 races by opportunity for your team

**Differential Finder**
- Flag drivers with high xP but likely low ownership
- "This driver is owned by few but could be the highest scorer this weekend"
- Inspired by FPL differential picks concept

**Form vs Luck Detector**
- Compare actual points vs xP over last 5 races
- "Overperforming" flag: driver scoring above xP (regression risk)
- "Underperforming" flag: driver scoring below xP (bounce-back candidate)
- Helps users avoid buying at peak and selling at trough

**Transfer Planner**
- Multi-week view: plan transfers 3 races ahead
- Chip timing recommendations based on fixture run
- Price rise/fall predictions based on recent xP vs price

**Teammate Comparison**
- Head-to-head qualifying and race stats for drivers within the same team
- Helps decide which teammate to pick when budget-constrained

---

## Phase 3: Championship Simulator 🔮 *The non-fantasy hook*

Makes the tool useful for every F1 fan, not just fantasy players. This is the distribution and marketing engine.

**Interactive Title Odds Calculator**
- Select your favourite driver
- See their current championship win probability (computed via Monte Carlo simulation)
- Simulation runs remaining races thousands of times, weighted by each driver's historical finish distribution
- Updates live after every race

**Scenario Builder**
- Drag-and-drop finishing positions for upcoming races
- "What if Max retires from the next 2 races?" → see probability shift instantly
- "What does George need to do in the last 5 races to win?" → system computes minimum required results
- Shareable scenarios via URL (e.g. `?scenario=VER:DNF,NOR:P1,PIA:P3`)

**Championship Math Panel**
- "Driver X is mathematically eliminated from the title" alerts
- Maximum possible points remaining per driver
- Points gap to leader with races remaining

**Season Replay**
- Replay any historical F1 season through the simulator
- "What if Senna hadn't crashed at Suzuka 1989?" style scenarios
- Uses Ergast historical data back to 2003

---

## Future Ideas (Unscheduled)

- **ML chip advisor**: replace rules with a model trained on historical chip outcomes
- **Multi-user leagues**: leaderboard for groups of friends using the tool together
- **Push notifications**: "Race starts in 1 hour — set your DRS Boost" reminder
- **Price prediction model**: predict next week's price changes using xP vs current price
- **Mobile-optimised view**: PWA with offline support for race weekends

---

*Roadmap version: 1.0 | Last updated: March 2026*
