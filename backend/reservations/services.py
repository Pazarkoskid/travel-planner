"""Резервациска логика. Секоја промена на капацитет е атомска.

Капацитетот се зафаќа при креирање на барањето (PENDING) и се ослободува при
REJECTED/CANCELLED. Финалната проверка е условен UPDATE (… WHERE available >= n),
па две паралелни барања не можат да го надминат капацитетот.
"""
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from businesses.models import AccommodationAvailability, BoatDeparture, Business
from businesses.services import nights, parse_stay
from core.exceptions import ServiceError
from core.models import audit
from notifications.models import notify

from .models import Reservation, ReservationItem, ReservationStatusHistory

S = Reservation.Status


def _existing_by_key(user, key):
    if key:
        return Reservation.objects.filter(user=user, idempotency_key=key).first()
    return None


def _check_business(business, expected_type):
    if business.verification_status != Business.Verification.APPROVED:
        raise ServiceError("Бизнисот не е одобрен.", code="business_not_approved")
    if business.type != expected_type:
        raise ServiceError("Погрешен тип услуга.", code="wrong_service_type")


def _record(res, from_status, actor, note=""):
    ReservationStatusHistory.objects.create(reservation=res, from_status=from_status or "", to_status=res.status,
                                            actor=actor, note=note)


def _notify_business(res, title):
    notify(res.business.owner, "reservation", title, f"Резервација #{res.pk}", res)


def create_accommodation_booking(user, unit, check_in, check_out, guests, notes="", idempotency_key=None):
    if (existing := _existing_by_key(user, idempotency_key)):
        return existing
    acc = unit.accommodation
    _check_business(acc.business, Business.Type.ACCOMMODATION)
    ci, co = parse_stay(check_in, check_out)
    if guests < 1 or guests > acc.max_guests:
        raise ServiceError(f"Бројот гости мора да е 1–{acc.max_guests}.", code="capacity_exceeded")
    stay = nights(ci, co)
    try:
        with transaction.atomic():
            rows = list(AccommodationAvailability.objects.select_for_update()
                        .filter(unit=unit, date__in=stay).order_by("date"))
            if len(rows) != len(stay):
                raise ServiceError("Некои ноќи немаат дефинирана достапност.", code="not_available")
            # Атомско намалување: успева само ако секоја ноќ има слободна единица.
            updated = (AccommodationAvailability.objects
                       .filter(unit=unit, date__in=stay, available_units__gte=1)
                       .update(available_units=F("available_units") - 1))
            if updated != len(stay):
                raise ServiceError("Објектот не е достапен за сите избрани ноќи.", code="not_available")
            subtotal = sum((r.price_per_night for r in rows), Decimal("0"))
            total = subtotal + (acc.cleaning_fee or 0)
            res = Reservation.objects.create(
                user=user, business=acc.business, service_type=Reservation.ServiceType.ACCOMMODATION,
                accommodation_unit=unit, check_in=ci, check_out=co, guests=guests, notes=notes,
                total_price=total, idempotency_key=idempotency_key,
            )
            ReservationItem.objects.bulk_create(
                [ReservationItem(reservation=res, description=f"Ноќ {r.date}", quantity=1,
                                 unit_price=r.price_per_night, total_price=r.price_per_night) for r in rows]
                + ([ReservationItem(reservation=res, description="Чистење", quantity=1,
                                    unit_price=acc.cleaning_fee, total_price=acc.cleaning_fee)]
                   if acc.cleaning_fee else [])
            )
            _record(res, None, user, "Креирано барање")
    except IntegrityError:
        if (existing := _existing_by_key(user, idempotency_key)):
            return existing
        raise
    _notify_business(res, "Ново барање за сместување")
    audit(user, "reservation.create", res)
    return res


def create_boat_reservation(user, departure, seats, notes="", idempotency_key=None):
    if (existing := _existing_by_key(user, idempotency_key)):
        return existing
    tour = departure.tour
    _check_business(tour.business, Business.Type.BOAT_TOUR)
    if seats < 1:
        raise ServiceError("Барем едно место.", code="invalid_seats")
    with transaction.atomic():
        updated = BoatDeparture.objects.filter(
            pk=departure.pk, status="SCHEDULED", starts_at__gt=timezone.now(),
            reserved_seats__lte=F("capacity") - seats,
        ).update(reserved_seats=F("reserved_seats") + seats)
        if updated != 1:
            raise ServiceError("Нема доволно слободни места или поаѓањето не е достапно.", code="not_available")
        total = tour.price_per_person * seats
        res = Reservation.objects.create(
            user=user, business=tour.business, service_type=Reservation.ServiceType.BOAT_TOUR,
            boat_departure=departure, guests=seats, notes=notes, total_price=total, idempotency_key=idempotency_key,
        )
        ReservationItem.objects.create(reservation=res, description=tour.title, quantity=seats,
                                       unit_price=tour.price_per_person, total_price=total)
        _record(res, None, user, "Креирано барање")
    _notify_business(res, "Ново барање за бродска тура")
    audit(user, "reservation.create", res)
    return res


def create_restaurant_request(user, business, reserved_for, guests, notes="", idempotency_key=None):
    if (existing := _existing_by_key(user, idempotency_key)):
        return existing
    _check_business(business, Business.Type.RESTAURANT)
    if not reserved_for or reserved_for <= timezone.now():
        raise ServiceError("Терминот мора да е во иднина.", code="invalid_datetime")
    max_party = getattr(getattr(business, "restaurant", None), "max_party_size", 12)
    if guests < 1 or guests > max_party:
        raise ServiceError(f"Бројот гости мора да е 1–{max_party}.", code="capacity_exceeded")
    with transaction.atomic():
        res = Reservation.objects.create(
            user=user, business=business, service_type=Reservation.ServiceType.RESTAURANT,
            reserved_for=reserved_for, guests=guests, notes=notes, idempotency_key=idempotency_key,
        )
        _record(res, None, user, "Барање маса — не е гаранција за достапност")
    _notify_business(res, "Ново барање за маса")
    return res


def create_taxi_request(user, business, reserved_for, guests, pickup, destination, notes="", idempotency_key=None):
    if (existing := _existing_by_key(user, idempotency_key)):
        return existing
    _check_business(business, Business.Type.TAXI)
    if not reserved_for or reserved_for <= timezone.now():
        raise ServiceError("Терминот мора да е во иднина.", code="invalid_datetime")
    cap = getattr(getattr(business, "taxi", None), "passenger_capacity", 4)
    if guests < 1 or guests > cap:
        raise ServiceError(f"Бројот патници мора да е 1–{cap}.", code="capacity_exceeded")
    if not pickup or not destination:
        raise ServiceError("Потребни се место на преземање и дестинација.", code="invalid_route")
    with transaction.atomic():
        res = Reservation.objects.create(
            user=user, business=business, service_type=Reservation.ServiceType.TAXI, reserved_for=reserved_for,
            guests=guests, pickup=pickup, destination=destination, notes=notes, idempotency_key=idempotency_key,
        )
        _record(res, None, user, "Барање превоз")
    _notify_business(res, "Ново барање за такси")
    return res


def _release_capacity(res):
    if res.service_type == Reservation.ServiceType.ACCOMMODATION and res.accommodation_unit_id:
        AccommodationAvailability.objects.filter(
            unit_id=res.accommodation_unit_id, date__in=nights(res.check_in, res.check_out)
        ).update(available_units=F("available_units") + 1)
    elif res.service_type == Reservation.ServiceType.BOAT_TOUR and res.boat_departure_id:
        BoatDeparture.objects.filter(pk=res.boat_departure_id, reserved_seats__gte=res.guests).update(
            reserved_seats=F("reserved_seats") - res.guests
        )


# Дозволени транзиции: (од, во) -> кој смее ("business" / "tourist").
TRANSITIONS = {
    (S.PENDING, S.CONFIRMED): "business",
    (S.PENDING, S.REJECTED): "business",
    (S.PENDING, S.ALTERNATIVE_PROPOSED): "business",
    (S.PENDING, S.QUOTED): "business",
    (S.ALTERNATIVE_PROPOSED, S.CONFIRMED): "tourist",
    (S.QUOTED, S.CONFIRMED): "tourist",
    (S.CONFIRMED, S.IN_PROGRESS): "business",
    (S.CONFIRMED, S.COMPLETED): "business",
    (S.IN_PROGRESS, S.COMPLETED): "business",
    (S.CONFIRMED, S.CANCELLED): "both",
    (S.PENDING, S.CANCELLED): "tourist",
    (S.ALTERNATIVE_PROPOSED, S.CANCELLED): "tourist",
    (S.QUOTED, S.CANCELLED): "tourist",
}

ACTION_TO_STATUS = {
    "confirm": S.CONFIRMED, "reject": S.REJECTED, "propose": S.ALTERNATIVE_PROPOSED, "quote": S.QUOTED,
    "start": S.IN_PROGRESS, "complete": S.COMPLETED, "cancel": S.CANCELLED, "accept": S.CONFIRMED,
}


def transition(res_id, to_status, actor, note="", proposed_datetime=None, quoted_price=None):
    with transaction.atomic():
        res = Reservation.objects.select_for_update().select_related("business", "boat_departure__tour").get(pk=res_id)
        allowed = TRANSITIONS.get((res.status, to_status))
        if not allowed:
            raise ServiceError(f"Не е дозволена промена {res.status} → {to_status}.", code="invalid_transition")
        is_business = res.business.can_manage(actor)
        is_tourist = res.user_id == actor.id
        if allowed == "business" and not is_business:
            raise ServiceError("Само бизнисот може да ја направи оваа промена.", code="forbidden", status_code=403)
        if allowed == "tourist" and not is_tourist:
            raise ServiceError("Само корисникот може да ја направи оваа промена.", code="forbidden", status_code=403)
        if allowed == "both" and not (is_business or is_tourist):
            raise ServiceError("Немате пристап.", code="forbidden", status_code=403)

        now = timezone.now()
        if to_status == S.ALTERNATIVE_PROPOSED:
            if res.service_type not in (Reservation.ServiceType.RESTAURANT, Reservation.ServiceType.TAXI):
                raise ServiceError("Алтернативен термин е достапен за ресторан/такси.", code="invalid_transition")
            if not proposed_datetime or proposed_datetime <= now:
                raise ServiceError("Потребен е иден предложен термин.", code="invalid_datetime")
            res.proposed_datetime = proposed_datetime
        if to_status == S.QUOTED:
            if res.service_type != Reservation.ServiceType.TAXI or quoted_price is None or Decimal(str(quoted_price)) <= 0:
                raise ServiceError("Понуда со цена важи само за такси.", code="invalid_quote")
            res.quoted_price = Decimal(str(quoted_price))
        if to_status == S.CONFIRMED and res.status == S.ALTERNATIVE_PROPOSED:
            res.reserved_for = res.proposed_datetime
        if to_status == S.CONFIRMED and res.status == S.QUOTED:
            res.total_price = res.quoted_price
        if to_status == S.CANCELLED and is_tourist and not is_business:
            start = res.check_in if res.check_in else None
            if start and start <= timezone.localdate():
                raise ServiceError("Престојот веќе започнал; откажувањето не е можно преку апликацијата.",
                                   code="cancel_window_closed")
        if to_status == S.COMPLETED:
            end = res.service_end
            if end and end > now:
                raise ServiceError("Услугата сè уште не е завршена.", code="not_finished")
            res.completed_at = now
        if to_status == S.CONFIRMED:
            res.confirmed_at = now
        if to_status in (S.CANCELLED, S.REJECTED):
            if res.status in Reservation.HOLDING:
                _release_capacity(res)
            res.cancelled_at = now
        old = res.status
        res.status = to_status
        if note:
            res.business_message = note if is_business else res.business_message
        res.save()
        _record(res, old, actor, note)

    target = res.user if is_business and not is_tourist else res.business.owner
    notify(target, "reservation_status", f"Резервација #{res.pk}: {res.get_status_display()}", note, res)
    audit(actor, "reservation.transition", res, old=old, new=to_status)
    return res
