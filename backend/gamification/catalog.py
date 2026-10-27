ART = "/badges/{}.webp"

GROUPS = {
    "city": ("Град", "#0f4c5c"),
    "water": ("Езеро и вода", "#1b64a8"),
    "nature": ("Природа", "#1d7a4f"),
    "heritage": ("Наследство", "#a3462b"),
}

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

EXISTING_ART = {
    "explorer": "explorer",
    "macedonia-explorer": "macedonia-100",
    "city-ohrid-100": "ohrid-100",
    "city-skopje-100": "skopje-100",
    "city-bitola-100": "bitola-100",
}


STAMP_INK = {
    "RELIGIOUS": "#8a2f3c", "HISTORY": "#8a5a12", "MUSEUM": "#2f4f8a", "CULTURE": "#1f6a5a",
    "VIEWPOINT": "#2f6b34", "NATURE": "#2f6b34", "BEACH": "#1b64a8",
}
PLACE_STAMPS = {
    "ohrid/sv-naum": ("Св. Наум", "monastery", "RELIGIOUS"),
    "ohrid/kaneo": ("Св. Јован Канео", "kaneo", "RELIGIOUS"),
    "ohrid/samoilova-tvrdina": ("Самуилова тврдина", "fortress", "HISTORY"),
    "ohrid/plaoshnik": ("Плаошник", "domes", "RELIGIOUS"),
    "ohrid/anticki-teatar": ("Антички театар", "theatre", "HISTORY"),
    "ohrid/sv-sofija": ("Св. Софија", "basilica", "RELIGIOUS"),
    "ohrid/perivlepta": ("Перивлепта", "church", "RELIGIOUS"),
    "ohrid/robevi": ("Робевата куќа", "oldhouse", "MUSEUM"),
    "ohrid/zaliv-na-koskite": ("Залив на коските", "stilts", "MUSEUM"),
    "ohrid/carsija": ("Охридска чаршија", "bazaar", "CULTURE"),
    "ohrid/galicica-vidikovec": ("Галичица", "viewpoint", "VIEWPOINT"),
    "ohrid/lagadin": ("Плажа Лагадин", "beach", "BEACH"),
    "ohrid/kej": ("Охридски кеј", "quay", "NATURE"),
    "ohrid/izvori-crn-drim": ("Извори на Црн Дрим", "springs", "NATURE"),
    "skopje/kamen-most": ("Камен мост", "bridge", "HISTORY"),
    "skopje/stara-carsija": ("Скопска чаршија", "bazaar", "CULTURE"),
    "skopje/kale": ("Тврдина Кале", "fortress", "HISTORY"),
    "skopje/majka-tereza": ("Мајка Тереза", "memorial", "MUSEUM"),
    "skopje/sv-spas": ("Св. Спас", "church", "RELIGIOUS"),
    "skopje/milenium-krst": ("Милениумски крст", "cross", "VIEWPOINT"),
    "skopje/matka": ("Кањон Матка", "canyon", "NATURE"),
    "bitola/sirok-sokak": ("Широк сокак", "street", "CULTURE"),
    "bitola/heraklea": ("Хераклеја", "columns", "HISTORY"),
    "bitola/saat-kula": ("Саат кула", "clocktower", "HISTORY"),
    "bitola/pelister": ("Пелистер", "pines", "NATURE"),
}


GROUPS_EN = {"city": "City", "water": "Lakes & water", "nature": "Nature", "heritage": "Heritage"}
LOCATION_NAMES_EN = {
    1: "Skopje", 2: "Ohrid", 3: "Bitola", 4: "Struga", 5: "Kruševo", 6: "Prilep", 7: "Tetovo", 8: "Štip", 9: "Veles",
    10: "Gevgelija", 11: "Kičevo", 12: "Kavadarci", 13: "Strumica", 14: "Kočani", 15: "Demir Kapija", 16: "Globočica",
    17: "Lake Ohrid", 18: "Lake Prespa", 19: "Lake Mladost", 20: "Šar Mountain", 21: "Lake Mavrovo", 22: "Bregalnica",
    23: "Lake Dojran", 24: "Kalište", 25: "Matka Canyon", 26: "Vranski Springs", 27: "Šar Mountain Flora", 28: "Jakupica",
    29: "Saint Naum", 30: "Samuel's Fortress", 31: "Cave", 32: "Galičnik", 33: "Kratovo", 34: "Pirin Springs",
    35: "Crno Drvo", 36: "Pelister", 37: "Belčište Springs", 38: "Crna River", 39: "Debar Hajduk", 40: "St. Prohor Pčinjski",
}
ACHIEVEMENTS_EN = {
    "nature-explorer": ("Nature Explorer", "3 nature places or viewpoints"),
    "history-buff": ("History Buff", "3 historic places"),
    "culture-explorer": ("Culture Explorer", "3 museums, churches or cultural places"),
    "mountain-hiker": ("Mountain Hiker", "2 mountain viewpoints"),
    "lake-explorer": ("Lakeshore", "3 places along Lake Ohrid"),
    "photographer": ("Photographer", "10 approved photo check-ins"),
    "wine-traveler": ("Wine Traveller", "Tikveš wineries — coming soon"),
}


def badge_text_en():
    out = {}
    for num, _slug, name, group, _rule in LOCATIONS:
        out[name] = LOCATION_NAMES_EN[num]
        out[f"{GROUPS[group][0]} — колекција „Македонија“"] = f"{GROUPS_EN[group]} — “Macedonia” collection"
    for code, name, desc, *_ in ACHIEVEMENTS:
        out[name], out[desc] = ACHIEVEMENTS_EN[code]
    return out


def stamp_art(key):
    return "stamp-" + key.replace("/", "-")


def location_art(num, slug):
    return f"loc-{num:02d}-{slug}"


def art_for_code(code):
    name = EXISTING_ART.get(code)
    if not name and code.startswith("place-"):
        city, _, slug = code[len("place-"):].partition("-")
        if f"{city}/{slug}" in PLACE_STAMPS:
            name = stamp_art(f"{city}/{slug}")
    return ART.format(name) if name else ""


def sync_catalog(Badge):
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
    for key in PLACE_STAMPS:
        city, slug = key.split("/")
        Badge.objects.filter(code=f"place-{city}-{slug}").update(art=ART.format(stamp_art(key)))
