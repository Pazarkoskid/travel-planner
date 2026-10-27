from rest_framework import serializers

from .models import (
    Accommodation, AccommodationAvailability, AccommodationUnit, BoatDeparture, BoatTour,
    Business, RestaurantProfile, TaxiService, TransportService,
)


class BusinessSerializer(serializers.ModelSerializer):
    avg_rating = serializers.FloatField(read_only=True, default=None)
    review_count = serializers.IntegerField(read_only=True, default=0)
    city_name = serializers.CharField(source="city.name", read_only=True)
    type_label = serializers.CharField(source="get_type_display", read_only=True)
    city_image_url = serializers.CharField(source="city.image_url", read_only=True)

    class Meta:
        model = Business
        fields = ("id", "name", "type", "type_label", "description", "city", "city_name", "city_image_url", "address",
                  "lat", "lng", "phone", "email", "website", "image_url", "logo", "is_sponsored", "avg_rating", "review_count")


class UnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccommodationUnit
        fields = ("id", "unit_name")


class AccommodationSerializer(serializers.ModelSerializer):
    business = BusinessSerializer(read_only=True)
    units = UnitSerializer(many=True, read_only=True)
    type_label = serializers.CharField(source="get_property_type_display", read_only=True)

    class Meta:
        model = Accommodation
        fields = ("id", "business", "title", "property_type", "type_label", "description", "max_guests",
                  "bedrooms", "beds", "amenities", "rules", "cleaning_fee", "free_cancellation_days",
                  "image_url", "units")


class AvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = AccommodationAvailability
        fields = ("date", "available_units", "price_per_night")


class RestaurantSerializer(serializers.ModelSerializer):
    business = BusinessSerializer(read_only=True)

    class Meta:
        model = RestaurantProfile
        fields = ("id", "business", "opening_hours", "menu", "price_range", "cuisine", "max_party_size")


class DepartureSerializer(serializers.ModelSerializer):
    remaining_seats = serializers.IntegerField(read_only=True)

    class Meta:
        model = BoatDeparture
        fields = ("id", "tour", "starts_at", "capacity", "reserved_seats", "remaining_seats", "status")
        read_only_fields = ("reserved_seats", "status")


class BoatTourSerializer(serializers.ModelSerializer):
    business = BusinessSerializer(read_only=True)
    upcoming_departures = serializers.SerializerMethodField()

    class Meta:
        model = BoatTour
        fields = ("id", "business", "title", "route", "description", "stops", "includes", "duration_min",
                  "price_per_person", "departure_point", "rules", "upcoming_departures")

    def get_upcoming_departures(self, obj):
        from django.utils import timezone

        limit = 60 if self.context.get("detail") else 10
        qs = obj.departures.filter(status="SCHEDULED", starts_at__gt=timezone.now())[:limit]
        return DepartureSerializer(qs, many=True).data


class TaxiSerializer(serializers.ModelSerializer):
    business = BusinessSerializer(read_only=True)

    class Meta:
        model = TaxiService
        fields = ("id", "business", "service_area", "passenger_capacity", "base_fare", "per_km", "available_24h",
                  "vehicles", "languages", "fare_info")


class TransportSerializer(serializers.ModelSerializer):
    business = BusinessSerializer(read_only=True)

    class Meta:
        model = TransportService
        fields = ("id", "business", "service_area", "opening_hours", "lines", "rentals", "price_info", "payment",
                  "languages", "features")
