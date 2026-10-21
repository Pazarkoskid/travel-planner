"""Ги синхронизира беџовите од каталогот и ги доделува на корисниците што веќе ги исполнуваат условите.

Идемпотентно — безбедно е да се пушта при секој deploy:
    python manage.py recompute_badges
"""
from django.core.management.base import BaseCommand

from accounts.models import User
from gamification import catalog, services
from gamification.models import Badge, PhotoCheckIn


class Command(BaseCommand):
    help = "Синхронизирај каталог на беџови и додели ги заслужените."

    def handle(self, *args, **opts):
        catalog.sync_catalog(Badge)
        total = 0
        users = User.objects.filter(checkins__status=PhotoCheckIn.Status.APPROVED).distinct()
        for user in users:
            last = PhotoCheckIn.objects.filter(user=user, status=PhotoCheckIn.Status.APPROVED).first()
            total += len(services.award_rule_badges(user, last))
        self.stdout.write(self.style.SUCCESS(f"Каталог: {Badge.objects.count()} беџови. Нови доделувања: {total}."))
