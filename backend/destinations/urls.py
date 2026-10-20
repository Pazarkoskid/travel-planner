from rest_framework.routers import DefaultRouter

from .admin_api import PlaceAdminViewSet
from .views import CityViewSet, PlaceViewSet

router = DefaultRouter()
router.register("cities", CityViewSet, basename="city")
router.register("places", PlaceViewSet, basename="place")
router.register("admin/places", PlaceAdminViewSet, basename="admin-place")
urlpatterns = router.urls
