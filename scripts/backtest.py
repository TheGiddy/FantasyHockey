#!/usr/bin/env python
"""Backtest: project 2024-25 using prior seasons, then compare to actuals.

Uses 2021-22, 2022-23, 2023-24 as the baseline (skipping COVID years
2019-20 and 2020-21) to project 2024-25.  Then compares projections
against actual 2024-25 stats.

Reports:
- RMSE per category
- Spearman rank correlation per category
- Top-50 hit rate (how many of our projected top 50 were actually top 50)
- Biggest positive and negative misses
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fantasy_hockey.config import DATA_DIR, OUTPUTS_DIR, SEASON_WEIGHTS
from fantasy_hockey.data import nhl_client
from fantasy_hockey.ingest.seasons import ingest_skaters, ingest_goalies
from fantasy_hockey.projections.skater_model import project_skaters
from fantasy_hockey.projections.goalie_model import project_goalies

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")
log = logging.getLogger(__name__)

# The season we're projecting (the "test" season).
TEST_SEASON = 20242025

# Baseline seasons to use for the projection (the "training" seasons).
# Skip COVID: 2019-20 (20192020) and 2020-21 (20202021).
BACKTEST_BASELINE = (20212022, 20222023, 20232024)

# Override season weights for the backtest baseline.
BACKTEST_WEIGHTS = {
    20212022: 1.0,
    20222023: 3.0,
    20232024: 5.0,
}

# Minimum GP in the test season to include a player in accuracy metrics
# (filters out injured/demoted players who are noise).
MIN_GP_ACTUAL = 20


def main(force: bool = False, skip_bio: bool = True):
    # --- Temporarily override season weights in config --------------------
    import fantasy_hockey.config as cfg
    orig_weights = cfg.SEASON_WEIGHTS.copy()
    cfg.SEASON_WEIGHTS.clear()
    cfg.SEASON_WEIGHTS.update(BACKTEST_WEIGHTS)

    try:
        _run_backtest(force, skip_bio)
    finally:
        cfg.SEASON_WEIGHTS.clear()
        cfg.SEASON_WEIGHTS.update(orig_weights)


def _run_backtest(force: bool, skip_bio: bool):
    print("=== BACKTEST: Project 2024-25 from 2021-22 / 2022-23 / 2023-24 ===\n")

    # --- Ingest baseline ---------------------------------------------------
    print("[1/5] Ingesting baseline seasons ...")
    # Force re-ingest so the combined cache uses our backtest seasons
    skaters_raw = ingest_skaters(BACKTEST_BASELINE, force=True)
    goalies_raw = ingest_goalies(BACKTEST_BASELINE, force=True)
    print(f"      Skaters: {len(skaters_raw)} rows, {skaters_raw['player_id'].nunique()} players")
    print(f"      Goalies: {len(goalies_raw)} rows, {goalies_raw['player_id'].nunique()} goalies")

    # --- Ingest actuals (test season) --------------------------------------
    print("\n[2/5] Fetching actual 2024-25 stats ...")
    actual_sk = nhl_client.skaters_combined(TEST_SEASON, force=force)
    actual_gk = nhl_client.goalie_summary(TEST_SEASON, force=force)

    # Normalise column names to match ingested data
    from fantasy_hockey.ingest.seasons import _normalise_columns
    actual_sk = _normalise_columns(actual_sk)
    actual_gk = _normalise_columns(actual_gk)
    print(f"      Actual skaters: {len(actual_sk)}")
    print(f"      Actual goalies: {len(actual_gk)}")

    # --- Project -----------------------------------------------------------
    print("\n[3/5] Running projections ...")
    birth_dates = None
    if not skip_bio:
        from fantasy_hockey.ingest.seasons import ingest_birth_dates
        try:
            birth_dates = ingest_birth_dates(skaters_raw, goalies_raw)
        except Exception as exc:
            log.warning("Birth dates unavailable: %s", exc)

    proj_sk = project_skaters(skaters_raw, birth_dates, target_season_start_year=2024)
    proj_gk = project_goalies(goalies_raw, birth_dates, target_season_start_year=2024)
    print(f"      Projected {len(proj_sk)} skaters, {len(proj_gk)} goalies")

    # --- Compare skaters ---------------------------------------------------
    print("\n[4/5] Evaluating skater projections ...")
    _evaluate_skaters(proj_sk, actual_sk)

    # --- Compare goalies ---------------------------------------------------
    print("\n[5/5] Evaluating goalie projections ...")
    _evaluate_goalies(proj_gk, actual_gk)

    print("\nBacktest complete.")


# ---------------------------------------------------------------------------
# Skater evaluation
# ---------------------------------------------------------------------------

# Projected column → actual column mapping
# proj_col → actual_col.  After merge with suffixes=("_proj", "_actual"),
# columns that exist on *both* sides get suffixed; unique names don't.
_SK_CAT_MAP = {
    "goals": "goals",           # both sides → goals_proj / goals_actual
    "assists": "assists",       # both sides → assists_proj / assists_actual
    "pim": "penalty_minutes",   # different names → pim (proj), penalty_minutes (actual)
    "ppp": "pp_points",         # different names
    "sog": "shots",             # different names
    "hits": "hits",             # both sides → hits_proj / hits_actual
    "blocks": "blocked_shots",  # different names
}


def _evaluate_skaters(proj: pd.DataFrame, actual: pd.DataFrame):
    # Filter actuals to players with meaningful GP
    actual = actual[actual["games_played"] >= MIN_GP_ACTUAL].copy()

    # Merge on player_id
    merged = proj.merge(
        actual[["player_id", "games_played"] + list(_SK_CAT_MAP.values())],
        on="player_id",
        how="inner",
        suffixes=("_proj", "_actual"),
    )
    print(f"      {len(merged)} skaters with both projection and {MIN_GP_ACTUAL}+ GP actuals")

    if len(merged) == 0:
        print("      No overlap found — cannot evaluate.")
        return

    results = []
    for proj_col, actual_col in _SK_CAT_MAP.items():
        # Resolve column names after merge with suffixes
        def _resolve(base, suffix):
            if f"{base}{suffix}" in merged.columns:
                return f"{base}{suffix}"
            if base in merged.columns:
                return base
            return None

        p_col = _resolve(proj_col, "_proj")
        a_col = _resolve(actual_col, "_actual")

        if p_col is None or a_col is None:
            log.warning("Could not find columns for %s (proj=%s, actual=%s)", proj_col, p_col, a_col)
            continue

        # Drop rows where either side is NaN for this category
        valid = merged[[p_col, a_col]].dropna()
        projected = valid[p_col].values.astype(float)
        actual_vals = valid[a_col].values.astype(float)

        rmse = np.sqrt(np.mean((projected - actual_vals) ** 2))
        mae = np.mean(np.abs(projected - actual_vals))

        # Spearman rank correlation
        spearman_r, spearman_p = scipy_stats.spearmanr(projected, actual_vals)

        # Top-50 hit rate (using full merged, NaN-filled rows won't rank high)
        valid_merged = merged.dropna(subset=[p_col, a_col])
        proj_top50 = set(valid_merged.nlargest(50, p_col)["player_id"])
        actual_top50 = set(valid_merged.nlargest(50, a_col)["player_id"])
        hit_rate = len(proj_top50 & actual_top50) / 50

        results.append({
            "Category": proj_col.upper(),
            "RMSE": round(rmse, 2),
            "MAE": round(mae, 2),
            "Spearman r": round(spearman_r, 3),
            "Top-50 Hit%": f"{hit_rate:.0%}",
        })

    results_df = pd.DataFrame(results)
    print("\n      Skater Accuracy Metrics:")
    print(results_df.to_string(index=False))

    # Biggest misses: players whose projected rank vs actual rank diverged most
    # Use goals as the primary sort for "rank"
    if "goals_proj" in merged.columns and "goals_actual" in merged.columns:
        merged["proj_rank"] = merged["goals_proj"].rank(ascending=False)
        merged["actual_rank"] = merged["goals_actual"].rank(ascending=False)
    elif "goals" in merged.columns:
        merged["proj_rank"] = merged["goals"].rank(ascending=False)
        merged["actual_rank"] = merged["goals"].rank(ascending=False)
        print("\n      (Skipping rank-miss analysis — column collision)")
        return

    merged["rank_diff"] = merged["proj_rank"] - merged["actual_rank"]

    print("\n      Biggest OVERESTIMATES (projected much higher than actual):")
    overest = merged.nsmallest(5, "rank_diff")[["skater_full_name", "proj_rank", "actual_rank", "rank_diff"]]
    print(overest.to_string(index=False))

    print("\n      Biggest UNDERESTIMATES (actual much higher than projected):")
    underest = merged.nlargest(5, "rank_diff")[["skater_full_name", "proj_rank", "actual_rank", "rank_diff"]]
    print(underest.to_string(index=False))


# ---------------------------------------------------------------------------
# Goalie evaluation
# ---------------------------------------------------------------------------

_GK_CAT_MAP = {
    "wins": "wins",
    "save_pct": "save_pct",
    "shutouts": "shutouts",
}


def _evaluate_goalies(proj: pd.DataFrame, actual: pd.DataFrame):
    actual = actual[actual["games_started"] >= 15].copy()

    merged = proj.merge(
        actual[["player_id", "games_started", "wins", "save_pct", "shutouts"]],
        on="player_id",
        how="inner",
        suffixes=("_proj", "_actual"),
    )
    print(f"      {len(merged)} goalies with both projection and 15+ GS actuals")

    if len(merged) == 0:
        print("      No overlap found.")
        return

    results = []
    for proj_col, actual_col in _GK_CAT_MAP.items():
        if f"{proj_col}_proj" in merged.columns:
            p_col = f"{proj_col}_proj"
        else:
            p_col = proj_col

        if f"{actual_col}_actual" in merged.columns:
            a_col = f"{actual_col}_actual"
        else:
            a_col = actual_col

        projected = merged[p_col].values.astype(float)
        actual_vals = merged[a_col].values.astype(float)

        rmse = np.sqrt(np.mean((projected - actual_vals) ** 2))
        mae = np.mean(np.abs(projected - actual_vals))
        spearman_r, _ = scipy_stats.spearmanr(projected, actual_vals)

        pool_size = min(24, len(merged))
        proj_top = set(merged.nlargest(pool_size, p_col)["player_id"])
        actual_top = set(merged.nlargest(pool_size, a_col)["player_id"])
        hit_rate = len(proj_top & actual_top) / pool_size if pool_size > 0 else 0

        fmt = ".4f" if proj_col == "save_pct" else ".2f"
        results.append({
            "Category": proj_col.upper(),
            "RMSE": format(rmse, fmt),
            "MAE": format(mae, fmt),
            "Spearman r": round(spearman_r, 3),
            f"Top-{pool_size} Hit%": f"{hit_rate:.0%}",
        })

    results_df = pd.DataFrame(results)
    print("\n      Goalie Accuracy Metrics:")
    print(results_df.to_string(index=False))

    # Top goalie misses
    if "wins_proj" in merged.columns:
        merged["proj_rank"] = merged["wins_proj"].rank(ascending=False)
        merged["actual_rank"] = merged["wins_actual"].rank(ascending=False)
        merged["rank_diff"] = merged["proj_rank"] - merged["actual_rank"]

        print("\n      Biggest goalie OVERESTIMATES:")
        print(merged.nsmallest(3, "rank_diff")[
            ["goalie_full_name", "proj_rank", "actual_rank", "rank_diff"]
        ].to_string(index=False))

        print("\n      Biggest goalie UNDERESTIMATES:")
        print(merged.nlargest(3, "rank_diff")[
            ["goalie_full_name", "proj_rank", "actual_rank", "rank_diff"]
        ].to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backtest projection model")
    parser.add_argument("--force", action="store_true", help="Re-fetch from APIs")
    parser.add_argument("--with-bio", action="store_true", help="Include age curves")
    args = parser.parse_args()
    main(force=args.force, skip_bio=not args.with_bio)
