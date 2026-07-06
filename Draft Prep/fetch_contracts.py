#!/usr/bin/env python3
"""
Contract fetcher — CapWages team pages (plain HTTP, __NEXT_DATA__ JSON).

Purpose: the "team-conviction" signal. NHL front offices sign post-ELC
players to big AAV/term based on private development data (LaCombe signed
$9M x long term BEFORE his breakout). A big bet on an age<=25 player is
foreshadowing the model's rate-detector can't see.

Output: data/contracts.csv (name, team, pos, dob, aav, years_left, type, expiry)
Usage: python fetch_contracts.py
"""
import csv, json, re, time, urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def get(url):
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", errors="replace")

def next_data(html):
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.S)
    return json.loads(m.group(1)) if m else None

def team_slugs():
    html = get("https://capwages.com")     # /teams index 404s; home lists all 32
    slugs = sorted(set(re.findall(r'/teams/([a-z_]+)', html)))
    return [s for s in slugs if "_" in s]

def money(s):
    try:
        return int(re.sub(r"[^\d]", "", str(s)) or 0)
    except ValueError:
        return 0

def parse_team(slug):
    d = next_data(get(f"https://capwages.com/teams/{slug}"))
    roster = d["props"]["pageProps"]["data"].get("roster", {})
    rows = []
    for group in roster.values():
        if not isinstance(group, list):
            continue
        for p in group:
            contracts = p.get("contracts") or []
            if not contracts:
                continue
            cur = contracts[0]
            details = cur.get("details") or []
            aav = max((money(x.get("aav")) for x in details), default=0)
            rows.append({
                "name": p.get("name", ""),
                "team": slug,
                "pos": p.get("pos", ""),
                "dob": p.get("born", ""),
                "aav": aav,
                "years_left": len(details),
                "type": cur.get("type", ""),
                "expiry": cur.get("expiryStatus", ""),
            })
    return rows

if __name__ == "__main__":
    slugs = team_slugs()
    print(f"{len(slugs)} teams")
    all_rows = []
    for s in slugs:
        try:
            rows = parse_team(s)
            all_rows.extend(rows)
            print(f"{s}: {len(rows)}")
        except Exception as e:
            print(f"{s}: FAILED ({e})")
        time.sleep(0.5)
    with open("data/contracts.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["name","team","pos","dob","aav","years_left","type","expiry"])
        w.writeheader()
        w.writerows(all_rows)
    print(f"data/contracts.csv: {len(all_rows)} contracts")
