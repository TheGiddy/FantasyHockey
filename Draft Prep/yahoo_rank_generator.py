#!/usr/bin/env python3
"""
yahoo_rank_generator.py — generate Yahoo-equivalent player rankings from NHL API data.

FINDING (fit on 95 skaters + 25 goalies from the league's actual 2025-26 Yahoo ranks):
  Yahoo's "Season Rank" in a categories league is an EQUAL-WEIGHT Z-SCORE SUM
  over the league's categories, computed per position group, then interleaved.
  Fit quality: skaters Spearman rho = 0.9987 (1.1% pairwise violations),
  goalies rho = 0.9985. Learned weights were statistically indistinguishable
  from equal (skaters 0.136-0.151 across 7 cats; goalies 0.32-0.35 across 3).

So to build your own rankings you do NOT need Yahoo's formula — you need:
  1. category totals per player (NHL API / your projections)
  2. a sensible normalization pool (see POOL_NOTE below)
  3. z-sum per group, then merge goalies via the fitted scale (alpha, beta)

POOL_NOTE: z-scores depend on the population mean/sd. Yahoo appears to normalize
over the fantasy-relevant pool, not all skaters. Filter to roughly the top
~250 skaters / ~60 goalies by ice time or GP before computing z-scores.
Rank order is moderately sensitive to this choice; ±50 pool size shifts
mid-tier players a few spots.

USAGE with fetch_nhl_data_v2.py outputs:
  python3 yahoo_rank_generator.py
Reads ./data/nhl_summary.csv, ./data/nhl_realtime.csv, ./data/nhl_goalies.csv
Writes ./my_rankings.csv

To rank PROJECTED seasons instead of actuals, feed projection lines through
rank_skaters()/rank_goalies() directly — that's the real payoff: draft-day
ranks in Yahoo's own currency, but built from YOUR model.
"""
import csv, json
from statistics import mean, pstdev

SKATER_CATS = ["G", "A", "PIM", "PPP", "SOG", "HIT", "BLK"]
GOALIE_CATS = ["W", "SVPCT", "SHO"]
# goalie->skater score mapping fitted from 25 anchor goalies with known overall ranks
ALPHA, BETA = 0.9271, -1.1437

def zsum(rows, cats):
    stats = {c: [r[c] for r in rows] for c in cats}
    mu = {c: mean(v) for c, v in stats.items()}
    sd = {c: pstdev(v) or 1.0 for c, v in stats.items()}
    for r in rows:
        r["score"] = sum((r[c] - mu[c]) / sd[c] for c in cats)
    return rows

def rank_skaters(rows):
    """rows: dicts with name + SKATER_CATS (numeric). Returns rows with score."""
    return zsum(rows, SKATER_CATS)

def rank_goalies(rows):
    """rows: dicts with name + GOALIE_CATS. Score mapped onto skater scale."""
    rows = zsum(rows, GOALIE_CATS)
    for r in rows:
        r["score"] = r["score"] * ALPHA + BETA
    return rows

def merge_and_rank(skaters, goalies):
    allp = skaters + goalies
    allp.sort(key=lambda r: -r["score"])
    for i, r in enumerate(allp, 1):
        r["rank"] = i
    return allp

def _f(row, *keys, default=0.0):
    for k in keys:
        if k in row and row[k] not in ("", None):
            return float(row[k])
    return default

def load_from_nhl_csvs(datadir="data", min_gp_skater=40, min_gp_goalie=20):
    """Merge NHL API summary (G/A/PIM/PPP/SOG) with realtime (HIT/BLK) by playerId."""
    rt = {}
    with open(f"{datadir}/nhl_realtime.csv") as f:
        for row in csv.DictReader(f):
            rt[row["playerId"]] = row
    skaters = []
    with open(f"{datadir}/nhl_summary.csv") as f:
        for row in csv.DictReader(f):
            if _f(row, "gamesPlayed") < min_gp_skater:
                continue
            r = rt.get(row["playerId"], {})
            skaters.append({
                "name": row.get("skaterFullName", row.get("playerId")),
                "pos": row.get("positionCode", ""),
                "G": _f(row, "goals"), "A": _f(row, "assists"),
                "PIM": _f(row, "penaltyMinutes"),
                "PPP": _f(row, "ppPoints", "powerPlayPoints"),
                "SOG": _f(row, "shots"),
                "HIT": _f(r, "hits"), "BLK": _f(r, "blockedShots"),
            })
    goalies = []
    with open(f"{datadir}/nhl_goalies.csv") as f:
        for row in csv.DictReader(f):
            if _f(row, "gamesPlayed") < min_gp_goalie:
                continue
            goalies.append({
                "name": row.get("goalieFullName", row.get("playerId")), "pos": "G",
                "W": _f(row, "wins"), "SVPCT": _f(row, "savePct"),
                "SHO": _f(row, "shutouts"),
            })
    return skaters, goalies

if __name__ == "__main__":
    skaters, goalies = load_from_nhl_csvs()
    ranked = merge_and_rank(rank_skaters(skaters), rank_goalies(goalies))
    with open("my_rankings.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["rank", "name", "pos", "score"])
        for r in ranked:
            w.writerow([r["rank"], r["name"], r["pos"], round(r["score"], 3)])
    print(f"Wrote my_rankings.csv ({len(ranked)} players)")
    for r in ranked[:15]:
        print(f'{r["rank"]:3d}  {r["name"]:24s} {r["pos"]:3s} {r["score"]:+.2f}')
