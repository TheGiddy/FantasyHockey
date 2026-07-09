#!/usr/bin/env python3
"""
Build a self-contained interactive HTML draft board from the v2 projections.

Reads output/projections_v2_{skaters,goalies}.csv and writes a single
output/draft_board.html with no external dependencies — open it directly in a
browser (prep or live draft, offline). Features:
  - dense, sortable/filterable big board (position tabs, search)
  - click a row to mark a player drafted (greys out -> top rows stay best-available)
  - claim a player to YOUR roster; keepers (kept==TD) are pre-claimed
  - roster-slot fill (3C/3LW/3RW/4D/2G/5BN) using multi-position eligibility,
    showing what you still need
  - goalie-tier tracker (the "don't punt goalies" cue from the two-season analysis)
  - collapsible opponent-intel panel (category profiles, posture, top threat)
  - localStorage persistence + reset

Run from ./Draft Prep:  python build_draft_board.py
"""
import csv
import json
from datetime import date

SK_CSV = "output/projections_v2_skaters.csv"
G_CSV = "output/projections_v2_goalies.csv"
OUT = "output/draft_board.html"

MY = "TD"                      # keeper flag for Twin Daddy in the CSVs
MAX_SKATERS = 320              # top-N skaters by vorp (rest is draft noise)
ROSTER = {"C": 3, "LW": 3, "RW": 3, "D": 4, "G": 2, "BN": 5}
SK_STATS = ["G", "A", "PIM", "PPP", "SOG", "HIT", "BLK"]

# Opponent intel from analyze_opponents.py + the H2H / draft-tendency analysis.
# Static snapshot of this session's findings (see output/opponents_analysis.md).
INTEL = {
    "headline": "Most dangerous: Sawchuk Dun Thats — #1 record (60%), beats TD "
                "H2H (3-4-1), and wins the goalie cats (W/SV%) that are your "
                "structural hole. Draft a starting goalie by R3–R5; don't punt.",
    "teams": [
        {"t": "Sawchuk Dun Thats", "rec": "28-17-2 (60%)", "strong": "BLK, SV%, W",
         "soft": "G, A", "posture": "steady contender", "gRound": "R6 / 4 goalies",
         "note": "TOP THREAT. Owns goalie cats + BLK/SOG. Attack with G/A."},
        {"t": "Twin Daddy (you)", "rec": "25-18-2 (56%)", "strong": "G, A, PPP",
         "soft": "W, SV%, SHO", "posture": "retool → contend", "gRound": "R15 / 2 goalies",
         "note": "Drafts goalies LAST & fewest — the root of the goalie hole."},
        {"t": "AdamSuxDix", "rec": "23-18-6 (49%)", "strong": "HIT, SV%",
         "soft": "A, W", "posture": "pick hoarder (+136 cap)", "gRound": "R5.5 / 3",
         "note": "Loaded with 2026-27 early picks — may reach early."},
        {"t": "Puppa'd Your Pants", "rec": "21-20-3 (48%)", "strong": "A, SV%",
         "soft": "G, BLK", "posture": "seller '24-25", "gRound": "R2.5 / 3.5",
         "note": "Goalie-early team; strong ratios."},
        {"t": "Autodraft", "rec": "21-21-3 (47%)", "strong": "HIT, BLK",
         "soft": "PPP, W", "posture": "managed (not orphan)", "gRound": "R15.5 / 2",
         "note": "Real team; motivated to trade fallers."},
        {"t": "The Most Distinguished Gents", "rec": "20-23-1 (45%)", "strong": "W, PIM",
         "soft": "PPP, A", "posture": "aggressive BUYER (−154 cap)", "gRound": "R10 / 3.5",
         "note": "Went all-in '25-26; TD owns them 5-1. Sell them talent for picks."},
        {"t": "Emotional Reactions", "rec": "17-22-5 (39%)", "strong": "SV%, A",
         "soft": "HIT, W", "posture": "mixed", "gRound": "R3 / 3.5",
         "note": "Elite goalies (SV% 93%) but weak overall."},
        {"t": "P.K. SubUwU", "rec": "12-28-4 (27%)", "strong": "SOG, PPP",
         "soft": "PIM, BLK", "posture": "seller / cellar (+76 cap)", "gRound": "R2 / 3",
         "note": "League doormat holding picks — target to buy talent cheap."},
    ],
}


def _num(v, cast=float, default=None):
    try:
        return cast(v)
    except (ValueError, TypeError):
        return default


def load_skaters():
    players = []
    with open(SK_CSV, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            vorp = _num(r.get("vorp"), float, default=None)
            if vorp is None:
                continue
            players.append({
                "name": r["name"], "pos": r.get("yahoo_pos", "") or "",
                "team": r.get("team", ""), "age": _num(r.get("age"), float, 0),
                "val": round(vorp, 2), "z": _num(r.get("z"), float, 0),
                "kept": (r.get("kept") or "").strip(), "type": "S",
                "note": (r.get("notes") or "").strip(),
                "breakout": (r.get("breakout") or "").strip().lower() == "true",
                "stats": {s: _num(r.get(s), float, 0) for s in SK_STATS},
            })
    players.sort(key=lambda p: -p["val"])
    return players[:MAX_SKATERS]


def load_goalies():
    players = []
    with open(G_CSV, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            z = _num(r.get("z"), float, None)
            if z is None:
                continue
            players.append({
                "name": r["name"], "pos": "G", "team": (r.get("team") or "").lstrip('"'),
                "age": 0, "val": round(z, 2), "z": round(z, 2),
                "kept": (r.get("kept") or "").strip(), "type": "G",
                "note": "", "breakout": False,
                "stats": {"starts": _num(r.get("starts_proj"), float, 0),
                          "W": _num(r.get("W"), float, 0),
                          "SV%": _num(r.get("sv_proj"), float, 0),
                          "SHO": _num(r.get("SHO"), float, 0),
                          "GSAx": _num(r.get("gsax60"), float, 0)},
            })
    players.sort(key=lambda p: -p["val"])
    return players


def sk_tier(v):
    return 1 if v >= 5 else 2 if v >= 3 else 3 if v >= 1.5 else 4 if v >= 0.5 else 5


def g_tier(z):
    return 1 if z >= 4 else 2 if z >= 2.5 else 3 if z >= 1.5 else 4 if z >= 0.7 else 5


def assemble():
    players = load_skaters() + load_goalies()
    for i, p in enumerate(players):
        p["id"] = i
        p["tier"] = g_tier(p["z"]) if p["type"] == "G" else sk_tier(p["val"])
    # overall rank by value (mixed vorp/z — a rough cross-position proxy)
    for rank, p in enumerate(sorted(players, key=lambda x: -x["val"]), 1):
        p["rank"] = rank
    return players


def render(players):
    data = json.dumps(players, ensure_ascii=False)
    intel = json.dumps(INTEL, ensure_ascii=False)
    roster = json.dumps(ROSTER)
    return HTML.replace("__DATA__", data).replace("__INTEL__", intel) \
               .replace("__ROSTER__", roster).replace("__DATE__", str(date.today())) \
               .replace("__MY__", MY).replace("__SKSTATS__", json.dumps(SK_STATS))


def main():
    players = assemble()
    html = render(players)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    n_sk = sum(1 for p in players if p["type"] == "S")
    n_g = sum(1 for p in players if p["type"] == "G")
    n_keep = sum(1 for p in players if p["kept"] == MY)
    print(f"{OUT}: {n_sk} skaters + {n_g} goalies, {n_keep} TD keepers pre-claimed")


# --------------------------------------------------------------------------
# Self-contained page. __TOKENS__ are replaced above. All CSS/JS inline.
# --------------------------------------------------------------------------
HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Twin Daddy — 2026-27 Draft Board</title>
<style>
  :root{
    --bg:#0f1216; --panel:#171b22; --panel2:#1e242d; --line:#2a323d;
    --txt:#e6eaf0; --dim:#95a1b2; --acc:#4ea1ff; --my:#2ec26b; --keepother:#6b7280;
    --warn:#ffb020; --t1:#7c5cff; --t2:#4ea1ff; --t3:#2ec26b; --t4:#c9a227; --t5:#5a6472;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--txt);
    font:13px/1.4 -apple-system,Segoe UI,Roboto,Arial,sans-serif}
  header{display:flex;align-items:center;gap:14px;padding:10px 16px;
    background:var(--panel);border-bottom:1px solid var(--line);position:sticky;top:0;z-index:5}
  header h1{font-size:15px;margin:0;font-weight:700;letter-spacing:.2px}
  header .date{color:var(--dim);font-size:11px}
  .banner{background:linear-gradient(90deg,#2a1e12,#171b22);color:var(--warn);
    padding:7px 16px;font-size:12px;border-bottom:1px solid var(--line)}
  .wrap{display:flex;gap:12px;padding:12px;align-items:flex-start}
  .main{flex:1 1 auto;min-width:0}
  .side{flex:0 0 300px;display:flex;flex-direction:column;gap:12px;position:sticky;top:52px}
  .controls{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:8px;align-items:center}
  .tab{padding:4px 11px;border:1px solid var(--line);border-radius:14px;background:var(--panel);
    color:var(--dim);cursor:pointer;user-select:none;font-weight:600}
  .tab.on{background:var(--acc);color:#04101f;border-color:var(--acc)}
  input[type=search]{background:var(--panel);border:1px solid var(--line);color:var(--txt);
    padding:5px 9px;border-radius:6px;min-width:150px}
  .toggle{color:var(--dim);cursor:pointer;user-select:none;display:flex;align-items:center;gap:4px}
  .toggle input{accent-color:var(--acc)}
  button.reset{margin-left:auto;background:var(--panel2);color:var(--dim);border:1px solid var(--line);
    padding:5px 10px;border-radius:6px;cursor:pointer}
  table{width:100%;border-collapse:collapse}
  th,td{padding:3px 6px;text-align:right;white-space:nowrap}
  th{position:sticky;top:52px;background:var(--panel);color:var(--dim);font-weight:600;
    border-bottom:1px solid var(--line);cursor:pointer;z-index:3}
  th.l,td.l{text-align:left}
  tbody tr{border-bottom:1px solid #1c222b;cursor:pointer}
  tbody tr:hover{background:#1b222c}
  td.name{font-weight:600}
  .tier{display:inline-block;width:4px;height:14px;border-radius:2px;vertical-align:middle;margin-right:5px}
  .t1{background:var(--t1)}.t2{background:var(--t2)}.t3{background:var(--t3)}.t4{background:var(--t4)}.t5{background:var(--t5)}
  .pos{color:var(--dim);font-size:11px}
  .val{font-weight:700}
  tr.gone{opacity:.32}
  tr.gone td.name{text-decoration:line-through}
  tr.mine{background:rgba(46,194,107,.10)}
  tr.mine:hover{background:rgba(46,194,107,.16)}
  .badge{font-size:10px;padding:1px 5px;border-radius:8px;font-weight:700}
  .b-my{background:var(--my);color:#04140a}
  .b-other{background:var(--keepother);color:#0c0f14}
  .b-maybe{background:var(--warn);color:#1c1204}
  .b-brk{background:#7c5cff;color:#fff}
  .act{display:inline-flex;gap:3px}
  .act b{width:20px;height:18px;line-height:17px;text-align:center;border:1px solid var(--line);
    border-radius:4px;color:var(--dim);font-weight:700;font-size:12px}
  .act b.claim:hover{background:var(--my);color:#04140a;border-color:var(--my)}
  .act b.x:hover{background:#e0524d;color:#fff;border-color:#e0524d}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:10px 12px}
  .card h2{margin:0 0 8px;font-size:12px;text-transform:uppercase;letter-spacing:.5px;color:var(--dim)}
  .slot{display:flex;justify-content:space-between;align-items:center;padding:3px 0;border-bottom:1px solid #1c222b}
  .slot .lbl{color:var(--dim);font-weight:600}
  .slot .fill{display:flex;gap:3px;flex-wrap:wrap;justify-content:flex-end;max-width:210px}
  .chip{background:var(--panel2);border:1px solid var(--line);border-radius:10px;padding:1px 6px;font-size:11px}
  .chip.keep{border-color:var(--my);color:var(--my)}
  .need{color:var(--warn);font-weight:700}
  .ok{color:var(--my);font-weight:700}
  .gt{display:flex;justify-content:space-between;padding:2px 0}
  .gt .n{font-weight:700}
  details summary{cursor:pointer;color:var(--dim);font-weight:600;font-size:12px}
  .team{border-bottom:1px solid #1c222b;padding:6px 0}
  .team .nm{font-weight:700}
  .team .meta{color:var(--dim);font-size:11px}
  .team .s{color:var(--my)}.team .w{color:#e0847d}
  .foot{color:var(--dim);font-size:11px;padding:8px 16px}
</style>
</head>
<body>
<header>
  <h1>🏒 Twin Daddy — 2026-27 Draft Board</h1>
  <span class="date">generated __DATE__ · value = VORP (skaters) / z (goalies)</span>
</header>
<div class="banner" id="banner"></div>

<div class="wrap">
  <div class="main">
    <div class="controls">
      <span class="tab on" data-pos="ALL">All</span>
      <span class="tab" data-pos="C">C</span>
      <span class="tab" data-pos="LW">LW</span>
      <span class="tab" data-pos="RW">RW</span>
      <span class="tab" data-pos="D">D</span>
      <span class="tab" data-pos="G">G</span>
      <input type="search" id="q" placeholder="search player…">
      <label class="toggle"><input type="checkbox" id="hideGone">hide drafted</label>
      <label class="toggle"><input type="checkbox" id="mineOnly">my roster only</label>
      <button class="reset" id="reset">reset draft</button>
    </div>
    <table id="board">
      <thead><tr id="head"></tr></thead>
      <tbody id="rows"></tbody>
    </table>
  </div>

  <div class="side">
    <div class="card">
      <h2>My roster fill</h2>
      <div id="roster"></div>
    </div>
    <div class="card">
      <h2>Goalie tiers left <span style="color:var(--warn)">(don't punt)</span></h2>
      <div id="gtrack"></div>
    </div>
    <div class="card">
      <details>
        <summary>Opponent intel</summary>
        <div id="intel" style="margin-top:8px"></div>
      </details>
    </div>
  </div>
</div>
<div class="foot">Click a row to mark drafted (any team). Use <b>＋</b> to claim to your roster, <b>✗</b> to just remove. State saves locally.</div>

<script>
const PLAYERS = __DATA__;
const INTEL = __INTEL__;
const ROSTER = __ROSTER__;
const SKSTATS = __SKSTATS__;
const MY = "__MY__";
const KEY = "tdDraft2627";

// ---- state: gone (drafted by anyone), mine (my roster) ----
let state = load();
function load(){
  try{const s=JSON.parse(localStorage.getItem(KEY)); if(s) return s;}catch(e){}
  return seed();
}
function seed(){
  // pre-claim TD keepers; opponent keepers are gone from the pool
  const gone={}, mine={};
  for(const p of PLAYERS){
    if(p.kept===MY){mine[p.id]=1; gone[p.id]=1;}
    else if(p.kept && p.kept!=="keep?"){gone[p.id]=1;}
  }
  return {gone,mine};
}
function save(){localStorage.setItem(KEY, JSON.stringify(state));}

let pos="ALL", q="", hideGone=false, mineOnly=false;
let sortKey="rank", sortDir=1;

const byId = Object.fromEntries(PLAYERS.map(p=>[p.id,p]));

function colset(){
  if(pos==="G") return [["rank","#"],["val","Val"],["name","Player"],["team","Tm"],
    ["starts","GS"],["W","W"],["SV%","SV%"],["SHO","SHO"],["GSAx","GSAx"],["act",""]];
  const base=[["rank","#"],["val","VORP"],["name","Player"],["pos","Pos"],["team","Tm"],["age","Age"]];
  if(pos==="ALL") return [...base,["stats","G/A · SOG · HIT/BLK · PPP"],["act",""]];
  return [...base, ...SKSTATS.map(s=>[s,s]), ["act",""]];
}

function fmt(p,key){
  if(key==="rank") return p.rank;
  if(key==="val") return p.val.toFixed(2);
  if(key==="age") return p.age?p.age.toFixed(0):"";
  if(key==="pos") return `<span class="pos">${p.pos}</span>`;
  if(key==="name"){
    let b="";
    if(p.kept===MY) b=' <span class="badge b-my">KEEP</span>';
    else if(p.kept==="keep?") b=' <span class="badge b-maybe">KEEP?</span>';
    else if(p.kept) b=` <span class="badge b-other">${p.kept}</span>`;
    if(p.breakout) b+=' <span class="badge b-brk">BRK</span>';
    return `<span class="tier t${p.tier}"></span><span class="name">${p.name}</span>${b}`
      + (p.note?`<div class="pos" style="font-size:10px">${p.note}</div>`:"");
  }
  if(key==="stats"){
    const s=p.stats;
    if(p.type==="G") return "";
    return `${s.G|0}/${s.A|0} · ${s.SOG|0} · ${s.HIT|0}/${s.BLK|0} · ${s.PPP|0}`;
  }
  if(key==="act") return `<span class="act"><b class="claim" data-a="claim" title="claim to my roster">＋</b>`
    + `<b class="x" data-a="x" title="remove (drafted by other)">✗</b></span>`;
  if(["G","A","PIM","PPP","SOG","HIT","BLK"].includes(key)) return p.stats[key]|0;
  if(key==="SV%") return p.stats["SV%"]?p.stats["SV%"].toFixed(3):"";
  if(["starts","W","SHO"].includes(key)) return p.stats[key]?p.stats[key].toFixed(0):"";
  if(key==="GSAx") return p.stats["GSAx"]!=null?p.stats["GSAx"].toFixed(2):"";
  return p[key]!=null?p[key]:"";
}

function visible(){
  let list = PLAYERS.filter(p=>{
    if(pos==="G" && p.type!=="G") return false;
    if(pos!=="ALL" && pos!=="G" && !p.pos.split("/").includes(pos)) return false;
    if(q && !p.name.toLowerCase().includes(q)) return false;
    if(hideGone && state.gone[p.id]) return false;
    if(mineOnly && !state.mine[p.id]) return false;
    return true;
  });
  const k=sortKey;
  list.sort((a,b)=>{
    let av,bv;
    if(["rank","val","age","z","tier"].includes(k)){av=a[k];bv=b[k];}
    else if(a.stats && k in a.stats){av=a.stats[k]||0;bv=b.stats[k]||0;}
    else {av=(""+fmt(a,k)).toLowerCase();bv=(""+fmt(b,k)).toLowerCase();}
    return av<bv?-sortDir:av>bv?sortDir:0;
  });
  return list;
}

function renderHead(){
  const cols=colset();
  document.getElementById("head").innerHTML = cols.map(([k,l])=>{
    const cls=(k==="name"||k==="pos"||k==="stats")?"l":"";
    const arrow = sortKey===k?(sortDir>0?" ▲":" ▼"):"";
    return `<th class="${cls}" data-k="${k}">${l}${arrow}</th>`;
  }).join("");
}

function renderRows(){
  const cols=colset();
  const rows=visible().map(p=>{
    const cls=[state.gone[p.id]?"gone":"", state.mine[p.id]?"mine":""].join(" ");
    const tds=cols.map(([k])=>{
      const cl=(k==="name"||k==="pos"||k==="stats")?"l":"";
      const extra=k==="val"?" val":"";
      return `<td class="${cl}${extra}${k==="name"?" name":""}" data-k="${k}">${fmt(p,k)}</td>`;
    }).join("");
    return `<tr data-id="${p.id}" class="${cls}">${tds}</tr>`;
  }).join("");
  document.getElementById("rows").innerHTML=rows;
}

// ---- roster fill (multi-position eligibility, greedy most-open) ----
function computeRoster(){
  const need={...ROSTER}; delete need.BN;
  const slots={C:[],LW:[],RW:[],D:[],G:[],BN:[]};
  const mine=PLAYERS.filter(p=>state.mine[p.id]).sort((a,b)=>b.val-a.val);
  for(const p of mine){
    const elig=p.pos.split("/").filter(x=>need[x]!==undefined);
    let best=null,bestOpen=0;
    for(const pp of elig){const open=need[pp]-slots[pp].length; if(open>bestOpen){best=pp;bestOpen=open;}}
    if(best) slots[best].push(p); else slots.BN.push(p);
  }
  return slots;
}
function renderRoster(){
  const slots=computeRoster();
  const order=["C","LW","RW","D","G","BN"];
  document.getElementById("roster").innerHTML = order.map(pos=>{
    const cap=ROSTER[pos], filled=slots[pos];
    const chips=filled.map(p=>`<span class="chip ${p.kept===MY?'keep':''}">${p.name.split(" ").slice(-1)[0]}</span>`).join("");
    const rem=cap-filled.length;
    const status = rem>0?`<span class="need">${rem} need</span>`:`<span class="ok">✓</span>`;
    return `<div class="slot"><span class="lbl">${pos} <span style="color:var(--dim)">${filled.length}/${cap}</span> ${status}</span><span class="fill">${chips}</span></div>`;
  }).join("");
}

function renderGtrack(){
  const left={1:0,2:0,3:0,4:0,5:0}, tot={1:0,2:0,3:0,4:0,5:0};
  for(const p of PLAYERS){ if(p.type!=="G") continue; tot[p.tier]++; if(!state.gone[p.id]) left[p.tier]++; }
  const lbl={1:"Elite (z≥4)",2:"Starter (2.5+)",3:"Startable (1.5+)",4:"Streamer (0.7+)",5:"Deep"};
  document.getElementById("gtrack").innerHTML=[1,2,3,4,5].map(t=>
    `<div class="gt"><span>${lbl[t]}</span><span class="n" style="color:var(--t${t})">${left[t]}/${tot[t]}</span></div>`
  ).join("");
}

function renderIntel(){
  document.getElementById("banner").textContent="⚠ "+INTEL.headline;
  document.getElementById("intel").innerHTML = INTEL.teams.map(x=>
    `<div class="team"><div class="nm">${x.t} <span class="meta">${x.rec}</span></div>`
    +`<div class="meta"><span class="s">▲ ${x.strong}</span> · <span class="w">▼ ${x.soft}</span></div>`
    +`<div class="meta">${x.posture} · goalies ${x.gRound}</div>`
    +`<div class="meta" style="color:#b9c4d3">${x.note}</div></div>`
  ).join("");
}

function renderAll(){renderHead();renderRows();renderRoster();renderGtrack();}

// ---- events ----
document.getElementById("rows").addEventListener("click",e=>{
  const tr=e.target.closest("tr"); if(!tr) return;
  const id=+tr.dataset.id;
  const a=e.target.closest("b")?.dataset.a;
  if(a==="claim"){ toggleMine(id); }
  else if(a==="x"){ toggleGone(id,true); }
  else { toggleGone(id,false); }   // row click = drafted (any team)
});
function toggleGone(id,forceOther){
  if(state.gone[id]){ delete state.gone[id]; delete state.mine[id]; }
  else { state.gone[id]=1; if(forceOther) delete state.mine[id]; }
  commit();
}
function toggleMine(id){
  if(state.mine[id]){ delete state.mine[id]; delete state.gone[id]; }
  else { state.mine[id]=1; state.gone[id]=1; }
  commit();
}
function commit(){save();renderRows();renderRoster();renderGtrack();}

document.querySelectorAll(".tab").forEach(t=>t.addEventListener("click",()=>{
  document.querySelectorAll(".tab").forEach(x=>x.classList.remove("on"));
  t.classList.add("on"); pos=t.dataset.pos;
  sortKey= pos==="G"?"val":"rank"; sortDir= pos==="G"?-1:1;
  renderAll();
}));
document.getElementById("q").addEventListener("input",e=>{q=e.target.value.toLowerCase().trim();renderRows();});
document.getElementById("hideGone").addEventListener("change",e=>{hideGone=e.target.checked;renderRows();});
document.getElementById("mineOnly").addEventListener("change",e=>{mineOnly=e.target.checked;renderRows();});
document.getElementById("head").addEventListener("click",e=>{
  const k=e.target.closest("th")?.dataset.k; if(!k||k==="act") return;
  if(sortKey===k) sortDir*=-1; else {sortKey=k; sortDir=(k==="name"||k==="pos"||k==="team")?1:-1; if(k==="rank")sortDir=1;}
  renderHead();renderRows();
});
document.getElementById("reset").addEventListener("click",()=>{
  if(confirm("Reset the whole draft (keeps your keepers)?")){ state=seed(); save(); renderAll(); }
});

renderIntel();
renderAll();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
