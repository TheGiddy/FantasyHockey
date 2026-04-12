"""Yahoo Fantasy API wrapper.

Thin convenience layer on top of ``yahoo_fantasy_api``.  Reads the existing
``oauth2.json`` and exposes league metadata, roster positions, stat
categories, draft results, and ADP info.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from yahoo_oauth import OAuth2
import yahoo_fantasy_api as yfa

import json

from fantasy_hockey.config import CACHE_DIR, OAUTH_FILE, YAHOO_GAME_CODE, YAHOO_CURRENT_GAME_YEAR

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes for structured output
# ---------------------------------------------------------------------------

@dataclass
class LeagueInfo:
    league_id: str
    name: str
    num_teams: int
    roster_positions: dict[str, int]   # position_code → count
    stat_categories: list[dict]
    current_week: int


@dataclass
class DraftPick:
    player_id: int
    player_name: str
    round: int
    pick: int
    team_key: str


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class YahooClient:
    """Stateful client — holds an authenticated OAuth session."""

    def __init__(self, oauth_file: str | Path = OAUTH_FILE) -> None:
        self._oauth = OAuth2(None, None, from_file=str(oauth_file))
        self._game = yfa.game.Game(self._oauth, YAHOO_GAME_CODE)
        self._league: yfa.league.League | None = None
        self._league_id: str | None = None

    # -- connection ----------------------------------------------------------

    @property
    def league(self) -> yfa.league.League:
        if self._league is None:
            ids = self._game.league_ids(year=YAHOO_CURRENT_GAME_YEAR)
            if not ids:
                raise RuntimeError(
                    f"No leagues found for {YAHOO_GAME_CODE} year={YAHOO_CURRENT_GAME_YEAR}"
                )
            self._league_id = ids[0]
            self._league = yfa.league.League(self._oauth, self._league_id)
            log.info("Connected to Yahoo league %s", self._league_id)
        return self._league

    # -- league metadata -----------------------------------------------------

    def league_info(self) -> LeagueInfo:
        lg = self.league
        settings = lg.settings()

        # positions() returns a dict like {"C": {"count": 3, ...}, "LW": ...}
        raw_positions = lg.positions()
        positions: dict[str, int] = {}
        if isinstance(raw_positions, dict):
            for code, info in raw_positions.items():
                positions[code] = int(info.get("count", 1)) if isinstance(info, dict) else 1
        else:
            # Fallback for list-of-dicts format
            for pos in raw_positions:
                code = pos.get("position", "??")
                positions[code] = positions.get(code, 0) + int(pos.get("count", 1))

        cats = lg.stat_categories()
        return LeagueInfo(
            league_id=self._league_id,
            name=settings.get("name", ""),
            num_teams=int(settings.get("num_teams", 0)),
            roster_positions=positions,
            stat_categories=cats,
            current_week=lg.current_week(),
        )

    # -- draft ---------------------------------------------------------------

    def draft_results(self, enrich: bool = True) -> list[DraftPick]:
        """Return every pick from the most recent draft, sorted by pick order.

        If *enrich* is True, fetches player details to fill in names (slower
        but needed for name-matching to NHL IDs).
        """
        raw = self.league.draft_results()
        picks: list[DraftPick] = []
        for p in raw:
            picks.append(DraftPick(
                player_id=int(p["player_id"]),
                player_name="",
                round=int(p["round"]),
                pick=int(p["pick"]),
                team_key=p["team_key"],
            ))
        picks.sort(key=lambda p: (p.round, p.pick))

        if enrich:
            self._enrich_pick_names(picks)

        return picks

    def _enrich_pick_names(self, picks: list[DraftPick]) -> None:
        """Fill in player_name for each pick by fetching details.  Results cached."""
        cache_file = CACHE_DIR / "yahoo_draft_names.json"

        # Load existing cache
        name_cache: dict[str, str] = {}
        if cache_file.exists():
            name_cache = json.loads(cache_file.read_text())

        lg = self.league
        updated = False
        for pick in picks:
            pid_str = str(pick.player_id)
            if pid_str in name_cache:
                pick.player_name = name_cache[pid_str]
                continue
            try:
                details = lg.player_details(pick.player_id)
                if details:
                    name_info = details[0].get("name", {})
                    pick.player_name = name_info.get("full", f"Yahoo#{pick.player_id}")
                    name_cache[pid_str] = pick.player_name
                    updated = True
            except Exception:
                log.warning("Could not enrich name for Yahoo player %d", pick.player_id)

        if updated:
            cache_file.write_text(json.dumps(name_cache, indent=2))

    # -- teams ---------------------------------------------------------------

    def teams(self) -> dict:
        """Return the raw teams dict from the league."""
        return self.league.teams()

    # -- keepers -------------------------------------------------------------

    @dataclass
    class RosterPlayer:
        """A player on a team's end-of-season roster with draft context."""
        player_name: str
        yahoo_player_id: int
        team_name: str
        team_key: str
        position: str
        eligible_positions: list[str] = field(default_factory=list)
        draft_round: int | None = None       # round they were drafted in THIS year's draft
        draft_pick: int | None = None
        drafted_by: str | None = None         # team_key of the team that drafted them
        next_keeper_round: int | None = None  # projected keeper cost next year
        keeper_eligible_next: bool = False     # can this player be kept next year?

    def all_rosters_with_keeper_eligibility(self, *, force: bool = False) -> list[RosterPlayer]:
        """Walk every team's roster and compute next-year keeper eligibility.

        For each player:
        1. Look up their draft round from this year's draft.
        2. Compute next year's keeper cost = draft_round - KEEPERS.rounds_earlier.
        3. If that cost falls in locked rounds (1-3) or they weren't drafted
           (waiver pickup / FA), they can't be kept.
        4. Waiver pickups are keepable at KEEPERS.waiver_keeper_round (12).
        5. Players acquired after KEEPERS.keeper_deadline are NOT keeper-eligible.

        Results are cached.
        """
        from datetime import datetime
        from fantasy_hockey.config import KEEPERS

        cache_file = CACHE_DIR / "yahoo_rosters_keeper_elig.json"
        if not force and cache_file.exists():
            raw = json.loads(cache_file.read_text())
            return [self.RosterPlayer(**r) for r in raw]

        lg = self.league
        teams = lg.teams()

        # Build draft lookup: yahoo_player_id -> {round, pick, team_key}
        draft = lg.draft_results()
        draft_map = {}
        for p in draft:
            draft_map[int(p["player_id"])] = {
                "round": int(p["round"]),
                "pick": int(p["pick"]),
                "team_key": p["team_key"],
            }

        # Scan transactions to determine:
        # 1. Which players were DROPPED at any point (waiver pickup = R12 keeper)
        # 2. Which players were acquired after the keeper deadline (ineligible)
        #
        # A player is a "waiver pickup" only if they were dropped to waivers/FA
        # at some point.  Trades do NOT reset the keeper round.
        was_dropped: set[int] = set()  # player IDs that were dropped at any point
        acquired_after_deadline: set[tuple[int, str]] = set()  # (player_id, team_key)
        deadline_ts: float | None = None
        if KEEPERS.keeper_deadline:
            deadline_ts = datetime.strptime(KEEPERS.keeper_deadline, "%Y-%m-%d").timestamp()

        try:
            txns = lg.transactions("add,drop,trade", "500")
            # Track the LATEST add/trade per (player_id, destination_team_key)
            latest_acquisition: dict[tuple[int, str], float] = {}
            for txn in txns:
                ts = float(txn.get("timestamp", 0))
                players = txn.get("players", {})
                if not isinstance(players, dict):
                    continue
                for key_or_idx, entry in players.items():
                    if key_or_idx == "count":
                        continue
                    if not isinstance(entry, dict):
                        continue
                    player_data = entry.get("player", [])
                    if not player_data or not isinstance(player_data, list):
                        continue
                    # Extract player_id from the metadata list (first element)
                    pid = 0
                    meta_list = player_data[0] if isinstance(player_data[0], list) else []
                    for item in meta_list:
                        if isinstance(item, dict) and "player_id" in item:
                            pid = int(item["player_id"])
                            break
                    if not pid:
                        continue
                    # Extract transaction_data (second element)
                    txn_data_raw = player_data[1] if len(player_data) > 1 else {}
                    txn_data_entries = txn_data_raw.get("transaction_data", txn_data_raw)
                    if isinstance(txn_data_entries, dict):
                        txn_data_entries = [txn_data_entries]
                    if not isinstance(txn_data_entries, list):
                        continue
                    for td in txn_data_entries:
                        if not isinstance(td, dict):
                            continue
                        # Track drops: player was sent to waivers/FA
                        if td.get("type") == "drop":
                            was_dropped.add(pid)
                        # Track acquisitions (add or trade) for deadline check
                        if td.get("destination_team_key") and td.get("type") in ("add", "trade"):
                            acq_key = (pid, td["destination_team_key"])
                            if ts > latest_acquisition.get(acq_key, 0):
                                latest_acquisition[acq_key] = ts

            if deadline_ts:
                for (pid, tk), ts in latest_acquisition.items():
                    if ts > deadline_ts:
                        acquired_after_deadline.add((pid, tk))
            log.info(
                "Transactions: %d players were dropped this season; "
                "%d player-team acquisitions after keeper deadline",
                len(was_dropped), len(acquired_after_deadline),
            )
        except Exception as exc:
            log.warning("Could not fetch transactions for keeper analysis: %s", exc)

        all_players: list[self.RosterPlayer] = []
        for tk in teams:
            t = teams[tk]
            team_key = t["team_key"]
            team_name = t["name"]
            team_obj = yfa.team.Team(self._oauth, team_key)
            roster = team_obj.roster()
            for p in roster:
                pid = int(p["player_id"])
                d = draft_map.get(pid)

                draft_round = d["round"] if d else None
                draft_pick = d["pick"] if d else None
                drafted_by = d["team_key"] if d else None

                # A player is a "waiver pickup" if they were:
                # - Never drafted (undrafted FA), OR
                # - Dropped to waivers/FA at any point during the season
                # Trades alone do NOT reset the keeper round.
                is_waiver = (drafted_by is None) or (pid in was_dropped)

                if is_waiver and KEEPERS.waiver_keeper_round is not None:
                    next_round = KEEPERS.waiver_keeper_round
                    eligible = next_round > max(KEEPERS.locked_rounds)
                elif draft_round is not None:
                    next_round = draft_round - KEEPERS.rounds_earlier
                    eligible = next_round > max(KEEPERS.locked_rounds)
                else:
                    next_round = None
                    eligible = False

                # Acquired after keeper deadline → not eligible
                if eligible and (pid, team_key) in acquired_after_deadline:
                    eligible = False
                    next_round = None

                # Filter out non-playing positions like IR, IR+, BN
                raw_elig = p.get("eligible_positions", [])
                playing_positions = [
                    pos for pos in raw_elig
                    if pos not in ("IR", "IR+", "BN", "Util", "G")
                ]

                all_players.append(self.RosterPlayer(
                    player_name=p["name"],
                    yahoo_player_id=pid,
                    team_name=team_name,
                    team_key=team_key,
                    position=p.get("selected_position", "?"),
                    eligible_positions=playing_positions,
                    draft_round=draft_round,
                    draft_pick=draft_pick,
                    drafted_by=drafted_by,
                    next_keeper_round=next_round if eligible else None,
                    keeper_eligible_next=eligible,
                ))

        # Cache
        cache_file.write_text(json.dumps(
            [{
                "player_name": r.player_name,
                "yahoo_player_id": r.yahoo_player_id,
                "team_name": r.team_name,
                "team_key": r.team_key,
                "position": r.position,
                "eligible_positions": r.eligible_positions,
                "draft_round": r.draft_round,
                "draft_pick": r.draft_pick,
                "drafted_by": r.drafted_by,
                "next_keeper_round": r.next_keeper_round,
                "keeper_eligible_next": r.keeper_eligible_next,
            } for r in all_players],
            indent=2,
        ))
        log.info(
            "Scanned %d roster players across %d teams; %d keeper-eligible",
            len(all_players), len(teams),
            sum(1 for r in all_players if r.keeper_eligible_next),
        )
        return all_players

    # -- player helpers ------------------------------------------------------

    def player_stats(self, player_ids: list[int], stat_type: str = "season"):
        """Wrapper around league.player_stats()."""
        return self.league.player_stats(player_ids, stat_type)

    def percent_owned(self, player_ids: list[int]) -> list[dict]:
        """Ownership percentage for a set of players."""
        return self.league.percent_owned(player_ids)
