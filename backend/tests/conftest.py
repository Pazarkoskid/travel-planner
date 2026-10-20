import io
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient

from accounts.models import User
from businesses.models import (
    Accommodation, AccommodationAvailability, AccommodationUnit, BoatDeparture, BoatTour, Business,
)
from destinations.models import City, Place


@pytest.fixture(autouse=True)
def _clear_cache(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"
    cache.clear()


def make_user(username, role="TOURIST"):
    return User.objects.create_user(username=username, email=f"{username}@t.mk", password="Test12345!x", role=role)


@pytest.fixture
def tourist(db):
    return make_user("ana")


@pytest.fixture
def other_tourist(db):
    return make_user("boban")


@pytest.fixture
def owner(db):
    return make_user("owner", "BUSINESS")


@pytest.fixture
def other_owner(db):
    return make_user("owner2", "BUSINESS")


@pytest.fixture
def admin_user(db):
    return make_user("moderator", "ADMIN")


def client_for(user=None):
    c = APIClient()
    if user:
        c.force_authenticate(user)
    return c


@pytest.fixture
def city(db):
    return City.objects.create(name="Охрид", slug="ohrid", center_lat=41.1172, center_lng=20.8016)


@pytest.fixture
def places(city):
    data = [
        ("sv-naum", "Св. Наум", "RELIGIOUS", 40.9137, 20.7406, True),
        ("kaneo", "Канео", "RELIGIOUS", 41.1110, 20.7883, True),
        ("tvrdina", "Самуилова тврдина", "HISTORY", 41.1153, 20.7958, True),
        ("teatar", "Антички театар", "HISTORY", 41.1147, 20.7991, True),
        ("lagadin", "Лагадин", "BEACH", 41.0560, 20.7880, False),
        ("galicica", "Галичица", "VIEWPOINT", 40.9890, 20.8180, False),
    ]
    return {slug: Place.objects.create(city=city, slug=slug, name=n, category=c, lat=lat, lng=lng, source="test",
                                       status="VERIFIED", is_required_landmark=req)
            for slug, n, c, lat, lng, req in data}


@pytest.fixture
def accommodation(owner, city):
    b = Business.objects.create(owner=owner, name="Вила", type="ACCOMMODATION", city=city, lat=41.11, lng=20.79,
                                verification_status="APPROVED")
    acc = Accommodation.objects.create(business=b, title="Соба", property_type="ROOM", max_guests=2,
                                       cleaning_fee=Decimal("10"))
    unit = AccommodationUnit.objects.create(accommodation=acc, unit_name="Соба 1")
    for i in range(30):
        AccommodationAvailability.objects.create(unit=unit, date=date.today() + timedelta(days=i),
                                                 available_units=1, price_per_night=Decimal("50"))
    return unit


@pytest.fixture
def departure(owner, city):
    from django.utils import timezone

    b = Business.objects.create(owner=owner, name="Брод", type="BOAT_TOUR", city=city, lat=41.11, lng=20.80,
                                verification_status="APPROVED")
    tour = BoatTour.objects.create(business=b, title="Тура", route="Охрид—Наум", duration_min=120,
                                   price_per_person=Decimal("15"), departure_point="Пристаниште")
    return BoatDeparture.objects.create(tour=tour, starts_at=timezone.now() + timedelta(days=2), capacity=3)


def jpeg(color=(10, 20, 30)):
    buf = io.BytesIO()
    Image.new("RGB", (32, 32), color).save(buf, format="JPEG")
    return SimpleUploadedFile(f"p{color}.jpg", buf.getvalue(), content_type="image/jpeg")
