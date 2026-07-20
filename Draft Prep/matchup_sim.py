#!/usr/bin/env python3
"""
H2H weekly matchup Monte Carlo — values rosters by the game we actually play
(most categories won per Mon-Sun week) instead of the season-total z-sum.

Pipeline:
  1. Rosters: keepers from the projections CSVs (either/or "keep?" groups
     resolved by vorp per the context file), remaining slots filled by a
     need-aware linear draft (same order every round; 2025 order, keeper
     rounds + traded picks from
     sim_draft_quick, scripted goalie tendencies).
  2. Weekly means: per-game projected rates x that NHL team's games in each of
     the 28 fantasy weeks (schedule_20262027.csv), scaled by a per-category
     utilization factor calibrated so simulated league-average weekly totals
     match the two seasons of actual league history.
  3. Weekly noise: per-category overdispersion (var/mean) measured from
     data/yahoo/weekly_cat_values_{2024,2025}.csv — real lineup/streaming
     variance, not textbook Poisson. W/SHO stay Poisson (small counts, ties
     matter); SV% is Normal with the historical within-team weekly sd.
  4. Simulate: sample the same random week for both teams, count the 10 cats,
     matchup win = more cats than the opponent (ties = half).

Outputs (output/matchup_sim.md):
  - calibration table (model vs history per cat)
  - projected league power ranking (all-pairs weekly win%)
  - TD vs each opponent with per-cat win rates
  - R1 pick analysis: candidate forced at TD's first pick, draft re-filled,
    season win% simulated — the "marginal category value" draft ranking.

Known simplifications: no daily lineup sitting beyond the utilization factor,
players independent within a week, opponents draft by vorp with scripted
goalie rounds, injuries only via gp_proj availability thinning.

Run from ./Draft Prep:  python matchup_sim.py
"""
from collections import defaultdict
from datetime import date, timedelta
import csv as _csv

import numpy as np
import pandas as pd

from projection_model_v2 import norm_name
from sim_draft_quick import ORDER, KEEP_ROUNDS, OWNER, G_ROUNDS, newest

TD = "TD"
SLOTS = {"C": 3, "LW": 3, "RW": 3, "D": 4, "G": 2}
ROSTER_SIZE = 20
SK_CATS = ["G", "A", "PIM", "PPP", "SOG", "HIT", "BLK"]
TD_G_PICKS = {(6, 2), (8, 2)}       # TD plan: goalies on the ER-slot R6/R8 picks
SHOTS_PER_START = 28.5
N_ROUNDS = 20
SEED = 7

# Either/or keeper groups from KeeperLeague_2026-27_Context.md — the team keeps
# the best (by vorp) of each group; the rest hit the draft pool.
MAYBE_GROUPS = [
    ("Gents", ["Sam Bennett", "Drake Batherson"]),
    ("ER", ["Jake Sanderson", "Will Cuylle"]),
    ("ER", ["Charlie McAvoy", "Alex Tuch", "Mika Zibanejad"]),
    ("Puppa", ["Trevor Zegras", "Thomas Harley"]),
]


# ---------------- data loading ----------------
def load_players():
    sk = pd.read_csv(newest("output/projections_v2_skaters.csv"), encoding="utf-8-sig")
    gl = pd.read_csv("output/projections_v2_goalies.csv", encoding="utf-8-sig")
    players = []
    for _, r in sk.iterrows():
        gp = max(float(r["gp_proj"]), 1.0)
        players.append({
            "name": r["name"], "ptype": "S",
            "pos": str(r["yahoo_pos"]).split("/"),
            "nhl": str(r["team"]).split(",")[-1].strip('"'),
            "kept": "" if pd.isna(r["kept"]) else str(r["kept"]),
            "val": float(r["vorp"]),
            "rates": {c: float(r[c]) / gp for c in SK_CATS},
            "avail": min(gp / 82.0, 1.0),
        })
    for _, r in gl.iterrows():
        st = max(float(r["starts_proj"]), 1.0)
        players.append({
            "name": r["name"], "ptype": "G", "pos": ["G"],
            "nhl": str(r["team"]).split(",")[-1].strip('"'),
            "kept": "" if pd.isna(r["kept"]) else str(r["kept"]),
            "val": float(r["z"]),
            "winrate": float(r["W"]) / st, "shorate": float(r["SHO"]) / st,
            "sv": float(r["sv_proj"]), "share": min(st / 82.0, 1.0),
        })
    return players


def load_weeks():
    """games[nhl_team] = np.array of games per Mon-Sun fantasy week."""
    by_week = defaultdict(lambda: defaultdict(int))
    with open("data/schedule_20262027.csv", encoding="utf-8") as f:
        for r in _csv.DictReader(f):
            d = date.fromisoformat(r["date"])
            wk = d - timedelta(days=d.weekday())
            by_week[wk][r["home"]] += 1
            by_week[wk][r["away"]] += 1
    weeks = sorted(by_week)
    teams = sorted({t for w in by_week.values() for t in w})
    games = {t: np.array([by_week[w].get(t, 0) for w in weeks], float) for t in teams}
    return games, len(weeks)


def load_calibration():
    """Per-cat overdispersion phi (weekly var/mean within a team-season),
    within-team weekly SV% sd, and historical league-mean weekly values."""
    frames = []
    for yr in (2024, 2025):
        df = pd.read_csv(f"data/yahoo/weekly_cat_values_{yr}.csv")
        df["season"] = yr
        frames.append(df)
    h = pd.concat(frames, ignore_index=True)
    phi, hist_mean = {}, {}
    for c in SK_CATS + ["W", "SHO"]:
        sub = h[h["stat"] == c]
        grp = sub.groupby(["season", "team"])["value"]
        phi[c] = float(np.clip((grp.var() / grp.mean()).median(), 1.0, 6.0))
        hist_mean[c] = float(sub["value"].mean())
    sv = h[h["stat"] == "SV%"]
    sv_sd = float(sv.groupby(["season", "team"])["value"].std().median())
    hist_mean["SV%"] = float(sv["value"].mean())
    return phi, sv_sd, hist_mean


# ---------------- rosters ----------------
def build_keepers(players):
    by_name = {norm_name(p["name"]): p for p in players}
    rosters = {t: [] for t in ORDER}
    pool = []
    maybe_flat = {norm_name(n): (t, i) for i, (t, grp) in enumerate(MAYBE_GROUPS)
                  for n in grp}
    groups = defaultdict(list)
    for p in players:
        nn = norm_name(p["name"])
        if nn in maybe_flat:
            groups[maybe_flat[nn]].append(p)
        elif p["kept"] in rosters:
            rosters[p["kept"]].append(p)
        else:
            pool.append(p)
    for (team, _), members in groups.items():
        members.sort(key=lambda p: -p["val"])
        rosters[team].append(members[0])
        pool.extend(members[1:])
    # keeper count must match the rounds the picks grid consumes; spill extras
    for t in ORDER:
        rosters[t].sort(key=lambda p: -p["val"])
        n = len(KEEP_ROUNDS[t])
        if len(rosters[t]) > n:
            pool.extend(rosters[t][n:])
            rosters[t] = rosters[t][:n]
    return rosters, pool


def slot_needs(roster):
    """Greedy most-open slot assignment; returns dict of unfilled start slots."""
    open_ = dict(SLOTS)
    for p in sorted(roster, key=lambda x: -x["val"]):
        elig = [q for q in p["pos"] if open_.get(q, 0) > 0]
        if elig:
            best = max(elig, key=lambda q: open_[q])
            open_[best] -= 1
    return open_


def pick_schedule(rosters):
    """Live picks per team in draft order, honoring keeper rounds + trades."""
    keep_sched = {t: sorted(KEEP_ROUNDS[t]) for t in ORDER}
    picks = []
    for rnd in range(1, N_ROUNDS + 1):
        for slot, slot_team in enumerate(ORDER, 1):
            team = OWNER.get((rnd, slot), slot_team)
            if rnd in keep_sched[team]:
                keep_sched[team].remove(rnd)
                continue
            picks.append((rnd, slot, team))
    return picks


def draft_fill(rosters_in, pool, td_first=None):
    rosters = {t: list(v) for t, v in rosters_in.items()}
    sk_pool = sorted([p for p in pool if p["ptype"] == "S"], key=lambda p: -p["val"])
    g_pool = sorted([p for p in pool if p["ptype"] == "G"], key=lambda p: -p["val"])
    if td_first is not None:      # reserve before earlier slots can snipe them
        (sk_pool if td_first["ptype"] == "S" else g_pool).remove(td_first)
    picks = pick_schedule(rosters)
    remaining = defaultdict(int)
    for _, _, t in picks:
        remaining[t] += 1
    g_count = {t: sum(1 for p in rosters[t] if p["ptype"] == "G") for t in ORDER}
    td_first_done = td_first is None

    for rnd, slot, team in picks:
        remaining[team] -= 1
        if len(rosters[team]) >= ROSTER_SIZE:
            continue
        needs = slot_needs(rosters[team])
        must_fill = sum(needs.values()) >= remaining[team] + 1
        pick = None
        if team == TD and not td_first_done:
            pick, td_first_done = td_first, True
        elif (needs["G"] > 0 and (must_fill or
              ((team, rnd) in G_ROUNDS and g_count[team] < 2) or
              (team == TD and (rnd, slot) in TD_G_PICKS and g_count[team] < 2))):
            if g_pool:
                pick = g_pool.pop(0)
        if pick is None:
            if must_fill:
                for i, p in enumerate(sk_pool):
                    if any(needs.get(q, 0) > 0 for q in p["pos"]):
                        pick = sk_pool.pop(i)
                        break
            if pick is None and sk_pool:
                pick = sk_pool.pop(0)
        if pick is None:
            continue
        if pick["ptype"] == "G":
            g_count[team] += 1
        rosters[team].append(pick)

    # grid/keeper-round bookkeeping can leave a team a pick short — waiver fill
    for t in ORDER:
        while len(rosters[t]) < ROSTER_SIZE:
            needs = slot_needs(rosters[t])
            src = g_pool if needs["G"] > 0 else sk_pool
            rosters[t].append(src.pop(0))
        assert len(rosters[t]) == ROSTER_SIZE
    return rosters


# ---------------- weekly lambda + simulation ----------------
class TeamModel:
    def __init__(self, roster, games, n_weeks, util):
        self.count = np.zeros((len(SK_CATS), n_weeks))
        w = np.zeros(n_weeks)
        sho = np.zeros(n_weeks)
        shots = np.zeros(n_weeks)
        sv_num = sv_den = 0.0
        for p in roster:
            g = games.get(p["nhl"])
            if g is None:                     # FA/unsigned — contributes nothing
                continue
            if p["ptype"] == "S":
                for i, c in enumerate(SK_CATS):
                    self.count[i] += p["rates"][c] * g * p["avail"] * util[c]
            else:
                starts = p["share"] * g
                w += starts * p["winrate"] * util["W"]
                sho += starts * p["shorate"] * util["SHO"]
                shots += starts * SHOTS_PER_START
                sv_num += p["sv"] * p["share"]
                sv_den += p["share"]
        self.w, self.sho, self.shots = w, sho, shots
        self.sv = sv_num / sv_den if sv_den else 0.88


def simulate(a, b, phi, sv_sd, n_weeks, n_sims, rng):
    wk = rng.integers(0, n_weeks, n_sims)
    wins_a = np.zeros(n_sims)
    wins_b = np.zeros(n_sims)
    cat_win_a = {}
    def draw_count(lam, ph):
        return np.maximum(np.rint(rng.normal(lam, np.sqrt(ph * lam))), 0)
    for i, c in enumerate(SK_CATS):
        xa = draw_count(a.count[i, wk], phi[c])
        xb = draw_count(b.count[i, wk], phi[c])
        wins_a += xa > xb
        wins_b += xb > xa
        cat_win_a[c] = float(np.mean(xa > xb) + 0.5 * np.mean(xa == xb))
    for c, la, lb in [("W", a.w, b.w), ("SHO", a.sho, b.sho)]:
        xa, xb = rng.poisson(la[wk]), rng.poisson(lb[wk])
        wins_a += xa > xb
        wins_b += xb > xa
        cat_win_a[c] = float(np.mean(xa > xb) + 0.5 * np.mean(xa == xb))
    sva = rng.normal(a.sv, sv_sd, n_sims)
    svb = rng.normal(b.sv, sv_sd, n_sims)
    wins_a += sva > svb
    wins_b += svb > sva
    cat_win_a["SV%"] = float(np.mean(sva > svb))
    match = float(np.mean(wins_a > wins_b) + 0.5 * np.mean(wins_a == wins_b))
    return match, cat_win_a, float(np.mean(wins_a))


# ---------------- calibration ----------------
def utilization(rosters, games, n_weeks, hist_mean):
    """Scale factors so raw model league-mean weekly totals match history.
    Values above 1 are the streaming uplift — history includes pickups adding
    games beyond the drafted 20-man roster (TD alone averaged 2+ adds/week),
    so goalie counting cats especially need headroom above 1."""
    raw = {c: 1.0 for c in SK_CATS + ["W", "SHO"]}
    models = {t: TeamModel(r, games, n_weeks, raw) for t, r in rosters.items()}
    util, model_mean = {}, {}
    for i, c in enumerate(SK_CATS):
        m = float(np.mean([tm.count[i].mean() for tm in models.values()]))
        model_mean[c] = m
        util[c] = float(np.clip(hist_mean[c] / m, 0.5, 1.3))
    for c, attr in [("W", "w"), ("SHO", "sho")]:
        m = float(np.mean([getattr(tm, attr).mean() for tm in models.values()]))
        model_mean[c] = m
        util[c] = float(np.clip(hist_mean[c] / m, 0.5, 2.5))
    return util, model_mean


# ---------------- reporting ----------------
def main():
    rng = np.random.default_rng(SEED)
    players = load_players()
    games, n_weeks = load_weeks()
    phi, sv_sd, hist_mean = load_calibration()
    keepers, pool = build_keepers(players)
    rosters = draft_fill(keepers, pool)
    util, model_mean = utilization(rosters, games, n_weeks, hist_mean)
    tm = {t: TeamModel(r, games, n_weeks, util) for t, r in rosters.items()}

    L = ["# H2H weekly matchup simulation (Monte Carlo)", "",
         f"Rosters = keepers + need-aware vorp draft (2025 order, TD slot 7). "
         f"{n_weeks} fantasy weeks from the 2026-27 schedule. Weekly noise "
         f"calibrated on 2024-25 + 2025-26 actual league weeks. Seed {SEED}.", "",
         "## Calibration (league-average weekly totals per team)", "",
         "| Cat | model raw | history | utilization | overdispersion phi |",
         "|---|---|---|---|---|"]
    for c in SK_CATS + ["W", "SHO"]:
        L.append(f"| {c} | {model_mean[c]:.1f} | {hist_mean[c]:.1f} "
                 f"| {util[c]:.2f} | {phi[c]:.1f} |")
    L.append(f"| SV% | — | {hist_mean['SV%']:.3f} | — | weekly sd {sv_sd:.4f} |")

    # power ranking: all-pairs weekly matchup win%
    power = {t: [] for t in ORDER}
    for i, t1 in enumerate(ORDER):
        for t2 in ORDER[i + 1:]:
            m, _, _ = simulate(tm[t1], tm[t2], phi, sv_sd, n_weeks, 3000, rng)
            power[t1].append(m)
            power[t2].append(1 - m)
    L += ["", "## Projected power ranking (avg weekly matchup win% vs field)", "",
          "| Team | win% |", "|---|---|"]
    for t in sorted(ORDER, key=lambda x: -np.mean(power[x])):
        L.append(f"| {t} | {np.mean(power[t]):.1%} |")

    # TD vs each opponent, per-cat
    cats = SK_CATS + ["W", "SHO", "SV%"]
    L += ["", "## Twin Daddy vs each opponent (per-cat weekly win rates)", "",
          "| Opp | match win% | " + " | ".join(cats) + " |",
          "|" + "|".join(["---"] * (len(cats) + 2)) + "|"]
    cat_avgs = defaultdict(list)
    for t in ORDER:
        if t == TD:
            continue
        m, cw, _ = simulate(tm[TD], tm[t], phi, sv_sd, n_weeks, 5000, rng)
        for c in cats:
            cat_avgs[c].append(cw[c])
        L.append(f"| {t} | {m:.1%} | " +
                 " | ".join(f"{cw[c]:.0%}" for c in cats) + " |")
    L.append("| **avg** | | " +
             " | ".join(f"**{np.mean(cat_avgs[c]):.0%}**" for c in cats) + " |")

    # R1 candidate analysis
    avail_sk = sorted([p for p in pool if p["ptype"] == "S"], key=lambda p: -p["val"])[:20]
    avail_g = sorted([p for p in pool if p["ptype"] == "G"], key=lambda p: -p["val"])[:4]
    L += ["", "## TD first pick (R1, slot 7): simulated season win% per candidate", "",
          "Candidate forced at R1, rest of draft re-filled greedily, TD simmed "
          "vs all 7 opponents (4,000 weeks each, common random numbers — "
          "differences under ~0.5% are still noise).", "",
          "| Candidate | pos | vorp/z | avg win% | avg cats/wk |", "|---|---|---|---|---|"]
    results = []
    for cand in avail_sk + avail_g:
        r2 = draft_fill(keepers, pool, td_first=cand)
        u2, _ = utilization(r2, games, n_weeks, hist_mean)
        tm_td = TeamModel(r2[TD], games, n_weeks, u2)
        # common random numbers: every candidate faces identical week draws
        # and noise, so ranking differences are pure roster effects
        rng_c = np.random.default_rng(SEED + 1)
        ws, cats_won = [], []
        for t in ORDER:
            if t == TD:
                continue
            m, _, cwk = simulate(tm_td, TeamModel(r2[t], games, n_weeks, u2),
                                 phi, sv_sd, n_weeks, 4000, rng_c)
            ws.append(m)
            cats_won.append(cwk)
        results.append((cand, float(np.mean(ws)), float(np.mean(cats_won))))
    results.sort(key=lambda x: -x[1])
    for cand, w, cwk in results:
        L.append(f"| {cand['name']} | {'/'.join(cand['pos'])} "
                 f"| {cand['val']:+.2f} | {w:.1%} | {cwk:.2f} |")

    L += ["", "## Assumptions & limits",
          "- No daily lineup sitting beyond the calibrated utilization factor; "
          "players independent within a week; injuries only as gp availability thinning.",
          "- Opponents draft best-vorp with scripted goalie rounds; keep? "
          "either/or groups resolved by vorp.",
          "- SV% weekly noise is the historical within-team sd — dominated by "
          "randomness, per the two-season diagnosis."]
    md = "\n".join(L)
    with open("output/matchup_sim.md", "w", encoding="utf-8") as f:
        f.write(md + "\n")
    print(md)


if __name__ == "__main__":
    main()
