from django.urls import path

from . import views

urlpatterns = [
    path("accommodation-bookings/", views.accommodation_booking),
    path("boat-reservations/", views.boat_reservation),
    path("restaurant-reservations/", views.restaurant_reservation),
    path("taxi-requests/", views.taxi_request),
    path("reservations/mine/", views.my_reservations),
    path("reservations/<int:pk>/", views.reservation_detail),
    path("reservations/<int:pk>/cancel/", views.cancel_reservation),
    path("reservations/<int:pk>/accept/", views.accept_proposal),
    path("business/reservations/", views.business_reservations),
    path("business/reservations/<int:pk>/", views.business_reservation_action),
    path("business/dashboard/", views.business_dashboard),
]
