"""Thin, typed wrappers around the NHL stats-rest and web API endpoints.

Every public function returns a :class:`pandas.DataFrame` for one season.
Pagination and retries are handled internally.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from fantasy_hockey.config import (
    NHL_REQUEST_TIMEOUT_S,
    NHL_STATS_BASE,
    NHL_STATS_PAGE_SIZE,
    NHL_WEB_BASE,
)
from fantasy_hockey.data import cache

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def _get_json(url: str, params: dict | None = None) -> dict:
    resp = requests.get(url, params=params, timeout=NHL_REQUEST_TIMEOUT_S)
    resp.raise_for_status()
    return resp.json()


def _paginated_fetch(
    report: str,
    player_type: str,
    season_id: int,
    game_type: int = 2,
) -> pd.DataFrame:
    """Fetch all rows from a stats-rest endpoint with pagination.

    Parameters
    ----------
    report : str
        The report slug, e.g. ``"summary"``, ``"realtime"``, ``"powerplay"``.
    player_type : str
        ``"skater"`` or ``"goalie"``.
    season_id : int
        E.g. ``20242025``.
    game_type : int
        2 = regular season, 3 = playoffs.
    """
    url = f"{NHL_STATS_BASE}/{player_type}/{report}"
    rows: list[dict[str, Any]] = []
    start = 0

    while True:
        data = _get_json(url, params={
            "isAggregate": "false",
            "isGame": "false",
            "start": start,
            "limit": NHL_STATS_PAGE_SIZE,
            "cayenneExp": f"seasonId={season_id} and gameTypeId={game_type}",
        })
        batch = data.get("data", [])
        rows.extend(batch)
        total = data.get("total", 0)
        start += NHL_STATS_PAGE_SIZE
        if start >= total or len(batch) == 0:
            break

    log.info(
        "%s/%s season=%s  → %d rows (API total=%d)",
        player_type, report, season_id, len(rows), total,
    )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Public API — skater stats
# ---------------------------------------------------------------------------

def skater_summary(season_id: int, *, force: bool = False) -> pd.DataFrame:
    """Goals, assists, PIM, PPP, shots, GP, position, TOI, etc."""
    key = f"skater_summary_{season_id}"
    return cache.load_or_fetch(
        key,
        lambda: _paginated_fetch("summary", "skater", season_id),
        force=force,
    )


def skater_realtime(season_id: int, *, force: bool = False) -> pd.DataFrame:
    """Hits, blocked shots, giveaways, takeaways."""
    key = f"skater_realtime_{season_id}"
    return cache.load_or_fetch(
        key,
        lambda: _paginated_fetch("realtime", "skater", season_id),
        force=force,
    )


def skater_powerplay(season_id: int, *, force: bool = False) -> pd.DataFrame:
    """PP goals, PP assists, PP points, PP TOI.  Useful for opportunity modeling."""
    key = f"skater_powerplay_{season_id}"
    return cache.load_or_fetch(
        key,
        lambda: _paginated_fetch("powerplay", "skater", season_id),
        force=force,
    )


# ---------------------------------------------------------------------------
# Public API — goalie stats
# ---------------------------------------------------------------------------

def goalie_summary(season_id: int, *, force: bool = False) -> pd.DataFrame:
    """Wins, save %, shutouts, GAA, GP, GS."""
    key = f"goalie_summary_{season_id}"
    return cache.load_or_fetch(
        key,
        lambda: _paginated_fetch("summary", "goalie", season_id),
        force=force,
    )


# ---------------------------------------------------------------------------
# Public API — player bio / landing (web API, not stats-rest)
# ---------------------------------------------------------------------------

def player_landing(player_id: int) -> dict:
    """Full player profile: birth date, position, team, draft info, featured stats.

    Not cached by default (called selectively, not in bulk).
    """
    url = f"{NHL_WEB_BASE}/player/{player_id}/landing"
    return _get_json(url)


def player_birth_dates(player_ids: list[int], *, force: bool = False) -> pd.DataFrame:
    """Fetch birth dates for a list of player IDs.  Cached as a single frame."""
    key = "player_birth_dates"

    if not force and cache.has(key):
        existing = cache.load(key)
        missing = set(player_ids) - set(existing["playerId"])
        if not missing:
            return existing[existing["playerId"].isin(player_ids)]
        # Fetch just the missing ones and append
        new_rows = _fetch_birth_rows(list(missing))
        combined = pd.concat([existing, pd.DataFrame(new_rows)], ignore_index=True)
        cache.save(key, combined)
        return combined[combined["playerId"].isin(player_ids)]

    rows = _fetch_birth_rows(player_ids)
    df = pd.DataFrame(rows)
    cache.save(key, df)
    return df


def _fetch_birth_rows(player_ids: list[int]) -> list[dict]:
    rows = []
    for pid in player_ids:
        try:
            data = player_landing(pid)
            rows.append({
                "playerId": pid,
                "birthDate": data.get("birthDate"),
                "position": data.get("position"),
                "currentTeamAbbrev": data.get("currentTeamAbbrev"),
                "firstName": data.get("firstName", {}).get("default", ""),
                "lastName": data.get("lastName", {}).get("default", ""),
            })
        except Exception:
            log.warning("Failed to fetch landing for player %s", pid, exc_info=True)
    return rows


# ---------------------------------------------------------------------------
# Convenience: combined skater frame for one season
# ---------------------------------------------------------------------------

def skaters_combined(season_id: int, *, force: bool = False) -> pd.DataFrame:
    """Merge skater summary + realtime into one row per player with all fantasy-relevant columns."""
    key = f"skaters_combined_{season_id}"
    if not force and cache.has(key):
        return cache.load(key)

    summary = skater_summary(season_id, force=force)
    realtime = skater_realtime(season_id, force=force)

    # Keep only the columns we need from realtime to avoid duplication
    realtime_cols = ["playerId", "hits", "blockedShots"]
    realtime_slim = realtime[realtime_cols].copy()

    merged = summary.merge(realtime_slim, on="playerId", how="left")
    cache.save(key, merged)
    return merged
