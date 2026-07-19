#!/usr/bin/env python3
"""
Projection model v2 — 2026-27 draft prep, data-driven.

Replaces v1's embedded single-season lines + hand judgment with:
  - 3-season weighted per-60 rates (weights 1/3/5, TOI-weighted) x projected TOI
  - Goals = 50/50 blend of (proj SOG x regressed sh%) and (weighted ixG/60 x finishing)
  - PPP from PP-specific per-60 x projected PP TOI (deployment tilted to last season)
  - Two age curves (offense vs physical), D offensive peak one year later (v1 insight)
  - Breakout blend for age<=26 players whose last-season P/60 beats weighted by >15%
    (analog of skater_model.py reliability floor — stops regression crushing risers)
  - Goalies: weighted SV% regressed to league mean + GSAx signal, start-share model
  - Keeper overlay from KeeperLeague_2026-27_Context.md (definite keeps flagged)

Inputs: ./data/*.csv from fetch_nhl_data_v2.py
Outputs: ./output/projections_v2_skaters.csv, projections_v2_goalies.csv,
         markdown tables to stdout.

Known limitations (v2): no team-context for goalie W beyond own history; PIM
majors/minors split loaded but aged with one physical curve; 2026-27 rookies
with zero NHL games not projectable (add manually).
"""
import os, unicodedata
import numpy as np
import pandas as pd

DATA, OUT = "data", "output"
SEASONS = [20232024, 20242025, 20252026]     # production window
HIST_SEASONS = [20182019, 20192020, 20202021, 20212022, 20222023]   # career sh%
AGE_DATE = pd.Timestamp("2027-01-15")        # mid-target-season
TEAM_GAMES = 82

def season_weights(seasons):
    """Marcel 1x/3x/5x by recency (players with fewer seasons keep the recent weights)."""
    return {s: w for s, w in zip(sorted(seasons), [1.0, 3.0, 5.0][-len(seasons):])}

os.makedirs(OUT, exist_ok=True)

def norm_name(s):
    s = unicodedata.normalize("NFKD", str(s))
    return "".join(c for c in s if not unicodedata.combining(c)).lower().strip()

def load_seasons(prefix, seasons=None):
    seasons = seasons or SEASONS
    sw = season_weights(seasons)
    frames = []
    for s in seasons:
        df = pd.read_csv(f"{DATA}/{prefix}_{s}.csv")
        # unstable API sort across pages can duplicate rows at page boundaries
        df = df.drop_duplicates(subset=["playerId"])
        df["season"] = s
        df["w"] = sw[s]
        frames.append(df)
    return pd.concat(frames, ignore_index=True)

# ---------------- age curves (v1, unchanged) ----------------
def age_mult_off(age, pos):
    a = age - (1 if pos == "D" else 0)          # D offensive peak later
    for lim, m in [(21,1.10),(23,1.06),(25,1.03),(28,1.00),(30,0.975),
                   (32,0.94),(34,0.89),(36,0.84)]:
        if a <= lim: return m
    return 0.76

def age_mult_phys(age):
    for lim, m in [(23,1.03),(30,1.00),(34,0.97)]:
        if age <= lim: return m
    return 0.91

# ---------------- keeper overlay (context file, verified lists) ----------------
KEPT = {  # definite/likely keeps -> keeping team
 "Wyatt Johnston":"Sawchuk","Matthew Tkachuk":"Sawchuk","Jack Eichel":"Sawchuk",
 "Martin Necas":"Sawchuk","Mackenzie Blackwood":"Sawchuk","Evan Bouchard":"Sawchuk",
 "Will Smith":"Sawchuk","Spencer Knight":"Sawchuk","Rasmus Andersson":"Sawchuk",
 "Anton Lundell":"Sawchuk",
 "Tage Thompson":"ASD","Sam Reinhart":"ASD","Nikita Zadorov":"ASD","MacKenzie Weegar":"ASD",
 "John Tavares":"ASD","Morgan Geekie":"ASD","Filip Forsberg":"ASD","Brock Faber":"ASD",
 "Nico Hischier":"ASD","Tomas Hertl":"ASD","Alex Laferriere":"ASD","Vince Dunn":"ASD",
 "Radko Gudas":"ASD","Charlie Coyle":"ASD",
 "Adrian Kempe":"Gents","John Carlson":"Gents",
 "Andrei Svechnikov":"Autodraft","Kiefer Sherwood":"Autodraft","Jakob Chychrun":"Autodraft",
 "Mark Scheifele":"Autodraft","Brandon Hagel":"Autodraft","Filip Gustavsson":"Autodraft",
 "Scott Wedgewood":"Autodraft","Nick Suzuki":"Autodraft","Simon Edvinsson":"Autodraft",
 "Matt Boldy":"ER","Juraj Slafkovsky":"ER","Jason Robertson":"ER","Macklin Celebrini":"ER",
 "Lane Hutson":"ER","Yaroslav Askarov":"ER",
 "Tom Wilson":"Puppa","Jesper Bratt":"Puppa","Zach Hyman":"Puppa","Logan Thompson":"Puppa",
 "Seth Jones":"Puppa","Clayton Keller":"Puppa","Kirill Marchenko":"Puppa","John Gibson":"Puppa",
 "Zach Werenski":"Puppa","Alexander Nikishin":"Puppa","Aleksander Barkov":"Puppa",
 "Matthew Schaefer":"Puppa",
 "Dougie Hamilton":"PK","Matthew Knies":"PK","Cole Caufield":"PK","Adam Fantilli":"PK",
 "Dustin Wolf":"PK","Mathieu Olivier":"PK","Darcy Kuemper":"PK","Shea Theodore":"PK",
 "Cutter Gauthier":"TD","Lukas Dostal":"TD","Leo Carlsson":"TD","Jackson LaCombe":"TD",
 "Dylan Guenther":"TD","Logan Cooley":"TD","Dylan Cozens":"TD","Dylan Holloway":"TD",
}
KEPT_MAYBE = {  # coin-flip keeps per context (either/or slots, sentiment risk)
 "Sam Bennett","Drake Batherson","Jake Sanderson","Will Cuylle","Charlie McAvoy",
 "Alex Tuch","Mika Zibanejad","Trevor Zegras","Thomas Harley","Evander Kane",
 "Jacob Trouba","Joel Eriksson Ek",
}
KEPT_N = {norm_name(k): v for k, v in KEPT.items()}
MAYBE_N = {norm_name(k) for k in KEPT_MAYBE}

# ==================== SKATERS ====================
def build_skaters(seasons=None, age_date=None, hist_seasons=None, use_weights=True,
                  use_conviction=True):
    seasons = seasons or SEASONS
    last_season = max(seasons)
    age_date = age_date if age_date is not None else AGE_DATE
    hist_seasons = hist_seasons or HIST_SEASONS

    summ = load_seasons("nhl_skater_summary", seasons)
    real = load_seasons("nhl_skater_realtime", seasons)[["playerId","season","hits","blockedShots"]]
    toi  = load_seasons("nhl_skater_timeonice", seasons)[["playerId","season","timeOnIce","ppTimeOnIce"]]
    pen  = load_seasons("nhl_skater_penalties", seasons)[["playerId","season","majorPenalties","minorPenalties"]]

    df = (summ.merge(real, on=["playerId","season"], how="left")
              .merge(toi,  on=["playerId","season"], how="left")
              .merge(pen,  on=["playerId","season"], how="left"))

    # MoneyPuck ixG (situation=all), season yr -> seasonId
    mps = []
    for s in seasons:
        yr = int(str(s)[:4])
        mp = pd.read_csv(f"{DATA}/moneypuck_skaters_{yr}.csv")
        mp = mp[mp["situation"] == "all"][["playerId","I_F_xGoals",
              "I_F_primaryAssists","I_F_secondaryAssists"]].drop_duplicates(subset=["playerId"])
        mp["season"] = s
        mps.append(mp)
    df = df.merge(pd.concat(mps, ignore_index=True), on=["playerId","season"], how="left")

    # bios: latest season available per player
    bios = load_seasons("nhl_skater_bios", seasons)
    bios = (bios.sort_values("season")
                .groupby("playerId").last().reset_index()
                [["playerId","birthDate","currentTeamAbbrev","positionCode"]]
                .rename(columns={"positionCode":"posBio"}))

    # sanity: TOI fields are seconds
    assert df["timeOnIce"].max() > 50000, "timeOnIce doesn't look like seconds"

    g = df.groupby("playerId")
    def wsum(col): return g.apply(lambda x: (x["w"] * x[col].fillna(0)).sum())

    out = pd.DataFrame({
        "name":   g["skaterFullName"].last(),
        "pos":    g["positionCode"].last(),
        "team":   g["teamAbbrevs"].last(),
        "gp_last": g.apply(lambda x: x.loc[x["season"]==last_season, "gamesPlayed"].sum()),
        "seasons": g["season"].nunique(),
    })
    wtoi = wsum("timeOnIce"); wgp = wsum("gamesPlayed")
    wppt = wsum("ppTimeOnIce")
    W = g["w"].sum()

    # weighted per-60 rates (TOI-weighted Marcel)
    for col, nm in [("goals","g"),("assists","a"),("shots","sog"),("hits","hit"),
                    ("blockedShots","blk"),("penaltyMinutes","pim"),("I_F_xGoals","xg")]:
        out[nm+"60"] = (wsum(col) / wtoi * 3600).fillna(0)
    out["ppp60pp"] = (wsum("ppPoints") / wppt.replace(0, np.nan) * 3600).fillna(0)

    # last-season rates for breakout blend + deployment tilt
    last = df[df["season"] == last_season].set_index("playerId")
    out["toi_pg_w"]  = wtoi / wgp.replace(0, np.nan)
    out["toi_pg_last"] = last["timeOnIce"] / last["gamesPlayed"]
    out["ppt_pg_w"]  = wppt / wgp.replace(0, np.nan)
    out["ppt_pg_last"] = last["ppTimeOnIce"] / last["gamesPlayed"]
    out["p60_w"] = (wsum("points") / wtoi * 3600)
    out["p60_last"] = (last["points"] / last["timeOnIce"] * 3600)
    # prior-seasons-only P/60 for breakout detection: comparing vs the 1/3/5
    # weighted avg can't work — it's already majority last-season
    prior = df[df["season"] < last_season]
    gp_prior = prior.groupby("playerId")
    out["p60_prior"] = (gp_prior.apply(lambda x: (x["w"]*x["points"]).sum()) /
                        gp_prior.apply(lambda x: (x["w"]*x["timeOnIce"]).sum()) * 3600)
    for col, nm in [("goals","g"),("assists","a"),("shots","sog"),("I_F_xGoals","xg"),
                    ("ppPoints","ppp_raw")]:
        out[nm+"60_last"] = (last[col] / last["timeOnIce"] * 3600)
    out["ppp60pp_last"] = (last["ppPoints"] / last["ppTimeOnIce"].replace(0,np.nan) * 3600)

    # GP projection: weighted share regressed toward 92% of 82
    out["gp_share_w"] = (wgp / (W * TEAM_GAMES)).clip(upper=1.0)
    out["gp_proj"] = (TEAM_GAMES * (0.65*out["gp_share_w"] + 0.35*0.92)).round().clip(upper=82).astype(int)

    # TOI projection: weighted with recent tilt (deployment is sticky-recent)
    out["toi_pg_proj"] = 0.7*out["toi_pg_w"] + 0.3*out["toi_pg_last"].fillna(out["toi_pg_w"])
    out["ppt_pg_proj"] = 0.5*out["ppt_pg_w"] + 0.5*out["ppt_pg_last"].fillna(out["ppt_pg_w"])

    # age + current team from bios
    out = out.reset_index().merge(bios, on="playerId", how="left")
    out["age"] = ((age_date - pd.to_datetime(out["birthDate"])).dt.days / 365.25)
    out["age"] = out["age"].fillna(27).round(1)
    out["team"] = out["currentTeamAbbrev"].fillna(out["team"])

    # breakout blend (reliability-floor analog): young risers tilt to last season
    ratio = out["p60_last"] / out["p60_prior"].replace(0, np.nan)
    out["breakout"] = (out["age"] <= 26) & (out["gp_last"] >= 40) & (ratio > 1.2)
    b = np.where(out["breakout"], 0.5, 0.0)
    for nm in ["g60","a60","sog60","xg60"]:
        lastcol = out[nm+"_last"].fillna(out[nm])
        out[nm] = (1-b)*out[nm] + b*lastcol
    out["ppp60pp"] = np.where(out["breakout"],
                              0.5*out["ppp60pp"] + 0.5*out["ppp60pp_last"].fillna(out["ppp60pp"]),
                              out["ppp60pp"])

    # team-conviction signal (contracts.csv from fetch_contracts.py): a big
    # post-ELC bet on an age<=25 player publishes the team's private
    # development data (LaCombe signed $9M before his breakout). Unlocks a
    # softer breakout treatment for players the rate-detector can't reach —
    # single-season players and near-miss sophomores. Not used in backtests:
    # only current contracts exist, which would leak the future.
    out["conviction"] = False
    out["conv_mult"] = 1.0
    cpath = f"{DATA}/contracts.csv"
    if use_conviction and os.path.exists(cpath):
        con = pd.read_csv(cpath)
        con["nn"] = con["name"].map(
            lambda s: norm_name(" ".join(reversed(str(s).split(", ")))))
        big = con[(con["aav"] >= 5_500_000) |
                  ((con["aav"] >= 4_000_000) & (con["years_left"] >= 5))]
        nn = out["name"].map(norm_name)
        out["conviction"] = (nn.isin(set(big["nn"])) & (out["age"] <= 25.5)
                             & ~out["breakout"])
        b2 = np.where(out["conviction"], 0.35, 0.0)
        for nm in ["g60","a60","sog60","xg60"]:
            lastcol = out[nm+"_last"].fillna(out[nm])
            out[nm] = (1-b2)*out[nm] + b2*lastcol
        out["ppp60pp"] = np.where(
            out["conviction"],
            0.65*out["ppp60pp"] + 0.35*out["ppp60pp_last"].fillna(out["ppp60pp"]),
            out["ppp60pp"])
        out["conv_mult"] = np.where(out["conviction"], 1.05, 1.0)

    # ---- shooting % regression (career 2018-26 + weighted recent, position prior)
    hist = pd.concat([pd.read_csv(f"{DATA}/nhl_shpct_{s}.csv").drop_duplicates(subset=["playerId"])
                      for s in hist_seasons],
                     ignore_index=True)
    career = pd.concat([hist[["playerId","goals","shots"]],
                        df[["playerId","goals","shots"]]], ignore_index=True) \
               .groupby("playerId").sum().rename(columns={"goals":"cG","shots":"cS"})
    out = out.merge(career, on="playerId", how="left").fillna({"cG":0,"cS":0})
    last26 = df[df["season"] == last_season]
    prior = {p: last26.loc[last26["positionCode"].eq("D") == (p=="D"), "goals"].sum() /
                max(last26.loc[last26["positionCode"].eq("D") == (p=="D"), "shots"].sum(), 1)
             for p in ["D","F"]}
    pos_prior = out["pos"].map(lambda p: prior["D"] if p == "D" else prior["F"])
    w3G, w3S = wsum("goals").reindex(out["playerId"]).values, wsum("shots").reindex(out["playerId"]).values
    career_reg = (out["cG"] + 400*pos_prior) / (out["cS"] + 400)
    recent_reg = (w3G + 150*pos_prior) / (w3S + 150)
    out["sh_proj"] = 0.55*recent_reg + 0.45*career_reg
    out["sh_last"] = (last["goals"] / last["shots"].replace(0,np.nan)).reindex(out["playerId"]).values

    # finishing vs xG (3yr), regressed to 1
    rawG = df.groupby("playerId")["goals"].sum().reindex(out["playerId"]).values
    rawXG = df.groupby("playerId")["I_F_xGoals"].sum().reindex(out["playerId"]).values
    out["fin"] = ((rawG + 10) / (np.nan_to_num(rawXG) + 10)).clip(0.8, 1.3)

    # ---- A1 share (assist sustainability): secondary assists are far noisier
    # year-over-year than primary, so an assist total built on A2s is regression
    # risk. Flag players >1 SD below their position's A1-share norm (min 60
    # assists over the window so the share itself isn't noise).
    a1 = df.groupby("playerId")["I_F_primaryAssists"].sum().reindex(out["playerId"]).values
    a2 = df.groupby("playerId")["I_F_secondaryAssists"].sum().reindex(out["playerId"]).values
    a_tot = np.nan_to_num(a1) + np.nan_to_num(a2)
    out["a1_share"] = np.where(a_tot >= 60, np.nan_to_num(a1) / np.maximum(a_tot, 1), np.nan)
    is_d = out["pos"].eq("D").values
    a1_norm, a1_std = {}, {}
    for d in [True, False]:
        grp = out.loc[(is_d == d) & out["a1_share"].notna(), "a1_share"]
        a1_norm[d], a1_std[d] = grp.mean(), grp.std(ddof=0)
    out["a1_pos_norm"] = [a1_norm[d] for d in is_d]
    out["a2_heavy"] = (out["a1_share"] <
                       out["a1_pos_norm"] - np.array([a1_std[d] for d in is_d]))
    out["a2_heavy"] = out["a2_heavy"].fillna(False)

    # manual deployment overrides (offseason moves, line changes — overrides.csv)
    out["off_mult"] = 1.0
    if os.path.exists("overrides.csv"):
        ov = pd.read_csv("overrides.csv")
        ov["nn"] = ov["name"].map(norm_name)
        omap = ov.set_index("nn")["off_mult"].to_dict()
        onote = ov.set_index("nn")["note"].to_dict()
        nn = out["name"].map(norm_name)
        out["off_mult"] = nn.map(omap).fillna(1.0)
        out["ov_note"] = nn.map(onote).fillna("")
    else:
        out["ov_note"] = ""

    # ---- assemble projections
    mo = (np.array([age_mult_off(a, p) for a, p in zip(out["age"], out["pos"])])
          * out["off_mult"].values * out["conv_mult"].values)
    mp_ = np.array([age_mult_phys(a) for a in out["age"]])
    hrs = out["toi_pg_proj"] * out["gp_proj"] / 3600
    pphrs = out["ppt_pg_proj"] * out["gp_proj"] / 3600

    out["SOG"] = (out["sog60"] * mo * hrs)
    g_shot = out["SOG"] * out["sh_proj"]
    g_xg   = out["xg60"] * mo * hrs * out["fin"]
    out["G"] = np.where(out["xg60"] > 0, 0.5*g_shot + 0.5*g_xg, g_shot)
    out["A"] = out["a60"] * mo * hrs
    out["PPP"] = (out["ppp60pp"] * mo * pphrs)
    out["HIT"] = out["hit60"] * mp_ * hrs
    out["BLK"] = out["blk60"] * mp_ * hrs
    out["PIM"] = out["pim60"] * mp_ * hrs
    for c in ["G","A","PIM","PPP","SOG","HIT","BLK"]:
        # fringe players (near-zero TOI samples) can produce inf/NaN rates;
        # they fall below the pool filter regardless
        out[c] = out[c].replace([np.inf, -np.inf], np.nan).fillna(0).round().astype(int)

    # notes
    notes = []
    for _, r in out.iterrows():
        n = []
        if r["breakout"]: n.append("breakout blend")
        if pd.notna(r["sh_last"]):
            d = r["sh_last"] - r["sh_proj"]
            if d > 0.02: n.append(f"sh% regress DOWN ({r['sh_last']:.1%}->{r['sh_proj']:.1%})")
            elif d < -0.02: n.append(f"sh% regress UP ({r['sh_last']:.1%}->{r['sh_proj']:.1%})")
        if r["a2_heavy"] and r["A"] >= 25:
            n.append(f"A regress risk (A1 {r['a1_share']:.0%} vs "
                     f"{'D' if r['pos']=='D' else 'F'} avg {r['a1_pos_norm']:.0%})")
        if r["gp_share_w"] < 0.72 and r["seasons"] > 1: n.append("GP risk")
        if r["age"] >= 33: n.append("age fade applied")
        if r["ov_note"]: n.append(f"OVERRIDE {r['off_mult']}: {r['ov_note']}")
        if r["conviction"]: n.append("team-conviction contract")
        notes.append("; ".join(n))
    out["notes"] = notes

    nn = out["name"].map(norm_name)
    out["kept"] = nn.map(KEPT_N).fillna("")
    out.loc[nn.isin(MAYBE_N), "kept"] = "keep?"

    # pool + two-pass z-sum over draftable skaters, weighted by category
    # leverage (data/yahoo/cat_weights.csv from analyze_league_2025.py)
    pool = out[(out["gp_proj"] >= 40) & (out["gp_last"] + 0.4*wgp.reindex(out["playerId"]).fillna(0).values >= 30)].copy()
    cats = ["G","A","PIM","PPP","SOG","HIT","BLK"]
    wpath = f"{DATA}/yahoo/cat_weights.csv"
    if use_weights and os.path.exists(wpath):
        cw = pd.read_csv(wpath).set_index("cat")["weight"].to_dict()
    else:
        cw = {}
    cw = {c: cw.get(c, 1.0) for c in cats}
    def zsum(frame, ref):
        return sum(cw[c] * (frame[c] - ref[c].mean()) / ref[c].std(ddof=0) for c in cats)
    pool["z"] = zsum(pool, pool)
    ref = pool.nlargest(140, "z")          # draftable pool defines replacement level (20-slot rosters)
    pool["z"] = zsum(pool, ref).round(2)
    pool = pool.sort_values("z", ascending=False)
    return pool

# ==================== Yahoo eligibility + positional VORP ====================
# Roster: 3C/3LW/3RW/4D x8 teams (2026-27 change: was 5D; 20 total slots);
# replacement index = starters + bench share.
REPL_INDEX = {"C": 30, "LW": 30, "RW": 30, "D": 40}
MULTIPOS_BONUS = 0.25   # project convention: +0.25 per extra eligible position

def add_yahoo_eligibility(sk):
    path = f"{DATA}/yahoo/eligibility.csv"
    if not os.path.exists(path):
        sk["yahoo_pos"], sk["vorp"] = "", sk["z"]
        return sk
    el = pd.read_csv(path)
    el["nn"] = el["name"].map(norm_name)
    sk = sk.copy()
    sk["nn"] = sk["name"].map(norm_name)
    sk = sk.merge(el[["nn","eligible_positions"]].drop_duplicates("nn"), on="nn", how="left")
    fallback = sk["pos"].map({"C":"C","L":"LW","R":"RW","D":"D"}).fillna("C")
    sk["yahoo_pos"] = sk["eligible_positions"].fillna(fallback)
    sk["pos_list"] = sk["yahoo_pos"].str.split("/")

    z_repl = {}
    for p, n in REPL_INDEX.items():
        elig = sk[sk["pos_list"].map(lambda L: p in L)]
        z_repl[p] = elig["z"].nlargest(n).iloc[-1] if len(elig) >= n else elig["z"].min()

    def vorp(row):
        best = max((row["z"] - z_repl[p]) for p in row["pos_list"] if p in z_repl)
        return best + MULTIPOS_BONUS * (len([p for p in row["pos_list"] if p in z_repl]) - 1)
    sk["vorp"] = sk.apply(vorp, axis=1).round(2)
    return sk.drop(columns=["nn","eligible_positions","pos_list"]).sort_values("vorp", ascending=False)

# ==================== GOALIES ====================
def build_goalies(seasons=None):
    seasons = seasons or SEASONS
    last_season = max(seasons)
    df = load_seasons("nhl_goalie_summary", seasons)
    mps = []
    for s in seasons:
        yr = int(str(s)[:4])
        mp = pd.read_csv(f"{DATA}/moneypuck_goalies_{yr}.csv")
        mp = mp[mp["situation"] == "all"][["playerId","xGoals","goals","icetime"]].drop_duplicates(subset=["playerId"])
        mp.columns = ["playerId","mpXG","mpGA","mpTOI"]
        mp["season"] = s
        mps.append(mp)
    df = df.merge(pd.concat(mps, ignore_index=True), on=["playerId","season"], how="left")

    lg_sv = df.loc[df["season"]==last_season, "saves"].sum() / df.loc[df["season"]==last_season, "shotsAgainst"].sum()

    g = df.groupby("playerId")
    def wsum(col): return g.apply(lambda x: (x["w"] * x[col].fillna(0)).sum())

    out = pd.DataFrame({
        "name": g["goalieFullName"].last(),
        "team": g["teamAbbrevs"].last(),
        "gs_last": g.apply(lambda x: x.loc[x["season"]==last_season, "gamesStarted"].sum()),
    })
    W = g["w"].sum()
    sa, sv, gs, wins, so = (wsum(c) for c in ["shotsAgainst","saves","gamesStarted","wins","shutouts"])
    xg, ga_mp, mtoi = wsum("mpXG"), wsum("mpGA"), wsum("mpTOI")

    sv_w = sv / sa.replace(0, np.nan)
    shrink = sa / (sa + 2800)
    dsvx = ((xg - ga_mp) / sa.replace(0, np.nan)).fillna(0)      # GSAx per shot
    out["sv_proj"] = (lg_sv + shrink*(0.6*(sv_w - lg_sv) + 0.4*dsvx)).round(4)
    out["gsax60"] = ((xg - ga_mp) / mtoi.replace(0,np.nan) * 3600).round(2)

    share_w = gs / (W * TEAM_GAMES)
    share_last = out["gs_last"] / TEAM_GAMES
    out["starts_proj"] = (TEAM_GAMES * (0.45*share_w + 0.55*share_last)).round().clip(upper=62)

    wr = ((wins + 0.5*25) / (gs + 25))                            # win rate, regressed
    out["W"] = (out["starts_proj"] * wr).round().astype(int)
    sr = (so + 0.04*30) / (gs + 30)
    out["SHO"] = (sr * out["starts_proj"]).round(1)

    pool = out[out["starts_proj"] >= 20].copy()
    for c, col in [("W","W"),("SV","sv_proj"),("SHO","SHO")]:
        pool["z"+c] = (pool[col] - pool[col].mean()) / pool[col].std(ddof=0)
    pool["z"] = (pool["zW"] + pool["zSV"] + pool["zSHO"]).round(2)
    nn = pool["name"].map(norm_name)
    pool["kept"] = nn.map(KEPT_N).fillna("")
    pool.loc[nn.isin(MAYBE_N), "kept"] = "keep?"
    return pool.sort_values("z", ascending=False)

# ==================== output ====================
def add_tiers(df, col, gap):
    """New tier wherever consecutive (sorted desc) values drop by >= gap."""
    tiers, t, prev = [], 1, None
    for v in df[col]:
        if prev is not None and (prev - v) >= gap:
            t += 1
        tiers.append(t)
        prev = v
    df = df.copy()
    df["tier"] = tiers
    return df

def md_table(df, cols, n, rank=True):
    lines = ["|#|" + "|".join(cols) + "|" if rank else "|" + "|".join(cols) + "|",
             "|" + "|".join(["---"] * (len(cols) + (1 if rank else 0))) + "|"]
    for i, (_, r) in enumerate(df.head(n).iterrows(), 1):
        cells = ([str(i)] if rank else []) + [str(r[c]) for c in cols]
        lines.append("|" + "|".join(cells) + "|")
    return "\n".join(lines)

if __name__ == "__main__":
    sk = build_skaters()
    sk = add_yahoo_eligibility(sk)
    gl = build_goalies()

    def safe_csv(df, path):
        try:
            df.to_csv(path, index=False, encoding="utf-8-sig")
        except PermissionError:   # file open in Excel — don't lose the run
            alt = path.replace(".csv", "_new.csv")
            df.to_csv(alt, index=False, encoding="utf-8-sig")
            print(f"WARNING: {path} locked (open in Excel?); wrote {alt}")

    keep_cols = ["name","yahoo_pos","team","age","gp_proj","G","A","PIM","PPP","SOG","HIT","BLK","z","vorp","kept","notes"]
    safe_csv(sk[keep_cols + ["sh_proj","fin","toi_pg_proj","breakout","a1_share"]], f"{OUT}/projections_v2_skaters.csv")
    gcols = ["name","team","starts_proj","W","sv_proj","SHO","gsax60","z","kept"]
    safe_csv(gl[gcols], f"{OUT}/projections_v2_goalies.csv")

    sk2 = sk.copy(); sk2["age"] = sk2["age"].round(0).astype(int)
    avail = add_tiers(sk2[sk2["kept"].isin(["", "keep?"])], "vorp", 0.45)
    keep_cols_avail = keep_cols[:keep_cols.index("kept")] + ["tier"] + keep_cols[keep_cols.index("kept"):]
    md = "\n\n".join([
        "# 2026-27 Projections v2 — data-driven (3-season weighted per-60 x TOI, ixG blend)",
        f"## Skaters — top 100 of {len(sk)} (7-cat z-sum, keeper-flagged)",
        md_table(sk2, keep_cols, 100),
        f"## Available skaters only (keepers removed, tiered) — top 60",
        md_table(avail, keep_cols_avail, 60),
        f"## Goalies — top 30 of {len(gl)}",
        md_table(add_tiers(gl, "z", 0.45), gcols + ["tier"], 30),
        f"Pool sizes: {len(sk)} skaters, {len(gl)} goalies. CSVs in ./{OUT}/.",
    ])
    with open(f"{OUT}/projections_v2.md", "w", encoding="utf-8") as f:
        f.write(md + "\n")
    print(md)
