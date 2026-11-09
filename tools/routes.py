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


def main():
    pick = dict(FIXED)
    pick.update({"sonvi": (23.2466, 105.4695), "niemson": (23.0366, 105.421), "tatnga": (23.0869, 105.3662),
                 "khauvai": (23.1138, 105.4806), "lungphin": (23.1354, 105.2792), "sungmang": (23.1645, 105.3187),
                 "tusan_dock": (23.23088, 105.42662)})
    plans = {
        "base": ["dongvan", "mapileng", "meovac", "mauque", "dugia"],
        "base_with_boat_road": ["dongvan", "mapileng", "tusan_dock", "mapileng", "meovac", "mauque", "dugia"],
        "sonvi_out_back": ["dongvan", "mapileng", "meovac", "sonvi", "meovac", "mauque", "dugia"],
        "sonvi_from_mapileng": ["dongvan", "mapileng", "sonvi", "meovac", "mauque", "dugia"],
        "sonvi_via_tusan": ["dongvan", "tusan_dock", "sonvi", "meovac", "mauque", "dugia"],
        "niemson_mauque": ["dongvan", "mapileng", "meovac", "niemson", "mauque", "dugia"],
        "tatnga_mauque": ["dongvan", "mapileng", "meovac", "tatnga", "mauque", "dugia"],
        "khauvai_niemson_mauque": ["dongvan", "mapileng", "meovac", "khauvai", "niemson", "mauque", "dugia"],
        "sungmang_lungphin": ["dongvan", "mapileng", "meovac", "sungmang", "lungphin", "mauque", "dugia"],
    }
    out = {"routes": {}}
    for name, seq in plans.items():
        try:
            out["routes"][name] = {"via": seq, **route([pick[s] for s in seq])}
        except Exception as e:
            out["routes"][name] = {"via": seq, "error": str(e)}
        time.sleep(1)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
