#!/usr/bin/env python3
"""Fetch multi-model hourly forecasts from Open-Meteo for the places in points.json.

Writes data/latest.json. Runs in GitHub Actions (see .github/workflows/fetch.yml)
and uses only the standard library, so the workflow installs nothing.
Set "active" to false in points.json to pause it without deleting anything.
"""
import datetime
import json
import os
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    with open(os.path.join(HERE, "points.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    if not cfg.get("active", True):
        print("points.json says active: false, nothing to do")
        return
    keys = list(cfg["points"])
    params = {
        "latitude": ",".join(str(cfg["points"][k][0]) for k in keys),
        "longitude": ",".join(str(cfg["points"][k][1]) for k in keys),
        "hourly": ",".join(cfg.get("hourly", ["temperature_2m", "precipitation"])),
        "models": ",".join(cfg["models"]),
        "timezone": cfg.get("timezone", "auto"),
        "forecast_days": cfg.get("forecast_days", 8),
    }
    url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(params, safe=",")
    req = urllib.request.Request(url, headers={"User-Agent": "trip-weather (github.com/marcospattaya/trip-weather)"})
    data, last_error = None, None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                data = json.load(r)
            break
        except Exception as e:  # network hiccup or rate limit: wait and retry
            last_error = e
            time.sleep(15 * (attempt + 1))
    if data is None:
        sys.exit(f"Open-Meteo request failed: {last_error}")
    if isinstance(data, dict):
        if data.get("error"):
            sys.exit(f"Open-Meteo error: {data.get('reason')}")
        data = [data]

    out = {
        "fetched_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "source": "Open-Meteo (open-meteo.com), CC BY 4.0",
        "timezone": params["timezone"],
        "models": cfg["models"],
        "time": data[0]["hourly"]["time"],
        "points": {},
    }
    for key, d in zip(keys, data):
        hourly = {name: values for name, values in d["hourly"].items() if name != "time"}
        out["points"][key] = {"elevation": d.get("elevation"), "hourly": hourly}

    os.makedirs(os.path.join(HERE, "data"), exist_ok=True)
    with open(os.path.join(HERE, "data", "latest.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, separators=(",", ":"))
    print(f"saved {len(keys)} places, {len(out['time'])} hours, {len(cfg['models'])} models")


if __name__ == "__main__":
    main()
