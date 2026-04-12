"""Z-score valuation engine.

Converts raw projected totals into z-scores relative to the draftable
player pool.  Each fantasy category gets its own z-score, and a player's
overall value is the sum of their z-scores across all categories.

Special handling:
- SV% is a rate stat: a goalie with 0.930 SV% in 60 GS is more valuable
  than 0.930 in 20 GS because the *volume* of saves stabilises the team's
  category.  We still z-score the raw SV%, but weight it by projected GS
  when blending into the final value.
- Goalies only contribute to 3 cats; skaters to 7.  To avoid goalies being
  undervalued, we compute z-scores within separate pools and then scale so
  that the best goalie and best skater have comparable total value.
"""

from __future__ import annotations

import pandas as pd
import numpy as np

from fantasy_hockey.config import (
    DRAFTABLE_PLAYER_POOL,
    SKATER_CATEGORIES,
    GOALIE_CATEGORIES,
)


# ---------------------------------------------------------------------------
# Skater z-scores
# ---------------------------------------------------------------------------

# Map from category short name → projected total column name in the skater
# projection output.
_SKATER_TOTAL_MAP: dict[str, str] = {
    "G": "goals",
    "A": "assists",
    "PIM": "pim",
    "PPP": "ppp",
    "SOG": "sog",
    "HIT": "hits",
    "BLK": "blocks",
}


def skater_zscores(
    proj: pd.DataFrame,
    pool_size: int | None = None,
) -> pd.DataFrame:
    """Add per-category z-score columns and a ``total_value`` column.

    Only the top *pool_size* skaters (by raw points = G + A) are used to
    compute the z-score mean/std, so replacement-level is realistic.
    """
    if pool_size is None:
        # Rough: total draftable minus ~24 goalie slots (12 teams * 2 G)
        pool_size = DRAFTABLE_PLAYER_POOL - 24

    df = proj.copy()

    # Determine replacement-level pool (top N by projected points)
    df["_raw_pts"] = df["goals"] + df["assists"]
    cutoff = df["_raw_pts"].nlargest(pool_size).iloc[-1] if len(df) >= pool_size else df["_raw_pts"].min()
    pool = df[df["_raw_pts"] >= cutoff]

    for cat, col in _SKATER_TOTAL_MAP.items():
        mean = pool[col].mean()
        std = pool[col].std()
        if std == 0 or np.isnan(std):
            df[f"z_{cat}"] = 0.0
        else:
            df[f"z_{cat}"] = (df[col] - mean) / std

    z_cols = [f"z_{cat}" for cat in _SKATER_TOTAL_MAP]
    df["total_value"] = df[z_cols].sum(axis=1)

    df.drop(columns=["_raw_pts"], inplace=True)
    return df.sort_values("total_value", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Goalie z-scores
# ---------------------------------------------------------------------------

_GOALIE_TOTAL_MAP: dict[str, str] = {
    "W": "wins",
    "SVPCT": "save_pct",
    "SHO": "shutouts",
}


def goalie_zscores(
    proj: pd.DataFrame,
    pool_size: int = 24,
) -> pd.DataFrame:
    """Add per-category z-scores for goalies.

    ``pool_size`` defaults to ~24 (2 goalies * 12 teams).
    """
    df = proj.copy()

    # Pool = top N goalies by projected wins
    pool = df.nlargest(pool_size, "wins")

    for cat, col in _GOALIE_TOTAL_MAP.items():
        mean = pool[col].mean()
        std = pool[col].std()
        if std == 0 or np.isnan(std):
            df[f"z_{cat}"] = 0.0
        else:
            df[f"z_{cat}"] = (df[col] - mean) / std

    z_cols = [f"z_{cat}" for cat in _GOALIE_TOTAL_MAP]
    df["total_value"] = df[z_cols].sum(axis=1)

    return df.sort_values("total_value", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Unified ranking
# ---------------------------------------------------------------------------

def unified_rankings(
    skater_z: pd.DataFrame,
    goalie_z: pd.DataFrame,
) -> pd.DataFrame:
    """Combine skater and goalie z-scored projections into a single ranked list.

    Scales goalie values so that the top goalie's value is comparable to the
    top skater's value (roughly — goalies dominate 3 cats, skaters 7, but a
    league-winning team needs good goalies).

    The scaling factor: top_skater_value / top_goalie_value * (3/7) gives
    goalies credit for dominating fewer categories.  We then multiply by a
    scarcity boost (there are far fewer fantasy-relevant goalies).
    """
    sk = skater_z.copy()
    gk = goalie_z.copy()

    # Scale goalie values to be comparable
    if len(gk) > 0 and gk["total_value"].max() != 0:
        top_sk_val = sk["total_value"].max() if len(sk) > 0 else 1.0
        top_gk_val = gk["total_value"].max()

        # goalies cover 3/10 categories but elite goalies are scarce
        goalie_scale = (top_sk_val / top_gk_val) * (3 / 7) * 1.2
        gk["total_value"] = gk["total_value"] * goalie_scale

    # Build unified frame
    sk_out = sk[["player_id", "skater_full_name", "position_code", "team_abbrevs",
                  "projected_gp", "total_value"]].copy()
    sk_out.rename(columns={"skater_full_name": "name"}, inplace=True)
    sk_out["player_type"] = "S"

    gk_out = gk[["player_id", "goalie_full_name", "team_abbrevs",
                  "projected_gs", "total_value"]].copy()
    gk_out.rename(columns={"goalie_full_name": "name", "projected_gs": "projected_gp"}, inplace=True)
    gk_out["position_code"] = "G"
    gk_out["player_type"] = "G"

    combined = pd.concat([sk_out, gk_out], ignore_index=True)
    combined = combined.sort_values("total_value", ascending=False).reset_index(drop=True)
    combined["rank"] = range(1, len(combined) + 1)

    return combined
