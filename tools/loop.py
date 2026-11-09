#!/usr/bin/env python3
"""One-off helper: is there a real loop through the border villages (Thuong Phung, Xin Cai, Son Vi)?

Looks up the village nodes in OpenStreetMap (Overpass), then routes a few variants
with the public OSRM server. Prints JSON (geometry included, no elevation).
"""
import json
import sys
import time
import urllib.parse
import urllib.request

UA = "trip-weather-routes/1.0 (github.com/marcospattaya/trip-weather)"


def get(url, data=None, tries=3, timeout=60):
    for n in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as ex:  # noqa: BLE001
            print(f"try {n + 1} failed for {url[:60]}: {ex}", file=sys.stderr)
            if n == tries - 1:
                raise
            time.sleep(5 * 2 ** n)


def main():
    q = """[out:json][timeout:60];
node["place"]["name"~"Xín Cái|Thượng Phùng|Sơn Vĩ|Lũng Làn|Pả Vi|Tát Ngà|Lũng Pù|Mèo Vạc"](23.10,105.30,23.40,105.62);
out;"""
    ov = get("https://overpass-api.de/api/interpreter", data=urllib.parse.urlencode({"data": q}).encode())
    places = [{"name": e["tags"].get("name"), "place": e["tags"].get("place"), "lat": e["lat"], "lon": e["lon"]}
              for e in ov.get("elements", [])]
    print(f"{len(places)} places", file=sys.stderr)

    def pick(name):
        c = [p for p in places if p["name"] and name.lower() in p["name"].lower()]
        rank = {"town": 0, "village": 1, "hamlet": 2, "isolated_dwelling": 3}
        c.sort(key=lambda p: rank.get(p["place"], 9))
        return (c[0]["lat"], c[0]["lon"]) if c else None

    DV = (23.27967, 105.36078); MPL = (23.24062, 105.41208); DOCK = (23.23088, 105.42662)
    MV = (23.16332, 105.41044); MD = (23.06559, 105.23774); DG = (22.9292, 105.2268)
    TP, XC, SV = pick("Thượng Phùng"), pick("Xín Cái"), pick("Sơn Vĩ")
    out = {"places": places, "picked": {"thuongphung": TP, "xincai": XC, "sonvi": SV}, "variants": {}}
    variants = {
        "loop_border_then_boat": [DV, TP, XC, SV, DOCK, MV, MD, DG],
        "loop_mpl_border_then_boat": [DV, MPL, TP, XC, SV, DOCK, MV, MD, DG],
        "sonvi_village_outback": [DV, MPL, DOCK, SV, MV, MD, DG],
        "original": [DV, MPL, DOCK, MV, MD, DG],
    }
    for name, pts in variants.items():
        if any(p is None for p in pts):
            out["variants"][name] = {"error": "missing waypoint"}
            continue
        coords = ";".join(f"{lon},{lat}" for lat, lon in pts)
        try:
            r = get("https://router.project-osrm.org/route/v1/driving/" + coords + "?overview=full&geometries=geojson&steps=true")
        except Exception as ex:  # noqa: BLE001
            out["variants"][name] = {"error": str(ex)}
            continue
        rt = r["routes"][0]
        roads = []
        for leg in rt["legs"]:
            for s in leg["steps"]:
                nm = (s.get("ref") or s.get("name") or "").strip()
                if s["distance"] > 800:
                    roads.append([nm, round(s["distance"] / 1000, 1)])
        out["variants"][name] = {
            "km": round(rt["distance"] / 1000, 1), "osrm_h": round(rt["duration"] / 3600, 2),
            "legs_km": [round(l["distance"] / 1000, 1) for l in rt["legs"]],
            "roads": roads,
            "line": [[round(c[1], 5), round(c[0], 5)] for c in rt["geometry"]["coordinates"]],
        }
        time.sleep(1.5)
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
