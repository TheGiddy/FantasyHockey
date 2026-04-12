"""Skater projection model.

Projects next-season counting stats for every skater in the baseline data
using a Marcel-style approach:

1. Weighted average of per-game rates across baseline seasons (recent = heavier).
2. Regression toward the position mean — more regression for players with fewer
   GP, less for high-GP veterans.
3. GP projection: weighted average of prior GPs, regressed toward 78.
4. Season totals = projected rate * projected GP.
"""

from __future__ import annotations

import pandas as pd
import numpy as np

from fantasy_hockey.config import BASELINE_SEASONS, SEASON_WEIGHTS
from fantasy_hockey.projections.rates import (
    SKATER_RATE_MAP,
    skater_rates,
)

# ---------------------------------------------------------------------------
# Tuning knobs
# ---------------------------------------------------------------------------

# Marcel regression: we blend a player's observed rate with the position-mean
# rate.  The "reliability" denominator controls how quickly observed data
# overwhelms the prior.  At RELIABILITY_GP games a player gets 50/50.
# Tuned via backtest: 200 works well for most cats; hits are more volatile
# but we use a single value for simplicity.
RELIABILITY_GP: float = 200.0

# Breakout / momentum adjustment for young players.
# If a player is <= BREAKOUT_MAX_AGE and their most recent season's rate
# exceeds the weighted average by > BREAKOUT_THRESHOLD (e.g. 30%), we tilt
# the projection toward the recent rate.  BREAKOUT_BLEND controls how much
# of the gap we close (0 = no adjustment, 1 = fully use recent rate).
BREAKOUT_MAX_AGE: int = 25
BREAKOUT_THRESHOLD: float = 0.20   # 20% improvement triggers adjustment
BREAKOUT_BLEND: float = 0.50       # close 50% of the gap toward recent rate
# Minimum GP in the most recent season to qualify for breakout detection.
BREAKOUT_MIN_RECENT_GP: int = 40
# Minimum reliability for breakout players during regression.  Without this,
# a player with 150 career GP gets reliability ~0.43 and the regression
# replaces 57% of their (breakout-adjusted) rate with the position mean.
# This floor ensures breakout players keep most of their observed signal.
BREAKOUT_RELIABILITY_FLOOR: float = 0.70

# GP projection: blend actual GP toward this target.  A full 82-game season
# is rare; 78 is a reasonable "healthy, everyday" baseline.
GP_REGRESS_TARGET: int = 78

# Weight of the regression target in the GP blend.  Higher = more conservative.
# Tuned via backtest: 0.35 reduces overestimation of injury-prone players
# (e.g. Sprong, Atkinson who played far fewer GP than history suggested).
GP_REGRESS_WEIGHT: float = 0.35

# Age curve — simple multiplicative factor keyed by age-next-season.
# Players outside this table get 1.0 (no adjustment).
# Based on conventional hockey aging curves: peak ~24-27, gradual decline after.
AGE_CURVE: dict[int, float] = {
    18: 0.85, 19: 0.90, 20: 0.94, 21: 0.97, 22: 1.00,
    23: 1.02, 24: 1.03, 25: 1.03, 26: 1.02, 27: 1.01,
    28: 1.00, 29: 0.99, 30: 0.98, 31: 0.97, 32: 0.96,
    33: 0.95, 34: 0.93, 35: 0.91, 36: 0.89, 37: 0.87,
    38: 0.85, 39: 0.82, 40: 0.79, 41: 0.76, 42: 0.73,
}


# ---------------------------------------------------------------------------
# Projection pipeline
# ---------------------------------------------------------------------------

def project_skaters(
    skaters_raw: pd.DataFrame,
    birth_dates: pd.DataFrame | None = None,
    target_season_start_year: int = 2026,
) -> pd.DataFrame:
    """Return one row per player with projected season totals.

    Parameters
    ----------
    skaters_raw : DataFrame
        Multi-season ingested skater data (from ``ingest_skaters``).
    birth_dates : DataFrame, optional
        Must have ``player_id`` and ``birthDate`` columns.  If provided,
        age-curve adjustments are applied.
    target_season_start_year : int
        The calendar year the projected season *starts* in (e.g. 2026 for
        the 2026-27 season).  Used for age calculation.
    """
    rates = skater_rates(skaters_raw)

    # --- Step 1: weighted average rates ------------------------------------
    proj = _weighted_avg_rates(rates)

    # --- Step 1b: breakout adjustment for young improving players ---------
    proj = _breakout_adjustment(proj, rates)

    # --- Step 2: Marcel regression toward position mean --------------------
    proj = _regress_to_position_mean(proj, rates)

    # --- Step 3: GP projection ---------------------------------------------
    proj = _project_gp(proj, rates)

    # --- Step 4: age curve (if birth dates available) ----------------------
    if birth_dates is not None and not birth_dates.empty:
        proj = _apply_age_curve(proj, birth_dates, target_season_start_year)

    # --- Step 5: season totals = rate * GP ---------------------------------
    rate_cols = list(SKATER_RATE_MAP.keys())
    total_col_map = {rc: rc.replace("_pg", "") for rc in rate_cols}

    for rate_col, total_col in total_col_map.items():
        proj[total_col] = proj[rate_col] * proj["projected_gp"]

    # Round totals for readability
    for col in total_col_map.values():
        proj[col] = proj[col].round(1)
    proj["projected_gp"] = proj["projected_gp"].round(0).astype(int)

    return proj.sort_values("goals", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Internal steps
# ---------------------------------------------------------------------------

def _weighted_avg_rates(rates: pd.DataFrame) -> pd.DataFrame:
    """Compute weighted-average per-game rates across seasons."""
    rate_cols = list(SKATER_RATE_MAP.keys())

    # Attach season weight
    rates = rates.copy()
    rates["_weight"] = rates["season_id"].map(SEASON_WEIGHTS).fillna(1.0)
    # Weight each rate by (season_weight * gp) so high-GP seasons dominate
    rates["_total_weight"] = rates["_weight"] * rates["games_played"]

    for rc in rate_cols:
        rates[f"_wr_{rc}"] = rates[rc] * rates["_total_weight"]

    agg = rates.groupby("player_id").agg(
        **{f"_sum_{rc}": (f"_wr_{rc}", "sum") for rc in rate_cols},
        _sum_weight=("_total_weight", "sum"),
    ).reset_index()

    for rc in rate_cols:
        agg[rc] = agg[f"_sum_{rc}"] / agg["_sum_weight"]

    # Carry forward the most-recent-season metadata
    latest_season = rates.loc[rates.groupby("player_id")["season_id"].idxmax()]
    meta = latest_season[["player_id", "skater_full_name", "position_code", "team_abbrevs"]].copy()

    proj = meta.merge(agg[["player_id"] + rate_cols], on="player_id")
    return proj


def _breakout_adjustment(proj: pd.DataFrame, rates: pd.DataFrame) -> pd.DataFrame:
    """Tilt projections toward most recent season for breakout players.

    The standard Marcel weighted average blends 3 seasons, which is great for
    established veterans but undervalues players in the middle of a breakout.
    This step detects players whose most recent season is significantly above
    their weighted average and:
    1. Shifts the weighted-average rates toward the recent season.
    2. Flags them for reduced regression in the next step (via _breakout_gp_bonus).

    Triggers when a player's recent season (>= BREAKOUT_MIN_RECENT_GP) shows
    >= BREAKOUT_THRESHOLD average improvement across key offensive rates.
    """
    rate_cols = list(SKATER_RATE_MAP.keys())

    # Get the most recent season for each player
    most_recent = rates.loc[rates.groupby("player_id")["season_id"].idxmax()].copy()
    most_recent = most_recent[most_recent["games_played"] >= BREAKOUT_MIN_RECENT_GP]

    if most_recent.empty:
        return proj

    # Build a lookup of most-recent-season rates and GP
    recent_lookup = most_recent.set_index("player_id")[rate_cols + ["games_played"]]

    proj["_is_breakout"] = False
    n_breakout = 0
    for idx, row in proj.iterrows():
        pid = row["player_id"]
        if pid not in recent_lookup.index:
            continue

        recent = recent_lookup.loc[pid]

        # Measure improvement across key offensive rates
        key_rates = ["goals_pg", "assists_pg", "ppp_pg", "sog_pg"]
        improvements = []
        for rc in key_rates:
            wavg = row[rc]
            rec = recent[rc]
            if wavg > 0:
                improvements.append((rec - wavg) / wavg)
            elif rec > 0:
                improvements.append(1.0)

        if not improvements:
            continue

        avg_improvement = np.mean(improvements)

        # Also check for steady multi-season upward trend: if a player has
        # 2+ seasons and each season is better than the last, they get credit
        # even if the most-recent-vs-weighted-avg gap is modest.
        if avg_improvement <= BREAKOUT_THRESHOLD:
            player_seasons = rates[rates["player_id"] == pid].sort_values("season_id")
            if len(player_seasons) >= 2:
                recent_two = player_seasons.tail(2)
                prev_goals = recent_two.iloc[0]["goals_pg"]
                curr_goals = recent_two.iloc[1]["goals_pg"]
                if prev_goals > 0 and curr_goals > prev_goals:
                    yoy_improvement = (curr_goals - prev_goals) / prev_goals
                    # A strong year-over-year jump (>25%) in goals with a high
                    # recent absolute rate qualifies as trending up
                    if yoy_improvement > 0.25 and curr_goals > 0.35:
                        avg_improvement = max(avg_improvement, BREAKOUT_THRESHOLD + 0.01)

        if avg_improvement > BREAKOUT_THRESHOLD:
            # Blend rates toward the recent season
            for rc in rate_cols:
                wavg_val = row[rc]
                recent_val = recent[rc]
                proj.at[idx, rc] = wavg_val + BREAKOUT_BLEND * (recent_val - wavg_val)

            # Flag for reduced regression in the next step
            proj.at[idx, "_is_breakout"] = True
            n_breakout += 1

    if n_breakout > 0:
        import logging
        logging.getLogger(__name__).info(
            "Breakout adjustment applied to %d skaters", n_breakout
        )
    return proj


def _regress_to_position_mean(proj: pd.DataFrame, rates: pd.DataFrame) -> pd.DataFrame:
    """Blend each player's rate toward the position-mean rate, weighted by total GP.

    Players flagged with a breakout GP bonus (from ``_breakout_adjustment``)
    get higher effective reliability, so the regression pulls them toward the
    mean less aggressively.
    """
    rate_cols = list(SKATER_RATE_MAP.keys())

    # Total GP across baseline for each player
    total_gp = rates.groupby("player_id")["games_played"].sum().rename("total_gp")
    proj = proj.merge(total_gp, on="player_id", how="left")
    proj["total_gp"] = proj["total_gp"].fillna(0)

    # Position means (across all player-seasons in the baseline)
    pos_means = rates.groupby("position_code")[rate_cols].mean()

    # Reliability weight: fraction of signal that comes from observed data
    # reliability = total_gp / (total_gp + RELIABILITY_GP)
    # Breakout players get a reliability floor so regression doesn't crush
    # their breakout-adjusted rates back toward the position mean.
    is_breakout = proj.pop("_is_breakout") if "_is_breakout" in proj.columns else False
    proj["_reliability"] = proj["total_gp"] / (proj["total_gp"] + RELIABILITY_GP)
    proj.loc[is_breakout == True, "_reliability"] = proj.loc[
        is_breakout == True, "_reliability"
    ].clip(lower=BREAKOUT_RELIABILITY_FLOOR)

    for rc in rate_cols:
        pos_mean_for_player = proj["position_code"].map(pos_means[rc])
        proj[rc] = (
            proj["_reliability"] * proj[rc]
            + (1 - proj["_reliability"]) * pos_mean_for_player
        )

    proj.drop(columns=["_reliability"], inplace=True)
    return proj


def _project_gp(proj: pd.DataFrame, rates: pd.DataFrame) -> pd.DataFrame:
    """Project GP: weighted average of historical GP, regressed toward 78."""
    rates = rates.copy()
    rates["_weight"] = rates["season_id"].map(SEASON_WEIGHTS).fillna(1.0)

    gp_agg = rates.groupby("player_id").apply(
        lambda g: np.average(g["games_played"], weights=g["_weight"]),
        include_groups=False,
    ).rename("avg_gp")

    proj = proj.merge(gp_agg, on="player_id", how="left")
    proj["avg_gp"] = proj["avg_gp"].fillna(GP_REGRESS_TARGET)

    # Blend toward target
    proj["projected_gp"] = (
        (1 - GP_REGRESS_WEIGHT) * proj["avg_gp"]
        + GP_REGRESS_WEIGHT * GP_REGRESS_TARGET
    )
    # Cap at 82
    proj["projected_gp"] = proj["projected_gp"].clip(upper=82)

    proj.drop(columns=["avg_gp"], inplace=True)
    return proj


def _apply_age_curve(
    proj: pd.DataFrame,
    birth_dates: pd.DataFrame,
    target_season_start_year: int,
) -> pd.DataFrame:
    """Multiply projected rates by an age-curve factor."""
    rate_cols = list(SKATER_RATE_MAP.keys())

    bd = birth_dates[["playerId", "birthDate"]].copy()
    bd = bd.rename(columns={"playerId": "player_id", "birthDate": "birth_date"})
    bd["birth_date"] = pd.to_datetime(bd["birth_date"], errors="coerce")

    proj = proj.merge(bd, on="player_id", how="left")

    # Age as of Oct 1 of the target season start year
    ref_date = pd.Timestamp(f"{target_season_start_year}-10-01")
    proj["age_next"] = ((ref_date - proj["birth_date"]).dt.days / 365.25).round(0)

    proj["age_factor"] = proj["age_next"].map(AGE_CURVE).fillna(1.0)

    for rc in rate_cols:
        proj[rc] = proj[rc] * proj["age_factor"]

    proj.drop(columns=["birth_date"], inplace=True)
    return proj
