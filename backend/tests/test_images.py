from unittest import mock

from django.core.management import call_command

from core.management.commands import fetch_images
from destinations.models import Place


def fake_get_json(url, params, timeout=15):
    if "generator" in params:  # пребарување на Wikipedia
        if "Nowhere" in params["gsrsearch"]:
            return {"query": {"pages": []}}
        return {"query": {"pages": [
            {"index": 1, "pageimage": "North_Macedonia_location_map.svg"},
            {"index": 2, "pageimage": "Kaneo_view.jpg"},
        ]}}
    return {"query": {"pages": [{"imageinfo": [{
        "thumburl": "https://upload.wikimedia.org/thumb/Kaneo_view.jpg/1600px-Kaneo_view.jpg",
        "extmetadata": {"Artist": {"value": "<a href='x'>Jane Doe</a>"}, "LicenseShortName": {"value": "CC BY-SA 4.0"}},
    }]}]}}


def test_fetch_images_sets_url_and_credit_and_skips_maps(places):
    places["sv-naum"].wiki_query = "Nowhere at all"
    places["sv-naum"].save()
    with mock.patch.object(fetch_images, "get_json", side_effect=fake_get_json):
        call_command("fetch_images")
    kaneo = Place.objects.get(slug="kaneo")
    assert kaneo.image_url.endswith("1600px-Kaneo_view.jpg")
    assert kaneo.image_credit == "Фото: Jane Doe, CC BY-SA 4.0, Wikimedia Commons"
    assert Place.objects.get(slug="sv-naum").image_url == ""


def test_fetch_images_survives_network_errors(places):
    with mock.patch.object(fetch_images, "get_json", side_effect=TimeoutError):
        call_command("fetch_images")
    assert not Place.objects.exclude(image_url="").exists()
