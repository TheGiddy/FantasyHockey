#!/usr/bin/env python3
"""
Deployment-riser screen: find Clarke-shaped players — age <= 26, rising
TOI and/or PP share across the last two season-pairs, still available
(not kept), with model value + last year's league draft cost for context.

Usage: python screen_risers.py [--pos D]
"""
import os, sys
import pandas as pd

def load(s):
    toi = pd.read_csv(f"data/nhl_skater_timeonice_{s}.csv").drop_duplicates("playerId")
    pp  = pd.read_csv(f"data/nhl_skater_powerplay_{s}.csv").drop_duplicates("playerId")
    m = toi.merge(pp[["playerId","ppTimeOnIcePctPerGame","ppPoints"]], on="playerId")
    m["toi"] = m["timeOnIcePerGame"] / 60
    m["ppshare"] = m["ppTimeOnIcePctPerGame"].where(m["ppTimeOnIcePctPerGame"] > 1,
                                                    m["ppTimeOnIcePctPerGame"] * 100)
    return m.set_index("playerId")[["skaterFullName","positionCode","gamesPlayed","toi","ppshare"]]

s24, s25, s26 = load(20232024), load(20242025), load(20252026)
df = s26.join(s25[["toi","ppshare","gamesPlayed"]], rsuffix="_25") \
        .join(s24[["toi","ppshare"]], rsuffix="_24")
df["d_toi_1"] = df["toi"] - df["toi_25"]          # last year vs prior
df["d_toi_2"] = df["toi_25"] - df["toi_24"]       # prior pair
df["d_pp_1"]  = df["ppshare"] - df["ppshare_25"]
df["d_pp_2"]  = df["ppshare_25"] - df["ppshare_24"]

def newest(p):
    a = p.replace(".csv", "_new.csv")
    return a if os.path.exists(a) and os.path.getmtime(a) > os.path.getmtime(p) else p

sk = pd.read_csv(newest("output/projections_v2_skaters.csv"))
sk["rank"] = range(1, len(sk) + 1)
proj = sk.set_index("name")[["rank","yahoo_pos","age","vorp","z","kept","notes"]]

df = df.join(proj, on="skaterFullName")

# market price: where the room drafted them in 2025 (blank = undrafted)
try:
    d25 = pd.read_csv("data/yahoo/draft_2025_flagged.csv")
    cost = d25.set_index("player")["round"]
    df["draft25"] = df["skaterFullName"].map(cost)
except FileNotFoundError:
    df["draft25"] = None

pos_filter = sys.argv[sys.argv.index("--pos") + 1] if "--pos" in sys.argv else None
r = df[(df["age"] <= 26)
       & (df["gamesPlayed"] >= 50)
       & (df["toi"] >= 16)
       & ((df["d_toi_1"] >= 1.2) | (df["d_pp_1"] >= 8))
       & (df["kept"].isna() | (df["kept"] == "keep?"))]
if pos_filter:
    r = r[r["positionCode"] == pos_filter]

r = r.sort_values("vorp", ascending=False)
cols = ["skaterFullName","positionCode","age","toi_24","toi_25","toi",
        "ppshare_25","ppshare","d_toi_1","d_pp_1","vorp","rank","draft25","kept"]
out = r[cols].rename(columns={
    "skaterFullName":"player","positionCode":"pos","toi_24":"TOI24","toi_25":"TOI25",
    "toi":"TOI26","ppshare_25":"PP%25","ppshare":"PP%26","d_toi_1":"dTOI",
    "d_pp_1":"dPP%","draft25":"drafted25"})
for c in ["TOI24","TOI25","TOI26","PP%25","PP%26","dTOI","dPP%"]:
    out[c] = out[c].round(1)
print(f"Deployment risers (age<=26, GP>=50, TOI>=16, rising TOI or PP share, available): {len(out)}")
print(out.head(25).to_string(index=False))
