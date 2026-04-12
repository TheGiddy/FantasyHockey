"""Draft ranker: combines z-score value with position scarcity and keeper math.

Outputs a final draft board with:
- Overall rank (by total fantasy value)
- Position rank (C1, C2, ... LW1, LW2, ... D1, D2, ... G1, G2, ...)
- Tier (groups of players with similar value, for quick "grab anyone in this tier")
- Keeper value (for leagues with keeper rules)
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from fantasy_hockey.config import KEEPERS


# ---------------------------------------------------------------------------
# Position scarcity bonus
# ---------------------------------------------------------------------------

# In a 3C/3LW/3RW/5D/2G league, defensemen who produce are scarce.
# We give a small boost to players at thinner positions.
POSITION_SCARCITY_BONUS: dict[str, float] = {
    "C": 0.0,
    "L": 0.0,    # LW
    "R": 0.0,    # RW
    "D": 0.15,   # defensemen are scarcer producers
    "G": 0.0,    # goalies already scaled in zscore.unified_rankings
}

# Multi-position eligibility bonus.  Players who can fill multiple roster
# slots are more valuable because they give roster flexibility on draft day
# and during the season.  Bonus per extra eligible position beyond 1.
MULTI_POSITION_BONUS_PER: float = 0.25


def apply_position_scarcity(rankings: pd.DataFrame) -> pd.DataFrame:
    """Add position-scarcity and multi-position eligibility bumps to total_value."""
    df = rankings.copy()
    df["scarcity_bonus"] = df["position_code"].map(POSITION_SCARCITY_BONUS).fillna(0.0)

    # Multi-position bonus: num_positions is set by projected_keepers for
    # rostered players.  Default to 1 (single position) if not present.
    if "num_positions" in df.columns:
        extra_pos = (df["num_positions"].fillna(1).astype(int) - 1).clip(lower=0)
        df["multi_pos_bonus"] = extra_pos * MULTI_POSITION_BONUS_PER
    else:
        df["multi_pos_bonus"] = 0.0

    df["adjusted_value"] = df["total_value"] + df["scarcity_bonus"] + df["multi_pos_bonus"]
    df = df.sort_values("adjusted_value", ascending=False).reset_index(drop=True)
    df["rank"] = range(1, len(df) + 1)
    return df


# ---------------------------------------------------------------------------
# Tier assignment
# ---------------------------------------------------------------------------

def assign_tiers(df: pd.DataFrame, value_col: str = "adjusted_value", gap_pct: float = 0.10) -> pd.DataFrame:
    """Group players into tiers based on natural breaks in value.

    A new tier starts when the value drop from one player to the next exceeds
    ``gap_pct`` of the standard deviation of values in the draftable pool.
    """
    df = df.copy()
    if len(df) == 0:
        df["tier"] = []
        return df

    values = df[value_col].values
    threshold = np.std(values) * gap_pct

    tiers = [1]
    for i in range(1, len(values)):
        if values[i - 1] - values[i] > threshold:
            tiers.append(tiers[-1] + 1)
        else:
            tiers.append(tiers[-1])
    df["tier"] = tiers
    return df


# ---------------------------------------------------------------------------
# Position ranks
# ---------------------------------------------------------------------------

def add_position_rank(df: pd.DataFrame) -> pd.DataFrame:
    """Add a ``position_rank`` column like C1, C2, D1, D2, G1, etc."""
    df = df.copy()
    df["position_rank"] = (
        df.groupby("position_code").cumcount() + 1
    )
    df["position_rank_label"] = df["position_code"] + df["position_rank"].astype(str)
    return df


# ---------------------------------------------------------------------------
# Keeper value
# ---------------------------------------------------------------------------

def add_keeper_value(
    df: pd.DataFrame,
    draft_results: list[dict] | None = None,
) -> pd.DataFrame:
    """Compute keeper surplus value.

    Keeper surplus = player's overall rank - their keeper round (prior draft
    round - ``KEEPERS.rounds_earlier``).  Higher surplus = better keeper.

    Uses ``draft_round`` column if already present on *df* (from Yahoo name
    matching).  Falls back to *draft_results* list if provided.
    Players drafted in locked rounds get keeper_eligible = False.
    """
    df = df.copy()

    # If draft_round not already on the frame, try to add from draft_results
    if "draft_round" not in df.columns:
        df["draft_round"] = np.nan
    if "draft_pick" not in df.columns:
        df["draft_pick"] = np.nan

    if draft_results is not None and df["draft_round"].isna().all():
        draft_map = {d["player_id"]: d["round"] for d in draft_results}
        df["draft_round"] = df["player_id"].map(draft_map)

    # Keeper eligibility
    df["keeper_eligible"] = True
    df.loc[df["draft_round"].isin(KEEPERS.locked_rounds), "keeper_eligible"] = False
    # Undrafted players can't be kept via this mechanism
    df.loc[df["draft_round"].isna(), "keeper_eligible"] = False

    df["keeper_round"] = np.nan
    df["keeper_surplus"] = np.nan

    has_round = df["draft_round"].notna() & df["keeper_eligible"]
    if has_round.any():
        # Keeper round = draft_round - rounds_earlier (minimum round 1)
        df.loc[has_round, "keeper_round"] = (
            df.loc[has_round, "draft_round"] - KEEPERS.rounds_earlier
        ).clip(lower=1)

        # Keeper surplus: positive means the player is worth more than
        # their keeper cost.  We compare their projected rank to the
        # "pick number" their keeper round represents.
        max_round = df["draft_round"].max()
        picks_per_round = len(df[df["draft_round"].notna()]) / max_round if max_round else 21
        df.loc[has_round, "keeper_surplus"] = (
            df.loc[has_round, "keeper_round"] * picks_per_round
            - df.loc[has_round, "rank"]
        )

    return df


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------

def build_draft_board(
    rankings: pd.DataFrame,
    draft_results: list[dict] | None = None,
) -> pd.DataFrame:
    """Run the full ranking pipeline: scarcity → tiers → position rank → keeper value."""
    df = apply_position_scarcity(rankings)
    df = assign_tiers(df)
    df = add_position_rank(df)
    df = add_keeper_value(df, draft_results)
    return df
