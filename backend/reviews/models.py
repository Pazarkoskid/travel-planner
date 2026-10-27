from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

DIMENSIONS = {
    "ACCOMMODATION": ["cleanliness", "location", "comfort", "value", "communication"],
    "RESTAURANT": ["food", "service", "atmosphere", "value"],
    "BOAT_TOUR": ["safety", "punctuality", "service", "communication", "overall"],
    "TAXI": ["punctuality", "safety", "service", "communication", "overall"],
}


class Review(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews")
    business = models.ForeignKey("businesses.Business", on_delete=models.CASCADE, related_name="reviews")
    reservation = models.OneToOneField("reservations.Reservation", on_delete=models.PROTECT, related_name="review")
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    dimension_scores = models.JSONField(default=dict, blank=True)
    comment = models.TextField(blank=True, max_length=3000)
    status = models.CharField(max_length=10, choices=[("VISIBLE", "Видлива"), ("HIDDEN", "Скриена")], default="VISIBLE")
    is_verified_booking = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class BusinessReply(models.Model):
    review = models.OneToOneField(Review, on_delete=models.CASCADE, related_name="reply")
    business_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    reply_text = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class ReviewReport(models.Model):
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="reports")
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    reason = models.CharField(max_length=500)
    status = models.CharField(max_length=10, choices=[("OPEN", "Отворено"), ("RESOLVED", "Решено"),
                                                      ("DISMISSED", "Отфрлено")], default="OPEN")
    moderator = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                  related_name="moderated_review_reports")
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("review", "reporter")
