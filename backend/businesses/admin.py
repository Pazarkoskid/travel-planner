from django.contrib import admin

from .models import (
    Accommodation, AccommodationAvailability, AccommodationUnit, BoatDeparture, BoatTour,
    Business, BusinessUser, RestaurantProfile, TaxiService,
)


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ("name", "type", "city", "owner", "verification_status", "is_sponsored")
    list_filter = ("type", "verification_status", "city", "is_sponsored")
    list_editable = ("verification_status",)
    search_fields = ("name",)


class UnitInline(admin.TabularInline):
    model = AccommodationUnit
    extra = 0


@admin.register(Accommodation)
class AccommodationAdmin(admin.ModelAdmin):
    list_display = ("title", "business", "property_type", "max_guests")
    inlines = [UnitInline]


@admin.register(AccommodationAvailability)
class AvailabilityAdmin(admin.ModelAdmin):
    list_display = ("unit", "date", "available_units", "price_per_night")
    list_filter = ("unit",)


class DepartureInline(admin.TabularInline):
    model = BoatDeparture
    extra = 0


@admin.register(BoatTour)
class BoatTourAdmin(admin.ModelAdmin):
    list_display = ("title", "business", "price_per_person", "duration_min")
    inlines = [DepartureInline]


admin.site.register(BusinessUser)
admin.site.register(RestaurantProfile)
admin.site.register(TaxiService)
