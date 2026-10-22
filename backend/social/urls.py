from django.urls import path

from . import views

urlpatterns = [
    path("people/search/", views.search),
    path("friends/", views.friends),
    path("friends/requests/", views.send_request),
    path("friends/requests/<int:pk>/accept/", views.accept),
    path("friends/requests/<int:pk>/decline/", views.decline),
    path("friends/<str:username>/", views.remove),
]
