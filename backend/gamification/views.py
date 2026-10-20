from django.db.models import Count
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, serializers
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from accounts.models import User
from core.exceptions import ServiceError
from core.models import audit
from core.permissions import IsAdminRole
from destinations.models import City, Place

from . import services
from .models import Badge, CityAchievement, PhotoCheckIn, PlacePhoto, PlaceReport, UserBadge


class BadgeSerializer(serializers.ModelSerializer):
    holders_count = serializers.IntegerField(read_only=True, default=None)

    class Meta:
        model = Badge
        fields = ("id", "code", "name", "description", "kind", "level", "place", "city", "icon", "holders_count")


class UserBadgeSerializer(serializers.ModelSerializer):
    badge = BadgeSerializer(read_only=True)

    class Meta:
        model = UserBadge
        fields = ("badge", "unlocked_at")


class AchievementSerializer(serializers.ModelSerializer):
    city_name = serializers.CharField(source="city.name", read_only=True)
    city_slug = serializers.CharField(source="city.slug", read_only=True)

    class Meta:
        model = CityAchievement
        fields = ("city", "city_name", "city_slug", "documented_required", "required_total", "documented_any",
                  "percent", "updated_at")


class PhotoSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(source="checkin.image", read_only=True)
    taken_at = serializers.DateTimeField(source="checkin.taken_at", read_only=True)
    status = serializers.CharField(source="checkin.status", read_only=True)
    place_name = serializers.CharField(source="place.name", read_only=True)
    photographer = serializers.SerializerMethodField()

    class Meta:
        model = PlacePhoto
        fields = ("id", "place", "place_name", "image", "caption", "is_public", "photographer", "taken_at",
                  "created_at", "status")

    def get_photographer(self, obj):
        return obj.user.username if obj.user.is_profile_public else "Турист"


class CheckInSerializer(serializers.ModelSerializer):
    place_name = serializers.CharField(source="place.name", read_only=True)

    class Meta:
        model = PhotoCheckIn
        fields = ("id", "place", "place_name", "image", "status", "distance_m", "taken_at", "verification_notes",
                  "created_at")


class UploadThrottle(UserRateThrottle):
    scope = "uploads"


def _float_or_none(v):
    try:
        return float(v) if v not in (None, "") else None
    except (TypeError, ValueError):
        raise ServiceError("Невалидни координати.", code="invalid_coordinates")


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
@throttle_classes([UploadThrottle])
def create_checkin(request, pk):
    place = get_object_or_404(Place, pk=pk)
    image = request.FILES.get("image")
    if not image:
        raise ServiceError("Прикачете фотографија (поле „image“).", code="missing_image")
    checkin, unlocked = services.create_checkin(
        request.user, place, image,
        client_lat=_float_or_none(request.data.get("lat")), client_lng=_float_or_none(request.data.get("lng")),
        caption=str(request.data.get("caption", "")),
        is_public=str(request.data.get("is_public", "true")).lower() in ("1", "true", "yes"),
    )
    ach = CityAchievement.objects.filter(user=request.user, city=place.city).first()
    return Response({
        "checkin": CheckInSerializer(checkin, context={"request": request}).data,
        "unlocked_badges": BadgeSerializer(unlocked, many=True).data,
        "city_progress": AchievementSerializer(ach).data if ach else None,
    }, status=201)


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def place_gallery(request, pk):
    place = get_object_or_404(Place, pk=pk)
    photos = (PlacePhoto.objects.filter(place=place, is_public=True, is_hidden=False,
                                        checkin__status=PhotoCheckIn.Status.APPROVED)
              .select_related("user", "checkin", "place"))
    holders = UserBadge.objects.filter(badge__place=place).count()
    return Response({
        "place_id": place.id, "badge_holders": holders,
        "photos": PhotoSerializer(photos, many=True, context={"request": request}).data,
    })


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def badges(request):
    qs = Badge.objects.annotate(holders_count=Count("holders")).order_by("kind", "name")
    if request.query_params.get("city"):
        qs = qs.filter(city__slug=request.query_params["city"])
    return Response(BadgeSerializer(qs, many=True).data)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def my_gamification(request):
    u = request.user
    achievements = {a.city_id: a for a in CityAchievement.objects.filter(user=u).select_related("city")}
    # Прикажи напредок и за градови каде уште нема посета.
    progress = []
    for city in City.objects.all():
        a = achievements.get(city.id)
        total = Place.objects.filter(city=city, status=Place.Status.VERIFIED, is_required_landmark=True).count()
        progress.append(AchievementSerializer(a).data if a else {
            "city": city.id, "city_name": city.name, "city_slug": city.slug, "documented_required": 0,
            "required_total": total, "documented_any": 0, "percent": 0.0, "updated_at": None})
    return Response({
        "badges": UserBadgeSerializer(UserBadge.objects.filter(user=u).select_related("badge"), many=True).data,
        "city_progress": progress,
        "checkins": CheckInSerializer(PhotoCheckIn.objects.filter(user=u).select_related("place")[:100], many=True,
                                      context={"request": request}).data,
    })


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def public_profile(request, username):
    u = get_object_or_404(User, username=username)
    is_self = request.user.is_authenticated and request.user.id == u.id
    if not u.is_profile_public and not is_self:
        raise ServiceError("Профилот е приватен.", code="private_profile", status_code=403)
    photos = PlacePhoto.objects.filter(user=u, is_hidden=False, checkin__status=PhotoCheckIn.Status.APPROVED)
    if not is_self:
        photos = photos.filter(is_public=True)
    visited = (Place.objects.filter(checkins__user=u, checkins__status=PhotoCheckIn.Status.APPROVED)
               .distinct().values("id", "name", "city__name"))
    history = UserBadge.objects.filter(user=u).select_related("badge")
    return Response({
        "username": u.username, "first_name": u.first_name, "last_name": u.last_name, "bio": u.bio,
        "avatar": request.build_absolute_uri(u.avatar.url) if u.avatar else None,
        "badges": UserBadgeSerializer(history, many=True).data,
        "city_progress": AchievementSerializer(CityAchievement.objects.filter(user=u).select_related("city"),
                                               many=True).data,
        "photos": PhotoSerializer(photos.select_related("place", "checkin", "user")[:60], many=True,
                                  context={"request": request}).data,
        "visited_places": list(visited),
        "favorite_places": list(u.favorite_places.values("id", "name", "city__name")),
        "saved_trips": u.trips.count() if is_self else None,
    })


@api_view(["PATCH", "DELETE"])
@permission_classes([permissions.IsAuthenticated])
def my_photo(request, pk):
    photo = get_object_or_404(PlacePhoto, pk=pk, user=request.user)
    if request.method == "DELETE":
        # Беџот останува: доказот е веќе проверен; фотографијата исчезнува од галеријата.
        photo.is_public = False
        photo.is_hidden = True
        photo.save(update_fields=["is_public", "is_hidden"])
        return Response(status=204)
    if "is_public" in request.data:
        photo.is_public = str(request.data["is_public"]).lower() in ("1", "true", "yes")
    if "caption" in request.data:
        photo.caption = str(request.data["caption"])[:300]
    photo.save()
    return Response(PhotoSerializer(photo, context={"request": request}).data)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def report_photo(request, pk):
    photo = get_object_or_404(PlacePhoto, pk=pk)
    reason = str(request.data.get("reason", "")).strip()
    if not reason:
        raise ServiceError("Наведете причина.", code="empty_reason")
    _, created = PlaceReport.objects.get_or_create(photo=photo, reporter=request.user, defaults={"reason": reason[:500]})
    return Response({"reported": True, "already_reported": not created}, status=201 if created else 200)


# --- Администрација ---------------------------------------------------------

@api_view(["GET"])
@permission_classes([IsAdminRole])
def admin_pending_checkins(request):
    qs = PhotoCheckIn.objects.filter(status=PhotoCheckIn.Status.PENDING).select_related("place", "user")
    data = CheckInSerializer(qs, many=True, context={"request": request}).data
    for row, c in zip(data, qs):
        row["username"] = c.user.username
    return Response(data)


@api_view(["POST"])
@permission_classes([IsAdminRole])
def admin_review_checkin(request, pk):
    approve = request.data.get("action") == "approve"
    if request.data.get("action") not in ("approve", "reject"):
        raise ServiceError("action: approve | reject", code="invalid_action")
    c, unlocked = services.review_checkin(pk, request.user, approve, str(request.data.get("note", "")))
    audit(request.user, f"checkin.{request.data['action']}", c)
    return Response({"checkin": CheckInSerializer(c, context={"request": request}).data,
                     "unlocked_badges": BadgeSerializer(unlocked, many=True).data})


@api_view(["GET"])
@permission_classes([IsAdminRole])
def admin_place_reports(request):
    qs = PlaceReport.objects.filter(status="OPEN").select_related("photo", "reporter", "photo__place", "photo__user",
                                                                  "photo__checkin")
    return Response([{"id": r.id, "reason": r.reason, "reporter": r.reporter.username, "created_at": r.created_at,
                      "photo": PhotoSerializer(r.photo, context={"request": request}).data} for r in qs])


@api_view(["POST"])
@permission_classes([IsAdminRole])
def admin_resolve_place_report(request, pk):
    rep = get_object_or_404(PlaceReport, pk=pk)
    action = request.data.get("action")
    if action not in ("hide", "dismiss"):
        raise ServiceError("action: hide | dismiss", code="invalid_action")
    if action == "hide":
        rep.photo.is_hidden = True
        rep.photo.save(update_fields=["is_hidden"])
        PlaceReport.objects.filter(photo=rep.photo, status="OPEN").update(
            status="RESOLVED", moderator=request.user, resolved_at=timezone.now())
    else:
        rep.status, rep.moderator, rep.resolved_at = "DISMISSED", request.user, timezone.now()
        rep.save()
    audit(request.user, f"place_report.{action}", rep.photo)
    return Response({"ok": True})
