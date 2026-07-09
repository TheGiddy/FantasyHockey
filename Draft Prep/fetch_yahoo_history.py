#!/usr/bin/env python3
"""
Yahoo history fetcher — pulls two completed seasons of league activity that
feed Twin-Daddy draft/keeper strategy:
  1. Transactions (add/drop/trade/commish) with player names, movement,
     source/destination teams, and a Twin-Daddy involvement flag.
  2. Weekly matchup category VALUES + stat WINNERS (same schema as
     fetch_yahoo_draftprep.py) PLUS a per-team-per-week matchup RESULT
     (W/L/T + cats won/lost/tied) derived from the pairing's stat winners.

Years: Yahoo game years 2024 (2024-25) and 2025 (2025-26).
Writes CSVs to ./data/yahoo/. Run from ./Draft Prep with ../oauth2.json.

Usage: python fetch_yahoo_history.py
"""
import csv, os, time
from datetime import datetime, timezone
from yahoo_oauth import OAuth2
import yahoo_fantasy_api as yfa

YEARS = [2024, 2025]
OUT = "data/yahoo"
os.makedirs(OUT, exist_ok=True)

# yfa's stat_categories() drops stat_id, so hardcode Yahoo's NHL ids.
STAT_MAP = {"1":"G","2":"A","5":"PIM","8":"PPP","14":"SOG","31":"HIT",
            "32":"BLK","19":"W","24":"SA","25":"SV","26":"SV%","27":"SHO"}
# The 10 scoring categories (SA/SV are tracked but not scored).
SCORING = {"G","A","PIM","PPP","SOG","HIT","BLK","W","SV%","SHO"}

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


def find_td_key(team_names):
    """Twin Daddy's team_key differs per season; match by (loose) name."""
    for tk, name in team_names.items():
        if "twin daddy" in str(name).strip().lower():
            return tk
    return None


def unix_to_date(ts):
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return ""


# ---- 1. transactions ----
def _norm_tdata(holder):
    """transaction_data arrives as a list[dict] or a bare dict — normalize."""
    td = holder.get("transaction_data") if isinstance(holder, dict) else None
    if isinstance(td, list):
        return td[0] if td else {}
    return td or {}


def _player_meta(meta_list):
    pid = pname = ""
    for d in meta_list:
        if not isinstance(d, dict):
            continue
        if "player_id" in d:
            pid = d["player_id"]
        if "name" in d and isinstance(d["name"], dict):
            pname = d["name"].get("full", "")
    return pid, pname


def _team_of(td, side, team_names):
    key = td.get(f"{side}_team_key", "")
    name = td.get(f"{side}_team_name") or team_names.get(key, "")
    return key, name


MOVEMENT = {"add": "added", "drop": "dropped", "trade": "traded"}


def transactions(lg, year, team_names, td_key):
    txs = lg.transactions("add,drop,trade,commish", "")
    fields = ["year", "transaction_id", "type", "status", "timestamp", "date",
              "player_id", "player", "movement", "source_type", "source_team",
              "destination_type", "destination_team", "involves_td"]
    rows = []
    for tx in txs:
        base = {
            "year": year,
            "transaction_id": tx.get("transaction_id", ""),
            "type": tx.get("type", ""),
            "status": tx.get("status", ""),
            "timestamp": tx.get("timestamp", ""),
            "date": unix_to_date(tx.get("timestamp")),
        }
        pending = []

        # involvement is per-leg: a leg involves TD iff td_key is that leg's own
        # source or destination. (A trade can bundle legs between other teams —
        # flagging the whole transaction would falsely attribute those to TD.)
        players = tx.get("players")
        if isinstance(players, dict):
            for k, v in players.items():
                if k == "count" or not isinstance(v, dict):
                    continue
                parr = v.get("player")
                if not parr or len(parr) < 2:
                    continue
                pid, pname = _player_meta(parr[0])
                td = _norm_tdata(parr[1])
                s_key, s_name = _team_of(td, "source", team_names)
                d_key, d_name = _team_of(td, "destination", team_names)
                pending.append({
                    **base,
                    "player_id": pid,
                    "player": pname,
                    "movement": MOVEMENT.get(td.get("type"), td.get("type", "")),
                    "source_type": td.get("source_type", ""),
                    "source_team": s_name,
                    "destination_type": td.get("destination_type", ""),
                    "destination_team": d_name,
                    "involves_td": 1 if td_key in (s_key, d_key) else 0,
                })

        # traded draft picks (keeper leagues trade these; capture them)
        for pk in tx.get("picks", []) or []:
            p = pk.get("pick", {}) if isinstance(pk, dict) else {}
            if not p:
                continue
            s_key, s_name = p.get("source_team_key", ""), p.get("source_team_name", "")
            d_key, d_name = p.get("destination_team_key", ""), p.get("destination_team_name", "")
            pending.append({
                **base,
                "player_id": "",
                "player": f"Draft pick R{p.get('round','?')}",
                "movement": "pick_traded",
                "source_type": "team",
                "source_team": s_name,
                "destination_type": "team",
                "destination_team": d_name,
                "involves_td": 1 if td_key in (s_key, d_key) else 0,
            })

        if pending:
            rows.extend(pending)
        else:  # keep empty commish transactions visible
            rows.append({**base, "player": "", "movement": tx.get("type", ""),
                         "involves_td": 0})

    rows.sort(key=lambda r: int(r["timestamp"] or 0))
    write_csv(f"{OUT}/transactions_{year}.csv", rows, fields)


# ---- 2. weekly matchup values, winners, and per-team results ----
def weekly(lg, year, team_names):
    end_week = int(lg.settings().get("end_week", 24))
    values, winners, results = [], [], []

    for wk in range(1, end_week + 1):
        try:
            raw = lg.matchups(wk)
        except Exception as e:
            print(f"  week {wk}: FAILED ({e})")
            continue
        league_node = raw["fantasy_content"]["league"]
        sb = next((n["scoreboard"] for n in league_node
                   if isinstance(n, dict) and "scoreboard" in n), None)
        if sb is None:
            print(f"  week {wk}: no scoreboard, skipping")
            continue
        matchups = sb["0"]["matchups"]
        for mk, mv in matchups.items():
            if mk == "count" or not isinstance(mv, dict):
                continue
            m = mv["matchup"]

            # collect this pairing's teams and stat winners together so we can
            # derive a per-team W/L/T result from the pairing alone.
            pair_keys = []
            teams_node = m["0"]["teams"]
            for tk, tv in teams_node.items():
                if tk == "count" or not isinstance(tv, dict):
                    continue
                tarr = tv["team"]
                meta, stats_node = tarr[0], tarr[1]
                tkey = next((d["team_key"] for d in meta
                             if isinstance(d, dict) and "team_key" in d), "")
                pair_keys.append(tkey)
                for st in stats_node.get("team_stats", {}).get("stats", []):
                    s = st["stat"]
                    values.append({
                        "week": wk,
                        "team": team_names.get(tkey, tkey),
                        "stat": STAT_MAP.get(str(s.get("stat_id")), s.get("stat_id")),
                        "value": s.get("value", ""),
                    })

            pair_won = {k: 0 for k in pair_keys}
            pair_tied = 0
            for swin in m.get("stat_winners", []):
                sw = swin.get("stat_winner", {})
                stat = STAT_MAP.get(str(sw.get("stat_id")), sw.get("stat_id"))
                wkey = sw.get("winner_team_key")
                tied = int(bool(sw.get("is_tied", 0)))
                winners.append({
                    "week": wk,
                    "stat": stat,
                    "winner": team_names.get(wkey, wkey or ""),
                    "tied": tied,
                })
                if stat not in SCORING:
                    continue
                if tied:
                    pair_tied += 1
                elif wkey in pair_won:
                    pair_won[wkey] += 1

            if len(pair_keys) == 2:
                a, b = pair_keys
                for me, opp in ((a, b), (b, a)):
                    won, lost = pair_won[me], pair_won[opp]
                    result = "win" if won > lost else "loss" if won < lost else "tie"
                    results.append({
                        "week": wk,
                        "team": team_names.get(me, me),
                        "opponent": team_names.get(opp, opp),
                        "cats_won": won,
                        "cats_lost": lost,
                        "cats_tied": pair_tied,
                        "result": result,
                    })
            else:
                print(f"  week {wk}: matchup had {len(pair_keys)} teams, "
                      "results row skipped")
        print(f"  week {wk}: ok")
        time.sleep(0.2)

    write_csv(f"{OUT}/weekly_cat_values_{year}.csv", values,
              ["week", "team", "stat", "value"])
    write_csv(f"{OUT}/weekly_stat_winners_{year}.csv", winners,
              ["week", "stat", "winner", "tied"])
    write_csv(f"{OUT}/weekly_matchup_results_{year}.csv", results,
              ["week", "team", "opponent", "cats_won", "cats_lost",
               "cats_tied", "result"])


if __name__ == "__main__":
    for year in YEARS:
        lg = get_league(year)
        if lg is None:
            print(f"== {year}: no league found, skipping ==")
            continue
        team_names = {tk: t["name"] for tk, t in lg.teams().items()}
        td_key = find_td_key(team_names)
        if td_key is None:
            raise RuntimeError(
                f"{year}: could not find Twin Daddy by name; teams were "
                f"{list(team_names.values())}")
        print(f"== {year}: {lg.settings().get('name')} — "
              f"Twin Daddy key = {td_key} ==")
        print("-- transactions --")
        transactions(lg, year, team_names, td_key)
        print("-- weekly matchups --")
        weekly(lg, year, team_names)
        time.sleep(0.3)
    print("Done.")
