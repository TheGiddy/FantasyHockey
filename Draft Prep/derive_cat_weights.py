#!/usr/bin/env python3
"""
Derive skater category-leverage weights for the projection model's z-sum,
using BOTH completed seasons (2024-25 and 2025-26) rather than 2025-26 alone.

Why both: 2025-26 was a Twin-Daddy sell year. League-wide category closeness
is robust to one team selling (TD is 1 of 8), but a single season is noisy —
e.g. HIT leverage was suppressed in the sell year (0.87 vs 1.05 contending).
Pooling both seasons de-noises the weights. See
`output/moves_matchups_analysis.md` and the league-diagnosis memory.

Method (same as analyze_league_2025.py): for each cat, per week, the mean
absolute pairwise value difference between teams normalized by the weekly
mean = relative margin (small = coin-flip = high leverage). Skater weight =
1/sqrt(mean relative margin), normalized to mean 1. Goalie cats stay
unweighted (SV% is hyper-flippable but unpredictable year-over-year).

Writes data/yahoo/cat_weights.csv. Run from ./Draft Prep.
"""
import pandas as pd
import numpy as np

YEARS = [2024, 2025]
SK_CATS = ["G", "A", "PIM", "PPP", "SOG", "HIT", "BLK"]
STAT_ID = {1: "G", 2: "A", 5: "PIM", 8: "PPP", 14: "SOG", 31: "HIT",
           32: "BLK", 19: "W", 24: "SA", 25: "SV", 26: "SV%", 27: "SHO"}


def load_values(year):
    v = pd.read_csv(f"data/yahoo/weekly_cat_values_{year}.csv")
    v["stat"] = pd.to_numeric(v["stat"], errors="coerce").map(STAT_ID).fillna(v["stat"])
    v["value"] = pd.to_numeric(v["value"], errors="coerce")
    v["year"] = year
    return v[v["stat"].isin(SK_CATS)].copy()


def relative_margin(val, cat):
    """Mean-over-weeks of the normalized pairwise value spread for one cat."""
    margins = []
    for _, grp in val[val["stat"] == cat].groupby(["year", "week"]):
        x = grp["value"].dropna().values
        if len(x) < 2 or np.nanmean(x) == 0:
            continue
        diffs = np.abs(x[:, None] - x[None, :])[np.triu_indices(len(x), 1)]
        margins.append(np.mean(diffs) / np.mean(x))
    return np.mean(margins)


def main():
    val = pd.concat([load_values(y) for y in YEARS], ignore_index=True)
    df = pd.DataFrame({"cat": SK_CATS})
    df["rel_margin"] = df["cat"].map(lambda c: relative_margin(val, c))
    df["weight"] = 1 / np.sqrt(df["rel_margin"])
    df["weight"] = (df["weight"] / df["weight"].mean()).round(3)
    df[["cat", "weight"]].to_csv("data/yahoo/cat_weights.csv", index=False)
    print("Skater z-sum weights (both seasons) -> data/yahoo/cat_weights.csv")
    print(df.sort_values("weight", ascending=False).to_string(index=False))


if __name__ == "__main__":
    main()
