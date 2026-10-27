from datetime import date

from rest_framework import serializers

from destinations.models import Place

from core.i18n import get_lang, tr

from .models import AIPlanRun, ItineraryDay, ItineraryItem, Trip
from .planner import INTEREST_CATEGORIES


class LangMixin:

    translated_fields = ()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        lang = get_lang(self.context.get("request"))
        if lang == "en":
            for f in self.translated_fields:
                v = data.get(f)
                if isinstance(v, list):
                    data[f] = [tr(x, lang) for x in v]
                elif isinstance(v, str):
                    data[f] = tr(v, lang)
        return data


class ItemSerializer(LangMixin, serializers.ModelSerializer):
    translated_fields = ("title", "reason", "warning", "accessibility_notes")

    lat = serializers.SerializerMethodField()
    lng = serializers.SerializerMethodField()
    category = serializers.CharField(source="place.category", read_only=True, default=None)
    image_url = serializers.CharField(source="place.image_url", read_only=True, default="")
    wheelchair = serializers.CharField(source="place.wheelchair", read_only=True, default=None)
    accessibility_notes = serializers.CharField(source="place.accessibility_notes", read_only=True, default="")

    class Meta:
        model = ItineraryItem
        fields = ("id", "source_type", "place", "business", "title", "start_time", "end_time", "order_index",
                  "travel_minutes_from_prev", "distance_km_from_prev", "est_cost", "reason", "warning",
                  "lat", "lng", "category", "image_url", "wheelchair", "accessibility_notes")

    def get_lat(self, obj):
        src = obj.place or obj.business
        return src.lat if src else None

    def get_lng(self, obj):
        src = obj.place or obj.business
        return src.lng if src else None


class DaySerializer(LangMixin, serializers.ModelSerializer):
    translated_fields = ("notes",)

    items = ItemSerializer(many=True, read_only=True)

    class Meta:
        model = ItineraryDay
        fields = ("day_number", "date", "notes", "items")


class RunSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIPlanRun
        fields = ("id", "provider", "model", "routing_provider", "selected_place_ids", "rejected_ids",
                  "validation_result", "metrics", "instructions", "duration_ms", "created_at")


class TripSerializer(LangMixin, serializers.ModelSerializer):
    translated_fields = ("warnings", "title")

    city_name = serializers.CharField(source="city.name", read_only=True)
    must_visit = serializers.PrimaryKeyRelatedField(many=True, queryset=Place.objects.all(), required=False)

    class Meta:
        model = Trip
        fields = ("id", "city", "city_name", "title", "start_date", "days", "guests", "budget", "interests",
                  "pace", "transport", "mobility", "must_visit", "accommodation", "modifiers", "warnings", "status",
                  "created_at", "updated_at")
        read_only_fields = ("modifiers", "warnings", "status")

    def validate_days(self, v):
        if not 1 <= v <= 10:
            raise serializers.ValidationError("Дозволено 1–10 дена.")
        return v

    def validate_guests(self, v):
        if not 1 <= v <= 20:
            raise serializers.ValidationError("Дозволено 1–20 гости.")
        return v

    def validate_start_date(self, v):
        if v < date.today():
            raise serializers.ValidationError("Датумот не може да е во минатото.")
        return v

    def validate_budget(self, v):
        if v is not None and v < 0:
            raise serializers.ValidationError("Буџетот не може да е негативен.")
        return v

    def validate_interests(self, v):
        if not isinstance(v, list) or any(i not in INTEREST_CATEGORIES for i in v):
            raise serializers.ValidationError(f"Дозволени: {', '.join(INTEREST_CATEGORIES)}.")
        return list(dict.fromkeys(v))

    def validate(self, attrs):
        city = attrs.get("city") or getattr(self.instance, "city", None)
        for p in attrs.get("must_visit", []):
            if p.city_id != city.id:
                raise serializers.ValidationError({"must_visit": f"„{p.name}“ не е во избраниот град."})
        acc = attrs.get("accommodation")
        if acc and acc.business.city_id != city.id:
            raise serializers.ValidationError({"accommodation": "Сместувањето не е во избраниот град."})
        return attrs


class TripDetailSerializer(TripSerializer):
    itinerary_days = DaySerializer(many=True, read_only=True)
    latest_run = serializers.SerializerMethodField()

    class Meta(TripSerializer.Meta):
        fields = TripSerializer.Meta.fields + ("itinerary_days", "latest_run")

    def get_latest_run(self, obj):
        run = obj.plan_runs.first()
        return RunSerializer(run).data if run else None
