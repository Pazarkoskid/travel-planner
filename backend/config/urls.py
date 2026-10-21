from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

api_patterns = [
    path("", include("accounts.urls")),
    path("", include("destinations.urls")),
    path("", include("businesses.urls")),
    path("", include("reservations.urls")),
    path("", include("reviews.urls")),
    path("", include("trips.urls")),
    path("", include("gamification.urls")),
    path("", include("notifications.urls")),
    path("", include("core.urls")),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include(api_patterns)),
]

if settings.DEBUG and not settings.SUPABASE_S3_ENDPOINT:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
