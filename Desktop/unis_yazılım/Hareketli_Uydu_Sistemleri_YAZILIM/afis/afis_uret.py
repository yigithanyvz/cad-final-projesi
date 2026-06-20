#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent


def font_path(name: str) -> str:
    path = Path("C:/Windows/Fonts") / name
    if not path.exists():
        raise SystemExit(f"Font bulunamadi: {path}")
    return str(path)


def wrap(c, text: str, x: float, y: float, width: float, font: str, size: int, leading: int) -> float:
    from reportlab.pdfbase.pdfmetrics import stringWidth

    line = ""
    for word in text.split():
        candidate = f"{line} {word}".strip()
        if stringWidth(candidate, font, size) <= width:
            line = candidate
        else:
            c.drawString(x, y, line)
            y -= leading
            line = word
    if line:
        c.drawString(x, y, line)
        y -= leading
    return y


def card(c, x, y, w, h, title):
    from reportlab.lib import colors

    c.setFillColor(colors.Color(0.03, 0.08, 0.16, alpha=0.84))
    c.setStrokeColor(colors.Color(0.40, 0.91, 0.98, alpha=0.36))
    c.roundRect(x, y, w, h, 18, fill=1, stroke=1)
    c.setFont("ArialBold", 13)
    c.setFillColor(colors.HexColor("#67e8f9"))
    c.drawString(x + 18, y + h - 34, title)


def main() -> None:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A3
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas

    pdfmetrics.registerFont(TTFont("Arial", font_path("arial.ttf")))
    pdfmetrics.registerFont(TTFont("ArialBold", font_path("arialbd.ttf")))

    out = ROOT / "mergen_tanitim_afisi.pdf"
    logo = ROOT / "logo.png"
    c = canvas.Canvas(str(out), pagesize=A3)
    w, h = A3
    m = 42

    c.setFillColor(colors.HexColor("#061024"))
    c.rect(0, 0, w, h, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#0b2f66"))
    c.circle(w * 0.82, h * 0.80, 240, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#082f49"))
    c.circle(w * 0.10, h * 0.12, 260, fill=1, stroke=0)
    c.setStrokeColor(colors.Color(0.49, 0.83, 0.99, alpha=0.13))
    for x in range(0, int(w), 42):
        c.line(x, 0, x, h)
    for y in range(0, int(h), 42):
        c.line(0, y, w, y)

    c.setFillColor(colors.Color(0.02, 0.07, 0.14, alpha=0.82))
    c.setStrokeColor(colors.Color(0.40, 0.91, 0.98, alpha=0.34))
    c.roundRect(m, h - 130, w - 2 * m, 86, 22, fill=1, stroke=1)
    if logo.exists():
        c.drawImage(str(logo), m + 18, h - 114, width=54, height=54, preserveAspectRatio=True, mask="auto")
    c.setFillColor(colors.white)
    c.setFont("ArialBold", 24)
    c.drawString(m + 86, h - 78, "UniS")
    c.setFont("ArialBold", 12)
    c.setFillColor(colors.HexColor("#bfeaff"))
    c.drawString(m + 86, h - 98, "Hareketli Uydu Terminali")
    c.setFont("Arial", 10)
    c.setFillColor(colors.HexColor("#9fc4df"))
    c.drawString(m + 86, h - 114, "Üniversite ve Üzeri Kategorisi")

    for idx, (a, b) in enumerate([("ULUDAĞ", "ÜNİ."), ("YAZILIM", "TOPLULUĞU")]):
        cx = w - m - 132 + idx * 68
        cy = h - 86
        c.setFillColor(colors.HexColor("#082f49") if idx == 0 else colors.HexColor("#0f172a"))
        c.setStrokeColor(colors.HexColor("#67e8f9") if idx == 0 else colors.HexColor("#a7f3d0"))
        c.circle(cx, cy, 28, fill=1, stroke=1)
        c.setFillColor(colors.white)
        c.setFont("ArialBold", 7)
        c.drawCentredString(cx, cy + 3, a)
        c.setFont("Arial", 6)
        c.drawCentredString(cx, cy - 8, b)

    c.setFont("ArialBold", 15)
    c.setFillColor(colors.HexColor("#67e8f9"))
    c.drawString(m, h - 180, "ULUDAĞ YAZILIM TOPLULUĞU'NUN İLK TEKNOFEST TAKIMI")
    c.setFont("ArialBold", 66)
    c.setFillColor(colors.white)
    c.drawString(m, h - 250, "MERGEN")
    c.setFont("ArialBold", 19)
    c.setFillColor(colors.HexColor("#bfeaff"))
    c.drawString(m + 2, h - 282, "Hareket halindeyken hedefini kaybetmeyen uydu terminali vizyonu")
    c.setFillColor(colors.HexColor("#00e5ff"))
    c.roundRect(m + 2, h - 300, 360, 5, 2.5, fill=1, stroke=0)

    cx, cy = w / 2, h - 520
    c.setStrokeColor(colors.Color(0.40, 0.91, 0.98, alpha=0.48))
    c.setLineWidth(2)
    c.ellipse(cx - 220, cy - 70, cx + 220, cy + 70, fill=0, stroke=1)
    c.ellipse(cx - 170, cy - 48, cx + 170, cy + 48, fill=0, stroke=1)
    c.circle(cx, cy, 88, fill=0, stroke=1)
    c.setStrokeColor(colors.white)
    c.setLineWidth(10)
    c.arc(cx - 76, cy - 56, cx + 76, cy + 78, 205, 130)
    c.setStrokeColor(colors.HexColor("#67e8f9"))
    c.setLineWidth(4)
    c.line(cx, cy, cx + 116, cy + 72)
    c.setFillColor(colors.HexColor("#a7f3d0"))
    c.circle(cx + 116, cy + 72, 8, fill=1, stroke=0)
    c.setFont("Arial", 11)
    c.setFillColor(colors.HexColor("#9fc4df"))
    c.drawCentredString(cx, cy - 140, "stabil takip • mobil platform • güvenilir yönelim")

    card(c, m, h - 610, 195, 160, "AMACIMIZ")
    c.setFont("Arial", 12)
    c.setFillColor(colors.HexColor("#e7f7ff"))
    wrap(c, "Hareketli platformlarda anten yönelimini koruyabilen, güvenilir bir terminal konsepti geliştirmek.", m + 18, h - 500, 160, "Arial", 12, 17)

    card(c, w - m - 195, h - 610, 195, 160, "VİZYONUMUZ")
    wrap(c, "Kesintisiz haberleşme için saha koşullarına uygun, geliştirilebilir ve yerli teknoloji üretmek.", w - m - 177, h - 500, 160, "Arial", 12, 17)

    card(c, m, h - 820, 330, 165, "GÖREVİMİZ")
    c.setFont("Arial", 13)
    c.setFillColor(colors.HexColor("#e7f7ff"))
    wrap(c, "Mekanik, elektronik ve yazılım çalışmalarını ortak bir hedefte birleştirerek yarışma şartlarına uygun bir prototip altyapısı oluşturmak.", m + 18, h - 705, 290, "Arial", 13, 19)

    card(c, w - m - 330, h - 820, 330, 165, "NELER YAPIYORUZ?")
    c.setFont("Arial", 12)
    y = h - 705
    for item in ["Hareketli terminal konsepti", "Stabil takip yazılım altyapısı", "Simülasyon ve doğrulama", "Kullanıcı arayüzü hazırlığı", "KTR ve sunum dokümantasyonu"]:
        c.drawString(w - m - 312, y, f"• {item}")
        y -= 18

    card(c, m, h - 1055, w - 2 * m, 150, "TAKIM ÜYELERİ")
    c.setFont("Arial", 12)
    c.setFillColor(colors.HexColor("#e7f7ff"))
    c.drawString(m + 20, h - 960, "Mehmet Efe Ekici • Simge Yeter • Kerim Yıldırım • Elif Toygar")
    c.drawString(m + 20, h - 985, "Can Hakan Altınok • Kadir Mehmet Güleç")
    c.drawString(m + 20, h - 1010, "Mert Kayra Yılmaz • Yusuf Talha Vergili • Hidayet Sevim • Rabia Sıla Batum")

    c.setFillColor(colors.Color(0.02, 0.07, 0.14, alpha=0.80))
    c.roundRect(m, 34, w - 2 * m, 42, 14, fill=1, stroke=0)
    c.setFont("Arial", 11)
    c.setFillColor(colors.HexColor("#9fc4df"))
    c.drawString(m + 14, 50, "UniS • Proje: Mergen • Kategori: Hareketli Uydu Terminali")
    c.drawRightString(w - m - 14, 50, "Tanıtım Afişi")

    c.showPage()
    c.save()
    print(out)


if __name__ == "__main__":
    main()
