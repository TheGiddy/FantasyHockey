#!/usr/bin/env python3
"""
Yahoo draft-prep fetcher — pulls the league-context data the NHL API can't:
  1. Position eligibility (Yahoo dual-eligibility != NHL position codes)
  2. 2025-26 weekly matchup category values + stat winners (category
     closeness weighting + Twin Daddy banger-deficit diagnosis)
  3. Draft results 2023-2025 (this room's market tendencies by round)

Writes CSVs to ./data/yahoo/. ADP/pre-draft ranks are NOT pulled here —
Yahoo publishes those closer to September; re-check before the draft.

Usage: python fetch_yahoo_draftprep.py   (needs ../oauth2.json)
"""
import csv, json, os, time
from yahoo_oauth import OAuth2
import yahoo_fantasy_api as yfa

YEAR = 2025            # 2025-26 (completed season)
DRAFT_YEARS = [2023, 2024, 2025]
OUT = "data/yahoo"
os.makedirs(OUT, exist_ok=True)

oauth = OAuth2(None, None, from_file="../oauth2.json")
game = yfa.game.Game(oauth, "nhl")

def get_league(year):
    ids = game.league_ids(year=year)
    if not ids:
        return None
    return yfa.league.League(oauth, ids[0])

def write_csv(path, rows, fields):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"{path}: {len(rows)} rows")

# ---- 1. position eligibility: taken players + all free agents ----
def eligibility(lg):
    players = {}
    for p in lg.taken_players():
        players[p["player_id"]] = p
    for pos in ["C", "LW", "RW", "D", "G"]:
        for p in lg.free_agents(pos):
            players.setdefault(p["player_id"], p)
        print(f"  free agents {pos}: cumulative {len(players)}")
    rows = []
    for pid, p in players.items():
        elig = [e for e in p.get("eligible_positions", []) if e not in ("Util", "BN", "IR", "IR+")]
        rows.append({
            "yahoo_id": pid,
            "name": p.get("name", ""),
            "eligible_positions": "/".join(elig),
            "n_positions": len([e for e in elig if e != "G"]) or (1 if "G" in elig else 0),
            "position_type": p.get("position_type", ""),
            "percent_owned": p.get("percent_owned", 0),
            "status": p.get("status", ""),
        })
    write_csv(f"{OUT}/eligibility.csv", rows,
              ["yahoo_id","name","eligible_positions","n_positions","position_type","percent_owned","status"])

# ---- 2. weekly matchup category values + stat winners ----
def weekly_categories(lg):
    # yfa's stat_categories() drops stat_id, so hardcode Yahoo's NHL ids
    stat_map = {"1":"G","2":"A","5":"PIM","8":"PPP","14":"SOG","31":"HIT",
                "32":"BLK","19":"W","24":"SA","25":"SV","26":"SV%","27":"SHO"}

    end_week = int(lg.settings().get("end_week", 24))
    team_names = {tk: t["name"] for tk, t in lg.teams().items()}

    values, winners = [], []
    for wk in range(1, end_week + 1):
        try:
            raw = lg.matchups(wk)
        except Exception as e:
            print(f"  week {wk}: FAILED ({e})")
            continue
        league_node = raw["fantasy_content"]["league"]
        sb = next((n["scoreboard"] for n in league_node if isinstance(n, dict) and "scoreboard" in n), None)
        if sb is None:
            continue
        matchups = sb["0"]["matchups"]
        for mk, mv in matchups.items():
            if mk == "count" or not isinstance(mv, dict):
                continue
            m = mv["matchup"]
            # stat winners
            for swin in m.get("stat_winners", []):
                sw = swin.get("stat_winner", {})
                winners.append({
                    "week": wk,
                    "stat": stat_map.get(str(sw.get("stat_id")), sw.get("stat_id")),
                    "winner": team_names.get(sw.get("winner_team_key"), sw.get("winner_team_key", "")),
                    "tied": int(bool(sw.get("is_tied", 0))),
                })
            # per-team category values
            teams_node = m["0"]["teams"]
            for tk, tv in teams_node.items():
                if tk == "count" or not isinstance(tv, dict):
                    continue
                tarr = tv["team"]
                meta, stats_node = tarr[0], tarr[1]
                tkey = next((d["team_key"] for d in meta if isinstance(d, dict) and "team_key" in d), "")
                for st in stats_node.get("team_stats", {}).get("stats", []):
                    s = st["stat"]
                    values.append({
                        "week": wk,
                        "team": team_names.get(tkey, tkey),
                        "stat": stat_map.get(str(s.get("stat_id")), s.get("stat_id")),
                        "value": s.get("value", ""),
                    })
        print(f"  week {wk}: ok")
        time.sleep(0.2)
    write_csv(f"{OUT}/weekly_cat_values_{YEAR}.csv", values, ["week","team","stat","value"])
    write_csv(f"{OUT}/weekly_stat_winners_{YEAR}.csv", winners, ["week","stat","winner","tied"])

# ---- 3. draft results with names, 3 years ----
def drafts():
    for yr in DRAFT_YEARS:
        lg = get_league(yr)
        if lg is None:
            print(f"  no league for {yr}")
            continue
        team_names = {tk: t["name"] for tk, t in lg.teams().items()}
        picks = lg.draft_results()
        ids = sorted({int(p["player_id"]) for p in picks})
        names = {}
        for i in range(0, len(ids), 25):
            batch = ids[i:i+25]
            try:
                for d in lg.player_details(batch):
                    names[int(d["player_id"])] = d.get("name", {}).get("full", "")
            except Exception as e:
                print(f"  player_details batch failed ({e})")
            time.sleep(0.3)
        rows = [{
            "year": yr,
            "round": int(p["round"]),
            "pick": int(p["pick"]),
            "team": team_names.get(p["team_key"], p["team_key"]),
            "yahoo_id": int(p["player_id"]),
            "player": names.get(int(p["player_id"]), ""),
        } for p in picks]
        rows.sort(key=lambda r: (r["round"], r["pick"]))
        write_csv(f"{OUT}/draft_{yr}.csv", rows, ["year","round","pick","team","yahoo_id","player"])

if __name__ == "__main__":
    lg = get_league(YEAR)
    print(f"Connected: {lg.settings().get('name')} ({YEAR})")
    print("== eligibility ==")
    eligibility(lg)
    print("== weekly categories ==")
    weekly_categories(lg)
    print("== draft history ==")
    drafts()
    print("Done.")
