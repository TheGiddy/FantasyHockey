#!/usr/bin/env python3
"""
Fetch the full 2026-27 NHL regular-season schedule (84 games/team, no Olympic
break) and write one row per game to ./data/schedule_20262027.csv.

Walks the api-web weekly schedule endpoint from the regular-season start date
to the end date, deduping on game id (weeks can overlap at boundaries).

Usage: python fetch_schedule.py
"""
import csv, json, os, time, urllib.request
from datetime import date, timedelta

SEASON = 20262027
START = date(2026, 9, 29)
OUT = f"data/schedule_{SEASON}.csv"

os.makedirs("data", exist_ok=True)


def get(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except Exception as e:
            if i == tries - 1:
                raise
            print(f"  retry {i+1} after error: {e}")
            time.sleep(2 * (i + 1))


def main():
    games, seen = [], set()
    day = START
    end = None
    while end is None or day <= end:
        data = get(f"https://api-web.nhle.com/v1/schedule/{day.isoformat()}")
        if end is None:
            end = date.fromisoformat(data["regularSeasonEndDate"])
            print(f"regular season: {data['regularSeasonStartDate']} -> {end}")
        for d in data.get("gameWeek", []):
            for g in d.get("games", []):
                if g.get("gameType") != 2 or g["id"] in seen:
                    continue
                seen.add(g["id"])
                games.append({
                    "gameId": g["id"],
                    "date": d["date"],
                    "away": g["awayTeam"]["abbrev"],
                    "home": g["homeTeam"]["abbrev"],
                })
        day += timedelta(days=7)
        time.sleep(0.25)

    games.sort(key=lambda g: (g["date"], g["gameId"]))
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["gameId", "date", "away", "home"])
        w.writeheader()
        w.writerows(games)

    teams = {g["home"] for g in games} | {g["away"] for g in games}
    per_team = {t: 0 for t in teams}
    for g in games:
        per_team[g["home"]] += 1
        per_team[g["away"]] += 1
    bad = {t: n for t, n in per_team.items() if n != 84}
    print(f"{OUT}: {len(games)} games, {len(teams)} teams")
    if bad:
        print(f"  WARNING: teams without 84 games: {bad}")


if __name__ == "__main__":
    main()
