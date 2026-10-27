import importlib.util
from html import escape
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "frontend" / "public" / "logos"

spec = importlib.util.spec_from_file_location("demo_catalog", ROOT / "backend" / "businesses" / "demo_catalog.py")
catalog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(catalog)

ICONS = {
    "star": '<path d="M12 3l2.6 5.6 6.1.7-4.5 4.2 1.2 6L12 16.6 6.6 19.5l1.2-6L3.3 9.3l6.1-.7z"/>',
    "backpack": '<path d="M7 8a5 5 0 0 1 10 0v11a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2z"/><path d="M10 3h4M9 13h6v4H9z"/>',
    "tree": '<path d="M12 3l6 8h-3l4 6H5l4-6H6z"/><path d="M12 17v4"/>',
    "taxi": '<path d="M4 16v-3l2-5h12l2 5v3z"/><path d="M10 8V5h4v3M6 16v3M18 16v3"/><circle cx="8" cy="13" r=".6"/><circle cx="16" cy="13" r=".6"/>',
    "plane": '<path d="M2 14l20-7-4 13-5-4-3 4v-5l9-7-11 6z"/>',
    "bus": '<rect x="4" y="3" width="16" height="15" rx="3"/><path d="M4 11h16M8 18v3M16 18v3"/><circle cx="8" cy="14.5" r=".6"/><circle cx="16" cy="14.5" r=".6"/>',
    "bike": '<circle cx="6" cy="16" r="3.5"/><circle cx="18" cy="16" r="3.5"/><path d="M6 16l4-8h5l3 8M10 8l3 8M13 5h3"/>',
    "crown": '<path d="M3 8l4.5 4L12 5l4.5 7L21 8l-2 11H5z"/><path d="M5 19h14"/>',
    "castle": '<path d="M4 21V9h3v3h2V9h6v3h2V9h3v12z"/><path d="M10 21v-4a2 2 0 0 1 4 0v4M4 9V5h3v4M17 9V5h3v4"/>',
    "mountain": '<path d="M2 20L9 7l4 6 3-4 6 11z"/><path d="M7.5 10l1.5 1.5L10.5 10"/>',
    "fork": '<path d="M7 3v7a2 2 0 0 0 2 2v9M11 3v7a2 2 0 0 1-2 2M9 3v6"/><path d="M17 21V3c-2 2-3 5-3 8h3"/>',
    "flower": '<circle cx="12" cy="9" r="2.5"/><path d="M12 6.5c0-3 4-3 3 0M14.5 9c3 0 3 4 0 3M12 11.5c0 3-4 3-3 0M9.5 9c-3 0-3-4 0-3"/><path d="M12 12v9M12 17c-3 0-4-2-4-3 2 0 4 1 4 3"/>',
    "house": '<path d="M3 11l9-7 9 7"/><path d="M5 10v10h14V10M10 20v-6h4v6"/>',
    "road": '<path d="M8 3L4 21M16 3l4 18M12 4v3M12 10v3M12 16v3"/>',
    "wave": '<path d="M2 9c3-3 5 3 8 0s5 3 8 0 3 0 4 0M2 15c3-3 5 3 8 0s5 3 8 0 3 0 4 0"/>',
    "fish": '<path d="M3 12c4-6 11-6 15 0-4 6-11 6-15 0z"/><path d="M18 12l3-3v6zM8 11v.01"/>',
    "boat": '<path d="M3 15h18l-3 5H6z"/><path d="M12 3v12M12 4l6 8h-6"/>',
}

SKIP = {"хотел", "хостел", "вила", "апартмани", "ресторан", "такси", "кафеана", "скара", "гостинска", "куќа",
        "етно", "—", "-", "bike", "&", "sup", "градски", "линии", "превоз", "приградски"}


def initials(name):
    base = re.sub(r"\(демо\)", "", name).split("—")[0]
    words = [w for w in re.findall(r"[\wЀ-ӿ]+", base) if w.lower() not in SKIP and not w.isdigit()]
    if not words:
        words = base.split()
    letters = "".join(w[0] for w in words[:2]).upper()
    return letters or name[:2].upper()


def shape_path(shape):
    if shape == "circle":
        return '<circle cx="64" cy="64" r="60" fill="url(#g)"/>'
    if shape == "hexagon":
        return '<path d="M64 4l52 30v60l-52 30-52-30V34z" fill="url(#g)"/>'
    if shape == "shield":
        return '<path d="M64 4l54 16v34c0 36-24 60-54 70C34 114 10 90 10 54V20z" fill="url(#g)"/>'
    return '<rect x="4" y="4" width="120" height="120" rx="34" fill="url(#g)"/>'


def svg(name, spec):
    c1, c2 = spec["colors"]
    fg = spec["fg"]
    icon = ICONS[spec["icon"]]
    text = spec.get("mono") or initials(name)
    size = 22 if len(text) < 2 else 20
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" role="img" aria-label="{escape(name)}">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{c1}"/><stop offset="1" stop-color="{c2}"/></linearGradient></defs>
{shape_path(spec["shape"])}
<g transform="translate(40 24) scale(2)" fill="none" stroke="{fg}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{icon}</g>
<text x="64" y="{100 if spec["shape"] != "shield" else 96}" text-anchor="middle" font-family="Onest, Arial, sans-serif" font-size="{size}" font-weight="800" letter-spacing="2" fill="{fg}">{escape(text)}</text>
</svg>
'''


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    count = 0
    for b in catalog.BUSINESSES:
        (OUT / f"{b['slug']}.svg").write_text(svg(b["name"], b["logo"]), encoding="utf-8")
        count += 1
    for name, spec in catalog.EXISTING_LOGOS.items():
        (OUT / f"{spec['slug']}.svg").write_text(svg(name, spec), encoding="utf-8")
        count += 1
    print(f"{count} логоа во {OUT}")


if __name__ == "__main__":
    main()
