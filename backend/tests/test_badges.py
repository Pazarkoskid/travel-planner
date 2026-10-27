from django.core.management import call_command

from gamification import catalog, services
from gamification.models import Badge, UserBadge

from .conftest import client_for, jpeg


def visit(user, place, color):
    return services.create_checkin(user, place, jpeg(color), client_lat=place.lat, client_lng=place.lng)


def test_catalog_loaded_by_migration(db):
    assert Badge.objects.filter(kind="REGION").count() == len(catalog.LOCATIONS)
    assert Badge.objects.filter(kind="CATEGORY").count() == len(catalog.ACHIEVEMENTS)
    ohrid = Badge.objects.get(code="region-ohrid")
    assert ohrid.art == "/badges/loc-02-ohrid.webp" and ohrid.available
    assert Badge.objects.get(code="region-struga").available is False
    assert Badge.objects.get(code="wine-traveler").available is False


def test_city_and_lake_badges_from_rules(tourist, places):
    _, unlocked = visit(tourist, places["kaneo"], (10, 120, 200))
    codes = {b.code for b in unlocked}
    assert {"region-ohrid", "region-ohrid-lake"} <= codes
    assert "lake-explorer" not in codes


def test_category_badge_needs_distinct_places(tourist, places):
    visit(tourist, places["tvrdina"], (200, 40, 40))
    visit(tourist, places["teatar"], (40, 200, 40))
    assert not UserBadge.objects.filter(user=tourist, badge__code="history-buff").exists()
    for p, c in (("sv-naum", (30, 30, 220)), ("lagadin", (220, 220, 30)), ("galicica", (30, 220, 220))):
        visit(tourist, places[p], c)
    assert not UserBadge.objects.filter(user=tourist, badge__code__in=["history-buff", "nature-explorer"]).exists()


def test_unavailable_badge_never_awarded(tourist, places):
    Badge.objects.filter(code="region-struga").update(rule={"city": "ohrid"})
    visit(tourist, places["kaneo"], (90, 90, 160))
    assert not UserBadge.objects.filter(user=tourist, badge__code="region-struga").exists()


def test_recompute_is_idempotent(tourist, places):
    visit(tourist, places["kaneo"], (15, 160, 90))
    UserBadge.objects.filter(user=tourist, badge__code="region-ohrid").delete()
    call_command("recompute_badges")
    call_command("recompute_badges")
    assert UserBadge.objects.filter(user=tourist, badge__code="region-ohrid").count() == 1


def test_badges_api_exposes_art_and_filter(db):
    rows = client_for().get("/api/v1/badges/?kind=region").json()
    assert len(rows) == len(catalog.LOCATIONS)
    assert rows[0]["art"].startswith("/badges/") and "available" in rows[0]


def test_rule_met_positive_cases():
    from collections import Counter

    stats = {"places": {"ohrid/kej", "ohrid/kaneo", "ohrid/lagadin"}, "cities": {"ohrid"},
             "categories": Counter({"HISTORY": 3, "NATURE": 1}), "photos": 10}
    rules = {code: rule for code, *_x, rule in catalog.ACHIEVEMENTS}
    assert services.rule_met(rules["history-buff"], stats)
    assert services.rule_met(rules["lake-explorer"], stats)
    assert services.rule_met(rules["photographer"], stats)
    assert not services.rule_met(rules["nature-explorer"], stats)
    assert not services.rule_met({}, stats)


def test_place_badge_gets_stamp_art(tourist, places):
    from gamification.models import Badge as B

    _, unlocked = visit(tourist, places["kaneo"], (70, 20, 130))
    assert B.objects.get(code="place-ohrid-kaneo").art == "/badges/stamp-ohrid-kaneo.webp"
    assert catalog.art_for_code("place-ohrid-unknown") == ""


def test_badges_in_english(db):
    rows = client_for().get("/api/v1/badges/?kind=region,category", HTTP_ACCEPT_LANGUAGE="en").json()
    by_code = {r["code"]: r for r in rows}
    assert by_code["region-ohrid-lake"]["name"] == "Lake Ohrid"
    assert by_code["region-ohrid"]["description"] == "City — “Macedonia” collection"
    assert by_code["history-buff"]["name"] == "History Buff"
    mk = client_for().get("/api/v1/badges/?kind=region").json()
    assert {r["code"]: r for r in mk}["region-ohrid-lake"]["name"] == "Охридско Езеро"


def test_weather_passes_language(settings, city):
    from unittest import mock

    from django.core.cache import cache

    from core import weather

    from .test_management import fake_ow

    settings.OPENWEATHER_API_KEY = "test"
    cache.clear()
    with mock.patch.object(weather, "_get", side_effect=fake_ow) as m:
        r = client_for().get(f"/api/v1/weather/?city={city.slug}", HTTP_ACCEPT_LANGUAGE="en").json()
    assert all(call.args[3] == "en" for call in m.call_args_list)
    assert r["location"] == "Ohrid"
