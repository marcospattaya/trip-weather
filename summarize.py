#!/usr/bin/env python3
"""Turn data/latest.json into one forecast row per day of a trip.

usage: python3 summarize.py latest.json trip.json [--now 2026-11-08T07:00]

trip.json lists the riding windows (kept out of this repo):
{
  "labels": {"ecmwf_ifs025": "ECMWF", ...},
  "rain_mm": 1.0,
  "heavy_mm": 8.0,
  "windows": [
    {"day": "Sun 8", "where": "A -> B", "points": ["a", "b"],
     "start": "2026-11-08T13:00", "end": "2026-11-08T18:00",
     "night": {"points": ["b"], "start": "2026-11-08T18:00", "end": "2026-11-09T08:00"}}
  ]
}

For each window and model: the coldest and warmest hour across the points (Low,
High) and the rain total at the wettest point. A model only counts for a window
if it covers every hour of it. Windows that ended before --now are left out.
Prints JSON on stdout.
"""
import json
import math
import statistics
import sys


def rnd(x):
    return int(math.floor(x + 0.5))


def span(a, b, unit=" °C"):
    a, b = rnd(a), rnd(b)
    return f"{a}{unit}" if a == b else f"{a}–{b}{unit}"


def feels_like(t, v=40.0):
    """Wind chill (Environment Canada) at riding speed v km/h."""
    p = v ** 0.16
    return 13.12 + 0.6215 * t - 11.37 * p + 0.3965 * t * p


def series(point, var, model, single):
    h = point["hourly"]
    return h.get(f"{var}_{model}") if not single else (h.get(var) or h.get(f"{var}_{model}"))


def window_stats(data, models, labels, pts, start, end):
    time = data["time"]
    if start not in time or end not in time:
        return []
    i0, i1 = time.index(start), time.index(end)
    single = len(models) == 1
    res = []
    for m in models:
        lo, hi, wettest, ok = math.inf, -math.inf, 0.0, True
        for p in pts:
            T = series(data["points"][p], "temperature_2m", m, single)
            R = series(data["points"][p], "precipitation", m, single)
            if not T or not R:
                ok = False
                break
            seg_t, seg_r = T[i0:i1], R[i0:i1]
            if any(v is None for v in seg_t) or any(v is None for v in seg_r):
                ok = False
                break
            lo, hi = min(lo, min(seg_t)), max(hi, max(seg_t))
            wettest = max(wettest, sum(seg_r))
        if ok and i1 > i0:
            res.append({"model": labels.get(m, m), "lo": round(lo, 1), "hi": round(hi, 1), "rain": round(wettest, 1)})
    return res


def rain_text(stats, night, rain_mm, heavy_mm):
    n = len(stats)
    if n == 0:
        return "No model reaches this day yet"
    wet = [s for s in stats if s["rain"] >= rain_mm]
    heavy = [s["model"] for s in stats if s["rain"] >= heavy_mm]
    k = len(wet)
    if k == 0:
        text = f"Dry in all {n} models" if n > 1 else "Dry"
    elif k * 4 <= n:
        text = f"Dry in {n - k} of {n} models"
    else:
        text = f"Showers in {k} of {n} models"
        if heavy and len(heavy) <= 3:
            names = heavy[0] if len(heavy) == 1 else ", ".join(heavy[:-1]) + " and " + heavy[-1]
            text += ", heavy in " + names
        elif heavy:
            text += ", heavy in most"
        elif max(s["rain"] for s in wet) < 3:
            text += ", light"
        else:
            text += f", {rnd(min(s['rain'] for s in wet))}–{rnd(max(s['rain'] for s in wet))} mm"
    if night:
        nn = len(night)
        nw = sum(1 for s in night if s["rain"] >= rain_mm)
        if nn and nw * 2 > nn:
            text += f"; rain overnight in {nw} of {nn}"
    return text


def main():
    args = sys.argv[1:]
    now = None
    if "--now" in args:
        i = args.index("--now")
        now = args[i + 1]
        del args[i:i + 2]
    data = json.load(open(args[0], encoding="utf-8"))
    trip = json.load(open(args[1], encoding="utf-8"))
    labels = trip.get("labels", {})
    rain_mm, heavy_mm = trip.get("rain_mm", 1.0), trip.get("heavy_mm", 8.0)
    models = data["models"]
    rows, used = [], set()
    for w in trip["windows"]:
        if now and w["end"] <= now:
            continue
        stats = window_stats(data, models, labels, w["points"], w["start"], w["end"])
        night = None
        if w.get("night"):
            nw = w["night"]
            night = window_stats(data, models, labels, nw["points"], nw["start"], nw["end"])
        used.update(s["model"] for s in stats)
        row = {"day": w["day"], "where": w["where"], "n": len(stats)}
        if stats:
            los, his = [s["lo"] for s in stats], [s["hi"] for s in stats]
            lo_med = statistics.median(los)
            row.update({
                "low": span(min(los), max(los)),
                "high": span(min(his), max(his)),
                "rain": rain_text(stats, night, rain_mm, heavy_mm),
                "lo_median": round(lo_med, 1),
                "feels_like_40kmh": rnd(feels_like(lo_med)),
                "models": stats,
            })
            if night:
                row["night"] = {"n": len(night), "lo": span(min(s["lo"] for s in night), max(s["lo"] for s in night)),
                                "wet": sum(1 for s in night if s["rain"] >= rain_mm),
                                "rain": [[s["model"], s["rain"]] for s in night]}
        else:
            row.update({"low": "–", "high": "–", "rain": rain_text(stats, None, rain_mm, heavy_mm)})
        rows.append(row)
    out = {"fetched_at": data["fetched_at"], "models_used": sorted(used), "rows": rows}
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
    print()


if __name__ == "__main__":
    main()
