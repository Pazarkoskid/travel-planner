"""Презема слободни (CC/PD) фотографии за градовите и местата од Wikipedia/Wikimedia Commons.

    python manage.py fetch_images            # само каде што нема слика
    python manage.py fetch_images --force    # ги заменува постоечките

За секое место се пребарува англиската Wikipedia (поле wiki_query), се зема главната
слободна слика на статијата (pilicense=free), па од Commons се читаат URL со ширина
1600px, авторот и лиценцата. Авторот и лиценцата се зачувуваат во image_credit и се
прикажуваат под фотографијата во апликацијата.
"""
import html
import json
import re
import urllib.parse
import urllib.request

from django.core.management.base import BaseCommand

from destinations.models import City, Place

USER_AGENT = "TravelPlannerMK/1.0 (diploma prototype; https://github.com/pazarkoskid)"
WIKI_API = "https://en.wikipedia.org/w/api.php"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
SKIP = re.compile(r"(\.svg$|map|locator|flag|coat_of_arms|logo|location)", re.I)
WIDTH = 1600


def get_json(url, params, timeout=15):
    full = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(full, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def strip_tags(value):
    return html.unescape(re.sub(r"<[^>]+>", "", value or "")).strip()


def find_file(query):
    """Враќа име на датотека (без 'File:') од најдобрата Wikipedia статија за поимот."""
    data = get_json(WIKI_API, {
        "action": "query", "format": "json", "formatversion": 2, "generator": "search",
        "gsrsearch": query, "gsrlimit": 3, "prop": "pageimages", "piprop": "name", "pilicense": "free",
    })
    pages = sorted(data.get("query", {}).get("pages", []), key=lambda p: p.get("index", 99))
    for page in pages:
        name = page.get("pageimage")
        if name and not SKIP.search(name):
            return name
    return None


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


class Command(BaseCommand):
    help = "Презема фотографии за градови и места од Wikimedia Commons (со автор и лиценца)."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Замени ги и постоечките слики")

    def handle(self, *args, **opts):
        objects = list(City.objects.all()) + list(Place.objects.select_related("city"))
        ok = skipped = failed = 0
        for obj in objects:
            if obj.image_url and not opts["force"]:
                skipped += 1
                continue
            query = obj.wiki_query or (f"{obj.name} {obj.city.name}" if isinstance(obj, Place) else obj.name)
            try:
                filename = find_file(query)
                url, credit = file_info(filename) if filename else (None, None)
            except Exception as exc:  # мрежа, timeout, променет API
                self.stderr.write(f"  {obj}: грешка ({exc})")
                failed += 1
                continue
            if not url:
                self.stdout.write(f"  {obj}: нема слободна слика за „{query}“")
                failed += 1
                continue
            obj.image_url, obj.image_credit = url, credit[:300]
            obj.save(update_fields=["image_url", "image_credit"])
            ok += 1
            self.stdout.write(f"  {obj}: {filename}")
        self.stdout.write(self.style.SUCCESS(f"Готово: {ok} нови, {skipped} постоечки, {failed} без слика."))
