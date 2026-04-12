"""Compute per-game rates for every fantasy-relevant category.

One row per (playerId, seasonId) with rate columns like ``goals_pg``,
``assists_pg``, etc.  These rates are the inputs to the projection model.
"""

from __future__ import annotations

import pandas as pd


# ---------------------------------------------------------------------------
# Skater rates
# ---------------------------------------------------------------------------

# Map from our rate column name → the raw counting stat column in the
# ingested data (snake_case after normalisation).
SKATER_RATE_MAP: dict[str, str] = {
    "goals_pg": "goals",
    "assists_pg": "assists",
    "pim_pg": "penalty_minutes",
    "ppp_pg": "pp_points",
    "sog_pg": "shots",
    "hits_pg": "hits",
    "blocks_pg": "blocked_shots",
}

# Columns carried through as-is (not rate-converted).
SKATER_META_COLS: list[str] = [
    "player_id",
    "season_id",
    "skater_full_name",
    "position_code",
    "team_abbrevs",
    "games_played",
    "time_on_ice_per_game",
]


def skater_rates(skaters: pd.DataFrame) -> pd.DataFrame:
    """Return a dataframe with per-game rates for each skater-season.

    Players with 0 GP in a season are dropped (no meaningful rate).
    """
    df = skaters[skaters["games_played"] > 0].copy()

    for rate_col, raw_col in SKATER_RATE_MAP.items():
        df[rate_col] = df[raw_col] / df["games_played"]

    keep = SKATER_META_COLS + list(SKATER_RATE_MAP.keys())
    return df[keep].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Goalie rates
# ---------------------------------------------------------------------------

# Goalies are trickier: wins and shutouts are counted per game, but SV%
# is already a rate.  We carry wins_pg and sho_pg as rates, and SV%
# as-is (it will be weighted by games started during projection).
GOALIE_RATE_MAP: dict[str, str] = {
    "wins_pg": "wins",
    "sho_pg": "shutouts",
}

GOALIE_META_COLS: list[str] = [
    "player_id",
    "season_id",
    "goalie_full_name",
    "team_abbrevs",
    "games_played",
    "games_started",
    "save_pct",
    "goals_against_average",
]


def goalie_rates(goalies: pd.DataFrame) -> pd.DataFrame:
    """Return a dataframe with per-game rates for each goalie-season.

    Uses games_started as the denominator for wins and shutouts (not GP),
    since those stats only accumulate when a goalie starts.
    """
    df = goalies[goalies["games_started"] > 0].copy()

    for rate_col, raw_col in GOALIE_RATE_MAP.items():
        df[rate_col] = df[raw_col] / df["games_started"]

    keep = GOALIE_META_COLS + list(GOALIE_RATE_MAP.keys())
    return df[keep].reset_index(drop=True)
