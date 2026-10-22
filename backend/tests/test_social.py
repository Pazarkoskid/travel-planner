import pytest

from accounts.models import User
from notifications.models import Notification
from social.models import Friendship

from .conftest import client_for


@pytest.fixture
def ana(db):
    return User.objects.create_user("marija", "marija@example.com", "Marija123!x", first_name="Марија", last_name="Петрова")


@pytest.fixture
def hidden(db):
    return User.objects.create_user("skrien", "s@example.com", "Skrien123!", first_name="Марија", is_profile_public=False)


def test_search_by_username_and_name_excludes_self_and_private(tourist, ana, hidden):
    c = client_for(tourist)
    by_name = c.get("/api/v1/people/search/?q=Марија").json()
    assert [r["username"] for r in by_name] == ["marija"]  # приватниот профил не се гледа
    assert by_name[0]["relation"] == "none" and by_name[0]["name"] == "Марија Петрова"
    assert c.get("/api/v1/people/search/?q=a").json() == []  # минимум 2 знаци
    assert tourist.username not in [r["username"] for r in c.get(f"/api/v1/people/search/?q={tourist.username}").json()]
    assert client_for().get("/api/v1/people/search/?q=ana").status_code == 401


def test_request_accept_flow_and_notifications(tourist, ana):
    r = client_for(tourist).post("/api/v1/friends/requests/", {"username": "marija"}, format="json")
    assert r.status_code == 201 and r.json()["relation"] == "outgoing"
    assert Notification.objects.filter(user=ana, type="friend").exists()
    # двојно барање е одбиено
    assert client_for(tourist).post("/api/v1/friends/requests/", {"username": "marija"}, format="json").status_code == 409
    lists = client_for(ana).get("/api/v1/friends/").json()
    req_id = lists["incoming"][0]["request_id"]
    # испраќачот не може сам да прифати
    assert client_for(tourist).post(f"/api/v1/friends/requests/{req_id}/accept/").status_code == 404
    assert client_for(ana).post(f"/api/v1/friends/requests/{req_id}/accept/").json()["relation"] == "friends"
    assert client_for(tourist).get("/api/v1/friends/").json()["friends"][0]["username"] == "marija"
    assert Notification.objects.filter(user=tourist, type="friend").exists()


def test_mutual_request_becomes_friendship(tourist, ana):
    client_for(ana).post("/api/v1/friends/requests/", {"username": tourist.username}, format="json")
    r = client_for(tourist).post("/api/v1/friends/requests/", {"username": "marija"}, format="json")
    assert r.status_code == 200 and r.json()["relation"] == "friends"
    assert Friendship.objects.count() == 1


def test_decline_remove_and_self(tourist, ana):
    c = client_for(tourist)
    assert c.post("/api/v1/friends/requests/", {"username": tourist.username}, format="json").status_code == 400
    c.post("/api/v1/friends/requests/", {"username": "marija"}, format="json")
    fid = Friendship.objects.get().pk
    assert client_for(ana).post(f"/api/v1/friends/requests/{fid}/decline/").status_code == 200
    assert not Friendship.objects.exists()
    c.post("/api/v1/friends/requests/", {"username": "marija"}, format="json")
    assert c.delete("/api/v1/friends/marija/").status_code == 204  # откажано барање
    assert c.delete("/api/v1/friends/marija/").status_code == 404


def test_private_profile_visible_to_friends_only(tourist, ana, hidden):
    assert client_for(tourist).post("/api/v1/friends/requests/", {"username": "skrien"}, format="json").status_code == 403
    assert client_for(tourist).get("/api/v1/users/skrien/").status_code == 403
    # skrien сам испраќа барање → по прифаќање, туристот го гледа профилот
    client_for(hidden).post("/api/v1/friends/requests/", {"username": tourist.username}, format="json")
    fid = Friendship.objects.get(to_user=tourist).pk
    client_for(tourist).post(f"/api/v1/friends/requests/{fid}/accept/")
    prof = client_for(tourist).get("/api/v1/users/skrien/")
    assert prof.status_code == 200 and prof.json()["relation"] == "friends"
    assert client_for(ana).get("/api/v1/users/skrien/").status_code == 403
    found = client_for(tourist).get("/api/v1/people/search/?q=skrien").json()
    assert found[0]["relation"] == "friends"  # пријателите се наоѓаат и со приватен профил


def test_friend_notification_in_english(tourist, ana):
    client_for(tourist).post("/api/v1/friends/requests/", {"username": "marija"}, format="json")
    rows = client_for(ana).get("/api/v1/notifications/", HTTP_ACCEPT_LANGUAGE="en").json()
    rows = rows["results"] if isinstance(rows, dict) else rows
    assert rows[0]["title"] == f"New friend request from {tourist.username}"


def test_seed_community_realistic_and_idempotent(db, settings, tmp_path):
    from django.core.management import call_command

    from gamification.models import PhotoLike, PlacePhoto
    from reviews.models import BusinessReply, Review

    settings.MEDIA_ROOT = tmp_path
    call_command("seed_demo")
    call_command("seed_community")
    assert User.objects.filter(email__endswith="@demo.example.com").count() == 8
    photos = PlacePhoto.objects.filter(user__email__endswith="@demo.example.com")
    assert photos.count() >= 30 and all("Демо фотографија" in p.caption for p in photos)
    assert PhotoLike.objects.exists()
    reviews = Review.objects.filter(user__email__endswith="@demo.example.com")
    assert reviews.count() == 9 and all(r.reservation.status == "COMPLETED" for r in reviews)
    assert BusinessReply.objects.filter(review__in=reviews).exists()
    turist = User.objects.get(username="turist")
    lists = client_for(turist).get("/api/v1/friends/").json()
    assert len(lists["friends"]) == 3 and len(lists["incoming"]) == 1 and len(lists["outgoing"]) == 1
    call_command("seed_community")  # втор пат не дуплира
    assert User.objects.filter(email__endswith="@demo.example.com").count() == 8
    call_command("seed_community", "--reset")
    assert Review.objects.filter(user__email__endswith="@demo.example.com").count() == 9


def test_photo_likes(tourist, other_tourist, places, settings, tmp_path):
    from gamification import services
    from gamification.models import PlacePhoto

    from .conftest import jpeg

    settings.MEDIA_ROOT = tmp_path
    p = places["kaneo"]
    services.create_checkin(other_tourist, p, jpeg((12, 34, 56)), client_lat=p.lat, client_lng=p.lng)
    photo = PlacePhoto.objects.get()
    c = client_for(tourist)
    r = c.post(f"/api/v1/photos/{photo.pk}/like/")
    assert r.json() == {"id": photo.pk, "like_count": 1, "liked_by_me": True}
    c.post(f"/api/v1/photos/{photo.pk}/like/")  # двоен лајк не се брои
    assert Notification.objects.filter(user=other_tourist, type="photo_like").count() == 1
    gallery = c.get(f"/api/v1/places/{p.pk}/gallery/").json()["photos"][0]
    assert gallery["like_count"] == 1 and gallery["liked_by_me"] is True
    assert client_for().get(f"/api/v1/places/{p.pk}/gallery/").json()["photos"][0]["liked_by_me"] is False
    assert c.delete(f"/api/v1/photos/{photo.pk}/like/").json()["like_count"] == 0
    assert client_for().post(f"/api/v1/photos/{photo.pk}/like/").status_code == 401
    photo.is_public = False
    photo.save()
    assert c.post(f"/api/v1/photos/{photo.pk}/like/").status_code == 404  # приватна фотографија

