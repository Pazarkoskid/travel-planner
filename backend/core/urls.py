from django.urls import path

from . import views

urlpatterns = [
    path("weather/", views.weather),
    path("amenities/", views.amenities),
    path("admin/analytics/", views.analytics),
    path("admin/businesses/pending/", views.pending_businesses),
    path("admin/businesses/<int:pk>/verify/", views.verify_business),
]
