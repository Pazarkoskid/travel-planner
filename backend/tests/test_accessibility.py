from destinations.models import Place
from trips.models import ItineraryItem
from trips.planner import generate_plan

from .conftest import client_for
from .test_planner import make_trip


def set_access(places):
    places["kaneo"].wheelchair = "NO"
    places["tvrdina"].wheelchair = "LIMITED"
    places["tvrdina"].accessibility_notes = "Стрмен успон."
    places["teatar"].wheelchair = "YES"
    for p in places.values():
        p.save()


def test_wheelchair_plan_excludes_inaccessible_and_warns(tourist, city, places):
    set_access(places)
    trip = make_trip(tourist, city, mobility="wheelchair", days=1)
    run = generate_plan(trip)
    assert places["kaneo"].pk not in run.selected_place_ids
    assert any("непристапни" in w and "Канео" in w for w in trip.warnings)
    item = ItineraryItem.objects.filter(day__trip=trip, place=places["tvrdina"]).first()
    if item:  # ако е избрана, мора да има предупредување за делумна пристапност
        assert "Делумно пристапно" in item.warning and "Стрмен успон" in item.warning
    assert run.metrics["accessible_share"] is not None


def test_must_visit_inaccessible_is_kept(tourist, city, places):
    set_access(places)
    trip = make_trip(tourist, city, mobility="wheelchair", days=1)
    trip.must_visit.add(places["kaneo"])
    run = generate_plan(trip)
    assert places["kaneo"].pk in run.selected_place_ids
    item = ItineraryItem.objects.get(day__trip=trip, place=places["kaneo"])
    assert "Непристапно" in item.warning


def test_reduced_mobility_scales_duration(tourist, city, places):
    set_access(places)
    trip = make_trip(tourist, city, mobility="reduced", days=1)
    trip.must_visit.add(places["teatar"])
    generate_plan(trip)
    item = ItineraryItem.objects.get(day__trip=trip, place=places["teatar"])
    minutes = (item.end_time.hour * 60 + item.end_time.minute) - (item.start_time.hour * 60 + item.start_time.minute)
    assert minutes == round(places["teatar"].visit_duration_min * 1.25)


def test_standard_plan_unchanged(tourist, city, places):
    set_access(places)
    trip = make_trip(tourist, city, days=2)
    generate_plan(trip)
    assert not any("непристапни" in w for w in trip.warnings)


def test_places_filter_and_api_fields(places):
    set_access(places)
    rows = client_for().get("/api/v1/places/?accessible=1").json()
    rows = rows["results"] if isinstance(rows, dict) else rows
    slugs = {r["slug"] for r in rows}
    assert "teatar" in slugs and "tvrdina" in slugs and "kaneo" not in slugs
    assert rows[0]["wheelchair_label"]


def test_trip_api_accepts_mobility(tourist, city):
    from datetime import date, timedelta

    r = client_for(tourist).post("/api/v1/trips/", {
        "city": city.pk, "start_date": str(date.today() + timedelta(days=2)), "days": 1, "guests": 1,
        "interests": ["history"], "mobility": "wheelchair"}, format="json")
    assert r.status_code == 201, r.json()
    assert r.json()["mobility"] == "wheelchair"


def test_seed_accessibility_does_not_override_admin(db):
    from destinations import accessibility_data
    from destinations.models import City

    c = City.objects.create(name="Охрид", slug="ohrid", center_lat=41.1, center_lng=20.8)
    p = Place.objects.create(city=c, slug="kaneo", name="Канео", category="RELIGIOUS", lat=41.1, lng=20.8,
                             source="t", wheelchair="YES")
    accessibility_data.apply(Place)
    p.refresh_from_db()
    assert p.wheelchair == "YES"


def test_trip_pdf_export_mk_and_en(tourist, city, places):
    set_access(places)
    trip = make_trip(tourist, city, mobility="wheelchair", days=2)
    generate_plan(trip)
    c = client_for(tourist)
    for lang in ("mk", "en"):
        r = c.get(f"/api/v1/trips/{trip.pk}/export/?format=pdf", HTTP_ACCEPT_LANGUAGE=lang)
        assert r.status_code == 200 and r["Content-Type"] == "application/pdf"
        assert r.content[:5] == b"%PDF-" and len(r.content) > 5000
    assert client_for().get(f"/api/v1/trips/{trip.pk}/export/?format=pdf").status_code == 401


def test_english_trip_text(tourist, city, places):
    set_access(places)
    trip = make_trip(tourist, city, mobility="wheelchair", days=1)
    generate_plan(trip)
    data = client_for(tourist).get(f"/api/v1/trips/{trip.pk}/", HTTP_ACCEPT_LANGUAGE="en").json()
    assert any(w.startswith("Left out as not accessible") for w in data["warnings"])
    assert any(w.startswith("Accessible mode") for w in data["warnings"])
    assert data["itinerary_days"][0]["notes"].startswith("Start: centre of Ohrid")
    reasons = [i["reason"] for d in data["itinerary_days"] for i in d["items"]]
    assert not any("одговара на интересот" in r for r in reasons)
