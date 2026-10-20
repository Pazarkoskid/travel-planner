from django.conf import settings
from django.db import models


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    type = models.CharField(max_length=40)
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    related_object_type = models.CharField(max_length=40, blank=True)
    related_object_id = models.CharField(max_length=40, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


def notify(user, type, title, body="", obj=None):
    return Notification.objects.create(
        user=user, type=type, title=title, body=body,
        related_object_type=obj.__class__.__name__ if obj is not None else "",
        related_object_id=str(obj.pk) if obj is not None else "",
    )
