"""Goalie projection model.

Similar Marcel-style approach to the skater model, but tailored for goalie
stats:

- Wins and shutouts are projected as rate * projected games started.
- SV% is a weighted average across seasons, weighted by games started
  (so a 60-GS season counts far more than a 10-GS season).
- GP/GS projection regresses toward a starter baseline (~55 GS) or a
  backup baseline (~25 GS) depending on prior usage.
"""

from __future__ import annotations

import pandas as pd
import numpy as np

from fantasy_hockey.config import BASELINE_SEASONS, SEASON_WEIGHTS
from fantasy_hockey.projections.rates import (
    GOALIE_RATE_MAP,
    goalie_rates,
)

# ---------------------------------------------------------------------------
# Tuning knobs
# ---------------------------------------------------------------------------

# Marcel regression parameters for goalies
RELIABILITY_GS: float = 80.0  # games started for 50/50 reliability

# GS projection targets: starter vs backup
GS_STARTER_TARGET: int = 55
GS_BACKUP_TARGET: int = 25
GS_STARTER_THRESHOLD: int = 35  # avg GS above this → project as starter
GS_REGRESS_WEIGHT: float = 0.3

# League-average SV% for regression
LEAGUE_AVG_SVPCT: float = 0.905

# Age curve for goalies (flatter peak, later decline than skaters)
GOALIE_AGE_CURVE: dict[int, float] = {
    20: 0.92, 21: 0.94, 22: 0.96, 23: 0.98, 24: 0.99,
    25: 1.00, 26: 1.01, 27: 1.02, 28: 1.02, 29: 1.01,
    30: 1.00, 31: 1.00, 32: 0.99, 33: 0.98, 34: 0.97,
    35: 0.96, 36: 0.94, 37: 0.92, 38: 0.90, 39: 0.87,
    40: 0.84,
}


# ---------------------------------------------------------------------------
# Projection pipeline
# ---------------------------------------------------------------------------

def project_goalies(
    goalies_raw: pd.DataFrame,
    birth_dates: pd.DataFrame | None = None,
    target_season_start_year: int = 2026,
) -> pd.DataFrame:
    """Return one row per goalie with projected season totals."""
    rates = goalie_rates(goalies_raw)

    proj = _weighted_avg_rates(rates)
    proj = _regress_svpct(proj, rates)
    proj = _project_gs(proj, rates)

    if birth_dates is not None and not birth_dates.empty:
        proj = _apply_age_curve(proj, birth_dates, target_season_start_year)

    # Season totals
    proj["wins"] = (proj["wins_pg"] * proj["projected_gs"]).round(0).astype(int)
    proj["shutouts"] = (proj["sho_pg"] * proj["projected_gs"]).round(1)
    proj["projected_gs"] = proj["projected_gs"].round(0).astype(int)

    return proj.sort_values("wins", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Internal steps
# ---------------------------------------------------------------------------

def _weighted_avg_rates(rates: pd.DataFrame) -> pd.DataFrame:
    """Weighted average of per-game rates (wins_pg, sho_pg) across seasons."""
    rate_cols = list(GOALIE_RATE_MAP.keys())

    rates = rates.copy()
    rates["_weight"] = rates["season_id"].map(SEASON_WEIGHTS).fillna(1.0)
    rates["_total_weight"] = rates["_weight"] * rates["games_started"]

    for rc in rate_cols:
        rates[f"_wr_{rc}"] = rates[rc] * rates["_total_weight"]

    agg = rates.groupby("player_id").agg(
        **{f"_sum_{rc}": (f"_wr_{rc}", "sum") for rc in rate_cols},
        _sum_weight=("_total_weight", "sum"),
    ).reset_index()

    for rc in rate_cols:
        agg[rc] = agg[f"_sum_{rc}"] / agg["_sum_weight"]

    # Most-recent metadata
    latest = rates.loc[rates.groupby("player_id")["season_id"].idxmax()]
    meta = latest[["player_id", "goalie_full_name", "team_abbrevs"]].copy()

    return meta.merge(agg[["player_id"] + rate_cols], on="player_id")


def _regress_svpct(proj: pd.DataFrame, rates: pd.DataFrame) -> pd.DataFrame:
    """Weighted average SV% across seasons, regressed toward league mean."""
    rates = rates.copy()
    rates["_weight"] = rates["season_id"].map(SEASON_WEIGHTS).fillna(1.0)
    rates["_gs_weight"] = rates["_weight"] * rates["games_started"]

    svpct_agg = rates.groupby("player_id").apply(
        lambda g: np.average(g["save_pct"], weights=g["_gs_weight"]),
        include_groups=False,
    ).rename("raw_svpct")

    total_gs = rates.groupby("player_id")["games_started"].sum().rename("total_gs")

    proj = proj.merge(svpct_agg, on="player_id", how="left")
    proj = proj.merge(total_gs, on="player_id", how="left")

    # Reliability-weighted regression toward league avg
    reliability = proj["total_gs"] / (proj["total_gs"] + RELIABILITY_GS)
    proj["save_pct"] = reliability * proj["raw_svpct"] + (1 - reliability) * LEAGUE_AVG_SVPCT

    proj.drop(columns=["raw_svpct"], inplace=True)
    return proj


def _project_gs(proj: pd.DataFrame, rates: pd.DataFrame) -> pd.DataFrame:
    """Project games started: weighted avg of historical GS, regressed to role target."""
    rates = rates.copy()
    rates["_weight"] = rates["season_id"].map(SEASON_WEIGHTS).fillna(1.0)

    gs_agg = rates.groupby("player_id").apply(
        lambda g: np.average(g["games_started"], weights=g["_weight"]),
        include_groups=False,
    ).rename("avg_gs")

    proj = proj.merge(gs_agg, on="player_id", how="left")

    # Determine starter vs backup
    target = np.where(
        proj["avg_gs"] >= GS_STARTER_THRESHOLD,
        GS_STARTER_TARGET,
        GS_BACKUP_TARGET,
    )
    proj["projected_gs"] = (
        (1 - GS_REGRESS_WEIGHT) * proj["avg_gs"]
        + GS_REGRESS_WEIGHT * target
    )
    proj["projected_gs"] = proj["projected_gs"].clip(upper=70)

    proj.drop(columns=["avg_gs"], inplace=True)
    return proj


def _apply_age_curve(
    proj: pd.DataFrame,
    birth_dates: pd.DataFrame,
    target_season_start_year: int,
) -> pd.DataFrame:
    """Apply goalie age-curve to win rate and SV%."""
    bd = birth_dates[["playerId", "birthDate"]].copy()
    bd = bd.rename(columns={"playerId": "player_id", "birthDate": "birth_date"})
    bd["birth_date"] = pd.to_datetime(bd["birth_date"], errors="coerce")

    proj = proj.merge(bd, on="player_id", how="left")

    ref_date = pd.Timestamp(f"{target_season_start_year}-10-01")
    proj["age_next"] = ((ref_date - proj["birth_date"]).dt.days / 365.25).round(0)

    proj["age_factor"] = proj["age_next"].map(GOALIE_AGE_CURVE).fillna(1.0)

    # Apply age factor to rates (not SV% — goalies' SV% aging is flatter
    # and already captured by the regression to league mean)
    proj["wins_pg"] = proj["wins_pg"] * proj["age_factor"]
    proj["sho_pg"] = proj["sho_pg"] * proj["age_factor"]

    proj.drop(columns=["birth_date"], inplace=True)
    return proj
