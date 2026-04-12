"""Generate draft board outputs: CSV and interactive HTML."""

from __future__ import annotations

import pandas as pd

from fantasy_hockey.config import OUTPUTS_DIR, TARGET_SEASON, season_id_to_label, MY_TEAM_NAME


def _output_path(filename: str) -> str:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    return str(OUTPUTS_DIR / filename)


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------

# Columns and their display-friendly names for the CSV/HTML output.
SKATER_DISPLAY_COLS: dict[str, str] = {
    "rank": "Rank",
    "tier": "Tier",
    "name": "Player",
    "position_code": "Pos",
    "team_abbrevs": "Team",
    "projected_gp": "GP",
    "goals": "G",
    "assists": "A",
    "pim": "PIM",
    "ppp": "PPP",
    "sog": "SOG",
    "hits": "HIT",
    "blocks": "BLK",
    "z_G": "zG",
    "z_A": "zA",
    "z_PIM": "zPIM",
    "z_PPP": "zPPP",
    "z_SOG": "zSOG",
    "z_HIT": "zHIT",
    "z_BLK": "zBLK",
    "adjusted_value": "Value",
    "position_rank_label": "PosRank",
    "keeper_eligible": "KeepOK",
    "draft_round": "DraftRd",
    "keeper_round": "KeepRd",
    "keeper_surplus": "KeepSurplus",
}

GOALIE_DISPLAY_COLS: dict[str, str] = {
    "rank": "Rank",
    "tier": "Tier",
    "name": "Player",
    "position_code": "Pos",
    "team_abbrevs": "Team",
    "projected_gp": "GS",
    "wins": "W",
    "save_pct": "SV%",
    "shutouts": "SHO",
    "z_W": "zW",
    "z_SVPCT": "zSV%",
    "z_SHO": "zSHO",
    "adjusted_value": "Value",
    "position_rank_label": "PosRank",
    "keeper_eligible": "KeepOK",
    "draft_round": "DraftRd",
    "keeper_round": "KeepRd",
    "keeper_surplus": "KeepSurplus",
}

UNIFIED_DISPLAY_COLS: dict[str, str] = {
    "rank": "Rank",
    "tier": "Tier",
    "name": "Player",
    "position_code": "Pos",
    "eligible_positions": "Elig",
    "team_abbrevs": "Team",
    "projected_gp": "GP/GS",
    "adjusted_value": "Value",
    "position_rank_label": "PosRank",
    "roster_team": "OwnedBy",
    "projected_kept": "ProjKept",
    "projected_kept_by": "KeptBy",
    "next_keeper_round": "KeepCost",
    "keeper_eligible_next": "KeepElig",
    "draft_round": "DraftRd",
    "keeper_surplus_next": "KeepSurplus",
}


def _select_and_rename(df: pd.DataFrame, col_map: dict[str, str]) -> pd.DataFrame:
    """Select columns that exist and rename them."""
    available = {k: v for k, v in col_map.items() if k in df.columns}
    return df[list(available.keys())].rename(columns=available)


def write_csv(
    skater_board: pd.DataFrame,
    goalie_board: pd.DataFrame,
    unified_board: pd.DataFrame,
) -> str:
    """Write a multi-sheet CSV (actually 3 separate CSVs)."""
    season_label = season_id_to_label(TARGET_SEASON)

    sk_path = _output_path(f"draft_board_skaters_{season_label}.csv")
    gk_path = _output_path(f"draft_board_goalies_{season_label}.csv")
    uni_path = _output_path(f"draft_board_overall_{season_label}.csv")

    _select_and_rename(skater_board, SKATER_DISPLAY_COLS).to_csv(sk_path, index=False)
    _select_and_rename(goalie_board, GOALIE_DISPLAY_COLS).to_csv(gk_path, index=False)
    _select_and_rename(unified_board, UNIFIED_DISPLAY_COLS).to_csv(uni_path, index=False)

    return uni_path


# ---------------------------------------------------------------------------
# HTML (interactive via plotly/pandas styling)
# ---------------------------------------------------------------------------

def write_html(
    skater_board: pd.DataFrame,
    goalie_board: pd.DataFrame,
    unified_board: pd.DataFrame,
    sleeper_data: tuple | None = None,
) -> str:
    """Write interactive HTML dashboard with search, sort, tier colors, and charts."""
    season_label = season_id_to_label(TARGET_SEASON)
    path = _output_path(f"draft_board_{season_label}.html")

    sk_df = _select_and_rename(skater_board.head(250), SKATER_DISPLAY_COLS)
    gk_df = _select_and_rename(goalie_board.head(50), GOALIE_DISPLAY_COLS)
    uni_df = _select_and_rename(unified_board.head(300), UNIFIED_DISPLAY_COLS)

    # Tag rows owned by the user's team
    my_name_lower = MY_TEAM_NAME.lower()
    for df in (uni_df,):
        if "OwnedBy" in df.columns:
            df["MyTeam"] = df["OwnedBy"].fillna("").str.lower().str.strip() == my_name_lower
        if "KeptBy" in df.columns:
            df["MyKeeper"] = df["KeptBy"].fillna("").str.lower().str.strip() == my_name_lower

    sk_json = sk_df.to_json(orient="records")
    gk_json = gk_df.to_json(orient="records")
    uni_json = uni_df.to_json(orient="records")

    # Sleeper/reach data
    sleeper_json = "[]"
    reach_json = "[]"
    if sleeper_data:
        sleepers, reaches, _ = sleeper_data
        if not sleepers.empty:
            sleeper_json = sleepers.to_json(orient="records")
        if not reaches.empty:
            reach_json = reaches.to_json(orient="records")

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Fantasy Hockey Draft Board - {season_label}</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
         margin: 0; padding: 1.5em; background: #f0f2f5; color: #1a1a2e; }}
  h1 {{ margin: 0 0 0.3em; font-size: 1.6em; }}
  .subtitle {{ color: #666; margin-bottom: 1.5em; font-size: 0.9em; }}
  .controls {{ display: flex; gap: 12px; align-items: center; flex-wrap: wrap; margin-bottom: 1em; }}
  .search-box {{ padding: 8px 14px; font-size: 0.9em; border: 1px solid #ccc; border-radius: 6px;
                 width: 260px; outline: none; }}
  .search-box:focus {{ border-color: #1a1a2e; box-shadow: 0 0 0 2px rgba(26,26,46,0.15); }}
  .filter-btn {{ padding: 6px 14px; border: 1px solid #ccc; background: white; border-radius: 16px;
                 cursor: pointer; font-size: 0.82em; transition: all 0.15s; }}
  .filter-btn:hover {{ border-color: #1a1a2e; }}
  .filter-btn.active {{ background: #1a1a2e; color: white; border-color: #1a1a2e; }}
  .tab-container {{ display: flex; gap: 4px; margin-bottom: 0; }}
  .tab-btn {{ padding: 10px 22px; cursor: pointer; border: none;
              background: #ddd; font-size: 0.95em; border-radius: 6px 6px 0 0;
              transition: background 0.15s; }}
  .tab-btn:hover {{ background: #ccc; }}
  .tab-btn.active {{ background: #1a1a2e; color: white; }}
  .tab-content {{ display: none; }}
  .tab-content.active {{ display: block; }}
  .table-wrap {{ overflow-x: auto; max-height: 75vh; overflow-y: auto;
                 background: white; border-radius: 0 6px 6px 6px;
                 box-shadow: 0 1px 4px rgba(0,0,0,0.1); }}
  table {{ border-collapse: collapse; width: 100%; font-size: 0.82em; }}
  th {{ background: #1a1a2e; color: white; padding: 8px 10px; text-align: left;
        position: sticky; top: 0; cursor: pointer; white-space: nowrap;
        user-select: none; z-index: 2; }}
  th:hover {{ background: #2a2a4e; }}
  th .sort-arrow {{ margin-left: 4px; font-size: 0.7em; }}
  td {{ padding: 6px 10px; border-bottom: 1px solid #eee; white-space: nowrap; }}
  tr:hover {{ background: #e8f4fd !important; }}
  /* Tier color bands */
  tr.tier-1 {{ background: #fff3cd; }}
  tr.tier-2 {{ background: #ffeaa7; }}
  tr.tier-3 {{ background: #dfe6e9; }}
  tr.tier-4 {{ background: #f8f9fa; }}
  tr.tier-5 {{ background: white; }}
  tr.tier-1:hover, tr.tier-2:hover, tr.tier-3:hover {{ background: #e8f4fd !important; }}
  /* Keeper highlight */
  td.keeper-yes {{ background: #d4edda; font-weight: 600; }}
  td.keeper-surplus-high {{ background: #c3e6cb; font-weight: 700; }}
  tr.kept-row {{ opacity: 0.55; }}
  tr.kept-row td:first-child {{ border-left: 4px solid #dc3545; }}
  tr.my-team-row {{ background: #e3f2fd !important; }}
  tr.my-team-row:hover {{ background: #bbdefb !important; }}
  tr.my-keeper-row {{ background: #c8e6c9 !important; opacity: 1 !important; }}
  tr.my-keeper-row td:first-child {{ border-left: 4px solid #2e7d32; }}
  tr.my-keeper-row:hover {{ background: #a5d6a7 !important; }}
  td.kept-cell {{ color: #dc3545; font-weight: 600; font-size: 0.78em; }}
  td.my-kept-cell {{ color: #2e7d32; font-weight: 600; font-size: 0.78em; }}
  /* Position badges */
  .pos {{ display: inline-block; padding: 2px 6px; border-radius: 3px; font-size: 0.8em;
           font-weight: 600; }}
  .pos-C {{ background: #e3f2fd; color: #1565c0; }}
  .pos-L, .pos-LW {{ background: #e8f5e9; color: #2e7d32; }}
  .pos-R, .pos-RW {{ background: #fce4ec; color: #c62828; }}
  .pos-D {{ background: #f3e5f5; color: #6a1b9a; }}
  .pos-G {{ background: #fff3e0; color: #e65100; }}
  .count-badge {{ background: #1a1a2e; color: white; padding: 2px 8px; border-radius: 10px;
                  font-size: 0.8em; margin-left: 6px; }}
  /* Sleeper/Reach section */
  .insight-cards {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1em; margin-bottom: 1.5em; }}
  .insight-card {{ background: white; border-radius: 8px; padding: 1em;
                   box-shadow: 0 1px 4px rgba(0,0,0,0.1); }}
  .insight-card h3 {{ margin: 0 0 0.5em; font-size: 1em; }}
  .insight-card.sleepers h3 {{ color: #2e7d32; }}
  .insight-card.reaches h3 {{ color: #c62828; }}
  .insight-list {{ list-style: none; padding: 0; margin: 0; font-size: 0.85em; }}
  .insight-list li {{ padding: 4px 0; border-bottom: 1px solid #f0f0f0; display: flex;
                      justify-content: space-between; }}
  .insight-list li:last-child {{ border: none; }}
  .delta-pos {{ color: #2e7d32; font-weight: 600; }}
  .delta-neg {{ color: #c62828; font-weight: 600; }}
</style>
</head>
<body>

<h1>Fantasy Hockey Draft Board &mdash; {season_label}</h1>
<p class="subtitle">Marcel-style projections | 3-year weighted baseline | Age curves | Keeper analysis</p>

<div id="insights" class="insight-cards"></div>

<div class="controls">
  <input type="text" class="search-box" id="searchBox" placeholder="Search player or team..." oninput="filterTable()">
  <button class="filter-btn active" data-pos="ALL" onclick="filterPos(this)">All</button>
  <button class="filter-btn" data-pos="C" onclick="filterPos(this)">C</button>
  <button class="filter-btn" data-pos="L" onclick="filterPos(this)">LW</button>
  <button class="filter-btn" data-pos="R" onclick="filterPos(this)">RW</button>
  <button class="filter-btn" data-pos="D" onclick="filterPos(this)">D</button>
  <button class="filter-btn" data-pos="G" onclick="filterPos(this)">G</button>
  <label style="font-size:0.85em; margin-left:12px; cursor:pointer;">
    <input type="checkbox" id="hideKept" onchange="filterTable()"> Hide kept players
  </label>
  <span id="rowCount" class="count-badge"></span>
</div>
<div style="font-size:0.8em; color:#666; margin-bottom:0.8em; display:flex; gap:18px; align-items:center;">
  <span><span style="display:inline-block;width:12px;height:12px;background:#c8e6c9;border-left:3px solid #2e7d32;margin-right:4px;"></span>Your keeper candidates</span>
  <span><span style="display:inline-block;width:12px;height:12px;background:#e3f2fd;margin-right:4px;"></span>Your roster</span>
  <span><span style="display:inline-block;width:12px;height:12px;background:#eee;opacity:0.55;border-left:3px solid #dc3545;margin-right:4px;"></span>Opponent projected keeper (off the board)</span>
</div>

<div class="tab-container">
  <button class="tab-btn active" onclick="showTab('overall',this)">Overall</button>
  <button class="tab-btn" onclick="showTab('skaters',this)">Skaters</button>
  <button class="tab-btn" onclick="showTab('goalies',this)">Goalies</button>
</div>

<div id="overall" class="tab-content active"><div class="table-wrap"><table id="tbl-overall"></table></div></div>
<div id="skaters" class="tab-content"><div class="table-wrap"><table id="tbl-skaters"></table></div></div>
<div id="goalies" class="tab-content"><div class="table-wrap"><table id="tbl-goalies"></table></div></div>

<script>
const DATA = {{
  overall: {uni_json},
  skaters: {sk_json},
  goalies: {gk_json},
}};
const SLEEPERS = {sleeper_json};
const REACHES = {reach_json};

let currentTab = 'overall';
let currentPos = 'ALL';
let sortCol = null;
let sortAsc = true;

function showTab(name, btn) {{
  currentTab = name;
  document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
  document.getElementById(name).classList.add('active');
  if(btn) btn.classList.add('active');
  sortCol = null;
  renderTable();
}}

function filterPos(btn) {{
  currentPos = btn.dataset.pos;
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  renderTable();
}}

function filterTable() {{ renderTable(); }}

function getFilteredData() {{
  let data = [...DATA[currentTab]];
  const q = document.getElementById('searchBox').value.toLowerCase();
  if (q) {{
    data = data.filter(r => {{
      const vals = Object.values(r).join(' ').toLowerCase();
      return vals.includes(q);
    }});
  }}
  if (currentPos !== 'ALL') {{
    const posCol = Object.keys(data[0] || {{}}).find(k => k === 'Pos');
    if (posCol) data = data.filter(r => r[posCol] === currentPos);
  }}
  if (document.getElementById('hideKept') && document.getElementById('hideKept').checked) {{
    data = data.filter(r => !r['ProjKept'] || r['MyKeeper']);
  }}
  if (sortCol !== null) {{
    data.sort((a, b) => {{
      let va = a[sortCol], vb = b[sortCol];
      if (va == null) return 1; if (vb == null) return -1;
      if (typeof va === 'string' && typeof vb === 'string') return sortAsc ? va.localeCompare(vb) : vb.localeCompare(va);
      return sortAsc ? va - vb : vb - va;
    }});
  }}
  return data;
}}

function renderTable() {{
  const data = getFilteredData();
  const tbl = document.getElementById('tbl-' + currentTab);
  if (!data.length) {{ tbl.innerHTML = '<tr><td>No results</td></tr>'; return; }}
  const cols = Object.keys(data[0]);
  let html = '<thead><tr>';
  cols.forEach((c, i) => {{
    const arrow = sortCol === c ? (sortAsc ? ' &#9650;' : ' &#9660;') : '';
    html += `<th onclick="sortBy('${{c}}')">${{c}}<span class="sort-arrow">${{arrow}}</span></th>`;
  }});
  html += '</tr></thead><tbody>';
  data.forEach(row => {{
    const tier = row['Tier'] || 99;
    const tierClass = tier <= 5 ? `tier-${{tier}}` : '';
    const isMyKeeper = row['MyKeeper'] === true;
    const isMyTeam = row['MyTeam'] === true;
    const isOppKept = (row['ProjKept'] === true) && !isMyKeeper;
    let rowClass = tierClass;
    if (isMyKeeper) rowClass += ' my-keeper-row';
    else if (isOppKept) rowClass += ' kept-row';
    else if (isMyTeam) rowClass += ' my-team-row';
    html += `<tr class="${{rowClass}}">`;
    cols.forEach(c => {{
      let v = row[c];
      let cls = '';
      if (c === 'Pos' && v) cls = `pos pos-${{v}}`;
      if (c === 'KeepElig' && v === true) cls = 'keeper-yes';
      if (c === 'KeepSurplus' && v > 50) cls = 'keeper-surplus-high';
      if (c === 'KeptBy' && v && v !== '-' && v !== null) cls = row['MyKeeper'] ? 'my-kept-cell' : 'kept-cell';
      if (v == null || v === '') v = '-';
      else if (typeof v === 'number') v = Number.isInteger(v) ? v : v.toFixed(2);
      if (c === 'Pos' && v !== '-') v = `<span class="${{cls}}">${{v}}</span>`;
      else if (cls) html += `<td class="${{cls}}">${{v}}</td>`;
      if (c !== 'Pos' && !cls) html += `<td>${{v}}</td>`;
      else if (c === 'Pos') html += `<td>${{v}}</td>`;
    }});
    html += '</tr>';
  }});
  html += '</tbody>';
  tbl.innerHTML = html;
  document.getElementById('rowCount').textContent = data.length + ' players';
}}

function sortBy(col) {{
  if (sortCol === col) sortAsc = !sortAsc;
  else {{ sortCol = col; sortAsc = true; }}
  renderTable();
}}

// Render sleeper/reach insight cards
function renderInsights() {{
  const container = document.getElementById('insights');
  if (!SLEEPERS.length && !REACHES.length) {{ container.style.display = 'none'; return; }}
  let html = '';
  if (SLEEPERS.length) {{
    html += '<div class="insight-card sleepers"><h3>Sleepers (Drafted Late, We Rank High)</h3><ul class="insight-list">';
    SLEEPERS.slice(0, 10).forEach(s => {{
      const delta = s.rank_delta ? '+' + Math.round(s.rank_delta) : '';
      html += `<li><span>${{s.name}} (${{s.position_code}}) &mdash; Rd ${{s.draft_round}}</span><span class="delta-pos">${{delta}}</span></li>`;
    }});
    html += '</ul></div>';
  }}
  if (REACHES.length) {{
    html += '<div class="insight-card reaches"><h3>Reaches (Drafted Early, We Rank Low)</h3><ul class="insight-list">';
    REACHES.slice(0, 10).forEach(s => {{
      const delta = s.rank_delta ? Math.round(s.rank_delta) : '';
      html += `<li><span>${{s.name}} (${{s.position_code}}) &mdash; Rd ${{s.draft_round}}</span><span class="delta-neg">${{delta}}</span></li>`;
    }});
    html += '</ul></div>';
  }}
  container.innerHTML = html;
}}

renderInsights();
renderTable();
</script>
</body>
</html>"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path
