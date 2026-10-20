from datetime import timedelta
from unittest import mock

import pytest
from django.core.cache import cache
from django.utils import timezone

from businesses.models import BoatDeparture, Business, TaxiService
from core import weather
from reservations import services

from .conftest import client_for


# --- Уредување од бизнис ------------------------------------------------------

def test_owner_edits_own_tour_but_not_others(owner, other_owner, departure):
    tour = departure.tour
    payload = {"description": "Нов опис", "stops": [
        {"name": "Пристаниште", "minutes": 0}, {"name": "Св. Наум", "minutes": 90, "stop_min": 120, "note": "Пауза"}]}
    r = client_for(owner).patch(f"/api/v1/business/boat-tours/{tour.pk}/", payload, format="json")
    assert r.status_code == 200, r.json()
    assert r.json()["stops"][1]["name"] == "Св. Наум"
    r = client_for(other_owner).patch(f"/api/v1/business/boat-tours/{tour.pk}/", {"description": "x"}, format="json")
    assert r.status_code == 404


def test_tour_stops_must_be_in_time_order(owner, departure):
    r = client_for(owner).patch(f"/api/v1/business/boat-tours/{departure.tour.pk}/", {"stops": [
        {"name": "Б", "minutes": 90}, {"name": "А", "minutes": 10}]}, format="json")
    assert r.status_code == 400


def test_owner_cannot_self_verify_or_sponsor(owner, departure):
    b = departure.tour.business
    client_for(owner).patch(f"/api/v1/business/my/{b.pk}/", {"verification_status": "APPROVED", "is_sponsored": True,
                                                             "phone": "+389 00 111 222"}, format="json")
    b.refresh_from_db()
    assert b.phone == "+389 00 111 222" and b.is_sponsored is False


def test_new_business_starts_pending(owner, city):
    r = client_for(owner).post("/api/v1/business/my/", {"name": "Ново такси", "type": "TAXI", "city": city.pk,
                                                        "lat": 41.11, "lng": 20.80}, format="json")
    assert r.status_code == 201, r.json()
    assert r.json()["verification_status"] == "PENDING"
    assert TaxiService.objects.filter(business_id=r.json()["id"]).exists()


def test_tourist_cannot_create_business(tourist, city):
    r = client_for(tourist).post("/api/v1/business/my/", {"name": "X", "type": "TAXI", "city": city.pk,
                                                          "lat": 41.1, "lng": 20.8}, format="json")
    assert r.status_code == 403


def test_restaurant_hours_validation(owner, city):
    b = Business.objects.create(owner=owner, name="Р", type="RESTAURANT", city=city, lat=41.1, lng=20.8,
                                verification_status="APPROVED")
    c = client_for(owner)
    assert c.patch(f"/api/v1/business/my/{b.pk}/restaurant/", {"opening_hours": {"mon": ["25:00", "23:00"]}},
                   format="json").status_code == 400
    r = c.patch(f"/api/v1/business/my/{b.pk}/restaurant/", {"opening_hours": {"mon": ["10:00", "22:00"], "sun": "closed"},
                                                            "menu": [{"name": "Пастрмка", "price": 12}]}, format="json")
    assert r.status_code == 200 and r.json()["menu"][0]["price"] == 12


def test_cancel_departure_releases_and_rejects(tourist, owner, departure):
    res = services.create_boat_reservation(tourist, departure, 2)
    r = client_for(owner).post(f"/api/v1/business/departures/{departure.pk}/cancel/")
    assert r.status_code == 200 and r.json()["status"] == "CANCELLED"
    res.refresh_from_db()
    departure.refresh_from_db()
    assert res.status == "REJECTED" and departure.reserved_seats == 0


# --- Администраторски каталог -------------------------------------------------

def test_admin_sets_price_and_hours_marks_verified(admin_user, places):
    p = places["kaneo"]
    r = client_for(admin_user).patch(f"/api/v1/admin/places/{p.pk}/", {"price_eur": "3.00", "opening_time": "09:00",
                                                                     "closing_time": "19:00"}, format="json")
    assert r.status_code == 200, r.json()
    assert r.json()["verified_at"] == str(timezone.localdate())
    pub = client_for().get(f"/api/v1/places/{p.pk}/").json()
    assert pub["price_eur"] == "3.00" and pub["opening_time"] == "09:00:00"


def test_admin_hours_validation_and_permissions(admin_user, owner, places):
    p = places["kaneo"]
    bad = client_for(admin_user).patch(f"/api/v1/admin/places/{p.pk}/", {"opening_time": "18:00", "closing_time": "09:00"},
                                       format="json")
    assert bad.status_code == 400
    assert client_for(owner).patch(f"/api/v1/admin/places/{p.pk}/", {"price_eur": "1"}, format="json").status_code == 403


# --- Детали за огласи ---------------------------------------------------------

def test_public_detail_pages(owner, city, departure):
    taxi = Business.objects.create(owner=owner, name="Такси", type="TAXI", city=city, lat=41.1, lng=20.8,
                                   phone="+389 00 000 000", verification_status="APPROVED")
    TaxiService.objects.create(business=taxi, service_area="Охрид", available_24h=True)
    t = client_for().get(f"/api/v1/taxi-services/{taxi.pk}/").json()
    assert t["business"]["phone"] == "+389 00 000 000" and t["available_24h"] is True
    for i in range(15):
        BoatDeparture.objects.create(tour=departure.tour, starts_at=timezone.now() + timedelta(days=3, hours=i), capacity=5)
    detail = client_for().get(f"/api/v1/boat-tours/{departure.tour.pk}/").json()
    listing = client_for().get("/api/v1/boat-tours/").json()
    rows = listing["results"] if isinstance(listing, dict) else listing
    assert len(detail["upcoming_departures"]) == 16 and len(rows[0]["upcoming_departures"]) == 10


# --- Временска прогноза -------------------------------------------------------

def fake_ow(path, lat, lng):
    if path == "weather":
        return {"main": {"temp": 21.4, "feels_like": 20.8, "humidity": 55}, "wind": {"speed": 3},
                "weather": [{"icon": "01d", "description": "ведро"}]}
    base = int(timezone.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
    items = [{"dt": base + h * 3600, "main": {"temp_min": 10 + h / 3, "temp_max": 12 + h / 3},
              "weather": [{"icon": "02n", "description": "малку облачно"}], "wind": {"speed": 2}, "pop": 0.2}
             for h in range(0, 48, 3)]
    return {"city": {"timezone": 7200}, "list": items}


def test_weather_without_key_is_clear_error(settings, city):
    settings.OPENWEATHER_API_KEY = ""
    r = client_for().get(f"/api/v1/weather/?city={city.slug}")
    assert r.status_code == 503 and r.json()["error"]["code"] == "weather_not_configured"


def test_weather_summary_and_cache(settings, city):
    settings.OPENWEATHER_API_KEY = "test"
    cache.clear()
    with mock.patch.object(weather, "_get", side_effect=fake_ow) as m:
        r1 = client_for().get(f"/api/v1/weather/?city={city.slug}").json()
        client_for().get(f"/api/v1/weather/?city={city.slug}")
    assert m.call_count == 2  # втор повик од кеш
    assert r1["current"]["temp"] == 21 and r1["location"] == "Охрид"
    assert r1["daily"][0]["icon"].endswith("d") and r1["daily"][0]["pop"] == 20


def test_weather_rejects_location_outside_country(settings):
    settings.OPENWEATHER_API_KEY = "test"
    assert client_for().get("/api/v1/weather/?lat=48.2&lng=16.3").status_code == 400


@pytest.mark.parametrize("err", [TimeoutError, ValueError])
def test_weather_upstream_errors(settings, city, err):
    settings.OPENWEATHER_API_KEY = "test"
    cache.clear()
    with mock.patch.object(weather, "_get", side_effect=err):
        r = client_for().get(f"/api/v1/weather/?city={city.pk}")
    assert r.status_code == 503 and r.json()["error"]["code"] == "weather_unavailable"
