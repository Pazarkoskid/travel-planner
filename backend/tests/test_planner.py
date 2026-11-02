from datetime import date, timedelta
from unittest import mock

from trips import llm
from trips.models import Trip
from trips.optimizer import optimize_order, route_cost
from trips.planner import generate_plan

from .conftest import client_for


def make_trip(user, city, **kw):
    defaults = dict(start_date=date.today() + timedelta(days=3), days=2, guests=2, budget=200,
                    interests=["history", "religion"], pace="balanced", transport="car")
    defaults.update(kw)
    return Trip.objects.create(user=user, city=city, **defaults)


def test_plan_contains_only_catalog_ids(tourist, city, places):
    trip = make_trip(tourist, city)
    run = generate_plan(trip)
    ids = {p.pk for p in places.values()}
    assert set(run.selected_place_ids) <= ids
    assert run.metrics["optimized_travel_min"] <= run.metrics["baseline_travel_min"] + 1e-6
    assert run.metrics["interest_coverage"] == 1.0
    assert any("работното време" in w for w in trip.warnings)


def test_llm_unknown_ids_are_rejected(tourist, city, places, settings):
    settings.LLM_PROVIDER, settings.ANTHROPIC_API_KEY = "anthropic", "test"
    kaneo = places["kaneo"].pk
    fake = '{"days": [{"day": 1, "place_ids": [%d, 99999]}, {"day": 2, "place_ids": [%d]}]}' % (kaneo, kaneo)
    with mock.patch.object(llm, "call_llm", return_value=fake):
        run = generate_plan(make_trip(tourist, city))
    assert run.provider == "anthropic"
    assert "99999" in run.rejected_ids and 99999 not in run.selected_place_ids
    assert run.selected_place_ids.count(kaneo) == 1


def test_llm_failure_falls_back(tourist, city, places, settings):
    settings.LLM_PROVIDER, settings.ANTHROPIC_API_KEY = "anthropic", "test"
    with mock.patch.object(llm, "call_llm", side_effect=TimeoutError):
        run = generate_plan(make_trip(tourist, city))
    assert run.provider == "rule_based_fallback" and run.selected_place_ids


def test_optimizer_not_worse_than_input_order():
    m = [[0, 5, 50, 10], [5, 0, 45, 6], [50, 45, 0, 40], [10, 6, 40, 0]]
    order = optimize_order(m)
    assert sorted(order) == [1, 2, 3]
    assert route_cost(order, m) <= route_cost([2, 1, 3], m)


def test_trip_api_permissions_and_export(tourist, other_tourist, city, places):
    c = client_for(tourist)
    r = c.post("/api/v1/trips/", {"city": city.pk, "start_date": str(date.today() + timedelta(days=2)), "days": 2,
                                   "guests": 2, "budget": "150", "interests": ["nature"], "pace": "relaxed",
                                   "transport": "car"}, format="json")
    assert r.status_code == 201, r.json()
    tid = r.json()["id"]
    assert c.post(f"/api/v1/trips/{tid}/generate/").status_code == 200
    assert client_for(other_tourist).get(f"/api/v1/trips/{tid}/").status_code == 404
    csv = c.get(f"/api/v1/trips/{tid}/export/?format=csv")
    assert csv.status_code == 200 and "Ден" in csv.content.decode("utf-8-sig")
    rev = c.post(f"/api/v1/trips/{tid}/revise/", {"instructions": "повеќе природа"}, format="json")
    assert "more_nature" in rev.json()["modifiers"]["active"]


def test_trip_validation(tourist, city):
    r = client_for(tourist).post("/api/v1/trips/", {"city": city.pk, "start_date": "2000-01-01", "days": 30,
                                                     "interests": ["xyz"]}, format="json")
    assert r.status_code == 400
    assert set(r.json()["error"]["details"]) >= {"start_date", "days", "interests"}


def test_llm_truncated_json_is_rejected_not_crashing():
    from trips import llm

    result, reasons, rejected, errors = llm.parse_and_validate('Еве план {"days": [', {1, 2}, 2)
    assert result is None and errors == ["Невалиден JSON од моделот"]
