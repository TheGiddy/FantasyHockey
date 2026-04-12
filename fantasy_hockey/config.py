"""Project-wide configuration: league constants, season window, file paths.

Anything that another module might want to tweak (categories, weights,
roster slots, baseline seasons) lives here so we have a single place to
edit it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
CACHE_DIR = DATA_DIR / "cache"
OUTPUTS_DIR = REPO_ROOT / "outputs"
OAUTH_FILE = REPO_ROOT / "oauth2.json"

for _p in (DATA_DIR, CACHE_DIR, OUTPUTS_DIR):
    _p.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# League settings (Yahoo H2H, 10 categories)
# ---------------------------------------------------------------------------

# Skater categories tracked by the league. Keys are our internal names;
# values are the NHL stats API field names from the skater stats endpoints.
SKATER_CATEGORIES: dict[str, str] = {
    "G": "goals",
    "A": "assists",
    "PIM": "penaltyMinutes",
    "PPP": "ppPoints",          # power play points = ppGoals + ppAssists
    "SOG": "shots",
    "HIT": "hits",
    "BLK": "blockedShots",
}

# Goalie categories. Field names from goalie summary endpoint.
GOALIE_CATEGORIES: dict[str, str] = {
    "W": "wins",
    "SVPCT": "savePctg",
    "SHO": "shutouts",
}

ALL_CATEGORIES: list[str] = list(SKATER_CATEGORIES.keys()) + list(GOALIE_CATEGORIES.keys())


# ---------------------------------------------------------------------------
# Roster construction
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RosterSlots:
    C: int = 3
    LW: int = 3
    RW: int = 3
    D: int = 5
    G: int = 2
    BN: int = 5
    IR: int = 1
    IR_PLUS: int = 2

    @property
    def active(self) -> int:
        return self.C + self.LW + self.RW + self.D + self.G + self.BN

    @property
    def draftable(self) -> int:
        # Active spots only (IR slots are filled in-season, not drafted into).
        return self.active


ROSTER = RosterSlots()
NUM_TEAMS = 8  # Verified from Yahoo: league has 8 teams
DRAFTABLE_PLAYER_POOL = NUM_TEAMS * ROSTER.draftable  # 8 * 21 = 168


# ---------------------------------------------------------------------------
# Keeper rules
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class KeeperRules:
    # A kept player's new draft round = prior round - rounds_earlier.
    rounds_earlier: int = 2
    # Players drafted in any of these rounds cannot be kept.
    locked_rounds: tuple[int, ...] = (1, 2, 3)
    # Waiver pickups (undrafted or on a different team than drafter) are
    # keepable at this fixed round.  Set to None to make them unkeptable.
    waiver_keeper_round: int = 12
    # Players acquired after this date are NOT keeper-eligible.
    # Format: "YYYY-MM-DD".  None = no deadline.
    keeper_deadline: str | None = "2026-03-15"


KEEPERS = KeeperRules()

# Your fantasy team name (case-insensitive match against Yahoo team names).
MY_TEAM_NAME: str = "twin daddy"


# ---------------------------------------------------------------------------
# Projection baseline
# ---------------------------------------------------------------------------

# Seasons used as the rolling 3-year baseline for next-year projections.
# COVID-shortened seasons (2019-20, 2020-21) are excluded by design.
# Stored as the season ID format the NHL stats API expects: YYYY1YYYY2 ints,
# e.g. 20232024 for the 2023-24 season.
BASELINE_SEASONS: tuple[int, ...] = (
    20232024,
    20242025,
    20252026,
)

# Per-season weights when computing the weighted-average rate baseline.
# Most recent season weighted heaviest.
SEASON_WEIGHTS: dict[int, float] = {
    20232024: 1.0,
    20242025: 3.0,
    20252026: 5.0,
}

# The season we are projecting *for*.
TARGET_SEASON: int = 20262027


# ---------------------------------------------------------------------------
# NHL API
# ---------------------------------------------------------------------------

NHL_STATS_BASE = "https://api.nhle.com/stats/rest/en"
NHL_WEB_BASE = "https://api-web.nhle.com/v1"

# Stats-rest endpoints expect a `cayenneExp` filter and return paginated rows.
NHL_STATS_PAGE_SIZE = 100
NHL_REQUEST_TIMEOUT_S = 30


# ---------------------------------------------------------------------------
# Yahoo
# ---------------------------------------------------------------------------

YAHOO_GAME_CODE = "nhl"
# Yahoo's "game year" for fantasy seasons usually matches the start year of
# the NHL season (e.g. 2025 for the 2025-26 season).
YAHOO_CURRENT_GAME_YEAR = 2025


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def season_id_to_label(season_id: int) -> str:
    """20232024 -> '2023-24'."""
    s = str(season_id)
    return f"{s[:4]}-{s[6:]}"
