#!/usr/bin/env python
"""Generate a complete draft board from ingested data.

Run:
    python scripts/generate_draft_board.py
    python scripts/generate_draft_board.py --force        # re-fetch from APIs
    python scripts/generate_draft_board.py --skip-yahoo   # skip Yahoo draft results
    python scripts/generate_draft_board.py --skip-bio     # skip birth-date fetching (no age curves)
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fantasy_hockey.config import BASELINE_SEASONS, season_id_to_label, TARGET_SEASON, MY_TEAM_NAME
from fantasy_hockey.ingest.seasons import ingest_skaters, ingest_goalies, ingest_birth_dates
from fantasy_hockey.projections.skater_model import project_skaters
from fantasy_hockey.projections.goalie_model import project_goalies
from fantasy_hockey.valuation.zscore import skater_zscores, goalie_zscores, unified_rankings
from fantasy_hockey.valuation.ranker import build_draft_board
from fantasy_hockey.projections.rookies import tag_rookies, add_prospect_overrides
from fantasy_hockey.projections.rates import skater_rates
from fantasy_hockey.output.draft_sheet import write_csv, write_html
from fantasy_hockey.output.sleepers import sleeper_reach_report, write_sleeper_report

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")
log = logging.getLogger(__name__)


def main(
    force: bool = False,
    skip_yahoo: bool = False,
    skip_bio: bool = False,
    seasons: tuple[int, ...] | None = None,
):
    seasons = seasons or BASELINE_SEASONS
    target_year = int(str(TARGET_SEASON)[:4])

    log.info("Baseline seasons: %s", [season_id_to_label(s) for s in seasons])
    log.info("Target season: %s", season_id_to_label(TARGET_SEASON))

    # --- Ingest -------------------------------------------------------------
    print("\n[1/6] Ingesting skater data ...")
    skaters_raw = ingest_skaters(seasons, force=force)
    print(f"      {len(skaters_raw)} skater-season rows, {skaters_raw['player_id'].nunique()} unique players")

    print("\n[2/6] Ingesting goalie data ...")
    goalies_raw = ingest_goalies(seasons, force=force)
    print(f"      {len(goalies_raw)} goalie-season rows, {goalies_raw['player_id'].nunique()} unique goalies")

    # --- Birth dates (for age curves) --------------------------------------
    birth_dates = None
    if not skip_bio:
        print("\n[3/6] Fetching birth dates for age curves ...")
        try:
            birth_dates = ingest_birth_dates(skaters_raw, goalies_raw, force=force)
            print(f"      {len(birth_dates)} players with birth dates")
        except Exception as exc:
            log.warning("Birth date fetch failed (%s) — proceeding without age curves", exc)
    else:
        print("\n[3/6] Skipping birth dates (--skip-bio)")

    # --- Projections --------------------------------------------------------
    print("\n[4/7] Projecting skater stats ...")
    skater_proj = project_skaters(skaters_raw, birth_dates, target_year)

    # Rookie handling
    rates_df = skater_rates(skaters_raw)
    skater_proj = tag_rookies(skater_proj, rates_df)
    skater_proj = add_prospect_overrides(skater_proj)
    n_rookies = skater_proj["is_rookie"].sum() if "is_rookie" in skater_proj.columns else 0
    print(f"      {len(skater_proj)} skaters projected ({n_rookies} rookies w/ blended prior)")
    print("      Top 10 by projected goals:")
    print(skater_proj[["skater_full_name", "position_code", "team_abbrevs",
                        "projected_gp", "goals", "assists", "ppp", "sog", "hits", "blocks", "pim"
                        ]].head(10).to_string(index=False))

    print("\n[4/7] Projecting goalie stats ...")
    goalie_proj = project_goalies(goalies_raw, birth_dates, target_year)
    print(f"      {len(goalie_proj)} goalies projected")
    print("      Top 10 by projected wins:")
    print(goalie_proj[["goalie_full_name", "team_abbrevs",
                        "projected_gs", "wins", "save_pct", "shutouts"
                        ]].head(10).to_string(index=False))

    # --- Valuation ----------------------------------------------------------
    print("\n[5/7] Computing z-scores and rankings ...")
    skater_z = skater_zscores(skater_proj)
    goalie_z = goalie_zscores(goalie_proj)
    unified = unified_rankings(skater_z, goalie_z)

    # --- Draft board --------------------------------------------------------
    # Get Yahoo draft results and match to our projections by name
    yahoo_picks_raw = None
    if not skip_yahoo:
        try:
            from fantasy_hockey.data.yahoo_client import YahooClient
            from fantasy_hockey.data.name_match import match_draft_to_projections
            from fantasy_hockey.valuation.projected_keepers import project_keepers

            yc = YahooClient()
            info = yc.league_info()
            print(f"      Yahoo league: {info.name} ({info.num_teams} teams)")

            picks = yc.draft_results(enrich=True)
            if picks:
                yahoo_picks_raw = [
                    {"player_name": p.player_name, "round": p.round, "pick": p.pick}
                    for p in picks
                ]
                print(f"      Loaded {len(yahoo_picks_raw)} draft picks from Yahoo")

                # Match to unified rankings by name
                unified, matched, total = match_draft_to_projections(
                    yahoo_picks_raw, unified, name_col="name"
                )
                print(f"      Matched {matched}/{total} draft picks to projections")

            # --- Projected keepers for NEXT season ----------------------------
            roster_players = yc.all_rosters_with_keeper_eligibility()
            n_eligible = sum(1 for r in roster_players if r.keeper_eligible_next)
            print(f"      Scanned {len(roster_players)} roster players, {n_eligible} keeper-eligible for next year")

            # Need rank on unified before projecting keepers
            unified = unified.sort_values("total_value", ascending=False).reset_index(drop=True)
            unified["rank"] = range(1, len(unified) + 1)

            unified, n_projected = project_keepers(roster_players, unified, name_col="name")
            print(f"      Projected {n_projected} players will be kept next season")

            # Print projected keepers by team
            kept_df = unified[unified["projected_kept"]].sort_values("projected_kept_by")
            if not kept_df.empty:
                print("\n      Projected keepers by team (for NEXT season):")
                for team_name, group in kept_df.groupby("projected_kept_by"):
                    players = ", ".join(
                        f"{r['name']} ({r['position_code']}, R{int(r['next_keeper_round'])})"
                        for _, r in group.iterrows()
                    )
                    print(f"        {team_name}: {players}")

        except Exception as exc:
            log.warning("Yahoo data unavailable (%s)", exc)
            import traceback; traceback.print_exc()

    # Build the final board (keeper analysis uses draft_round from matched data)
    board = build_draft_board(unified, draft_results=None)

    # Also build detailed skater/goalie boards with z-scores
    from fantasy_hockey.valuation.ranker import apply_position_scarcity, assign_tiers, add_position_rank
    sk_board = skater_z.copy()
    sk_board.rename(columns={"skater_full_name": "name"}, inplace=True)
    sk_board["adjusted_value"] = sk_board["total_value"]
    sk_board = assign_tiers(sk_board)
    sk_board = add_position_rank(sk_board)
    sk_board["rank"] = range(1, len(sk_board) + 1)

    gk_board = goalie_z.copy()
    gk_board["adjusted_value"] = gk_board["total_value"]
    gk_board["position_code"] = "G"
    gk_board = assign_tiers(gk_board)
    gk_board = add_position_rank(gk_board)
    gk_board["rank"] = range(1, len(gk_board) + 1)
    # Rename for unified output compatibility
    gk_board.rename(columns={"goalie_full_name": "name"}, inplace=True)

    # --- Sleeper/reach analysis -----------------------------------------------
    sleeper_data = None
    if "draft_round" in board.columns and board["draft_round"].notna().any():
        sleeper_data = sleeper_reach_report(board)
        sleepers, reaches, _ = sleeper_data
        if not sleepers.empty:
            print(f"\n[6/7] Sleeper/reach analysis: {len(sleepers)} sleepers, {len(reaches)} reaches")

    print("\n[7/7] Writing outputs ...")
    csv_path = write_csv(sk_board, gk_board, board)
    html_path = write_html(sk_board, gk_board, board, sleeper_data=sleeper_data)

    if sleeper_data:
        sleeper_path = write_sleeper_report(board)
        if sleeper_path:
            print(f"      Sleepers: {sleeper_path}")

    print(f"\n      CSV:  {csv_path}")
    print(f"      HTML: {html_path}")

    # --- Summary ------------------------------------------------------------
    print("\n=== TOP 25 OVERALL ===")
    top25 = board.head(25)[["rank", "tier", "name", "position_code", "team_abbrevs",
                             "projected_gp", "adjusted_value"]].copy()
    top25["adjusted_value"] = top25["adjusted_value"].round(2)
    print(top25.to_string(index=False))

    print("\n=== TOP 10 GOALIES ===")
    top_g = board[board["position_code"] == "G"].head(10)[
        ["rank", "name", "team_abbrevs", "projected_gp", "adjusted_value"]
    ].copy()
    top_g["adjusted_value"] = top_g["adjusted_value"].round(2)
    print(top_g.to_string(index=False))

    if "projected_kept" in board.columns and board["projected_kept"].any():
        kept = board[board["projected_kept"] == True].copy()
        kept_cols = ["rank", "name", "position_code", "projected_kept_by",
                     "draft_round", "next_keeper_round"]
        kept_cols = [c for c in kept_cols if c in kept.columns]

        # Split into your keepers vs opponents'
        my_name_lower = MY_TEAM_NAME.lower()
        my_kept = kept[kept["projected_kept_by"].str.lower().str.strip() == my_name_lower]
        opp_kept = kept[kept["projected_kept_by"].str.lower().str.strip() != my_name_lower]

        if not my_kept.empty:
            print(f"\n=== YOUR KEEPER CANDIDATES ({len(my_kept)} players) ===")
            print(my_kept[kept_cols].to_string(index=False))

        print(f"\n=== OPPONENT PROJECTED KEEPERS ({len(opp_kept)} players off the board) ===")
        print(opp_kept[kept_cols].to_string(index=False))

        # Show top draftable players (not projected to be kept by opponents)
        available = board[
            (board["projected_kept"] != True) |
            (board["projected_kept_by"].str.lower().str.strip() == my_name_lower)
        ].head(15)
        print("\n=== TOP 15 DRAFTABLE (excluding opponent keepers) ===")
        avail_cols = ["rank", "tier", "name", "position_code", "team_abbrevs",
                      "projected_gp", "adjusted_value"]
        avail_cols = [c for c in avail_cols if c in available.columns]
        available_disp = available[avail_cols].copy()
        available_disp["adjusted_value"] = available_disp["adjusted_value"].round(2)
        print(available_disp.to_string(index=False))

    print("\nDraft board generation complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate fantasy hockey draft board")
    parser.add_argument("--force", action="store_true", help="Re-fetch all data from APIs")
    parser.add_argument("--skip-yahoo", action="store_true", help="Skip Yahoo API")
    parser.add_argument("--skip-bio", action="store_true", help="Skip birth date fetching")
    parser.add_argument("--complete-only", action="store_true",
                        help="Use only the first 2 baseline seasons (skip current/incomplete)")
    args = parser.parse_args()

    seasons = BASELINE_SEASONS[:2] if args.complete_only else None
    main(force=args.force, skip_yahoo=args.skip_yahoo, skip_bio=args.skip_bio, seasons=seasons)
