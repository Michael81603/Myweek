from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


TYPE_LABELS = {
    "activity": "Activite",
    "habit": "Habitude",
    "task": "Tache",
}

TYPE_COLORS = {
    "activity": colors.HexColor("#c7d2fe"),
    "habit": colors.HexColor("#ddd6fe"),
    "task": colors.HexColor("#bfdbfe"),
    "done": colors.HexColor("#bbf7d0"),
    "mixed": colors.HexColor("#fef3c7"),
    "empty": colors.white,
}

DAY_LABELS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]


def text(value):
    return str(value or "")


def time_label_from_minutes(minutes):
    hour = minutes // 60
    minute = minutes % 60
    return f"{hour:02d}:{minute:02d}"


def absolute_minutes(entry):
    sort_time = entry["sort_time"]
    if sort_time is None:
        return None
    return sort_time.hour * 60 + sort_time.minute


def entry_duration(entry):
    return entry["duration_minutes"]


def slot_key(entry):
    start = absolute_minutes(entry)
    if start is None:
        return ("unscheduled", "Sans heure")
    end = start + entry_duration(entry)
    return (start, f"{time_label_from_minutes(start)} - {time_label_from_minutes(end)}")


def entry_title(entry):
    if entry["kind"] == "activity":
        return entry["activity"].title
    if entry["kind"] == "habit":
        return entry["habit"].title
    return entry["task"].title


def entry_subtitle(entry):
    if entry["kind"] == "activity":
        return entry["activity"].subtitle
    if entry["kind"] == "habit":
        return "Faite" if entry["done"] else entry["habit"].get_frequency_display()
    task = entry["task"]
    return f"{task.get_status_display()} - {task.get_priority_display()}"


def entry_cell_text(entry):
    title = entry_title(entry)
    subtitle = entry_subtitle(entry)
    label = TYPE_LABELS[entry["kind"]]
    parts = [f"<b>{title}</b>", subtitle, f"<font size='6'>{label}</font>"]
    return "<br/>".join(part for part in parts if part)


def cell_background(entries):
    if not entries:
        return TYPE_COLORS["empty"]
    if len(entries) > 1:
        return TYPE_COLORS["mixed"]
    entry = entries[0]
    if entry["kind"] == "habit" and entry["done"]:
        return TYPE_COLORS["done"]
    if entry["kind"] == "task" and entry["task"].is_done:
        return TYPE_COLORS["done"]
    return TYPE_COLORS[entry["kind"]]


def paragraph(value, style):
    return Paragraph(text(value).replace("\n", "<br/>"), style)


def pdf_columns(columns):
    visible_columns = [column for column in columns if column["day"]["index"] < 5]
    weekend_columns = [
        column
        for column in columns
        if column["day"]["index"] >= 5 and (column["timed_entries"] or column["unscheduled_entries"])
    ]
    return visible_columns + weekend_columns


def timetable_rows(schedule_context, body_style, time_style):
    columns = pdf_columns(schedule_context["columns"])
    slots = {}

    for column in columns:
        for entry in column["timed_entries"] + column["unscheduled_entries"]:
            key, label = slot_key(entry)
            slots.setdefault(key, {"label": label, "days": {}})
            slots[key]["days"].setdefault(column["day"]["index"], []).append(entry)

    sorted_slots = sorted(
        slots.items(),
        key=lambda item: (
            item[0] == "unscheduled",
            item[0] if isinstance(item[0], int) else 999999,
        ),
    )
    rows = [[paragraph("Horaires", time_style)] + [paragraph(DAY_LABELS[column["day"]["index"]], time_style) for column in columns]]

    if not sorted_slots:
        rows.append([paragraph("Libre", time_style)] + [paragraph("", body_style) for _ in columns])
        return rows, [[None for _ in columns]], columns

    backgrounds = []
    for _, slot in sorted_slots:
        row = [paragraph(slot["label"], time_style)]
        row_backgrounds = []
        for column in columns:
            entries = slot["days"].get(column["day"]["index"], [])
            row_backgrounds.append(cell_background(entries))
            if entries:
                row.append(paragraph("<br/><br/>".join(entry_cell_text(entry) for entry in entries), body_style))
            else:
                row.append(paragraph("", body_style))
        rows.append(row)
        backgrounds.append(row_backgrounds)

    return rows, backgrounds, columns


def build_schedule_pdf(schedule_context, user):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=0.7 * cm,
        leftMargin=0.7 * cm,
        topMargin=0.8 * cm,
        bottomMargin=0.8 * cm,
        pageCompression=0,
        title="MyWeek - Emploi du temps",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TimetableTitle",
        parent=styles["Title"],
        textColor=colors.HexColor("#111827"),
        fontSize=16,
        leading=20,
        alignment=TA_CENTER,
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "TimetableSubtitle",
        parent=styles["Normal"],
        textColor=colors.HexColor("#111827"),
        fontSize=11,
        leading=14,
        alignment=TA_CENTER,
        spaceAfter=10,
    )
    header_style = ParagraphStyle(
        "TimetableHeader",
        parent=styles["Normal"],
        textColor=colors.HexColor("#111827"),
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=11,
        alignment=TA_CENTER,
    )
    body_style = ParagraphStyle(
        "TimetableBody",
        parent=styles["Normal"],
        textColor=colors.HexColor("#111827"),
        fontSize=8,
        leading=10,
        alignment=TA_CENTER,
    )

    rows, backgrounds, columns = timetable_rows(schedule_context, body_style, header_style)
    day_count = len(columns)
    available_width = landscape(A4)[0] - (1.4 * cm)
    time_col_width = 2.6 * cm
    day_col_width = (available_width - time_col_width) / day_count
    col_widths = [time_col_width] + [day_col_width for _ in range(day_count)]

    table = Table(rows, colWidths=col_widths, repeatRows=1)
    table_style = [
        ("GRID", (0, 0), (-1, -1), 0.8, colors.HexColor("#374151")),
        ("BOX", (0, 0), (-1, -1), 1.1, colors.HexColor("#111827")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]

    for row_index, row_backgrounds in enumerate(backgrounds, start=1):
        table_style.append(("BACKGROUND", (0, row_index), (0, row_index), colors.HexColor("#f8fafc")))
        for day_index, background in enumerate(row_backgrounds, start=1):
            table_style.append(("BACKGROUND", (day_index, row_index), (day_index, row_index), background))

    table.setStyle(TableStyle(table_style))

    story = [
        Paragraph("MYWEEK", title_style),
        Paragraph(
            f"Emploi du temps - a partir du {schedule_context['week_start']:%d/%m/%Y}",
            subtitle_style,
        ),
        Spacer(1, 4),
        table,
        Spacer(1, 8),
        Paragraph(f"Utilisateur : {user.username}", ParagraphStyle("Footer", parent=styles["Normal"], fontSize=7, textColor=colors.HexColor("#64748b"))),
    ]

    doc.build(story)
    buffer.seek(0)
    return buffer
