from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Avg, Count, Q

from core.exceptions import ServiceError

from .models import Accommodation, AccommodationAvailability, Business


def with_ratings(qs):
    return qs.annotate(
        avg_rating=Avg("reviews__rating", filter=Q(reviews__status="VISIBLE")),
        review_count=Count("reviews", filter=Q(reviews__status="VISIBLE"), distinct=True),
    )


def parse_stay(check_in, check_out):
    try:
        ci = date.fromisoformat(str(check_in))
        co = date.fromisoformat(str(check_out))
    except (TypeError, ValueError):
        raise ServiceError("Невалиден датум (YYYY-MM-DD).", code="invalid_dates")
    if co <= ci:
        raise ServiceError("Check-out мора да биде по check-in.", code="invalid_dates")
    if ci < date.today():
        raise ServiceError("Check-in не може да биде во минатото.", code="invalid_dates")
    if (co - ci).days > 60:
        raise ServiceError("Максимум 60 ноќи по резервација.", code="invalid_dates")
    return ci, co


def nights(ci, co):
    return [ci + timedelta(days=i) for i in range((co - ci).days)]


def unit_quote(unit, ci, co):
    stay = nights(ci, co)
    rows = list(AccommodationAvailability.objects.filter(unit=unit, date__in=stay, available_units__gte=1))
    if len(rows) != len(stay):
        return None
    nightly = [(r.date, r.price_per_night) for r in sorted(rows, key=lambda r: r.date)]
    subtotal = sum((p for _, p in nightly), Decimal("0"))
    fee = unit.accommodation.cleaning_fee or Decimal("0")
    return {"nights": len(stay), "nightly": nightly, "subtotal": subtotal, "fees": fee, "total": subtotal + fee}


def search_accommodations(*, city=None, check_in=None, check_out=None, guests=1, max_total=None,
                          amenities=(), property_type=None):
    qs = Accommodation.objects.filter(
        business__verification_status=Business.Verification.APPROVED, max_guests__gte=guests
    ).select_related("business", "business__city").prefetch_related("units")
    if city:
        qs = qs.filter(business__city__slug=city) if not str(city).isdigit() else qs.filter(business__city_id=city)
    if property_type:
        qs = qs.filter(property_type=property_type)
    amenities = [a for a in amenities if a]
    results = []
    ci = co = None
    if check_in and check_out:
        ci, co = parse_stay(check_in, check_out)
    ratings = {b.id: b for b in with_ratings(Business.objects.filter(id__in=qs.values("business_id")))}
    for acc in qs:
        if amenities and not set(amenities).issubset(set(acc.amenities)):
            continue
        best = None
        if ci:
            for unit in acc.units.all():
                q = unit_quote(unit, ci, co)
                if q and (best is None or q["total"] < best[1]["total"]):
                    best = (unit, q)
            if best is None:
                continue
            if max_total and best[1]["total"] > Decimal(str(max_total)):
                continue
        b = ratings.get(acc.business_id)
        avg = b.avg_rating if b else None
        reasons = []
        if max_total and best:
            reasons.append("одговара на буџетот")
        if amenities:
            reasons.append("ги има бараните удобности")
        if avg:
            reasons.append(f"оценка {avg:.1f}/5")
        score = (avg or 3.5) + 0.2 * len(set(amenities) & set(acc.amenities))
        if best:
            score -= float(best[1]["total"]) / 1000
        results.append({
            "accommodation": acc,
            "unit": best[0] if best else None,
            "quote": best[1] if best else None,
            "avg_rating": avg,
            "review_count": b.review_count if b else 0,
            "score": score,
            "reason": ", ".join(reasons) or "достапно за избраните датуми",
        })
    results.sort(key=lambda r: r["score"], reverse=True)
    return results
