#!/usr/bin/env python3
"""
Quick deterministic draft sim — one pass, no Monte Carlo (that's the August
build). Opponents pick best-available vorp; goalie-needy teams take goalies
at their historical rounds; keeper slots consume picks in their rounds.
Assumes 2025 draft order repeats (TD slot 7). "keep?" coin-flips treated as
KEPT (conservative — don't plan around them falling).

Usage: python sim_draft_quick.py
"""
import os
import pandas as pd

ORDER = ["Gents","ER","ASD","Autodraft","Puppa","PK","TD","Sawchuk"]  # 2025 order
# approximate keeper rounds per team (context file verified lists)
KEEP_ROUNDS = {
    "Sawchuk": [3,4,7,9,10,11,12,12,16],
    "ASD": [3,4,7,8,8,9,12,12,12,12,12,12,16,18],
    "Gents": [3,11,14],
    "Autodraft": [3,8,9,9,10,11,11,16,17],
    "ER": [3,4,9,10,12,13,15,19],
    "Puppa": [4,5,6,7,9,10,11,12,13,13,15,16,18],
    "PK": [4,7,11,12,13,14,14,15],
    "TD": [7,10,12,12,15,16,19,19],
}
# traded pick ownership: (round, slot) -> actual owner (context file)
OWNER = {(4,4):"TD", (5,2):"TD", (6,2):"TD", (8,2):"TD",          # TD's acquired slots
         (11,7):"ER", (13,7):"ER", (14,7):"Autodraft",            # TD's traded-away rounds
         (17,7):"PK", (18,7):"PK", (20,7):"ER"}
# scripted goalie picks: (team, round) -> take top goalie
G_ROUNDS = {("Gents",3),("Gents",8),("ASD",4),("ASD",9),
            ("Sawchuk",13),("ER",14),("PK",15),("Puppa",16),("Autodraft",17)}
# TD goalie strategy: G1 and G2 on the early (ER slot-2) picks at R6 and R8

def newest(p):
    a = p.replace(".csv","_new.csv")
    return a if os.path.exists(a) and os.path.getmtime(a) > os.path.getmtime(p) else p

sk = pd.read_csv(newest("output/projections_v2_skaters.csv"))
sk = sk[sk["kept"].isna()].sort_values("vorp", ascending=False)   # keep? = kept
gl = pd.read_csv("output/projections_v2_goalies.csv")
gl = gl[gl["kept"].isna()].sort_values("z", ascending=False)

skaters = sk[["name","yahoo_pos","vorp","G","A","SOG","HIT","BLK"]].to_dict("records")
goalies = gl[["name","team","W","sv_proj","starts_proj","z"]].to_dict("records")
keep_sched = {t: sorted(KEEP_ROUNDS[t]) for t in ORDER}

td_log = []
g_taken = {t: 0 for t in ORDER}
for rnd in range(1, 22):
    for slot, slot_team in enumerate(ORDER, 1):
        team = OWNER.get((rnd, slot), slot_team)
        if rnd in keep_sched[team]:
            keep_sched[team].remove(rnd)
            continue                                    # keeper consumes pick
        is_td = team == "TD"
        take_g = ((team, rnd) in G_ROUNDS and g_taken[team] < 2) or \
                 (is_td and (rnd, slot) in ((6,2),(8,2)))
        if take_g and goalies:
            g_taken[team] += 1
            # TD's traded early slots (ER slot 2) used for goalies at R6/R8
            pick = goalies.pop(0)
            desc = f"G: {pick['name']} ({pick['team']}, {pick['W']}W, {pick['sv_proj']:.3f})"
            alt = ", ".join(g["name"] for g in goalies[:3])
        elif skaters:
            pick = skaters.pop(0)
            desc = (f"{pick['name']} ({pick['yahoo_pos']}, vorp {pick['vorp']:+.2f}, "
                    f"{pick['SOG']} SOG/{pick['HIT']} HIT/{pick['BLK']} BLK)")
            alt = ", ".join(f"{s['name']} {s['vorp']:+.1f}" for s in skaters[:4])
        else:
            continue
        if is_td:
            td_log.append((rnd, slot, desc, alt, ", ".join(
                f"G{i+1}:{g['name']}" for i, g in enumerate(goalies[:2]))))

print("TWIN DADDY PICKS (2025 order assumed; keep? players treated as kept)\n")
for rnd, slot, desc, alt, gtop in td_log:
    print(f"R{rnd:>2} pick {slot}  ->  {desc}")
    print(f"           next best: {alt}")
    if rnd in (5, 6, 7, 8):
        print(f"           top goalies left: {gtop}")
    print()
