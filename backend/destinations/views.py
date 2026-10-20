from django.db.models import Count, Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from core.geo import bounding_box, haversine_km

from .models import City, Place
from .serializers import CitySerializer, PlaceSerializer


class CityViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CitySerializer
    pagination_class = None

    def get_queryset(self):
        return City.objects.annotate(
            place_count=Count("places", filter=Q(places__status=Place.Status.VERIFIED)),
            required_landmarks=Count("places", filter=Q(places__is_required_landmark=True,
                                                        places__status=Place.Status.VERIFIED)),
        )

    @action(detail=True)
    def places(self, request, pk=None):
        qs = Place.objects.filter(city_id=pk, status=Place.Status.VERIFIED).select_related("city")
        return Response(PlaceSerializer(qs, many=True).data)


class PlaceViewSet(viewsets.ReadOnlyModelViewSet):
    """GET /places/?city=&category=&near=lat,lng&radius_km=&required=1"""

    serializer_class = PlaceSerializer

    def get_queryset(self):
        qs = Place.objects.filter(status=Place.Status.VERIFIED).select_related("city").annotate(
            badge_holders=Count("badges__holders", distinct=True)
        )
        p = self.request.query_params
        if p.get("city"):
            qs = qs.filter(city__slug=p["city"]) if not p["city"].isdigit() else qs.filter(city_id=p["city"])
        if p.get("category"):
            qs = qs.filter(category__in=p["category"].upper().split(","))
        if p.get("required") == "1":
            qs = qs.filter(is_required_landmark=True)
        if p.get("q"):
            qs = qs.filter(name__icontains=p["q"])
        return qs

    def list(self, request, *args, **kwargs):
        near = request.query_params.get("near")
        if not near:
            return super().list(request, *args, **kwargs)
        try:
            lat, lng = (float(x) for x in near.split(","))
            radius = float(request.query_params.get("radius_km", 5))
        except ValueError:
            raise ValidationError({"near": "Формат: near=lat,lng"})
        if not (0 < radius <= 100):
            raise ValidationError({"radius_km": "Дозволено: 0–100 km."})
        lat_min, lat_max, lng_min, lng_max = bounding_box(lat, lng, radius)
        places = []
        for place in self.get_queryset().filter(lat__range=(lat_min, lat_max), lng__range=(lng_min, lng_max)):
            place._distance_km = haversine_km(lat, lng, place.lat, place.lng)
            if place._distance_km <= radius:
                places.append(place)
        places.sort(key=lambda p: p._distance_km)
        return Response(self.get_serializer(places, many=True).data)
