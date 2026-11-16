---
name: weather-aware-slots
description: Find an outdoor break that fits a free calendar interval and an hourly forecast.
---

# Weather-aware free slots

Use when someone wants a walk, an outdoor study break or a weather-aware free interval. Ask for a duration and free intervals with explicit UTC offsets, or obtain them from an authorized read-only calendar tool. Return one start and end time in the user's timezone, the maximum rain probability and a short reason. When the schedule or forecast is unavailable, name the missing source.

Run the bundled Python 3.11+ script from this skill's installed directory. The offline example has one rainy hour followed by a suitable hour.

```sh
python scripts/weather_slots.py --example
```

The example selects 18:00–18:30 UTC on January 12, with 10% rain probability. For other requests, pass a JSON object on standard input with `free` intervals, `minutes`, and either supplied hourly `weather` or public `coordinates` in latitude/longitude order. Intervals are half-open. Each weather row has an offset-aware hour `start`, `tempC`, `rainPct` and `windKmh`. The optional live lookup sends the coordinates to Open-Meteo and can fall back to the National Weather Service for US locations. Calendar titles and free intervals stay in the caller. [NWS API](https://www.weather.gov/documentation/services-web-api)

The computation checks every forecast hour touched by the full break. It accepts 8–30 °C, at most 35% rain probability and wind up to 30 km/h. Among feasible options it favors lower rain risk, temperatures closer to 20 °C, then an earlier start. A missing hour disqualifies that window. [Open-Meteo forecast data](https://open-meteo.com/en/docs)
