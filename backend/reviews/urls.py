from django.urls import path

from . import views

urlpatterns = [
    path("reservations/<int:pk>/review/", views.create_review),
    path("businesses/<int:pk>/reviews/", views.business_reviews),
    path("reviews/latest/", views.latest_reviews),
    path("reviews/<int:pk>/reply/", views.reply),
    path("reviews/<int:pk>/report/", views.report),
    path("admin/review-reports/", views.admin_review_reports),
    path("admin/review-reports/<int:pk>/resolve/", views.admin_resolve_review_report),
]
