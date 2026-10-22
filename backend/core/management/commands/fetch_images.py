"""Презема слободни (CC/PD) фотографии за градовите и местата од Wikipedia/Wikimedia Commons.

    python manage.py fetch_images            # само каде што нема слика
    python manage.py fetch_images --force    # ги заменува постоечките

За секое место се пребарува англиската Wikipedia (поле wiki_query), потоа македонската
(име на местото), па Commons директно. Се зема слободна слика (pilicense=free), а од Commons
URL со стандардна ширина 1280px (Wikimedia ограничува нестандардни ширини), авторот и лиценцата.
Меѓу барањата има пауза, а при HTTP 429 се чека и се пробува повторно.

Сликите НЕ се линкуваат директно (Wikimedia го ограничува вградувањето на сликички на други сајтови):
се преземаат, се намалуваат на најмногу 1600px (JPEG) и се зачувуваат во нашиот storage —
Supabase Storage на Render, локално media/. Авторот и лиценцата остануваат во image_credit.

    python manage.py fetch_images              # пребарај што нема слика + префрли ги постоечките Wikimedia линкови
    python manage.py fetch_images --force      # пребарај и замени ги сите
    python manage.py fetch_images --no-store   # само линкови (стар начин) Авторот и лиценцата се зачувуваат во image_credit и се
прикажуваат под фотографијата во апликацијата.
"""
import html
import io
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from PIL import Image

from destinations.models import City, Place

USER_AGENT = "TravelPlannerMK/1.0 (diploma prototype; https://github.com/pazarkoskid)"
WIKI_API = "https://en.wikipedia.org/w/api.php"
MK_WIKI_API = "https://mk.wikipedia.org/w/api.php"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
SKIP = re.compile(r"(\.svg$|map|locator|flag|coat_of_arms|logo|location)", re.I)
WIDTH = 1280  # стандардна ширина; нестандардните (пр. 1600) Wikimedia ги ограничува
FALLBACK_WIDTH = 960
WIKIMEDIA = re.compile(r"^https?://upload\.wikimedia\.org/")
MAX_SIDE = 1600
OLD_WIDTHS = re.compile(r"/(1600)px-")  # линкови од постарата верзија → се преземаат наново
PAUSE = 0.4


def get_json(url, params, timeout=15, attempts=4):
    full = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(full, headers={"User-Agent": USER_AGENT})
    for attempt in range(attempts):
        try:
            time.sleep(PAUSE)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 503) and attempt < attempts - 1:
                wait = int(exc.headers.get("Retry-After") or 0) or 2 ** (attempt + 1)
                time.sleep(min(wait, 30))
                continue
            raise


def strip_tags(value):
    return html.unescape(re.sub(r"<[^>]+>", "", value or "")).strip()


def _search_pageimage(api, query):
    data = get_json(api, {
        "action": "query", "format": "json", "formatversion": 2, "generator": "search",
        "gsrsearch": query, "gsrlimit": 3, "prop": "pageimages", "piprop": "name", "pilicense": "free",
    })
    pages = sorted(data.get("query", {}).get("pages", []), key=lambda p: p.get("index", 99))
    for page in pages:
        name = page.get("pageimage")
        if name and not SKIP.search(name):
            return name
    return None


def _search_commons(query):
    data = get_json(COMMONS_API, {
        "action": "query", "format": "json", "formatversion": 2, "list": "search", "srsearch": f"{query} filetype:bitmap",
        "srnamespace": 6, "srlimit": 5,
    })
    for hit in data.get("query", {}).get("search", []):
        name = hit["title"].split(":", 1)[-1]
        if not SKIP.search(name):
            return name
    return None


def find_file(query, mk_query=None):
    """Име на датотека (без 'File:'): en.wikipedia → mk.wikipedia → Commons."""
    return (_search_pageimage(WIKI_API, query)
            or (mk_query and _search_pageimage(MK_WIKI_API, mk_query))
            or _search_commons(query))


def file_info(filename):
    """Враќа (url, credit) за датотеката од Commons (или en.wikipedia ако не е на Commons)."""
    for api in (COMMONS_API, WIKI_API):
        data = get_json(api, {
            "action": "query", "format": "json", "formatversion": 2, "titles": f"File:{filename}",
            "prop": "imageinfo", "iiprop": "url|extmetadata", "iiurlwidth": WIDTH,
        })
        pages = data.get("query", {}).get("pages", [])
        if not pages or pages[0].get("missing") or not pages[0].get("imageinfo"):
            continue
        info = pages[0]["imageinfo"][0]
        meta = info.get("extmetadata", {})
        artist = strip_tags(meta.get("Artist", {}).get("value", "")) or "непознат автор"
        license_name = strip_tags(meta.get("LicenseShortName", {}).get("value", "")) or "слободна лиценца"
        url = info.get("thumburl") or info.get("url")
        return url, f"Фото: {artist[:120]}, {license_name}, Wikimedia Commons"
    return None, None


def download(url, timeout=30):
    """Ја презема сликата (со User-Agent и повторен обид при 429). При грешка за сликичка пробува 960px."""
    candidates = [url]
    m = re.search(r"/(\d+)px-", url)
    if m and int(m[1]) != FALLBACK_WIDTH:
        candidates.append(url.replace(f"/{m[1]}px-", f"/{FALLBACK_WIDTH}px-"))
    last = None
    for candidate in candidates:
        for attempt in range(3):
            try:
                time.sleep(PAUSE)
                req = urllib.request.Request(candidate, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    return resp.read()
            except urllib.error.HTTPError as exc:
                last = exc
                if exc.code in (429, 503) and attempt < 2:
                    time.sleep(min(int(exc.headers.get("Retry-After") or 0) or 2 ** (attempt + 1), 30))
                    continue
                break
    raise last or RuntimeError("download failed")


def store_image(obj, data):
    """Намалува и зачувува како JPEG во storage; враќа јавен URL."""
    im = Image.open(io.BytesIO(data))
    im = im.convert("RGB")
    im.thumbnail((MAX_SIDE, MAX_SIDE))
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=82, optimize=True, progressive=True)
    kind = "cities" if isinstance(obj, City) else f"places/{obj.city.slug}"
    name = default_storage.save(f"photos/{kind}/{obj.slug}.jpg", ContentFile(buf.getvalue()))
    return default_storage.url(name)


class Command(BaseCommand):
    help = "Презема фотографии за градови и места од Wikimedia Commons (со автор и лиценца)."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Замени ги и постоечките слики")
        parser.add_argument("--no-store", action="store_true", help="Не ги презема сликите, само линк (не се препорачува)")

    def handle(self, *args, **opts):
        objects = list(City.objects.all()) + list(Place.objects.select_related("city"))
        # Зачувување само кога има траен storage (Supabase) или локален развој; на Render без
        # Supabase дискот е привремен и /media не се сервира → тогаш остануваат линкови.
        store = not opts["no_store"] and (bool(settings.SUPABASE_S3_ENDPOINT) or settings.DEBUG)
        if not opts["no_store"] and not store:
            self.stdout.write(self.style.WARNING(
                "Нема Supabase Storage (SUPABASE_S3_*) — сликите остануваат како линкови до Wikimedia."))
        ok = moved = skipped = failed = 0
        for obj in objects:
            linked = bool(obj.image_url) and bool(WIKIMEDIA.search(obj.image_url))
            if obj.image_url and not opts["force"] and not (store and linked) and not OLD_WIDTHS.search(obj.image_url):
                skipped += 1
                continue
            try:
                if obj.image_url and linked and not opts["force"]:
                    # Веќе има слободна слика (автор и лиценца се зачувани) — само ја префрламе кај нас.
                    url, credit, label = OLD_WIDTHS.sub(f"/{WIDTH}px-", obj.image_url), obj.image_credit, "префрлена"
                else:
                    query = obj.wiki_query or (f"{obj.name} {obj.city.name}" if isinstance(obj, Place) else obj.name)
                    mk_query = f"{obj.name} {obj.city.name}" if isinstance(obj, Place) else obj.name
                    filename = find_file(query, mk_query)
                    url, credit = file_info(filename) if filename else (None, None)
                    label = filename
                    if not url:
                        self.stdout.write(f"  {obj}: нема слободна слика за „{query}“")
                        failed += 1
                        continue
                if store:
                    url = store_image(obj, download(url))
            except Exception as exc:  # мрежа, timeout, променет API, неважечка слика
                self.stderr.write(f"  {obj}: грешка ({exc})")
                failed += 1
                continue
            obj.image_url, obj.image_credit = url, (credit or "")[:300]
            obj.save(update_fields=["image_url", "image_credit"])
            if label == "префрлена":
                moved += 1
            else:
                ok += 1
            self.stdout.write(f"  {obj}: {label} → {url}")
        self.stdout.write(self.style.SUCCESS(
            f"Готово: {ok} нови, {moved} префрлени во нашиот storage, {skipped} постоечки, {failed} без слика."))
