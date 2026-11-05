# trip-weather

Three times a day (04:40, 11:40 and 17:40, UTC+7) a GitHub Action fetches hourly forecasts from nine
global models for the places in `points.json` and saves them to `data/latest.json`:
ECMWF, ECMWF AI, GFS, ICON, GEM, JMA, UK Met Office, ARPEGE and CMA, all through [Open-Meteo](https://open-meteo.com)
(data CC BY 4.0). The short-range models stop after a few days, so later days use fewer of them.

`summarize.py` turns that file into one row per day of a trip (coldest and warmest riding hour, and how many
models show rain), given the riding windows in a separate `trip.json` that is not stored here.

- Pause it: set `"active": false` in `points.json`.
- Next trip: change the places in `points.json`.
- Run it now: Actions tab, "Fetch forecast", "Run workflow".
