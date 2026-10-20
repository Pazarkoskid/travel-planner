from rest_framework import serializers

from .models import City, Place


class CitySerializer(serializers.ModelSerializer):
    place_count = serializers.IntegerField(read_only=True)
    required_landmarks = serializers.IntegerField(read_only=True)

    class Meta:
        model = City
        fields = ("id", "name", "slug", "region", "description", "center_lat", "center_lng",
                  "image_url", "image_credit", "place_count", "required_landmarks")


class PlaceSerializer(serializers.ModelSerializer):
    city_name = serializers.CharField(source="city.name", read_only=True)
    category_label = serializers.CharField(source="get_category_display", read_only=True)
    distance_km = serializers.SerializerMethodField()
    badge_holders = serializers.IntegerField(read_only=True, default=None)

    class Meta:
        model = Place
        fields = (
            "id", "city", "city_name", "name", "slug", "category", "category_label", "description",
            "lat", "lng", "visit_duration_min", "price_eur", "opening_time", "closing_time",
            "source", "verified_at", "status", "is_required_landmark", "checkin_radius_m",
            "image_url", "image_credit", "distance_km", "badge_holders",
        )

    def get_distance_km(self, obj):
        d = getattr(obj, "_distance_km", None)
        return round(d, 2) if d is not None else None
