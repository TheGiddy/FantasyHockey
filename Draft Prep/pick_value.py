#!/usr/bin/env python3
"""
Pick-value curve + pre-draft trade evaluator.

Maps each draft slot -> expected available vorp:
  1. Keeper slots by round parsed from the context file's ground-truth CSV,
     filtered to the model's projected-keep list (KEPT) — these rounds are
     consumed and yield no live player.
  2. A live pick's board index = overall slot minus keeper slots ahead of it
     (keepers assumed uniform within their round).
  3. Pick value = mean vorp of the next few available players at that index
     (window models the market not drafting exactly by our board).

Trade math: acquiring player P pre-draft to keep with a round-R pick nets
  surplus = vorp(P) - pickvalue(R)  [you burn the pick, gain the player]
The cost side (players/picks sent) is listed but judged manually — trade
currency (Wallstedt, Sennecke...) has team-specific value.

Skater board only; goalies are a separate scale (see projections goalie tab).
Usage: python pick_value.py    Output: ./output/pick_values.md
"""
import os, re
import numpy as np
import pandas as pd
from projection_model_v2 import KEPT, norm_name

TEAMS, ROUNDS = 8, 21
MY_SLOT = 7          # TD's 2025 draw; 2026 order TBD (late July)
CONTEXT = "KeeperLeague_2026-27_Context.md"

# TD's live picks after keepers (context file)
TD_PICKS = ["R1","R2","R3","R4","R4b","R5","R5b","R6","R6b","R8","R8b","R9","R21"]

# acquisition targets: player -> round of the spare pick that would keep them
TARGETS = {
    "Alex Tuch": 6, "Alex DeBrincat": 5, "Timo Meier": 6, "Sebastian Aho": 5,
    "Seth Jarvis": 6, "Miro Heiskanen": 4, "Darren Raddysh": 8,
}

def newest(path):
    alt = path.replace(".csv", "_new.csv")
    if os.path.exists(alt) and (not os.path.exists(path) or
                                os.path.getmtime(alt) > os.path.getmtime(path)):
        return alt
    return path

# ---- keeper slots per round (context ground-truth CSV x model KEPT list) ----
def keeper_rounds():
    txt = open(CONTEXT, encoding="utf-8", errors="replace").read()
    rows = re.findall(r"^([^,\n]+),([^,\n]+),([^,\n]+),([^,\n]+)(?:,[x ]?){0,5}$",
                      txt.split("Team Name,Player Name,Drafted Round,Keeper Round")[1],
                      flags=re.M)
    kept_n = {norm_name(k) for k in KEPT}
    per_round = {r: 0 for r in range(1, ROUNDS + 1)}
    matched = set()
    for team, player, drafted, kround in rows:
        nn = norm_name(player)
        if nn in kept_n and nn not in matched:
            matched.add(nn)
            try:
                per_round[int(kround)] += 1
            except ValueError:
                per_round[12] += 1          # "Not Drafted" -> R12 default
    # KEPT names missing from the CSV (encoding casualties): assume R12
    for miss in kept_n - matched:
        per_round[12] += 1
    return per_round

def build_curve(board, per_round, slot=MY_SLOT):
    """expected vorp for each (round, slot) live pick."""
    def value_at(rnd):
        overall = (rnd - 1) * TEAMS + slot
        keepers_ahead = sum(per_round[r] for r in range(1, rnd)) \
                        + per_round[rnd] * (slot - 1) / TEAMS
        j = int(round(overall - keepers_ahead))          # 1-based board index
        j = max(1, min(j, len(board)))
        window = board[j - 1: j + 3]
        return float(np.mean(window)) if len(window) else float(board[-1])
    return {r: value_at(r) for r in range(1, ROUNDS + 1)}

if __name__ == "__main__":
    sk = pd.read_csv(newest("output/projections_v2_skaters.csv"))
    avail = sk[sk["kept"].isna() | (sk["kept"] == "keep?")].sort_values("vorp", ascending=False)
    board = avail["vorp"].values

    per_round = keeper_rounds()
    curve = build_curve(board, per_round)

    lines = ["# Pick values & trade targets (skater board, TD slot "
             f"{MY_SLOT} of {TEAMS}; keeper slots: {sum(per_round.values())})\n"]
    lines.append("## Expected available vorp by round (linear draft)\n")
    lines.append("|round|keeper slots in round|expected vorp at TD pick|")
    lines.append("|---|---|---|")
    for r in range(1, ROUNDS + 1):
        own = " **(TD pick)**" if f"R{r}" in TD_PICKS or f"R{r}b" in TD_PICKS else ""
        lines.append(f"|R{r}|{per_round[r]}|{curve[r]:+.2f}{own}|")
    lines.append("")

    lines.append("## Trade-target surplus (acquire pre-draft, keep with spare pick)\n")
    lines.append("|target|vorp|keep w/ pick|pick's draft value|net surplus (z)|")
    lines.append("|---|---|---|---|---|")
    nn_map = {norm_name(n): n for n in TARGETS}
    for _, p in avail.iterrows():
        nn = norm_name(p["name"])
        if nn in nn_map:
            r = TARGETS[nn_map[nn]]
            surplus = p["vorp"] - curve[r]
            lines.append(f"|{p['name']}|{p['vorp']:+.2f}|R{r}|{curve[r]:+.2f}|**{surplus:+.2f}**|")
    lines.append("\nCost side (players/picks sent) is manual: currency = Wallstedt, "
                 "Sennecke, Dorofeyev, Larkin per context file. Goalies not on this board.")

    out = "\n".join(lines)
    with open("output/pick_values.md", "w", encoding="utf-8") as f:
        f.write(out + "\n")
    print(out)
