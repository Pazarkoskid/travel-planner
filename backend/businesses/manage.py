import re
from decimal import Decimal

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from core.models import audit

from .models import (
    Accommodation, AccommodationUnit, BoatDeparture, BoatTour, Business, RestaurantProfile, TaxiService,
    managed_businesses,
)
from .serializers import DepartureSerializer

HHMM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def _managed(model, user, **lookup):
    obj = get_object_or_404(model, **lookup)
    business = obj if isinstance(obj, Business) else obj.business
    if not business.can_manage(user):
        raise NotFound("Не постои.")
    return obj


class BusinessEditSerializer(serializers.ModelSerializer):
    class Meta:
        model = Business
        fields = ("id", "name", "type", "city", "description", "address", "lat", "lng", "phone", "email", "website",
                  "image_url", "verification_status", "is_sponsored")
        read_only_fields = ("verification_status", "is_sponsored")

    def validate(self, attrs):
        if self.instance and "type" in attrs and attrs["type"] != self.instance.type:
            raise serializers.ValidationError({"type": "Типот на бизнис не може да се смени."})
        lat, lng = attrs.get("lat"), attrs.get("lng")
        if lat is not None and not 40.8 <= lat <= 42.4 or lng is not None and not 20.4 <= lng <= 23.1:
            raise serializers.ValidationError("Координатите се надвор од Северна Македонија.")
        return attrs


class AccommodationEditSerializer(serializers.ModelSerializer):
    units = serializers.SerializerMethodField()

    class Meta:
        model = Accommodation
        fields = ("id", "business", "title", "property_type", "description", "max_guests", "bedrooms", "beds",
                  "amenities", "rules", "cleaning_fee", "free_cancellation_days", "image_url", "units")
        read_only_fields = ("business",)

    def get_units(self, obj):
        return [{"id": u.id, "unit_name": u.unit_name} for u in obj.units.all()]

    def validate_amenities(self, v):
        bad = set(v) - set(Accommodation.AMENITIES)
        if bad:
            raise serializers.ValidationError(f"Непознати удобности: {', '.join(sorted(bad))}.")
        return list(dict.fromkeys(v))

    def validate_max_guests(self, v):
        if not 1 <= v <= 30:
            raise serializers.ValidationError("Дозволено 1–30 гости.")
        return v


class RestaurantEditSerializer(serializers.ModelSerializer):
    class Meta:
        model = RestaurantProfile
        fields = ("opening_hours", "menu", "price_range", "cuisine", "max_party_size")

    def validate_opening_hours(self, v):
        if not isinstance(v, dict):
            raise serializers.ValidationError("Очекуван објект {ден: [од, до]}.")
        for day, span in v.items():
            if day not in DAYS:
                raise serializers.ValidationError(f"Непознат ден „{day}“.")
            if span in (None, [], "closed"):
                continue
            if not (isinstance(span, list) and len(span) == 2 and all(HHMM.match(str(t)) for t in span)):
                raise serializers.ValidationError(f"{day}: формат [\"HH:MM\", \"HH:MM\"].")
        return v

    def validate_menu(self, v):
        if not isinstance(v, list):
            raise serializers.ValidationError("Менито е листа.")
        out = []
        for item in v:
            name = str(item.get("name", "")).strip()
            if not name:
                raise serializers.ValidationError("Секоја ставка има име.")
            price = item.get("price")
            if price not in (None, "") and Decimal(str(price)) < 0:
                raise serializers.ValidationError("Цената не може да е негативна.")
            out.append({"name": name[:120], "price": float(price) if price not in (None, "") else None,
                        "note": str(item.get("note", ""))[:200]})
        return out


class StopSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    minutes = serializers.IntegerField(min_value=0, max_value=24 * 60)
    stop_min = serializers.IntegerField(min_value=0, max_value=12 * 60, required=False, default=0)
    lat = serializers.FloatField(required=False, allow_null=True, min_value=40.8, max_value=42.4)
    lng = serializers.FloatField(required=False, allow_null=True, min_value=20.4, max_value=23.1)
    note = serializers.CharField(max_length=300, required=False, allow_blank=True, default="")


class BoatTourEditSerializer(serializers.ModelSerializer):
    stops = StopSerializer(many=True, required=False)

    class Meta:
        model = BoatTour
        fields = ("id", "business", "title", "route", "description", "stops", "includes", "duration_min",
                  "price_per_person", "departure_point", "rules")
        read_only_fields = ("business",)

    def validate_stops(self, v):
        minutes = [s["minutes"] for s in v]
        if minutes != sorted(minutes):
            raise serializers.ValidationError("Постојките мора да се подредени по време од поаѓањето.")
        return v

    def validate_price_per_person(self, v):
        if v <= 0:
            raise serializers.ValidationError("Цената мора да е поголема од 0.")
        return v


class TaxiEditSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaxiService
        fields = ("service_area", "passenger_capacity", "base_fare", "per_km", "available_24h", "vehicles",
                  "languages", "fare_info")


def _business_payload(b):
    data = BusinessEditSerializer(b).data
    if b.type == Business.Type.ACCOMMODATION:
        data["accommodations"] = AccommodationEditSerializer(b.accommodations.prefetch_related("units"), many=True).data
    elif b.type == Business.Type.RESTAURANT:
        profile, _ = RestaurantProfile.objects.get_or_create(business=b)
        data["restaurant"] = RestaurantEditSerializer(profile).data
    elif b.type == Business.Type.BOAT_TOUR:
        tours = []
        for t in b.boat_tours.all():
            row = BoatTourEditSerializer(t).data
            row["departures"] = DepartureSerializer(
                t.departures.filter(starts_at__gte=timezone.now()).order_by("starts_at")[:60], many=True).data
            tours.append(row)
        data["boat_tours"] = tours
    elif b.type == Business.Type.TAXI:
        taxi, _ = TaxiService.objects.get_or_create(business=b, defaults={"service_area": b.city.name})
        data["taxi"] = TaxiEditSerializer(taxi).data
    return data


AUTH = [permissions.IsAuthenticated]


@api_view(["GET", "POST"])
@permission_classes(AUTH)
def my_businesses(request):
    if request.method == "GET":
        qs = managed_businesses(request.user).select_related("city").order_by("name")
        return Response([_business_payload(b) for b in qs])
    if request.user.role not in ("BUSINESS", "ADMIN") and not request.user.is_superuser:
        return Response({"error": {"code": "forbidden", "message": "Потребен е бизнис-профил.", "details": None}},
                        status=403)
    s = BusinessEditSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    with transaction.atomic():
        b = s.save(owner=request.user, verification_status=Business.Verification.PENDING)
        if b.type == Business.Type.RESTAURANT:
            RestaurantProfile.objects.create(business=b)
        elif b.type == Business.Type.TAXI:
            TaxiService.objects.create(business=b, service_area=b.city.name)
    audit(request.user, "business.create", b)
    return Response(_business_payload(b), status=status.HTTP_201_CREATED)


@api_view(["GET", "PATCH"])
@permission_classes(AUTH)
def my_business_detail(request, pk):
    b = _managed(Business, request.user, pk=pk)
    if request.method == "PATCH":
        s = BusinessEditSerializer(b, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        audit(request.user, "business.update", b, fields=sorted(request.data.keys()))
    return Response(_business_payload(b))


@api_view(["POST"])
@permission_classes(AUTH)
def create_accommodation(request, pk):
    b = _managed(Business, request.user, pk=pk)
    if b.type != Business.Type.ACCOMMODATION:
        return Response({"error": {"code": "wrong_type", "message": "Бизнисот не е сместување.", "details": None}}, status=400)
    s = AccommodationEditSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    with transaction.atomic():
        acc = s.save(business=b)
        AccommodationUnit.objects.create(accommodation=acc, unit_name=request.data.get("unit_name") or "Единица 1")
    audit(request.user, "accommodation.create", acc)
    return Response(AccommodationEditSerializer(acc).data, status=201)


@api_view(["PATCH"])
@permission_classes(AUTH)
def edit_accommodation(request, pk):
    acc = _managed(Accommodation, request.user, pk=pk)
    s = AccommodationEditSerializer(acc, data=request.data, partial=True)
    s.is_valid(raise_exception=True)
    s.save()
    audit(request.user, "accommodation.update", acc, fields=sorted(request.data.keys()))
    return Response(s.data)


@api_view(["PATCH"])
@permission_classes(AUTH)
def edit_restaurant(request, pk):
    b = _managed(Business, request.user, pk=pk, type=Business.Type.RESTAURANT)
    profile, _ = RestaurantProfile.objects.get_or_create(business=b)
    s = RestaurantEditSerializer(profile, data=request.data, partial=True)
    s.is_valid(raise_exception=True)
    s.save()
    audit(request.user, "restaurant.update", b, fields=sorted(request.data.keys()))
    return Response(s.data)


@api_view(["PATCH"])
@permission_classes(AUTH)
def edit_taxi(request, pk):
    b = _managed(Business, request.user, pk=pk, type=Business.Type.TAXI)
    taxi, _ = TaxiService.objects.get_or_create(business=b, defaults={"service_area": b.city.name})
    s = TaxiEditSerializer(taxi, data=request.data, partial=True)
    s.is_valid(raise_exception=True)
    s.save()
    audit(request.user, "taxi.update", b, fields=sorted(request.data.keys()))
    return Response(s.data)


@api_view(["POST"])
@permission_classes(AUTH)
def create_boat_tour(request, pk):
    b = _managed(Business, request.user, pk=pk, type=Business.Type.BOAT_TOUR)
    s = BoatTourEditSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    tour = s.save(business=b)
    audit(request.user, "boat_tour.create", tour)
    return Response(BoatTourEditSerializer(tour).data, status=201)


@api_view(["PATCH"])
@permission_classes(AUTH)
def edit_boat_tour(request, pk):
    tour = _managed(BoatTour, request.user, pk=pk)
    s = BoatTourEditSerializer(tour, data=request.data, partial=True)
    s.is_valid(raise_exception=True)
    s.save()
    audit(request.user, "boat_tour.update", tour, fields=sorted(request.data.keys()))
    return Response(s.data)


@api_view(["POST"])
@permission_classes(AUTH)
def cancel_departure(request, pk):
    from reservations.models import Reservation
    from reservations.services import transition

    dep = get_object_or_404(BoatDeparture.objects.select_related("tour__business"), pk=pk)
    if not dep.tour.business.can_manage(request.user):
        raise NotFound("Не постои.")
    if dep.status == "CANCELLED":
        return Response(DepartureSerializer(dep).data)
    affected = Reservation.objects.filter(boat_departure=dep, status__in=Reservation.HOLDING)
    note = "Поаѓањето е откажано од операторот."
    count = 0
    for res in affected:
        target = Reservation.Status.REJECTED if res.status == Reservation.Status.PENDING else Reservation.Status.CANCELLED
        transition(res.pk, target, request.user, note)
        count += 1
    dep.refresh_from_db()
    dep.status = "CANCELLED"
    dep.save(update_fields=["status"])
    audit(request.user, "departure.cancel", dep, affected=count)
    return Response(DepartureSerializer(dep).data)
