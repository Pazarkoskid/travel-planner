from django.core.management import call_command

from businesses.demo_catalog import BUSINESSES
from businesses.models import Accommodation, Business, TransportService
from destinations.models import Place

from .conftest import client_for


def test_seed_catalog_is_idempotent_and_covers_all_cities(db):
    call_command("seed_catalog")
    call_command("seed_catalog")
    assert Business.objects.filter(name__in=[b["name"] for b in BUSINESSES]).count() == len(BUSINESSES)
    for city in ("ohrid", "skopje", "bitola"):
        types = set(Business.objects.filter(city__slug=city).values_list("type", flat=True))
        assert {"ACCOMMODATION", "TAXI", "BUS", "BIKE_RENTAL"} <= types
        assert Place.objects.filter(city__slug=city).count() >= 12
    logos = list(Business.objects.filter(name__in=[b["name"] for b in BUSINESSES]).values_list("logo", flat=True))
    assert all(logos) and len(set(logos)) == len(logos)
    acc = Accommodation.objects.get(title="Апартман со поглед на Вардар")
    assert acc.units.get().availability.count() == 180


def test_transport_api_filters_and_detail(db):
    call_command("seed_catalog")
    c = client_for()
    bikes = c.get("/api/v1/transport-services/?city=skopje&type=BIKE_RENTAL").json()
    bikes = bikes["results"] if isinstance(bikes, dict) else bikes
    assert len(bikes) == 2 and all(b["rentals"] for b in bikes)
    bus = TransportService.objects.get(business__name="Градски линии Скопје (демо)")
    detail = c.get(f"/api/v1/transport-services/{bus.business_id}/").json()
    assert detail["business"]["logo"] == "/logos/skopje-gradski-linii.svg"
    assert {line["code"] for line in detail["lines"]} >= {"2", "60"}


def test_accommodation_search_finds_new_cities(db):
    call_command("seed_catalog")
    from datetime import date, timedelta

    ci = date.today() + timedelta(days=10)
    res = client_for().get(f"/api/v1/accommodations/?city=bitola&check_in={ci}&check_out={ci + timedelta(days=2)}&guests=2").json()
    assert len(res) >= 3 and all(r["quote"] for r in res)
