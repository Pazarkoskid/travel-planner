from django.contrib import admin

from .models import Reservation, ReservationItem, ReservationStatusHistory


class ItemInline(admin.TabularInline):
    model = ReservationItem
    extra = 0


class HistoryInline(admin.TabularInline):
    model = ReservationStatusHistory
    extra = 0
    readonly_fields = ("from_status", "to_status", "actor", "note", "created_at")


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ("id", "service_type", "business", "user", "status", "total_price", "requested_at")
    list_filter = ("service_type", "status")
    inlines = [ItemInline, HistoryInline]
