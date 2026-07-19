#!/usr/bin/env python3
"""
Per-team fantasy schedule metrics from data/schedule_20262027.csv:

  - off-night games (Mon/Wed/Fri/Sun — light slates where a roster spot is
    usually free) and off-night share
  - streamability: each game weighted by the share of the league NOT playing
    that night (1 - slate_size/16), so a 4-game Wednesday counts ~0.75 and a
    13-game Saturday ~0.19; summed per team. Data-driven version of the
    "usable starts" idea.
  - back-to-back sets (backup-goalie games floor)
  - perfect weeks: 4-game Mon-Sun weeks played entirely on off-nights
  - games + off-night games in each league playoff week

League playoff weeks follow last season's pattern (one week earlier than the
Yahoo default): finals end the Sunday before the NHL season's final week.
Update PLAYOFF_WEEKS when Yahoo publishes the real 2026-27 dates.

Reads:  data/schedule_20262027.csv   (from fetch_schedule.py)
Writes: data/schedule_team_metrics.csv, output/schedule_analysis.md

Run from ./Draft Prep:  python analyze_schedule.py
"""
import csv, os
from collections import defaultdict
from datetime import date, timedelta

SCHED_CSV = "data/schedule_20262027.csv"
METRICS_CSV = "data/schedule_team_metrics.csv"
REPORT_MD = "output/schedule_analysis.md"

OFF_NIGHTS = {0, 2, 4, 6}          # Mon, Wed, Fri, Sun (weekday() numbers)
LEAGUE_TEAMS = 32

# Projected from the 2025-26 league calendar (R1 Mar 16-22, R2 Mar 23-29,
# finals Mar 30-Apr 5) shifted to 2027 Mondays. Not yet confirmed by Yahoo.
PLAYOFF_WEEKS = [
    ("R1", date(2027, 3, 15), date(2027, 3, 21)),
    ("R2", date(2027, 3, 22), date(2027, 3, 28)),
    ("Final", date(2027, 3, 29), date(2027, 4, 4)),
]


def load_games():
    with open(SCHED_CSV, encoding="utf-8") as f:
        return [{"date": date.fromisoformat(r["date"]),
                 "away": r["away"], "home": r["home"]}
                for r in csv.DictReader(f)]


def monday_of(d):
    return d - timedelta(days=d.weekday())


def analyze(games):
    slate = defaultdict(int)                 # date -> games that night
    for g in games:
        slate[g["date"]] += 1

    team_dates = defaultdict(list)           # team -> sorted game dates
    for g in games:
        team_dates[g["home"]].append(g["date"])
        team_dates[g["away"]].append(g["date"])

    rows = []
    for team, dates in team_dates.items():
        dates.sort()
        off = [d for d in dates if d.weekday() in OFF_NIGHTS]
        stream = sum(1 - slate[d] / LEAGUE_TEAMS * 2 for d in dates)
        b2b = sum(1 for a, b in zip(dates, dates[1:]) if (b - a).days == 1)

        by_week = defaultdict(list)
        for d in dates:
            by_week[monday_of(d)].append(d)
        perfect = sum(1 for wk in by_week.values()
                      if len(wk) == 4 and all(d.weekday() in OFF_NIGHTS for d in wk))

        row = {"team": team, "games": len(dates),
               "offnight": len(off),
               "offnight_pct": round(100 * len(off) / len(dates), 1),
               "streamability": round(stream, 1),
               "b2b_sets": b2b, "perfect_weeks": perfect}
        for name, lo, hi in PLAYOFF_WEEKS:
            wk = [d for d in dates if lo <= d <= hi]
            row[f"po_{name}_g"] = len(wk)
            row[f"po_{name}_off"] = sum(1 for d in wk if d.weekday() in OFF_NIGHTS)
        row["po_total_g"] = sum(row[f"po_{n}_g"] for n, _, _ in PLAYOFF_WEEKS)
        rows.append(row)

    rows.sort(key=lambda r: -r["streamability"])
    return rows, slate


def write_csv(rows):
    with open(METRICS_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def md_table(rows, cols, headers):
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join("---" for _ in headers) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    return "\n".join(out)


def write_report(rows, slate):
    night_avg = defaultdict(list)
    for d, n in slate.items():
        night_avg[d.weekday()].append(n)
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    slate_line = ", ".join(
        f"{day_names[wd]} {sum(v)/len(v):.1f}" for wd, v in sorted(night_avg.items()))

    fin = sorted(rows, key=lambda r: (-r["po_Final_g"], -r["po_Final_off"]))
    po = sorted(rows, key=lambda r: -r["po_total_g"])
    b2b = sorted(rows, key=lambda r: -r["b2b_sets"])
    po_weeks = ", ".join(f"{n} {lo.isoformat()}..{hi.isoformat()}"
                         for n, lo, hi in PLAYOFF_WEEKS)

    parts = [
        "# 2026-27 schedule analysis (fantasy)",
        "",
        f"84-game season, no Olympic break. Avg games by night: {slate_line}.",
        f"Off-nights = Mon/Wed/Fri/Sun. League playoff weeks (projected from "
        f"last season's calendar, **confirm when Yahoo posts them**): {po_weeks}.",
        "",
        "## Streamability / off-nights (full season)",
        "",
        "Streamability weights each game by the share of the league idle that "
        "night — a proxy for how often the game fills an open roster spot.",
        "",
        md_table(rows, ["team", "games", "offnight", "offnight_pct",
                        "streamability", "perfect_weeks"],
                 ["Team", "GP", "Off-night", "Off %", "Stream", "Perfect wks"]),
        "",
        "## League playoff weeks",
        "",
        md_table(po, ["team", "po_R1_g", "po_R1_off", "po_R2_g", "po_R2_off",
                      "po_Final_g", "po_Final_off", "po_total_g"],
                 ["Team", "R1", "R1 off", "R2", "R2 off",
                  "Final", "Final off", "Total"]),
        "",
        "Best finals week (games, then off-nights): " +
        ", ".join(f"{r['team']} ({r['po_Final_g']}g/{r['po_Final_off']}off)"
                  for r in fin[:6]),
        "",
        "## Back-to-back sets (backup-goalie games floor)",
        "",
        md_table(b2b, ["team", "b2b_sets"], ["Team", "B2B sets"]),
        "",
    ]
    os.makedirs("output", exist_ok=True)
    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))


def main():
    games = load_games()
    rows, slate = analyze(games)
    write_csv(rows)
    write_report(rows, slate)
    top, bot = rows[0], rows[-1]
    print(f"{METRICS_CSV}: {len(rows)} teams")
    print(f"  most streamable: {top['team']} ({top['offnight']} off-nights, "
          f"score {top['streamability']})")
    print(f"  least: {bot['team']} ({bot['offnight']} off-nights, "
          f"score {bot['streamability']})")


if __name__ == "__main__":
    main()
