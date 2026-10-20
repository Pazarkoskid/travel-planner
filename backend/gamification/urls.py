from django.urls import path

from . import views

urlpatterns = [
    path("places/<int:pk>/checkins/", views.create_checkin),
    path("places/<int:pk>/gallery/", views.place_gallery),
    path("badges/", views.badges),
    path("me/gamification/", views.my_gamification),
    path("users/<str:username>/", views.public_profile),
    path("photos/<int:pk>/", views.my_photo),
    path("photos/<int:pk>/report/", views.report_photo),
    path("admin/checkins/", views.admin_pending_checkins),
    path("admin/checkins/<int:pk>/review/", views.admin_review_checkin),
    path("admin/place-reports/", views.admin_place_reports),
    path("admin/place-reports/<int:pk>/resolve/", views.admin_resolve_place_report),
]
