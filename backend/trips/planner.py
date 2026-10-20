"""AI pipeline за план (спецификација 6.2).

1. Валидација (serializers) → 2. Кандидати од проверен каталог → 3. Цени/достапност
(само познати) → 4. Избор: LLM (JSON со IDs) или детерминистички → 5. Валидација на IDs
→ 6. OR-Tools редослед + временски блокови → 7. Приказ со причини и предупредувања.
"""
import time
from datetime import datetime, timedelta
from datetime import time as dtime
from decimal import Decimal

from django.db import transaction

from businesses.models import Business
from core.geo import haversine_km
from core.routing import travel_matrix
from destinations.models import Place

from . import llm
from .models import AIPlanRun, ItineraryDay, ItineraryItem
from .optimizer import optimize_order, route_cost

C = Place.Category
INTEREST_CATEGORIES = {
    "history": {C.HISTORY, C.MUSEUM},
    "religion": {C.RELIGIOUS},
    "nature": {C.NATURE, C.VIEWPOINT, C.BEACH},
    "beach": {C.BEACH},
    "culture": {C.CULTURE, C.MUSEUM, C.HISTORY},
    "local_food": {C.FOOD},
    "activities": {C.ACTIVITY, C.NATURE},
    "museums": {C.MUSEUM},
}
INTEREST_LABELS = {
    "history": "историја", "religion": "цркви и манастири", "nature": "природа", "beach": "плажи",
    "culture": "култура", "local_food": "локална храна", "activities": "активности", "museums": "музеи",
}
# Темпо → (максимум места дневно, минути активности без ручек).
PACE_PER_DAY = {"relaxed": 4, "balanced": 6, "intense": 8}
PACE_MINUTES = {"relaxed": 330, "balanced": 450, "intense": 540}
DAY_START = dtime(9, 0)
DAY_END = dtime(19, 0)
LUNCH_AFTER = dtime(12, 30)
LUNCH_MIN = 60

REVISION_KEYWORDS = {
    "cheaper": ("поевтин", "евтин", "cheap", "буџет"),
    "slower": ("побав", "бавно", "помалку места", "slow", "relax"),
    "faster": ("повеќе места", "побрз", "интензив", "faster", "more places"),
    "more_nature": ("природ", "nature", "планин", "езеро"),
    "more_history": ("историј", "history", "музе", "култур"),
    "less_walking": ("помалку пешач", "less walk", "без пешачење", "кратки"),
}


def parse_revision(text):
    t = (text or "").lower()
    return {key for key, words in REVISION_KEYWORDS.items() if any(w in t for w in words)}


def start_point(trip):
    if trip.accommodation_id:
        b = trip.accommodation.business
        return b.lat, b.lng, f"сместување „{trip.accommodation.title}“"
    return trip.city.center_lat, trip.city.center_lng, f"центар на {trip.city.name}"


def per_day_count(trip):
    n = PACE_PER_DAY.get(trip.pace, 6)
    mods = set(trip.modifiers.get("active", []))
    if "slower" in mods:
        n -= 1
    if "faster" in mods:
        n += 1
    return max(2, min(n, 9))


def day_minutes(trip):
    m = PACE_MINUTES.get(trip.pace, 450)
    mods = set(trip.modifiers.get("active", []))
    if "slower" in mods:
        m -= 90
    if "faster" in mods:
        m += 60
    return max(180, min(m, 540))


def retrieve_candidates(trip):
    """Само VERIFIED места од каталогот. Цени/работно време — само ако се зачувани."""
    s_lat, s_lng, _ = start_point(trip)
    mods = set(trip.modifiers.get("active", []))
    must = set(trip.must_visit.values_list("id", flat=True))
    wanted = set()
    for i in trip.interests:
        wanted |= INTEREST_CATEGORIES.get(i, set())
    budget_cap = None
    if trip.budget:
        budget_cap = Decimal(trip.budget) * Decimal("0.4")  # еден влез не смее да „изеде“ >40% од буџетот
    out, excluded = [], []
    for p in Place.objects.filter(city=trip.city, status=Place.Status.VERIFIED):
        dist = haversine_km(s_lat, s_lng, p.lat, p.lng)
        score, reasons = 0.0, []
        if p.category in wanted:
            score += 3
            matched = [INTEREST_LABELS[i] for i in trip.interests if p.category in INTEREST_CATEGORIES.get(i, ())]
            reasons.append("одговара на интересот: " + ", ".join(matched))
        if p.is_required_landmark:
            score += 1
            reasons.append("клучна знаменитост на градот")
        if p.id in must:
            score += 100
            reasons.append("го означивте како задолжително")
        if "more_nature" in mods and p.category in INTEREST_CATEGORIES["nature"]:
            score += 2
        if "more_history" in mods and p.category in INTEREST_CATEGORIES["culture"]:
            score += 2
        if "cheaper" in mods and p.price_eur is not None:
            score += 1 if p.price_eur == 0 else -1.5
        distance_weight = 0.35 if ("less_walking" in mods or trip.transport == "walking") else 0.08
        score -= distance_weight * dist
        if budget_cap is not None and p.price_eur is not None and p.price_eur * trip.guests > budget_cap and p.id not in must:
            excluded.append(p.name)
            continue
        if trip.transport == "walking" and dist > 6 and p.id not in must:
            continue  # недостижно пешки во разумно време
        out.append({
            "id": p.id, "name": p.name, "category": p.category, "duration": p.visit_duration_min,
            "price": float(p.price_eur) if p.price_eur is not None else None, "lat": p.lat, "lng": p.lng,
            "required": p.is_required_landmark, "score": round(score, 3), "reason": "; ".join(reasons),
            "opening": p.opening_time, "closing": p.closing_time, "must": p.id in must,
        })
    out.sort(key=lambda c: c["score"], reverse=True)
    return out, excluded


def _minutes_between(a, b, transport):
    from core.geo import estimate_travel

    return estimate_travel(a["lat"], a["lng"], b["lat"], b["lng"], transport)[1]


def rule_based_selection(candidates, days, per_day, start, transport, budget_min=450):
    """Детерминистички избор: семе = најдобро место, па се додаваат блиски места со висок резултат."""
    unused = list(candidates)
    plan = []
    origin = {"lat": start[0], "lng": start[1]}
    for _ in range(days):
        day, used_min, last = [], 0.0, origin
        while unused and len(day) < per_day:
            def value(c):
                return c["score"] + (1000 if c["must"] else 0) - _minutes_between(last, c, transport) / 15

            best = max(unused, key=value)
            cost = _minutes_between(last, best, transport) + best["duration"]
            if used_min + cost > budget_min and day:
                break
            day.append(best["id"])
            used_min += cost
            last = best
            unused.remove(best)
        plan.append(day)
    return plan


def schedule_day(ids, by_id, km, minutes, index_of, day_date):
    """Временски блокови. Враќа (items, violations, travel_total)."""
    t = datetime.combine(day_date, DAY_START)
    items, violations, travel_total, prev, lunch_done = [], 0, 0.0, 0, False
    for pid in ids:
        node = index_of[pid]
        c = by_id[pid]
        travel = minutes[prev][node]
        dist = km[prev][node]
        if not lunch_done and t.time() >= LUNCH_AFTER:
            items.append({"type": "MEAL", "start": t, "end": t + timedelta(minutes=LUNCH_MIN)})
            t += timedelta(minutes=LUNCH_MIN)
            lunch_done = True
        t += timedelta(minutes=travel)
        travel_total += travel
        warning = ""
        if c["opening"] and t.time() < c["opening"]:
            t = datetime.combine(day_date, c["opening"])
        end = t + timedelta(minutes=c["duration"])
        if c["closing"] and end.time() > c["closing"]:
            violations += 1
            warning = "Можно е да затвори пред крајот на посетата."
        items.append({"type": "PLACE", "id": pid, "start": t, "end": end, "travel": travel, "km": dist,
                      "warning": warning})
        t = end
        prev = node
    if not lunch_done and items:
        items.append({"type": "MEAL", "start": t, "end": t + timedelta(minutes=LUNCH_MIN)})
        t += timedelta(minutes=LUNCH_MIN)
    if t.time() > DAY_END or t.date() != day_date:
        violations += 1
    return items, violations, travel_total


def nearest_restaurant(city, lat, lng):
    best, best_d = None, None
    for b in Business.objects.filter(city=city, type=Business.Type.RESTAURANT,
                                     verification_status=Business.Verification.APPROVED):
        d = haversine_km(lat, lng, b.lat, b.lng)
        if best_d is None or d < best_d:
            best, best_d = b, d
    return best, best_d


def generate_plan(trip, instructions=""):
    t0 = time.monotonic()
    if instructions:
        mods = set(trip.modifiers.get("active", [])) | parse_revision(instructions)
        trip.modifiers = {"active": sorted(mods), "last_instruction": instructions[:300]}
        trip.save(update_fields=["modifiers"])
    warnings = []
    candidates, excluded = retrieve_candidates(trip)
    if excluded:
        warnings.append(f"Изоставени поради буџетот: {', '.join(excluded)}.")
    if not candidates:
        warnings.append("Нема проверени места што одговараат на барањето.")
    by_id = {c["id"]: c for c in candidates}
    per_day = per_day_count(trip)
    s_lat, s_lng, s_label = start_point(trip)

    provider, model_name, reasons, rejected, validation_errors = "rule_based", "", {}, [], []
    selection = None
    if llm.llm_enabled() and candidates:
        try:
            selection, reasons, rejected, validation_errors = llm.select_with_llm(
                trip, candidates[:40], per_day, trip.modifiers.get("last_instruction", ""))
            provider, model_name = "anthropic", llm.settings.LLM_MODEL
            if selection is None or not any(selection):
                raise ValueError("празен избор")
        except Exception as exc:
            warnings.append("AI моделот не беше достапен; планот е создаден со детерминистички алгоритам.")
            validation_errors.append(str(exc)[:200])
            selection, provider, model_name = None, "rule_based_fallback", ""
    if selection is None:
        selection = rule_based_selection(candidates, trip.days, per_day, (s_lat, s_lng), trip.transport,
                                         day_minutes(trip))
    # Задолжителните места мора да се во планот.
    chosen = {pid for day in selection for pid in day}
    for c in candidates:
        if c["must"] and c["id"] not in chosen:
            min(selection, key=len).append(c["id"])

    all_ids = [pid for day in selection for pid in day]
    points = [(s_lat, s_lng)] + [(by_id[p]["lat"], by_id[p]["lng"]) for p in all_ids]
    km, minutes, routing_provider, route_warnings = travel_matrix(points, trip.transport)
    warnings += route_warnings
    index_of = {pid: i + 1 for i, pid in enumerate(all_ids)}

    metrics = {"baseline_travel_min": 0.0, "optimized_travel_min": 0.0, "baseline_violations": 0,
               "optimized_violations": 0}
    days_out = []
    for d, ids in enumerate(selection):
        day_date = trip.start_date + timedelta(days=d)
        nodes = [index_of[p] for p in ids]
        sub = [[minutes[i][j] for j in [0] + nodes] for i in [0] + nodes]
        order_local = optimize_order(sub) if nodes else []
        optimized = [ids[k - 1] for k in order_local]
        b_items, b_viol, b_travel = schedule_day(ids, by_id, km, minutes, index_of, day_date)
        o_items, o_viol, o_travel = schedule_day(optimized, by_id, km, minutes, index_of, day_date)
        # Оптимизацијата се прифаќа само ако не е полоша по прекршувања и време.
        if (o_viol, o_travel) > (b_viol, b_travel):
            o_items, o_viol, o_travel = b_items, b_viol, b_travel
        metrics["baseline_travel_min"] += b_travel
        metrics["optimized_travel_min"] += o_travel
        metrics["baseline_violations"] += b_viol
        metrics["optimized_violations"] += o_viol
        days_out.append((d + 1, day_date, o_items))

    unknown_hours = sum(1 for p in all_ids if not by_id[p]["opening"])
    unknown_price = sum(1 for p in all_ids if by_id[p]["price"] is None)
    if unknown_hours:
        warnings.append(f"За {unknown_hours} места работното време не е проверено — потребна е потврда.")
    if unknown_price:
        warnings.append(f"За {unknown_price} места цената не е позната и не е вклучена во трошоците.")
    if metrics["optimized_violations"]:
        warnings.append("Некои денови не можат целосно да ги исполнат временските ограничувања.")

    covered = {i for i in trip.interests if any(by_id[p]["category"] in INTEREST_CATEGORIES.get(i, ()) for p in all_ids)}
    b, o = metrics["baseline_travel_min"], metrics["optimized_travel_min"]
    metrics.update({
        "baseline_travel_min": round(b, 1), "optimized_travel_min": round(o, 1),
        "travel_improvement_pct": round((b - o) / b * 100, 1) if b else 0.0,
        "interest_coverage": round(len(covered) / len(trip.interests), 2) if trip.interests else None,
        "place_validity": 1.0 if all_ids else None,
        "places_selected": len(all_ids),
        "unknown_hours": unknown_hours, "unknown_prices": unknown_price,
    })

    with transaction.atomic():
        trip.itinerary_days.all().delete()
        known_cost = Decimal("0")
        for number, day_date, items in days_out:
            day = ItineraryDay.objects.create(trip=trip, day_number=number, date=day_date,
                                              notes=f"Почеток: {s_label}")
            last_lat, last_lng = s_lat, s_lng
            for idx, it in enumerate(items):
                if it["type"] == "MEAL":
                    rest, dist = nearest_restaurant(trip.city, last_lat, last_lng)
                    ItineraryItem.objects.create(
                        day=day, source_type="MEAL", business=rest, order_index=idx,
                        title=f"Ручек — {rest.name}" if rest else "Пауза за ручек",
                        start_time=it["start"].time(), end_time=it["end"].time(),
                        reason=f"најблизок ресторан (~{dist:.1f} km)" if rest else "слободен избор",
                    )
                    continue
                c = by_id[it["id"]]
                cost = Decimal(str(c["price"])) * trip.guests if c["price"] is not None else None
                if cost:
                    known_cost += cost
                ItineraryItem.objects.create(
                    day=day, place_id=c["id"], source_type="PLACE", title=c["name"], order_index=idx,
                    start_time=it["start"].time(), end_time=it["end"].time(),
                    travel_minutes_from_prev=round(it["travel"], 1), distance_km_from_prev=round(it["km"], 2),
                    est_cost=cost, reason=reasons.get(c["id"]) or c["reason"] or "блиску до маршрутата",
                    warning=it["warning"],
                )
                last_lat, last_lng = c["lat"], c["lng"]
        metrics["known_cost_eur"] = float(known_cost)
        if trip.budget and known_cost > trip.budget:
            warnings.append("Познатите трошоци го надминуваат буџетот.")
        trip.warnings = warnings
        trip.status = "GENERATED"
        trip.save(update_fields=["warnings", "status", "updated_at"])
        metrics["generation_ms"] = int((time.monotonic() - t0) * 1000)
        run = AIPlanRun.objects.create(
            trip=trip, provider=provider, model=model_name, routing_provider=routing_provider,
            selected_place_ids=all_ids, rejected_ids=[str(r) for r in rejected],
            validation_result={"valid": True, "errors": validation_errors, "unknown_ids_rejected": len(rejected)},
            metrics=metrics, instructions=(instructions or "")[:500], duration_ms=metrics["generation_ms"],
        )
    return run
