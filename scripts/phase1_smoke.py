#!/usr/bin/env python
"""Phase 1 smoke test — validate that the ingest pipeline works end-to-end.

Run:
    python -m scripts.phase1_smoke          (from repo root)
    python scripts/phase1_smoke.py          (also fine)

What it does:
1. Pulls skater + goalie stats for the first two *complete* baseline seasons
   (skips the current in-progress season if it isn't finished yet).
2. Prints row counts and top-10 sanity checks.
3. Optionally connects to Yahoo and prints league settings for verification.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Make sure the repo root is on sys.path so we can import fantasy_hockey
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fantasy_hockey.config import BASELINE_SEASONS, season_id_to_label
from fantasy_hockey.ingest.seasons import ingest_goalies, ingest_skaters

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")
log = logging.getLogger(__name__)


def main(force: bool = False, skip_yahoo: bool = False, seasons: tuple[int, ...] | None = None):
    if seasons is None:
        # Default: use only the first two complete seasons (skip current/incomplete)
        seasons = BASELINE_SEASONS[:2]
        log.info(
            "Using first 2 baseline seasons for smoke test: %s",
            [season_id_to_label(s) for s in seasons],
        )

    # --- Skaters -----------------------------------------------------------
    print("\n=== SKATERS ===")
    skaters = ingest_skaters(seasons, force=force)
    print(f"  Total skater-season rows: {len(skaters)}")
    print(f"  Columns: {list(skaters.columns)}")
    print(f"  Unique players: {skaters['player_id'].nunique()}")
    print(f"  Seasons present: {sorted(skaters['season_id'].unique())}")

    # Top 10 by points (most recent season)
    latest = skaters[skaters["season_id"] == max(seasons)]
    top_points = latest.nlargest(10, "points")[
        ["skater_full_name", "position_code", "team_abbrevs", "games_played",
         "goals", "assists", "points", "pp_points", "shots", "penalty_minutes"]
    ]
    print("\n  Top 10 skaters by points (most recent complete season):")
    print(top_points.to_string(index=False))

    # Verify hits/blocks came through from the realtime merge
    if "hits" in skaters.columns and "blocked_shots" in skaters.columns:
        top_hits = latest.nlargest(5, "hits")[["skater_full_name", "hits", "blocked_shots"]]
        print("\n  Top 5 by hits (verifying realtime merge):")
        print(top_hits.to_string(index=False))
    else:
        print("\n  WARNING: hits/blocked_shots columns missing — realtime merge may have failed")
        print(f"  Available columns: {[c for c in skaters.columns if 'hit' in c or 'block' in c]}")

    # --- Goalies -----------------------------------------------------------
    print("\n=== GOALIES ===")
    goalies = ingest_goalies(seasons, force=force)
    print(f"  Total goalie-season rows: {len(goalies)}")
    print(f"  Unique goalies: {goalies['player_id'].nunique()}")

    latest_g = goalies[goalies["season_id"] == max(seasons)]
    top_goalies = latest_g.nlargest(5, "wins")[
        ["goalie_full_name", "team_abbrevs", "games_played", "games_started",
         "wins", "save_pct", "shutouts", "goals_against_average"]
    ]
    print("\n  Top 5 goalies by wins (most recent complete season):")
    print(top_goalies.to_string(index=False))

    # --- Yahoo (optional) --------------------------------------------------
    if not skip_yahoo:
        print("\n=== YAHOO LEAGUE ===")
        try:
            from fantasy_hockey.data.yahoo_client import YahooClient

            yc = YahooClient()
            info = yc.league_info()
            print(f"  League:     {info.name}")
            print(f"  League ID:  {info.league_id}")
            print(f"  Teams:      {info.num_teams}")
            print(f"  Week:       {info.current_week}")
            print(f"  Positions:  {info.roster_positions}")
            print(f"  Categories: {[c.get('display_name', c) for c in info.stat_categories]}")

            # Draft results
            picks = yc.draft_results()
            if picks:
                print(f"\n  Draft picks: {len(picks)} total")
                print(f"  Rounds: {max(p.round for p in picks)}")
                print(f"  First 5: {[(p.round, p.pick, p.player_name) for p in picks[:5]]}")
            else:
                print("  No draft results available (draft may not have happened yet)")

        except Exception as exc:
            print(f"  Yahoo connection failed: {exc}")
            print("  (This is OK — NHL data ingest is the critical path)")

    print("\nPhase 1 smoke test complete. OK")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 1 smoke test")
    parser.add_argument("--force", action="store_true", help="Re-fetch from API even if cached")
    parser.add_argument("--skip-yahoo", action="store_true", help="Skip Yahoo API checks")
    parser.add_argument(
        "--all-seasons", action="store_true",
        help="Use ALL baseline seasons (including current/incomplete)",
    )
    args = parser.parse_args()

    seasons = BASELINE_SEASONS if args.all_seasons else None
    main(force=args.force, skip_yahoo=args.skip_yahoo, seasons=seasons)
