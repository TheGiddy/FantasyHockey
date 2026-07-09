#!/usr/bin/env python3
"""
League-wide opponent analysis across the two completed seasons (2024-25,
2025-26). For every team: matchup record, per-category strength/weakness
profile (where TD can attack them), roster posture (buyer/seller via trades),
and streaming activity.

Reads ./data/yahoo/{transactions,weekly_matchup_results,weekly_cat_values}_{2024,2025}.csv
Output: ./output/opponents_analysis.md (+ stdout)
"""
import pandas as pd

YEARS = [2024, 2025]
LABEL = {2024: "2024-25", 2025: "2025-26"}
CATS = ["G", "A", "PIM", "PPP", "SOG", "HIT", "BLK", "W", "SV%", "SHO"]
GOALIE_CATS = ["W", "SV%", "SHO"]
MY_TEAM = "Twin Daddy"

# team display names vary across seasons (Puppa renamed); map to canonical
CANON = [
    ("twin daddy", "Twin Daddy"),
    ("puppa", "Puppa'd Your Pants"),
    ("sawchuk", "Sawchuk Dun Thats"),
    ("adamsux", "AdamSuxDix"),
    ("subuwu", "P.K. SubUwU"),
    ("p.k", "P.K. SubUwU"),
    ("emotional", "Emotional Reactions"),
    ("distinguished", "The Most Distinguished Gents"),
    ("autodraft", "Autodraft"),
]


def canon(name):
    n = str(name).strip().lower()
    for key, label in CANON:
        if key in n:
            return label
    return str(name)


def load_results(year):
    r = pd.read_csv(f"data/yahoo/weekly_matchup_results_{year}.csv")
    r["team_c"] = r["team"].map(canon)
    r["opp_c"] = r["opponent"].map(canon)
    r["year"] = year
    return r


def load_values(year):
    v = pd.read_csv(f"data/yahoo/weekly_cat_values_{year}.csv")
    v["value"] = pd.to_numeric(v["value"], errors="coerce")
    v["team_c"] = v["team"].map(canon)
    v["year"] = year
    return v


def load_tx(year):
    t = pd.read_csv(f"data/yahoo/transactions_{year}.csv")
    t["src_c"] = t["source_team"].map(canon)
    t["dst_c"] = t["destination_team"].map(canon)
    t["year"] = year
    return t


# ---- 1. matchup records ----
def records_section(results, lines):
    lines.append("## Matchup records — league standings (both seasons)\n")
    lines.append("|team|2024-25|2025-26|combined|combined win%|")
    lines.append("|---|---|---|---|---|")
    teams = sorted(results["team_c"].unique())
    rows = []
    for t in teams:
        cells, cw = {}, {"win": 0, "loss": 0, "tie": 0}
        for y in YEARS:
            sub = results[(results["team_c"] == t) & (results["year"] == y)]
            vc = sub["result"].value_counts().to_dict()
            w, l, ti = vc.get("win", 0), vc.get("loss", 0), vc.get("tie", 0)
            cells[y] = f"{w}-{l}-{ti}"
            for k, v in (("win", w), ("loss", l), ("tie", ti)):
                cw[k] += v
        tot = sum(cw.values())
        wp = cw["win"] / tot if tot else 0
        rows.append((t, cells, cw, wp))
    for t, cells, cw, wp in sorted(rows, key=lambda x: -x[3]):
        mark = "**" if t == MY_TEAM else ""
        comb = f"{cw['win']}-{cw['loss']}-{cw['tie']}"
        lines.append(f"|{mark}{t}{mark}|{cells[2024]}|{cells[2025]}|{comb}|{wp:.0%}|")
    lines.append("")


# ---- 2. per-team category profile (both seasons, head-to-head) ----
def category_profile(results, values, lines):
    lines.append("## Category profiles — win% per cat, both seasons combined\n")
    lines.append("Each team's value vs its weekly opponent. **Bold** = TD.\n")
    teams = sorted(results["team_c"].unique())
    prof = {}
    for t in teams:
        tally = {c: [0, 0, 0] for c in CATS}  # w,l,t
        tr = results[results["team_c"] == t]
        for r in tr.itertuples():
            va = values[(values.year == r.year) & (values.week == r.week) & (values.team_c == t)]
            vo = values[(values.year == r.year) & (values.week == r.week) & (values.team_c == r.opp_c)]
            for c in CATS:
                a = va[va.stat == c]["value"]
                b = vo[vo.stat == c]["value"]
                if a.empty or b.empty or pd.isna(a.iloc[0]) or pd.isna(b.iloc[0]):
                    continue
                av, bv = float(a.iloc[0]), float(b.iloc[0])
                tally[c][0 if av > bv else 1 if av < bv else 2] += 1
        prof[t] = tally

    header = "|team|" + "|".join(CATS) + "|"
    lines.append(header)
    lines.append("|---|" + "|".join(["---"] * len(CATS)) + "|")
    for t in sorted(teams):
        mark = "**" if t == MY_TEAM else ""
        cells = []
        for c in CATS:
            w, l, ti = prof[t][c]
            tot = w + l + ti
            cells.append(f"{w/tot:.0%}" if tot else "-")
        lines.append(f"|{mark}{t}{mark}|" + "|".join(cells) + "|")
    lines.append("")

    # narrative: each team's 2 best and 2 worst cats. SHO is excluded — it's a
    # tie-lottery (low win% for everyone) so it's noise, not an attack angle.
    lines.append("### Where each team is strong / soft (attack the soft cats; SHO excluded as a tie-lottery)\n")
    for t in sorted(teams):
        rates = []
        for c in CATS:
            if c == "SHO":
                continue
            w, l, ti = prof[t][c]
            tot = w + l + ti
            if tot:
                rates.append((c, w / tot))
        rates.sort(key=lambda x: -x[1])
        strong = ", ".join(f"{c} {r:.0%}" for c, r in rates[:2])
        soft = ", ".join(f"{c} {r:.0%}" for c, r in rates[-2:])
        mark = "**" if t == MY_TEAM else ""
        lines.append(f"- {mark}{t}{mark}: strong **{strong}** · soft **{soft}**")
    lines.append("")
    return prof


# ---- 3. roster posture: buyers vs sellers ----
def _pick_round(player):
    # "Draft pick R12" -> 12; picks not tagged with a round default to mid (11)
    s = str(player)
    if "R" in s:
        tail = s.split("R")[-1].strip()
        if tail.isdigit():
            return int(tail)
    return 11


def _capital(picks):
    # earlier picks are worth more; a 20-round draft => value = 21 - round
    return sum(21 - _pick_round(p) for p in picks)


def _classify(net_players, cap_delta):
    # buyer: adds players, spends early-pick capital; seller: the reverse
    if net_players >= 1 and cap_delta <= -3:
        return "BUYER"
    if net_players <= -1 and cap_delta >= 3:
        return "SELLER"
    if abs(net_players) >= 2:
        return "BUYER" if net_players > 0 else "SELLER"
    return "mixed"


def posture_section(txs, lines):
    lines.append("## Roster posture — buyers vs sellers, per season\n")
    lines.append("Pick swaps are balanced by count in this league, so posture "
                 "is read from **pick quality** (draft-capital delta, early rounds "
                 "worth more) alongside net players traded. This is the signal for "
                 "who TD can deal picks-for-talent (buyers) or talent-for-picks "
                 "(sellers) with in 2026-27.\n")
    teams = set(txs["src_c"]).union(txs["dst_c"])
    teams = sorted(t for t in teams if t and any(k in str(t).lower() for k, _ in CANON))
    for year in YEARS:
        ty = txs[txs.year == year]
        lines.append(f"### {LABEL[year]}\n")
        lines.append("|team|players in|players out|net players|pick-capital delta|waiver adds|posture|")
        lines.append("|---|---|---|---|---|---|---|")
        rows = []
        for t in teams:
            pl_in = ty[(ty.movement == "traded") & (ty.dst_c == t)]
            pl_out = ty[(ty.movement == "traded") & (ty.src_c == t)]
            pk_in = ty[(ty.movement == "pick_traded") & (ty.dst_c == t)]["player"]
            pk_out = ty[(ty.movement == "pick_traded") & (ty.src_c == t)]["player"]
            adds = len(ty[(ty.movement == "added") & (ty.dst_c == t)])
            net_pl = len(pl_in) - len(pl_out)
            cap = _capital(pk_in) - _capital(pk_out)
            rows.append((t, len(pl_in), len(pl_out), net_pl, cap, adds,
                         _classify(net_pl, cap)))
        for t, pin, pout, net_pl, cap, adds, posture in sorted(rows, key=lambda x: x[6]):
            mark = "**" if t == MY_TEAM else ""
            lines.append(f"|{mark}{t}{mark}|{pin}|{pout}|{net_pl:+d}|{cap:+d}|{adds}|{posture}|")
        lines.append("")


def main():
    results = pd.concat([load_results(y) for y in YEARS], ignore_index=True)
    values = pd.concat([load_values(y) for y in YEARS], ignore_index=True)
    txs = pd.concat([load_tx(y) for y in YEARS], ignore_index=True)

    lines = ["# League opponent analysis (2024-25 and 2025-26)\n"]
    records_section(results, lines)
    category_profile(results, values, lines)
    posture_section(txs, lines)

    out = "\n".join(lines)
    with open("output/opponents_analysis.md", "w", encoding="utf-8") as f:
        f.write(out + "\n")
    print(out)


if __name__ == "__main__":
    main()
