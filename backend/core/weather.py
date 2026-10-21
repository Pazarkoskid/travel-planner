"""Временска прогноза преку OpenWeather (бесплатни API-ја: current weather + 5 day / 3 hour forecast).

* Клучот е само на серверот (OPENWEATHER_API_KEY) — никогаш во frontend.
* Резултатите се кешираат (WEATHER_CACHE_SECONDS) по заокружени координати, за да не се троши квотата.
* Прогнозата е до 5 дена однапред и е неизвесна; frontend-от го кажува тоа.
"""
import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from django.conf import settings
from django.core.cache import cache

from .exceptions import ServiceError

logger = logging.getLogger(__name__)
BASE = "https://api.openweathermap.org/data/2.5"


def _get(path, lat, lng):
    params = {"lat": f"{lat:.4f}", "lon": f"{lng:.4f}", "units": "metric", "lang": "mk",
              "appid": settings.OPENWEATHER_API_KEY}
    url = f"{BASE}/{path}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=settings.WEATHER_TIMEOUT_SECONDS) as resp:
        return json.loads(resp.read().decode())


def _summarize_daily(forecast):
    tz_shift = timedelta(seconds=forecast.get("city", {}).get("timezone", 0))
    days = defaultdict(list)
    for item in forecast.get("list", []):
        local = datetime.fromtimestamp(item["dt"], tz=timezone.utc) + tz_shift
        days[local.date().isoformat()].append((local, item))
    out = []
    for day, items in sorted(days.items()):
        temps_min = [i["main"]["temp_min"] for _, i in items]
        temps_max = [i["main"]["temp_max"] for _, i in items]
        # Иконата и описот за денот се од терминот најблиску до пладне.
        midday = min(items, key=lambda x: abs(x[0].hour - 13))[1]
        descriptions = Counter(i["weather"][0]["description"] for _, i in items)
        out.append({
            "date": day,
            "min": round(min(temps_min)),
            "max": round(max(temps_max)),
            "icon": midday["weather"][0]["icon"].replace("n", "d"),
            "description": midday["weather"][0]["description"] or descriptions.most_common(1)[0][0],
            "pop": round(max(i.get("pop", 0) for _, i in items) * 100),
            "wind": round(max(i["wind"]["speed"] for _, i in items) * 3.6),
        })
    return out[:6]


def get_weather(lat, lng):
    if not settings.OPENWEATHER_API_KEY:
        searched = ", ".join(str(p) for p in (settings.BASE_DIR.parent / ".env", settings.BASE_DIR / ".env"))
        raise ServiceError(f"Прогнозата не е конфигурирана: нема OPENWEATHER_API_KEY. Се бара во: {searched}",
                           code="weather_not_configured", status_code=503)
    key = f"weather:{round(lat, 2)}:{round(lng, 2)}"
    cached = cache.get(key)
    if cached:
        return cached
    try:
        current = _get("weather", lat, lng)
        forecast = _get("forecast", lat, lng)
    except urllib.error.HTTPError as exc:
        logger.warning("OpenWeather HTTP error: %s", exc)
        if exc.code == 401:
            raise ServiceError("OpenWeather го одби клучот (401). Нов клуч се активира до 2 часа по регистрацијата; "
                               "проверете дали е точно копиран и дали е-поштата е потврдена.",
                               code="weather_invalid_key", status_code=503)
        raise ServiceError("Прогнозата моментално не е достапна.", code="weather_unavailable", status_code=503)
    except Exception as exc:  # мрежа, timeout
        logger.warning("OpenWeather error: %s", exc)
        raise ServiceError("Прогнозата моментално не е достапна.", code="weather_unavailable", status_code=503)
    data = {
        "current": {
            "temp": round(current["main"]["temp"]),
            "feels_like": round(current["main"]["feels_like"]),
            "humidity": current["main"]["humidity"],
            "wind": round(current["wind"]["speed"] * 3.6),
            "icon": current["weather"][0]["icon"],
            "description": current["weather"][0]["description"],
        },
        "daily": _summarize_daily(forecast),
        "source": "OpenWeather",
        "fetched_at": datetime.now(tz=timezone.utc).isoformat(),
    }
    cache.set(key, data, settings.WEATHER_CACHE_SECONDS)
    return data
