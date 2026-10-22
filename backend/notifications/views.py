from django.utils import timezone
from rest_framework import permissions, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        from core.i18n import get_lang, tr

        data = super().to_representation(instance)
        lang = get_lang(self.context.get("request"))
        if lang == "en":
            data["title"], data["body"] = tr(data["title"], lang), tr(data["body"], lang)
        return data

    class Meta:
        model = Notification
        fields = ("id", "type", "title", "body", "related_object_type", "related_object_id", "read_at", "created_at")


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    @action(detail=True, methods=["post"])
    def read(self, request, pk=None):
        n = self.get_object()
        n.read_at = n.read_at or timezone.now()
        n.save(update_fields=["read_at"])
        return Response(self.get_serializer(n).data)

    @action(detail=False, methods=["post"], url_path="read-all")
    def read_all(self, request):
        count = self.get_queryset().filter(read_at__isnull=True).update(read_at=timezone.now())
        return Response({"updated": count})

    @action(detail=False, url_path="unread-count")
    def unread_count(self, request):
        return Response({"unread": self.get_queryset().filter(read_at__isnull=True).count()})
