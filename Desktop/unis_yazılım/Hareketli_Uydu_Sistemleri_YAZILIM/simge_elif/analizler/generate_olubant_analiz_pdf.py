#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path


def _register_turkish_font():
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        font_path = "C:/Windows/Fonts/arial.ttf"
        if Path(font_path).exists():
            pdfmetrics.registerFont(TTFont("Arial", font_path))
            pdfmetrics.registerFont(TTFont("Arial-Bold", "C:/Windows/Fonts/arialbd.ttf"))
            pdfmetrics.registerFont(TTFont("Arial-Italic", "C:/Windows/Fonts/ariali.ttf"))
            pdfmetrics.registerFont(TTFont("Arial-BoldItalic", "C:/Windows/Fonts/arialbi.ttf"))
            return True
    except Exception:
        pass
    return False


def main() -> None:
    source = Path(__file__).with_name("Ölü_Bant_Analiz_Raporu.md")
    target = Path(__file__).with_name("Ölü_Bant_Analiz_Raporu.pdf")
    text = source.read_text(encoding="utf-8")
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib import colors
    except ImportError as exc:
        raise SystemExit("PDF icin `pip install reportlab`") from exc

    has_turkish = _register_turkish_font()
    doc = SimpleDocTemplate(str(target), pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()

    if has_turkish:
        fn = "Arial"
        for s in styles.byName.values():
            s.fontName = fn

    styles.add(ParagraphStyle("CodeBlock", fontName="Courier" if not has_turkish else "Arial", fontSize=7.5, leading=10, leftIndent=8, spaceBefore=6, spaceAfter=6, backColor=colors.Color(0.95, 0.95, 0.95)))

    story = []
    code_block = False
    code_lines = []
    table_lines = []
    in_table = False

    def flush_code():
        nonlocal code_lines
        if code_lines:
            story.append(Paragraph("<br/>".join(code_lines), styles["CodeBlock"]))
            code_lines = []

    def flush_table():
        nonlocal table_lines, in_table
        if not table_lines:
            return
        rows = []
        for line in table_lines:
            cells = [c.strip() for c in line.split("|")[1:-1]]
            rows.append(cells)
        if len(rows) >= 2:
            header = rows[0]
            body = rows[2:] if len(rows) > 2 and all("-" in c for c in rows[1]) else rows[1:]
            data = [header] + body
            n = len(header)
            if n > 0:
                w = doc.width / n
                tbl = Table(data, colWidths=[w] * n)
                tbl.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3a5c")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold" if not has_turkish else "Arial-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 8), ("FONTSIZE", (0, 1), (-1, -1), 7.5),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.Color(0.7, 0.7, 0.7)),
                    ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.Color(0.95, 0.97, 1.0)]),
                ]))
                story.append(Spacer(1, 6))
                story.append(tbl)
                story.append(Spacer(1, 8))
        table_lines = []
        in_table = False

    for line in text.splitlines():
        s = line.strip()
        if s.startswith("```"):
            if code_block:
                flush_code()
                code_block = False
            else:
                flush_code()
                code_block = True
            continue
        if code_block:
            code_lines.append(s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
            continue
        if "|" in s and s.startswith("|"):
            if not in_table:
                flush_table()
                in_table = True
            table_lines.append(s)
            continue
        else:
            if in_table:
                flush_table()
        if s.startswith("# ") and not s.startswith("## "):
            flush_code()
            story.append(Paragraph(s[2:], styles["Title"]))
            story.append(Spacer(1, 6))
        elif s.startswith("## ") and not s.startswith("### "):
            flush_code()
            story.append(Spacer(1, 8))
            story.append(Paragraph(s[3:], styles["Heading2"]))
        elif s.startswith("### "):
            flush_code()
            story.append(Spacer(1, 6))
            story.append(Paragraph(s[4:], styles["Heading3"]))
        elif s == "":
            story.append(Spacer(1, 4))
        else:
            flush_code()
            txt = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
            txt = txt.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            txt = re.sub(r"&lt;b&gt;(.+?)&lt;/b&gt;", r"<b>\1</b>", txt)
            story.append(Paragraph(txt, styles["BodyText"]))

    flush_code()
    flush_table()
    doc.build(story)
    print(f"PDF olusturuldu: {target}")


if __name__ == "__main__":
    main()
