"""Rookie handling for players with limited NHL history.

Players with fewer than MIN_CAREER_GP games across the baseline seasons
don't have enough data for reliable per-game rate projections.  We assign
them a position-specific "rookie baseline" derived from the average
first-year production of NHL players, then blend with whatever limited
data they do have.

Notable prospects can be manually overridden via PROSPECT_OVERRIDES.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from fantasy_hockey.projections.rates import SKATER_RATE_MAP, GOALIE_RATE_MAP

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Players with fewer than this many GP across the baseline window get
# rookie treatment (blended with rookie prior).
MIN_CAREER_GP: int = 50

# Average per-game rates for a "typical" NHL rookie by position.
# These are approximate based on historical rookie averages.
# Format: {rate_column: value}
ROOKIE_SKATER_RATES: dict[str, dict[str, float]] = {
    "C": {
        "goals_pg": 0.18, "assists_pg": 0.28, "pim_pg": 0.35,
        "ppp_pg": 0.08, "sog_pg": 1.8, "hits_pg": 1.2, "blocks_pg": 0.8,
    },
    "L": {
        "goals_pg": 0.18, "assists_pg": 0.25, "pim_pg": 0.40,
        "ppp_pg": 0.07, "sog_pg": 1.9, "hits_pg": 1.5, "blocks_pg": 0.7,
    },
    "R": {
        "goals_pg": 0.18, "assists_pg": 0.25, "pim_pg": 0.40,
        "ppp_pg": 0.07, "sog_pg": 1.9, "hits_pg": 1.5, "blocks_pg": 0.7,
    },
    "D": {
        "goals_pg": 0.06, "assists_pg": 0.18, "pim_pg": 0.40,
        "ppp_pg": 0.05, "sog_pg": 1.5, "hits_pg": 1.8, "blocks_pg": 1.5,
    },
}

ROOKIE_GOALIE_RATES: dict[str, float] = {
    "wins_pg": 0.45,
    "sho_pg": 0.04,
}
ROOKIE_GOALIE_SVPCT: float = 0.905

# Projected GP for a rookie (conservative — not all rookies are starters).
ROOKIE_GP: int = 55
ROOKIE_GS_GOALIE: int = 30

# Manual overrides for notable prospects entering the NHL.
# Add players you're tracking who are expected to play next season.
# Format: {"Name": {"position": "C", rate overrides...}}
PROSPECT_OVERRIDES: dict[str, dict] = {
    # Example:
    # "Macklin Celebrini": {
    #     "position": "C",
    #     "projected_gp": 78,
    #     "goals_pg": 0.30,
    #     "assists_pg": 0.35,
    # },
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def tag_rookies(proj: pd.DataFrame, rates: pd.DataFrame) -> pd.DataFrame:
    """Add an ``is_rookie`` flag and rookie-prior blend to skater projections.

    Parameters
    ----------
    proj : DataFrame
        Output from ``project_skaters`` — one row per player with rate columns.
    rates : DataFrame
        Per-game rates with ``player_id``, ``games_played``, ``season_id``.
    """
    # Compute total career GP across baseline
    career_gp = rates.groupby("player_id")["games_played"].sum().rename("career_gp")
    proj = proj.merge(career_gp, on="player_id", how="left")
    proj["career_gp"] = proj["career_gp"].fillna(0)
    proj["is_rookie"] = proj["career_gp"] < MIN_CAREER_GP

    rate_cols = list(SKATER_RATE_MAP.keys())

    for idx, row in proj[proj["is_rookie"]].iterrows():
        pos = row.get("position_code", "C")
        rookie_rates = ROOKIE_SKATER_RATES.get(pos, ROOKIE_SKATER_RATES["C"])

        # Blend: weight observed data by career_gp, rookie prior by (MIN_CAREER_GP - career_gp)
        gp = row["career_gp"]
        obs_weight = gp / MIN_CAREER_GP
        prior_weight = 1 - obs_weight

        for rc in rate_cols:
            observed = row[rc]
            prior = rookie_rates.get(rc, 0)
            proj.at[idx, rc] = obs_weight * observed + prior_weight * prior

        # Adjust GP projection downward for rookies
        if row["projected_gp"] > ROOKIE_GP and gp < 30:
            proj.at[idx, "projected_gp"] = ROOKIE_GP

    return proj


def add_prospect_overrides(proj: pd.DataFrame) -> pd.DataFrame:
    """Add manually specified prospects who aren't in the NHL data yet.

    These are players you're watching who will enter the league next season.
    Configure via ``PROSPECT_OVERRIDES`` in this file.
    """
    if not PROSPECT_OVERRIDES:
        return proj

    rate_cols = list(SKATER_RATE_MAP.keys())
    new_rows = []

    for name, override in PROSPECT_OVERRIDES.items():
        pos = override.get("position", "C")
        base_rates = ROOKIE_SKATER_RATES.get(pos, ROOKIE_SKATER_RATES["C"])

        row = {
            "player_id": hash(name) % 100000 + 900000,  # synthetic ID
            "skater_full_name": name,
            "position_code": pos,
            "team_abbrevs": override.get("team", "???"),
            "projected_gp": override.get("projected_gp", ROOKIE_GP),
            "total_gp": 0,
            "is_rookie": True,
            "career_gp": 0,
        }
        for rc in rate_cols:
            row[rc] = override.get(rc, base_rates.get(rc, 0))

        # Compute season totals
        for rc in rate_cols:
            total_col = rc.replace("_pg", "")
            row[total_col] = round(row[rc] * row["projected_gp"], 1)

        new_rows.append(row)

    if new_rows:
        new_df = pd.DataFrame(new_rows)
        # Align columns
        for col in proj.columns:
            if col not in new_df.columns:
                new_df[col] = np.nan
        proj = pd.concat([proj, new_df[proj.columns]], ignore_index=True)

    return proj
