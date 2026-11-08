"""Евалуација на планерот со и без јазичен модел.

Ги генерира истите комбинации како во поглавје 9.2 од трудот:
3 града x 2/3 дена x 3 темпа x 2 превоза x 3 групи интереси x 2 режима подвижност = 216 планови.

Примери:
    python manage.py evaluate_planner                       # само детерминистички (без трошок)
    python manage.py evaluate_planner --llm --subset 36     # 36 комбинации, секоја со и без модел
    python manage.py evaluate_planner --llm --model claude-haiku-5-5
    python manage.py evaluate_planner --llm --provider gemini --subset 36

За --llm се потребни ANTHROPIC_API_KEY (--provider anthropic) или
GEMINI_API_KEY (--provider gemini) во околината. Резултатите се запишуваат во
eval_results/<време>/ (plans.csv, summary.json, summary.md).
"""
import csv
import itertools
import json
import random
import statistics
import time
from datetime import date, timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from destinations.models import City, Place
from trips import llm
from trips.models import Trip
from trips.planner import INTEREST_CATEGORIES, generate_plan

CITIES = ["ohrid", "skopje", "bitola"]
DAYS = [2, 3]
PACES = ["relaxed", "balanced", "intense"]
TRANSPORTS = ["walking", "car"]
INTERESTS = {
    "history_culture": ["history", "culture"],
    "nature_beach": ["nature", "beach"],
    "religion_museums": ["religion", "museums"],
}
MOBILITY = ["standard", "wheelchair"]


class _Rollback(Exception):
    pass


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return round(statistics.mean(xs), 3) if xs else None


def _median(xs):
    xs = [x for x in xs if x is not None]
    return round(statistics.median(xs), 3) if xs else None


class Command(BaseCommand):
    help = "Евалуација на планерот (216 комбинации) со и без јазичен модел."

    def add_arguments(self, parser):
        parser.add_argument("--llm", action="store_true", help="Секоја комбинација и со јазичниот модел.")
        parser.add_argument("--subset", type=int, default=0, help="Случаен стратификуван подмножество (0 = сите).")
        parser.add_argument("--provider", choices=["anthropic", "gemini"], default="anthropic")
        parser.add_argument("--model", default="", help="Име на модел (стандардно според провајдерот).")
        parser.add_argument("--sleep", type=float, default=None,
                            help="Пауза во секунди по секој повик (стандардно 5 за gemini, 0 за anthropic).")
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument("--guests", type=int, default=2)
        parser.add_argument("--budget", type=int, default=300)
        parser.add_argument("--out", default="eval_results")

    def handle(self, *args, **o):
        if o["llm"]:
            key = settings.GEMINI_API_KEY if o["provider"] == "gemini" else settings.ANTHROPIC_API_KEY
            if not key:
                env = "GEMINI_API_KEY" if o["provider"] == "gemini" else "ANTHROPIC_API_KEY"
                raise CommandError(f"За --llm --provider {o['provider']} постави {env} во околината.")
            if not o["model"]:
                o["model"] = "gemini-2.5-flash" if o["provider"] == "gemini" else settings.LLM_MODEL
            if o["sleep"] is None:
                o["sleep"] = 5.0 if o["provider"] == "gemini" else 0.0
        cities = {c.slug: c for c in City.objects.filter(slug__in=CITIES)}
        missing = set(CITIES) - set(cities)
        if missing:
            raise CommandError(f"Недостасуваат градови {missing}. Изврши: python manage.py seed_demo")

        combos = list(itertools.product(CITIES, DAYS, PACES, TRANSPORTS, INTERESTS, MOBILITY))
        if o["subset"] and o["subset"] < len(combos):
            rnd = random.Random(o["seed"])
            by_city = {c: [x for x in combos if x[0] == c] for c in CITIES}
            per = max(1, o["subset"] // len(CITIES))
            combos = [x for c in CITIES for x in rnd.sample(by_city[c], min(per, len(by_city[c])))]

        user, _ = get_user_model().objects.get_or_create(username="eval-bot", defaults={"email": "eval@example.com"})
        modes = ["rule_based"] + (["llm"] if o["llm"] else [])
        rows = []
        for i, (city, days, pace, transport, interest_key, mobility) in enumerate(combos, 1):
            base = {"combo": i, "city": city, "days": days, "pace": pace, "transport": transport,
                    "interests": interest_key, "mobility": mobility}
            selections = {}
            for mode in modes:
                row = dict(base, mode=mode)
                row.update(self._run_one(user, cities[city], days, pace, transport, INTERESTS[interest_key],
                                         mobility, mode, o))
                selections[mode] = set(row.pop("_ids"))
                rows.append(row)
            if len(selections) == 2:
                a, b = selections["rule_based"], selections["llm"]
                jacc = round(len(a & b) / len(a | b), 3) if a | b else None
                rows[-1]["jaccard_vs_rule_based"] = jacc
            self.stdout.write(f"[{i}/{len(combos)}] {city} {days}d {pace} {transport} {interest_key} {mobility}")
            if rows[-1].get("error"):
                self.stdout.write(self.style.WARNING(f"    модел: грешка → резервен алгоритам: {rows[-1]['error']}"))

        out = Path(o["out"]) / time.strftime("%Y%m%d-%H%M%S")
        out.mkdir(parents=True, exist_ok=True)
        fields = sorted({k for r in rows for k in r}, key=lambda k: (k not in base and k != "mode", k))
        with open(out / "plans.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
        summary = {m: self._summarize([r for r in rows if r["mode"] == m]) for m in modes}
        summary["_config"] = {k: o[k] for k in ("subset", "seed", "guests", "budget")} | {
            "provider": o["provider"] if o["llm"] else None,
            "model": (o["model"] or settings.LLM_MODEL) if o["llm"] else None, "combos": len(combos)}
        (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        (out / "summary.md").write_text(self._markdown(summary, modes), encoding="utf-8")
        self.stdout.write(self._markdown(summary, modes))
        self.stdout.write(self.style.SUCCESS(f"Резултати: {out}"))

    def _run_one(self, user, city, days, pace, transport, interests, mobility, mode, o):
        old = (settings.LLM_PROVIDER, settings.LLM_MODEL)
        if mode == "llm":
            settings.LLM_PROVIDER = o["provider"]
            if o["model"]:
                settings.LLM_MODEL = o["model"]
        else:
            settings.LLM_PROVIDER = "none"
        result = {}
        try:
            with transaction.atomic():
                trip = Trip.objects.create(
                    user=user, city=city, start_date=date(2026, 6, 15) + timedelta(days=0), days=days,
                    guests=o["guests"], budget=o["budget"], interests=interests, pace=pace,
                    transport=transport, mobility=mobility)
                t0 = time.monotonic()
                run = generate_plan(trip)
                wall = int((time.monotonic() - t0) * 1000)
                m = run.metrics
                ids = list(run.selected_place_ids)
                places = {p.pk: p for p in Place.objects.filter(pk__in=ids)}
                required = set(Place.objects.filter(city=city, status=Place.Status.VERIFIED,
                                                    is_required_landmark=True).values_list("pk", flat=True))
                interest_cats = set().union(*(INTEREST_CATEGORIES.get(i, set()) for i in interests))
                cats = [places[p].category for p in ids if p in places]
                per_day = [sum(1 for it in d.items.all() if it.source_type == "PLACE")
                           for d in trip.itinerary_days.all()]
                result = {
                    "provider": run.provider,
                    "fallback": run.provider == "rule_based_fallback",
                    "places": len(ids),
                    "places_per_day_min": min(per_day) if per_day else 0,
                    "places_per_day_max": max(per_day) if per_day else 0,
                    "baseline_travel_min": m["baseline_travel_min"],
                    "optimized_travel_min": m["optimized_travel_min"],
                    "improvement_pct": m["travel_improvement_pct"],
                    "violations_before": m["baseline_violations"],
                    "violations_after": m["optimized_violations"],
                    "interest_coverage": m["interest_coverage"],
                    "interest_share": round(sum(c in interest_cats for c in cats) / len(cats), 3) if cats else None,
                    "distinct_categories": len(set(cats)),
                    "required_landmarks_share": (round(len(required & set(ids)) / len(required), 3)
                                                 if required else None),
                    "catalog_validity": 1.0 if all(p in places for p in ids) else 0.0,
                    "rejected_ids": len(run.rejected_ids),
                    "error": "; ".join(run.validation_result.get("errors", []))[:200] if run.provider == "rule_based_fallback" else "",
                    "known_cost_eur": m.get("known_cost_eur"),
                    "accessible_share": m.get("accessible_share"),
                    "generation_ms": wall,
                    "_ids": ids,
                }
                raise _Rollback
        except _Rollback:
            pass
        finally:
            settings.LLM_PROVIDER, settings.LLM_MODEL = old
        if mode == "llm" and o.get("sleep"):
            time.sleep(o["sleep"])  # бесплатниот план на Gemini има ограничување на барања во минута
        return result

    @staticmethod
    def _summarize(rows):
        if not rows:
            return {}
        imp = [r["improvement_pct"] for r in rows]
        return {
            "plans": len(rows),
            "fallback_rate": _mean([float(r["fallback"]) for r in rows]),
            "baseline_travel_min": _mean([r["baseline_travel_min"] for r in rows]),
            "optimized_travel_min": _mean([r["optimized_travel_min"] for r in rows]),
            "improvement_pct_mean": _mean(imp),
            "improvement_pct_median": _median(imp),
            "violations_before": sum(r["violations_before"] for r in rows),
            "violations_after": sum(r["violations_after"] for r in rows),
            "catalog_validity": _mean([r["catalog_validity"] for r in rows]),
            "interest_coverage": _mean([r["interest_coverage"] for r in rows]),
            "interest_share": _mean([r["interest_share"] for r in rows]),
            "distinct_categories": _mean([r["distinct_categories"] for r in rows]),
            "required_landmarks_share": _mean([r["required_landmarks_share"] for r in rows]),
            "places": _mean([r["places"] for r in rows]),
            "rejected_ids_total": sum(r["rejected_ids"] for r in rows),
            "generation_ms_mean": _mean([r["generation_ms"] for r in rows]),
            "generation_ms_max": max(r["generation_ms"] for r in rows),
            "jaccard_vs_rule_based": _mean([r.get("jaccard_vs_rule_based") for r in rows]),
        }

    @staticmethod
    def _markdown(summary, modes):
        keys = [k for k in summary[modes[0]]]
        lines = ["| Метрика | " + " | ".join(modes) + " |", "|---|" + "---|" * len(modes)]
        for k in keys:
            lines.append(f"| {k} | " + " | ".join(str(summary[m].get(k)) for m in modes) + " |")
        return "\n".join(lines) + "\n"
