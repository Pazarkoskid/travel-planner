"""Превод на текстовите што ги генерира серверот (план, предупредувања, PDF) на англиски.

Јазикот се зема од заглавието Accept-Language (frontend-от го праќа „en“ или „mk“).
Податоците од каталогот (имиња на места, описи) остануваат на македонски; преведуваат се
фиксните реченици и шаблоните со вредности. Непознат текст се враќа непроменет.
"""
import re

from destinations import accessibility_data as acc

STATUS_EN = {
    "Чека одговор": "Awaiting reply", "Понудено (такси)": "Quoted (taxi)", "Предложен друг термин": "Another time proposed",
    "Потврдено": "Confirmed", "Во тек": "In progress", "Завршено": "Completed", "Одбиено": "Rejected", "Откажано": "Cancelled",
}
CITY_EN = {"Охрид": "Ohrid", "Скопје": "Skopje", "Битола": "Bitola", "Струга": "Struga"}
INTEREST_EN = {
    "историја": "history", "цркви и манастири": "churches and monasteries", "природа": "nature", "плажи": "beaches",
    "култура": "culture", "локална храна": "local food", "активности": "activities", "музеи": "museums",
}

EXACT = {
    "клучна знаменитост на градот": "key landmark of the city",
    "го означивте како задолжително": "you marked it as a must-see",
    "пристапно со инвалидска количка": "wheelchair accessible",
    "без скали": "step-free",
    "блиску до маршрутата": "close to the route",
    "слободен избор": "your choice",
    "Пауза за ручек": "Lunch break",
    "Можно е да затвори пред крајот на посетата.": "It may close before the end of the visit.",
    "Пристапноста не е проверена — јавете се однапред.": "Accessibility not verified — call ahead.",
    "Делумно пристапно — проверете го теренот.": "Partly accessible — check the terrain.",
    "Непристапно.": "Not accessible.",
    "Нема проверени места што одговараат на барањето.": "No verified places match the request.",
    "AI моделот не беше достапен; планот е создаден со детерминистички алгоритам.":
        "The AI model was unavailable; the plan was created with the deterministic algorithm.",
    "Некои денови не можат целосно да ги исполнат временските ограничувања.":
        "Some days cannot fully meet the time constraints.",
    "Познатите трошоци го надминуваат буџетот.": "Known costs exceed the budget.",
    "Пристапен режим: времето за посета е зголемено, а податоците за пристапност се проценки — проверете ги пред тргнување.":
        "Accessible mode: visit times are longer, and accessibility data are estimates — check before you go.",
    "Сервисот за рутирање е недостапен; времињата се проценети од воздушно растојание.":
        "The routing service is unavailable; times are estimated from straight-line distance.",
    "Времињата за движење се проценка (воздушно растојание × фактор), не реална рута.":
        "Travel times are estimates (straight-line distance × factor), not a real route.",
    acc.NOTE: acc.NOTE_EN,
    "5 различни места во градот": "5 different places in the city",
    "50% од задолжителните знаменитости": "50% of the required landmarks",
    "Сите задолжителни знаменитости": "All required landmarks",
    "Истражувач": "Explorer", "Прво документирано место": "First documented place",
    "Истражувач на Македонија": "Macedonia Explorer", "100% во повеќе градови": "100% in several cities",
    "Фото-посетата не е одобрена": "The photo check-in was not approved", "Нова рецензија": "New review",
    "Бизнисот одговори на вашата рецензија": "The business replied to your review",
    "Ново барање за сместување": "New accommodation request", "Ново барање за бродска тура": "New boat tour request",
    "Ново барање за маса": "New table request", "Ново барање за такси": "New taxi request",
}


def _badge_text():
    from gamification.catalog import badge_text_en

    return badge_text_en()


_BADGES = None


def _city(name):
    return CITY_EN.get(name, name)


def _note(text):
    """Белешка за пристапност: „<белешка> <NOTE>“ → англиски."""
    text = text.strip()
    if text.endswith(acc.NOTE):
        base = text[: -len(acc.NOTE)].strip()
        return f"{acc.NOTES_EN.get(base, base)} {acc.NOTE_EN}".strip()
    return acc.NOTES_EN.get(text, text)


PATTERNS = [
    (re.compile(r"^Документирана посета на (.+)$"), lambda m: f"Documented visit to {m[1]}"),
    (re.compile(r"^Локален авантурист — (.+)$"), lambda m: f"Local Adventurer — {_city(m[1])}"),
    (re.compile(r"^Градски истражувач — (.+)$"), lambda m: f"City Explorer — {_city(m[1])}"),
    (re.compile(r"^(.+) 100% — Мајстор на градот$"), lambda m: f"{_city(m[1])} 100% — City Master"),
    (re.compile(r"^Нов печат: (.+)$"), lambda m: f"New stamp: {tr(m[1], 'en')}"),
    (re.compile(r"^Резервација #(\d+)$"), lambda m: f"Booking #{m[1]}"),
    (re.compile(r"^(.+) ја лајкна вашата фотографија$"), lambda m: f"{m[1]} liked your photo"),
    (re.compile(r"^Ново барање за пријателство од (.+)$"), lambda m: f"New friend request from {m[1]}"),
    (re.compile(r"^(.+) го прифати вашето барање за пријателство$"), lambda m: f"{m[1]} accepted your friend request"),
    (re.compile(r"^Резервација #(\d+): (.+)$"), lambda m: f"Booking #{m[1]}: {STATUS_EN.get(m[2], m[2])}"),
    (re.compile(r"^Оценка (\d)/5$"), lambda m: f"Rating {m[1]}/5"),
    (re.compile(r"^одговара на интересот: (.+)$"),
     lambda m: "matches your interest: " + ", ".join(INTEREST_EN.get(x.strip(), x.strip()) for x in m[1].split(","))),
    (re.compile(r"^најблизок ресторан \(~([\d.]+) km\)$"), lambda m: f"nearest restaurant (~{m[1]} km)"),
    (re.compile(r"^Ручек — (.+)$"), lambda m: f"Lunch — {m[1]}"),
    (re.compile(r"^Почеток: сместување „(.+)“$"), lambda m: f"Start: accommodation “{m[1]}”"),
    (re.compile(r"^Почеток: центар на (.+)$"), lambda m: f"Start: centre of {_city(m[1])}"),
    (re.compile(r"^(\d+) дена во (.+)$"), lambda m: f"{m[1]} days in {_city(m[2])}"),
    (re.compile(r"^Изоставени поради буџетот: (.+)\.$"), lambda m: f"Left out because of the budget: {m[1]}."),
    (re.compile(r"^Изоставени како непристапни: (.+)\.$"), lambda m: f"Left out as not accessible: {m[1]}."),
    (re.compile(r"^За (\d+) места работното време не е проверено — потребна е потврда\.$"),
     lambda m: f"Opening hours are not verified for {m[1]} places — please confirm."),
    (re.compile(r"^За (\d+) места цената не е позната и не е вклучена во трошоците\.$"),
     lambda m: f"The price is unknown for {m[1]} places and is not included in the costs."),
    (re.compile(r"^Делумно пристапно: (.+)$", re.S), lambda m: f"Partly accessible: {_note(m[1])}"),
    (re.compile(r"^Непристапно: (.+)$", re.S), lambda m: f"Not accessible: {_note(m[1])}"),
]


def get_lang(request):
    if request is None:
        return "mk"
    explicit = getattr(request, "query_params", {}).get("lang") if hasattr(request, "query_params") else None
    header = (explicit or request.META.get("HTTP_ACCEPT_LANGUAGE", "")).lower()
    return "en" if header.startswith("en") else "mk"


def _one(text):
    global _BADGES
    text = text.strip()
    if text in EXACT:
        return EXACT[text]
    if _BADGES is None:
        _BADGES = _badge_text()
    if text in _BADGES:
        return _BADGES[text]
    for rx, fn in PATTERNS:
        m = rx.match(text)
        if m:
            return fn(m)
    return _note(text) if text.endswith(acc.NOTE) or text in acc.NOTES_EN else text


def tr(text, lang):
    """Преведува реченица. Причините („a; b; c“) се преведуваат дел по дел; белешките за
    пристапност можат да содржат „;“, па нив ги препознаваме по почетокот."""
    if lang != "en" or not text:
        return text
    text = text.strip()
    for known in ("Можно е да затвори пред крајот на посетата.",):
        if text.startswith(known + " "):
            return _one(known) + " " + tr(text[len(known) + 1:], lang)
    if text.startswith(("Делумно пристапно:", "Непристапно:")) or text.endswith(acc.NOTE) or text in acc.NOTES_EN:
        return _one(text)
    if "; " in text:
        return "; ".join(_one(p) for p in text.split("; "))
    return _one(text)
