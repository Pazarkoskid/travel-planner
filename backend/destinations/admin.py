from django.contrib import admin

from .models import City, Place


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ("name", "region", "image_credit")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "category", "status", "is_required_landmark", "verified_at")
    list_filter = ("city", "category", "status", "is_required_landmark")
    list_editable = ("is_required_landmark", "status")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
