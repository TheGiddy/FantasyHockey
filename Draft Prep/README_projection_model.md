# Fantasy Hockey Projection Model — Code Package & Thought Process
*Session artifacts, 2026-07-05. Companion to KeeperLeague_2026-27_Context.md*

## Files
- `projection_model_v1.py` — the model that produced the projections table. Self-contained; embedded player data; run with `python3 projection_model_v1.py > projections.md`
- `fetch_nhl_data_v2.py` — data fetcher for v2, to run in Claude Code at home (needs open network). Pulls NHL stats API reports (summary, realtime hits/blocks, TOI splits, PP, penalties, goalies) + MoneyPuck xG/GSAx CSVs into `./data/`

## v1 thought process (what it does and why)

**Goal:** rank ~95 draft-relevant players by projected 2026-27 value in an 8-team H2H league with cats G/A/PIM/PPP/SOG/HIT/BLK (+ W/SV%/SHO for goalies).

**Design decisions:**
1. **Base = actual 25-26 category lines** extracted from the league's Yahoo player list, because Yahoo's season rank already encodes the league's exact weighting. Generic fantasy ranks mislead here (e.g., Heiskanen: top-12 D in standard leagues, #73 in this format).
2. **Two age curves, not one.** Offensive stats (G/A/PPP/SOG) peak ~24-28 and decay ~3%/yr through the early 30s, steeper after 34. Physical stats (PIM/HIT/BLK) are usage/personality-driven and decay far more slowly (~3% total through early 30s). Defensemen's offensive peak shifted one year later. This split is the core insight for a banger-weighted league: physical specialists (Cozens, Wilson, Zadorov, Weegar) hold value into their 30s while finesse scorers fade.
3. **Shooting-% regression handled qualitatively** via a deployment multiplier + note rather than a formal career-sh% pull (didn't have career data in-session). Flags: Geekie 21.5% and Stamkos 20.4%-at-36 regress down; Pastrnak (29G on 261 SOG), Meier (24G on 269), M. Tkachuk and Rantanen (injury-suppressed) regress up.
4. **Deployment multipliers, hand-coded** (0.90-1.30): age-leap candidates (Schaefer 1.12, Carlsson 1.12, Bedard 1.10, Sennecke 1.10, Fantilli 1.08), GP-recovery (Cooley 1.30 for 54→78 GP), injury bounce-back (Matthews 1.18), age-cliff fades (Ovechkin 0.90, Tavares/Josi/E. Karlsson 0.92, Crosby 0.93, Panarin 0.95).
5. **Value = sum of z-scores across the 7 skater cats** within the projected pool. Z-sum is the standard roto/cats valuation; it makes a 339-hit season and a 45-goal season commensurable.
6. **Goalies deliberately NOT modeled.** Year-over-year goalie variance (team defense, workload splits, sh% luck) swamps age curves; a numeric projection would be false precision. Qualitative guidance instead: draft locked starters on structured teams; GSAx is the v2 fix.

**Known limitations (be honest with yourself on draft day):**
- No xG/TOI/zone-start inputs (sandbox network blocked NHL API) — deployment effects are my judgment, not data
- Carlsson/Cooley/Holloway baselines estimated (outside visible top-119 screenshots)
- GP not modeled except Cooley; injury risk lives in notes only
- Single-season base = noisy; a proper model blends 3 seasons (weights ~55/30/15) — v2 item
- ±15% honest error bar on any individual line

## v2 — BUILT (2026-07-05, Claude Code at home)
- `fetch_nhl_data_v2.py` extended: 3 seasons (2023-24..2025-26) of skater summary/realtime/timeonice/powerplay/penalties/bios + goalie summary/advanced/bios, 5 seasons of sh% history (2018-19..2022-23), MoneyPuck skaters/goalies x3 → 39 CSVs in `./data/`
- `projection_model_v2.py` — run `python projection_model_v2.py` → `./output/projections_v2.md` + skater/goalie CSVs
  - 3-season weighted per-60 (1/3/5, TOI-weighted) × projected TOI (0.7 weighted + 0.3 last) × projected GP (share regressed to 92%)
  - Goals = 50/50 (proj SOG × regressed sh%) + (weighted ixG/60 × finishing [G/xG, clipped 0.8-1.3]); sh% = 0.55 recent-regressed + 0.45 career-regressed, position priors from live league rates
  - PPP = PP-specific per-60 × projected PP TOI (deployment 50/50 weighted/last)
  - v1's two age curves kept verbatim; breakout blend = last-season P/60 > 1.2× *prior-seasons-only* P/60 (NOT vs the 1/3/5 average — that's majority last-season already and never triggers), age ≤ 26, GP ≥ 40 → 50% tilt of offensive rates to last season
  - Goalies: SV% = league mean + shrink×(0.6 raw dev + 0.4 GSAx/shot); starts share 0.55 last + 0.45 weighted; W/SHO rates regressed
  - Keeper overlay from context file (definite keeps + coin-flip "keep?") baked into output; "available only" table = actual draft pool
- Data notes: NHL stats API pages can duplicate rows at page boundaries (dedupe on playerId per season); TOI fields are seconds; MoneyPuck merges cleanly on NHL playerId
- Findings vs v1: Hellebuyck fine (G4 overall — Yahoo list artifact); Carlsson's low format rank confirmed by data (no bangers); Gauthier/Cooley sh% regression is real (ixG well below goals)

## Schedule module (2026-07-19)
- `fetch_schedule.py` → `data/schedule_20262027.csv` (full 2026-27 slate from api-web weekly endpoint; 1,344 games, 84/team, no Olympic break)
- `analyze_schedule.py` → `data/schedule_team_metrics.csv` + `output/schedule_analysis.md`: per-team off-night games (Mon/Wed/Fri/Sun), streamability (each game weighted by share of league idle that night), B2B sets (backup-goalie games floor), perfect weeks, and games per league playoff week
- League playoff weeks ≠ Yahoo default (we run a week earlier; 2025-26 was Mar 16–Apr 5). Projected 2027 dates in `PLAYOFF_WEEKS` (R1 Mar 15–21, R2 Mar 22–28, F Mar 29–Apr 4) — **update when Yahoo posts the real calendar**
- `build_draft_board.py` picks up the metrics CSV automatically → OffN/FinW columns (+ B2B for goalies) as draft tiebreakers; deliberately NOT in the z-sum (talent first, calendar as tiebreak)
- Key 2026-27 facts: COL 40 / NYR 39 / WSH+UTA 38 off-nights vs NSH 20 (18-game usable-start spread); PIT 15 B2Bs vs VGK/CGY 8; under OUR playoff dates MIN has the dream finals week (4g, all off-nights), WSH leads total playoff volume (12g)

## v2 roadmap (original, at home, Claude Code, open network)
1. Run `fetch_nhl_data_v2.py` → `./data/*.csv`
2. Replace embedded lines with 3-season weighted per-60 rates × projected TOI (the single biggest accuracy gain)
3. PPP: model as PP1-share × team PP quality using the powerplay report's PP TOI
4. Goals: blend ixG/60 (MoneyPuck) with career sh% — formalizes the regression calls
5. HIT/BLK/PIM: per-60 rates × projected TOI; split PIM into majors (sticky) vs minors (noise) if fight data available
6. Goalies: GSAx/60 (MoneyPuck) + projected start share; W ≈ starts × team strength
7. Re-run z-sum valuation, but weight categories by the league's historical weekly closeness (a cat you lose 20-80 anyway is worth less than a coin-flip cat)
8. Keeper overlay: subtract kept players (see context file KEEPS/FALLS) from the pool before computing replacement level — replacement level, not raw value, is what a draft pick is worth

## Session decision log (compressed)
- Keepers finalized: Gauthier/Dostal R19, Carlsson/LaCombe R12, Guenther R10, Cooley R16 (acq. for Raddysh), Cozens R15 (#17 format!), Holloway R7
- Key data findings: Cozens #17, Heiskanen only #73, Wedgewood #9, Suzuki #8, Celebrini #3, Matthews #119/pre-rank 17 (buy-low), Dostal outside top 175 (G plan needed), Hellebuyck absent (investigate)
- Keeper analysis corrected twice: (1) "kept with earlier pick" rule expands keeps; (2) full CSV × pick-inventory cross-check. Ground truth lives in the context file
- Roster diagnosis: 6th place despite 5 breakouts = skill-heavy shape donating PIM/HIT/BLK; draft priority = multi-cat bangers + physical D
- Strategy discoveries: spare R8/R8/R9 can keep acquired rd-12 players (Raddysh/Swayman class); linear draft + traded-slot rule means Autodraft's and ER's draw positions affect TD's doubled rounds; trade before draw to be slot-proof
