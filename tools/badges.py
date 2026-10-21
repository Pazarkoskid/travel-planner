"""Генерира слики за беџовите (frontend/public/badges/*.webp).

Локации: пејзажот се зема од оригиналните 256px PNG (кругот е поместен по редови од листот),
а рамката, бројот и натписот се цртаат наново, униформно.
Достигнувања: целосно векторски (SVG), во иста визуелна линија.

    pip install playwright pillow
    python -m playwright install chromium
    python tools/badges.py --src <папка со locations/> [--png-out ui-badges]
"""
import argparse
import base64
import importlib.util
import io
import math
import pathlib

from PIL import Image, ImageFilter
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("catalog", ROOT / "backend/gamification/catalog.py")
catalog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(catalog)

FONT_DIR = ROOT / "frontend/node_modules/@fontsource/onest/files"
OUT = ROOT / "frontend/public/badges"
GOLD, GOLD_LIGHT, INK = "#d6a73a", "#f0cf73", "#17282e"


def row_top(num):
    """Горниот раб на кругот во оригиналната слика (поместување по редови од листот)."""
    return 2 if num <= 9 else 10 if num <= 16 else 23 if num <= 24 else 34 if num <= 32 else 41


def scene_data_uri(path, num):
    im = Image.open(path).convert("RGB")
    cy, r = row_top(num) + 112, 97
    box = (128 - r, cy - r, 128 + r, min(256, cy + r))
    crop = im.crop(box)
    if crop.height < 2 * r:  # долу недостасува: дополни со последниот ред
        full = Image.new("RGB", (2 * r, 2 * r))
        full.paste(crop, (0, 0))
        last = crop.crop((0, crop.height - 1, crop.width, crop.height)).resize((2 * r, 2 * r - crop.height))
        full.paste(last, (0, crop.height))
        crop = full
    crop = crop.resize((440, 440), Image.LANCZOS).filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=2))
    buf = io.BytesIO()
    crop.save(buf, format="JPEG", quality=92)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def _font_uri(sub, w):
    data = (FONT_DIR / f"onest-{sub}-{w}-normal.woff2").read_bytes()
    return "data:font/woff2;base64," + base64.b64encode(data).decode()


# Фонтовите се вградени (data URI) — set_content страницата не смее да чита file:// фонтови.
FONT_CSS = "".join(
    f"@font-face{{font-family:Onest;font-weight:{w};src:url('{_font_uri(s, w)}') format('woff2')}}"
    for w in (700, 800) for s in ("latin", "cyrillic"))

FIT_JS = """
for (const t of document.querySelectorAll('text[data-max]')) {
  const max = +t.dataset.max; let fs = +t.getAttribute('font-size');
  while (t.getComputedTextLength() > max && fs > 14) { fs -= 1; t.setAttribute('font-size', fs); }
}
"""

PIN = "M0-13c-6.4 0-11 4.8-11 10.7C-11 5.6 0 16 0 16S11 5.6 11-2.3C11-8.2 6.4-13 0-13zm0 15a4.3 4.3 0 1 1 0-8.6A4.3 4.3 0 0 1 0 2z"


def split_name(name, limit=12):
    words = name.upper().split()
    if len(name) <= limit or len(words) == 1:
        return [name.upper()]
    best = min(range(1, len(words)), key=lambda i: abs(len(" ".join(words[:i])) - len(" ".join(words[i:]))))
    return [" ".join(words[:best]), " ".join(words[best:])]


def location_svg(num, name, color, scene):
    lines = split_name(name)
    if len(lines) == 1:
        text = f'<text x="256" y="414" font-size="40" data-max="300" text-anchor="middle">{lines[0]}</text>'
    else:
        text = (f'<text x="256" y="400" font-size="32" data-max="320" text-anchor="middle">{lines[0]}</text>'
                f'<text x="256" y="436" font-size="32" data-max="250" text-anchor="middle">{lines[1]}</text>')
    return f"""
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">
  <defs>
    <clipPath id="c"><circle cx="256" cy="256" r="214"/></clipPath>
    <radialGradient id="ring" cx="50%" cy="35%" r="65%"><stop offset="0" stop-color="{color}" stop-opacity=".82"/><stop offset="1" stop-color="{color}"/></radialGradient>
    <linearGradient id="shade" x1="0" y1="0" x2="0" y2="1"><stop offset=".45" stop-color="#000" stop-opacity="0"/><stop offset=".72" stop-color="#000" stop-opacity=".28"/></linearGradient>
    <linearGradient id="gold" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{GOLD_LIGHT}"/><stop offset=".5" stop-color="{GOLD}"/><stop offset="1" stop-color="#a87d1e"/></linearGradient>
  </defs>
  <circle cx="256" cy="256" r="250" fill="url(#ring)"/>
  <circle cx="256" cy="256" r="244" fill="none" stroke="#fff" stroke-opacity=".22" stroke-width="2"/>
  <g clip-path="url(#c)">
    <image href="{scene}" x="36" y="36" width="440" height="440" preserveAspectRatio="xMidYMid slice"/>
    <rect x="36" y="36" width="440" height="440" fill="url(#shade)"/>
    <path d="M42 352H470V476H42z" fill="{color}" fill-opacity=".97"/>
    <path d="M42 352H470" stroke="url(#gold)" stroke-width="4"/>
  </g>
  <circle cx="256" cy="256" r="216" fill="none" stroke="url(#gold)" stroke-width="7"/>
  <g transform="translate(256 352)">
    <circle r="23" fill="url(#gold)" stroke="#fff" stroke-width="3"/>
    <path d="{PIN}" transform="scale(.95)" fill="{color}"/>
  </g>
  <g font-family="Onest" font-weight="800" fill="#fff" letter-spacing="1.5">{text}</g>
  <g transform="translate(256 30)">
    <rect x="-40" y="-17" width="80" height="34" rx="17" fill="url(#gold)" stroke="#fff" stroke-width="3"/>
    <text y="7.5" font-family="Onest" font-weight="800" font-size="20" fill="{INK}" text-anchor="middle">№ {num:02d}</text>
  </g>
</svg>"""


ICONS = {
    "leaf": '<path d="M18 84C14 44 44 14 88 12c4 42-24 74-70 72z" fill="#fff"/><path d="M24 78C40 58 56 42 76 26" stroke="{c}" stroke-width="5" stroke-linecap="round" fill="none"/>',
    "column": '<path d="M14 28 50 10l36 18z" fill="#fff"/><rect x="16" y="30" width="68" height="8" rx="2" fill="#fff"/><g fill="#fff"><rect x="22" y="40" width="10" height="38"/><rect x="45" y="40" width="10" height="38"/><rect x="68" y="40" width="10" height="38"/></g><rect x="12" y="80" width="76" height="9" rx="2" fill="#fff"/>',
    "amphora": '<path d="M38 10h24v6h-4v8c12 6 20 18 20 32 0 18-12 30-28 34-16-4-28-16-28-34 0-14 8-26 20-32v-8h-4z" fill="#fff"/><path d="M28 40c-10-2-14 6-10 14M72 40c10-2 14 6 10 14" stroke="#fff" stroke-width="5" fill="none" stroke-linecap="round"/><path d="M26 56h48" stroke="{c}" stroke-width="4"/>',
    "mountain": '<path d="M4 86 36 30l14 22 14-28 32 62z" fill="#fff"/><path d="M36 30l-8 14 6-2 4 5 4-7zM64 24l-7 14 5-2 4 5 5-6z" fill="{c}"/>',
    "waves": '<g fill="none" stroke="#fff" stroke-width="8" stroke-linecap="round"><path d="M8 34c10 0 10-8 21-8s10 8 21 8 10-8 21-8 10 8 21 8"/><path d="M8 56c10 0 10-8 21-8s10 8 21 8 10-8 21-8 10 8 21 8"/><path d="M8 78c10 0 10-8 21-8s10 8 21 8 10-8 21-8 10 8 21 8"/></g>',
    "camera": '<path d="M36 18h28l6 10h14a8 8 0 0 1 8 8v42a8 8 0 0 1-8 8H16a8 8 0 0 1-8-8V36a8 8 0 0 1 8-8h14z" fill="#fff"/><circle cx="50" cy="56" r="19" fill="{c}"/><circle cx="50" cy="56" r="12" fill="#fff"/><circle cx="78" cy="40" r="4" fill="{c}"/>',
    "wine": '<path d="M28 8h44c2 26-6 42-22 44C34 50 26 34 28 8z" fill="#fff"/><path d="M30 26h40" stroke="{c}" stroke-width="4"/><rect x="47" y="50" width="6" height="30" fill="#fff"/><rect x="30" y="80" width="40" height="8" rx="4" fill="#fff"/>',
    "compass": '<circle cx="50" cy="50" r="40" fill="none" stroke="#fff" stroke-width="7"/><path d="M50 16 60 50 50 84 40 50z" fill="#fff"/><path d="M50 16 60 50H40z" fill="{gold}"/><circle cx="50" cy="50" r="5" fill="{c}"/>',
    "sun": "".join(
        f'<path d="M50 50 {50 + 46 * math.cos(math.radians(a - 9)):.1f} {50 + 46 * math.sin(math.radians(a - 9)):.1f} '
        f'{50 + 46 * math.cos(math.radians(a + 9)):.1f} {50 + 46 * math.sin(math.radians(a + 9)):.1f}z" fill="{{gold}}"/>'
        for a in range(0, 360, 45)) + '<circle cx="50" cy="50" r="17" fill="{gold}" stroke="{c}" stroke-width="4"/>',
    "kaneo": '<path d="M2 92V74h20l6-6h44l8 8 14 16z" fill="#fff"/><path d="M26 66V50l24-12 24 12v16z" fill="#fff"/><path d="M42 40V26h16v14zM40 27l10-14 10 14z" fill="#fff"/><rect x="47" y="52" width="6" height="12" fill="{c}"/>',
    "bridge": '<path d="M2 40h96v14c-8 0-12 6-14 20H70c-2-12-8-18-14-18s-12 6-14 18H28c-2-14-6-20-14-20H2z" fill="#fff"/><g fill="#fff"><rect x="10" y="28" width="6" height="12"/><rect x="47" y="28" width="6" height="12"/><rect x="84" y="28" width="6" height="12"/></g><path d="M2 86c12 0 12-6 24-6s12 6 24 6 12-6 24-6 12 6 24 6" stroke="#fff" stroke-width="5" fill="none"/>',
    "clocktower": '<path d="M38 30h24v62H38z" fill="#fff"/><path d="M34 30 50 4l16 26z" fill="#fff"/><circle cx="50" cy="44" r="8" fill="{c}"/><path d="M50 39v5l3 3" stroke="#fff" stroke-width="2" fill="none"/><rect x="44" y="62" width="12" height="18" rx="6" fill="{c}"/><rect x="28" y="88" width="44" height="6" fill="#fff"/>',
}


def laurel(side):
    """Ловорова гранка од дното нагоре, по лак со радиус 186."""
    out = []
    start, end, n = 100, 205, 8
    pts = [math.radians(start + (end - start) * i / (n - 1)) for i in range(n)]
    stem = " ".join(f"{256 + side * 186 * math.cos(a):.1f},{256 + 186 * math.sin(a):.1f}" for a in pts)
    out.append(f'<polyline points="{stem}" fill="none" stroke="url(#gold)" stroke-width="4" stroke-linecap="round"/>')
    for i, a in enumerate(pts[1:], 1):
        x, y = 256 + side * 186 * math.cos(a), 256 + 186 * math.sin(a)
        tangent = math.degrees(math.atan2(186 * math.cos(a), -side * 186 * math.sin(a)))
        size = 1 - i * 0.045
        for k in (-1, 1):
            ang = tangent + k * 38
            ox, oy = 14 * math.cos(math.radians(ang)) * size, 14 * math.sin(math.radians(ang)) * size
            out.append(f'<ellipse cx="{x + ox:.1f}" cy="{y + oy:.1f}" rx="{7.5 * size:.1f}" ry="{17 * size:.1f}" '
                       f'transform="rotate({ang + 90:.1f} {x + ox:.1f} {y + oy:.1f})"/>')
    return "".join(out)


def achievement_svg(title, icon, color, big=None):
    ic = ICONS[icon].replace("{c}", color).replace("{gold}", GOLD)
    tall = False
    if big:  # „Град 100%“: име на градот + 100% во лентата
        head = f'<text x="256" y="290" font-size="46" data-max="300" text-anchor="middle" fill="#fff">{title.upper()}</text>'
        ribbon_text = '<text x="256" y="375" font-size="38" text-anchor="middle" fill="#17282e">100%</text>'
        icon_g = f'<g transform="translate(196 118) scale(1.2)">{ic}</g>'
    else:
        head = ""
        lines = split_name(title, 14)
        if len(lines) == 1:
            ribbon_text = f'<text x="256" y="371" font-size="28" data-max="292" text-anchor="middle" fill="#17282e">{lines[0]}</text>'
        else:
            tall = True
            ribbon_text = (f'<text x="256" y="356" font-size="24" data-max="280" text-anchor="middle" fill="#17282e">{lines[0]}</text>'
                           f'<text x="256" y="384" font-size="24" data-max="280" text-anchor="middle" fill="#17282e">{lines[1]}</text>')
        icon_g = f'<g transform="translate(171 112) scale(1.7)">{ic}</g>'
    ribbon = ('<path d="M62 326h388l-24 34 24 34H62l24-34z" fill="url(#gold)" stroke="#fff" stroke-width="3"/>' if tall else
              '<path d="M70 334h372l-22 26 22 26H70l22-26z" fill="url(#gold)" stroke="#fff" stroke-width="3"/>')
    return f"""
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">
  <defs>
    <radialGradient id="bg" cx="50%" cy="38%" r="62%"><stop offset="0" stop-color="{color}" stop-opacity=".78"/><stop offset=".7" stop-color="{color}"/><stop offset="1" stop-color="{color}"/></radialGradient>
    <linearGradient id="gold" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{GOLD_LIGHT}"/><stop offset=".5" stop-color="{GOLD}"/><stop offset="1" stop-color="#a87d1e"/></linearGradient>
  </defs>
  <circle cx="256" cy="256" r="250" fill="url(#bg)"/>
  <circle cx="256" cy="256" r="230" fill="none" stroke="url(#gold)" stroke-width="8"/>
  <circle cx="256" cy="256" r="212" fill="none" stroke="#fff" stroke-opacity=".35" stroke-width="2" stroke-dasharray="3 9"/>
  <g fill="url(#gold)">{laurel(-1)}{laurel(1)}</g>
  {icon_g}
  <g font-family="Onest" font-weight="800" letter-spacing="1">{head}</g>
  {ribbon}
  <g font-family="Onest" font-weight="800" letter-spacing="1">{ribbon_text}</g>
  <g transform="translate(256 448)" fill="url(#gold)"><path d="M0-14 4-4 14-4 6 2 9 12 0 6-9 12-6 2-14-4-4-4z"/></g>
</svg>"""


def render(page, svg):
    page.set_content(f"<html><head><style>{FONT_CSS}body{{margin:0;background:transparent}}</style></head><body>{svg}</body></html>")
    page.evaluate("document.fonts.ready")
    page.wait_for_timeout(60)
    page.evaluate(FIT_JS)
    return Image.open(io.BytesIO(page.screenshot(omit_background=True, clip={"x": 0, "y": 0, "width": 512, "height": 512})))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="папка со locations/*.png")
    ap.add_argument("--png-out", default=None, help="и PNG 512px во оваа папка")
    args = ap.parse_args()
    src = pathlib.Path(args.src)
    OUT.mkdir(parents=True, exist_ok=True)
    png_out = pathlib.Path(args.png_out) if args.png_out else None
    if png_out:
        png_out.mkdir(parents=True, exist_ok=True)

    jobs = []
    for num, slug, name, group, _rule in catalog.LOCATIONS:
        f = src / "locations" / f"{num:02d}_{slug}.png"
        jobs.append((catalog.location_art(num, slug), location_svg(num, name, catalog.GROUPS[group][1], scene_data_uri(f, num))))
    for code, name, _desc, icon, color, _rule in catalog.ACHIEVEMENTS:
        jobs.append((code, achievement_svg(name, icon, color)))
    jobs += [
        ("explorer", achievement_svg("Истражувач", "compass", "#0f4c5c")),
        ("macedonia-100", achievement_svg("Македонија", "sun", "#9c2a22", big=True)),
        ("ohrid-100", achievement_svg("Охрид", "kaneo", "#0f4c5c", big=True)),
        ("skopje-100", achievement_svg("Скопје", "bridge", "#1d7a4f", big=True)),
        ("bitola-100", achievement_svg("Битола", "clocktower", "#a3462b", big=True)),
    ]
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 512, "height": 512})
        for name, svg in jobs:
            im = render(page, svg)
            im.resize((384, 384), Image.LANCZOS).save(OUT / f"{name}.webp", "WEBP", quality=86, method=6)
            if png_out:
                im.save(png_out / f"{name}.png", optimize=True)
        browser.close()
    print(f"Готово: {len(jobs)} беџови → {OUT}")


if __name__ == "__main__":
    main()
