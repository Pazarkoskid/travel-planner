import json
import logging
import urllib.request

from django.conf import settings

logger = logging.getLogger(__name__)

SYSTEM = (
    "Ти си туристички планер за Северна Македонија. Избираш САМО од дадените кандидати по нивниот id. "
    "Не измислувај места, цени, работно време ни достапност. Врати САМО валиден JSON без друг текст."
)


def llm_enabled():
    return settings.LLM_PROVIDER == "anthropic" and bool(settings.ANTHROPIC_API_KEY)


def build_prompt(trip, candidates, per_day, instructions=""):
    cand = [{"id": c["id"], "name": c["name"], "category": c["category"], "duration_min": c["duration"],
             "price_eur": c["price"], "required_landmark": c["required"]} for c in candidates]
    return (
        f"Град: {trip.city.name}. Денови: {trip.days}. Гости: {trip.guests}. Буџет (EUR, вкупно): {trip.budget}. "
        f"Интереси: {', '.join(trip.interests) or 'општо'}. Темпо: {trip.pace} (до {per_day} места дневно). "
        f"Превоз: {trip.transport}. Дополнителни барања: {instructions or 'нема'}.\n"
        f"Кандидати: {json.dumps(cand, ensure_ascii=False)}\n"
        'Формат: {"days": [{"day": 1, "place_ids": [1, 2], "reasons": {"1": "кратко зошто"}}]}. '
        "Групирај места што се блиску во ист ден. Секое место најмногу еднаш."
    )


def call_llm(prompt):
    body = json.dumps({
        "model": settings.LLM_MODEL, "max_tokens": 1500, "system": SYSTEM,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=body, method="POST",
        headers={"x-api-key": settings.ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=settings.LLM_TIMEOUT_SECONDS) as resp:
        data = json.loads(resp.read().decode())
    return "".join(block.get("text", "") for block in data.get("content", []))


def parse_and_validate(raw, valid_ids, days):
    errors, rejected = [], []
    text = raw.strip()
    try:
        if "{" in text:
            text = text[text.index("{"): text.rindex("}") + 1]
        data = json.loads(text)
        day_list = data["days"]
        assert isinstance(day_list, list)
    except Exception:
        return None, {}, [], ["Невалиден JSON од моделот"]
    used, result, reasons = set(), [[] for _ in range(days)], {}
    for entry in day_list:
        try:
            d = int(entry.get("day", 0)) - 1
        except (TypeError, ValueError):
            continue
        if not 0 <= d < days:
            errors.append(f"Невалиден ден {entry.get('day')}")
            continue
        for pid in entry.get("place_ids", []):
            try:
                pid = int(pid)
            except (TypeError, ValueError):
                rejected.append(pid)
                continue
            if pid not in valid_ids:
                rejected.append(pid)
                continue
            if pid in used:
                continue
            used.add(pid)
            result[d].append(pid)
        for k, v in (entry.get("reasons") or {}).items():
            if str(k).isdigit() and int(k) in used:
                reasons[int(k)] = str(v)[:300]
    if rejected:
        errors.append(f"Отфрлени непознати IDs: {rejected}")
    return result, reasons, rejected, errors


def select_with_llm(trip, candidates, per_day, instructions=""):
    valid = {c["id"] for c in candidates}
    raw = call_llm(build_prompt(trip, candidates, per_day, instructions))
    return parse_and_validate(raw, valid, trip.days)
