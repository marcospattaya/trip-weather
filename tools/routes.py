#!/usr/bin/env python3
"""One-off helper: geometry and elevation profile for the new Day 3 (Dong Van -> Son Vi loop -> Du Gia).

Routes with the public OSRM server, samples the line every 250 m and asks the
Open-Meteo elevation API (Copernicus 90 m DEM) for each sample. Prints JSON.
"""
import json
import math
import time
import urllib.request

UA = "trip-weather-routes/1.0 (github.com/marcospattaya/trip-weather)"
STOPS = [("dongvan", 23.27967, 105.36078), ("mapileng", 23.24062, 105.41208), ("dock", 23.23088, 105.42662),
         ("sonvi", 23.2466, 105.4695), ("pavi", 23.21008, 105.41633), ("meovac", 23.16332, 105.41044),
         ("mauque", 23.06559, 105.23774), ("dugia", 22.9292, 105.2268)]


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode("utf-8"))


def hav(a, b):
    R = 6371.0
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def main():
    coords = ";".join(f"{lon},{lat}" for _, lat, lon in STOPS)
    r = get("https://router.project-osrm.org/route/v1/driving/" + coords + "?overview=full&geometries=geojson&steps=false")
    rt = r["routes"][0]
    line = [(c[1], c[0]) for c in rt["geometry"]["coordinates"]]
    # resample every 250 m
    samples, carry = [(0.0, line[0])], 0.0
    dist = 0.0
    step = 0.25
    nxt = step
    for a, b in zip(line, line[1:]):
        seg = hav(a, b)
        while seg > 0 and dist + seg >= nxt:
            t = (nxt - dist) / seg
            samples.append((nxt, (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))))
            nxt += step
        dist += seg
    samples.append((dist, line[-1]))
    elev = []
    for i in range(0, len(samples), 100):
        chunk = samples[i:i + 100]
        lat = ",".join(f"{p[1][0]:.5f}" for p in chunk)
        lon = ",".join(f"{p[1][1]:.5f}" for p in chunk)
        e = get(f"https://api.open-meteo.com/v1/elevation?latitude={lat}&longitude={lon}")
        elev += e["elevation"]
        time.sleep(1)
    print(json.dumps({
        "km": round(rt["distance"] / 1000, 1), "osrm_h": round(rt["duration"] / 3600, 2),
        "legs_km": [round(l["distance"] / 1000, 1) for l in rt["legs"]],
        "stops": [s[0] for s in STOPS],
        "line": [[round(a, 5), round(b, 5)] for a, b in line],
        "profile": [[round(k, 2), round(z)] for (k, _), z in zip(samples, elev)],
    }))


if __name__ == "__main__":
    main()
