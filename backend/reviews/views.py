from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from core.exceptions import ServiceError
from core.models import audit
from core.permissions import IsAdminRole
from notifications.models import notify
from reservations.models import Reservation

from .models import DIMENSIONS, BusinessReply, Review, ReviewReport


class ReplySerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessReply
        fields = ("reply_text", "created_at", "updated_at")


class ReviewSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    service_type = serializers.CharField(source="reservation.service_type", read_only=True)
    reply = ReplySerializer(read_only=True)

    class Meta:
        model = Review
        fields = ("id", "business", "username", "service_type", "rating", "dimension_scores", "comment",
                  "is_verified_booking", "created_at", "reply")


class ReviewIn(serializers.Serializer):
    rating = serializers.IntegerField(min_value=1, max_value=5)
    dimension_scores = serializers.DictField(child=serializers.IntegerField(min_value=1, max_value=5), required=False)
    comment = serializers.CharField(required=False, allow_blank=True, max_length=3000)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def create_review(request, pk):
    """Серверски проверки: сопственик на резервацијата, статус COMPLETED, една рецензија."""
    res = get_object_or_404(Reservation, pk=pk)
    if res.user_id != request.user.id:
        raise ServiceError("Може да оцените само сопствена резервација.", code="forbidden", status_code=403)
    if res.status != Reservation.Status.COMPLETED:
        raise ServiceError("Рецензија е дозволена само по завршена услуга (COMPLETED).", code="not_completed")
    d = ReviewIn(data=request.data)
    d.is_valid(raise_exception=True)
    v = d.validated_data
    allowed = set(DIMENSIONS.get(res.service_type, []))
    dims = v.get("dimension_scores", {})
    if set(dims) - allowed:
        raise ServiceError(f"Дозволени критериуми: {', '.join(sorted(allowed))}.", code="invalid_dimensions")
    try:
        with transaction.atomic():
            review = Review.objects.create(user=request.user, business_id=res.business_id, reservation=res,
                                           rating=v["rating"], dimension_scores=dims, comment=v.get("comment", ""))
    except IntegrityError:
        raise ServiceError("Веќе постои рецензија за оваа резервација.", code="already_reviewed", status_code=409)
    notify(res.business.owner, "review", "Нова рецензија", f"Оценка {review.rating}/5", review)
    return Response(ReviewSerializer(review).data, status=201)


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def business_reviews(request, pk):
    qs = Review.objects.filter(business_id=pk, status="VISIBLE").select_related("user", "reservation", "reply")
    return Response(ReviewSerializer(qs, many=True).data)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def reply(request, pk):
    review = get_object_or_404(Review.objects.select_related("business"), pk=pk)
    if not review.business.can_manage(request.user):
        raise ServiceError("Само бизнисот може да одговори.", code="forbidden", status_code=403)
    text = str(request.data.get("reply_text", "")).strip()
    if not text:
        raise ServiceError("Одговорот е празен.", code="empty_reply")
    # Бизнисот може да го уреди својот одговор, но никогаш самата рецензија.
    obj, _ = BusinessReply.objects.update_or_create(review=review, defaults={"reply_text": text[:2000],
                                                                             "business_user": request.user})
    notify(review.user, "review_reply", "Бизнисот одговори на вашата рецензија", "", review)
    return Response(ReplySerializer(obj).data)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def report(request, pk):
    review = get_object_or_404(Review, pk=pk)
    reason = str(request.data.get("reason", "")).strip()
    if not reason:
        raise ServiceError("Наведете причина.", code="empty_reason")
    _, created = ReviewReport.objects.get_or_create(review=review, reporter=request.user,
                                                    defaults={"reason": reason[:500]})
    return Response({"reported": True, "already_reported": not created}, status=201 if created else 200)


@api_view(["GET"])
@permission_classes([IsAdminRole])
def admin_review_reports(request):
    qs = ReviewReport.objects.filter(status="OPEN").select_related("review", "reporter")
    return Response([{
        "id": r.id, "reason": r.reason, "reporter": r.reporter.username, "created_at": r.created_at,
        "review": ReviewSerializer(r.review).data,
    } for r in qs])


@api_view(["POST"])
@permission_classes([IsAdminRole])
def admin_resolve_review_report(request, pk):
    rep = get_object_or_404(ReviewReport, pk=pk)
    action = request.data.get("action")
    if action not in ("hide", "dismiss"):
        raise ServiceError("action: hide | dismiss", code="invalid_action")
    with transaction.atomic():
        if action == "hide":
            rep.review.status = "HIDDEN"
            rep.review.save(update_fields=["status"])
            ReviewReport.objects.filter(review=rep.review, status="OPEN").update(
                status="RESOLVED", moderator=request.user, resolved_at=timezone.now())
        else:
            rep.status, rep.moderator, rep.resolved_at = "DISMISSED", request.user, timezone.now()
            rep.save()
    audit(request.user, f"review_report.{action}", rep.review)
    return Response({"ok": True})


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def latest_reviews(request):
    qs = (Review.objects.filter(status="VISIBLE").select_related("user", "reservation", "reply", "business")
          .order_by("-created_at")[:6])
    data = ReviewSerializer(qs, many=True).data
    for row, r in zip(data, qs):
        row["business_name"] = r.business.name
    return Response(data)
