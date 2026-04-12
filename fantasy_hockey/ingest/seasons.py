"""Ingest skater and goalie stats for the configured baseline seasons.

Combines multiple seasons into a single long-format dataframe with a
``seasonId`` column, then writes to ``data/players_raw.parquet``.
"""

from __future__ import annotations

import logging

import pandas as pd

from fantasy_hockey.config import BASELINE_SEASONS, DATA_DIR, season_id_to_label
from fantasy_hockey.data import cache, nhl_client

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Skaters
# ---------------------------------------------------------------------------

def ingest_skaters(
    seasons: tuple[int, ...] = BASELINE_SEASONS,
    *,
    force: bool = False,
) -> pd.DataFrame:
    """Pull combined skater stats for each season and stack them.

    Returns a long-format DataFrame: one row per (playerId, seasonId).  Columns
    include all fantasy-relevant counting stats plus metadata (name, position,
    team, GP, TOI).
    """
    key = "skaters_all_seasons"
    if not force and cache.has(key):
        return cache.load(key)

    frames: list[pd.DataFrame] = []
    for sid in seasons:
        log.info("Fetching skaters for %s …", season_id_to_label(sid))
        df = nhl_client.skaters_combined(sid, force=force)
        frames.append(df)

    combined = pd.concat(frames, ignore_index=True)

    # Normalise column names to snake_case for convenience
    combined = _normalise_columns(combined)

    cache.save(key, combined)
    log.info("Ingested %d skater-season rows across %d seasons", len(combined), len(seasons))
    return combined


# ---------------------------------------------------------------------------
# Goalies
# ---------------------------------------------------------------------------

def ingest_goalies(
    seasons: tuple[int, ...] = BASELINE_SEASONS,
    *,
    force: bool = False,
) -> pd.DataFrame:
    key = "goalies_all_seasons"
    if not force and cache.has(key):
        return cache.load(key)

    frames: list[pd.DataFrame] = []
    for sid in seasons:
        log.info("Fetching goalies for %s …", season_id_to_label(sid))
        df = nhl_client.goalie_summary(sid, force=force)
        frames.append(df)

    combined = pd.concat(frames, ignore_index=True)
    combined = _normalise_columns(combined)

    cache.save(key, combined)
    log.info("Ingested %d goalie-season rows across %d seasons", len(combined), len(seasons))
    return combined


# ---------------------------------------------------------------------------
# Bio data (birth dates for age curves)
# ---------------------------------------------------------------------------

def ingest_birth_dates(
    skaters: pd.DataFrame,
    goalies: pd.DataFrame,
    *,
    force: bool = False,
) -> pd.DataFrame:
    """Fetch birth dates for every unique player in the ingested data."""
    all_ids = (
        set(skaters["player_id"].unique()) | set(goalies["player_id"].unique())
    )
    log.info("Fetching birth dates for %d unique players …", len(all_ids))
    return nhl_client.player_birth_dates(sorted(all_ids), force=force)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """CamelCase → snake_case."""
    import re

    def _to_snake(name: str) -> str:
        # Insert underscore before uppercase letters, then lowercase everything
        s = re.sub(r"(?<=[a-z0-9])([A-Z])", r"_\1", name)
        return s.lower()

    return df.rename(columns=_to_snake)
