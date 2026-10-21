"""Демо податоци: градови, места од data/seed_places.csv, демо бизниси, корисници и беџови.

    python manage.py seed_demo            # идемпотентно
    python manage.py seed_demo --reset    # брише демо бизниси/резервации пред повторно полнење
    python manage.py seed_demo --if-empty # само ако базата е празна (се користи при deploy на Render)

SEED_ADMIN_PASSWORD (env) ја заменува демо лозинката на admin при прво креирање — задолжително за јавен deploy.
"""
import csv
import io
import os
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from PIL import Image

from accounts.models import User
from businesses.models import (
    Accommodation, AccommodationAvailability, AccommodationUnit, BoatDeparture, BoatTour, Business,
    RestaurantProfile, TaxiService,
)
from destinations.models import City, Place
from gamification import services as gamification
from gamification.models import PhotoCheckIn
from reservations.models import Reservation, ReservationItem, ReservationStatusHistory
from reviews.models import Review

CITIES = [
    ("ohrid", "Охрид", "Југозападен", 41.1172, 20.8016, "Град на Охридското Езеро, под заштита на УНЕСКО.", "Ohrid"),
    ("skopje", "Скопје", "Скопски", 41.9973, 21.4280, "Главен град, стара чаршија и кањонот Матка.", "Skopje"),
    ("bitola", "Битола", "Пелагониски", 41.0314, 21.3347, "Широк сокак, Хераклеја и Пелистер.", "Bitola"),
]
SOURCE = "Демо seed (OpenStreetMap, приближни координати) — потребна проверка"
PASSWORDS = {"admin": "Admin12345!", "host": "Host12345!", "turist": "Turist12345!"}


def find_csv(explicit):
    candidates = [explicit, os.environ.get("SEED_CSV"),
                  Path(settings.BASE_DIR).parent / "data" / "seed_places.csv",
                  Path(settings.BASE_DIR) / "data" / "seed_places.csv", Path("/data/seed_places.csv")]
    for c in candidates:
        if c and Path(c).exists():
            return Path(c)
    raise CommandError("Не е пронајден seed_places.csv (користи --csv).")


def demo_image(color):
    buf = io.BytesIO()
    Image.new("RGB", (64, 48), color).save(buf, format="JPEG")
    return SimpleUploadedFile(f"demo-{color[0]}-{color[1]}-{color[2]}.jpg", buf.getvalue(), content_type="image/jpeg")


class Command(BaseCommand):
    help = "Полни демо податоци за развој и презентација."

    def add_arguments(self, parser):
        parser.add_argument("--csv", default=None)
        parser.add_argument("--reset", action="store_true")
        parser.add_argument("--if-empty", action="store_true", help="Прескокни ако веќе има градови во базата")

    @transaction.atomic
    def handle(self, *args, **opts):
        if opts["if_empty"] and City.objects.exists():
            self.stdout.write("Базата веќе има податоци — seed е прескокнат.")
            return
        if opts["reset"]:
            Review.objects.all().delete()
            Reservation.objects.all().delete()
            Business.objects.filter(name__endswith="(демо)").delete()
            PhotoCheckIn.objects.filter(user__username="turist").delete()

        cities = {}
        for slug, name, region, lat, lng, desc, wiki in CITIES:
            cities[slug], _ = City.objects.update_or_create(
                slug=slug, defaults={"name": name, "region": region, "center_lat": lat, "center_lng": lng,
                                     "description": desc, "wiki_query": wiki})

        with open(find_csv(opts["csv"]), encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        for r in rows:
            Place.objects.update_or_create(
                city=cities[r["city_slug"]], slug=r["slug"],
                defaults={"name": r["name"], "category": r["category"], "lat": float(r["lat"]),
                          "lng": float(r["lng"]), "visit_duration_min": int(r["visit_duration_min"]),
                          "is_required_landmark": r["is_required_landmark"] == "1", "description": r["description"],
                          "wiki_query": r.get("wiki_query", ""),
                          "source": SOURCE, "status": Place.Status.VERIFIED})
        self.stdout.write(f"Места: {len(rows)}")

        users = {}
        for username, role in (("admin", User.Role.ADMIN), ("host", User.Role.BUSINESS), ("turist", User.Role.TOURIST)):
            u, created = User.objects.get_or_create(username=username, defaults={
                "email": f"{username}@example.com", "role": role, "first_name": username.capitalize(),
                "is_staff": role == User.Role.ADMIN, "is_superuser": role == User.Role.ADMIN})
            if created:
                pw = os.environ.get("SEED_ADMIN_PASSWORD") if username == "admin" else None
                u.set_password(pw or PASSWORDS[username])
                u.save()
            users[username] = u
        users["turist"].bio = "Сакам езера, манастири и добра храна."
        users["turist"].save(update_fields=["bio"])

        ohrid = cities["ohrid"]
        host = users["host"]
        approved = Business.Verification.APPROVED

        def biz(name, type_, lat, lng, **extra):
            b, _ = Business.objects.update_or_create(
                name=name, defaults={"owner": host, "type": type_, "city": extra.pop("city", ohrid), "lat": lat,
                                     "lng": lng, "verification_status": extra.pop("status", approved), **extra})
            return b

        vila = biz("Вила Езерски Поглед (демо)", "ACCOMMODATION", 41.1118, 20.7960,
                   address="Стар град, Охрид", description="Демо објект со поглед на езерото.")
        apt = biz("Апартмани Стар Град (демо)", "ACCOMMODATION", 41.1150, 20.8030, address="Чаршија, Охрид",
                  description="Демо апартмани до чаршијата.")
        rest = biz("Ресторан Крајбрежје (демо)", "RESTAURANT", 41.1120, 20.7930, description="Демо ресторан.")
        boat = biz("Охридски бродски тури (демо)", "BOAT_TOUR", 41.1132, 20.8008, description="Демо бродски тури.")
        taxi = biz("Охрид Такси (демо)", "TAXI", 41.1172, 20.8016, description="Демо такси служба.")
        biz("Хотел Нова понуда (демо)", "ACCOMMODATION", 41.1200, 20.8000, status=Business.Verification.PENDING,
            description="Чека одобрување од администратор.")

        acc1, _ = Accommodation.objects.update_or_create(business=vila, title="Двокреветна соба со тераса", defaults={
            "property_type": "ROOM", "max_guests": 2, "bedrooms": 1, "beds": 1,
            "amenities": ["wifi", "ac", "terrace", "lake_view"], "cleaning_fee": Decimal("0"),
            "rules": "Check-in 14:00, check-out 10:00. Без пушење."})
        acc2, _ = Accommodation.objects.update_or_create(business=apt, title="Семеен апартман", defaults={
            "property_type": "APARTMENT", "max_guests": 4, "bedrooms": 2, "beds": 3,
            "amenities": ["wifi", "ac", "parking", "kitchen"], "cleaning_fee": Decimal("15"),
            "rules": "Check-in 15:00, check-out 11:00."})
        u1, _ = AccommodationUnit.objects.get_or_create(accommodation=acc1, unit_name="Соби со тераса (3 единици)")
        u2, _ = AccommodationUnit.objects.get_or_create(accommodation=acc2, unit_name="Апартман 1")
        today = date.today()
        for unit, units, base in ((u1, 3, 45), (u2, 1, 70)):
            for i in range(180):
                d = today + timedelta(days=i)
                price = base * (1.4 if d.month in (7, 8) else 1.0) * (1.15 if d.weekday() >= 4 else 1.0)
                AccommodationAvailability.objects.get_or_create(
                    unit=unit, date=d, defaults={"available_units": units,
                                                 "price_per_night": Decimal(str(round(price, 2)))})

        RestaurantProfile.objects.update_or_create(business=rest, defaults={
            "opening_hours": {d: ["11:00", "23:00"] for d in ("mon", "tue", "wed", "thu", "fri", "sat", "sun")},
            "menu": [{"name": "Охридска пастрмка (демо цена)", "price": 14}, {"name": "Тавче гравче", "price": 5}],
            "price_range": "€€", "cuisine": "Македонска, риба од езерото", "max_party_size": 12})
        tour, _ = BoatTour.objects.update_or_create(business=boat, title="Охрид — Св. Наум со брод", defaults={
            "route": "Пристаниште Охрид → Св. Наум → Охрид", "duration_min": 300,
            "price_per_person": Decimal("15"), "departure_point": "Пристаниште Охрид",
            "rules": "Деца до 6 години бесплатно; јакна при лошо време.",
            "description": "Демо тура: крстарење по источниот брег на Охридското Езеро до манастирот Св. Наум, "
                           "со слободно време за посета на манастирот и изворите на Црн Дрим.",
            "includes": "Возење со брод во двата правци, водич на брод (македонски и англиски).",
            "stops": [
                {"name": "Пристаниште Охрид", "minutes": 0, "stop_min": 0, "lat": 41.1132, "lng": 20.8008, "note": "Поаѓање"},
                {"name": "Залив на коските", "minutes": 45, "stop_min": 10, "lat": 41.0130, "lng": 20.8030,
                 "note": "Кратка пауза за фотографии од бродот"},
                {"name": "Св. Наум", "minutes": 90, "stop_min": 150, "lat": 40.9137, "lng": 20.7406,
                 "note": "Слободно време: манастир, извори, ручек"},
                {"name": "Пристаниште Охрид", "minutes": 300, "stop_min": 0, "lat": 41.1132, "lng": 20.8008, "note": "Враќање"},
            ]})
        tz = timezone.get_current_timezone()
        for i in range(1, 31):
            for hour in (10, 15):
                starts = timezone.make_aware(datetime.combine(today + timedelta(days=i), time(hour, 0)), tz)
                BoatDeparture.objects.get_or_create(tour=tour, starts_at=starts, defaults={"capacity": 20})
        TaxiService.objects.update_or_create(business=taxi, defaults={
            "service_area": "Охрид, Струга и аеродром Охрид", "passenger_capacity": 4, "available_24h": True,
            "vehicles": "Седан и комбе до 8 лица (демо)", "languages": "македонски, англиски",
            "fare_info": "Демо податоци: цената ја потврдува операторот со понуда пред возењето."})
        Business.objects.filter(pk=taxi.pk).update(phone="+389 00 000 000", email="taxi-demo@example.com")
        Business.objects.filter(pk=boat.pk).update(phone="+389 00 000 001")
        Business.objects.filter(pk=rest.pk).update(phone="+389 00 000 002", address="Кеј, Охрид")

        # Завршена резервација во минатото → демонстрира рецензија „Проверена резервација“.
        turist = users["turist"]
        if not Reservation.objects.filter(user=turist, status="COMPLETED").exists():
            ci, co = today - timedelta(days=10), today - timedelta(days=7)
            res = Reservation.objects.create(
                user=turist, business=vila, service_type="ACCOMMODATION", accommodation_unit=u1, check_in=ci,
                check_out=co, guests=2, total_price=Decimal("135"), status="COMPLETED",
                confirmed_at=timezone.now() - timedelta(days=12), completed_at=timezone.now() - timedelta(days=7))
            ReservationItem.objects.create(reservation=res, description="3 ноќи (демо)", quantity=3,
                                           unit_price=Decimal("45"), total_price=Decimal("135"))
            for a, b in (("", "PENDING"), ("PENDING", "CONFIRMED"), ("CONFIRMED", "COMPLETED")):
                ReservationStatusHistory.objects.create(reservation=res, from_status=a, to_status=b, actor=host)
            # Демо рецензија (тест-податок) за да се види приказот на проверени рецензии.
            Review.objects.create(user=turist, business=vila, reservation=res, rating=5,
                                  dimension_scores={"cleanliness": 5, "location": 5, "comfort": 4, "value": 5},
                                  comment="Демо рецензија: тераса со поглед на езерото и мирна улица во стариот град.")

        # Беџови + 3 фото-посети во Охрид → „3 од 10“ (30%) како во спецификацијата.
        gamification.ensure_global_badges()
        for city in cities.values():
            gamification.ensure_city_badges(city)
            for place in city.places.filter(is_required_landmark=True):
                gamification.ensure_place_badge(place)
        from gamification import catalog
        from gamification.models import Badge

        catalog.sync_catalog(Badge)
        if not PhotoCheckIn.objects.filter(user=turist).exists():
            for i, slug in enumerate(("sv-naum", "kaneo", "samoilova-tvrdina")):
                p = Place.objects.get(city=ohrid, slug=slug)
                gamification.create_checkin(turist, p, demo_image((40 + i * 60, 120, 200 - i * 50)),
                                            client_lat=p.lat, client_lng=p.lng, caption=f"Посета на {p.name}")

        self.stdout.write("Фотографии: python manage.py fetch_images (потребен е интернет).")
        self.stdout.write(self.style.SUCCESS(
            "Демо податоците се подготвени. Корисници: admin / host / turist (лозинки во README)."))
