"""PDF извоз на план за патување (reportlab, фонт Onest со кирилица).

Содржи: заглавие со лого, основни податоци, предупредувања, распоред по денови
(време, место, причина, движење, трошок, пристапност) и QR-код до планот во апликацијата
(ако е поставен FRONTEND_URL).
"""
import io
import os
from datetime import date
from pathlib import Path

from django.utils import timezone
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)
from xml.sax.saxutils import escape

from core.i18n import CITY_EN, tr

ASSETS = Path(__file__).resolve().parent.parent / "core" / "assets"
TEAL, GREEN, GOLD, INK, MUTED = (colors.HexColor(c) for c in ("#0d3640", "#1d9e6e", "#c99a2e", "#17282e", "#53666c"))
MIST, RULE, WARN_BG = colors.HexColor("#eaf4f1"), colors.HexColor("#d9e7e3"), colors.HexColor("#fdf8ea")

_fonts_ready = False


def _fonts():
    global _fonts_ready
    if not _fonts_ready:
        pdfmetrics.registerFont(TTFont("Onest", str(ASSETS / "Onest-Regular.ttf")))
        pdfmetrics.registerFont(TTFont("Onest-Bold", str(ASSETS / "Onest-Bold.ttf")))
        pdfmetrics.registerFontFamily("Onest", normal="Onest", bold="Onest-Bold")
        _fonts_ready = True


L = {
    "mk": {
        "app": "Travel Planner Македонија", "plan": "План за патување", "from": "Почеток", "days": "Денови",
        "guests": "Гости", "budget": "Буџет", "pace": "Темпо", "transport": "Превоз", "mobility": "Пристапност",
        "warnings": "Предупредувања", "day": "Ден", "time": "Време", "activity": "Активност", "details": "Детали",
        "travel": "{m} мин движење, {km} km", "cost": "Трошок", "unknown": "непознато", "generated": "Генерирано",
        "page": "Страна", "qr": "Отворете го планот во апликацијата", "no_plan": "Планот уште не е генериран.",
        "note": "Цените и работното време се прикажуваат само ако се проверени. Проверете пред посета.",
        "access": {"YES": "пристапно со количка", "LIMITED": "делумно пристапно", "NO": "непристапно",
                   "UNKNOWN": "пристапност непроверена"},
        "pace_v": {"relaxed": "бавно", "balanced": "умерено", "intense": "интензивно"},
        "transport_v": {"car": "автомобил", "walking": "пешки", "public": "јавен превоз/такси", "bicycle": "велосипед"},
        "mobility_v": {"standard": "без посебни потреби", "reduced": "намалена подвижност", "wheelchair": "инвалидска количка"},
        "months": ["јануари", "февруари", "март", "април", "мај", "јуни", "јули", "август", "септември", "октомври",
                   "ноември", "декември"],
        "weekdays": ["понеделник", "вторник", "среда", "четврток", "петок", "сабота", "недела"],
    },
    "en": {
        "app": "Travel Planner Macedonia", "plan": "Trip plan", "from": "Start", "days": "Days",
        "guests": "Guests", "budget": "Budget", "pace": "Pace", "transport": "Transport", "mobility": "Accessibility",
        "warnings": "Warnings", "day": "Day", "time": "Time", "activity": "Activity", "details": "Details",
        "travel": "{m} min travel, {km} km", "cost": "Cost", "unknown": "unknown", "generated": "Generated",
        "page": "Page", "qr": "Open the plan in the app", "no_plan": "The plan has not been generated yet.",
        "note": "Prices and opening hours are shown only when verified. Please check before visiting.",
        "access": {"YES": "wheelchair accessible", "LIMITED": "partly accessible", "NO": "not accessible",
                   "UNKNOWN": "accessibility not verified"},
        "pace_v": {"relaxed": "relaxed", "balanced": "balanced", "intense": "intense"},
        "transport_v": {"car": "car", "walking": "walking", "public": "public transport/taxi", "bicycle": "bicycle"},
        "mobility_v": {"standard": "no special needs", "reduced": "reduced mobility", "wheelchair": "wheelchair"},
        "months": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
                   "November", "December"],
        "weekdays": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
    },
}


def _date(d: date, t, weekday=False):
    s = f"{d.day} {t['months'][d.month - 1]} {d.year}"
    return f"{t['weekdays'][d.weekday()]}, {s}" if weekday else s


def _styles():
    base = dict(fontName="Onest", textColor=INK, leading=13, fontSize=9.5, alignment=TA_LEFT)
    return {
        "brand": ParagraphStyle("brand", **{**base, "fontName": "Onest-Bold", "fontSize": 11, "textColor": TEAL}),
        "title": ParagraphStyle("title", **{**base, "fontName": "Onest-Bold", "fontSize": 20, "leading": 24, "textColor": TEAL}),
        "kicker": ParagraphStyle("kicker", **{**base, "textColor": GREEN, "fontName": "Onest-Bold"}),
        "h2": ParagraphStyle("h2", **{**base, "fontName": "Onest-Bold", "fontSize": 13, "leading": 17, "textColor": TEAL,
                                      "spaceBefore": 8, "spaceAfter": 4, "keepWithNext": 1}),
        "body": ParagraphStyle("body", **base),
        "small": ParagraphStyle("small", **{**base, "fontSize": 8, "leading": 10.5, "textColor": MUTED, "keepWithNext": 0}),
        "cell_b": ParagraphStyle("cell_b", **{**base, "fontName": "Onest-Bold"}),
        "warn": ParagraphStyle("warn", **{**base, "fontSize": 8.5, "leading": 11.5, "textColor": colors.HexColor("#5e4300")}),
    }


def _qr(url, size=26 * mm):
    w = QrCodeWidget(url)
    x1, y1, x2, y2 = w.getBounds()
    d = Drawing(size, size, transform=[size / (x2 - x1), 0, 0, size / (y2 - y1), 0, 0])
    d.add(w)
    return d


def render_trip_pdf(trip, lang="mk"):
    _fonts()
    t = L["en" if lang == "en" else "mk"]
    S = _styles()
    buf = io.BytesIO()
    title = tr(trip.title, lang) or trip.city.name
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=16 * mm,
                            bottomMargin=18 * mm, title=title, author=t["app"], subject=t["plan"])
    generated = timezone.localtime().strftime("%d.%m.%Y %H:%M")

    def footer(canvas, doc_):
        canvas.saveState()
        canvas.setFont("Onest", 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(16 * mm, 10 * mm, f"{t['app']} · {t['generated']} {generated}")
        canvas.drawRightString(A4[0] - 16 * mm, 10 * mm, f"{t['page']} {doc_.page}")
        canvas.setStrokeColor(RULE)
        canvas.line(16 * mm, 13 * mm, A4[0] - 16 * mm, 13 * mm)
        canvas.restoreState()

    story = []
    logo = Image(str(ASSETS / "logo-mark.png"), width=14 * mm, height=14 * mm)
    head = Table([[logo, [Paragraph(t["app"], S["brand"]), Paragraph(t["plan"], S["small"])]]],
                 colWidths=[17 * mm, None])
    head.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    story += [head, Spacer(1, 6 * mm)]
    city = CITY_EN.get(trip.city.name, trip.city.name) if lang == "en" else trip.city.name
    story += [Paragraph(escape(city), S["kicker"]),
              Paragraph(escape(title), S["title"]), Spacer(1, 3 * mm)]

    budget = f"{trip.budget:.0f} €" if trip.budget is not None else t["unknown"]
    info = [
        [t["from"], _date(trip.start_date, t), t["days"], str(trip.days)],
        [t["guests"], str(trip.guests), t["budget"], budget],
        [t["pace"], t["pace_v"].get(trip.pace, trip.pace), t["transport"], t["transport_v"].get(trip.transport, trip.transport)],
        [t["mobility"], t["mobility_v"].get(trip.mobility, trip.mobility), "", ""],
    ]
    info_rows = [[Paragraph(escape(c), S["small"] if i % 2 == 0 else S["cell_b"]) for i, c in enumerate(r)] for r in info]
    info_tbl = Table(info_rows, colWidths=[24 * mm, 46 * mm, 22 * mm, None])
    info_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), MIST), ("SPAN", (1, 3), (-1, 3)),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    frontend = os.environ.get("FRONTEND_URL", "").rstrip("/")
    if frontend:
        qr = Table([[_qr(f"{frontend}/trips/{trip.pk}")], [Paragraph(t["qr"], S["small"])]], colWidths=[30 * mm])
        top = Table([[info_tbl, qr]], colWidths=[None, 32 * mm])
        top.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
        story.append(top)
    else:
        story.append(info_tbl)

    if trip.warnings:
        rows = [[Paragraph(t["warnings"], ParagraphStyle("wb", parent=S["warn"], fontName="Onest-Bold"))]]
        rows += [[Paragraph("• " + escape(tr(w, lang)), S["warn"])] for w in trip.warnings]
        wt = Table(rows, colWidths=[None])
        wt.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), WARN_BG), ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#ecdcb0")),
                                ("LEFTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 2),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
        story += [Spacer(1, 5 * mm), wt]

    days = list(trip.itinerary_days.all().prefetch_related("items__place"))
    if not days:
        story += [Spacer(1, 6 * mm), Paragraph(t["no_plan"], S["body"])]
    for day in days:
        rows = [[Paragraph(t["time"], S["small"]), Paragraph(t["activity"], S["small"]), Paragraph(t["details"], S["small"])]]
        meal_rows = []
        for it in day.items.all():
            when = f"{it.start_time:%H:%M}–{it.end_time:%H:%M}"
            details = []
            if it.reason:
                details.append(escape(tr(it.reason, lang)))
            if it.travel_minutes_from_prev:
                details.append(t["travel"].format(m=round(it.travel_minutes_from_prev), km=it.distance_km_from_prev))
            if it.source_type == "PLACE":
                details.append(f"{t['cost']}: {f'{it.est_cost:.2f} €' if it.est_cost is not None else t['unknown']}")
                if trip.mobility != "standard" and it.place:
                    details.append(f"{t['mobility']}: {t['access'].get(it.place.wheelchair, '')}")
            if it.warning:
                details.append(f"<font color='#855800'><b>!</b> {escape(tr(it.warning, lang))}</font>")
            rows.append([Paragraph(when, S["cell_b"]), Paragraph(escape(tr(it.title, lang)), S["cell_b"]),
                         Paragraph("<br/>".join(details), S["small"])])
            if it.source_type == "MEAL":
                meal_rows.append(len(rows) - 1)
        tbl = Table(rows, colWidths=[27 * mm, 50 * mm, None], repeatRows=1)
        style = [
            ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ]
        style += [("BACKGROUND", (0, r), (-1, r), colors.HexColor("#f4faf7")) for r in meal_rows]
        tbl.setStyle(TableStyle(style))
        heading = Paragraph(f"{t['day']} {day.day_number} · {_date(day.date, t, weekday=True)}", S["h2"])
        notes = Paragraph(escape(tr(day.notes, lang)), S["small"]) if day.notes else Spacer(1, 1)
        # Насловот и белешката остануваат со првите редови од табелата; табелата се дели меѓу страни.
        story += [Spacer(1, 4 * mm), KeepTogether([heading, notes, Spacer(1, 2 * mm)]), tbl]

    story += [Spacer(1, 6 * mm), Paragraph(t["note"], S["small"])]
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buf.getvalue()
