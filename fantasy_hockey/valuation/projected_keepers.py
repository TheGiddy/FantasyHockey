"""Project which players each team is likely to keep next season.

For each team, we:
1. Look at their end-of-season roster.
2. Filter to keeper-eligible players (draft_round - 2 > 3).
3. Compute "keeper surplus" = projected value rank vs. keeper round cost.
4. Assume each team keeps their best-surplus players (up to a configurable max).
5. Flag those players as "projected kept" — they won't be available in the draft.

This is a *projection*, not a certainty.  Managers may make surprising decisions,
but the model gives a realistic view of who's likely off the board.
"""

from __future__ import annotations

import pandas as pd

from fantasy_hockey.config import NUM_TEAMS
from fantasy_hockey.data.name_match import normalise_name


# Maximum keepers per team — most Yahoo keeper leagues allow a set number.
# This is configurable; set to None for "keep as many as eligible".
MAX_KEEPERS_PER_TEAM: int | None = None


def project_keepers(
    roster_players: list,
    projections: pd.DataFrame,
    name_col: str = "name",
    max_per_team: int | None = MAX_KEEPERS_PER_TEAM,
) -> pd.DataFrame:
    """Match roster players to projections and flag likely keepers.

    Parameters
    ----------
    roster_players : list[RosterPlayer]
        From ``YahooClient.all_rosters_with_keeper_eligibility()``.
    projections : pd.DataFrame
        Unified draft board with ``name``, ``rank``, ``adjusted_value`` columns.
    name_col : str
        Column in projections containing player names.
    max_per_team : int | None
        Max keepers per team.  None = no limit (keep all positive-surplus).

    Returns
    -------
    DataFrame
        The projections frame with added columns:
        - ``roster_team``: which fantasy team currently has this player
        - ``next_keeper_round``: the round cost to keep them next year
        - ``keeper_eligible_next``: bool
        - ``keeper_surplus_next``: value surplus over keeper cost
        - ``projected_kept``: True if we think this player will be kept
        - ``projected_kept_by``: team name of the projected keeper
    """
    proj = projections.copy()

    # Build normalised name lookup from roster data
    # Group by team for per-team keeper selection
    eligible_by_team: dict[str, list[dict]] = {}  # team_name -> list of player info
    name_to_roster: dict[str, dict] = {}  # norm_name -> roster info

    for rp in roster_players:
        norm = normalise_name(rp.player_name)
        elig_pos = getattr(rp, "eligible_positions", [])
        info = {
            "player_name": rp.player_name,
            "team_name": rp.team_name,
            "team_key": rp.team_key,
            "next_keeper_round": rp.next_keeper_round,
            "keeper_eligible_next": rp.keeper_eligible_next,
            "draft_round": rp.draft_round,
            "eligible_positions": elig_pos,
        }
        name_to_roster[norm] = info
        if rp.keeper_eligible_next:
            eligible_by_team.setdefault(rp.team_name, []).append({
                **info,
                "norm_name": norm,
            })

    # Match roster data to projections
    proj["_norm"] = proj[name_col].apply(normalise_name)
    proj["roster_team"] = proj["_norm"].map(lambda n: name_to_roster.get(n, {}).get("team_name"))
    proj["next_keeper_round"] = proj["_norm"].map(
        lambda n: name_to_roster.get(n, {}).get("next_keeper_round")
    )
    proj["keeper_eligible_next"] = proj["_norm"].map(
        lambda n: name_to_roster.get(n, {}).get("keeper_eligible_next", False)
    )
    proj["eligible_positions"] = proj["_norm"].map(
        lambda n: ",".join(name_to_roster.get(n, {}).get("eligible_positions", []))
    )
    proj["num_positions"] = proj["eligible_positions"].apply(
        lambda s: len(s.split(",")) if s else 1
    )

    # Compute keeper surplus: how much better is the player's rank than their
    # keeper round cost?  A player ranked #10 kept at round 8 (pick ~57-64)
    # has huge surplus.  We use picks_per_round to convert rounds to rank-equivalents.
    total_picks = len(proj[proj["draft_round"].notna()]) if "draft_round" in proj.columns else NUM_TEAMS * 21
    max_round = proj["draft_round"].max() if "draft_round" in proj.columns and proj["draft_round"].notna().any() else 21
    picks_per_round = total_picks / max_round if max_round else NUM_TEAMS

    proj["keeper_surplus_next"] = None
    elig_mask = proj["keeper_eligible_next"] == True
    if elig_mask.any():
        proj.loc[elig_mask, "keeper_surplus_next"] = (
            proj.loc[elig_mask, "next_keeper_round"].astype(float) * picks_per_round
            - proj.loc[elig_mask, "rank"].astype(float)
        )

    # For each team, select the best keeper-eligible players
    proj["projected_kept"] = False
    proj["projected_kept_by"] = None

    for team_name, eligible_list in eligible_by_team.items():
        # Find these players in projections
        team_norm_names = {e["norm_name"] for e in eligible_list}
        team_mask = proj["_norm"].isin(team_norm_names) & (proj["keeper_eligible_next"] == True)

        team_candidates = proj[team_mask].copy()
        if team_candidates.empty:
            continue

        # Sort by surplus (best keepers first)
        team_candidates = team_candidates.sort_values("keeper_surplus_next", ascending=False)

        # Only keep players with positive surplus (keeping a negative-surplus
        # player means you're overpaying — no rational manager does this)
        team_candidates = team_candidates[
            team_candidates["keeper_surplus_next"].astype(float) > 0
        ]

        if max_per_team is not None:
            team_candidates = team_candidates.head(max_per_team)

        kept_indices = team_candidates.index
        proj.loc[kept_indices, "projected_kept"] = True
        proj.loc[kept_indices, "projected_kept_by"] = team_name

    proj.drop(columns=["_norm"], inplace=True)

    n_projected = proj["projected_kept"].sum()
    return proj, n_projected
