import io
import urllib.error
from unittest import mock

from django.core.management import call_command

from core.management.commands import fetch_images
from destinations.models import Place

THUMB = "https://upload.wikimedia.org/thumb/Kaneo_view.jpg/1280px-Kaneo_view.jpg"
INFO = {"query": {"pages": [{"imageinfo": [{
    "thumburl": THUMB,
    "extmetadata": {"Artist": {"value": "<a href='x'>Jane Doe</a>"}, "LicenseShortName": {"value": "CC BY-SA 4.0"}},
}]}]}}
EMPTY = {"query": {"pages": [], "search": []}}


def fake_get_json(url, params, timeout=15):
    q = params.get("gsrsearch") or params.get("srsearch") or ""
    if "Nowhere" in q or "Св. Наум" in q:  # нема слика никаде
        return EMPTY
    if "generator" in params:  # пребарување на Wikipedia
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
    assert kaneo.image_url == THUMB  # стандардна ширина 1280px
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
        if "list" in params:  # Commons пребарување
            return {"query": {"search": [{"title": "File:Kaneo_view.jpg"}]}}
        return INFO

    with mock.patch.object(fetch_images, "get_json", side_effect=fake):
        call_command("fetch_images")
    assert Place.objects.get(slug="kaneo").image_url == THUMB
    assert any("mk.wikipedia" in c for c in calls)


def test_old_1600px_links_are_refetched(places):
    p = places["kaneo"]
    p.image_url = "https://upload.wikimedia.org/thumb/x.jpg/1600px-x.jpg"
    p.save()
    with mock.patch.object(fetch_images, "get_json", side_effect=fake_get_json):
        call_command("fetch_images")
    p.refresh_from_db()
    assert p.image_url == THUMB


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
