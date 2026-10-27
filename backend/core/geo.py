import math

EARTH_RADIUS_KM = 6371.0088

SPEEDS_KMH = {"walking": 4.5, "car": 35.0, "public": 20.0, "bicycle": 14.0}
DETOUR_FACTOR = {"walking": 1.25, "car": 1.35, "public": 1.4, "bicycle": 1.3}


def haversine_km(lat1, lng1, lat2, lng2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def haversine_m(lat1, lng1, lat2, lng2):
    return haversine_km(lat1, lng1, lat2, lng2) * 1000


def bounding_box(lat, lng, radius_km):
    dlat = radius_km / 111.32
    dlng = radius_km / (111.32 * max(math.cos(math.radians(lat)), 0.01))
    return lat - dlat, lat + dlat, lng - dlng, lng + dlng


def estimate_travel(lat1, lng1, lat2, lng2, transport="car"):
    transport = transport if transport in SPEEDS_KMH else "car"
    km = haversine_km(lat1, lng1, lat2, lng2) * DETOUR_FACTOR[transport]
    minutes = km / SPEEDS_KMH[transport] * 60
    if transport in ("car", "public") and km > 0.05:
        minutes += 5
    return round(km, 2), round(minutes, 1)
