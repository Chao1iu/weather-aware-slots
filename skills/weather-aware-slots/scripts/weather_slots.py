"""Find a continuous outdoor window from free intervals and hourly weather in UTC."""

import argparse
from datetime import UTC, datetime, timedelta
import json
import re
import sys
from urllib import parse, request


def instant(value):
    value = datetime.fromisoformat(value)
    if value.utcoffset() is None:
        raise ValueError("Every boundary needs a UTC offset.")
    return value.astimezone(UTC)


def forecast(latitude=34.021, longitude=-118.286):
    query = parse.urlencode({"latitude": latitude, "longitude": longitude, "timezone": "UTC",
                             "timeformat": "unixtime", "forecast_days": 3, "wind_speed_unit": "kmh",
                             "hourly": "temperature_2m,precipitation_probability,wind_speed_10m"})
    try:
        with request.urlopen("https://api.open-meteo.com/v1/forecast?" + query, timeout=6) as response:
            fields = json.load(response)["hourly"]
        rows = [{"start": datetime.fromtimestamp(stamp, UTC).isoformat(), "tempC": temp, "rainPct": rain,
                 "windKmh": wind, "source": "Open-Meteo"} for stamp, temp, rain, wind in
                zip(fields["time"], fields["temperature_2m"], fields["precipitation_probability"],
                    fields["wind_speed_10m"], strict=True) if None not in (temp, rain, wind)]
        if rows:
            return rows
    except (OSError, ValueError, KeyError):
        pass
    headers = {"User-Agent": "CSCI599 Campus Forecast (educational project)", "Accept": "application/geo+json"}
    point = f"https://api.weather.gov/points/{float(latitude):.4f},{float(longitude):.4f}"
    with request.urlopen(request.Request(point, headers=headers), timeout=8) as response:
        url = json.load(response)["properties"]["forecastHourly"]
    if parse.urlsplit(url).netloc != "api.weather.gov" or parse.urlsplit(url).scheme != "https":
        raise ValueError("Invalid National Weather Service forecast link.")
    with request.urlopen(request.Request(url, headers=headers), timeout=8) as response:
        periods = json.load(response)["properties"]["periods"]
    rows = []
    for hour in periods:
        speeds = re.findall(r"[\d.]+", hour["windSpeed"])
        rain = (hour.get("probabilityOfPrecipitation") or {}).get("value")
        if not speeds or rain is None or hour.get("temperature") is None:
            continue
        wind = max(map(float, speeds)) * (1.609344 if "mph" in hour["windSpeed"] else 1)
        temp = hour["temperature"]
        rows.append({"start": instant(hour["startTime"]).isoformat(), "tempC": round((temp-32)*5/9, 1)
                     if hour["temperatureUnit"] == "F" else temp, "rainPct": rain,
                     "windKmh": round(wind, 1), "source": "National Weather Service"})
    if not rows:
        raise ValueError("The weather providers have no complete hourly observations.")
    return rows


def suggest(free, weather, minutes=30):
    if isinstance(minutes, bool) or not isinstance(minutes, int) or not 5 <= minutes <= 180:
        raise ValueError("Choose a duration from 5 to 180 minutes.")
    duration = timedelta(minutes=minutes)
    hour = timedelta(hours=1)
    samples = {instant(row["start"]): row for row in weather}
    choices = []
    for gap in free:
        left, right = instant(gap["start"]), instant(gap["end"])
        starts = {left, *(t for t in samples if left < t < right)}
        for start in starts:
            end = start + duration
            if end > right:
                continue
            cursor = start.replace(minute=0, second=0, microsecond=0)
            used = []
            while cursor < end:
                row = samples.get(cursor)
                if not row or not (8 <= row["tempC"] <= 30 and row["rainPct"] <= 35 and row["windKmh"] <= 30):
                    break
                used.append(row)
                cursor += hour
            if cursor >= end:
                rain = max(r["rainPct"] for r in used)
                wind = max(r["windKmh"] for r in used)
                choices.append(((rain, max(abs(r["tempC"] - 20) for r in used), start),
                                {"start": start.isoformat(), "end": end.isoformat(), "minutes": minutes,
                                 "maxRainPct": rain, "maxWindKmh": wind,
                                 "temperatureC": [min(r["tempC"] for r in used), max(r["tempC"] for r in used)]}))
    if not choices:
        return {"slot": None, "reason": "No continuous free interval has suitable forecast coverage for the requested duration."}
    slot = min(choices, key=lambda item: item[0])[1]
    return {"slot": slot, "reason": "The full interval is free and every forecast hour meets the temperature, rain and wind limits."}


def example():
    free = [{"start": "2026-01-12T17:35:00Z", "end": "2026-01-12T18:45:00Z"}]
    weather = [{"start": "2026-01-12T17:00:00Z", "tempC": 14, "rainPct": 70, "windKmh": 9},
               {"start": "2026-01-12T18:00:00Z", "tempC": 18, "rainPct": 10, "windKmh": 8}]
    return suggest(free, weather, 30)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--example", action="store_true")
    args = parser.parse_args()
    if args.example:
        result = example()
    else:
        payload = json.load(sys.stdin)
        weather = payload["weather"] if "weather" in payload else forecast(*payload["coordinates"])
        result = suggest(payload["free"], weather, payload.get("minutes", 30))
    print(json.dumps(result, indent=2))
