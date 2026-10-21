"""UI/UX слики од сите екрани за лаптоп, таблет и телефон, плус мокапи со рамки на уреди.

Потребно (еднаш):
    pip install playwright pillow
    python -m playwright install chromium

Пуштање (backend на :8000 и frontend на :5173 треба да работат, со seed_demo податоци):
    python tools/screenshots.py
    python tools/screenshots.py --out ui-sliki --sample-weather

Опции:
    --sample-weather  прикажи пример-прогноза ако нема OPENWEATHER_API_KEY
    --blank-tiles     празни плочки за карта (кога нема интернет)
Резултат: <out>/laptop, <out>/tablet, <out>/phone, <out>/mockups, <out>/pregled-*.png
"""
import argparse
import asyncio
import datetime as dt
import io
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from playwright.async_api import async_playwright

DEVICES = {
    "laptop": {"viewport": {"width": 1440, "height": 900}, "scale": 1, "mobile": False},
    "tablet": {"viewport": {"width": 834, "height": 1194}, "scale": 2, "mobile": True},
    "phone": {"viewport": {"width": 390, "height": 844}, "scale": 3, "mobile": True},
}
USERS = {"turist": "Turist12345!", "host": "Host12345!", "admin": "Admin12345!"}


def sample_weather():
    today = dt.date.today()
    icons = ["01d", "02d", "10d", "03d", "01d", "02d"]
    return {
        "location": "Охрид",
        "current": {"temp": 19, "feels_like": 18, "humidity": 58, "wind": 9, "icon": "02d", "description": "малку облачно"},
        "daily": [{"date": str(today + dt.timedelta(days=i)), "min": 9 + i % 3, "max": 19 + (i * 2) % 5, "icon": icons[i],
                   "description": "пример", "pop": [10, 20, 70, 30, 0, 10][i], "wind": 10} for i in range(6)],
        "source": "OpenWeather (пример-податоци)", "fetched_at": "",
    }


def weather_icon_png(code):
    """Едноставна икона (сонце/облак/дожд) кога OpenWeather иконите не се достапни."""
    im = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if code.startswith(("01", "02")):
        d.ellipse([22, 18, 66, 62], fill=(255, 205, 80, 255))
    if not code.startswith("01"):
        d.ellipse([28, 42, 62, 72], fill=(240, 244, 247, 255))
        d.ellipse([48, 32, 86, 70], fill=(240, 244, 247, 255))
        d.rounded_rectangle([24, 56, 86, 78], 11, fill=(240, 244, 247, 255))
    if code.startswith(("09", "10")):
        for x in (38, 54, 70):
            d.line([(x, 84), (x - 4, 94)], fill=(140, 200, 255, 255), width=4)
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


def blank_tile():
    im = Image.new("RGB", (256, 256), (228, 236, 233))
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


async def discover(page, base):
    """ID-а на огласи од API, за скриптата да не зависи од фиксни броеви."""
    async def get(path):
        r = await page.request.get(f"{base}/api/v1{path}")
        data = await r.json()
        return data["results"] if isinstance(data, dict) and "results" in data else data
    places = await get("/places/?city=ohrid")
    kaneo = next((p for p in places if p["slug"] == "kaneo"), places[0])
    acc = (await get("/accommodations/"))[0]
    tour = (await get("/boat-tours/"))[0]
    biz = await get("/businesses/")
    taxi = next(b for b in biz if b["type"] == "TAXI")
    rest = next(b for b in biz if b["type"] == "RESTAURANT")
    return {"place": kaneo["id"], "acc": acc["id"], "tour": tour["id"], "taxi": taxi["id"], "rest": rest["id"],
            "boatbiz": tour["business"]["id"]}


def pages(ids):
    """(датотека, наслов, патека, корисник, акција)"""
    return [
        ("01-pocetna", "Почетна", "/", None, None),
        ("02-mesta", "Места и карта", "/places?city=ohrid", None, None),
        ("03-mesto-detali", "Место: детали, прогноза, фото-посета", f"/places/{ids['place']}", "turist", None),
        ("04-smestuvanje", "Пребарување сместување", "/stay", None, None),
        ("05-smestuvanje-oglas", "Оглас за сместување", f"/stay/{ids['acc']}", "turist", None),
        ("06-brodski-turi", "Бродски тури", "/boat-tours", None, None),
        ("07-brodska-tura", "Бродска тура: рута, постојки, поаѓања", f"/boat-tours/{ids['tour']}", "turist", None),
        ("08-restorani-taksi", "Ресторани и такси", "/services", None, None),
        ("09-taksi", "Такси: тарифи и контакт", f"/taxi/{ids['taxi']}", None, None),
        ("10-restoran", "Ресторан: мени и работно време", f"/restaurants/{ids['rest']}", None, None),
        ("11-najava", "Најава", "/login", None, None),
        ("12-registracija", "Регистрација", "/register", None, None),
        ("13-novo-patuvanje", "Ново патување", "/trips/new?city=1", "turist", None),
        ("14-plan", "AI план по денови", "/trips", "turist", "open-first-trip"),
        ("15-patuvanja", "Мои патувања", "/trips", "turist", None),
        ("16-rezervacii", "Мои резервации", "/reservations", "turist", None),
        ("17-pasos", "Мој профил и пасош со печати", "/me", "turist", None),
        ("18-javen-profil", "Јавен профил", "/u/turist", None, None),
        ("19-biznis-tabla", "Бизнис-табла", "/business", "host", "all-reservations"),
        ("20-biznis-uredi", "Уредување на бродска тура", f"/business/{ids['boatbiz']}/edit", "host", None),
        ("21-nov-biznis", "Нов бизнис", "/business/new", "host", None),
        ("22-admin", "Администрација", "/admin", "admin", None),
        ("23-admin-katalog", "Админ: уредување место", "/admin", "admin", "edit-place"),
        ("24-meni-mobilen", "Мобилно мени", "/", "turist", "open-menu"),
        ("25-izvori", "Извори на фотографии", "/credits", None, None),
    ]


async def settle(page, ms=900):
    """Почекај мрежата да се смири (со горна граница — HMR/надворешни ресурси може да не завршат)."""
    try:
        await page.wait_for_load_state("networkidle", timeout=6000)
    except Exception:
        pass
    await page.wait_for_timeout(ms)


async def login(page, base, user):
    r = await page.request.post(f"{base}/api/v1/auth/login/", data={"username": user, "password": USERS[user]})
    tokens = await r.json()
    await page.goto(base + "/login")
    await page.evaluate("t => { localStorage.setItem('tpm_access', t.access); localStorage.setItem('tpm_refresh', t.refresh); }", tokens)


async def capture(args):
    out = Path(args.out)
    weather = json.dumps(sample_weather())
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        probe = await browser.new_page()
        ids = await discover(probe, args.base)
        await probe.close()
        for dev, cfg in DEVICES.items():
            (out / dev).mkdir(parents=True, exist_ok=True)
            sessions = {}
            for name, title, path, user, action in pages(ids):
                if action == "open-menu" and dev == "laptop":
                    continue
                if args.only and name not in args.only.split(","):
                    continue
                key = user or "_anon"
                if key not in sessions:
                    ctx = await browser.new_context(viewport=cfg["viewport"], device_scale_factor=cfg["scale"],
                                                    is_mobile=cfg["mobile"], has_touch=cfg["mobile"], locale="mk-MK")
                    if args.sample_weather:
                        await ctx.route("**/api/v1/weather/**", lambda r: r.fulfill(status=200, content_type="application/json", body=weather))
                        await ctx.route("**/openweathermap.org/img/**", lambda r: r.fulfill(
                            status=200, content_type="image/png", body=weather_icon_png(r.request.url.split("/")[-1][:3])))
                    if args.blank_tiles:
                        tile = blank_tile()
                        await ctx.route("**/tile.openstreetmap.org/**", lambda r: r.fulfill(status=200, content_type="image/png", body=tile))
                    pg = await ctx.new_page()
                    if user:
                        await login(pg, args.base, user)
                    sessions[key] = pg
                pg = sessions[key]
                await pg.goto(args.base + path)
                await settle(pg)
                if action == "open-first-trip":
                    await pg.locator("a.card-link", has_text="Охрид").first.click()
                    await settle(pg, 1200)
                elif action == "all-reservations":
                    await pg.select_option("select[aria-label='Филтер по статус']", "")
                    await pg.wait_for_timeout(800)
                elif action == "edit-place":
                    await pg.locator(".admin-place-row .btn").first.click()
                    await pg.wait_for_timeout(400)
                    await pg.locator(".admin-places .subcard").first.scroll_into_view_if_needed()
                elif action == "open-menu":
                    if dev == "tablet" or dev == "phone":
                        await pg.click("button.menu-btn")
                        await pg.wait_for_timeout(400)
                await pg.screenshot(path=str(out / dev / f"{name}.png"), full_page=False)
                if name in ("01-pocetna", "07-brodska-tura", "14-plan"):
                    await pg.screenshot(path=str(out / dev / f"{name}-cela.png"), full_page=True)
                print(f"{dev:7} {name}")
            for pg in sessions.values():
                await pg.context.close()
        await browser.close()
    return [(n, t) for n, t, *_ in pages(ids)]


# ------------------------- Мокапи со рамки -------------------------

BG = (226, 240, 236)
DARK = (22, 30, 34)
INK = (13, 54, 64)


def font(size, bold=False):
    for name in (("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"), "arial.ttf", "Arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def shadow(canvas, box, radius, blur=28, offset=16, alpha=70):
    sh = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    x0, y0, x1, y1 = box
    ImageDraw.Draw(sh).rounded_rectangle([x0, y0 + offset, x1, y1 + offset], radius, fill=(10, 40, 48, alpha))
    canvas.alpha_composite(sh.filter(ImageFilter.GaussianBlur(blur)))


def rounded(img, radius):
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, img.size[0] - 1, img.size[1] - 1], radius, fill=255)
    out = img.convert("RGBA")
    out.putalpha(mask)
    return out


def laptop_frame(shot, width):
    s = shot.resize((width, round(shot.height * width / shot.width)), Image.LANCZOS)
    bez = max(10, width // 60)
    W, H = width + bez * 2, s.height + bez * 2 + bez
    img = Image.new("RGBA", (W + width // 8, H + width // 24), (0, 0, 0, 0))
    ox = width // 16
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([ox, 0, ox + W, H], bez * 2, fill=DARK)
    d.ellipse([ox + W // 2 - 4, bez // 2 - 2, ox + W // 2 + 4, bez // 2 + 6], fill=(60, 70, 74))
    img.alpha_composite(s.convert("RGBA"), (ox + bez, bez + bez // 2))
    base_y = H
    d.polygon([(0, base_y), (img.width, base_y), (img.width - width // 30, base_y + width // 26), (width // 30, base_y + width // 26)],
              fill=(200, 206, 208))
    d.rectangle([img.width // 2 - width // 12, base_y, img.width // 2 + width // 12, base_y + width // 120], fill=(170, 178, 180))
    return img


def tablet_frame(shot, width):
    bez = max(14, width // 22)
    inner = width - bez * 2
    s = shot.resize((inner, round(shot.height * inner / shot.width)), Image.LANCZOS)
    img = Image.new("RGBA", (width, s.height + bez * 2), (0, 0, 0, 0))
    ImageDraw.Draw(img).rounded_rectangle([0, 0, img.width - 1, img.height - 1], bez * 2, fill=DARK)
    img.alpha_composite(rounded(s, bez // 2), (bez, bez))
    return img


def phone_frame(shot, width):
    """Рамка на телефон со статусна лента над екранот, за „островот“ да не покрива содржина."""
    bez = max(8, width // 26)
    inner = width - bez * 2
    s = shot.convert("RGB").resize((inner, round(shot.height * inner / shot.width)), Image.LANCZOS)
    bar_h = round(inner * 0.12)
    bar_col = s.getpixel((4, 4))
    screen = Image.new("RGB", (inner, s.height + bar_h), bar_col)
    screen.paste(s, (0, bar_h))
    light = sum(bar_col) < 380
    d = ImageDraw.Draw(screen)
    txt = (255, 255, 255) if light else (20, 30, 34)
    d.text((round(inner * 0.09), round(bar_h * 0.32)), "9:41", font=font(max(10, round(inner * 0.045)), True), fill=txt)
    bx = inner - round(inner * 0.16)
    d.rounded_rectangle([bx, round(bar_h * 0.38), bx + round(inner * 0.08), round(bar_h * 0.62)], 3, outline=txt, width=2)
    d.rectangle([bx + 3, round(bar_h * 0.38) + 3, bx + round(inner * 0.06), round(bar_h * 0.62) - 3], fill=txt)
    img = Image.new("RGBA", (width, screen.height + bez * 2), (0, 0, 0, 0))
    dd = ImageDraw.Draw(img)
    dd.rounded_rectangle([0, 0, img.width - 1, img.height - 1], bez * 5, fill=DARK)
    img.alpha_composite(rounded(screen, bez * 4), (bez, bez))
    iw = round(inner * 0.3)
    dd.rounded_rectangle([width // 2 - iw // 2, bez + round(bar_h * 0.22), width // 2 + iw // 2, bez + round(bar_h * 0.72)],
                         bar_h, fill=DARK)
    return img


def mockup(out, name, title):
    shots = {dev: out / dev / f"{name}.png" for dev in DEVICES}
    have = {k: Image.open(v) for k, v in shots.items() if v.exists()}
    if not have:
        return None
    W, H = 2400, 1280
    canvas = Image.new("RGBA", (W, H), BG + (255,))
    d = ImageDraw.Draw(canvas)
    d.text((90, 70), title, font=font(54, True), fill=INK)
    d.text((92, 140), "Travel Planner МК: лаптоп, таблет и телефон", font=font(28), fill=(80, 100, 105))
    bottom = H - 80
    # Лаптоп лево, таблет во средина, телефон десно, со мало преклопување.
    if "laptop" in have:
        fr = laptop_frame(have["laptop"], 1240)
        x, y = 60, bottom - fr.height
        shadow(canvas, (x, y, x + fr.width, y + fr.height), 30)
        canvas.alpha_composite(fr, (x, y))
    if "tablet" in have:
        fr = tablet_frame(have["tablet"], 600)
        scale = min(1, (bottom - 250) / fr.height)
        fr = fr.resize((round(fr.width * scale), round(fr.height * scale)), Image.LANCZOS)
        x, y = 1330, bottom - fr.height
        shadow(canvas, (x, y, x + fr.width, y + fr.height), 36)
        canvas.alpha_composite(fr, (x, y))
    if "phone" in have:
        fr = phone_frame(have["phone"], 330)
        scale = min(1, (bottom - 300) / fr.height)
        fr = fr.resize((round(fr.width * scale), round(fr.height * scale)), Image.LANCZOS)
        x, y = W - fr.width - 60, bottom - fr.height
        shadow(canvas, (x, y, x + fr.width, y + fr.height), 40)
        canvas.alpha_composite(fr, (x, y))
    path = out / "mockups" / f"{name}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(path, quality=92)
    return path


def contact_sheet(out, dev, items, cols):
    files = [(out / dev / f"{n}.png", t) for n, t in items if (out / dev / f"{n}.png").exists()]
    if not files:
        return
    thumb_w = {"laptop": 560, "tablet": 360, "phone": 230}[dev]
    first = Image.open(files[0][0])
    thumb_h = round(first.height * thumb_w / first.width)
    pad, label = 36, 80
    rows = math.ceil(len(files) / cols)
    W = cols * thumb_w + (cols + 1) * pad
    H = 150 + rows * (thumb_h + label + pad)
    sheet = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(sheet)
    d.text((pad, 50), {"laptop": "Лаптоп (1440 × 900)", "tablet": "Таблет (834 × 1194)", "phone": "Телефон (390 × 844)"}[dev],
           font=font(44, True), fill=INK)
    for i, (f, t) in enumerate(files):
        im = Image.open(f).convert("RGB").resize((thumb_w, thumb_h), Image.LANCZOS)
        x = pad + (i % cols) * (thumb_w + pad)
        y = 150 + (i // cols) * (thumb_h + label + pad)
        sheet.paste(rounded(im, 14), (x, y), rounded(im, 14))
        f20 = font(20)
        words, lines, cur = f"{i + 1}. {t}".split(), [], ""
        for w in words:  # прелами го насловот во ширината на сликата
            test = f"{cur} {w}".strip()
            if d.textlength(test, font=f20) <= thumb_w:
                cur = test
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
        for j, line in enumerate(lines[:2]):
            d.text((x, y + thumb_h + 10 + j * 26), line, font=f20, fill=(40, 60, 66))
    sheet.save(out / f"pregled-{dev}.png", quality=90)


def build_mockups(out, items):
    for n, t in items:
        mockup(out, n, t)
    contact_sheet(out, "laptop", items, 4)
    contact_sheet(out, "tablet", items, 6)
    contact_sheet(out, "phone", items, 8)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:5173")
    ap.add_argument("--out", default="ui-sliki")
    ap.add_argument("--sample-weather", action="store_true")
    ap.add_argument("--blank-tiles", action="store_true")
    ap.add_argument("--mockups-only", action="store_true")
    ap.add_argument("--only", default="", help="само одредени екрани, пр. 01-pocetna,14-plan")
    args = ap.parse_args()
    out = Path(args.out)
    if args.mockups_only:
        items = [(n, t) for n, t, *_ in pages({"place": 0, "acc": 0, "tour": 0, "taxi": 0, "rest": 0, "boatbiz": 0})]
    else:
        items = asyncio.run(capture(args))
    build_mockups(out, items)
    print(f"Готово: {out.resolve()}")


if __name__ == "__main__":
    main()
