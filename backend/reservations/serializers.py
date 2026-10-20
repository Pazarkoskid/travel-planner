from rest_framework import serializers

from .models import Reservation, ReservationItem, ReservationStatusHistory


class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReservationItem
        fields = ("description", "quantity", "unit_price", "total_price")


class HistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ReservationStatusHistory
        fields = ("from_status", "to_status", "note", "created_at")


class ReservationSerializer(serializers.ModelSerializer):
    business_name = serializers.CharField(source="business.name", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    service_label = serializers.CharField(source="get_service_type_display", read_only=True)
    user_name = serializers.CharField(source="user.username", read_only=True)
    unit_name = serializers.CharField(source="accommodation_unit.unit_name", read_only=True, default=None)
    departure_at = serializers.DateTimeField(source="boat_departure.starts_at", read_only=True, default=None)
    items = ItemSerializer(many=True, read_only=True)
    history = HistorySerializer(many=True, read_only=True)
    has_review = serializers.SerializerMethodField()
    can_review = serializers.SerializerMethodField()

    class Meta:
        model = Reservation
        fields = (
            "id", "business", "business_name", "user_name", "service_type", "service_label", "status",
            "status_label", "guests", "accommodation_unit", "unit_name", "check_in", "check_out",
            "boat_departure", "departure_at", "reserved_for", "pickup", "destination", "notes",
            "business_message", "proposed_datetime", "quoted_price", "total_price", "currency",
            "requested_at", "confirmed_at", "completed_at", "cancelled_at", "items", "history",
            "has_review", "can_review",
        )

    def get_has_review(self, obj):
        return hasattr(obj, "review")

    def get_can_review(self, obj):
        req = self.context.get("request")
        return bool(req and obj.user_id == req.user.id and obj.status == "COMPLETED" and not hasattr(obj, "review"))


class AccommodationBookingIn(serializers.Serializer):
    unit_id = serializers.IntegerField()
    check_in = serializers.DateField()
    check_out = serializers.DateField()
    guests = serializers.IntegerField(min_value=1)
    notes = serializers.CharField(required=False, allow_blank=True, max_length=500)
    idempotency_key = serializers.CharField(required=False, max_length=64)


class BoatReservationIn(serializers.Serializer):
    departure_id = serializers.IntegerField()
    seats = serializers.IntegerField(min_value=1, max_value=50)
    notes = serializers.CharField(required=False, allow_blank=True, max_length=500)
    idempotency_key = serializers.CharField(required=False, max_length=64)


class RestaurantReservationIn(serializers.Serializer):
    business_id = serializers.IntegerField()
    reserved_for = serializers.DateTimeField()
    guests = serializers.IntegerField(min_value=1)
    notes = serializers.CharField(required=False, allow_blank=True, max_length=500)
    idempotency_key = serializers.CharField(required=False, max_length=64)


class TaxiRequestIn(RestaurantReservationIn):
    pickup = serializers.CharField(max_length=300)
    destination = serializers.CharField(max_length=300)


class BusinessActionIn(serializers.Serializer):
    action = serializers.ChoiceField(choices=["confirm", "reject", "propose", "quote", "start", "complete", "cancel"])
    note = serializers.CharField(required=False, allow_blank=True, max_length=500)
    proposed_datetime = serializers.DateTimeField(required=False)
    quoted_price = serializers.DecimalField(required=False, max_digits=8, decimal_places=2)
