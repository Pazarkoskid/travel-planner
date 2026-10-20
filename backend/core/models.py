from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=64)
    object_type = models.CharField(max_length=64)
    object_id = models.CharField(max_length=64)
    metadata = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.action} {self.object_type}#{self.object_id}"


def audit(actor, action, obj, **metadata):
    AuditLog.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        action=action,
        object_type=obj.__class__.__name__,
        object_id=str(obj.pk),
        metadata=metadata,
    )
