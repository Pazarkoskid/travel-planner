from unittest import mock

from django.core.cache import cache

from core import amenities

from .conftest import client_for

OVERPASS = {"elements": [
    {"type": "node", "id": 1, "lat": 41.1172, "lon": 20.8016, "tags": {"shop": "bakery", "name": "Пекара Охрид", "opening_hours": "Mo-Su 06:00-22:00"}},
    {"type": "way", "id": 2, "center": {"lat": 41.115, "lon": 20.80}, "tags": {"shop": "supermarket", "name": "Маркет", "addr:street": "Кеј Македонија", "addr:housenumber": "5"}},
    {"type": "node", "id": 3, "lat": 41.113, "lon": 20.799, "tags": {"amenity": "bureau_de_change", "name": "Менувачница"}},
    {"type": "node", "id": 4, "lat": 41.114, "lon": 20.798, "tags": {"shop": "kiosk", "phone": "+389 46 000 000"}},
    {"type": "node", "id": 5, "lat": 41.114, "lon": 20.798, "tags": {"shop": "clothes"}},  # не е во категориите
    {"type": "node", "id": 1, "lat": 41.1172, "lon": 20.8016, "tags": {"shop": "bakery"}},  # дупликат
]}


def test_query_contains_all_categories():
    q = amenities.build_query(41.1, 20.8, 3000, list(amenities.CATEGORIES))
    for cond in ('"shop"="bakery"', '"shop"="supermarket"', '"amenity"="bureau_de_change"', '"shop"="kiosk"', '"amenity"="atm"'):
        assert cond in q
    assert "around:3000,41.10000,20.80000" in q and "out center" in q


def test_amenities_api_parses_and_caches(city):
    cache.clear()
    with mock.patch.object(amenities, "_fetch", return_value=OVERPASS) as m:
        r1 = client_for().get(f"/api/v1/amenities/?city={city.slug}").json()
        client_for().get(f"/api/v1/amenities/?city={city.pk}")
    assert m.call_count == 1  # втор повик од кеш
    cats = sorted(i["category"] for i in r1["items"])
    assert cats == ["bakery", "exchange", "kiosk", "market"]
    market = next(i for i in r1["items"] if i["category"] == "market")
    assert market["address"] == "Кеј Македонија 5" and market["lat"] == 41.115
    assert "OpenStreetMap" in r1["source"]


def test_amenities_unavailable_uses_stale_or_503(city, settings):
    cache.clear()
    settings.AMENITIES_CACHE_SECONDS = 1
    with mock.patch.object(amenities, "_fetch", side_effect=TimeoutError):
        r = client_for().get(f"/api/v1/amenities/?city={city.slug}")
    assert r.status_code == 503 and r.json()["error"]["code"] == "amenities_unavailable"
    with mock.patch.object(amenities, "_fetch", return_value=OVERPASS):
        client_for().get(f"/api/v1/amenities/?city={city.slug}")
    cache.delete(f"amenities:v1:{city.slug}:{settings.AMENITIES_RADIUS_M}")  # свеж кеш истекол
    with mock.patch.object(amenities, "_fetch", side_effect=TimeoutError):
        stale = client_for().get(f"/api/v1/amenities/?city={city.slug}").json()
    assert stale["stale"] is True and len(stale["items"]) == 4


def test_amenities_requires_known_city(db):
    assert client_for().get("/api/v1/amenities/").status_code == 400
    assert client_for().get("/api/v1/amenities/?city=nowhere").status_code == 404
