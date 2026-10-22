from django.contrib import admin

from .models import Friendship


@admin.register(Friendship)
class FriendshipAdmin(admin.ModelAdmin):
    list_display = ("from_user", "to_user", "status", "created_at", "accepted_at")
    list_filter = ("status",)
    search_fields = ("from_user__username", "to_user__username")
