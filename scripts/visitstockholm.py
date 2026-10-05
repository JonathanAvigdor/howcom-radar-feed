#!/usr/bin/env python3
"""Fetch this week's events from the Visit Stockholm open API (no key needed).

Usage: python3 visitstockholm.py <out_file> [sample.json]
API: https://api.visitstockholm.com/api/public-v1/events/?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD&page=N
Data: Stockholm Business Region AB, CC BY 4.0 (credit shown on the screen).
Writes a JSON list in the same shape as events.json. Never breaks the daily job.
"""
import json, sys, re, datetime, urllib.request, urllib.parse

OUT = sys.argv[1] if len(sys.argv) > 1 else "visitstockholm.json"
SAMPLE = sys.argv[2] if len(sys.argv) > 2 else None
BASE = "https://api.visitstockholm.com/api/public-v1/events/"
DAYS = 7          # same window as the screen
MAX_SPAN = 4      # skip long-running exhibitions and tours: keep events lasting at most 4 days
MAX_PAGES = 40    # 16 events per page

# venue name on Visit Stockholm (lower case, start of name) -> (radar venue key, venue name, capacity)
VENUES = [
    ("strawberry arena", "strawberry", "Strawberry Arena", 50000), ("3arena", "3arena", "3Arena", 30000),
    ("avicii arena", "avicii", "Avicii Arena", 16000), ("hovet", "hovet", "Hovet", 8500),
    ("annexet", "annexet", "Annexet", 3000), ("fållan", "fallan", "Fållan", 3000),
    ("stockholm waterfront", "waterfront", "Stockholm Waterfront", 3000),
    ("filadelfia", "filadelfia", "Filadelfia Convention Center", 2500),
    ("stockholmsmässan", "stockholmsmassan", "Stockholmsmässan", 10000), ("kistamässan", "kistamassan", "Kistamässan", 5000),
    ("cirkus", "cirkus", "Cirkus", 1650), ("göta lejon", "gotalejon", "Göta Lejon", 1250), ("berns", "berns", "Berns", 1200),
    ("debaser strand", "debaser", "Debaser Strand", 1000), ("fryshuset", "fryshuset", "Fryshuset", 2000),
    ("rival", "rival", "Rival", 700), ("münchenbryggeriet", "munchen", "Münchenbryggeriet", 1500),
]
# category -> (audience, audience group, crowd guess when the venue is unknown)
CATS = {
    "festivals": ("Mixed, festival audience", "Young adults 20–39", 2000),
    "fairs": ("30–60, fair visitors", "Adults 30–55", 3000),
    "sports": ("Mixed, sports fans", "Adults 30–55", 2000),
    "music": ("Mixed, live music fans", "Young adults 20–39", 300),
    "stage-film": ("25–60, culture audience", "Adults 30–55", 300),
    "family": ("Families with children", "Families", 300),
    "clubs-parties": ("20–35, nightlife", "Young adults 20–39", 300),
    "eat-drink": ("25–55, food and drink", "Adults 30–55", 300),
    "exhibitions": ("Mixed, culture audience", "Adults 30–55", 300),
    "networking-community": ("Adults, professionals", "Adults 30–55", 200),
    "science-tech": ("Adults, tech and science", "Adults 30–55", 200),
    "careers-leadership": ("Adults, professionals", "Adults 30–55", 200),
    "christmas-new-years-eve": ("Families and all ages", "Families", 500),
}
SKIP = {"guided-tours"}  # tours repeat daily and aren't crowd events

def fetch_pages(dfrom, dto):
    if SAMPLE:
        return json.load(open(SAMPLE))["results"]
    rows, page = [], 1
    while page and page <= MAX_PAGES:
        q = urllib.parse.urlencode({"date_from": dfrom, "date_to": dto, "page": page})
        req = urllib.request.Request(BASE + "?" + q, headers={"User-Agent": "howcom-radar-feed/1.0", "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.load(r)
        rows += d.get("results", [])
        page = d.get("next")
    return rows

def norm(s):
    return re.sub(r"[^a-z0-9åäö]", "", (s or "").lower())

def main():
    today = datetime.date.today()
    dto = today + datetime.timedelta(days=DAYS - 1)
    rows = fetch_pages(today.isoformat(), dto.isoformat())
    out, seen, skipped = [], set(), 0
    for e in rows:
        title = (e.get("title") or {}).get("en") or (e.get("title") or {}).get("sv") or ""
        try:
            sd = datetime.date.fromisoformat(e["start_date"]); ed = datetime.date.fromisoformat(e.get("end_date") or e["start_date"])
        except Exception:
            continue
        slugs = [c.get("slug") for c in (e.get("categories") or [])]
        if not title or (ed - sd).days > MAX_SPAN or (slugs and all(s in SKIP for s in slugs)):
            skipped += 1; continue
        key = (norm(title)[:24], e["start_date"])
        if key in seen: continue
        seen.add(key)
        vname = (e.get("venue_name") or "").strip()
        venue = next((v for v in VENUES if vname.lower().startswith(v[0])), None)
        cat = next((s for s in slugs if s in CATS), None)
        aud, grp, guess = CATS.get(cat, ("Mixed audience", "Adults 30–55", 300))
        t = (e.get("start_time") or "")[:5] or None
        out.append(dict(
            id="vs-" + str(e["id"]), title=title.strip(), date=max(sd, today).isoformat(),
            endDate=ed.isoformat() if ed > sd else None, time=t,
            venueKey=venue[1] if venue else "", venueName=venue[2] if venue else (vname or "Stockholm"),
            area=e.get("closest_station") and ("Near " + e["closest_station"]) or (e.get("city") or ""),
            crowd=venue[3] if venue else guess, audience=aud, audienceGroup=grp,
            category="visitstockholm", vsCategory=cat, source="visitstockholm",
            link="https://www.visitstockholm.com/events/" + (e.get("url") or "") + "/" if e.get("url") else None,
            ooh=None, notes="From Visit Stockholm (CC BY 4.0). Crowd is venue capacity or a rough estimate."))
    json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=1)
    print(f"Visit Stockholm: {len(rows)} listings, {len(out)} kept, {skipped} long-running or tours skipped")

if __name__ == "__main__":
    try:
        main()
    except Exception as ex:
        print("Visit Stockholm failed:", ex)
