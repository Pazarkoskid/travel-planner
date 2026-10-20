"""Администраторско уредување на каталогот: цени, работно време, опис, статус, знаменитости.

Кога админот внесува цена или работно време без датум на проверка, датумот се
поставува на денес — апликацијата прикажува цена/работно време само со извор и датум.
"""
from django.utils import timezone
from rest_framework import serializers, viewsets

from core.models import audit
from core.permissions import IsAdminRole

from .models import Place

CHECKED = ("price_eur", "opening_time", "closing_time")


class PlaceAdminSerializer(serializers.ModelSerializer):
    city_name = serializers.CharField(source="city.name", read_only=True)

    class Meta:
        model = Place
        fields = ("id", "city", "city_name", "name", "slug", "category", "description", "lat", "lng",
                  "visit_duration_min", "price_eur", "opening_time", "closing_time", "source", "verified_at",
                  "status", "is_required_landmark", "checkin_radius_m", "image_url", "image_credit", "wiki_query")

    def validate(self, attrs):
        get = lambda k: attrs.get(k, getattr(self.instance, k, None))  # noqa: E731
        opening, closing = get("opening_time"), get("closing_time")
        if (opening is None) != (closing is None):
            raise serializers.ValidationError("Внесете и почеток и крај на работното време (или ниедно).")
        if opening and closing and closing <= opening:
            raise serializers.ValidationError({"closing_time": "Крајот мора да е по почетокот."})
        if attrs.get("price_eur") is not None and attrs["price_eur"] < 0:
            raise serializers.ValidationError({"price_eur": "Цената не може да е негативна."})
        lat, lng = get("lat"), get("lng")
        if lat is not None and not 40.8 <= lat <= 42.4 or lng is not None and not 20.4 <= lng <= 23.1:
            raise serializers.ValidationError("Координатите се надвор од Северна Македонија.")
        if not get("source"):
            raise serializers.ValidationError({"source": "Наведете извор на податоците."})
        touched = any(k in attrs for k in CHECKED)
        if touched and "verified_at" not in attrs:
            attrs["verified_at"] = timezone.localdate()
        return attrs


class PlaceAdminViewSet(viewsets.ModelViewSet):
    """/admin/places/ — сите места (и непроверени), филтри ?city=&status=&q="""

    serializer_class = PlaceAdminSerializer
    permission_classes = [IsAdminRole]
    pagination_class = None
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        qs = Place.objects.select_related("city").order_by("city__name", "name")
        p = self.request.query_params
        if p.get("city"):
            qs = qs.filter(city__slug=p["city"]) if not p["city"].isdigit() else qs.filter(city_id=p["city"])
        if p.get("status"):
            qs = qs.filter(status=p["status"])
        if p.get("q"):
            qs = qs.filter(name__icontains=p["q"])
        return qs

    def perform_create(self, serializer):
        from django.utils.text import slugify

        name = serializer.validated_data["name"]
        slug = serializer.validated_data.get("slug") or slugify(name, allow_unicode=True)[:200] or "mesto"
        obj = serializer.save(slug=slug)
        audit(self.request.user, "place.create", obj)

    def perform_update(self, serializer):
        obj = serializer.save()
        audit(self.request.user, "place.update", obj, fields=sorted(self.request.data.keys()))
