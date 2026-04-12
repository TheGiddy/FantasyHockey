"""Match Yahoo player names to NHL player IDs via fuzzy name matching.

Yahoo and NHL APIs use different player IDs.  The only reliable link is the
player's name, which can differ slightly (e.g. "Matt" vs "Matthew",
accented characters, suffixes like "Jr.").  We do exact match first, then
fall back to a normalised comparison.
"""

from __future__ import annotations

import re
import unicodedata

import pandas as pd


def normalise_name(name: str) -> str:
    """Lowercase, strip accents, remove suffixes and punctuation."""
    # NFD decompose then strip combining marks (accent removal)
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_name = "".join(c for c in nfkd if not unicodedata.combining(c))
    # Lowercase
    ascii_name = ascii_name.lower().strip()
    # Remove suffixes
    ascii_name = re.sub(r"\b(jr|sr|ii|iii|iv)\b\.?", "", ascii_name)
    # Remove punctuation and extra spaces
    ascii_name = re.sub(r"[^a-z\s]", "", ascii_name)
    ascii_name = re.sub(r"\s+", " ", ascii_name).strip()
    return ascii_name


def match_draft_to_projections(
    draft_picks: list[dict],
    projections: pd.DataFrame,
    name_col: str = "name",
) -> pd.DataFrame:
    """Add ``draft_round`` to projections by matching Yahoo draft names.

    Parameters
    ----------
    draft_picks : list[dict]
        Each dict has at least ``player_name`` and ``round``.
    projections : DataFrame
        Must have a *name_col* column with player names and a ``player_id``
        column.
    name_col : str
        Column in *projections* containing player names.

    Returns
    -------
    DataFrame
        The projections frame with ``draft_round`` and ``draft_pick`` columns
        added where a match was found.
    """
    proj = projections.copy()
    proj["_norm_name"] = proj[name_col].apply(normalise_name)

    # Build lookup from normalised name → draft info
    draft_lookup: dict[str, dict] = {}
    for pick in draft_picks:
        norm = normalise_name(pick["player_name"])
        if norm and norm not in draft_lookup:
            draft_lookup[norm] = pick

    proj["draft_round"] = proj["_norm_name"].map(
        lambda n: draft_lookup.get(n, {}).get("round")
    )
    proj["draft_pick"] = proj["_norm_name"].map(
        lambda n: draft_lookup.get(n, {}).get("pick")
    )

    matched = proj["draft_round"].notna().sum()
    total = len(draft_picks)

    proj.drop(columns=["_norm_name"], inplace=True)
    return proj, matched, total
