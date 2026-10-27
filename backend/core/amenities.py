import json
import logging
import urllib.parse
import urllib.request

from django.conf import settings
from django.core.cache import cache

from .exceptions import ServiceError

logger = logging.getLogger(__name__)

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


SHOP_RE = "^(bakery|pastry|supermarket|convenience|greengrocer|kiosk|newsagent|tobacco)$"
AMENITY_RE = "^(marketplace|bureau_de_change|atm|pharmacy)$"


def build_query(lat, lng, radius_m, categories=None):
    around = f"(around:{radius_m},{lat:.5f},{lng:.5f})"
    return (f'[out:json][timeout:20];(nwr["shop"~"{SHOP_RE}"]{around};'
            f'nwr["amenity"~"{AMENITY_RE}"]{around};);out center tags 500;')


def _endpoints():
    urls = [settings.OVERPASS_URL, *getattr(settings, "OVERPASS_FALLBACK_URLS", [])]
    return list(dict.fromkeys(u for u in urls if u))


def _fetch(query):
    data = urllib.parse.urlencode({"data": query}).encode()
    errors = []
    for url in _endpoints():
        req = urllib.request.Request(url, data=data, headers={
            "User-Agent": UA, "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded"})
        try:
            with urllib.request.urlopen(req, timeout=settings.OVERPASS_TIMEOUT_SECONDS) as resp:
                payload = json.loads(resp.read().decode())
            if "elements" not in payload:
                raise ValueError(payload.get("remark", "no elements"))
            return payload
        except Exception as exc:
            logger.warning("Overpass %s failed: %s", url, exc)
            errors.append(f"{url}: {exc}")
    raise ConnectionError("; ".join(errors) or "no Overpass endpoint")


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
    query = build_query(city.center_lat, city.center_lng, radius_m)
    try:
        items = parse(_fetch(query))
    except Exception as exc:
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
