from django.contrib import admin

from .models import Badge, CityAchievement, PhotoCheckIn, PlacePhoto, PlaceReport, UserBadge


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "kind", "level", "city", "place")
    list_filter = ("kind", "level", "city")


@admin.register(PhotoCheckIn)
class CheckInAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "place", "status", "distance_m", "created_at")
    list_filter = ("status", "place__city")


@admin.register(PlacePhoto)
class PlacePhotoAdmin(admin.ModelAdmin):
    list_display = ("id", "place", "user", "is_public", "is_hidden", "created_at")
    list_editable = ("is_hidden",)


admin.site.register(UserBadge)
admin.site.register(CityAchievement)
admin.site.register(PlaceReport)
