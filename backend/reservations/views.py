from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from businesses.models import AccommodationUnit, BoatDeparture, Business, managed_businesses

from . import services
from .models import Reservation
from .serializers import (
    AccommodationBookingIn, BoatReservationIn, BusinessActionIn, ReservationSerializer,
    RestaurantReservationIn, TaxiRequestIn,
)

AUTH = [permissions.IsAuthenticated]


def _out(request, res, status=201):
    return Response(ReservationSerializer(res, context={"request": request}).data, status=status)


@api_view(["POST"])
@permission_classes(AUTH)
def accommodation_booking(request):
    d = AccommodationBookingIn(data=request.data)
    d.is_valid(raise_exception=True)
    v = d.validated_data
    unit = get_object_or_404(AccommodationUnit.objects.select_related("accommodation__business"), pk=v["unit_id"])
    res = services.create_accommodation_booking(request.user, unit, v["check_in"], v["check_out"], v["guests"],
                                                v.get("notes", ""), v.get("idempotency_key"))
    return _out(request, res)


@api_view(["POST"])
@permission_classes(AUTH)
def boat_reservation(request):
    d = BoatReservationIn(data=request.data)
    d.is_valid(raise_exception=True)
    v = d.validated_data
    dep = get_object_or_404(BoatDeparture.objects.select_related("tour__business"), pk=v["departure_id"])
    res = services.create_boat_reservation(request.user, dep, v["seats"], v.get("notes", ""), v.get("idempotency_key"))
    return _out(request, res)


@api_view(["POST"])
@permission_classes(AUTH)
def restaurant_reservation(request):
    d = RestaurantReservationIn(data=request.data)
    d.is_valid(raise_exception=True)
    v = d.validated_data
    biz = get_object_or_404(Business, pk=v["business_id"])
    res = services.create_restaurant_request(request.user, biz, v["reserved_for"], v["guests"],
                                             v.get("notes", ""), v.get("idempotency_key"))
    return _out(request, res)


@api_view(["POST"])
@permission_classes(AUTH)
def taxi_request(request):
    d = TaxiRequestIn(data=request.data)
    d.is_valid(raise_exception=True)
    v = d.validated_data
    biz = get_object_or_404(Business, pk=v["business_id"])
    res = services.create_taxi_request(request.user, biz, v["reserved_for"], v["guests"], v["pickup"],
                                       v["destination"], v.get("notes", ""), v.get("idempotency_key"))
    return _out(request, res)


@api_view(["GET"])
@permission_classes(AUTH)
def my_reservations(request):
    qs = (Reservation.objects.filter(user=request.user)
          .select_related("business", "accommodation_unit", "boat_departure")
          .prefetch_related("items", "history"))
    return Response(ReservationSerializer(qs, many=True, context={"request": request}).data)


@api_view(["GET"])
@permission_classes(AUTH)
def reservation_detail(request, pk):
    res = get_object_or_404(Reservation, pk=pk)
    if res.user_id != request.user.id and not res.business.can_manage(request.user):
        return Response({"error": {"code": "not_found", "message": "Не постои.", "details": None}}, status=404)
    return _out(request, res, status=200)


@api_view(["POST"])
@permission_classes(AUTH)
def cancel_reservation(request, pk):
    res = get_object_or_404(Reservation, pk=pk, user=request.user)
    res = services.transition(res.pk, Reservation.Status.CANCELLED, request.user, request.data.get("note", ""))
    return _out(request, res, status=200)


@api_view(["POST"])
@permission_classes(AUTH)
def accept_proposal(request, pk):
    res = get_object_or_404(Reservation, pk=pk, user=request.user)
    res = services.transition(res.pk, Reservation.Status.CONFIRMED, request.user, "Корисникот прифати")
    return _out(request, res, status=200)


# --- Бизнис ---------------------------------------------------------------

@api_view(["GET"])
@permission_classes(AUTH)
def business_reservations(request):
    qs = (Reservation.objects.filter(business__in=managed_businesses(request.user))
          .select_related("business", "user", "accommodation_unit", "boat_departure")
          .prefetch_related("items", "history"))
    if request.query_params.get("status"):
        qs = qs.filter(status=request.query_params["status"])
    return Response(ReservationSerializer(qs, many=True, context={"request": request}).data)


@api_view(["PATCH", "POST"])
@permission_classes(AUTH)
def business_reservation_action(request, pk):
    res = get_object_or_404(Reservation.objects.select_related("business"), pk=pk)
    if not res.business.can_manage(request.user):
        # 404 наместо 403 — не откриваме туѓи резервации.
        return Response({"error": {"code": "not_found", "message": "Не постои.", "details": None}}, status=404)
    d = BusinessActionIn(data=request.data)
    d.is_valid(raise_exception=True)
    v = d.validated_data
    res = services.transition(res.pk, services.ACTION_TO_STATUS[v["action"]], request.user, v.get("note", ""),
                              proposed_datetime=v.get("proposed_datetime"), quoted_price=v.get("quoted_price"))
    return _out(request, res, status=200)


@api_view(["GET"])
@permission_classes(AUTH)
def business_dashboard(request):
    businesses = managed_businesses(request.user).annotate(
        total=Count("reservations", distinct=True),
        pending=Count("reservations", filter=Q(reservations__status="PENDING"), distinct=True),
        confirmed=Count("reservations", filter=Q(reservations__status__in=["CONFIRMED", "IN_PROGRESS", "COMPLETED"]),
                        distinct=True),
        avg_rating=Avg("reviews__rating", filter=Q(reviews__status="VISIBLE")),
        review_count=Count("reviews", filter=Q(reviews__status="VISIBLE"), distinct=True),
    )
    data = []
    for b in businesses:
        rate = round(b.confirmed / b.total * 100, 1) if b.total else None
        data.append({
            "id": b.id, "name": b.name, "type": b.type, "verification_status": b.verification_status,
            "reservations_total": b.total, "pending": b.pending, "confirmation_rate_pct": rate,
            "avg_rating": round(b.avg_rating, 2) if b.avg_rating else None, "review_count": b.review_count,
        })
    return Response({"businesses": data})
