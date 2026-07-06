#!/usr/bin/env python3
"""
v2 data fetcher — pulls the inputs the v1 model lacked: multi-season stats,
TOI splits, PP deployment, bios (age), sh% history, and MoneyPuck xG/GSAx.
Writes CSVs to ./data/ for the projection model.

Usage: python3 fetch_nhl_data_v2.py
"""
import json, csv, os, time, urllib.request

os.makedirs("data", exist_ok=True)

# Rolling 3-season window for weighted rates (project convention: COVID
# seasons 2019-20/2020-21 excluded from projection baselines).
MODEL_SEASONS = [20232024, 20242025, 20252026]
# Extra seasons, summary-only, for career sh% regression (goals roadmap item).
SHPCT_HISTORY_SEASONS = [20182019, 20192020, 20202021, 20212022, 20222023]

PAGE = 100

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

def fetch_report(kind, name, season):
    """Page through one stats-API report for one season, return rows."""
    base = f"https://api.nhle.com/stats/rest/en/{kind}/{name}"
    rows, start = [], 0
    while True:
        url = (f"{base}?isAggregate=false&isGame=false&limit={PAGE}&start={start}"
               f"&cayenneExp=seasonId={season}%20and%20gameTypeId=2")
        data = get(url)["data"]
        rows.extend(data)
        if len(data) < PAGE:
            break
        start += PAGE
        time.sleep(0.25)
    return rows

def write_csv(path, rows):
    if not rows:
        print(f"  WARNING: no rows for {path}")
        return
    # union of keys across rows, first row's order first (API rows are uniform,
    # but don't silently drop columns if they aren't)
    fields = list(rows[0].keys())
    for r in rows[1:]:
        for k in r:
            if k not in fields:
                fields.append(k)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

# ---- 1. NHL stats API: skater reports x 3 seasons ----
SKATER_REPORTS = {
    "summary": "G/A/PPP/SOG/PIM, GP, TOI/gm, sh%",
    "realtime": "hits, blocked shots, giveaways/takeaways",
    "timeonice": "ES/PP/SH TOI splits",
    "powerplay": "PP TOI + PP production (PP1-share modeling)",
    "penalties": "PIM detail (majors vs minors)",
    "bios": "DOB, position, height/weight, draft year, current team",
}

def nhl_skaters():
    for season in MODEL_SEASONS:
        for name in SKATER_REPORTS:
            rows = fetch_report("skater", name, season)
            write_csv(f"data/nhl_skater_{name}_{season}.csv", rows)
            print(f"skater {name} {season}: {len(rows)} rows")

# ---- 2. NHL stats API: goalie reports x 3 seasons ----
GOALIE_REPORTS = {
    "summary": "W, SV%, SO, GP/GS",
    "advanced": "quality starts, goals-against detail",
    "bios": "DOB, current team",
}

def nhl_goalies():
    for season in MODEL_SEASONS:
        for name in GOALIE_REPORTS:
            rows = fetch_report("goalie", name, season)
            write_csv(f"data/nhl_goalie_{name}_{season}.csv", rows)
            print(f"goalie {name} {season}: {len(rows)} rows")

# ---- 3. Career sh% history: summary-only for older seasons ----
def shpct_history():
    for season in SHPCT_HISTORY_SEASONS:
        rows = fetch_report("skater", "summary", season)
        keep = ["playerId", "skaterFullName", "seasonId", "gamesPlayed",
                "goals", "shots", "shootingPct"]
        slim = [{k: r.get(k) for k in keep} for r in rows]
        write_csv(f"data/nhl_shpct_{season}.csv", slim)
        print(f"sh% history {season}: {len(slim)} rows")

# ---- 4. MoneyPuck: xG, GSAx, per-60 rates ----
def moneypuck():
    for season in MODEL_SEASONS:
        yr = str(season)[:4]
        for kind in ("skaters", "goalies"):
            url = f"https://moneypuck.com/moneypuck/playerData/seasonSummary/{yr}/regular/{kind}.csv"
            dest = f"data/moneypuck_{kind}_{yr}.csv"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as f:
                f.write(r.read())
            print(f"moneypuck {kind} {yr}: saved")

if __name__ == "__main__":
    t0 = time.time()
    nhl_skaters()
    nhl_goalies()
    shpct_history()
    moneypuck()
    print(f"Done in {time.time()-t0:.0f}s. Feed ./data/*.csv into projection model v2.")
