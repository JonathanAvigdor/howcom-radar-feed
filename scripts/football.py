#!/usr/bin/env python3
"""Fetch upcoming AIK, Hammarby and Sweden (men + women) matches from API-Football.

Usage: FOOTBALL_KEY=... python3 football.py <out_file>
Writes a JSON list of events in the same shape as events.json. If the API refuses or fails,
it writes nothing and exits 0, so the daily job keeps using the matches in events.json.
Prints every API error so the GitHub Actions log shows what happened.
"""
import json, os, sys, urllib.request, urllib.parse, datetime

KEY = os.environ.get("FOOTBALL_KEY", "").strip()
OUT = sys.argv[1] if len(sys.argv) > 1 else "football_api.json"
BASE = "https://v3.football.api-sports.io/"
TZ = "Europe/Stockholm"
HORIZON_DAYS = 92

# name to search, country filter, national team?, crowd estimate for a Stockholm home game, audience
TEAMS = [
    dict(key="aik", search="AIK", country="Sweden", national=False, exact="AIK Stockholm", alt=["AIK"], crowd=22000,
         audience="18–55, football supporters"),
    dict(key="hammarby", search="Hammarby", country="Sweden", national=False, exact="Hammarby FF", alt=["Hammarby"], crowd=25000,
         audience="18–55, football supporters"),
    dict(key="sweden-men", search="Sweden", country=None, national=True, exact="Sweden", alt=[], crowd=35000,
         audience="All ages, national-team audience"),
    dict(key="sweden-women", search="Sweden", country=None, national=True, exact="Sweden W", alt=["Sweden Women"], crowd=18000,
         audience="All ages, families and national-team fans"),
]
STOCKHOLM_VENUES = {  # API venue name (lower case) -> radar venue key
    "strawberry arena": "strawberry", "friends arena": "strawberry", "nationalarenan": "strawberry",
    "3arena": "3arena", "tele2 arena": "3arena", "grimsta ip": "grimsta",
}
TV = {"Allsvenskan": "TV4 Play", "UEFA Nations League": "Viaplay"}
calls = 0

def get(path, **params):
    global calls
    calls += 1
    req = urllib.request.Request(BASE + path + "?" + urllib.parse.urlencode(params), headers={"x-apisports-key": KEY})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.load(r)
    if d.get("errors"):
        print(f"API error on {path} {params}: {d['errors']}")
    return d

def find_team(t):
    d = get("teams", search=t["search"])
    rows = [r["team"] for r in d.get("response", [])]
    def ok(tm):
        n = tm["name"]
        if bool(tm.get("national")) != t["national"]: return False
        if t["country"] and tm.get("country") != t["country"]: return False
        if n == t["exact"] or n in t["alt"]: return True
        if not t["national"]:  # club: name starts with the search word, skip women/youth/reserve sides
            return n.lower().startswith(t["search"].lower()) and not any(x in n for x in (" W", "U19", "U21", "U23", " II", " 2"))
        return False
    exact = [tm for tm in rows if tm["name"] == t["exact"] or tm["name"] in t["alt"]]
    pick = [tm for tm in (exact or rows) if ok(tm)]
    if pick:
        return pick[0]["id"], pick[0]["name"]
    print(f"Team not found: {t['exact']} (candidates: {[(tm['name'], tm.get('national')) for tm in rows][:12]})")
    return None, None

def main():
    if not KEY:
        print("FOOTBALL_KEY not set; skipping API-Football"); return
    today = datetime.date.today()
    horizon = today + datetime.timedelta(days=HORIZON_DAYS)
    out, seen = [], set()
    for t in TEAMS:
        tid, tname = find_team(t)
        if not tid: continue
        d = get("fixtures", team=tid, next=15, timezone=TZ)
        rows = d.get("response", [])
        print(f"{tname} (id {tid}): {len(rows)} upcoming fixtures")
        for f in rows:
            fx, lg, tm = f["fixture"], f["league"], f["teams"]
            if fx["id"] in seen: continue
            seen.add(fx["id"])
            start = fx["date"]  # local time because of timezone=Europe/Stockholm
            date, time = start[:10], start[11:16]
            if datetime.date.fromisoformat(date) > horizon: continue
            home = tm["home"]["id"] == tid
            venue = (fx.get("venue") or {}).get("name") or ""
            city = (fx.get("venue") or {}).get("city") or ""
            vkey = STOCKHOLM_VENUES.get(venue.lower(), "")
            tbd = (fx.get("status") or {}).get("short") == "TBD"
            ev = dict(id=f"api-{fx['id']}", title=f"{tm['home']['name']} – {tm['away']['name']} ({lg['name']})",
                      date=date, time=None if tbd else time, category="football", team=t["key"], comp=lg["name"],
                      tv=TV.get(lg["name"]), away=not home, audience=t["audience"], audienceGroup="Adults 30–55",
                      source="api-football", link=None, endDate=None, ooh=None)
            if home:
                ev.update(venueKey=vkey, venueName="" if vkey else (venue or "Stockholm"), crowd=t["crowd"],
                          notes="Crowd is a typical-attendance estimate." + (" Kick-off time not set yet." if tbd else ""))
            else:
                ev.update(venueKey="", venueName="Away: " + (city or tm["home"]["name"]), crowd=0,
                          notes="Away game. Stockholm fans watch on TV: sports bars and homes.")
            out.append(ev)
    print(f"API-Football: {len(out)} matches kept, {calls} requests used")
    if out:
        json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=1)
    else:
        print("No matches from API-Football; the job will use events.json instead")

if __name__ == "__main__":
    try:
        main()
    except Exception as ex:  # never break the daily job
        print("API-Football failed:", ex)
