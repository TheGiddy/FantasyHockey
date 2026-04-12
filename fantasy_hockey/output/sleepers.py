"""Sleeper and reach analysis.

Compares our projected rank to where players were actually drafted in the
Yahoo league.  A "sleeper" is a player we rank much higher than they were
drafted — good target for next year's draft.  A "reach" is a player
drafted much higher than our projection justifies.
"""

from __future__ import annotations

import pandas as pd

from fantasy_hockey.config import OUTPUTS_DIR, TARGET_SEASON, season_id_to_label


def sleeper_reach_report(board: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Generate sleeper/reach analysis from a draft board with draft_round data.

    Returns (sleepers, reaches, full_report) DataFrames.
    """
    df = board[board["draft_round"].notna()].copy()
    if df.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    # ADP proxy: draft pick number (round * picks_per_round approximation)
    max_round = df["draft_round"].max()
    total_drafted = len(df)
    picks_per_round = total_drafted / max_round if max_round else 8

    df["adp_rank"] = ((df["draft_round"] - 1) * picks_per_round + df["draft_pick"] % picks_per_round).round(0)
    # Simpler: just use draft_pick directly if available
    if "draft_pick" in df.columns and df["draft_pick"].notna().any():
        df["adp_rank"] = df["draft_pick"]

    df["rank_delta"] = df["adp_rank"] - df["rank"]
    # Positive delta = sleeper (drafted later than our rank)
    # Negative delta = reach (drafted earlier than our rank)

    report_cols = ["rank", "name", "position_code", "team_abbrevs",
                   "draft_round", "adp_rank", "rank_delta", "adjusted_value", "tier"]

    # Filter to available columns
    report_cols = [c for c in report_cols if c in df.columns]

    full_report = df[report_cols].sort_values("rank_delta", ascending=False)

    sleepers = full_report[full_report["rank_delta"] > 15].head(20)
    reaches = full_report[full_report["rank_delta"] < -15].tail(20).sort_values("rank_delta")

    return sleepers, reaches, full_report


def write_sleeper_report(board: pd.DataFrame) -> str | None:
    """Write sleeper/reach CSV and return the path."""
    sleepers, reaches, full = sleeper_reach_report(board)

    if full.empty:
        return None

    season_label = season_id_to_label(TARGET_SEASON)
    path = OUTPUTS_DIR / f"sleepers_reaches_{season_label}.csv"

    with open(path, "w", newline="", encoding="utf-8") as f:
        f.write("=== SLEEPERS (Drafted Later Than Projected) ===\n")
        sleepers.to_csv(f, index=False)
        f.write("\n\n=== REACHES (Drafted Earlier Than Projected) ===\n")
        reaches.to_csv(f, index=False)
        f.write("\n\n=== FULL REPORT ===\n")
        full.to_csv(f, index=False)

    return str(path)
