import threading
from datetime import date, timedelta

import pytest
from django.db import connection

from businesses.models import AccommodationAvailability, BoatDeparture
from core.exceptions import ServiceError
from reservations import services
from reservations.models import Reservation

from .conftest import client_for

D = lambda n: date.today() + timedelta(days=n)


def test_booking_snapshot_price_and_items(tourist, accommodation):
    res = services.create_accommodation_booking(tourist, accommodation, D(3), D(5), 2)
    assert res.status == "PENDING"
    assert res.total_price == 110
    assert res.items.count() == 3
    assert not AccommodationAvailability.objects.filter(unit=accommodation, date__in=[D(3), D(4)],
                                                        available_units__gt=0).exists()


def test_no_double_booking(tourist, other_tourist, accommodation):
    services.create_accommodation_booking(tourist, accommodation, D(3), D(5), 1)
    with pytest.raises(ServiceError):
        services.create_accommodation_booking(other_tourist, accommodation, D(4), D(6), 1)
    assert AccommodationAvailability.objects.get(unit=accommodation, date=D(5)).available_units == 1


def test_checkout_after_checkin_and_capacity(tourist, accommodation):
    with pytest.raises(ServiceError):
        services.create_accommodation_booking(tourist, accommodation, D(5), D(5), 1)
    with pytest.raises(ServiceError):
        services.create_accommodation_booking(tourist, accommodation, D(3), D(4), 3)


def test_idempotency_key_returns_same_reservation(tourist, accommodation):
    a = services.create_accommodation_booking(tourist, accommodation, D(3), D(4), 1, idempotency_key="k1")
    b = services.create_accommodation_booking(tourist, accommodation, D(3), D(4), 1, idempotency_key="k1")
    assert a.pk == b.pk and Reservation.objects.count() == 1


def test_reject_releases_capacity(tourist, owner, accommodation):
    res = services.create_accommodation_booking(tourist, accommodation, D(3), D(4), 1)
    services.transition(res.pk, "REJECTED", owner)
    assert AccommodationAvailability.objects.get(unit=accommodation, date=D(3)).available_units == 1


def test_boat_capacity_and_release(tourist, other_tourist, departure):
    r1 = services.create_boat_reservation(tourist, departure, 3)
    with pytest.raises(ServiceError):
        services.create_boat_reservation(other_tourist, departure, 1)
    services.transition(r1.pk, "CANCELLED", tourist)
    departure.refresh_from_db()
    assert departure.reserved_seats == 0


def test_tourist_cannot_confirm_own_request(tourist, accommodation):
    res = services.create_accommodation_booking(tourist, accommodation, D(3), D(4), 1)
    with pytest.raises(ServiceError):
        services.transition(res.pk, "CONFIRMED", tourist)


def test_completion_not_before_service_end(tourist, owner, accommodation):
    res = services.create_accommodation_booking(tourist, accommodation, D(3), D(4), 1)
    services.transition(res.pk, "CONFIRMED", owner)
    with pytest.raises(ServiceError):
        services.transition(res.pk, "COMPLETED", owner)


def test_business_cannot_see_or_manage_other_business(tourist, other_owner, accommodation):
    res = services.create_accommodation_booking(tourist, accommodation, D(3), D(4), 1)
    c = client_for(other_owner)
    assert c.patch(f"/api/v1/business/reservations/{res.pk}/", {"action": "confirm"}, format="json").status_code == 404
    assert c.get("/api/v1/business/reservations/").json() == []


def test_api_booking_flow(tourist, owner, accommodation):
    c = client_for(tourist)
    r = c.post("/api/v1/accommodation-bookings/", {"unit_id": accommodation.pk, "check_in": str(D(2)),
                                                    "check_out": str(D(4)), "guests": 2}, format="json")
    assert r.status_code == 201, r.json()
    rid = r.json()["id"]
    r = client_for(owner).patch(f"/api/v1/business/reservations/{rid}/", {"action": "confirm"}, format="json")
    assert r.json()["status"] == "CONFIRMED"
    assert client_for(tourist).get("/api/v1/reservations/mine/").json()[0]["status"] == "CONFIRMED"


@pytest.mark.django_db(transaction=True)
@pytest.mark.skipif(connection.vendor == "sqlite", reason="Вистинска конкурентност се тестира на PostgreSQL")
def test_concurrent_last_seats(tourist, other_tourist, departure):
    BoatDeparture.objects.filter(pk=departure.pk).update(capacity=1)
    results = []

    def book(user):
        try:
            services.create_boat_reservation(user, departure, 1)
            results.append("ok")
        except ServiceError:
            results.append("fail")
        finally:
            connection.close()

    threads = [threading.Thread(target=book, args=(u,)) for u in (tourist, other_tourist)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    departure.refresh_from_db()
    assert sorted(results) == ["fail", "ok"] and departure.reserved_seats == 1
