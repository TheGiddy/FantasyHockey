#!/usr/bin/env python3
"""
League diagnosis from 2025-26 Yahoo weekly data.
  1. Per-team per-category W/L/T record (confirms/refutes TD banger deficit)
  2. League-wide category closeness (how often each cat is decided by a
     margin one roster move could flip) -> suggested draft weighting signal
  3. Draft market tendencies by round (2024 vs 2025: goalie timing, etc.)

Inputs: ./data/yahoo/*.csv from fetch_yahoo_draftprep.py
Output: ./output/league_diagnosis_2025.md (+ stdout)
"""
import pandas as pd
import numpy as np

MY_TEAM = "Twin Daddy"
CATS = ["G","A","PIM","PPP","SOG","HIT","BLK","W","SV%","SHO"]

# Yahoo NHL stat ids (yfa's stat_categories() doesn't expose ids, so the
# fetcher stored raw ids): 1 G, 2 A, 5 PIM, 8 PPP, 14 SOG, 31 HIT, 32 BLK,
# 19 W, 24 SA, 25 SV, 26 SV%, 27 SHO
STAT_ID = {1:"G",2:"A",5:"PIM",8:"PPP",14:"SOG",31:"HIT",32:"BLK",
           19:"W",24:"SA",25:"SV",26:"SV%",27:"SHO"}

win = pd.read_csv("data/yahoo/weekly_stat_winners_2025.csv")
val = pd.read_csv("data/yahoo/weekly_cat_values_2025.csv")
for df in (win, val):
    df["stat"] = pd.to_numeric(df["stat"], errors="coerce").map(STAT_ID).fillna(df["stat"])
val = val[val["stat"].isin(CATS)].copy()
val["value"] = pd.to_numeric(val["value"], errors="coerce")

lines = ["# League diagnosis — 2025-26 weekly data\n"]

# ---- 1. per-team category records ----
lines.append("## Category W-L records by team (23 weeks; ties excluded from W)\n")
teams = sorted(val["team"].unique())
rec = pd.DataFrame(index=teams, columns=CATS, dtype=float)
nweeks = win["week"].nunique()
for t in teams:
    for c in CATS:
        w = len(win[(win["winner"] == t) & (win["stat"] == c) & (win["tied"] == 0)])
        rec.loc[t, c] = w
rec["TOTAL"] = rec.sum(axis=1)
rec = rec.sort_values("TOTAL", ascending=False).astype(int)
lines.append("|team|" + "|".join(CATS) + "|TOTAL|")
lines.append("|---|" + "|".join(["---"] * (len(CATS) + 1)) + "|")
for t, r in rec.iterrows():
    mark = "**" if t == MY_TEAM else ""
    lines.append(f"|{mark}{t}{mark}|" + "|".join(str(r[c]) for c in CATS) + f"|{r['TOTAL']}|")
lines.append("")
td = rec.loc[MY_TEAM]
phys = td[["PIM","HIT","BLK"]].sum(); skill = td[["G","A","PPP","SOG"]].sum(); goal = td[["W","SV%","SHO"]].sum()
lines.append(f"**{MY_TEAM}**: skill cats {skill}/{4*nweeks} ({skill/(4*nweeks):.0%}), "
             f"physical cats {phys}/{3*nweeks} ({phys/(3*nweeks):.0%}), "
             f"goalie cats {goal}/{3*nweeks} ({goal/(3*nweeks):.0%})\n")

# ---- 2. category closeness (league-wide) ----
# For each week+cat: mean absolute pairwise difference between all team values,
# normalized by the league weekly mean -> relative margin. Small = coin-flip cat.
lines.append("## Category closeness (relative weekly margin between teams; smaller = more coin-flip = more draft leverage)\n")
rows = []
for c in CATS:
    margins = []
    for wk, grp in val[val["stat"] == c].groupby("week"):
        v = grp["value"].dropna().values
        if len(v) < 2 or np.nanmean(v) == 0:
            continue
        diffs = np.abs(v[:, None] - v[None, :])[np.triu_indices(len(v), 1)]
        margins.append(np.mean(diffs) / (np.mean(v) if c != "SV%" else 1))
    rows.append({"cat": c, "rel_margin": np.mean(margins)})
close = pd.DataFrame(rows)
close["leverage_rank"] = close["rel_margin"].rank().astype(int)
close = close.sort_values("rel_margin")
lines.append("|cat|relative margin|leverage rank (1 = most coin-flip)|")
lines.append("|---|---|---|")
for _, r in close.iterrows():
    fmt = f"{r['rel_margin']:.3f}" if r["cat"] == "SV%" else f"{r['rel_margin']:.2f}"
    lines.append(f"|{r['cat']}|{fmt}|{r['leverage_rank']}|")
lines.append("")

# skater-cat z-sum weights for the projection model: sqrt of inverse margin
# (full inverse over-trusts one season of margins), normalized to mean 1.
# Goalie cats stay unweighted: SV% is hyper-flippable but unpredictable
# year-over-year (backtest r=0.066) — flippability x predictability ~ cancels.
SK_CATS = ["G","A","PIM","PPP","SOG","HIT","BLK"]
skc = close[close["cat"].isin(SK_CATS)].copy()
skc["weight"] = 1 / np.sqrt(skc["rel_margin"])
skc["weight"] = (skc["weight"] / skc["weight"].mean()).round(3)
skc[["cat","weight"]].to_csv("data/yahoo/cat_weights.csv", index=False)
lines.append("Skater z-sum weights written to data/yahoo/cat_weights.csv: " +
             ", ".join(f"{r.cat} {r.weight}" for r in skc.itertuples()) + "\n")

# ---- 3a. keeper vs live-pick separation (2025 draft) ----
# Yahoo doesn't expose is_keeper for this league, so infer:
#   keeper: same team drafted same player in 2024 >= 2 rounds later than the
#           2025 slot (keep-at-round-minus-2, or rescued with an earlier pick)
#   possible waiver keeper: undrafted in 2024, taken at exactly R12
# Limits: waiver keepers rescued with earlier picks and re-drafted drop-adds
# are invisible to this heuristic.
def team_norm(t):
    return "Puppa" if "puppa" in str(t).lower() else str(t)

d24 = pd.read_csv("data/yahoo/draft_2024.csv")
d25 = pd.read_csv("data/yahoo/draft_2025.csv")
for df in (d24, d25):
    df["team_n"] = df["team"].map(team_norm)
m = d25.merge(d24[["yahoo_id","team_n","round"]]
              .rename(columns={"team_n":"team24","round":"round24"}),
              on="yahoo_id", how="left")
m["keeper"] = (m["team_n"] == m["team24"]) & (m["round"] <= m["round24"] - 2)
m["waiver_keeper_maybe"] = m["round24"].isna() & (m["round"] == 12)
elig_all = pd.read_csv("data/yahoo/eligibility.csv")
m = m.merge(elig_all[["yahoo_id","position_type"]], on="yahoo_id", how="left")
m.to_csv("data/yahoo/draft_2025_flagged.csv", index=False, encoding="utf-8-sig")

lines.append("## 2025 draft: keepers vs live picks (heuristic — see script header)\n")
lines.append("|team|keepers|waiver-keeper?|live picks|first LIVE goalie|live D in R1-10|")
lines.append("|---|---|---|---|---|---|")
for t, g in m.groupby("team_n"):
    live = g[~g["keeper"] & ~g["waiver_keeper_maybe"]]
    lg_ = live[live["position_type"] == "G"]["round"]
    dmask = live["yahoo_id"].isin(
        elig_all[elig_all["eligible_positions"].fillna("").str.contains("D")]["yahoo_id"])
    lines.append(f"|{t}|{int(g['keeper'].sum())}|{int(g['waiver_keeper_maybe'].sum())}"
                 f"|{len(live)}|R{lg_.min() if len(lg_) else '-'}"
                 f"|{int((live[dmask.reindex(live.index, fill_value=False)]['round'] <= 10).sum())}|")
lines.append("")
lines.append("### Inferred 2025 keepers by team (eyeball check)\n")
for t, g in m[m["keeper"]].groupby("team_n"):
    ks = ", ".join(f"{r.player} (R{r.round}<-R{int(r.round24)})" for r in g.itertuples())
    lines.append(f"- **{t}**: {ks}")
lines.append("")

# ---- 3. draft market tendencies ----
lines.append("## Draft market by round (when this room drafts goalies)\n")
for yr in (2024, 2025):
    try:
        d = pd.read_csv(f"data/yahoo/draft_{yr}.csv")
    except FileNotFoundError:
        continue
    elig = pd.read_csv("data/yahoo/eligibility.csv")
    d = d.merge(elig[["yahoo_id","position_type"]], on="yahoo_id", how="left")
    g_rounds = d[d["position_type"] == "G"].groupby("round").size()
    lines.append(f"**{yr} draft** — goalies per round: " +
                 ", ".join(f"R{r}:{n}" for r, n in g_rounds.items()) +
                 f" (total {g_rounds.sum()})")
lines.append("")

out = "\n".join(lines)
with open("output/league_diagnosis_2025.md", "w", encoding="utf-8") as f:
    f.write(out + "\n")
print(out)
