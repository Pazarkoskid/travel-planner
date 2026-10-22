"""Почетни податоци за пристапност (инвалидска количка) за демо местата.

ВАЖНО: ова се ПРОЦЕНКИ за прототипот (терен, скали, калдрма), означени како такви во
белешката. Пред продукција ги проверува администраторот (Админ → Каталог) или се увезуваат
од OpenStreetMap (ознака wheelchair=*). Се користат во seed_demo и во миграцијата 0005, која
менува само места со „непознато“ (не пребришува рачни измени).
"""
NOTE = "Проценка за прототипот — потребна е проверка на терен."

ACCESSIBILITY = {
    # "град/место": (wheelchair, белешка)
    "ohrid/sv-naum": ("LIMITED", "Рамни патеки до манастирот; калдрма и скали кај влезот во црквата."),
    "ohrid/kaneo": ("NO", "Стрмна патека и скали над езерото; нема пристап без скали."),
    "ohrid/samoilova-tvrdina": ("LIMITED", "Стрмен успон низ стариот град; со возило до влезот, внатре нерамен терен."),
    "ohrid/plaoshnik": ("LIMITED", "Успон по калдрма; околу црквата делумно рамни патеки."),
    "ohrid/anticki-teatar": ("LIMITED", "Камени скали; горниот дел се гледа од улицата."),
    "ohrid/sv-sofija": ("LIMITED", "Неколку скали кај влезот."),
    "ohrid/perivlepta": ("NO", "Стрмни улички и скали во горниот дел на стариот град."),
    "ohrid/robevi": ("NO", "Повеќекатна стара куќа со дрвени скали, без лифт."),
    "ohrid/zaliv-na-koskite": ("LIMITED", "Дрвена платформа; реконструираните куќи имаат скали."),
    "ohrid/carsija": ("LIMITED", "Рамна пешачка зона, но калдрма на делови."),
    "ohrid/galicica-vidikovec": ("LIMITED", "До видиковецот со автомобил; патеките понатаму се планински."),
    "ohrid/lagadin": ("LIMITED", "Песочна плажа; пристап до кејот без скали."),
    "ohrid/kej": ("YES", "Рамно шеталиште покрај езерото."),
    "ohrid/izvori-crn-drim": ("LIMITED", "Патеки и дрвени мостчиња; делови со чакал."),
    "skopje/kamen-most": ("YES", "Рамен пешачки мост, пристап од плоштадот без скали."),
    "skopje/stara-carsija": ("LIMITED", "Калдрма и мали наклони."),
    "skopje/kale": ("LIMITED", "Успон до влезот; внатре нерамен терен."),
    "skopje/majka-tereza": ("YES", "Модерен објект во центарот, рамен пристап."),
    "skopje/sv-spas": ("NO", "Црквата е вкопана; влезот е преку скали надолу."),
    "skopje/milenium-krst": ("LIMITED", "Со жичница до врвот; околу крстот поплочено, наклони."),
    "skopje/matka": ("LIMITED", "Првиот дел од патеката покрај кањонот е поплочен; чамците не се пристапни."),
    "bitola/sirok-sokak": ("YES", "Рамна пешачка улица."),
    "bitola/heraklea": ("LIMITED", "Чакал и нерамен терен меѓу остатоците."),
    "bitola/saat-kula": ("YES", "Рамен плоштад; кулата однатре не е отворена."),
    "bitola/pelister": ("LIMITED", "Неколку поплочени делови кај центарот за посетители; патеките се планински."),
}


def apply(Place, only_unknown=True):
    for key, (wheelchair, note) in ACCESSIBILITY.items():
        city, slug = key.split("/")
        qs = Place.objects.filter(city__slug=city, slug=slug)
        if only_unknown:
            qs = qs.filter(wheelchair="UNKNOWN")
        qs.update(wheelchair=wheelchair, accessibility_notes=f"{note} {NOTE}")


# Англиски верзии (за англискиот интерфејс и PDF); клуч = македонската белешка.
NOTE_EN = "Prototype estimate — needs on-site verification."
NOTES_EN = {
    "Рамни патеки до манастирот; калдрма и скали кај влезот во црквата.": "Level paths to the monastery; cobbles and steps at the church entrance.",
    "Стрмна патека и скали над езерото; нема пристап без скали.": "Steep path and steps above the lake; no step-free access.",
    "Стрмен успон низ стариот град; со возило до влезот, внатре нерамен терен.": "Steep climb through the old town; vehicle access to the gate, uneven ground inside.",
    "Успон по калдрма; околу црквата делумно рамни патеки.": "Cobbled climb; partly level paths around the church.",
    "Камени скали; горниот дел се гледа од улицата.": "Stone steps; the upper part can be seen from the street.",
    "Неколку скали кај влезот.": "A few steps at the entrance.",
    "Стрмни улички и скали во горниот дел на стариот град.": "Steep alleys and steps in the upper old town.",
    "Повеќекатна стара куќа со дрвени скали, без лифт.": "Multi-storey old house with wooden stairs, no lift.",
    "Дрвена платформа; реконструираните куќи имаат скали.": "Wooden platform; the reconstructed houses have steps.",
    "Рамна пешачка зона, но калдрма на делови.": "Level pedestrian zone, cobbled in parts.",
    "До видиковецот со автомобил; патеките понатаму се планински.": "Car access to the viewpoint; trails beyond are mountain paths.",
    "Песочна плажа; пристап до кејот без скали.": "Sandy beach; step-free access to the promenade.",
    "Рамно шеталиште покрај езерото.": "Level lakeside promenade.",
    "Патеки и дрвени мостчиња; делови со чакал.": "Paths and wooden footbridges; gravel in parts.",
    "Рамен пешачки мост, пристап од плоштадот без скали.": "Level pedestrian bridge, step-free from the square.",
    "Калдрма и мали наклони.": "Cobblestones and gentle slopes.",
    "Успон до влезот; внатре нерамен терен.": "Climb to the entrance; uneven ground inside.",
    "Модерен објект во центарот, рамен пристап.": "Modern building in the centre, level access.",
    "Црквата е вкопана; влезот е преку скали надолу.": "The church is sunken; entry is down a flight of steps.",
    "Со жичница до врвот; околу крстот поплочено, наклони.": "Cable car to the top; paved around the cross, with slopes.",
    "Првиот дел од патеката покрај кањонот е поплочен; чамците не се пристапни.": "The first part of the canyon path is paved; the boats are not accessible.",
    "Рамна пешачка улица.": "Level pedestrian street.",
    "Чакал и нерамен терен меѓу остатоците.": "Gravel and uneven ground among the ruins.",
    "Рамен плоштад; кулата однатре не е отворена.": "Level square; the tower interior is not open.",
    "Неколку поплочени делови кај центарот за посетители; патеките се планински.": "Some paved sections near the visitor centre; trails are mountain paths.",
}
