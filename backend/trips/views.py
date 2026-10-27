import csv

from django.http import HttpResponse
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from core.i18n import get_lang, tr

from .models import Trip
from .planner import generate_plan
from .serializers import DaySerializer, RunSerializer, TripDetailSerializer, TripSerializer


class TripViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (Trip.objects.filter(user=self.request.user).select_related("city")
                .prefetch_related("itinerary_days__items__place", "itinerary_days__items__business", "plan_runs"))

    def get_serializer_class(self):
        return TripDetailSerializer if self.action == "retrieve" else TripSerializer

    def get_throttles(self):
        if self.action in ("generate", "revise"):
            self.throttle_scope = "ai_generate"
        return super().get_throttles()

    def perform_create(self, serializer):
        trip = serializer.save(user=self.request.user)
        if not trip.title:
            trip.title = f"{trip.days} дена во {trip.city.name}"
            trip.save(update_fields=["title"])

    @action(detail=True, methods=["post"])
    def generate(self, request, pk=None):
        trip = self.get_object()
        generate_plan(trip)
        return Response(TripDetailSerializer(self.get_queryset().get(pk=trip.pk), context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def revise(self, request, pk=None):
        trip = self.get_object()
        text = str(request.data.get("instructions", "")).strip()
        if not text:
            raise ValidationError({"instructions": "Опишете ја измената (пр. „поевтино“, „повеќе природа“)."})
        generate_plan(trip, instructions=text[:300])
        return Response(TripDetailSerializer(self.get_queryset().get(pk=trip.pk), context={"request": request}).data)

    @action(detail=True)
    def itinerary(self, request, pk=None):
        trip = self.get_object()
        lang = get_lang(request)
        return Response({"warnings": [tr(w, lang) for w in trip.warnings],
                         "days": DaySerializer(trip.itinerary_days.all(), many=True, context={"request": request}).data})

    @action(detail=True, methods=["post", "get"])
    def evaluate(self, request, pk=None):
        trip = self.get_object()
        runs = trip.plan_runs.all()[:10]
        if not runs:
            raise ValidationError("Планот сè уште не е генериран.")
        return Response({"latest": RunSerializer(runs[0]).data, "history": RunSerializer(runs, many=True).data})

    @action(detail=True)
    def export(self, request, pk=None):
        trip = self.get_object()
        fmt = request.query_params.get("format", "csv")
        if fmt == "pdf":
            from .pdf import render_trip_pdf

            resp = HttpResponse(render_trip_pdf(trip, get_lang(request)), content_type="application/pdf")
            resp["Content-Disposition"] = f'attachment; filename="trip-{trip.pk}.pdf"'
            return resp
        if fmt != "csv":
            raise ValidationError({"format": "Поддржани формати: csv, pdf."})
        resp = HttpResponse(content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = f'attachment; filename="trip-{trip.pk}.csv"'
        resp.write("﻿")
        w = csv.writer(resp)
        w.writerow(["Ден", "Датум", "Од", "До", "Активност", "Патување (мин)", "Растојание (km)", "Трошок (EUR)",
                    "Причина", "Предупредување"])
        for day in trip.itinerary_days.all():
            for it in day.items.all():
                w.writerow([day.day_number, day.date, it.start_time.strftime("%H:%M"), it.end_time.strftime("%H:%M"),
                            it.title, it.travel_minutes_from_prev, it.distance_km_from_prev,
                            it.est_cost if it.est_cost is not None else "непознато", it.reason, it.warning])
        return resp
