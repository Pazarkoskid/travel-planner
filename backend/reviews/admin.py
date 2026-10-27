from django.contrib import admin

from .models import BusinessReply, Review, ReviewReport


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("id", "business", "user", "rating", "status", "created_at")
    list_filter = ("status", "rating")
    readonly_fields = ("user", "business", "reservation", "rating", "dimension_scores", "comment")


@admin.register(ReviewReport)
class ReviewReportAdmin(admin.ModelAdmin):
    list_display = ("review", "reporter", "status", "created_at")
    list_filter = ("status",)


admin.site.register(BusinessReply)
