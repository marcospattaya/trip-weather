#!/usr/bin/env python3
"""One-off helper: road distances for detour options between Dong Van and Du Gia.

Geocodes villages with Nominatim and routes with the public OSRM server, then
prints JSON (distance, OSRM time, roads used) for each candidate itinerary.
"""
import json
import time
import urllib.parse
import urllib.request

UA = "trip-weather-routes/1.0 (github.com/marcospattaya/trip-weather)"
FIXED = {
    "dongvan": (23.27967, 105.36078), "mapileng": (23.24062, 105.41208),
    "meovac": (23.16332, 105.41044), "mauque": (23.06559, 105.23774),
    "dugia": (22.9292, 105.2268),
}
PLACES = ["Xín Cái", "Thượng Phùng", "Sơn Vĩ", "Niêm Sơn", "Lũng Pù", "Khâu Vai",
          "Lũng Phìn", "Pải Lủng", "Tát Ngà", "Pả Vi", "Niêm Tòng", "Nậm Ban", "Sủng Máng"]


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def geocode(name):
    q = urllib.parse.urlencode({"q": name, "countrycodes": "vn", "format": "jsonv2", "limit": 5,
                                "viewbox": "105.10,23.45,105.60,22.85", "bounded": 1})
    try:
        res = get("https://nominatim.openstreetmap.org/search?" + q)
    except Exception as e:
        return {"error": str(e)}
    time.sleep(1.2)
    return [{"name": h.get("display_name"), "lat": float(h["lat"]), "lon": float(h["lon"]),
             "type": h.get("type"), "class": h.get("category") or h.get("class")} for h in res]


def route(points):
    coords = ";".join(f"{lon},{lat}" for lat, lon in points)
    url = ("https://router.project-osrm.org/route/v1/driving/" + coords +
           "?overview=false&steps=true&annotations=false")
    r = get(url)
    if r.get("code") != "Ok":
        return {"error": r.get("code")}
    rt = r["routes"][0]
    roads = {}
    for leg in rt["legs"]:
        for s in leg["steps"]:
            key = (s.get("ref") or "") + " | " + (s.get("name") or "")
            roads[key] = roads.get(key, 0) + s["distance"]
    return {"km": round(rt["distance"] / 1000, 1), "osrm_h": round(rt["duration"] / 3600, 2),
            "legs_km": [round(l["distance"] / 1000, 1) for l in rt["legs"]],
            "roads_km": {k: round(v / 1000, 1) for k, v in sorted(roads.items(), key=lambda kv: -kv[1]) if v > 500}}


def steps(points):
    coords = ";".join(f"{lon},{lat}" for lat, lon in points)
    r = get("https://router.project-osrm.org/route/v1/driving/" + coords + "?overview=false&steps=true")
    out = []
    for i, leg in enumerate(r["routes"][0]["legs"]):
        for s in leg["steps"]:
            out.append({"leg": i, "km": round(s["distance"] / 1000, 2), "mode": s.get("mode"), "name": s.get("name"),
                        "ref": s.get("ref"), "type": s["maneuver"].get("type"),
                        "at": [round(s["maneuver"]["location"][1], 5), round(s["maneuver"]["location"][0], 5)]})
    return out


def main():
    dock, sonvi, meovac = (23.23088, 105.42662), (23.2466, 105.4695), (23.16332, 105.41044)
    print(json.dumps({"dock_to_sonvi_to_meovac": steps([dock, sonvi, meovac])}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
