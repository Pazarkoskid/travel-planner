from django.conf import settings
from django.db import models
from django.db.models import Q


class Friendship(models.Model):
    """Барање за пријателство: from_user → to_user. По прифаќање важи во двете насоки."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Чека одговор"
        ACCEPTED = "ACCEPTED", "Пријатели"

    from_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="friend_requests_sent")
    to_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="friend_requests_received")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["from_user", "to_user"], name="unique_friend_request"),
            models.CheckConstraint(condition=~Q(from_user=models.F("to_user")), name="no_self_friendship"),
        ]

    def other(self, user):
        return self.to_user if self.from_user_id == user.id else self.from_user

    @classmethod
    def between(cls, a, b):
        return cls.objects.filter(Q(from_user=a, to_user=b) | Q(from_user=b, to_user=a)).first()

    @classmethod
    def are_friends(cls, a, b):
        if not (a and b and getattr(a, "is_authenticated", False)):
            return False
        f = cls.between(a, b)
        return bool(f and f.status == cls.Status.ACCEPTED)
