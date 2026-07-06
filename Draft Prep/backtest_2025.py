#!/usr/bin/env python3
"""
Backtest: project 2025-26 blind (window 2022-23..2024-25, career sh% through
2021-22 only), score vs actual 2025-26, and compare against two baselines:
  naive  — 2024-25 totals carried forward
  market — this room's 2025 live draft picks (pick order = implied rank)

Fetches 2022-23 NHL data + 2022 MoneyPuck on first run (missing from the
production window). Output: ./output/backtest_2025.md
"""
import os, urllib.request
import numpy as np
import pandas as pd

import fetch_nhl_data_v2 as F
from projection_model_v2 import build_skaters, build_goalies, norm_name

BT_SEASONS = [20222023, 20232024, 20242025]
BT_HIST = [20182019, 20192020, 20202021, 20212022]   # career sh%, no overlap
ACTUAL = 20252026
CATS = ["G","A","PIM","PPP","SOG","HIT","BLK"]
ACT_COLS = {"G":"goals","A":"assists","PIM":"penaltyMinutes","PPP":"ppPoints",
            "SOG":"shots","HIT":"hits","BLK":"blockedShots"}

# ---- ensure 2022-23 inputs exist ----
def ensure_data():
    for name in F.SKATER_REPORTS:
        p = f"data/nhl_skater_{name}_20222023.csv"
        if not os.path.exists(p):
            F.write_csv(p, F.fetch_report("skater", name, 20222023))
            print(f"fetched {p}")
    for name in F.GOALIE_REPORTS:
        p = f"data/nhl_goalie_{name}_20222023.csv"
        if not os.path.exists(p):
            F.write_csv(p, F.fetch_report("goalie", name, 20222023))
            print(f"fetched {p}")
    for kind in ("skaters", "goalies"):
        p = f"data/moneypuck_{kind}_2022.csv"
        if not os.path.exists(p):
            url = f"https://moneypuck.com/moneypuck/playerData/seasonSummary/2022/regular/{kind}.csv"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as r, open(p, "wb") as f:
                f.write(r.read())
            print(f"fetched {p}")

def two_pass_z(df, cats, pool_n=150):
    def zsum(frame, ref):
        return sum((frame[c] - ref[c].mean()) / ref[c].std(ddof=0) for c in cats)
    z = zsum(df, df)
    ref = df.loc[z.nlargest(pool_n).index]
    return zsum(df, ref)

def load_actual():
    s = pd.read_csv(f"data/nhl_skater_summary_{ACTUAL}.csv").drop_duplicates("playerId")
    r = pd.read_csv(f"data/nhl_skater_realtime_{ACTUAL}.csv").drop_duplicates("playerId")
    a = s.merge(r[["playerId","hits","blockedShots"]], on="playerId")
    a = a.rename(columns={v: k for k, v in ACT_COLS.items()})
    a = a[["playerId","skaterFullName","gamesPlayed"] + CATS]
    a["z_act"] = two_pass_z(a, CATS)
    return a

def naive_baseline():
    s = pd.read_csv("data/nhl_skater_summary_20242025.csv").drop_duplicates("playerId")
    r = pd.read_csv("data/nhl_skater_realtime_20242025.csv").drop_duplicates("playerId")
    n = s.merge(r[["playerId","hits","blockedShots"]], on="playerId")
    n = n.rename(columns={v: k for k, v in ACT_COLS.items()})[["playerId"] + CATS]
    n["z_naive"] = two_pass_z(n, CATS)
    return n[["playerId","z_naive"]]

if __name__ == "__main__":
    ensure_data()
    proj = build_skaters(seasons=BT_SEASONS, age_date=pd.Timestamp("2026-01-15"),
                         hist_seasons=BT_HIST, use_weights=False)  # equal weights: comparable to actual z
    actual = load_actual()
    naive = naive_baseline()

    m = (proj[["playerId","name","age","breakout","z"] + CATS]
         .merge(actual[["playerId","gamesPlayed","z_act"] + CATS],
                on="playerId", suffixes=("_p","_a"))
         .merge(naive, on="playerId", how="left"))

    lines = ["# Backtest — 2025-26 projected blind from 2022-25 data\n"]
    lines.append(f"Matched players: {len(m)} (projected pool x actual 2025-26)\n")

    # rank quality: model vs naive
    lines.append("## Value-rank quality (Spearman rank correlation vs actual 7-cat z)\n")
    sp_model = m["z"].corr(m["z_act"], method="spearman")
    sp_naive = m["z_naive"].corr(m["z_act"], method="spearman")
    lines.append(f"- model v2: **{sp_model:.3f}**")
    lines.append(f"- naive (2024-25 carried forward): **{sp_naive:.3f}**")

    # market baseline: 2025 live draft picks only, same-subset comparison
    try:
        dr = pd.read_csv("data/yahoo/draft_2025_flagged.csv")
        live = dr[~dr["keeper"] & ~dr["waiver_keeper_maybe"] & (dr["position_type"] != "G")].copy()
        live["nn"] = live["player"].map(norm_name)
        mm = m.copy(); mm["nn"] = mm["name"].map(norm_name)
        sub = mm.merge(live[["nn","pick"]], on="nn")
        sp_mkt = (-sub["pick"]).corr(sub["z_act"], method="spearman")
        sp_model_sub = sub["z"].corr(sub["z_act"], method="spearman")
        lines.append(f"- market (2025 live picks, n={len(sub)}): **{sp_mkt:.3f}** "
                     f"(model on same subset: **{sp_model_sub:.3f}**)")
    except FileNotFoundError:
        lines.append("- market baseline skipped (draft_2025_flagged.csv missing)")
    lines.append("")

    # top-50 hit rate
    top50a = set(m.nlargest(50, "z_act")["playerId"])
    hit_m = len(set(m.nlargest(50, "z")["playerId"]) & top50a)
    hit_n = len(set(m.nlargest(50, "z_naive")["playerId"]) & top50a)
    lines.append(f"## Top-50 hit rate\n\nmodel {hit_m}/50, naive {hit_n}/50\n")

    # per-category quality (actual GP >= 40 to reduce injury noise)
    lines.append("## Per-category correlation & MAE (actual GP >= 40)\n")
    lines.append("|cat|r (model)|r (naive)|MAE (model)|")
    lines.append("|---|---|---|---|")
    m40 = m[m["gamesPlayed"] >= 40]
    nv = pd.read_csv("data/nhl_skater_summary_20242025.csv").drop_duplicates("playerId")
    nvr = pd.read_csv("data/nhl_skater_realtime_20242025.csv").drop_duplicates("playerId")
    nv = nv.merge(nvr[["playerId","hits","blockedShots"]], on="playerId") \
           .rename(columns={v: k for k, v in ACT_COLS.items()})
    m40n = m40.merge(nv[["playerId"] + CATS], on="playerId", suffixes=("", "_nv"))
    for c in CATS:
        r_m = m40[f"{c}_p"].corr(m40[f"{c}_a"])
        r_n = m40n[c].corr(m40n[f"{c}_a"]) if f"{c}_nv" not in m40n else m40n[f"{c}_nv"].corr(m40n[f"{c}_a"])
        mae = (m40[f"{c}_p"] - m40[f"{c}_a"]).abs().mean()
        lines.append(f"|{c}|{r_m:.3f}|{r_n:.3f}|{mae:.1f}|")
    lines.append("")

    # breakout flag performance
    bk = m[m["breakout"]]
    lines.append(f"## Breakout blend check\n\n{len(bk)} players flagged; "
                 f"mean projected z {bk['z'].mean():.2f}, mean actual z {bk['z_act'].mean():.2f} "
                 f"(all matched: proj {m['z'].mean():.2f}, actual {m['z_act'].mean():.2f})\n")

    # biggest misses
    m["rank_p"] = m["z"].rank(ascending=False)
    m["rank_a"] = m["z_act"].rank(ascending=False)
    m["rank_err"] = m["rank_p"] - m["rank_a"]
    rel = m[(m["rank_p"] <= 120) | (m["rank_a"] <= 120)]
    lines.append("## Biggest misses (players in either top-120)\n")
    lines.append("**Model too LOW (breakouts it missed):**")
    for r in rel.nlargest(8, "rank_err").itertuples():
        lines.append(f"- {r.name}: proj rank {int(r.rank_p)}, actual {int(r.rank_a)} (GP {int(r.gamesPlayed)})")
    lines.append("\n**Model too HIGH (busts it bought):**")
    for r in rel.nsmallest(8, "rank_err").itertuples():
        lines.append(f"- {r.name}: proj rank {int(r.rank_p)}, actual {int(r.rank_a)} (GP {int(r.gamesPlayed)})")
    lines.append("")

    # goalies
    gp_ = build_goalies(seasons=BT_SEASONS)
    ga = pd.read_csv(f"data/nhl_goalie_summary_{ACTUAL}.csv").drop_duplicates("playerId")
    gm = gp_.reset_index().merge(ga[["playerId","wins","savePct","shutouts","gamesStarted"]],
                                 on="playerId")
    gm = gm[gm["gamesStarted"] >= 20]
    lines.append(f"## Goalies (actual GS >= 20, n={len(gm)})\n")
    lines.append(f"- W: r={gm['W'].corr(gm['wins']):.3f}, MAE={ (gm['W']-gm['wins']).abs().mean():.1f}")
    lines.append(f"- SV%: r={gm['sv_proj'].corr(gm['savePct']):.3f}")
    lines.append(f"- starts: r={gm['starts_proj'].corr(gm['gamesStarted']):.3f}")

    out = "\n".join(lines)
    with open("output/backtest_2025.md", "w", encoding="utf-8") as f:
        f.write(out + "\n")
    print(out)
