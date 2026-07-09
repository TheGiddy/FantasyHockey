#!/usr/bin/env python3
"""
Twin-Daddy moves + matchup analysis across the two completed seasons
(2024-25 and 2025-26). Feeds draft/keeper strategy.

Reads ./data/yahoo/{transactions,weekly_matchup_results,weekly_cat_values}_{2024,2025}.csv
from fetch_yahoo_history.py.
Output: ./output/moves_matchups_analysis.md (+ stdout)
"""
import os
import pandas as pd
import numpy as np

MY_TEAM = "Twin Daddy"
YEARS = [2024, 2025]
LABEL = {2024: "2024-25", 2025: "2025-26"}
CATS = ["G", "A", "PIM", "PPP", "SOG", "HIT", "BLK", "W", "SV%", "SHO"]
KEEPER_CUTOFF = {2024: "2025-03-15", 2025: "2026-03-15"}  # Mar 15 deadline

os.makedirs("output", exist_ok=True)


def is_td(series):
    return series.fillna("").str.lower().str.contains("twin daddy")


# ---------- close-loss rule ----------
# A cat TD lost that a plausibly small swing could have flipped. Thresholds
# reflect how each cat accrues: rare/goalie cats flip on 1, skater counting
# cats on ~2, high-volume cats on a ~10% margin, SV% on a 0.010 delta.
def is_close_loss(cat, td_val, opp_val):
    m = opp_val - td_val
    if m <= 0:
        return False
    if cat == "SV%":
        return m <= 0.010
    if cat in ("W", "SHO", "PPP"):
        return m <= 1
    if cat in ("G", "A"):
        return m <= 2
    return m <= 0.10 * max(1.0, (td_val + opp_val) / 2)  # SOG, HIT, BLK, PIM


def load(year):
    tx = pd.read_csv(f"data/yahoo/transactions_{year}.csv")
    res = pd.read_csv(f"data/yahoo/weekly_matchup_results_{year}.csv")
    val = pd.read_csv(f"data/yahoo/weekly_cat_values_{year}.csv")
    val["value"] = pd.to_numeric(val["value"], errors="coerce")
    return tx, res, val


def moves_section(tx, year, lines):
    lines.append(f"### {LABEL[year]} moves\n")
    td = tx[tx["involves_td"] == 1].copy()
    if td.empty:
        lines.append("_No Twin Daddy transactions found._\n")
        return {}

    counts = td["movement"].value_counts().to_dict()
    n_add = counts.get("added", 0)
    n_drop = counts.get("dropped", 0)
    n_trade_rows = counts.get("traded", 0)
    n_pick = counts.get("pick_traded", 0)
    n_trades = td[td["movement"].isin(["traded", "pick_traded"])]["transaction_id"].nunique()
    n_addrop_tx = td[td["movement"].isin(["added", "dropped"])]["transaction_id"].nunique()

    lines.append(f"- Transactions involving TD: **{td['transaction_id'].nunique()}** "
                 f"({n_addrop_tx} add/drop, {n_trades} trades)")
    lines.append(f"- Players added: **{n_add}**, dropped: **{n_drop}**, "
                 f"traded (players): **{n_trade_rows}**, picks traded: **{n_pick}**")

    # churn: adds per matchup week (season ~ nweeks)
    weeks = pd.read_csv(f"data/yahoo/weekly_matchup_results_{year}.csv")["week"].nunique()
    per_wk = f"{n_add / weeks:.1f}" if weeks else "n/a"
    lines.append(f"- Waiver/streaming churn: **{per_wk} adds per week** "
                 f"over {weeks} weeks")

    # most-added / most-dropped players (repeat streaming)
    adds = td[td["movement"] == "added"]["player"].value_counts()
    drops = td[td["movement"] == "dropped"]["player"].value_counts()
    top_add = ", ".join(f"{n}x {p}" for p, n in adds[adds > 1].items()) or "none repeated"
    top_drop = ", ".join(f"{n}x {p}" for p, n in drops[drops > 1].items()) or "none repeated"
    lines.append(f"- Most re-added: {top_add}")
    lines.append(f"- Most re-dropped: {top_drop}")

    # post-deadline (not keeper-eligible) acquisitions
    cutoff = KEEPER_CUTOFF[year]
    # only INCOMING moves matter — a player TD traded away isn't an acquisition
    late = td[(td["date"] > cutoff) &
              ((td["movement"] == "added") |
               ((td["movement"] == "traded") & is_td(td["destination_team"])))]
    if len(late):
        names = ", ".join(f"{r.player} ({r.date})" for r in late.itertuples())
        lines.append(f"- **After Mar 15 (NOT keeper-eligible):** {names}")
    else:
        lines.append(f"- After Mar 15 (not keeper-eligible): none")
    lines.append("")

    # chronological log, one row per transaction
    lines.append(f"#### {LABEL[year]} chronological move log\n")
    lines.append("|date|type|acquired / added|sent / dropped|")
    lines.append("|---|---|---|---|")
    for tid, g in td.groupby("transaction_id"):
        g = g.sort_values("movement")
        date = g["date"].iloc[0]
        acq = g[(g["movement"] == "added") |
                ((g["movement"].isin(["traded", "pick_traded"])) & is_td(g["destination_team"]))]["player"].tolist()
        snt = g[(g["movement"] == "dropped") |
                ((g["movement"].isin(["traded", "pick_traded"])) & is_td(g["source_team"]))]["player"].tolist()
        # label from the leg movements (Yahoo's top-level `type` is unreliable
        # for waiver/FA moves); flag post-deadline only when TD acquired someone.
        moves = set(g["movement"])
        if moves & {"traded", "pick_traded"}:
            label = "trade"
        elif {"added", "dropped"} <= moves:
            label = "add/drop"
        elif "added" in moves:
            label = "add"
        elif "dropped" in moves:
            label = "drop"
        else:
            label = g["type"].iloc[0]
        late_flag = " (post-Mar15)" if (date > cutoff and acq) else ""
        lines.append(f"|{date}|{label}{late_flag}|{', '.join(acq)}|{', '.join(snt)}|")
    lines.append("")
    return counts


def matchup_records(lines):
    lines.append("## Matchup records (Twin Daddy)\n")
    lines.append("|season|W|L|T|win%|")
    lines.append("|---|---|---|---|---|")
    combined = {"win": 0, "loss": 0, "tie": 0}
    per_year = {}
    for year in YEARS:
        res = pd.read_csv(f"data/yahoo/weekly_matchup_results_{year}.csv")
        tdr = res[is_td(res["team"])]
        vc = tdr["result"].value_counts().to_dict()
        w, l, t = vc.get("win", 0), vc.get("loss", 0), vc.get("tie", 0)
        per_year[year] = tdr
        for k in combined:
            combined[k] += vc.get(k, 0)
        wp = w / (w + l + t) if (w + l + t) else 0
        lines.append(f"|{LABEL[year]}|{w}|{l}|{t}|{wp:.0%}|")
    cw, cl, ct = combined["win"], combined["loss"], combined["tie"]
    ctot = cw + cl + ct
    lines.append(f"|**combined**|{cw}|{cl}|{ct}|{cw/ctot if ctot else 0:.0%}|")
    lines.append("")
    return per_year


def category_winrate(lines):
    """Per-cat W/L/T for TD across both seasons, from head-to-head cat values."""
    lines.append("## Per-category head-to-head (both seasons combined)\n")
    lines.append("TD value vs that week's opponent, per scoring category.\n")
    tallies = {c: {"w": 0, "l": 0, "t": 0, "close_l": 0} for c in CATS}
    for year in YEARS:
        res = pd.read_csv(f"data/yahoo/weekly_matchup_results_{year}.csv")
        val = pd.read_csv(f"data/yahoo/weekly_cat_values_{year}.csv")
        val["value"] = pd.to_numeric(val["value"], errors="coerce")
        tdr = res[is_td(res["team"])]
        for r in tdr.itertuples():
            wk, opp = r.week, r.opponent
            for c in CATS:
                a = val[(val.week == wk) & (is_td(val.team)) & (val.stat == c)]["value"]
                b = val[(val.week == wk) & (val.team == opp) & (val.stat == c)]["value"]
                if a.empty or b.empty or pd.isna(a.iloc[0]) or pd.isna(b.iloc[0]):
                    continue
                av, bv = float(a.iloc[0]), float(b.iloc[0])
                if av > bv:
                    tallies[c]["w"] += 1
                elif av < bv:
                    tallies[c]["l"] += 1
                    if is_close_loss(c, av, bv):
                        tallies[c]["close_l"] += 1
                else:
                    tallies[c]["t"] += 1

    lines.append("|cat|W|L|T|win%|close losses (flippable)|")
    lines.append("|---|---|---|---|---|---|")
    rows = []
    for c in CATS:
        t = tallies[c]
        tot = t["w"] + t["l"] + t["t"]
        wp = t["w"] / tot if tot else 0
        rows.append((c, t, wp))
    for c, t, wp in sorted(rows, key=lambda x: -x[2]):
        lines.append(f"|{c}|{t['w']}|{t['l']}|{t['t']}|{wp:.0%}|{t['close_l']}|")
    lines.append("")

    strong = [c for c, t, wp in rows if wp >= 0.60]
    weak = [c for c, t, wp in rows if wp <= 0.40]
    lines.append(f"- **Reliable wins (>=60%):** {', '.join(strong) or 'none'}")
    lines.append(f"- **Reliable losses (<=40%):** {', '.join(weak) or 'none'}")
    total_close = sum(t["close_l"] for _, t, _ in rows)
    lines.append(f"- **Flippable category losses across both seasons: {total_close}** "
                 "(cats lost by a margin a small swing could have reversed — "
                 "see thresholds in script).")
    lines.append("")
    return rows


def opponents_and_trends(per_year, lines):
    lines.append("## Opponents & trends\n")
    for year in YEARS:
        tdr = per_year[year].sort_values("week")
        opps = tdr["opponent"].value_counts()
        rep = ", ".join(f"{n}x {o}" for o, n in opps[opps > 1].items()) or "no repeats"
        avg_won = tdr["cats_won"].mean()
        lines.append(f"- **{LABEL[year]}**: avg {avg_won:.1f}/10 cats won per week; "
                     f"faced {tdr['opponent'].nunique()} distinct opponents; "
                     f"repeat opponents: {rep}")
    lines.append("")
    # cross-season swing
    w24 = per_year[2024]["result"].value_counts()
    w25 = per_year[2025]["result"].value_counts()
    lines.append(f"- **Cross-season trend:** {w24.get('win',0)}-{w24.get('loss',0)}-"
                 f"{w24.get('tie',0)} in {LABEL[2024]} vs {w25.get('win',0)}-"
                 f"{w25.get('loss',0)}-{w25.get('tie',0)} in {LABEL[2025]} "
                 f"(avg cats won {per_year[2024]['cats_won'].mean():.1f} -> "
                 f"{per_year[2025]['cats_won'].mean():.1f}).")
    lines.append("")


def main():
    lines = ["# Twin Daddy — moves & matchups (2024-25 and 2025-26)\n"]

    lines.append("## Transaction / moves log\n")
    lines.append("_Keeper context: acquisitions after **March 15** are not "
                 "keeper-eligible; flagged below._\n")
    for year in YEARS:
        tx, _, _ = load(year)
        moves_section(tx, year, lines)

    per_year = matchup_records(lines)
    category_winrate(lines)
    opponents_and_trends(per_year, lines)

    out = "\n".join(lines)
    with open("output/moves_matchups_analysis.md", "w", encoding="utf-8") as f:
        f.write(out + "\n")
    print(out)


if __name__ == "__main__":
    main()
