from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "actor", "action", "object_type", "object_id")
    list_filter = ("action", "object_type")
    readonly_fields = ("timestamp", "actor", "action", "object_type", "object_id", "metadata")
