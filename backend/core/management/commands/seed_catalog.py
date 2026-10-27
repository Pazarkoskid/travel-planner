import csv
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import User
from businesses.demo_catalog import BUSINESSES, EXISTING_LOGOS, logo_path
from businesses.models import (
    Accommodation, AccommodationAvailability, AccommodationUnit, Business, RestaurantProfile, TaxiService,
    TransportService,
)
from destinations import accessibility_data
from destinations.models import City, Place

from .seed_demo import CITIES, PASSWORDS, SOURCE, find_csv

DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
HORIZON = 180


def season_price(base, d):
    return Decimal(str(round(base * (1.4 if d.month in (7, 8) else 1.0) * (1.15 if d.weekday() >= 4 else 1.0), 2)))


class Command(BaseCommand):
    help = "Додава/ажурира места и демо бизниси (сместување, такси, автобуси, велосипеди) без бришење."

    def add_arguments(self, parser):
        parser.add_argument("--csv", default=None)

    @transaction.atomic
    def handle(self, *args, **opts):
        cities = {}
        for slug, name, region, lat, lng, desc, wiki in CITIES:
            cities[slug], _ = City.objects.get_or_create(
                slug=slug, defaults={"name": name, "region": region, "center_lat": lat, "center_lng": lng,
                                     "description": desc, "wiki_query": wiki})

        with open(find_csv(opts["csv"]), encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        new_places = 0
        for r in rows:
            _, created = Place.objects.update_or_create(
                city=cities[r["city_slug"]], slug=r["slug"],
                defaults={"name": r["name"], "category": r["category"], "lat": float(r["lat"]),
                          "lng": float(r["lng"]), "visit_duration_min": int(r["visit_duration_min"]),
                          "is_required_landmark": r["is_required_landmark"] == "1", "description": r["description"],
                          "wiki_query": r.get("wiki_query", ""), "source": SOURCE, "status": Place.Status.VERIFIED})
            new_places += created
        accessibility_data.apply(Place)

        host, created = User.objects.get_or_create(username="host", defaults={
            "email": "host@example.com", "role": User.Role.BUSINESS, "first_name": "Host"})
        if created:
            host.set_password(PASSWORDS["host"])
            host.save()

        for name, spec in EXISTING_LOGOS.items():
            Business.objects.filter(name=name, logo="").update(logo=logo_path(spec["slug"]))

        new_biz = 0
        for spec in BUSINESSES:
            b, created = Business.objects.update_or_create(name=spec["name"], defaults={
                "owner": host, "type": spec["type"], "city": cities[spec["city"]], "lat": spec["lat"],
                "lng": spec["lng"], "address": spec.get("address", ""), "phone": spec.get("phone", ""),
                "email": spec.get("email", ""), "website": spec.get("website", ""),
                "description": spec.get("description", ""), "logo": logo_path(spec["slug"]),
                "verification_status": Business.Verification.APPROVED})
            new_biz += created
            if spec["type"] == "ACCOMMODATION":
                self._listings(b, spec["listings"])
            elif spec["type"] == "TAXI":
                TaxiService.objects.update_or_create(business=b, defaults=spec["taxi"])
            elif spec["type"] in ("BUS", "BIKE_RENTAL"):
                TransportService.objects.update_or_create(business=b, defaults=spec["transport"])
            elif spec["type"] == "RESTAURANT":
                r = spec["restaurant"]
                RestaurantProfile.objects.update_or_create(business=b, defaults={
                    "cuisine": r["cuisine"], "price_range": r["price_range"], "max_party_size": r["max_party_size"],
                    "menu": r["menu"], "opening_hours": {d: list(r["hours"]) for d in DAYS}})

        self.stdout.write(self.style.SUCCESS(
            f"Места: {len(rows)} (нови {new_places}). Бизниси од каталогот: {len(BUSINESSES)} (нови {new_biz})."))

    def _listings(self, business, listings):
        today = date.today()
        for item in listings:
            acc, _ = Accommodation.objects.update_or_create(business=business, title=item["title"], defaults={
                "property_type": item["property_type"], "max_guests": item["max_guests"],
                "bedrooms": item["bedrooms"], "beds": item["beds"], "amenities": item["amenities"],
                "rules": item["rules"], "description": item["description"],
                "cleaning_fee": Decimal(str(item["cleaning_fee"])),
                "free_cancellation_days": item["free_cancellation_days"]})
            unit, _ = AccommodationUnit.objects.get_or_create(
                accommodation=acc, defaults={"unit_name": f"{item['title']} ({item['units']} ед.)"})
            have = set(AccommodationAvailability.objects.filter(unit=unit, date__gte=today)
                       .values_list("date", flat=True))
            AccommodationAvailability.objects.bulk_create([
                AccommodationAvailability(unit=unit, date=d, available_units=item["units"],
                                          price_per_night=season_price(item["price"], d))
                for d in (today + timedelta(days=i) for i in range(HORIZON)) if d not in have
            ])
