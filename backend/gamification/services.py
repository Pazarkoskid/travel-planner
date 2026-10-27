import hashlib
from datetime import datetime, timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Count
from django.utils import timezone
from PIL import Image

from core.exceptions import ServiceError

from . import catalog
from core.geo import haversine_m
from destinations.models import City, Place
from notifications.models import notify

from .models import Badge, CityAchievement, PhotoCheckIn, PlacePhoto, UserBadge

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}


def _to_deg(value, ref):
    d, m, s = (float(x) for x in value)
    deg = d + m / 60 + s / 3600
    return -deg if ref in ("S", "W") else deg


def read_exif(fileobj):
    lat = lng = taken = None
    try:
        fileobj.seek(0)
        img = Image.open(fileobj)
        exif = img.getexif()
        gps = exif.get_ifd(0x8825)
        if gps and 2 in gps and 4 in gps:
            lat = _to_deg(gps[2], gps.get(1, "N"))
            lng = _to_deg(gps[4], gps.get(3, "E"))
        raw = exif.get_ifd(0x8769).get(36867) or exif.get(306)
        if raw:
            taken = timezone.make_aware(datetime.strptime(str(raw), "%Y:%m:%d %H:%M:%S"))
    except Exception:
        pass
    finally:
        fileobj.seek(0)
    return lat, lng, taken


def validate_image(fileobj):
    if fileobj.size > settings.MAX_PHOTO_BYTES:
        raise ServiceError("Фотографијата е преголема.", code="file_too_large")
    try:
        fileobj.seek(0)
        img = Image.open(fileobj)
        fmt = img.format
        img.verify()
    except Exception:
        raise ServiceError("Датотеката не е валидна слика.", code="invalid_image")
    finally:
        fileobj.seek(0)
    if fmt not in ALLOWED_FORMATS:
        raise ServiceError("Дозволени формати: JPEG, PNG, WEBP.", code="invalid_image")
    h = hashlib.sha256()
    for chunk in fileobj.chunks():
        h.update(chunk)
    fileobj.seek(0)
    return h.hexdigest()


def decide(place, client, exif):
    radius = place.checkin_radius_m or settings.CHECKIN_DEFAULT_RADIUS_M
    notes = []
    client_d = haversine_m(*client, place.lat, place.lng) if client else None
    exif_d = haversine_m(*exif, place.lat, place.lng) if exif else None
    distance = client_d if client_d is not None else exif_d
    if client_d is not None and client_d <= radius:
        if exif_d is not None and exif_d > radius * 5:
            notes.append("GPS од уредот и EXIF значително се разликуваат — рачна проверка.")
            return PhotoCheckIn.Status.PENDING, distance, notes
        notes.append(f"Локацијата на уредот е во радиус од {radius} m.")
        return PhotoCheckIn.Status.APPROVED, distance, notes
    if exif_d is not None and exif_d <= radius:
        notes.append("Локацијата е само од EXIF — потребна е рачна проверка.")
        return PhotoCheckIn.Status.PENDING, distance, notes
    known = [d for d in (client_d, exif_d) if d is not None]
    if known and min(known) > radius * 10:
        notes.append(f"Локацијата е премногу далеку од местото (~{int(min(known))} m).")
        return PhotoCheckIn.Status.REJECTED, distance, notes
    if not known:
        notes.append("Нема GPS податоци — рачна проверка.")
    else:
        notes.append("Локацијата е надвор од дозволениот радиус — рачна проверка.")
    return PhotoCheckIn.Status.PENDING, distance, notes


def create_checkin(user, place, image, client_lat=None, client_lng=None, caption="", is_public=True):
    if place.status != Place.Status.VERIFIED:
        raise ServiceError("Местото не е во проверениот каталог.", code="invalid_place")
    digest = validate_image(image)
    if PhotoCheckIn.objects.filter(image_sha256=digest).exists():
        raise ServiceError("Оваа фотографија веќе е прикачена.", code="duplicate_photo", status_code=409)
    exif_lat, exif_lng, taken = read_exif(image)
    client = (float(client_lat), float(client_lng)) if client_lat is not None and client_lng is not None else None
    exif = (exif_lat, exif_lng) if exif_lat is not None else None
    status, distance, notes = decide(place, client, exif)
    if taken and taken > timezone.now() + timedelta(hours=1):
        notes.append("EXIF датумот е во иднина — игнориран.")
        taken = None
    with transaction.atomic():
        checkin = PhotoCheckIn.objects.create(
            user=user, place=place, image=image, image_sha256=digest, client_lat=client[0] if client else None,
            client_lng=client[1] if client else None, exif_lat=exif_lat, exif_lng=exif_lng, taken_at=taken,
            distance_m=round(distance, 1) if distance is not None else None, status=status, verification_notes=notes,
        )
        PlacePhoto.objects.create(checkin=checkin, place=place, user=user, caption=caption[:300], is_public=is_public)
        unlocked = award_for_checkin(checkin) if status == PhotoCheckIn.Status.APPROVED else []
    return checkin, unlocked


def ensure_city_badges(city):
    specs = [
        (f"city-{city.slug}-local", f"Локален авантурист — {city.name}", "5 различни места во градот",
         Badge.Level.LOCAL_ADVENTURER, "🧭"),
        (f"city-{city.slug}-50", f"Градски истражувач — {city.name}", "50% од задолжителните знаменитости",
         Badge.Level.CITY_EXPLORER, "🗺️"),
        (f"city-{city.slug}-100", f"{city.name} 100% — Мајстор на градот", "Сите задолжителни знаменитости",
         Badge.Level.CITY_MASTER, "👑"),
    ]
    out = {}
    for code, name, desc, level, icon in specs:
        out[level], _ = Badge.objects.get_or_create(
            code=code, defaults={"name": name, "description": desc, "kind": Badge.Kind.LEVEL, "level": level,
                                 "city": city, "icon": icon, "art": catalog.art_for_code(code), "sort": 60 if code.endswith("-100") else 300})
    return out


def ensure_place_badge(place):
    code = f"place-{place.city.slug}-{place.slug}"
    badge, _ = Badge.objects.get_or_create(
        code=code,
        defaults={"name": place.name, "description": f"Документирана посета на {place.name}",
                  "kind": Badge.Kind.PLACE, "place": place, "city": place.city, "icon": "📸",
                  "art": catalog.art_for_code(code), "sort": 200})
    return badge


def ensure_global_badges():
    explorer, _ = Badge.objects.get_or_create(code="explorer", defaults={
        "name": "Истражувач", "description": "Прво документирано место", "kind": Badge.Kind.LEVEL,
        "level": Badge.Level.EXPLORER, "icon": "🌱", "art": catalog.art_for_code("explorer"), "sort": 50})
    mk, _ = Badge.objects.get_or_create(code="macedonia-explorer", defaults={
        "name": "Истражувач на Македонија", "description": "100% во повеќе градови", "kind": Badge.Kind.LEVEL,
        "level": Badge.Level.MACEDONIA_EXPLORER, "icon": "🇲🇰", "art": catalog.art_for_code("macedonia-explorer"),
        "sort": 99})
    return explorer, mk


def _grant(user, badge, checkin, unlocked):
    try:
        with transaction.atomic():
            _, created = UserBadge.objects.get_or_create(user=user, badge=badge, defaults={"source_checkin": checkin})
    except IntegrityError:
        created = False
    if created:
        unlocked.append(badge)
        notify(user, "badge", f"Нов печат: {badge.name}", badge.description, badge)


def recompute_city(user, city):
    approved = PhotoCheckIn.objects.filter(user=user, status=PhotoCheckIn.Status.APPROVED, place__city=city)
    documented_any = approved.values("place").distinct().count()
    required_total = Place.objects.filter(city=city, status=Place.Status.VERIFIED, is_required_landmark=True).count()
    documented_required = (approved.filter(place__is_required_landmark=True, place__status=Place.Status.VERIFIED)
                           .values("place").distinct().count())
    percent = round(documented_required / required_total * 100, 1) if required_total else 0.0
    ach, _ = CityAchievement.objects.update_or_create(
        user=user, city=city, defaults={"documented_any": documented_any, "required_total": required_total,
                                        "documented_required": documented_required, "percent": percent})
    return ach


def award_for_checkin(checkin):
    user, place, city = checkin.user, checkin.place, checkin.place.city
    unlocked = []
    explorer, mk = ensure_global_badges()
    _grant(user, ensure_place_badge(place), checkin, unlocked)
    _grant(user, explorer, checkin, unlocked)
    ach = recompute_city(user, city)
    levels = ensure_city_badges(city)
    if ach.documented_any >= 5:
        _grant(user, levels[Badge.Level.LOCAL_ADVENTURER], checkin, unlocked)
    if ach.required_total and ach.percent >= 50:
        _grant(user, levels[Badge.Level.CITY_EXPLORER], checkin, unlocked)
    if ach.required_total and ach.percent >= 100:
        _grant(user, levels[Badge.Level.CITY_MASTER], checkin, unlocked)
        cities_with_list = (City.objects.annotate(n=Count("places", filter=_required_q())).filter(n__gt=0).count())
        needed = max(1, min(settings.MACEDONIA_EXPLORER_MIN_CITIES, cities_with_list))
        if CityAchievement.objects.filter(user=user, percent__gte=100).count() >= needed and needed > 1:
            _grant(user, mk, checkin, unlocked)
    award_rule_badges(user, checkin, unlocked)
    return unlocked


def rule_met(rule, stats):
    if not rule:
        return False
    if "city" in rule:
        return rule["city"] in stats["cities"]
    if "places" in rule:
        return len(stats["places"] & set(rule["places"])) >= rule.get("min", 1)
    if "categories" in rule:
        return sum(stats["categories"][c] for c in rule["categories"]) >= rule.get("min", 1)
    if "photos" in rule:
        return stats["photos"] >= rule["photos"]
    return False


def user_stats(user):
    from collections import Counter

    approved = PhotoCheckIn.objects.filter(user=user, status=PhotoCheckIn.Status.APPROVED)
    rows = set(approved.values_list("place_id", "place__city__slug", "place__slug", "place__category"))
    return {
        "places": {f"{c}/{s}" for _, c, s, _ in rows},
        "cities": {c for _, c, _, _ in rows},
        "categories": Counter(cat for _, _, _, cat in rows),
        "photos": approved.count(),
    }


def award_rule_badges(user, checkin=None, unlocked=None):
    unlocked = [] if unlocked is None else unlocked
    stats = user_stats(user)
    for badge in Badge.objects.filter(kind__in=[Badge.Kind.REGION, Badge.Kind.CATEGORY], available=True):
        if rule_met(badge.rule, stats):
            _grant(user, badge, checkin, unlocked)
    return unlocked


def _required_q():
    from django.db.models import Q

    return Q(places__is_required_landmark=True, places__status=Place.Status.VERIFIED)


def review_checkin(checkin_id, moderator, approve, note=""):
    with transaction.atomic():
        c = PhotoCheckIn.objects.select_for_update().get(pk=checkin_id)
        if c.status != PhotoCheckIn.Status.PENDING:
            raise ServiceError("Проверката е веќе завршена.", code="already_reviewed")
        c.status = PhotoCheckIn.Status.APPROVED if approve else PhotoCheckIn.Status.REJECTED
        c.reviewed_by = moderator
        c.verification_notes = c.verification_notes + [f"Модератор: {note or ('одобрено' if approve else 'одбиено')}"]
        c.save()
        unlocked = award_for_checkin(c) if approve else []
    if not approve:
        notify(c.user, "checkin", "Фото-посетата не е одобрена", note, c)
    return c, unlocked
