import io
import urllib.error
from unittest import mock

import pytest
from django.core.management import call_command
from PIL import Image

from core.management.commands import fetch_images
from destinations.models import Place

THUMB = "https://upload.wikimedia.org/thumb/Kaneo_view.jpg/1280px-Kaneo_view.jpg"
INFO = {"query": {"pages": [{"imageinfo": [{
    "thumburl": THUMB,
    "extmetadata": {"Artist": {"value": "<a href='x'>Jane Doe</a>"}, "LicenseShortName": {"value": "CC BY-SA 4.0"}},
}]}]}}
EMPTY = {"query": {"pages": [], "search": []}}


def jpeg_bytes(w=2400, h=1600):
    buf = io.BytesIO()
    Image.new("RGB", (w, h), (30, 120, 160)).save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture(autouse=True)
def local_media(settings, tmp_path, monkeypatch):
    settings.MEDIA_ROOT = tmp_path
    settings.DEBUG = True
    monkeypatch.setattr(fetch_images, "PAUSE", 0)
    downloaded = []

    def fake_download(url, timeout=30):
        downloaded.append(url)
        return jpeg_bytes()

    monkeypatch.setattr(fetch_images, "download", fake_download)
    return downloaded


def fake_get_json(url, params, timeout=15):
    q = params.get("gsrsearch") or params.get("srsearch") or ""
    if "Nowhere" in q or "Св. Наум" in q:
        return EMPTY
    if "generator" in params:
        return {"query": {"pages": [
            {"index": 1, "pageimage": "North_Macedonia_location_map.svg"},
            {"index": 2, "pageimage": "Kaneo_view.jpg"},
        ]}}
    return INFO


def test_fetch_images_sets_url_and_credit_and_skips_maps(places):
    places["sv-naum"].wiki_query = "Nowhere at all"
    places["sv-naum"].save()
    with mock.patch.object(fetch_images, "get_json", side_effect=fake_get_json):
        call_command("fetch_images")
    kaneo = Place.objects.get(slug="kaneo")
    assert kaneo.image_url.startswith("/media/photos/places/ohrid/kaneo")
    assert kaneo.image_credit == "Фото: Jane Doe, CC BY-SA 4.0, Wikimedia Commons"
    assert Place.objects.get(slug="sv-naum").image_url == ""


def test_falls_back_to_mk_wikipedia_then_commons(places):
    calls = []

    def fake(url, params, timeout=15):
        calls.append(url)
        if "en.wikipedia" in url and "generator" in params:
            return EMPTY
        if "mk.wikipedia" in url:
            return EMPTY
        if "list" in params:
            return {"query": {"search": [{"title": "File:Kaneo_view.jpg"}]}}
        return INFO

    with mock.patch.object(fetch_images, "get_json", side_effect=fake):
        call_command("fetch_images")
    assert Place.objects.get(slug="kaneo").image_url.startswith("/media/photos/")
    assert any("mk.wikipedia" in c for c in calls)


def test_existing_wikimedia_links_are_moved_to_our_storage(places, local_media, settings):
    p = places["kaneo"]
    p.image_url = "https://upload.wikimedia.org/thumb/x.jpg/1600px-x.jpg"
    p.image_credit = "Фото: Jane Doe, CC BY-SA 4.0, Wikimedia Commons"
    p.save()
    with mock.patch.object(fetch_images, "get_json", side_effect=AssertionError("не смее да пребарува")):
        call_command("fetch_images")
    p.refresh_from_db()
    assert p.image_url.startswith("/media/photos/places/ohrid/kaneo")
    assert p.image_credit.startswith("Фото: Jane Doe")
    assert local_media == ["https://upload.wikimedia.org/thumb/x.jpg/1280px-x.jpg"]
    with Image.open(settings.MEDIA_ROOT / p.image_url.removeprefix("/media/")) as im:
        assert max(im.size) <= 1600


def test_download_falls_back_to_960(monkeypatch):
    monkeypatch.undo()
    monkeypatch.setattr(fetch_images, "PAUSE", 0)
    monkeypatch.setattr(fetch_images.time, "sleep", lambda s: None)
    calls = []

    def fake_urlopen(req, timeout=30):
        calls.append(req.full_url)
        if "/1280px-" in req.full_url:
            raise urllib.error.HTTPError(req.full_url, 403, "Forbidden", {}, None)
        ok = mock.MagicMock()
        ok.__enter__.return_value = io.BytesIO(b"img")
        return ok

    monkeypatch.setattr(fetch_images.urllib.request, "urlopen", fake_urlopen)
    assert fetch_images.download("https://upload.wikimedia.org/t/a.jpg/1280px-a.jpg") == b"img"
    assert calls[-1].endswith("/960px-a.jpg")


def test_retries_on_429(monkeypatch):
    monkeypatch.setattr(fetch_images, "PAUSE", 0)
    monkeypatch.setattr(fetch_images.time, "sleep", lambda s: None)
    err = urllib.error.HTTPError("u", 429, "Too Many Requests", {"Retry-After": "1"}, None)
    ok = mock.MagicMock()
    ok.__enter__.return_value = io.BytesIO(b'{"ok": 1}')
    with mock.patch.object(fetch_images.urllib.request, "urlopen", side_effect=[err, ok]):
        assert fetch_images.get_json("https://x", {}) == {"ok": 1}


def test_fetch_images_survives_network_errors(places):
    with mock.patch.object(fetch_images, "get_json", side_effect=TimeoutError):
        call_command("fetch_images")
    assert not Place.objects.exclude(image_url="").exists()


def test_without_supabase_in_production_keeps_links(places, settings):
    settings.DEBUG, settings.SUPABASE_S3_ENDPOINT = False, ""
    with mock.patch.object(fetch_images, "get_json", side_effect=fake_get_json):
        call_command("fetch_images")
    assert Place.objects.get(slug="kaneo").image_url == THUMB
