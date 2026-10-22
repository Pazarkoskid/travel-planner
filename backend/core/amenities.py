"""Корисни објекти за туристи од OpenStreetMap (Overpass API): пекари, маркети, менувачници, трафики…

* Податоците се © OpenStreetMap contributors (ODbL) — се прикажува атрибуција.
* Се бара круг околу центарот на градот; резултатот се кешира (AMENITIES_CACHE_SECONDS), за да не се
  оптоварува јавниот Overpass сервер.
* Ако Overpass не е достапен, се враќа последниот кеширан одговор или празна листа со порака.
"""
import json
import logging
import urllib.parse
import urllib.request

from django.conf import settings
from django.core.cache import cache

from .exceptions import ServiceError

logger = logging.getLogger(__name__)

# категорија → OSM услови (Overpass QL, за node/way)
CATEGORIES = {
    "bakery": ['["shop"="bakery"]', '["shop"="pastry"]'],
    "market": ['["shop"="supermarket"]', '["shop"="convenience"]', '["shop"="greengrocer"]', '["amenity"="marketplace"]'],
    "exchange": ['["amenity"="bureau_de_change"]'],
    "kiosk": ['["shop"="kiosk"]', '["shop"="newsagent"]', '["shop"="tobacco"]'],
    "atm": ['["amenity"="atm"]'],
    "pharmacy": ['["amenity"="pharmacy"]'],
}
UA = "TravelPlannerMK/1.0 (diploma prototype; https://github.com/pazarkoskid)"


def _category(tags):
    shop, amenity = tags.get("shop"), tags.get("amenity")
    if shop in ("bakery", "pastry"):
        return "bakery"
    if shop in ("supermarket", "convenience", "greengrocer") or amenity == "marketplace":
        return "market"
    if amenity == "bureau_de_change":
        return "exchange"
    if shop in ("kiosk", "newsagent", "tobacco"):
        return "kiosk"
    if amenity == "atm":
        return "atm"
    if amenity == "pharmacy":
        return "pharmacy"
    return None


def build_query(lat, lng, radius_m, categories):
    parts = []
    for cat in categories:
        for cond in CATEGORIES[cat]:
            for kind in ("node", "way"):
                parts.append(f"{kind}{cond}(around:{radius_m},{lat:.5f},{lng:.5f});")
    return f"[out:json][timeout:25];({''.join(parts)});out center tags 400;"


def _fetch(query):
    data = urllib.parse.urlencode({"data": query}).encode()
    req = urllib.request.Request(settings.OVERPASS_URL, data=data, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=settings.OVERPASS_TIMEOUT_SECONDS) as resp:
        return json.loads(resp.read().decode())


def parse(payload):
    out, seen = [], set()
    for el in payload.get("elements", []):
        tags = el.get("tags", {})
        cat = _category(tags)
        lat = el.get("lat") or el.get("center", {}).get("lat")
        lng = el.get("lon") or el.get("center", {}).get("lon")
        if not cat or lat is None or lng is None:
            continue
        key = (el.get("type"), el.get("id"))
        if key in seen:
            continue
        seen.add(key)
        street = " ".join(x for x in (tags.get("addr:street"), tags.get("addr:housenumber")) if x)
        out.append({
            "id": f"{el.get('type')}/{el.get('id')}",
            "category": cat,
            "name": tags.get("name:mk") or tags.get("name") or tags.get("brand") or tags.get("operator") or "",
            "lat": round(lat, 6), "lng": round(lng, 6),
            "opening_hours": tags.get("opening_hours", ""),
            "address": street,
            "phone": tags.get("phone") or tags.get("contact:phone") or "",
            "website": tags.get("website") or tags.get("contact:website") or "",
            "brand": tags.get("brand", ""),
            "osm_url": f"https://www.openstreetmap.org/{el.get('type')}/{el.get('id')}",
        })
    return out


def get_amenities(city, radius_m=None):
    radius_m = radius_m or settings.AMENITIES_RADIUS_M
    key = f"amenities:v1:{city.slug}:{radius_m}"
    stale_key = key + ":stale"
    cached = cache.get(key)
    if cached is not None:
        return cached
    query = build_query(city.center_lat, city.center_lng, radius_m, list(CATEGORIES))
    try:
        items = parse(_fetch(query))
    except Exception as exc:  # мрежа, timeout, 429 од Overpass
        logger.warning("Overpass error for %s: %s", city.slug, exc)
        stale = cache.get(stale_key)
        if stale is not None:
            return {**stale, "stale": True}
        raise ServiceError("Податоците од OpenStreetMap моментално не се достапни. Обидете се повторно.",
                           code="amenities_unavailable", status_code=503)
    data = {"city": city.slug, "center": [city.center_lat, city.center_lng], "radius_m": radius_m,
            "items": items, "source": "© OpenStreetMap contributors (ODbL)", "stale": False}
    cache.set(key, data, settings.AMENITIES_CACHE_SECONDS)
    cache.set(stale_key, data, 60 * 60 * 24 * 7)
    return data
