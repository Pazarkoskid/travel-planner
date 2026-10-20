from django.contrib import admin

from .models import AIPlanRun, ItineraryDay, ItineraryItem, Trip


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "city", "start_date", "days", "status")
    list_filter = ("city", "status")


@admin.register(AIPlanRun)
class AIPlanRunAdmin(admin.ModelAdmin):
    list_display = ("id", "trip", "provider", "routing_provider", "duration_ms", "created_at")
    readonly_fields = [f.name for f in AIPlanRun._meta.fields]


admin.site.register(ItineraryDay)
admin.site.register(ItineraryItem)
