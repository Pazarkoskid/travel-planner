import json
import logging
import urllib.request

from django.conf import settings

from .geo import estimate_travel

logger = logging.getLogger(__name__)

OSRM_PROFILES = {"car": "driving", "walking": "foot", "bicycle": "bike", "public": "driving"}


def _haversine_matrix(points, transport):
    n = len(points)
    km = [[0.0] * n for _ in range(n)]
    minutes = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i != j:
                km[i][j], minutes[i][j] = estimate_travel(*points[i], *points[j], transport=transport)
    return km, minutes


def _osrm_matrix(points, transport):
    profile = OSRM_PROFILES.get(transport, "driving")
    coords = ";".join(f"{lng},{lat}" for lat, lng in points)
    url = f"{settings.OSRM_URL.rstrip('/')}/table/v1/{profile}/{coords}?annotations=duration,distance"
    with urllib.request.urlopen(url, timeout=settings.ROUTING_TIMEOUT_SECONDS) as resp:
        data = json.loads(resp.read().decode())
    if data.get("code") != "Ok":
        raise ValueError(f"OSRM error: {data.get('code')}")
    km = [[(d or 0) / 1000 for d in row] for row in data["distances"]]
    minutes = [[(d or 0) / 60 for d in row] for row in data["durations"]]
    return km, minutes


def travel_matrix(points, transport="car"):
    warnings = []
    if settings.ROUTING_PROVIDER == "osrm" and len(points) > 1:
        try:
            km, minutes = _osrm_matrix(points, transport)
            return km, minutes, "osrm", warnings
        except Exception as exc:
            logger.warning("OSRM unavailable, falling back: %s", exc)
            warnings.append("Сервисот за рутирање е недостапен; времињата се проценети од воздушно растојание.")
    km, minutes = _haversine_matrix(points, transport)
    if settings.ROUTING_PROVIDER != "osrm":
        warnings.append("Времињата за движење се проценка (воздушно растојание × фактор), не реална рута.")
    return km, minutes, "haversine", warnings
