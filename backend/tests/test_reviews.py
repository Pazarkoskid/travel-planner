from datetime import date, timedelta

from reservations.models import Reservation

from .conftest import client_for


def completed_reservation(user, unit):
    return Reservation.objects.create(
        user=user, business=unit.accommodation.business, service_type="ACCOMMODATION", accommodation_unit=unit,
        check_in=date.today() - timedelta(days=5), check_out=date.today() - timedelta(days=3), status="COMPLETED")


def test_review_only_after_completed(tourist, accommodation):
    res = Reservation.objects.create(user=tourist, business=accommodation.accommodation.business,
                                     service_type="ACCOMMODATION", status="CONFIRMED")
    r = client_for(tourist).post(f"/api/v1/reservations/{res.pk}/review/", {"rating": 5}, format="json")
    assert r.status_code == 400 and r.json()["error"]["code"] == "not_completed"


def test_one_review_per_reservation_and_verified_badge(tourist, accommodation):
    res = completed_reservation(tourist, accommodation)
    c = client_for(tourist)
    r = c.post(f"/api/v1/reservations/{res.pk}/review/",
               {"rating": 4, "dimension_scores": {"cleanliness": 5}, "comment": "Супер"}, format="json")
    assert r.status_code == 201 and r.json()["is_verified_booking"] is True
    r = c.post(f"/api/v1/reservations/{res.pk}/review/", {"rating": 1}, format="json")
    assert r.status_code == 409


def test_other_user_cannot_review(tourist, other_tourist, accommodation):
    res = completed_reservation(tourist, accommodation)
    r = client_for(other_tourist).post(f"/api/v1/reservations/{res.pk}/review/", {"rating": 5}, format="json")
    assert r.status_code == 403


def test_invalid_dimension_rejected(tourist, accommodation):
    res = completed_reservation(tourist, accommodation)
    r = client_for(tourist).post(f"/api/v1/reservations/{res.pk}/review/",
                                 {"rating": 5, "dimension_scores": {"food": 5}}, format="json")
    assert r.status_code == 400


def test_owner_replies_but_cannot_edit_and_admin_moderates(tourist, owner, other_tourist, admin_user, accommodation):
    res = completed_reservation(tourist, accommodation)
    rid = client_for(tourist).post(f"/api/v1/reservations/{res.pk}/review/", {"rating": 2, "comment": "Лошо"},
                                   format="json").json()["id"]
    r = client_for(owner).post(f"/api/v1/reviews/{rid}/reply/", {"reply_text": "Извинете"}, format="json")
    assert r.status_code == 200
    assert client_for(owner).patch(f"/api/v1/reviews/{rid}/", {"rating": 5}, format="json").status_code in (404, 405)
    client_for(other_tourist).post(f"/api/v1/reviews/{rid}/report/", {"reason": "спам"}, format="json")
    rep = client_for(admin_user).get("/api/v1/admin/review-reports/").json()[0]
    client_for(admin_user).post(f"/api/v1/admin/review-reports/{rep['id']}/resolve/", {"action": "hide"}, format="json")
    biz = accommodation.accommodation.business_id
    assert client_for().get(f"/api/v1/businesses/{biz}/reviews/").json() == []
