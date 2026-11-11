#!/usr/bin/env python3
"""One-off helper: geometry and elevation profile for the new Day 4 (Du Gia -> Lung Tam -> Quan Ba -> Ha Giang).

Routes with the public OSRM server, samples the line every 250 m and asks the
Open-Meteo elevation API (Copernicus 90 m DEM) for each sample. Prints JSON.
"""
import json
import math
import sys
import time
import urllib.request

UA = "trip-weather-routes/1.0 (github.com/marcospattaya/trip-weather)"
STOPS = [("home", 22.93131, 105.21653), ("fall", 22.92548, 105.19765), ("lungtam", 23.04931, 105.04384),
         ("tamson", 23.06506, 104.99228), ("heaven", 23.04932, 104.99302), ("bacsum", 22.98817, 104.9359),
         ("hg", 22.82937, 104.98386)]


def get(url, tries=4, timeout=30):
    for n in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as ex:  # noqa: BLE001
            print(f"try {n + 1} failed for {url[:70]}: {ex}", file=sys.stderr)
            if n == tries - 1:
                raise
            time.sleep(5 * 2 ** n)


def elevations(chunk):
    """Open-Meteo (Copernicus 90 m) first, OpenTopoData SRTM 90 m if it keeps failing."""
    lat = ",".join(f"{p[1][0]:.5f}" for p in chunk)
    lon = ",".join(f"{p[1][1]:.5f}" for p in chunk)
    try:
        return get(f"https://api.open-meteo.com/v1/elevation?latitude={lat}&longitude={lon}", tries=3)["elevation"], "open-meteo"
    except Exception:  # noqa: BLE001
        locs = "|".join(f"{p[1][0]:.5f},{p[1][1]:.5f}" for p in chunk)
        r = get(f"https://api.opentopodata.org/v1/srtm90m?locations={locs}", tries=3)
        return [x["elevation"] for x in r["results"]], "opentopodata"


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
    print(f"route {rt['distance'] / 1000:.1f} km, {len(samples)} samples", file=sys.stderr)
    elev, srcs = [], []
    for i in range(0, len(samples), 100):
        chunk = samples[i:i + 100]
        e, src = elevations(chunk)
        print(f"chunk {i // 100}: {len(e)} points from {src}", file=sys.stderr)
        elev += e
        srcs.append(src)
        time.sleep(1.5)
    print(json.dumps({
        "km": round(rt["distance"] / 1000, 1), "osrm_h": round(rt["duration"] / 3600, 2),
        "legs_km": [round(l["distance"] / 1000, 1) for l in rt["legs"]],
        "stops": [s[0] for s in STOPS],
        "elev_sources": srcs,
        "line": [[round(a, 5), round(b, 5)] for a, b in line],
        "profile": [[round(k, 2), round(z)] for (k, _), z in zip(samples, elev)],
    }))


if __name__ == "__main__":
    main()
