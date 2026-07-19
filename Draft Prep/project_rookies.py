#!/usr/bin/env python3
"""
NHLe rookie projections — fills the model's known blind spot: players with no
(or minimal) NHL history are invisible to the per-60 pipeline, and they're
exactly where keeper-league value hides (Gauthier R19).

Method (league-equivalency, Desjardins/Vollman lineage with an NNHLe-style age
term): translate each prospect's club-league scoring to NHL points-per-game
using per-league factors, boost for age (young = still improving) and draft
pedigree (top picks outperform their junior stats), then decompose into the 7
league cats. HIT/BLK have no junior signal and get NHL position 40th-percentile
rates; treat every line as a wide-error median, not a forecast.

Only players passing the make-the-NHL gate land on the draft board; the full
evaluated list is printed for manual review (overrides.csv-style judgment
stays with the human).

Reads:  data/prospect_meta.csv, data/prospect_stats.csv (fetch_prospects.py),
        data/nhl_skater_summary/realtime CSVs, data/yahoo/cat_weights.csv,
        output/projections_v2_skaters.csv (for z/vorp reference pool)
Writes: output/projections_v2_rookies.csv, output/rookies.md

Run from ./Draft Prep:  python project_rookies.py
"""
import os, unicodedata
import numpy as np
import pandas as pd

DATA, OUT = "data", "output"
LAST_SEASON = 20252026
AGE_DATE = pd.Timestamp("2027-01-15")

# NHL-equivalency factors (points): Vollman-era consensus refreshed with
# community NNHLe estimates. Leagues not listed don't translate reliably
# (tournaments, U18s) and are ignored.
NHLE = {
    "AHL": 0.47, "KHL": 0.77, "SHL": 0.62, "Liiga": 0.54, "NL": 0.46,
    "Czechia": 0.55, "DEL": 0.43, "HockeyAllsvenskan": 0.44, "SL": 0.40,
    "VHL": 0.34, "Mestis": 0.30, "NCAA": 0.41, "USHL": 0.27, "NTDP": 0.27,
    "OHL": 0.30, "WHL": 0.28, "QMJHL": 0.26, "BCHL": 0.16,
    "J20 Nationell": 0.19, "MHL": 0.23, "U20 SM-sarja": 0.18, "ECHL": 0.38,
}
SEASON_W = {20252026: 3.0, 20242025: 1.0}
MIN_CLUB_GP = 10
NHL_GP_CAP = 25          # more than this and the main model already sees them

POS_MAP = {"L": "LW", "R": "RW", "W": "RW", "F": "C"}
G_SHARE_NORM = {"D": 0.25, "F": 0.42}     # goals as share of points
REPL_INDEX = {"C": 30, "LW": 30, "RW": 30, "D": 40}   # mirror projection_model_v2


def norm_name(s):
    s = unicodedata.normalize("NFKD", str(s))
    return "".join(c for c in s if not unicodedata.combining(c)).lower().strip()


def nhle_ppg(rows):
    """Recency-and-GP-weighted NHL-equivalent points per game over club seasons."""
    w = rows["gp"] * rows["season"].map(SEASON_W)
    return float((rows["p"] / rows["gp"] * rows["league"].map(NHLE) * w).sum() / w.sum())


def age_mult(age):
    return float(np.clip(1 + 0.05 * (21 - age), 1.0, 1.20))


def pedigree_mult(overall):
    return 1.15 if overall <= 3 else 1.08 if overall <= 10 else 1.0


def build_rookies():
    meta = pd.read_csv(f"{DATA}/prospect_meta.csv")
    stats = pd.read_csv(f"{DATA}/prospect_stats.csv")
    meta = meta[(meta["pos"] != "G") & (meta["nhl_gp"] <= NHL_GP_CAP)].copy()
    stats = stats[(stats["league"].isin(NHLE)) & (stats["gp"] >= MIN_CLUB_GP)]

    # NHL position benchmarks: sh% by position; HIT/BLK per-game 40th percentile
    # (rookies play sheltered minutes — median would flatter them)
    summ = pd.read_csv(f"{DATA}/nhl_skater_summary_{LAST_SEASON}.csv").drop_duplicates("playerId")
    real = pd.read_csv(f"{DATA}/nhl_skater_realtime_{LAST_SEASON}.csv").drop_duplicates("playerId")
    nhl = summ.merge(real[["playerId", "hits", "blockedShots"]], on="playerId")
    nhl = nhl[nhl["gamesPlayed"] >= 40]
    nhl["isD"] = nhl["positionCode"] == "D"
    sh_pct = {d: nhl.loc[nhl["isD"] == d, "goals"].sum() /
                 nhl.loc[nhl["isD"] == d, "shots"].sum() for d in [True, False]}
    hit_pg = {d: (nhl.loc[nhl["isD"] == d, "hits"] /
                  nhl.loc[nhl["isD"] == d, "gamesPlayed"]).quantile(0.4) for d in [True, False]}
    blk_pg = {d: (nhl.loc[nhl["isD"] == d, "blockedShots"] /
                  nhl.loc[nhl["isD"] == d, "gamesPlayed"]).quantile(0.4) for d in [True, False]}

    rows = []
    for _, m in meta.iterrows():
        st = stats[stats["playerId"] == m["playerId"]]
        if st.empty:
            continue
        ppg = nhle_ppg(st)
        age = (AGE_DATE - pd.Timestamp(m["birthDate"])).days / 365.25
        ppg_adj = ppg * age_mult(age) * pedigree_mult(m["overall"])

        likely_nhl = (ppg_adj * 82 >= 45) or (m["nhl_gp"] >= 5) or \
                     (m["draftYear"] == 2026 and m["overall"] <= 5)
        gp = 72 if m["overall"] <= 5 else 65 if m["nhl_gp"] >= 5 else 60

        pos = POS_MAP.get(m["pos"], m["pos"])
        is_d = pos == "D"
        P = ppg_adj * gp
        g_share = 0.5 * (st["g"].sum() / max(st["p"].sum(), 1)) + \
                  0.5 * G_SHARE_NORM["D" if is_d else "F"]
        G = P * g_share
        A = P - G
        SOG = G / sh_pct[is_d]
        PPP = P * (0.32 if m["overall"] <= 10 else 0.22)
        pim_pg = (st["pim"].sum() / st["gp"].sum())
        PIM = min(pim_pg, 1.5) * 0.6 * gp
        rec = st.sort_values(["season", "gp"]).iloc[-1]
        rows.append({
            "name": m["name"], "yahoo_pos": pos, "team": m["team"],
            "age": round(age, 1), "gp_proj": gp,
            "G": round(G), "A": round(A), "PIM": round(PIM), "PPP": round(PPP),
            "SOG": round(SOG), "HIT": round(hit_pg[is_d] * gp),
            "BLK": round(blk_pg[is_d] * gp),
            "draft": f"{m['draftYear']} #{m['overall']}", "nhl_gp": m["nhl_gp"],
            "nhle_p82": round(ppg_adj * 82), "likely_nhl": likely_nhl,
            "notes": (f"ROOKIE NHLe ({rec['league']} {rec['p']}p/{rec['gp']}gp"
                      f", {m['draftYear']} #{m['overall']})"),
        })
    return pd.DataFrame(rows).sort_values("nhle_p82", ascending=False)


def add_value(rk):
    """z/vorp on the main pool's scale so rookies sort sensibly on the board."""
    sk = pd.read_csv(f"{OUT}/projections_v2_skaters.csv", encoding="utf-8-sig")
    cats = ["G", "A", "PIM", "PPP", "SOG", "HIT", "BLK"]
    wpath = f"{DATA}/yahoo/cat_weights.csv"
    cw = pd.read_csv(wpath).set_index("cat")["weight"].to_dict() if os.path.exists(wpath) else {}
    cw = {c: cw.get(c, 1.0) for c in cats}
    ref = sk.nlargest(140, "z")
    rk["z"] = sum(cw[c] * (rk[c] - ref[c].mean()) / ref[c].std(ddof=0) for c in cats).round(2)
    z_repl = {p: sk[sk["yahoo_pos"].str.split("/").map(lambda L: p in L)]["z"]
                .nlargest(n).iloc[-1] for p, n in REPL_INDEX.items()}
    rk["vorp"] = (rk["z"] - rk["yahoo_pos"].map(z_repl)).round(2)
    # already-projected players (few NHL GP but in the pool) stay in the main CSV
    taken = set(sk["name"].map(norm_name))
    return rk[~rk["name"].map(norm_name).isin(taken)]


def main():
    rk = add_value(build_rookies())
    board = rk[rk["likely_nhl"]].copy()
    cols = ["name", "yahoo_pos", "team", "age", "gp_proj", "G", "A", "PIM",
            "PPP", "SOG", "HIT", "BLK", "z", "vorp", "notes"]
    board["kept"] = ""
    board[cols + ["kept", "draft", "nhle_p82"]].to_csv(
        f"{OUT}/projections_v2_rookies.csv", index=False, encoding="utf-8-sig")

    lines = ["# NHLe rookie projections (wide error bars — medians, not forecasts)",
             "", f"## Draft-board rookies ({len(board)} pass the make-the-NHL gate)", ""]
    show = ["name", "yahoo_pos", "team", "age", "draft", "nhle_p82",
            "gp_proj", "G", "A", "SOG", "PPP", "z", "vorp"]
    for df, title in [(board, None),
                      (rk[~rk["likely_nhl"]].head(25), "## Watchlist (gated out — likely not NHL regulars yet)")]:
        if title:
            lines += ["", title, ""]
        lines.append("|" + "|".join(show) + "|")
        lines.append("|" + "|".join(["---"] * len(show)) + "|")
        for _, r in df.iterrows():
            lines.append("|" + "|".join(str(r[c]) for c in show) + "|")
    with open(f"{OUT}/rookies.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines[:40]))
    print(f"\n{OUT}/projections_v2_rookies.csv: {len(board)} board rookies "
          f"of {len(rk)} evaluated")


if __name__ == "__main__":
    main()
