from rest_framework.renderers import JSONRenderer

from .i18n import CITY_EN, get_lang

CITY_KEYS = {"city_name", "city", "location", "city__name"}


def _walk(value):
    if isinstance(value, list):
        return [_walk(v) for v in value]
    if isinstance(value, dict):
        is_city = "center_lat" in value and "slug" in value
        out = {}
        for k, v in value.items():
            if isinstance(v, str) and (k in CITY_KEYS or (is_city and k == "name")) and v in CITY_EN:
                out[k] = CITY_EN[v]
            else:
                out[k] = _walk(v)
        return out
    return value


class LangJSONRenderer(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        request = (renderer_context or {}).get("request")
        if data is not None and get_lang(request) == "en":
            data = _walk(data)
        return super().render(data, accepted_media_type, renderer_context)
