#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import re


def main() -> None:
    source = Path(__file__).with_name("Mergen_Detayli_Rapor.md")
    target = Path(__file__).with_name("Mergen_Detayli_Rapor.pdf")
    text = source.read_text(encoding="utf-8")

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_LEFT, TA_CENTER
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
            PageBreak, KeepTogether,
        )
        from reportlab.lib import colors
        from reportlab.lib.units import mm
    except ImportError as exc:
        raise SystemExit("PDF uretimi icin `pip install reportlab` calistirin.") from exc

    doc = SimpleDocTemplate(
        str(target), pagesize=A4,
        rightMargin=36, leftMargin=36,
        topMargin=36, bottomMargin=36,
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        "CodeBlock", fontName="Courier", fontSize=7.5, leading=10,
        leftIndent=8, spaceBefore=6, spaceAfter=6,
        backColor=colors.Color(0.95, 0.95, 0.95),
    ))
    # Use existing "Code" style if available, but we use "CodeBlock"
    styles.add(ParagraphStyle(
        "TableCell", parent=styles["Normal"],
        fontSize=7.5, leading=10,
    ))
    styles.add(ParagraphStyle(
        "TableCellHeader", parent=styles["Normal"],
        fontSize=8, leading=11,
        fontName="Helvetica-Bold",
        textColor=colors.white,
    ))
    styles.add(ParagraphStyle(
        "MyHeading3", parent=styles["Heading2"],
        fontSize=12, leading=16,
        spaceBefore=10, spaceAfter=4,
        textColor=colors.Color(0.2, 0.3, 0.5),
    ))
    styles.add(ParagraphStyle(
        "MyHeading4", parent=styles["Heading2"],
        fontSize=10, leading=14,
        spaceBefore=8, spaceAfter=3,
    ))

    story = []
    code_block = False
    code_lines = []
    table_lines = []
    in_table = False

    def flush_code():
        nonlocal code_lines
        if code_lines:
            text = "<br/>".join(code_lines)
            story.append(Paragraph(text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"), styles["CodeBlock"]))
            code_lines = []

    def flush_table():
        nonlocal table_lines, in_table
        if table_lines:
            rows = []
            for line in table_lines:
                cells = [c.strip() for c in line.split("|")[1:-1]]
                rows.append(cells)
            if len(rows) >= 2:
                header = rows[0]
                body = rows[2:] if len(rows) > 2 and rows[1][0] and all("-" in c for c in rows[1]) else rows[1:]
                data = [header] + body
                col_count = len(header)
                table = Table(data, colWidths=[doc.width / col_count] * col_count)
                style_cmds = [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3a5c")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 8),
                    ("FONTSIZE", (0, 1), (-1, -1), 7.5),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.Color(0.7, 0.7, 0.7)),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.Color(0.95, 0.97, 1.0)]),
                ]
                table.setStyle(TableStyle(style_cmds))
                story.append(Spacer(1, 6))
                story.append(table)
                story.append(Spacer(1, 8))
            table_lines = []
            in_table = False

    for line in text.splitlines():
        stripped = line.strip()

        # Code block management
        if stripped.startswith("```"):
            if code_block:
                flush_code()
                code_block = False
            else:
                flush_code()
                code_block = True
            continue

        if code_block:
            code_lines.append(stripped.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
            continue

        # Table detection
        if "|" in stripped and stripped.startswith("|"):
            if not in_table:
                flush_table()
                in_table = True
            table_lines.append(stripped)
            continue
        else:
            if in_table:
                flush_table()

        # Headings
        if stripped.startswith("# ") and not stripped.startswith("## "):
            flush_code()
            story.append(Paragraph(stripped[2:], styles["Title"]))
            story.append(Spacer(1, 6))
        elif stripped.startswith("## ") and not stripped.startswith("### "):
            flush_code()
            story.append(Spacer(1, 10))
            story.append(Paragraph(stripped[3:], styles["Heading2"]))
        elif stripped.startswith("### ") and not stripped.startswith("#### "):
            flush_code()
            story.append(Spacer(1, 8))
            story.append(Paragraph(stripped[4:], styles["MyHeading3"]))
        elif stripped.startswith("#### "):
            flush_code()
            story.append(Spacer(1, 6))
            story.append(Paragraph(stripped[5:], styles["MyHeading4"]))
        elif stripped == "---":
            story.append(Spacer(1, 4))
            story.append(Paragraph("─" * 80, styles["Normal"]))
            story.append(Spacer(1, 4))
        elif stripped == "":
            story.append(Spacer(1, 4))
        else:
            flush_code()
            # Bold handling
            text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", stripped)
            text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            text = re.sub(r"&lt;b&gt;(.+?)&lt;/b&gt;", r"<b>\1</b>", text)
            story.append(Paragraph(text, styles["BodyText"]))

    flush_code()
    flush_table()

    doc.build(story)
    print(f"PDF olusturuldu: {target}")


if __name__ == "__main__":
    main()
