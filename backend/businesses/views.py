from datetime import date, timedelta

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_datetime
from rest_framework import permissions, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from core.models import audit

from .models import (
    Accommodation, AccommodationAvailability, AccommodationUnit, BoatDeparture, BoatTour,
    Business, RestaurantProfile, TaxiService, TransportService,
)
from .serializers import (
    AccommodationSerializer, AvailabilitySerializer, BoatTourSerializer, BusinessSerializer,
    DepartureSerializer, RestaurantSerializer, TaxiSerializer, TransportSerializer,
)
from .services import parse_stay, search_accommodations, unit_quote, with_ratings

APPROVED = Business.Verification.APPROVED


class BusinessViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BusinessSerializer

    def get_queryset(self):
        qs = with_ratings(Business.objects.filter(verification_status=APPROVED).select_related("city"))
        p = self.request.query_params
        if p.get("type"):
            qs = qs.filter(type=p["type"])
        if p.get("city"):
            qs = qs.filter(city__slug=p["city"])
        return qs


class AccommodationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AccommodationSerializer
    queryset = Accommodation.objects.filter(business__verification_status=APPROVED).select_related("business", "business__city").order_by("title")

    def list(self, request, *args, **kwargs):
        p = request.query_params
        try:
            guests = int(p.get("guests", 1))
        except ValueError:
            raise ValidationError({"guests": "Мора да е број."})
        results = search_accommodations(
            city=p.get("city"), check_in=p.get("check_in"), check_out=p.get("check_out"), guests=guests,
            max_total=p.get("max_total"), amenities=p.get("amenities", "").split(","),
            property_type=p.get("type"),
        )
        out = []
        for r in results:
            q = r["quote"]
            out.append({
                **AccommodationSerializer(r["accommodation"]).data,
                "avg_rating": r["avg_rating"],
                "review_count": r["review_count"],
                "recommendation_reason": r["reason"],
                "quote": None if not q else {
                    "unit_id": r["unit"].id, "unit_name": r["unit"].unit_name, "nights": q["nights"],
                    "subtotal": q["subtotal"], "fees": q["fees"], "total": q["total"],
                },
            })
        return Response(out)

    @action(detail=True)
    def availability(self, request, pk=None):
        acc = self.get_object()
        p = request.query_params
        if p.get("check_in") and p.get("check_out"):
            ci, co = parse_stay(p["check_in"], p["check_out"])
            units = []
            for unit in acc.units.all():
                q = unit_quote(unit, ci, co)
                units.append({
                    "unit_id": unit.id, "unit_name": unit.unit_name, "available": q is not None,
                    "nights": q["nights"] if q else None, "total": q["total"] if q else None,
                    "nightly": [{"date": d, "price": pr} for d, pr in q["nightly"]] if q else [],
                })
            return Response({"check_in": ci, "check_out": co, "units": units})
        start = date.today()
        rows = AccommodationAvailability.objects.filter(unit__accommodation=acc, date__gte=start,
                                                        date__lt=start + timedelta(days=60))
        cal = {}
        for r in rows:
            cal.setdefault(r.unit_id, []).append(AvailabilitySerializer(r).data)
        return Response({"calendar": cal})


class RestaurantViewSet(viewsets.ReadOnlyModelViewSet):

    serializer_class = RestaurantSerializer
    queryset = RestaurantProfile.objects.filter(business__verification_status=APPROVED).select_related("business", "business__city").order_by("business__name")
    lookup_field = "business_id"


class BoatTourViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BoatTourSerializer
    queryset = BoatTour.objects.filter(business__verification_status=APPROVED).select_related("business", "business__city").order_by("title")

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "detail": self.action == "retrieve"}


class TaxiViewSet(viewsets.ReadOnlyModelViewSet):

    serializer_class = TaxiSerializer
    queryset = TaxiService.objects.filter(business__verification_status=APPROVED).select_related("business", "business__city").order_by("business__name")
    lookup_field = "business_id"


class TransportViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TransportSerializer
    lookup_field = "business_id"

    def get_queryset(self):
        qs = TransportService.objects.filter(business__verification_status=APPROVED).select_related(
            "business", "business__city").order_by("business__name")
        p = self.request.query_params
        if p.get("city"):
            qs = qs.filter(business__city__slug=p["city"])
        if p.get("type"):
            qs = qs.filter(business__type=p["type"])
        return qs


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def departure_availability(request, pk):
    dep = get_object_or_404(BoatDeparture, pk=pk)
    return Response(DepartureSerializer(dep).data)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def set_unit_availability(request, pk):
    unit = get_object_or_404(AccommodationUnit.objects.select_related("accommodation__business"), pk=pk)
    if not unit.accommodation.business.can_manage(request.user):
        raise PermissionDenied("Не управувате со овој објект.")
    try:
        start, end = parse_stay(request.data["start"], request.data["end"])
        units = int(request.data["available_units"])
        price = request.data["price_per_night"]
    except (KeyError, ValueError):
        raise ValidationError("Потребни: start, end, available_units, price_per_night.")
    if units < 0 or float(price) <= 0:
        raise ValidationError("Невалиден број единици или цена.")
    with transaction.atomic():
        d = start
        while d < end:
            AccommodationAvailability.objects.update_or_create(
                unit=unit, date=d, defaults={"available_units": units, "price_per_night": price}
            )
            d += timedelta(days=1)
    audit(request.user, "availability.set", unit, start=str(start), end=str(end))
    return Response({"ok": True})


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def create_departure(request, pk):
    tour = get_object_or_404(BoatTour.objects.select_related("business"), pk=pk)
    if not tour.business.can_manage(request.user):
        raise PermissionDenied("Не управувате со оваа тура.")
    starts_at = parse_datetime(str(request.data.get("starts_at", "")))
    try:
        capacity = int(request.data.get("capacity", 0))
    except ValueError:
        capacity = 0
    if not starts_at or capacity <= 0:
        raise ValidationError("Потребни: starts_at (ISO) и capacity > 0.")
    dep = BoatDeparture.objects.create(tour=tour, starts_at=starts_at, capacity=capacity)
    return Response(DepartureSerializer(dep).data, status=201)
