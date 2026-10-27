import io
import zlib
import random
import urllib.request
from datetime import timedelta
from decimal import Decimal

from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

from accounts.models import User
from businesses.models import AccommodationUnit, BoatDeparture, BoatTour, Business
from destinations.models import Place
from gamification import services as gamification
from gamification.models import PhotoCheckIn, PhotoLike, PlacePhoto
from reservations.models import Reservation, ReservationItem, ReservationStatusHistory
from reviews.models import BusinessReply, Review
from social.models import Friendship

PASSWORD = "Demo12345!"
USER_AGENT = "TravelPlannerMK/1.0 (diploma prototype; demo seed)"

PEOPLE = [
    ("marija.p", "Марија", "Петровска", "Секој викенд на Охрид. Фотографирам изгрејсонца и стари улички."),
    ("stefan.n", "Стефан", "Николовски", "Планинар. Пелистер, Галичица и Шар се мојот втор дом."),
    ("elena.k", "Елена", "Костовска", "Музеи, цркви, фрески — и добра охридска пастрмка после тоа."),
    ("anna.mueller", "Anna", "Müller", "From Munich. Slow travel, lakes and Byzantine churches."),
    ("tom.harris", "Tom", "Harris", "Backpacking the Balkans one bakery at a time."),
    ("lucia.rossi", "Lucia", "Rossi", "Architetta. Byzantine art, old bazaars and golden hour."),
    ("goran.t", "Горан", "Трајковски", "Велосипедист од Битола. Секој сокак го знам на две тркала."),
    ("ivana.d", "Ивана", "Димовска", "Мама на две деца — барам места погодни за семејства."),
]

VISITS = {
    "marija.p": ["ohrid/kaneo", "ohrid/sv-naum", "ohrid/samoilova-tvrdina", "ohrid/kej", "ohrid/plaoshnik", "ohrid/lagadin"],
    "stefan.n": ["bitola/pelister", "ohrid/galicica-vidikovec", "skopje/matka", "skopje/milenium-krst"],
    "elena.k": ["ohrid/sv-sofija", "ohrid/perivlepta", "ohrid/robevi", "ohrid/plaoshnik", "skopje/sv-spas"],
    "anna.mueller": ["ohrid/kaneo", "ohrid/zaliv-na-koskite", "ohrid/sv-naum", "ohrid/anticki-teatar"],
    "tom.harris": ["skopje/kamen-most", "skopje/stara-carsija", "skopje/kale", "skopje/matka", "bitola/sirok-sokak"],
    "lucia.rossi": ["ohrid/sv-sofija", "ohrid/perivlepta", "bitola/heraklea", "skopje/stara-carsija", "ohrid/carsija"],
    "goran.t": ["bitola/sirok-sokak", "bitola/saat-kula", "bitola/heraklea", "bitola/pelister"],
    "ivana.d": ["ohrid/kej", "ohrid/lagadin", "skopje/majka-tereza", "ohrid/izvori-crn-drim"],
}

CAPTIONS_MK = {
    "RELIGIOUS": ["Тишина и фрески што ти го запираат здивот.", "Вреди секој чекор до горе.", "Најубаво рано наутро, пред групите."],
    "HISTORY": ["Поглед од кој не сакаш да заминеш.", "Историја на секој камен.", "Земете вода, сонцето пече."],
    "MUSEUM": ["Одлично водење, прашајте за деталите.", "Мал музеј, многу приказни."],
    "CULTURE": ["Кафе, ѓеврек и луѓе — вистинската чаршија.", "Шетање без мапа, најдобро."],
    "NATURE": ["Водата е бистра како стакло.", "Совршено за пикник со деца.", "Свеж воздух и нула гужва."],
    "VIEWPOINT": ["Целото езеро како на дланка.", "Залезот оттука е обврзен."],
    "BEACH": ["Мирна плажа, топла вода кон крајот на август.", "Чадор, книга и езеро."],
}
CAPTIONS_EN = {
    "RELIGIOUS": ["Frescoes that stop you in your tracks.", "Worth every step up the hill.", "Go early, before the tour groups."],
    "HISTORY": ["A view you don't want to leave.", "History in every stone.", "Bring water, the sun is strong."],
    "MUSEUM": ["Great guide — ask about the details.", "Small museum, lots of stories."],
    "CULTURE": ["Coffee, simit and people watching.", "Best explored without a map."],
    "NATURE": ["Crystal clear water.", "Perfect for a picnic.", "Fresh air, no crowds."],
    "VIEWPOINT": ["The whole lake at your feet.", "Stay for the sunset."],
    "BEACH": ["Quiet beach, warm water in late August.", "Umbrella, a book and the lake."],
}

REVIEWS = [
    ("marija.p", "ACCOMMODATION", 5, {"cleanliness": 5, "location": 5, "comfort": 5, "value": 5, "communication": 5},
     "Терасата гледа директно на езерото, а домаќинката не дочека со домашно слатко. Одиме пак!",
     "Ви благодариме, Марија! Ве очекуваме повторно."),
    ("anna.mueller", "ACCOMMODATION", 4, {"cleanliness": 5, "location": 5, "comfort": 4, "value": 4, "communication": 4},
     "Lovely room in the old town, quiet at night. The stairs are steep with luggage, but the view makes up for it.",
     "Thank you, Anna! We now offer help with luggage from the parking."),
    ("ivana.d", "ACCOMMODATION", 4, {"cleanliness": 4, "location": 5, "comfort": 4, "value": 5, "communication": 5},
     "Апартманот е простран за семејство со две деца, кујната има сè. Паркингот е малку подалеку.", None),
    ("tom.harris", "BOAT_TOUR", 5, {"safety": 5, "punctuality": 5, "service": 5, "communication": 4, "overall": 5},
     "Best way to reach St. Naum — the captain stopped at the springs and told great stories. Bring a jacket for the way back.",
     "Thanks Tom, see you on the next trip!"),
    ("elena.k", "BOAT_TOUR", 4, {"safety": 5, "punctuality": 4, "service": 4, "communication": 4, "overall": 4},
     "Убаво крстарење, тргна десетина минути подоцна, но паузата кај Св. Наум беше доволна.", None),
    ("lucia.rossi", "RESTAURANT", 5, {"food": 5, "service": 5, "atmosphere": 5, "value": 4},
     "Pastrmka alla griglia perfetta e vista sul lago. Prenotate la terrazza al tramonto!",
     "Grazie mille, Lucia!"),
    ("stefan.n", "RESTAURANT", 3, {"food": 4, "service": 2, "atmosphere": 4, "value": 3},
     "Храната е добра, но во петок навечер чекавме долго за сметката. Резервирајте однапред.",
     "Се извинуваме за чекањето — во петоците веќе имаме дополнителен келнер."),
    ("goran.t", "TAXI", 5, {"punctuality": 5, "safety": 5, "service": 5, "communication": 5, "overall": 5},
     "Од аеродромот до Охрид без доцнење, фиксна цена како што пишуваше во понудата.", None),
    ("anna.mueller", "TAXI", 4, {"punctuality": 5, "safety": 4, "service": 4, "communication": 3, "overall": 4},
     "On time and fair price. The driver spoke a little English — the quote in the app helped a lot.", None),
]


def painted(seed, size=(1280, 960)):
    rnd = random.Random(seed)
    w, h = size
    im = Image.new("RGB", size)
    d = ImageDraw.Draw(im)
    top, bottom = (rnd.randint(90, 140), rnd.randint(150, 190), rnd.randint(210, 240)), (250, rnd.randint(200, 230), 170)
    for y in range(h):
        t = y / h
        d.line([(0, y), (w, y)], fill=tuple(int(top[i] * (1 - t) + bottom[i] * t) for i in range(3)))
    d.ellipse([w * 0.7, h * 0.12, w * 0.8, h * 0.25], fill=(255, 226, 150))
    for layer, (shade, base) in enumerate(((60, 0.55), (35, 0.62))):
        pts = [(0, h)] + [(x, h * base - rnd.randint(0, 160) * (1 - layer * 0.4)) for x in range(0, w + 160, 160)] + [(w, h)]
        d.polygon(pts, fill=(shade, 90 + layer * 20, 80 + layer * 10))
    d.rectangle([0, h * 0.68, w, h], fill=(30, 120 + rnd.randint(0, 40), 140 + rnd.randint(0, 40)))
    return im.filter(ImageFilter.GaussianBlur(1.2))


def place_photo(place):
    url = place.image_url or ""
    try:
        if url.startswith("/media/"):
            with default_storage.open(url.removeprefix("/media/")) as fh:
                return Image.open(io.BytesIO(fh.read())).convert("RGB")
        if url.startswith("http"):
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=20) as resp:
                return Image.open(io.BytesIO(resp.read())).convert("RGB")
    except Exception:
        return None
    return None


def variant(base, seed):
    rnd = random.Random(seed)
    w, h = base.size
    scale = rnd.uniform(0.62, 0.86)
    cw, ch = int(w * scale), int(h * scale)
    x, y = rnd.randint(0, w - cw), rnd.randint(0, h - ch)
    im = base.crop((x, y, x + cw, y + ch))
    if rnd.random() < 0.35:
        im = ImageOps.mirror(im)
    im = ImageEnhance.Brightness(im).enhance(rnd.uniform(0.9, 1.12))
    im = ImageEnhance.Contrast(im).enhance(rnd.uniform(0.92, 1.12))
    im = ImageEnhance.Color(im).enhance(rnd.uniform(0.85, 1.2))
    im.thumbnail((1280, 1280))
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=84)
    return buf.getvalue()


class Command(BaseCommand):
    help = "Демо туристи, фото-посети, лајкови, пријателства и рецензии."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true")

    def handle(self, *args, **opts):
        usernames = [p[0] for p in PEOPLE]
        if opts["reset"]:
            Review.objects.filter(user__username__in=usernames).delete()
            User.objects.filter(username__in=usernames).delete()
        elif User.objects.filter(username__in=usernames).exists():
            self.stdout.write("Демо-заедницата веќе постои — прескокнато (--reset за повторно).")
            return
        rnd = random.Random(2026)
        now = timezone.now()
        users = {}
        for username, first, last, bio in PEOPLE:
            u = User.objects.create_user(username=username, email=f"{username}@demo.example.com", password=PASSWORD,
                                         first_name=first, last_name=last, bio=bio)
            users[username] = u

        places = {f"{p.city.slug}/{p.slug}": p for p in Place.objects.select_related("city")}
        bases = {}
        photos = 0
        for username, keys in VISITS.items():
            u = users[username]
            foreign = username in ("anna.mueller", "tom.harris", "lucia.rossi")
            for i, key in enumerate(keys):
                p = places.get(key)
                if not p:
                    continue
                if key not in bases:
                    bases[key] = place_photo(p) or painted(zlib.crc32(key.encode()))
                seed = f"{username}/{key}"
                data = variant(bases[key], seed)
                pool = (CAPTIONS_EN if foreign else CAPTIONS_MK).get(p.category, ["…"])
                text = random.Random(seed).choice(pool)
                source = f" · Демо фотографија, извор: {p.image_credit}" if p.image_credit else " · Демо фотографија"
                try:
                    checkin, _ = gamification.create_checkin(
                        u, p, SimpleUploadedFile(f"{u.username}-{p.slug}.jpg", data, content_type="image/jpeg"),
                        client_lat=p.lat + rnd.uniform(-0.0004, 0.0004), client_lng=p.lng + rnd.uniform(-0.0004, 0.0004),
                        caption=(text + source)[:300])
                except Exception as exc:
                    self.stderr.write(f"  {username} @ {key}: {exc}")
                    continue
                when = now - timedelta(days=rnd.randint(3, 120), hours=rnd.randint(0, 10))
                PhotoCheckIn.objects.filter(pk=checkin.pk).update(created_at=when, taken_at=when)
                PlacePhoto.objects.filter(checkin=checkin).update(created_at=when)
                photos += 1

        likers = list(users.values()) + list(User.objects.filter(username__in=["turist", "host"]))
        likes = 0
        for photo in PlacePhoto.objects.filter(user__in=users.values()):
            for liker in rnd.sample(likers, rnd.randint(0, 6)):
                if liker.id != photo.user_id:
                    PhotoLike.objects.get_or_create(photo=photo, user=liker)
                    likes += 1

        def befriend(a, b, accepted=True):
            f, _ = Friendship.objects.get_or_create(from_user=a, to_user=b)
            if accepted:
                f.status, f.accepted_at = Friendship.Status.ACCEPTED, now - timedelta(days=rnd.randint(1, 60))
                f.save(update_fields=["status", "accepted_at"])

        pairs = [("marija.p", "elena.k"), ("marija.p", "stefan.n"), ("stefan.n", "goran.t"), ("anna.mueller", "lucia.rossi"),
                 ("tom.harris", "anna.mueller"), ("ivana.d", "marija.p"), ("elena.k", "lucia.rossi")]
        for a, b in pairs:
            befriend(users[a], users[b])
        turist = User.objects.filter(username="turist").first()
        if turist:
            for name in ("marija.p", "anna.mueller", "stefan.n"):
                befriend(users[name], turist)
            befriend(users["tom.harris"], turist, accepted=False)
            befriend(turist, users["lucia.rossi"], accepted=False)

        reviews = self.seed_reviews(users, rnd, now)
        self.stdout.write(self.style.SUCCESS(
            f"Демо-заедница: {len(users)} туристи, {photos} фото-посети, {likes} лајкови, "
            f"{Friendship.objects.count()} пријателства/барања, {reviews} рецензии. Лозинка: {PASSWORD}"))

    @transaction.atomic
    def seed_reviews(self, users, rnd, now):
        by_type = {}
        for b in Business.objects.filter(name__endswith="(демо)", verification_status=Business.Verification.APPROVED):
            by_type.setdefault(b.type, []).append(b)
        host = User.objects.filter(username="host").first()
        made = 0
        for i, (username, kind, rating, dims, comment, reply) in enumerate(REVIEWS):
            options = by_type.get(kind)
            if not options:
                continue
            b = options[i % len(options)]
            u = users[username]
            days_ago = rnd.randint(8, 90)
            done = now - timedelta(days=days_ago)
            res = Reservation(user=u, business=b, service_type=kind, status=Reservation.Status.COMPLETED,
                              confirmed_at=done - timedelta(days=5), completed_at=done)
            price = Decimal("0")
            if kind == "ACCOMMODATION":
                unit = AccommodationUnit.objects.filter(accommodation__business=b).first()
                nights = rnd.randint(2, 4)
                res.accommodation_unit, res.guests = unit, rnd.randint(2, 4)
                res.check_in, res.check_out = (done - timedelta(days=nights)).date(), done.date()
                price = Decimal(45 * nights)
                items = [(f"{nights} ноќи (демо)", nights, Decimal("45"))]
            elif kind == "BOAT_TOUR":
                tour = BoatTour.objects.filter(business=b).first()
                if not tour:
                    continue
                dep = BoatDeparture.objects.create(tour=tour, starts_at=done, capacity=20, reserved_seats=2)
                res.boat_departure, res.guests = dep, 2
                price = tour.price_per_person * 2
                items = [("2 места (демо)", 2, tour.price_per_person)]
            elif kind == "RESTAURANT":
                res.reserved_for, res.guests = done, rnd.randint(2, 5)
                items = []
            else:
                res.reserved_for, res.guests = done, rnd.randint(1, 3)
                res.pickup, res.destination = "Аеродром Охрид", "Охрид, стар град"
                res.quoted_price = price = Decimal("15")
                items = [("Превоз, фиксна цена (демо)", 1, Decimal("15"))]
            res.total_price = price or None
            res.save()
            Reservation.objects.filter(pk=res.pk).update(requested_at=done - timedelta(days=7))
            for desc, qty, unit_price in items:
                ReservationItem.objects.create(reservation=res, description=desc, quantity=qty, unit_price=unit_price,
                                               total_price=unit_price * qty)
            for a, z in (("", "PENDING"), ("PENDING", "CONFIRMED"), ("CONFIRMED", "COMPLETED")):
                ReservationStatusHistory.objects.create(reservation=res, from_status=a, to_status=z, actor=host)
            review = Review.objects.create(user=u, business=b, reservation=res, rating=rating, dimension_scores=dims,
                                           comment=comment)
            Review.objects.filter(pk=review.pk).update(created_at=done + timedelta(days=1))
            if reply and host:
                BusinessReply.objects.create(review=review, business_user=host, reply_text=reply)
            made += 1
        return made
