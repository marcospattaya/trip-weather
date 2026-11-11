#!/usr/bin/env python3
"""One-off helper: OSM geometry around Ma Pi Leng (the Skypath) and the road from Son Vi to border marker 476."""
import json
import sys
import time
import urllib.parse
import urllib.request

UA = "trip-weather-routes/1.0 (github.com/marcospattaya/trip-weather)"


def get(url, data=None, tries=3, timeout=90):
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
    q = """[out:json][timeout:90];
(
  way["highway"](23.226,105.380,23.258,105.425);
  node["name"~"Mỏm|Skypath|Sky path|tử thần|Mã Pí Lèng|Ma Pi Leng|Tu Sản",i](23.20,105.36,23.28,105.45);
  node["tourism"](23.226,105.380,23.258,105.425);
);
out geom;"""
    ov = get("https://overpass-api.de/api/interpreter", data=urllib.parse.urlencode({"data": q}).encode())
    ways, nodes = [], []
    for e in ov.get("elements", []):
        if e["type"] == "way":
            ways.append({"id": e["id"], "tags": e.get("tags", {}),
                         "geom": [[round(p["lat"], 6), round(p["lon"], 6)] for p in e.get("geometry", [])]})
        elif e["type"] == "node":
            nodes.append({"id": e["id"], "tags": e.get("tags", {}), "lat": e["lat"], "lon": e["lon"]})
    print(f"{len(ways)} ways, {len(nodes)} nodes", file=sys.stderr)
    r = get("https://router.project-osrm.org/route/v1/driving/105.4695,23.2466;105.48037,23.24553?overview=full&geometries=geojson")
    rt = r["routes"][0]
    print(json.dumps({"ways": ways, "nodes": nodes,
                      "marker476": {"km": round(rt["distance"] / 1000, 2),
                                    "line": [[round(c[1], 6), round(c[0], 6)] for c in rt["geometry"]["coordinates"]]}},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
