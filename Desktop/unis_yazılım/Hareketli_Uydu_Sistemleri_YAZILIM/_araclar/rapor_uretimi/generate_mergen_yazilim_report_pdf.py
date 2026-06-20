#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


def escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def find_windows_font(file_name: str) -> Path | None:
    font_path = Path("C:/Windows/Fonts") / file_name
    return font_path if font_path.exists() else None


def configure_turkish_fonts(styles) -> None:
    """ReportLab'in varsayilan fontlari Turkce karakterleri desteklemez.

    Bu nedenle Windows'taki Arial fontunu gomerek PDF'te `ı, İ, ş, Ş, ğ, Ğ`
    gibi karakterlerin siyah kutu olarak gorunmesini engelliyoruz.
    """
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    regular_font = find_windows_font("arial.ttf")
    bold_font = find_windows_font("arialbd.ttf")
    monospace_font = find_windows_font("consola.ttf") or regular_font

    if regular_font is None:
        raise SystemExit("Turkce PDF icin C:/Windows/Fonts/arial.ttf bulunamadi.")

    pdfmetrics.registerFont(TTFont("MergenArial", str(regular_font)))
    pdfmetrics.registerFont(TTFont("MergenArialBold", str(bold_font or regular_font)))
    pdfmetrics.registerFont(TTFont("MergenMono", str(monospace_font)))

    for style_name in ("Normal", "BodyText"):
        styles[style_name].fontName = "MergenArial"
    for style_name in ("Title", "Heading1", "Heading2", "Heading3"):
        styles[style_name].fontName = "MergenArialBold"
    styles["Code"].fontName = "MergenMono"
    styles["Code"].fontSize = 7


def main() -> None:
    source = Path(__file__).with_name("Mergen_Yazilim_Calismalari_Raporu.md")
    target = Path(__file__).with_name("Mergen_Yazilim_Calismalari_Raporu.pdf")
    text = source.read_text(encoding="utf-8")

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, Preformatted, SimpleDocTemplate, Spacer
    except ImportError as exc:
        raise SystemExit("PDF uretimi icin `python -m pip install reportlab` calistirin.") from exc

    doc = SimpleDocTemplate(str(target), pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    configure_turkish_fonts(styles)
    story = []
    in_code = False
    code_lines: list[str] = []

    def flush_code() -> None:
        nonlocal code_lines
        if code_lines:
            story.append(Preformatted("\n".join(code_lines), styles["Code"]))
            story.append(Spacer(1, 6))
            code_lines = []

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if line.startswith("```"):
            if in_code:
                flush_code()
                in_code = False
            else:
                in_code = True
            continue
        if in_code:
            code_lines.append(line)
            continue
        if line.startswith("# "):
            story.append(Paragraph(escape(line[2:]), styles["Title"]))
            story.append(Spacer(1, 8))
        elif line.startswith("## "):
            story.append(Spacer(1, 8))
            story.append(Paragraph(escape(line[3:]), styles["Heading2"]))
        elif line.startswith("### "):
            story.append(Spacer(1, 6))
            story.append(Paragraph(escape(line[4:]), styles["Heading3"]))
        elif line.startswith("| "):
            story.append(Paragraph(escape(line), styles["Code"]))
        elif line.strip():
            story.append(Paragraph(escape(line), styles["BodyText"]))
        else:
            story.append(Spacer(1, 5))

    flush_code()
    doc.build(story)
    print(target)


if __name__ == "__main__":
    main()
