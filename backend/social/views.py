"""Пребарување корисници и пријатели.

GET    /people/search/?q=           јавни профили (и пријатели) по корисничко име или име и презиме
GET    /friends/                    {friends, incoming, outgoing}
POST   /friends/requests/           {"username": "..."} — ако другиот веќе ви испратил, веднаш сте пријатели
POST   /friends/requests/<id>/accept/   само примачот
POST   /friends/requests/<id>/decline/  само примачот (барањето се брише)
DELETE /friends/<username>/         отстрани пријател или откажи испратено барање
"""
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from accounts.models import User
from core.exceptions import ServiceError
from notifications.models import notify

from .models import Friendship

MAX_RESULTS = 20


class SearchThrottle(UserRateThrottle):
    scope = "people_search"


def _relation(me, other, rel):
    """none | friends | outgoing | incoming (+ id на барањето)."""
    f = rel.get(other.id)
    if not f:
        return "none", None
    if f.status == Friendship.Status.ACCEPTED:
        return "friends", f.id
    return ("outgoing" if f.from_user_id == me.id else "incoming"), f.id


def _relations(me, users):
    ids = [u.id for u in users]
    rel = {}
    for f in Friendship.objects.filter(Q(from_user=me, to_user_id__in=ids) | Q(to_user=me, from_user_id__in=ids)):
        rel[f.to_user_id if f.from_user_id == me.id else f.from_user_id] = f
    return rel


def person(me, u, rel=None):
    rel = rel if rel is not None else _relations(me, [u])
    status, fid = _relation(me, u, rel)
    return {
        "username": u.username,
        "name": f"{u.first_name} {u.last_name}".strip(),
        "bio": u.bio[:140],
        "badges": getattr(u, "badge_count", None),
        "is_public": u.is_profile_public,
        "relation": status,
        "request_id": fid,
    }


def _annotated(qs):
    return qs.annotate(badge_count=Count("user_badges", distinct=True))


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
@throttle_classes([SearchThrottle])
def search(request):
    q = str(request.query_params.get("q", "")).strip()
    if len(q) < 2:
        return Response([])
    me = request.user
    words = q.split()
    cond = Q()
    for w in words[:3]:
        cond &= Q(username__icontains=w) | Q(first_name__icontains=w) | Q(last_name__icontains=w)
    friend_ids = Friendship.objects.filter(
        Q(from_user=me) | Q(to_user=me), status=Friendship.Status.ACCEPTED
    ).values_list("from_user_id", "to_user_id")
    friends = {i for pair in friend_ids for i in pair} - {me.id}
    # Приватни профили се наоѓаат само ако веќе сте пријатели.
    qs = (_annotated(User.objects.filter(cond, is_active=True).exclude(pk=me.pk)
                     .filter(Q(is_profile_public=True) | Q(pk__in=friends)))
          .order_by("username")[:MAX_RESULTS])
    users = list(qs)
    rel = _relations(me, users)
    return Response([person(me, u, rel) for u in users])


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def friends(request):
    me = request.user
    rows = Friendship.objects.filter(Q(from_user=me) | Q(to_user=me)).select_related("from_user", "to_user")
    others = {f.other(me).id for f in rows}
    users = {u.id: u for u in _annotated(User.objects.filter(pk__in=others))}
    out = {"friends": [], "incoming": [], "outgoing": []}
    rel = {f.other(me).id: f for f in rows}
    for f in rows:
        u = users[f.other(me).id]
        item = {**person(me, u, rel), "since": f.accepted_at or f.created_at}
        if f.status == Friendship.Status.ACCEPTED:
            out["friends"].append(item)
        elif f.to_user_id == me.id:
            out["incoming"].append(item)
        else:
            out["outgoing"].append(item)
    out["friends"].sort(key=lambda x: x["username"])
    return Response(out)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def send_request(request):
    me = request.user
    target = get_object_or_404(User, username=str(request.data.get("username", "")), is_active=True)
    if target == me:
        raise ServiceError("Не можете да се додадете себеси.", code="self_friend")
    with transaction.atomic():
        existing = Friendship.between(me, target)
        if existing:
            if existing.status == Friendship.Status.ACCEPTED:
                raise ServiceError("Веќе сте пријатели.", code="already_friends", status_code=409)
            if existing.from_user_id == me.id:
                raise ServiceError("Барањето е веќе испратено.", code="request_exists", status_code=409)
            # Другиот веќе ви испратил барање → прифаќање.
            existing.status, existing.accepted_at = Friendship.Status.ACCEPTED, timezone.now()
            existing.save(update_fields=["status", "accepted_at"])
            notify(target, "friend", f"{me.username} го прифати вашето барање за пријателство", "", existing)
            return Response(person(me, target), status=200)
        if not target.is_profile_public:
            raise ServiceError("Профилот е приватен.", code="private_profile", status_code=403)
        try:
            f = Friendship.objects.create(from_user=me, to_user=target)
        except IntegrityError:
            raise ServiceError("Барањето е веќе испратено.", code="request_exists", status_code=409)
    notify(target, "friend", f"Ново барање за пријателство од {me.username}", "", f)
    return Response(person(me, target), status=201)


def _incoming(request, pk):
    return get_object_or_404(Friendship, pk=pk, to_user=request.user, status=Friendship.Status.PENDING)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def accept(request, pk):
    f = _incoming(request, pk)
    f.status, f.accepted_at = Friendship.Status.ACCEPTED, timezone.now()
    f.save(update_fields=["status", "accepted_at"])
    notify(f.from_user, "friend", f"{request.user.username} го прифати вашето барање за пријателство", "", f)
    return Response(person(request.user, f.from_user))


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def decline(request, pk):
    f = _incoming(request, pk)
    other = f.from_user
    f.delete()
    return Response(person(request.user, other))


@api_view(["DELETE"])
@permission_classes([permissions.IsAuthenticated])
def remove(request, username):
    other = get_object_or_404(User, username=username)
    f = Friendship.between(request.user, other)
    if not f:
        raise ServiceError("Не сте пријатели.", code="not_friends", status_code=404)
    f.delete()
    return Response(status=204)
