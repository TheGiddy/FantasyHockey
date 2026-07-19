#!/usr/bin/env python3
"""
Fetch draft-pick prospects (2024-2026 classes, rounds 1-2) with their junior/
European/NCAA season stats for NHLe rookie projections.

The draft-picks endpoint has no playerIds, so each pick is resolved through the
NHL search API by name, then the player landing supplies birthdate, current
team, NHL career GP, and per-league season totals.

Writes:
  data/prospect_meta.csv   one row per resolved prospect
  data/prospect_stats.csv  one row per regular-season club-league season
                           (last two seasons, non-NHL leagues)

Usage: python fetch_prospects.py
"""
import csv, os, time, unicodedata, urllib.parse

import requests

DRAFT_YEARS = [2024, 2025, 2026]
MAX_ROUND = 2
STAT_SEASONS = {20242025, 20252026}
# Not club leagues — tournament rows are tiny samples and translate badly.
EXCLUDE_LEAGUES = {"WJC-20", "WJC-18", "International", "International-Jr",
                   "WC", "Olympics", "Hlinka Memorial"}

os.makedirs("data", exist_ok=True)


def get(url, tries=3):
    # requests (certifi CA bundle) — Python's own store rejects search.d3.nhle.com
    for i in range(tries):
        try:
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            if i == tries - 1:
                raise
            print(f"  retry {i+1} after error: {e}")
            time.sleep(2 * (i + 1))


def norm(s):
    s = unicodedata.normalize("NFKD", str(s))
    return "".join(c for c in s if not unicodedata.combining(c)).lower().strip()


import re

def search_player(first, last):
    """Resolve a draftee to a playerId: exact normalized full-name match, else a
    unique last-name match among the results (covers nicknames — 'Ben Kindel'
    for 'Benjamin Kindel', 'Simon (Haoxi) Wang')."""
    first = re.sub(r"\s*\(.*?\)", "", first).strip()
    q = urllib.parse.quote(f"{first} {last}")
    res = get(f"https://search.d3.nhle.com/api/v1/search/player"
              f"?culture=en-us&limit=10&q={q}")
    full = norm(f"{first} {last}")
    exact = [r for r in res if norm(r.get("name", "")) == full]
    if not exact:
        q = urllib.parse.quote(last)
        res = get(f"https://search.d3.nhle.com/api/v1/search/player"
                  f"?culture=en-us&limit=20&q={q}")
        exact = [r for r in res if norm(r.get("name", "")) == full]
        if not exact:
            by_last = [r for r in res
                       if norm(r.get("name", "").split()[-1]) == norm(last)
                       and r.get("playerId")]
            if len(by_last) == 1:
                exact = by_last
    if len(exact) == 1 and exact[0].get("playerId"):
        return int(exact[0]["playerId"])
    return None


def main():
    meta_rows, stat_rows = [], []
    for year in DRAFT_YEARS:
        picks = get(f"https://api-web.nhle.com/v1/draft/picks/{year}/all")["picks"]
        picks = [p for p in picks if p["round"] <= MAX_ROUND]
        print(f"draft {year}: {len(picks)} picks in rounds 1-{MAX_ROUND}")
        for p in picks:
            if "firstName" not in p:      # forfeited/void pick slots have no player
                continue
            first, last = p["firstName"]["default"], p["lastName"]["default"]
            pid = search_player(first, last)
            time.sleep(0.2)
            if pid is None:
                print(f"  UNRESOLVED: {first} {last} ({year} #{p['overallPick']})")
                continue
            d = get(f"https://api-web.nhle.com/v1/player/{pid}/landing")
            time.sleep(0.2)
            nhl_gp = (d.get("careerTotals", {}).get("regularSeason") or {}) \
                .get("gamesPlayed", 0)
            meta_rows.append({
                "playerId": pid, "name": f"{first} {last}",
                "pos": p.get("positionCode", d.get("position", "")),
                "draftYear": year, "overall": p["overallPick"],
                "team": d.get("currentTeamAbbrev", p.get("teamAbbrev", "")),
                "birthDate": d.get("birthDate", ""), "nhl_gp": nhl_gp,
            })
            for s in d.get("seasonTotals", []):
                if (s.get("gameTypeId") == 2 and s.get("season") in STAT_SEASONS
                        and s.get("leagueAbbrev") not in EXCLUDE_LEAGUES
                        and s.get("leagueAbbrev") != "NHL"):
                    stat_rows.append({
                        "playerId": pid, "season": s["season"],
                        "league": s["leagueAbbrev"],
                        "gp": s.get("gamesPlayed", 0), "g": s.get("goals", 0),
                        "a": s.get("assists", 0), "p": s.get("points", 0),
                        "pim": s.get("pim", 0),
                    })

    for path, rows in [("data/prospect_meta.csv", meta_rows),
                       ("data/prospect_stats.csv", stat_rows)]:
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"{path}: {len(rows)} rows")


if __name__ == "__main__":
    main()
