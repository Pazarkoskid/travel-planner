from django.urls import path
from rest_framework.routers import DefaultRouter

from . import manage, views

router = DefaultRouter()
router.register("businesses", views.BusinessViewSet, basename="business")
router.register("accommodations", views.AccommodationViewSet, basename="accommodation")
router.register("restaurants", views.RestaurantViewSet, basename="restaurant")
router.register("boat-tours", views.BoatTourViewSet, basename="boat-tour")
router.register("taxi-services", views.TaxiViewSet, basename="taxi-service")

urlpatterns = router.urls + [
    path("boat-departures/<int:pk>/availability/", views.departure_availability),
    path("business/units/<int:pk>/availability/", views.set_unit_availability),
    path("business/boat-tours/<int:pk>/departures/", views.create_departure),
    path("business/my/", manage.my_businesses),
    path("business/my/<int:pk>/", manage.my_business_detail),
    path("business/my/<int:pk>/accommodations/", manage.create_accommodation),
    path("business/my/<int:pk>/restaurant/", manage.edit_restaurant),
    path("business/my/<int:pk>/taxi/", manage.edit_taxi),
    path("business/my/<int:pk>/boat-tours/", manage.create_boat_tour),
    path("business/accommodations/<int:pk>/", manage.edit_accommodation),
    path("business/boat-tours/<int:pk>/", manage.edit_boat_tour),
    path("business/departures/<int:pk>/cancel/", manage.cancel_departure),
]
