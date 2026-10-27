import pytest

from core.exceptions import ServiceError
from gamification import services
from gamification.models import CityAchievement, UserBadge

from .conftest import client_for, jpeg


def test_checkin_within_radius_awards_place_badge(tourist, places):
    p = places["sv-naum"]
    c = client_for(tourist)
    r = c.post(f"/api/v1/places/{p.pk}/checkins/", {"image": jpeg(), "lat": p.lat, "lng": p.lng}, format="multipart")
    assert r.status_code == 201, r.json()
    body = r.json()
    assert body["checkin"]["status"] == "APPROVED"
    codes = {b["code"] for b in body["unlocked_badges"]}
    assert "explorer" in codes and any(code.startswith("place-") for code in codes)
    assert body["city_progress"]["documented_required"] == 1 and body["city_progress"]["required_total"] == 4


def test_far_away_rejected_and_no_gps_pending(tourist, places):
    p = places["kaneo"]
    far, _ = services.create_checkin(tourist, p, jpeg((1, 1, 1)), client_lat=41.99, client_lng=21.43)
    assert far.status == "REJECTED"
    none, unlocked = services.create_checkin(tourist, p, jpeg((2, 2, 2)))
    assert none.status == "PENDING" and unlocked == []


def test_duplicate_photo_rejected(tourist, other_tourist, places):
    p = places["kaneo"]
    services.create_checkin(tourist, p, jpeg((5, 5, 5)), client_lat=p.lat, client_lng=p.lng)
    with pytest.raises(ServiceError) as e:
        services.create_checkin(other_tourist, p, jpeg((5, 5, 5)), client_lat=p.lat, client_lng=p.lng)
    assert e.value.error_code == "duplicate_photo"


def test_progress_counts_unique_places_not_photos(tourist, places):
    p = places["kaneo"]
    for i in range(10):
        services.create_checkin(tourist, p, jpeg((i * 20, 50, 50)), client_lat=p.lat, client_lng=p.lng)
    ach = CityAchievement.objects.get(user=tourist)
    assert ach.documented_required == 1 and ach.percent == 25.0
    assert UserBadge.objects.filter(user=tourist, badge__place=p).count() == 1


def test_city_100_badge(tourist, places):
    for i, slug in enumerate(("sv-naum", "kaneo", "tvrdina", "teatar")):
        p = places[slug]
        services.create_checkin(tourist, p, jpeg((i * 60, 100, 100)), client_lat=p.lat, client_lng=p.lng)
    ach = CityAchievement.objects.get(user=tourist)
    assert ach.percent == 100.0
    assert UserBadge.objects.filter(user=tourist, badge__code="city-ohrid-100").exists()
    assert UserBadge.objects.filter(user=tourist, badge__code="city-ohrid-50").exists()


def test_admin_approves_pending(tourist, admin_user, places):
    p = places["tvrdina"]
    c, _ = services.create_checkin(tourist, p, jpeg((9, 9, 9)))
    r = client_for(admin_user).post(f"/api/v1/admin/checkins/{c.pk}/review/", {"action": "approve"}, format="json")
    assert r.status_code == 200 and r.json()["checkin"]["status"] == "APPROVED"
    assert client_for(tourist).post(f"/api/v1/admin/checkins/{c.pk}/review/", {"action": "approve"}).status_code == 403


def test_gallery_respects_privacy_and_reports(tourist, other_tourist, admin_user, places):
    p = places["kaneo"]
    services.create_checkin(tourist, p, jpeg((7, 7, 7)), client_lat=p.lat, client_lng=p.lng)
    services.create_checkin(other_tourist, p, jpeg((8, 8, 8)), client_lat=p.lat, client_lng=p.lng, is_public=False)
    gallery = client_for().get(f"/api/v1/places/{p.pk}/gallery/").json()
    assert len(gallery["photos"]) == 1 and gallery["badge_holders"] == 2
    photo_id = gallery["photos"][0]["id"]
    client_for(other_tourist).post(f"/api/v1/photos/{photo_id}/report/", {"reason": "несоодветно"}, format="json")
    rep = client_for(admin_user).get("/api/v1/admin/place-reports/").json()[0]
    client_for(admin_user).post(f"/api/v1/admin/place-reports/{rep['id']}/resolve/", {"action": "hide"}, format="json")
    assert client_for().get(f"/api/v1/places/{p.pk}/gallery/").json()["photos"] == []


def test_private_profile(tourist, other_tourist):
    tourist.is_profile_public = False
    tourist.save()
    assert client_for(other_tourist).get("/api/v1/users/ana/").status_code == 403
    assert client_for(tourist).get("/api/v1/users/ana/").status_code == 200
