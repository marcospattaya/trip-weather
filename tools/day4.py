#!/usr/bin/env python3
"""One-off helper: longer ways back from Du Gia to Ha Giang for Day 4 (OSRM + Nominatim). Prints JSON."""
import json
import sys
import time
import urllib.parse
import urllib.request

UA = "trip-weather-routes/1.0 (github.com/marcospattaya/trip-weather)"


def get(url, tries=3, timeout=45):
    for n in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as ex:  # noqa: BLE001
            print(f"try {n + 1} failed for {url[:60]}: {ex}", file=sys.stderr)
            if n == tries - 1:
                raise
            time.sleep(4 * 2 ** n)


def geo(q):
    try:
        r = get("https://nominatim.openstreetmap.org/search?format=json&limit=1&countrycodes=vn&q=" + urllib.parse.quote(q))
        time.sleep(1.2)
        return [float(r[0]["lat"]), float(r[0]["lon"])] if r else None
    except Exception:  # noqa: BLE001
        return None


HOME = (22.93131, 105.21653); FALL = (22.92548, 105.19765); HG = (22.82937, 104.98386)
MN = (22.77321, 105.16842); YM = (23.1172, 105.14912); TS = (23.06506, 104.99228)
HV = (23.04932, 104.99302); BS = (22.98817, 104.9359); LT = (23.04931, 105.04384)


def main():
    places = {}
    for name in ["Đường Thượng, Yên Minh", "Cán Tỷ, Quản Bạ", "Lũng Hồ, Yên Minh", "Thuận Hòa, Vị Xuyên", "Tùng Vài, Quản Bạ",
                 "Bát Đại Sơn, Quản Bạ", "Na Khê, Yên Minh", "Bạch Đích, Yên Minh", "Đông Minh, Yên Minh", "Lao Và Chải, Yên Minh"]:
        places[name] = geo(name)
    print(json.dumps(places, ensure_ascii=False), file=sys.stderr)
    V = {
        "planned_minhngoc": [HOME, FALL, MN, HG],
        "yenminh_quanba": [HOME, FALL, YM, TS, HV, BS, HG],
        "lungtam_quanba": [HOME, FALL, LT, TS, HV, BS, HG],
    }
    if places.get("Cán Tỷ, Quản Bạ"):
        V["cantỷ_lungtam"] = [HOME, FALL, tuple(places["Cán Tỷ, Quản Bạ"]), LT, TS, HV, BS, HG]
    if places.get("Đường Thượng, Yên Minh"):
        V["duongthuong_yenminh"] = [HOME, FALL, tuple(places["Đường Thượng, Yên Minh"]), YM, TS, HV, BS, HG]
    if places.get("Thuận Hòa, Vị Xuyên"):
        V["minhngoc_thuanhoa"] = [HOME, FALL, MN, tuple(places["Thuận Hòa, Vị Xuyên"]), HG]
    out = {"places": places, "variants": {}}
    for name, pts in V.items():
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
                if s["distance"] > 1500:
                    roads.append([nm, round(s["distance"] / 1000, 1)])
        out["variants"][name] = {
            "km": round(rt["distance"] / 1000, 1), "osrm_h": round(rt["duration"] / 3600, 2),
            "legs_km": [round(l["distance"] / 1000, 1) for l in rt["legs"]], "roads": roads,
            "line": [[round(c[1], 5), round(c[0], 5)] for c in rt["geometry"]["coordinates"]],
        }
        time.sleep(1.5)
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
