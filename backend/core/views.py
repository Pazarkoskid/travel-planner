from django.db.models import Count
from django.shortcuts import get_object_or_404
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from accounts.models import User
from businesses.models import Business
from gamification.models import PhotoCheckIn, PlaceReport, UserBadge
from reservations.models import Reservation
from reviews.models import Review, ReviewReport
from trips.models import AIPlanRun, Trip

from .exceptions import ServiceError
from .models import AuditLog, audit
from .permissions import IsAdminRole


@api_view(["GET"])
@permission_classes([IsAdminRole])
def analytics(request):
    runs = AIPlanRun.objects.all()[:200]
    gen = [r.duration_ms for r in runs]
    improvements = [r.metrics.get("travel_improvement_pct", 0) for r in runs if r.metrics]
    return Response({
        "users": dict(User.objects.values_list("role").annotate(n=Count("id"))),
        "businesses": dict(Business.objects.values_list("verification_status").annotate(n=Count("id"))),
        "reservations": dict(Reservation.objects.values_list("status").annotate(n=Count("id"))),
        "trips": Trip.objects.count(),
        "plan_runs": AIPlanRun.objects.count(),
        "avg_generation_ms": round(sum(gen) / len(gen)) if gen else None,
        "avg_travel_improvement_pct": round(sum(improvements) / len(improvements), 1) if improvements else None,
        "reviews": Review.objects.count(),
        "open_review_reports": ReviewReport.objects.filter(status="OPEN").count(),
        "pending_checkins": PhotoCheckIn.objects.filter(status="PENDING").count(),
        "open_photo_reports": PlaceReport.objects.filter(status="OPEN").count(),
        "badges_unlocked": UserBadge.objects.count(),
        "recent_audit": list(AuditLog.objects.values("timestamp", "action", "object_type", "object_id")[:20]),
    })


@api_view(["GET"])
@permission_classes([IsAdminRole])
def pending_businesses(request):
    qs = Business.objects.filter(verification_status=Business.Verification.PENDING).select_related("city", "owner")
    return Response([{"id": b.id, "name": b.name, "type": b.type, "city": b.city.name, "owner": b.owner.username,
                      "created_at": b.created_at} for b in qs])


@api_view(["POST"])
@permission_classes([IsAdminRole])
def verify_business(request, pk):
    b = get_object_or_404(Business, pk=pk)
    status = request.data.get("status")
    if status not in Business.Verification.values:
        raise ServiceError(f"status: {', '.join(Business.Verification.values)}", code="invalid_status")
    b.verification_status = status
    b.save(update_fields=["verification_status"])
    audit(request.user, "business.verify", b, status=status)
    return Response({"id": b.id, "verification_status": b.verification_status})


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def weather(request):
    from destinations.models import City, Place

    from .weather import get_weather

    p = request.query_params
    if p.get("place"):
        obj = get_object_or_404(Place, pk=p["place"])
        lat, lng, label = obj.lat, obj.lng, obj.name
    elif p.get("city"):
        obj = get_object_or_404(City, **({"pk": p["city"]} if p["city"].isdigit() else {"slug": p["city"]}))
        lat, lng, label = obj.center_lat, obj.center_lng, obj.name
    else:
        try:
            lat, lng, label = float(p["lat"]), float(p["lng"]), ""
        except (KeyError, ValueError):
            raise ServiceError("Потребно: city, place или lat и lng.", code="invalid_location")
        if not (40.0 <= lat <= 43.0 and 20.0 <= lng <= 23.5):
            raise ServiceError("Локацијата е надвор од Македонија.", code="invalid_location")
    from .i18n import CITY_EN, get_lang

    lang = get_lang(request)
    if lang == "en":
        label = CITY_EN.get(label, label)
    return Response({"location": label, **get_weather(lat, lng, lang)})


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def amenities(request):
    from destinations.models import City

    from .amenities import get_amenities

    ref = str(request.query_params.get("city", "")).strip()
    if not ref:
        raise ServiceError("Потребен е град (city).", code="city_required")
    city = City.objects.filter(pk=ref).first() if ref.isdigit() else City.objects.filter(slug=ref).first()
    if not city:
        raise ServiceError("Градот не постои.", code="not_found", status_code=404)
    return Response(get_amenities(city))
