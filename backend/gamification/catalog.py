"""Каталог на беџови со слики (frontend/public/badges/).

Податоците се чисти Python структури (без Django import), за да ги користат и
миграцијата (историски модели) и скриптата за слики (tools/badges.py).

Правила (Badge.rule):
  {"city": "ohrid"}                         — прва одобрена посета во градот
  {"places": ["ohrid/kej", ...]}            — посета на кое било од местата
  {"categories": ["HISTORY"], "min": 3}     — N различни места од категоријата
  {"photos": 10}                            — N одобрени фото-посети
Беџ без правило што може да се исполни е „наскоро“ (available=False).
"""

ART = "/badges/{}.webp"

# Групи → боја на рамката
GROUPS = {
    "city": ("Град", "#0f4c5c"),
    "water": ("Езеро и вода", "#1b64a8"),
    "nature": ("Природа", "#1d7a4f"),
    "heritage": ("Наследство", "#a3462b"),
}

# (број, slug на сликата, име, група, правило или None)
LOCATIONS = [
    (1, "skopje", "Скопје", "city", {"city": "skopje"}),
    (2, "ohrid", "Охрид", "city", {"city": "ohrid"}),
    (3, "bitola", "Битола", "city", {"city": "bitola"}),
    (4, "struga", "Струга", "city", None),
    (5, "krusevo", "Крушево", "city", None),
    (6, "prilep", "Прилеп", "city", None),
    (7, "tetovo", "Тетово", "city", None),
    (8, "stip", "Штип", "city", None),
    (9, "veles", "Велес", "city", None),
    (10, "gevgelija", "Гевгелија", "city", None),
    (11, "kicevo", "Кичево", "city", None),
    (12, "kavadarci", "Кавадарци", "city", None),
    (13, "strumica", "Струмица", "city", None),
    (14, "kochani", "Кочани", "city", None),
    (15, "demir_kapija", "Демир Капија", "nature", None),
    (16, "globocica", "Глобочица", "water", None),
    (17, "ohrid_lake", "Охридско Езеро", "water",
     {"places": ["ohrid/kej", "ohrid/lagadin", "ohrid/zaliv-na-koskite", "ohrid/kaneo", "ohrid/sv-naum",
                 "ohrid/izvori-crn-drim"]}),
    (18, "prespa_lake", "Преспанско Езеро", "water", None),
    (19, "mladost_lake", "Езеро Младост", "water", None),
    (20, "shar_mountain", "Шар Планина", "nature", None),
    (21, "mavrovo_lake", "Мавровско Езеро", "water", None),
    (22, "bregalnica_lake", "Брегалница", "water", None),
    (23, "dojran_lake", "Дојранско Езеро", "water", None),
    (24, "kalishte", "Калиште", "water", None),
    (25, "matka_canyon", "Кањон Матка", "nature", {"places": ["skopje/matka"]}),
    (26, "vranjski_izvori", "Врански извори", "nature", None),
    (27, "shar_mountain_flora", "Флора на Шар Планина", "nature", None),
    (28, "jakupica", "Јакупица", "nature", None),
    (29, "sveti_naum", "Свети Наум", "heritage", {"places": ["ohrid/sv-naum"]}),
    (30, "samuil_fortress", "Самуилова тврдина", "heritage", {"places": ["ohrid/samoilova-tvrdina"]}),
    (31, "pekhina", "Пештера", "nature", None),
    (32, "galichnik", "Галичник", "heritage", None),
    (33, "kratovo", "Кратово", "heritage", None),
    (34, "pirin_springs", "Пирински извори", "nature", None),
    (35, "crno_drvore", "Црно Дрво", "nature", None),
    (36, "pelister", "Пелистер", "nature", {"places": ["bitola/pelister"]}),
    (37, "belchishki_springs", "Белчишки извори", "water", None),
    (38, "crna_reka", "Црна Река", "water", None),
    (39, "lebarski_hajduk", "Дебарски хајдук", "heritage", None),
    (40, "sv_prohor_pchinski", "Св. Прохор Пчињски", "heritage", None),
]

# Достигнувања: (code, име, опис, икона, боја, правило или None)
ACHIEVEMENTS = [
    ("nature-explorer", "Истражувач на природата", "3 природни места или видиковци", "leaf", "#1d7a4f",
     {"categories": ["NATURE", "VIEWPOINT", "BEACH"], "min": 3}),
    ("history-buff", "Љубител на историјата", "3 историски места", "column", "#a36a1f",
     {"categories": ["HISTORY"], "min": 3}),
    ("culture-explorer", "Културен истражувач", "3 музеи, цркви или културни места", "amphora", "#7a2f86",
     {"categories": ["CULTURE", "MUSEUM", "RELIGIOUS"], "min": 3}),
    ("mountain-hiker", "Планинар", "2 планински видиковци", "mountain", "#2f5d3a",
     {"places": ["ohrid/galicica-vidikovec", "bitola/pelister", "skopje/milenium-krst"], "min": 2}),
    ("lake-explorer", "Езерски брег", "3 места покрај Охридското Езеро", "waves", "#1b64a8",
     {"places": ["ohrid/kej", "ohrid/lagadin", "ohrid/zaliv-na-koskite", "ohrid/kaneo", "ohrid/sv-naum",
                 "ohrid/izvori-crn-drim"], "min": 3}),
    ("photographer", "Фотограф", "10 одобрени фото-посети", "camera", "#26343a", {"photos": 10}),
    ("wine-traveler", "Вински патник", "Винарии во Тиквешијата — наскоро", "wine", "#7d1f3a", None),
]

# Слики за постоечките беџови (код → слика)
EXISTING_ART = {
    "explorer": "explorer",
    "macedonia-explorer": "macedonia-100",
    "city-ohrid-100": "ohrid-100",
    "city-skopje-100": "skopje-100",
    "city-bitola-100": "bitola-100",
}


def location_art(num, slug):
    return f"loc-{num:02d}-{slug}"


def art_for_code(code):
    name = EXISTING_ART.get(code)
    return ART.format(name) if name else ""


def sync_catalog(Badge):
    """Создава/ажурира REGION и CATEGORY беџови и ги поставува сликите. Идемпотентно."""
    for num, slug, name, group, rule in LOCATIONS:
        Badge.objects.update_or_create(code=f"region-{slug.replace('_', '-')}", defaults={
            "name": name, "description": f"{GROUPS[group][0]} — колекција „Македонија“",
            "kind": "REGION", "icon": "📍", "art": ART.format(location_art(num, slug)),
            "rule": rule or {}, "available": bool(rule), "sort": num})
    for i, (code, name, desc, _icon, _color, rule) in enumerate(ACHIEVEMENTS):
        Badge.objects.update_or_create(code=code, defaults={
            "name": name, "description": desc, "kind": "CATEGORY", "icon": "🏅", "art": ART.format(code),
            "rule": rule or {}, "available": bool(rule), "sort": 100 + i})
    order = {"explorer": 50, "city-ohrid-100": 60, "city-skopje-100": 61, "city-bitola-100": 62, "macedonia-explorer": 99}
    for code, art in EXISTING_ART.items():
        Badge.objects.filter(code=code).update(art=ART.format(art), sort=order.get(code, 0))
    # Беџовите за поединечни места остануваат класичен печат (сликата е на регионалниот беџ).
    Badge.objects.filter(kind="PLACE").exclude(art="").update(art="")
