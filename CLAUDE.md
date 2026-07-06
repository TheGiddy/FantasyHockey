# FantasyHockey

Python draft prediction tool for Yahoo fantasy hockey. Ranks players for the upcoming draft, identifies sleepers vs ADP, and computes keeper values.

## League
- **Yahoo ID:** 465.l.2337 — "Winnipeg Jets Adventuring Comp", 8 teams
- **Format:** Weekly H2H, 10 categories: G, A, PIM, PPP, SOG, HIT, BLK + W, SV%, SHO
- **Roster:** 3C, 3LW, 3RW, 5D, 2G, 5 BN, 1 IR, 2 IR+ (21 draftable slots)

## Keeper rules
- Keep 2 rounds earlier than draft round (R8 → kept at R6)
- R1–R3 picks cannot be kept
- Waiver pickups: fixed R12 keeper round (resets regardless of original round)
- Deadline: **March 15** — acquisitions after this date are not keeper-eligible

## Critical: secrets
`oauth2.json` at repo root contains OAuth credentials — **never commit this file** (already gitignored).

## Model
- Marcel projections: 3-year weighted (1x/3x/5x) with regression to position mean
- Breakout adjustment: reliability floor 0.70 for young/improving players
- Multi-position bonus: +0.25 per extra Yahoo-eligible position
- Excludes COVID seasons (2019-20, 2020-21)
- Config in `config.py` (MY_TEAM_NAME = "Twin Daddy")

## Data sources
- NHL: `https://api-web.nhle.com/v1` and `https://api.nhle.com/stats/rest/en`
- Yahoo: `yahoo_fantasy_api` library
