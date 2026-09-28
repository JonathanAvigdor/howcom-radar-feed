#!/usr/bin/env python3
"""Stockholm OOH Radar refresh.
Usage: python3 refresh.py <TICKETMASTER_KEY>
Fetches ~92 days of Ticketmaster events within 30 km of Stockholm plus a 16-day Open-Meteo forecast,
enriches them with the venue table below, and writes database documents to ./db plus ./batch.json
(ArtifactData batch entries for collections tm/<YYYY-MM> and feeds/weather, feeds/meta)."""
import json, time, urllib.request, urllib.parse, sys, os, datetime
KEY = sys.argv[1]
_t = datetime.datetime.now(datetime.timezone.utc)
start = _t.strftime("%Y-%m-%dT00:00:00Z"); end = (_t + datetime.timedelta(days=93)).strftime("%Y-%m-%dT23:59:59Z")
out=[]; page=0
while True:
    q=dict(apikey=KEY,countryCode="SE",latlong="59.3293,18.0686",radius="30",unit="km",size="199",page=str(page),sort="date,asc",startDateTime=start,endDateTime=end,locale="*")
    d=json.load(urllib.request.urlopen("https://app.ticketmaster.com/discovery/v2/events.json?"+urllib.parse.urlencode(q),timeout=30))
    out+=d.get("_embedded",{}).get("events",[]); tp=d["page"]["totalPages"]; page+=1
    if page>=tp or page*199>=1000: break
    time.sleep(0.3)
json.dump(out,open("tm_raw.json","w")); print("fetched", len(out))
wxu="https://api.open-meteo.com/v1/forecast?latitude=59.33&longitude=18.07&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,wind_speed_10m_max&timezone=Europe%2FStockholm&forecast_days=16"
for i in range(4):
    try: open("wx.json","wb").write(urllib.request.urlopen(wxu,timeout=30).read()); break
    except Exception as ex: print("weather retry", ex); time.sleep(10)
import re, collections
TODAY = datetime.date.today()
HORIZON = TODAY + datetime.timedelta(days=92)

VENUES = [
 dict(key="strawberry", name="Strawberry Arena", area="Solna · Arenastaden", lat=59.3727, lon=18.0003, capacity=50000,
      capNote="Football ~50,000; stadium concerts up to ~65,000", kind="stadium",
      ooh=["Solna station (pendeltåg + Tvärbanan)","Mall of Scandinavia","Arenastaden walkway","E4 / Uppsalavägen approach","T-Centralen (pendeltåg to Solna)"],
      tm=["Strawberry Arena","Friends Arena","Nationalarenan"]),
 dict(key="3arena", name="3Arena", area="Johanneshov · Globen area", lat=59.2903, lon=18.0845, capacity=30000,
      capNote="Football ~30,000; concerts up to ~40,000", kind="stadium",
      ooh=["Gullmarsplan hub (metro, Tvärbanan, buses)","Globen metro","Enskede gård (Tvärbanan)","Globen Shopping","Skanstull / Ringvägen"],
      tm=["3Arena","Tele2 Arena"]),
 dict(key="avicii", name="Avicii Arena", area="Johanneshov · Globen area", lat=59.2936, lon=18.0831, capacity=16000,
      capNote="Arena concerts ~16,000", kind="arena",
      ooh=["Globen metro","Gullmarsplan hub (metro, Tvärbanan, buses)","Globen Shopping","Skanstull / Ringvägen","Nynäsvägen approach"],
      tm=["Avicii Arena","Globen","Ericsson Globe"]),
 dict(key="hovet", name="Hovet", area="Johanneshov · Globen area", lat=59.2927, lon=18.0806, capacity=8500,
      capNote="Concerts/hockey ~8,000–9,000", kind="arena",
      ooh=["Gullmarsplan hub (metro, Tvärbanan, buses)","Globen metro","Globen Shopping","Skanstull / Ringvägen"],
      tm=["Hovet"]),
 dict(key="annexet", name="Annexet", area="Johanneshov · Globen area", lat=59.2941, lon=18.0812, capacity=3000,
      capNote="~3,000 standing", kind="hall",
      ooh=["Globen metro","Gullmarsplan hub","Globen Shopping"], tm=["Annexet"]),
 dict(key="fallan", name="Fållan", area="Johanneshov · Globen area", lat=59.2915, lon=18.0830, capacity=3000,
      capNote="Approx. ~3,000 standing", kind="hall",
      ooh=["Gullmarsplan hub","Globen metro","Globen Shopping"], tm=["Fållan"]),
 dict(key="waterfront", name="Stockholm Waterfront", area="Norrmalm · Central Station", lat=59.3322, lon=18.0530, capacity=3000,
      capNote="Main auditorium ~3,000", kind="hall",
      ooh=["Stockholm Central / T-Centralen","Cityterminalen","Arlanda Express platforms","Vasagatan"], tm=["Stockholm Waterfront"]),
 dict(key="filadelfia", name="Filadelfia Convention Center", area="Vasastan · S:t Eriksplan", lat=59.3406, lon=18.0371, capacity=2500,
      capNote="Approx. ~2,500 seated", kind="hall",
      ooh=["S:t Eriksplan metro","Odenplan (metro + pendeltåg)","Sankt Eriksgatan"], tm=["Filadelfia Convention Center"]),
 dict(key="stockholmsmassan", name="Stockholmsmässan", area="Älvsjö", lat=59.2790, lon=18.0100, capacity=10000,
      capNote="Fairs: roughly 5,000–30,000 visitors a day depending on event", kind="fair",
      ooh=["Älvsjö station (pendeltåg)","Älvsjö centrum","Götalandsvägen approach"], tm=["Stockholmsmässan"]),
 dict(key="kistamassan", name="Kistamässan", area="Kista", lat=59.4033, lon=17.9446, capacity=5000,
      capNote="Fairs: a few thousand visitors a day", kind="fair",
      ooh=["Kista metro","Kista Galleria","Kista Science Tower area"], tm=["Kistamässan"]),
 dict(key="cirkus", name="Cirkus", area="Djurgården", lat=59.3262, lon=18.0988, capacity=1650,
      capNote="~1,650 seated", kind="theatre",
      ooh=["Nybroplan (tram 7, boats)","Strandvägen","Djurgårdsbron / tram 7 stops"], tm=["Cirkus","Nya Cirkus"]),
 dict(key="gotalejon", name="Göta Lejon", area="Södermalm · Götgatan", lat=59.3138, lon=18.0730, capacity=1250,
      capNote="~1,250 seated", kind="theatre",
      ooh=["Medborgarplatsen metro","Skanstull metro","Götgatan retail strip","Ringen centrum"], tm=["Göta Lejon"]),
 dict(key="berns", name="Berns", area="Norrmalm · Berzelii park", lat=59.3317, lon=18.0737, capacity=1200,
      capNote="Approx. ~1,000–1,200", kind="club",
      ooh=["Kungsträdgården metro","Norrmalmstorg / Hamngatan","Nybroplan","Berzelii park"], tm=["Berns"]),
 dict(key="debaser", name="Debaser Strand", area="Södermalm · Hornstull", lat=59.3157, lon=18.0340, capacity=1000,
      capNote="Approx. ~1,000 standing", kind="club",
      ooh=["Hornstull metro","Hornsgatan","Långholmsgatan"], tm=["Debaser Strand","Debaser Nova"]),
 dict(key="fryshuset", name="Fryshuset", area="Johanneshov · Mårtensdal", lat=59.3036, lon=18.0955, capacity=2000,
      capNote="Approx. ~2,000", kind="hall",
      ooh=["Mårtensdal (Tvärbanan)","Gullmarsplan hub","Hammarby sjöstad"], tm=["Fryshuset"]),
 dict(key="rival", name="Rival", area="Södermalm · Mariatorget", lat=59.3170, lon=18.0620, capacity=700,
      capNote="~700 seated", kind="theatre",
      ooh=["Mariatorget metro","Hornsgatan","Slussen hub"], tm=["Rival"]),
 dict(key="munchen", name="Münchenbryggeriet", area="Södermalm · Söder Mälarstrand", lat=59.3195, lon=18.0555, capacity=1500,
      capNote="Approx. ~1,500 across halls", kind="hall",
      ooh=["Slussen hub","Mariatorget metro","Söder Mälarstrand"], tm=["Münchenbryggeriet","Münchenbryggeriet - Mälarsalen"]),
 dict(key="grimsta", name="Grimsta IP", area="Västerort · Råcksta", lat=59.3530, lon=17.8830, capacity=5000,
      capNote="Approx. ~5,000", kind="stadium",
      ooh=["Råcksta metro","Vällingby centrum","Johannelund / Hässelby strand line"], tm=[]),
 dict(key="city", name="Stockholm city (several venues)", area="City centre", lat=59.3326, lon=18.0649, capacity=0,
      capNote="Citywide", kind="city",
      ooh=["T-Centralen / Sergels torg","Drottninggatan","Hötorget","Östermalmstorg","Slussen hub"], tm=[]),
]
BY_TM = {}
for v in VENUES:
    for n in v["tm"]: BY_TM[n.lower()] = v["key"]
VK = {v["key"]: v for v in VENUES}

GENRE_AUD = {
 "Theatre": ("30–65, theatre audience","Adults 30–55"), "Spectacular": ("Families and 25–60","Families"),
 "Dance": ("25–60, culture audience","Adults 30–55"), "Comedy": ("25–45, comedy fans","Young adults 20–39"),
 "Rock": ("30–55, rock and pop","Adults 30–55"), "Hip-Hop/Rap": ("16–30, hip-hop","Youth 16–29"),
 "Dance/Electronic": ("20–35, club and electronic","Young adults 20–39"), "Classical": ("40+, classical","Mature 50+"),
 "Jazz": ("35+, jazz","Mature 50+"), "Holiday": ("Families and 40+, Christmas concerts","Families"),
 "Family": ("Families with children","Families"), "Children's Theatre": ("Families with children 3–12","Families"),
 "Food & Drink": ("25–55, food and drink","Adults 30–55"), "Fairs & Festivals": ("Mixed, fair visitors","Adults 30–55"),
 "Latin": ("25–55, Latin music","Adults 30–55"), "R&B": ("18–35, R&B","Young adults 20–39"),
 "Folk": ("35+, folk and Americana","Mature 50+"), "Alternative": ("20–35, alternative","Young adults 20–39"),
 "Opera": ("45+, opera","Mature 50+"), "Blues": ("45+, blues","Mature 50+"), "Soccer": ("25–55, football fans","Adults 30–55"),
 "World": ("30–60, world music","Adults 30–55"), "Magic & Illusion": ("Families and 25–50","Families"),
 "Multimedia": ("20–45 and families, film fans","Young adults 20–39"), "Lecture/Seminar": ("30–60, talks","Adults 30–55"),
}
OVR = [
 ("j. cole", "18–34, hip-hop", "Youth 16–29"), ("don toliver", "16–29, hip-hop / trap", "Youth 16–29"),
 ("bryson tiller", "20–35, R&B", "Young adults 20–39"), ("tove lo", "20–39, pop", "Young adults 20–39"),
 ("benjamin ingrosso", "15–40, Swedish pop, many families", "Young adults 20–39"),
 ("deep purple", "50+, classic rock", "Mature 50+"), ("joe bonamassa", "45+, blues rock", "Mature 50+"),
 ("stevie wonder", "35–70, soul and pop", "Adults 30–55"), ("good charlotte", "30–45, pop-punk", "Adults 30–55"),
 ("simple plan", "28–42, pop-punk", "Adults 30–55"), ("comic con", "15–40, fandom and gaming", "Youth 16–29"),
 ("idol live", "Families and teens", "Families"), ("harry potter", "20–45 and families, film fans", "Young adults 20–39"),
 ("icona pop", "25–40, pop / electronic", "Young adults 20–39"), ("dizzee rascal", "30–45, UK rap", "Adults 30–55"),
 ("tinie tempah", "30–45, UK rap", "Adults 30–55"), ("the streets", "30–45, UK rap", "Adults 30–55"),
 ("saint levant", "18–35, alt-pop", "Young adults 20–39"), ("elgrandetoto", "16–30, rap", "Youth 16–29"),
 ("murda", "16–30, Swedish rap", "Youth 16–29"), ("omah lay", "18–32, afrobeats", "Youth 16–29"),
 ("beabadoobee", "16–28, indie", "Youth 16–29"), ("ricardo montaner", "35+, Latin pop", "Adults 30–55"),
 ("los kjarkas", "35+, Andean folk", "Adults 30–55"), ("tomten är far", "Families and 30–60", "Families"),
 ("djungelboken", "Families with children", "Families"), ("alice i underlandet", "Families with children", "Families"),
 ("svansjön", "Families and 30–60", "Families"), ("paradox", "30–55, film and game music", "Adults 30–55"),
 ("cat power", "30–50, indie", "Adults 30–55"), ("sisters of mercy", "45+, goth rock", "Mature 50+"),
 ("zucchero", "45+, Italian rock", "Mature 50+"), ("max raabe", "50+, cabaret", "Mature 50+"),
]
def clean(name):
    n = re.sub(r"[,\-|–]*\s*Platinum\s*Tic\w*\s*$", "", name, flags=re.I).strip(" ,-|")
    n = re.sub(r"\s*,\s*Platinum tickets", "", n, flags=re.I)
    if "comic con" in n.lower(): n = "Comic Con Stockholm Winter"
    return re.sub(r"\s+", " ", n).strip()

def t2m(t): h,m = map(int,t.split(":")[:2]); return h*60+m
def m2t(m): m%=1440; return f"{m//60:02d}:{m%60:02d}"
def windows(start, kind, segment, genre):
    if not start: return ("Doors / all day", "Typically 10:00–18:00" if kind=="fair" else "Check event")
    s=t2m(start)
    if genre=="Soccer" or segment=="Sports": a,b,c,d = s-90, s, s+110, s+150
    elif kind in ("stadium","arena"): a,b,c,d = s-150, s, s+150, s+210
    elif kind=="theatre" or segment=="Arts & Theatre": a,b,c,d = s-60, s, s+120, s+165
    else: a,b,c,d = s-90, s, s+135, s+180
    return (f"{m2t(a)}–{m2t(b)}", f"{m2t(c)}–{m2t(d)}")

def aud_for(name, genre):
    low = name.lower()
    for k,a,g in OVR:
        if k in low: return a,g
    return GENRE_AUD.get(genre, ("Mixed audience","Adults 30–55"))

raw = json.load(open("tm_raw.json"))
seen = {}; skipped = 0
for e in raw:
    v = (e.get("_embedded",{}).get("venues") or [{}])[0]
    if e.get("distance", 0) > 30 or "upsell" in (v.get("name") or "").lower() or re.search(r"garderob|parkering|presentkort|voucher", e["name"], re.I): skipped += 1; continue
    d = e["dates"]["start"].get("localDate")
    if not d: continue
    dd = datetime.date.fromisoformat(d)
    if dd < TODAY or dd > HORIZON: continue
    if (e["dates"].get("status") or {}).get("code") in ("cancelled","canceled"): continue
    c = (e.get("classifications") or [{}])[0]
    seg = (c.get("segment") or {}).get("name") or ""; gen = (c.get("genre") or {}).get("name") or ""
    if gen == "Undefined": gen = ""
    name = clean(e["name"]); vname = (v.get("name") or "").strip()
    key = BY_TM.get(vname.lower())
    t = e["dates"]["start"].get("localTime"); t = t[:5] if t else None
    k = (name.lower(), d, vname.lower())
    if k in seen:
        if t and (not seen[k]["time"] or t < seen[k]["time"]): seen[k]["time"] = t
        continue
    ven = VK.get(key)
    cap = ven["capacity"] if ven else 400
    kind = ven["kind"] if ven else "small"
    aud, grp = aud_for(name, gen)
    seen[k] = dict(id=e["id"], name=name, date=d, time=t, venueKey=key, venueName=ven["name"] if ven else vname,
        area=ven["area"] if ven else (v.get("city",{}).get("name") or "Stockholm"), segment=seg, genre=gen,
        crowd=cap, crowdEst=bool(ven), audience=aud, audienceGroup=grp, url=e.get("url"), kind=kind)
evs = sorted(seen.values(), key=lambda x: (x["date"], x["time"] or "99"))
for x in evs:
    x["arrive"], x["exit"] = windows(x["time"], x["kind"], x["segment"], x["genre"])
print("events", len(evs), "skipped>30km", skipped)
os.makedirs("db", exist_ok=True)
months = collections.defaultdict(list)
for x in evs:
    x.pop("kind", None); months[x["date"][:7]].append(x)
now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
for m, lst in months.items():
    doc = dict(month=m, updatedAt=now, source="Ticketmaster Discovery API", events=lst)
    json.dump(doc, open(f"db/tm_{m}.json","w"), ensure_ascii=False)
    print(m, len(lst), os.path.getsize(f"db/tm_{m}.json"))
for v in VENUES:
    vv = {k:v[k] for k in v if k!="tm"}; json.dump(vv, open(f"db/venue_{v['key']}.json","w"), ensure_ascii=False)
# weather (skipped if the forecast could not be fetched)
if os.path.exists("wx.json"):
    wx = json.load(open("wx.json"))["daily"]
    days = [dict(date=wx["time"][i], code=wx["weather_code"][i], tmax=wx["temperature_2m_max"][i], tmin=wx["temperature_2m_min"][i],
                 precip=wx["precipitation_sum"][i], pop=wx["precipitation_probability_max"][i], wind=wx["wind_speed_10m_max"][i]) for i in range(len(wx["time"]))]
    normals = {"09": dict(tmax=16, tmin=9, wetDays=9), "10": dict(tmax=10, tmin=5, wetDays=10), "11": dict(tmax=5, tmin=1, wetDays=11),
               "12": dict(tmax=2, tmin=-2, wetDays=11), "01": dict(tmax=0, tmin=-5, wetDays=10),
               "02": dict(tmax=0, tmin=-5, wetDays=8), "03": dict(tmax=4, tmin=-2, wetDays=8), "04": dict(tmax=10, tmin=2, wetDays=7),
               "05": dict(tmax=16, tmin=7, wetDays=7), "06": dict(tmax=20, tmin=11, wetDays=8), "07": dict(tmax=23, tmin=14, wetDays=8), "08": dict(tmax=21, tmin=13, wetDays=9)}
    json.dump(dict(updatedAt=now, source="Open-Meteo", location="Stockholm", days=days, normals=normals,
                   normalsNote="Approximate Stockholm monthly averages (1991–2020)"), open("db/weather.json","w"))
json.dump(dict(updatedAt=now, months=sorted(months), eventCount=len(evs)), open("db/meta.json","w"))

import glob
writes=[]
for f in sorted(glob.glob("db/tm_*.json")):
    writes.append(dict(op="set",collection="tm",doc_id=os.path.basename(f)[3:-5],file_path=os.path.abspath(f)))
if os.path.exists("db/weather.json"): writes.append(dict(op="set",collection="feeds",doc_id="weather",file_path=os.path.abspath("db/weather.json")))
writes.append(dict(op="set",collection="feeds",doc_id="meta",file_path=os.path.abspath("db/meta.json")))
json.dump(writes,open("batch.json","w")); print("batch entries", len(writes)); print(json.dumps(writes))
