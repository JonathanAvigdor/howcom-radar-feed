#!/usr/bin/env python3
"""Build today.json for the HowCom office screen (Bauer DOOH, 1080x1920).

Usage: python3 build_feed.py <data_dir> <out_file>
<data_dir> holds the radar's database documents as JSON files:
  tm_YYYY-MM.json          Ticketmaster month docs   (or tm/YYYY-MM.json)
  weather.json             feeds/weather             (or feeds/weather.json)
  venue_<key>.json         venue table               (or venues/<key>.json)
  events_manual/<id>.json  team + researched events
Output is a small JSON file (~2 KB): the week's biggest events and a 6-day forecast.
"""
import json, sys, os, glob, datetime
from zoneinfo import ZoneInfo

src, out = sys.argv[1], sys.argv[2]
tz = ZoneInfo("Europe/Stockholm")
now = datetime.datetime.now(tz)
today = now.date()
end = today + datetime.timedelta(days=6)

def load(pattern):
    return [json.load(open(p)) for p in sorted(glob.glob(os.path.join(src, pattern)))]
def unwrap(d):  # ArtifactData dumps may wrap the body as {"data": {...}}
    return d["data"] if isinstance(d, dict) and "data" in d and isinstance(d["data"], dict) and len(d) <= 4 else d

venues = {}
for v in load("venue_*.json") + load("venues/*.json"):
    v = unwrap(v); venues[v["key"]] = v

events = []
for m in load("tm_*.json") + load("tm/*.json"):
    for e in unwrap(m).get("events", []):
        events.append(dict(date=e["date"], time=e.get("time"), title=e["name"], venue=e["venueName"],
                           area=e.get("area", ""), crowd=e.get("crowd") or 0, audience=e.get("audience", ""), kind="tm"))
manual = [unwrap(json.load(open(p))) for p in sorted(glob.glob(os.path.join(src, "events_manual", "*.json")))]
if os.path.exists(os.path.join(src, "events.json")):
    manual += json.load(open(os.path.join(src, "events.json")))
for e in manual:
    v = venues.get(e.get("venueKey") or "", {})
    crowd = e.get("crowd")
    if crowd is None: crowd = v.get("capacity", 0)
    events.append(dict(date=e["date"], endDate=e.get("endDate"), time=e.get("time"), title=e["title"],
                       venue=v.get("name") or e.get("venueName") or "Stockholm", area=v.get("area") or e.get("area", ""),
                       crowd=crowd or 0, audience=e.get("audience", ""), kind="team" if e.get("source") == "team" else "curated"))

def in_week(e):
    d = datetime.date.fromisoformat(e["date"])
    last = datetime.date.fromisoformat(e.get("endDate") or e["date"])
    return last >= today and d <= end

week = [e for e in events if in_week(e)]
# one row per show: collapse repeat nights of the same title at the same venue
groups = {}
for e in week:
    k = (e["title"].lower(), e["venue"].lower())
    g = groups.setdefault(k, dict(e, nights=0))
    g["nights"] += 1
    if (e["date"], e.get("time") or "99") < (g["date"], g.get("time") or "99"):
        g.update(date=e["date"], time=e.get("time"))
venue_rows = sorted([g for g in groups.values() if g["crowd"]], key=lambda g: (-g["crowd"], g["date"]))
city_rows = sorted([g for g in groups.values() if not g["crowd"]], key=lambda g: g["date"])
top = venue_rows[:6 - min(1, len(city_rows))] + city_rows[:1]
top.sort(key=lambda g: (max(g["date"], today.isoformat()), g.get("time") or "99"))

def row(g):
    r = dict(date=max(g["date"], today.isoformat()), time=g.get("time"), title=g["title"][:70], venue=g["venue"],
             area=g["area"], crowd=g["crowd"], audience=g["audience"][:48])
    if g.get("endDate"): r["until"] = g["endDate"]
    if g["nights"] > 1: r["nights"] = g["nights"]
    return r

wx = {}
for w in load("weather.json") + load("feeds/weather.json"):
    wx = unwrap(w)
days = [dict(date=d["date"], code=d.get("code"), tmax=round(d["tmax"]), tmin=round(d["tmin"]),
             precip=round(d.get("precip") or 0, 1), pop=d.get("pop"), wind=round(d.get("wind") or 0))
        for d in wx.get("days", []) if d["date"] >= today.isoformat() and d.get("tmax") is not None and d.get("tmin") is not None][:6]

feed = dict(v=1, generatedAt=now.isoformat(timespec="minutes"), weekStart=today.isoformat(), weekEnd=end.isoformat(),
            eventsInWeek=len(groups), events=[row(g) for g in top], weather=days,
            normals=wx.get("normals", {}))
os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
json.dump(feed, open(out, "w"), ensure_ascii=False, separators=(",", ":"))
print(f"{out}: {os.path.getsize(out)} bytes, {len(feed['events'])} events, {len(days)} weather days")
