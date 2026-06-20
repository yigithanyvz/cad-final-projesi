#!/usr/bin/env python3
"""
UniS Projesi - Kapsamli Sunum PDF Uretici
Slide tabanli, detayli aciklamali, profesyonel format
"""

from __future__ import annotations
from pathlib import Path
from datetime import datetime

try:
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm, cm
    from reportlab.lib.colors import (
        HexColor, black, white, grey, yellow
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer,
        Table, TableStyle, PageBreak, HRFlowable,
        KeepTogether, Frame, PageTemplate, BaseDocTemplate
    )
    from reportlab.platypus.flowables import Flowable
except ImportError as exc:
    raise SystemExit("pip install reportlab") from exc


OUTPUT = Path(__file__).with_name("UniS_Sunum.pdf")
NOW = datetime.now().strftime("%d.%m.%Y")

PAGE_W, PAGE_H = landscape(A4)
MARGIN = 25 * mm
CONTENT_W = PAGE_W - 2 * MARGIN

# ── Renkler ──
C_DARK = HexColor("#0d47a1")
C_PRIMARY = HexColor("#1565c0")
C_LIGHT = HexColor("#42a5f5")
C_ACCENT = HexColor("#ff6f00")
C_BG = HexColor("#e3f2fd")
C_DARK_BG = HexColor("#0a1929")
C_GREEN = HexColor("#2e7d32")
C_RED = HexColor("#c62828")
C_GREY = HexColor("#546e7a")
C_WHITE = white
C_BLACK = black
C_TABLE_ALT = HexColor("#e8eaf6")
C_TABLE_HEADER = HexColor("#0d47a1")
C_CODE_BG = HexColor("#f5f5f5")

# ── Styles ──
styles = getSampleStyleSheet()

def make_style(name, **kw):
    s = ParagraphStyle(name, **kw)
    styles.add(s)
    return s

make_style("SlideTitle", fontName="Helvetica-Bold", fontSize=26,
           textColor=C_DARK, leading=32, spaceAfter=8)
make_style("SlideSub", fontName="Helvetica", fontSize=14,
           textColor=C_GREY, leading=18, spaceAfter=16)
make_style("SectionTitle", fontName="Helvetica-Bold", fontSize=30,
           textColor=C_WHITE, leading=36, alignment=TA_CENTER)
make_style("SectionSub", fontName="Helvetica", fontSize=16,
           textColor=HexColor("#bbdefb"), alignment=TA_CENTER, leading=20)
make_style("BodySlide", fontName="Helvetica", fontSize=12,
           textColor=C_BLACK, alignment=TA_LEFT, leading=16, spaceAfter=6)
make_style("BulletSlide", fontName="Helvetica", fontSize=12,
           textColor=C_BLACK, alignment=TA_LEFT, leading=16,
           leftIndent=20, bulletIndent=8, spaceAfter=4)
make_style("CodeSlide", fontName="Courier", fontSize=10,
           textColor=C_BLACK, alignment=TA_LEFT, leading=13,
           leftIndent=16, spaceAfter=3, spaceBefore=2,
           backColor=C_CODE_BG)
make_style("SmallNote", fontName="Helvetica-Oblique", fontSize=10,
           textColor=C_PRIMARY, alignment=TA_LEFT, leading=13,
           leftIndent=12, spaceAfter=4)
make_style("Tiny", fontName="Helvetica", fontSize=8,
           textColor=C_GREY, alignment=TA_CENTER, leading=10)
make_style("Highlight", fontName="Helvetica-Bold", fontSize=13,
           textColor=C_ACCENT, alignment=TA_LEFT, leading=17, spaceAfter=6)
make_style("BulletSmall", fontName="Helvetica", fontSize=11,
           textColor=C_BLACK, alignment=TA_LEFT, leading=14,
           leftIndent=16, bulletIndent=6, spaceAfter=3)
make_style("TCH", fontName="Helvetica-Bold", fontSize=10,
           textColor=C_WHITE, alignment=TA_CENTER, leading=13)
make_style("TC", fontName="Helvetica", fontSize=10,
           textColor=C_BLACK, alignment=TA_LEFT, leading=13)


# ── Yardimcilar ──

def new_slide(title, subtitle=None, story=None):
    if story is None:
        story = []
    story.append(Paragraph(title, styles["SlideTitle"]))
    if subtitle:
        story.append(Paragraph(subtitle, styles["SlideSub"]))
    story.append(Spacer(1, 4))
    return story

def bullet(text, story):
    story.append(Paragraph(text, styles["BulletSlide"]))
    return story

def bullet_small(text, story):
    story.append(Paragraph(text, styles["BulletSmall"]))
    return story

def body(text, story):
    story.append(Paragraph(text, styles["BodySlide"]))
    return story

def code(text, story):
    story.append(Paragraph(text.replace("\n", "<br/>"), styles["CodeSlide"]))
    return story

def note(text, story):
    story.append(Paragraph(text, styles["SmallNote"]))
    return story

def highlight(text, story):
    story.append(Paragraph(text, styles["Highlight"]))
    return story

def spacer(h=6, story=None):
    if story is None:
        story = []
    story.append(Spacer(1, h))
    return story

def tbl(headers, rows, col_widths=None):
    data = [[Paragraph(h, styles["TCH"]) for h in headers]]
    for row in rows:
        data.append([Paragraph(str(c), styles["TC"]) for c in row])
    t = Table(data, colWidths=col_widths, repeatRows=1)
    cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), C_TABLE_HEADER),
        ("TEXTCOLOR", (0, 0), (-1, 0), C_WHITE),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#90caf9")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            cmds.append(("BACKGROUND", (0, i), (-1, i), C_TABLE_ALT))
    t.setStyle(TableStyle(cmds))
    return t

def section_slide(title, subtitle, number, story):
    story.append(Spacer(1, 80))
    story.append(Paragraph(f"BOLUM {number}", ParagraphStyle(
        "SecNum", fontName="Helvetica-Bold", fontSize=14,
        textColor=HexColor("#90caf9"), alignment=TA_CENTER, leading=18)))
    story.append(Spacer(1, 12))
    story.append(HRFlowable(width="40%", thickness=2,
                             color=HexColor("#90caf9"), spaceBefore=6, spaceAfter=12))
    story.append(Paragraph(title, styles["SectionTitle"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph(subtitle, styles["SectionSub"]))
    story.append(PageBreak())
    return story


# ═══════════════════════════════════════════════════════════════
#  SUNUM ICERIGI
# ═══════════════════════════════════════════════════════════════

def build():
    story = []

    # ════════════════════════════════════════════
    # SLIDE 1 — KAPAK
    # ════════════════════════════════════════════
    story.append(Spacer(1, 50))
    story.append(HRFlowable(width="60%", thickness=3,
                             color=C_DARK, spaceBefore=6, spaceAfter=20))
    story.append(Paragraph("UNIS", ParagraphStyle(
        "BigTitle", fontName="Helvetica-Bold", fontSize=42,
        textColor=C_DARK, alignment=TA_CENTER, leading=48)))
    story.append(Paragraph("HAREKETLI UYDU TERMINALI", ParagraphStyle(
        "BigSub", fontName="Helvetica-Bold", fontSize=28,
        textColor=C_PRIMARY, alignment=TA_CENTER, leading=34)))
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="60%", thickness=3,
                             color=C_DARK, spaceBefore=6, spaceAfter=20))
    story.append(Spacer(1, 12))
    story.append(Paragraph("Proje Kapsamli Teknik Sunum", ParagraphStyle(
        "MidText", fontName="Helvetica", fontSize=18,
        textColor=C_GREY, alignment=TA_CENTER, leading=22)))
    story.append(Spacer(1, 8))
    story.append(Paragraph("BTK Satellite Terminal Yarismasi", ParagraphStyle(
        "MidText2", fontName="Helvetica", fontSize=14,
        textColor=C_GREY, alignment=TA_CENTER, leading=18)))
    story.append(Spacer(1, 30))
    story.append(Paragraph(f"Hazirlanma Tarihi: {NOW}", ParagraphStyle(
        "DateText", fontName="Helvetica", fontSize=12,
        textColor=C_GREY, alignment=TA_CENTER, leading=16)))
    story.append(Spacer(1, 8))
    story.append(Paragraph("Yazilim Ekibi: Kerim, Efe, Elif, Simge", ParagraphStyle(
        "TeamText", fontName="Helvetica", fontSize=12,
        textColor=C_PRIMARY, alignment=TA_CENTER, leading=16)))
    story.append(Spacer(1, 8))
    story.append(Paragraph("ROS 2 Humble | Gazebo Classic | C++ | Python | Tkinter",
                           ParagraphStyle("TechText", fontName="Helvetica", fontSize=11,
                                          textColor=C_GREY, alignment=TA_CENTER, leading=14)))
    story.append(PageBreak())

    # ════════════════════════════════════════════
    # SLIDE 2 — ICINDEKILER
    # ════════════════════════════════════════════
    new_slide("Icerik", "Sunum Akisi", story)
    toc_data = [
        ["1", "Proje Genel Bakis", "Proje tanimi, amac, kapsam"],
        ["2", "Sistem Mimarisi", "4 katmanli mimari ve veri akisi"],
        ["3", "Bilesen 1: Gomulu Yazilim", "Kerim - 5 adimli STM32/Teensy C++ kodu"],
        ["4", "Bilesen 2: ROS 2 & Gazebo", "Efe - Kontrol node'lari, simulasyon, dataset"],
        ["5", "Bilesen 3: Python Arayuz", "Ekip - Tkinter GUI, uydu hesabi"],
        ["6", "Bilesen 4: Stabilizasyon", "Simge/Elif - C++ referans kodu"],
        ["7", "Sartname Karsilama", "13 gereksinim analizi"],
        ["8", "Performans & Metrikler", "Hiz, dogruluk, CPU kullanimi"],
        ["9", "Yol Haritasi", "KTR hazirlik ve ilerleme plani"],
        ["10", "Sonuc", "Genel degerlendirme ve cikarimlar"],
    ]
    story.append(tbl(["#", "Baslik", "Aciklama"], toc_data, [25, 140, 230]))
    story.append(PageBreak())

    # ════════════════════════════════════════════
    # BOLUM 1 — PROJE GENEL BAKIS
    # ════════════════════════════════════════════
    section_slide("PROJE GENEL BAKIS", "Hedef, Amac ve Bilesenler", 1, story)

    new_slide("Proje Tanimi", "Hareketli Uydu Terminali (SOTM)", story)
    body("UniS projesi, BTK Satellite Terminal Yarismasi icin gelistirilen "
         "bir Hareketli Uydu Terminali (Satellite On The Move - SOTM) "
         "yazilim sistemidir.", story)
    spacer(6, story)
    highlight("Temel Hedef:", story)
    bullet("Hareketli bir platform (arac, gemi, Insansiz Kara Araci) "
           "uzerindeki antenin, platform hareket halindeyken bir haberlesme "
           "uydusuna kilitli kalmasini saglamak", story)
    spacer(6, story)
    highlight("Karsilanan Temel Zorluklar:", story)
    bullet("Platformun ani sarsintilari ve egimlerine karsi gercek zamanli stabilizasyon", story)
    bullet("Uydunun goreceli konumunun surekli ve hassas sekilde takibi", story)
    bullet("Sensor gurultusu ve mekanik titresimlerin filtrelenmesi", story)
    bullet("Hedef kaybi durumunda hizli yeniden kilitlenme (8 sn)", story)
    bullet("Insan makine arayuzu uzerinden kolay kontrol", story)
    story.append(PageBreak())

    new_slide("Proje Bilesenleri", "4 ana bilesen, 4 ekip uyesi", story)
    comp_rows = [
        ["Gomulu\nYazilim", "Kerim", "C++", "STM32/Teensy\n5 adimli kontrol dongusu\nEKF, SGP4, PID, Telemetri", "Donanim uzerinde\ngercek zamanli kontrol"],
        ["ROS 2 &\nGazebo", "Efe", "C++\nPython", "ROS 2 Humble node'lari\nGazebo Classic simulasyon\nDataset dogrulama araci", "Algoritma dogrulama\nve simulasyon"],
        ["Python\nArayuz", "Ekip", "Python\nTkinter", "Kullanici arayuzu\nUydu yonelim hesabi\nROS bridge", "Insan-makine\narayuzu"],
        ["Stabilizasyon\nOrnegi", "Simge\nElif", "C++", "PID + low-pass filtre\nReferans implementasyon", "Referans kod\nve ogrenme"],
    ]
    story.append(tbl(
        ["Bilesen", "Kisi", "Dil", "Detay", "Rol"],
        comp_rows, [65, 50, 50, 150, 80]))
    story.append(PageBreak())

    new_slide("Teknik Yigin", "Kullanilan teknolojiler ve araclar", story)
    tech_rows = [
        ["Platform", "STM32 (HAL), Teensy, FreeRTOS, Bare-metal C++"],
        ["ROS Sürümü", "ROS 2 Humble (Ubuntu 22.04)"],
        ["Simulasyon", "Gazebo Classic 11 + ros2_control"],
        ["Arayuz", "Python 3 + Tkinter + reportlab"],
        ["Gelistirme", "CMake, colcon, VS Code, Git"],
        ["Sensorler", "IMU (MPU-6050), GPS (NMEA), QPD, Encoder, Limit Switch"],
        ["Iletisim", "UART (115200 baud), ROS 2 Topics/Services"],
        ["Gorev Yonetimi", "FreeRTOS (opsiyonel), bare-metal super-loop"],
    ]
    story.append(tbl(["Alan", "Kullanilan Teknoloji"], tech_rows, [80, 310]))
    story.append(PageBreak())

    # ════════════════════════════════════════════
    # BOLUM 2 — SISTEM MIMARISI
    # ════════════════════════════════════════════
    section_slide("SISTEM MIMARISI", "4 Katmanli Veri Akisi ve Kontrol Mantigi", 2, story)

    new_slide("Mimariye Genel Bakis", "4 katmanli moduler yapi", story)
    body("Sistem yazilimi, her biri belirli bir sorumluluga sahip "
         "4 ana katmandan olusur. Veri akisi asagidan yukariya dogru "
         "ilerler ve her katman bir oncekinin ciktisini kullanir.", story)
    spacer(8, story)
    arch_rows = [
        ["1. ALGILAMA\n(Perception)", "IMU (ivmeolcer + jiroskop)\nGPS (NMEA)\nEncoder\nQPD/Lazer\nLimit Switch", "100 Hz\n1 Hz\n100 Hz\nKesikli\nHer dongu", "Ham sensor verilerinin\ntoplanmasi ve on islenmesi"],
        ["2. KESTIRIM\n(Estimation)", "Kalman Filtresi (EKF)\nQuaternion Yonelim\nSGP4 Propagator\nKoordinat Donusum", "100 Hz\n100 Hz\n1 Hz\n1 Hz", "Sensor fuzyonu ile\nanlamli durum bilgisi\nuretimi"],
        ["3. KONTROL\n(Control)", "Azimuth PID\nElevasyon PID\nStabilizasyon PID\nQPD Aktif Takip\nSpiral Arama", "100 Hz\n100 Hz\n100 Hz\n100 Hz\nOlay bazli", "Motor komutlarinin\nhesaplanmasi ve\nuygulanmasi"],
        ["4. ARAYUZ\n(Interface)", "Tkinter GUI\nROS 2 Bridge\nTelemetri\nParametre Yonetimi", "Kullanici\netkilesimi", "Insan-makine\narayuzu ve sistem\nyonetimi"],
    ]
    story.append(tbl(
        ["Katman", "Bilesenler", "Frekans", "Gorev"],
        arch_rows, [70, 140, 55, 120]))
    story.append(PageBreak())

    new_slide("Veri Akisi Semasi", "Katmanlar arasi veri akisi", story)
    flow_lines = [
        "IMU/Gyro",
        "  |  (100 Hz, ham accel + gyro)",
        "  v",
        "+-----------------------+",
        "|  EKF (7-durumlu)     |  -> Quaternion -> Roll/Pitch/Yaw",
        "|  Kalman Filtresi     |  -> Gyro bias tahmini",
        "+-----------------------+",
        "  |",
        "  v",
        "+-----------------------+",
        "|  STABILIZASYON PID   |  -> X/Y Itki Motor Komutu",
        "|  (hedef roll=0,      |",
        "|   hedef pitch=0)     |",
        "+-----------------------+",
        "",
        "GPS + Uydu Parametresi",
        "  |  (1 Hz, LLA + TLE)",
        "  v",
        "+-----------------------+",
        "|  SGP4 Propagator     |  -> Uydu ECI Konumu",
        "|  + Koordinat Donusum |  -> Az/El Acilari",
        "+-----------------------+",
        "  |",
        "  +-- Platform Tilt Telafisi (roll/pitch ile duzeltme)",
        "  v",
        "+-----------------------+",
        "|  AZIMUTH/ELEVASYON   |  -> Az/El Motor Komutu",
        "|  PID Kontrol         |",
        "+-----------------------+",
        "",
        "QPD/Lazer",
        "  |  (hataya gore)",
        "  v",
        "+-----------------------+",
        "|  QPD Hata Vektoru   |  -> Az/El Offset Duzeltmesi",
        "|  ex = (A+D)-(B+C)/T |",
        "|  ey = (A+B)-(C+D)/T |",
        "+-----------------------+",
        "",
        "Encoder -> PID Geri Beslemesi (kapali dongu)",
        "GUI -> Mod/Hedef/Parametre Komutlari",
    ]
    for line in flow_lines:
        if line:
            code(line, story)
        else:
            spacer(2, story)
    story.append(PageBreak())

    new_slide("Kontrol State Machine", "Sistemin calisma modlari", story)
    body("Sistem, asagidaki durum makinasi ile yonetilir:", story)
    spacer(4, story)
    sm_rows = [
        ["POWER_ON", "Guc acilisi", "Donanim baslatma baslangici"],
        ["HW_SELF_TEST", "Donanim oz-testi", "IMU, GPS, motor, encoder testi"],
        ["HOMING", "Sifir noktasi", "Limit switch -> encoder=0"],
        ["CALIBRATING", "IMU kalibrasyon", "500 ornek bias tahmini"],
        ["IDLE", "Bekleme", "Kullanici komutu bekliyor"],
        ["AUTO_TRACKING", "Otomatik takip", "EKF + SGP4 + PID + QPD aktif"],
        ["MANUAL", "Manuel mod", "Kullanici Az/El girisleri"],
        ["ERROR", "Hata", "Motorlar durduruldu, bekleniyor"],
    ]
    story.append(tbl(
        ["Durum", "Aciklama", "Detay"],
        sm_rows, [80, 100, 200]))
    story.append(Spacer(1, 8))
    note("Gecisler: AUTO <-> MANUAL (kullanici komutu), "
         "herhangi bir durumdan ERROR (hata tespiti)", story)
    story.append(PageBreak())

    # ════════════════════════════════════════════
    # BOLUM 3 — GOMULU YAZILIM (KERIM)
    # ════════════════════════════════════════════
    section_slide("BILESEN 1: GOMULU YAZILIM", "Kerim — 5 Adimli Kontrol Dongusu (C++)", 3, story)

    new_slide("5 Adimli Mimari", "STM32/Teensy uzerinde gercek zamanli kontrol", story)
    body("Gomulu yazilim, bir mikrodenetleyici (STM32 veya Teensy) "
         "uzerinde calisan, 5 adimdan olusan bir kontrol dongusuden "
         "olusur. FreeRTOS veya bare-metal ortamda calisabilir.", story)
    spacer(6, story)
    five_rows = [
        ["1", "BASLATMA\nVE\nKALIBRASYON", "initialization.h", "Donanim testi\nHoming\nIMU kalibrasyonu", "1 kez\n(sistem acilista)"],
        ["2", "VERI\nTOPLAMA", "main.cpp", "IMU 100Hz\nGPS 1Hz\nEncoder 100Hz\nUART komut", "Her 10ms"],
        ["3", "SENSOR\nFUZYONU &\nKOORDINAT", "SensorFusion.h\nSatelliteTracker.h", "EKF predict+update\nSGP4 propagasyon\nPlatform tilt telafisi", "Her 10ms"],
        ["4", "PID\nKONTROL\n& GUVENLIK", "PIDController.h", "Az/El PID\nAnti-windup\nDeadband\nSafetyMonitor", "Her 10ms"],
        ["5", "TELEMETRI\n& GERI\nBESLEME", "telemetry.h", "72 byte UART paketi\nCRC16\nKomut kuyrugu", "Her 100ms"],
    ]
    story.append(tbl(
        ["Adim", "Islev", "Dosya", "Detay", "Periyot"],
        five_rows, [25, 60, 80, 140, 55]))
    story.append(Spacer(1, 8))
    code("Toplam Dongu Performansi: ~3.3ms (hedef 10ms) -> %67 CPU Kullanimi", story)
    story.append(PageBreak())

    new_slide("Adim 1: Baslatma ve Kalibrasyon", "Detayli anlatim", story)
    highlight("1A — Donanim Oz-Testi (HardwareSelfTest):", story)
    body("Sistem enerji aldigi anda tum donanim bilesenlerini test eder:", story)
    bullet("IMU: 0x68 adresinde MPU-6050 algilanmasi ve yer cekimi olcumunun "
           "kontrolu (9.80665 +/- 2 m/s²)", story)
    bullet("GPS: NMEA modulu ile UART iletisimi", story)
    bullet("Motor suruculer: Azimut ve elevasyon motorlari", story)
    bullet("Encoder'lar: Her iki eksen acisi sensoru", story)
    note("Herhangi bir test basarisiz olursa ilgili hata bayragi "
         "set edilir ve sistem ERROR moduna alinir.", story)
    spacer(8, story)

    highlight("1B — Homing (HomingProcedure):", story)
    body("Antenin referans (sifir) noktasinin belirlenmesi:", story)
    code("1. CW yonunde limit switch'e dogru yaklasma (%5 PWM)", story)
    code("2. Limit switch tetiklenince aninda durma", story)
    code("3. 100ms bekleme (mekanik salinim sonlansin)", story)
    code("4. CCW yonunde 2 derece geri cekilme (%3 PWM, 400ms)", story)
    code("5. Bu nokta encoder=0 olarak belirlenir", story)
    note("15 saniye timeout: limit switch bulunamazsa hata.", story)
    spacer(8, story)

    highlight("1C — IMU Kalibrasyonu (IMUCalibration):", story)
    body("Cihaz hareketsizken 500 ornek (5 saniye) toplanir:", story)
    bullet("Gyro Bias: Hareketliyken ortalama gyro degeri (ideal: 0). "
           "Bu deger EKF'ye baslangic degeri olarak verilir.", story)
    bullet("Accel Bias: normalized yer cekimi vektorunden sapma.", story)
    bullet("Kalite Kontrol: Accel scale %5 tolerans, gyro norm < 0.1 rad/s", story)
    story.append(PageBreak())

    new_slide("Adim 2: Veri Toplama", "Sensor okuma ve on isleme", story)
    body("Ana kontrol dongusunun her adiminda (10ms) asagidaki "
         "islemler gerceklestirilir:", story)
    spacer(4, story)
    dt_rows = [
        ["IMU (MPU-6050)", "100 Hz (10ms)", "3-eksen ivmeolcer (m/s²)\n3-eksen jiroskop (rad/s)", "Kalibrasyon bias'i cikarilir\nEKF predict+update girdisi"],
        ["GPS (NMEA)", "1 Hz (1000ms)", "Enlem/Boylam/Irtifa\nHDOP, hiz, yon\nUydu sayisi", "HDOP < 5m ise gecerli\nfix yoksa hata bayragi"],
        ["Encoder", "Her dongu (10ms)", "Azimut acisi\nElevasyon acisi\nAnlik hiz (dps)", "PID geri beslemesi"],
        ["Limit Switch", "Her dongu", "Azimut min/max\nElevasyon min/max", "Guvenlik monitoru girdisi"],
        ["UART Komut", "Olay bazli", "CommandPacket\n(8 elemanli FIFO)", "Kullanici komut kuyrugu"],
    ]
    story.append(tbl(
        ["Sensor", "Frekans", "Veri", "Kullanim"],
        dt_rows, [70, 70, 120, 110]))
    story.append(PageBreak())

    new_slide("Adim 3A: Extended Kalman Filter", "7-durumlu IMU Sensor Fuzyonu", story)
    body("EKF, IMU'nun gyro ve ivmeolcer verilerini birlestirerek "
         "terminalin uzaysal yonelimini (orientation) kestirir.", story)
    spacer(4, story)

    highlight("Durum Vektoru (7 boyut):", story)
    code("x = [q0, q1, q2, q3,  bx, by, bz]", story)
    code("      Birim quaternion     Gyro bias (rad/s)", story)
    spacer(4, story)

    highlight("EKF Isleyisi:", story)
    bullet("<b>Predict (Tahmin):</b> Jiroskop olcumunden quaternion "
           "kinematigi ile durum ilerletilir.", story)
    code("  q_dot = 0.5 * Omega(w_corrected) * q", story)
    code("  w_corrected = w_measured - bias", story)
    code("  7x7 Jacobian matrisi ile kovaryans yayilimi", story)
    spacer(4, story)
    bullet("<b>Update (Duzeltme):</b> Ivmeolcer olcumu ile duzeltme.", story)
    code("  h(x) = R(q) * [0, 0, g]^T  (beklenen ivme)", story)
    code("  Olcum yeniligi: innov = accel_raw - h(x)", story)
    code("  Kalman kazanci: K = P*H'*(H*P*H' + R)^-1", story)
    code("  Guncelleme: x += K * innov, P = (I-K*H)*P", story)
    spacer(4, story)
    bullet("Ivme buyuklugu yer cekiminden %30'dan fazla saparsa "
           "(100% hareket) update adimi atlanir.", story)
    note("Bu sayede yuksek ivmeli manevralarda hatali guncelleme "
         "engellenir.", story)
    story.append(PageBreak())

    new_slide("Adim 3B: SGP4 Uydu Propagatoru", "TLE'den uydu konumuna", story)
    body("SGP4 (Simplified General Perturbations #4), TLE (Two-Line "
         "Element) verisini kullanarak yapay uydularin yorunge "
         "konumunu hesaplar.", story)
    spacer(4, story)

    highlight("Veri Akisi:", story)
    code("TLE (ham metin) -> TLEParser::parse()", story)
    code("  -> TLEData (yapisal veri)", story)
    code("  -> SGP4Propagator::init()", story)
    code("  -> SGP4Elements (onceden hesaplanmis sabitler)", story)
    code("  -> SGP4Propagator::propagate(JulianDate)", story)
    code("  -> ECI konum ve hiz vektorleri (km, km/s)", story)
    code("  -> CoordinateTransform::eciToECEF()", story)
    code("  -> ECEF (Dunya merkezli, Dunya sabit)", story)
    code("  -> CoordinateTransform::calcAzEl(gozlemci_LLA)", story)
    code("  -> Az/El acilari (derece) + menzil (km)", story)
    spacer(6, story)

    highlight("SGP4 Ozellikleri:", story)
    bullet("Newton-Raphson ile Kepler denklemi cozumu (8 iterasyon)", story)
    bullet("J2, J3 pertubasyon etkileri dahil", story)
    bullet("Atmosferik suruklenme (BSTAR) modellemesi", story)
    bullet("Perigee < 156 km icin ozel durum (dusuk yorunge)", story)
    bullet("Epoch'dan itibaren herhangi bir JD'de konum hesaplama", story)
    spacer(4, story)

    highlight("Koordinat Donusumleri:", story)
    bullet("ECI -> ECEF: Greenwich Sidereal Time (GAST) ile dunya donusu", story)
    bullet("ECEF -> LLA: WGS-84 elipsoid, Bowring iterasyonu", story)
    bullet("LLA -> Az/El: NED (North-East-Down) cercevesinde", story)
    story.append(PageBreak())

    new_slide("Adim 3C: Platform Tilt Telafisi", "Arac egiminin matematiksel duzeltmesi", story)
    body("Arac bir yokus veya egimde duruyorsa, uyduya dogru "
         "hesaplanan Az/El acilari gövde cercevesinde gecersiz olur. "
         "Bu nedenle EKF'den gelen roll/pitch bilgisi kullanilarak "
         "hedef acilari duzeltilir.", story)
    spacer(6, story)

    highlight("Matematiksel Model:", story)
    body("1. Uydu birim vektoru kuresel koordinatlardan NED cercevesine "
         "cevrilir.", story)
    code("ux = cos(el) * sin(az)", story)
    code("uy = cos(el) * cos(az)", story)
    code("uz = sin(el)", story)
    spacer(3, story)
    body("2. Platform donus matrisi uygulanir: R = Ry(pitch) * Rx(roll)", story)
    code("bx = cp*ux + sp*sr*uy + sp*cr*uz", story)
    code("by =          cr*uy    - sr*uz", story)
    code("bz = -sp*ux + cp*sr*uy + cp*cr*uz", story)
    spacer(3, story)
    body("3. Goevde cercevesinden tekrar Az/El'e:", story)
    code("el_comp = asin(bz)", story)
    code("az_comp = atan2(bx, by)", story)
    spacer(4, story)
    note("Bu duzeltme olmadan, egimli bir yuzeyde anten yanlis "
         "yone dogrultulmus olur.", story)
    story.append(PageBreak())

    new_slide("Adim 4: PID Kontrol ve Guvenlik", "Detayli PID analizi", story)
    body("PID kontrol, iki bagimsiz eksen icin ayri PIDController "
         "siniflariyla gerceklestirilir.", story)
    spacer(4, story)

    highlight("PID Parametreleri:", story)
    pid_rows = [
        ["Parametre", "Azimut", "Elevasyon", "Anlami"],
        ["Kp (Oransal)", "2.5", "3.0", "Buyuk -> hizli tepki, salinim riski"],
        ["Ki (Integral)", "0.1", "0.08", "Kalici hatayi sifirlar"],
        ["Kd (Turev)", "0.3", "0.25", "Salinimi azaltir, yumusatir"],
        ["Max Integral", "20.0", "15.0", "Anti-windup limiti"],
        ["Deadband", "+/-0.1 derece", "+/-0.1 derece", "Altinda motor durur"],
        ["Turev Filtre", "0.7", "0.7", "EMA katsayisi"],
        ["Max Hiz", "60 derece/s", "30 derece/s", "Guvenlik limiti"],
    ]
    story.append(tbl(
        pid_rows[0], pid_rows[1:], [110, 60, 60, 140]))
    spacer(8, story)

    highlight("PID Formulu:", story)
    code("error = target - measured", story)
    code("P = Kp * error", story)
    code("I += Ki * error * dt    (anti-windup ile)", story)
    code("D = Kd * (error - prev_error) / dt    (filtreli)", story)
    code("output = clamp(P + I + D, min, max)", story)
    spacer(6, story)

    highlight("Anti-Windup Mekanizmasi:", story)
    body("Cikis doyuktaysa VE hata ayni yonde ise integratör "
         "dondurulur. Bu sayede integral sarmasi (windup) "
         "engellenir ve toparlanma suresi kisalir.", story)
    spacer(4, story)
    highlight("Deadband:", story)
    body("+/-0.1 derece icinde hata sifir kabul edilir, "
         "integrator sifirlanir ve motor durdurulur. "
         "Bu, surekli mikro-duzeltmeleri engelleyerek "
         "motor omrunu uzatir ve guc tuketimini azaltir.", story)
    story.append(PageBreak())

    new_slide("Adim 4: Guvenlik Monitoru", "4 seviyeli koruma sistemi", story)
    body("SafetyMonitor, fiziksel ve yazilimsal limitleri "
         "denetleyerek sistemi guvenli bolgede tutar:", story)
    spacer(4, story)

    safe_rows = [
        ["SAFE", "Guvenli bolge\n(Normal calisma)", "Komut oldugu gibi iletilir\nHiz sinirlamasi yok", "Yesil"],
        ["SOFT", "Yazilim limiti yakini\n(Uyari bolgesi)", "Hiz %50 azaltilir\nKablo koruma aktif", "Sari"],
        ["HARD", "Fiziksel limit\n(Kritik bolge)", "Motor DURDURULUR\nHata bayragi set edilir", "Turuncu"],
        ["FAULT", "Limit switch tetiklendi\n(Acil durum)", "Acil durdurma\nSistem ERROR moduna alinir", "Kirmizi"],
    ]
    story.append(tbl(
        ["Seviye", "Durum", "Aksiyon", "Renk"],
        safe_rows, [55, 95, 160, 40]))
    spacer(8, story)

    highlight("Kablo Sarmalama Korumasi:", story)
    body("Azimut ekseni 350 dereceyi gectiginde (kablo sarmasi "
         "riski), motor hizi kademeli olarak azaltilir:", story)
    code("if (pos >= cable_wrap):", story)
    code("    scale = 1 - (pos - cable_wrap) / (hard_max - cable_wrap)", story)
    code("    cmd *= clamp(scale, 0.0, 1.0)", story)
    story.append(PageBreak())

    new_slide("Adim 5: Telemetri Paketi", "72 byte, UART 115200 baud, 10 Hz", story)
    body("Telemetri sistemi, sistemin anlik durumunu 10 Hz "
         "frekansinda PC/GUI'ye bildirir.", story)
    spacer(4, story)

    highlight("Paket Yapisi:", story)
    tel_rows = [
        ["Baslik", "Magic (0xABCD)", "2 byte", "Paket baslangici"],
        ["", "Timestamp", "4 byte", "ms cinsinden sure"],
        ["Durum", "System State", "1 byte", "8 durum"],
        ["", "Error Flags", "2 byte", "8 hata kodu"],
        ["Konum", "Latitude, Longitude, Altitude", "12 byte", "WGS-84"],
        ["Yonelim", "Roll, Pitch, Yaw", "12 byte", "EKF ciktisi"],
        ["Anten", "Az/El gercek (encoder)", "8 byte", "Gercek konum"],
        ["", "Az/El hedef (setpoint)", "8 byte", "Hedef konum"],
        ["", "Az/El hata", "8 byte", "Takip hatasi"],
        ["Uydu", "Sat Az/El/Menzil", "12 byte", "SGP4 ciktisi"],
        ["Sinyal", "RSSI", "1 byte", "dBm"],
        ["Dogrulama", "CRC-16 (CCITT)", "2 byte", "X-25 polinom"],
        ["TOPLAM", "", "72 byte", ""],
    ]
    story.append(tbl(
        ["Kategori", "Alan", "Boyut", "Aciklama"],
        tel_rows, [50, 130, 50, 120]))
    spacer(6, story)

    highlight("Komut Seti (GUI -> Terminal):", story)
    cmd_rows = [
        ["SET_AUTO_MODE", "1", "Otomatik takip modu"],
        ["SET_MANUAL", "2", "Manuel kontrol modu"],
        ["MANUAL_AZ", "3", "Azimut manuel hedef (float)"],
        ["MANUAL_EL", "4", "Elevasyon manuel hedef (float)"],
        ["LOAD_TLE", "5", "Yeni TLE yukle"],
        ["HOME", "6", "Homing (sifirlama)"],
        ["EMERGENCY_STOP", "7", "Acil durdurma"],
    ]
    story.append(tbl(
        ["Komut", "Kod", "Aciklama"], cmd_rows, [100, 35, 160]))
    story.append(PageBreak())

    # ════════════════════════════════════════════
    # BOLUM 4 — ROS 2 & GAZEBO (EFE)
    # ════════════════════════════════════════════
    section_slide("BILESEN 2: ROS 2 & GAZEBO", "Efe — Kontrol Node'lari, Simulasyon, Dataset", 4, story)

    new_slide("ROS 2 Mimarisi", "mergen_control paketi detayli inceleme", story)
    body("ROS 2 Humble uzerinde calisan kontrol node'lari, "
         "ozel mesaj tipleri ve Gazebo entegrasyonu.", story)
    spacer(4, story)

    highlight("Topic Yapisi:", story)
    topic_rows = [
        ["/mergen/imu_filtered", "ImuFiltered", "Subscription", "Filtrelenmis IMU (roll/pitch)"],
        ["/mergen/motor_state", "MotorState", "Subscription", "Encoder motor konumu"],
        ["/mergen/target_angles", "TargetAngles", "Subscription", "Hedef Az/El acilari"],
        ["/mergen/motor_command", "MotorCommand", "Publisher", "PWM + stabilizasyon ciktisi"],
    ]
    story.append(tbl(
        ["Topic", "Mesaj Tipi", "Tip", "Aciklama"],
        topic_rows, [130, 80, 70, 100]))
    spacer(6, story)

    highlight("Kontrol Node'u (control_node.cpp):", story)
    body("100 Hz timer ile calisan ana kontrol node'u:", story)
    bullet("3 subscription: IMU filtrelenmis, motor durumu, hedef acilari", story)
    bullet("1 publisher: Motor komutlari (PWM + stabilizasyon)", story)
    bullet("Her 10ms'de: Azimuth PID, Elevasyon PID, Stabilizasyon", story)
    bullet("Cikti: azimuth_pwm, elevation_pwm, stabilizer_x/y_pwm", story)
    story.append(PageBreak())

    new_slide("PID Kontroller (C++)", "mergen_control kutuphanesi", story)
    body("mergen_control kutuphanesi 4 ana sinif icerir. Her biri "
         "belirli bir kontrol gorevini ustlenir.", story)
    spacer(4, story)

    highlight("1. PidController:", story)
    code("PidController az_pid(2.0, 0.02, 0.15, -1.0, 1.0);", story)
    code("PidController el_pid(2.2, 0.02, 0.16, -1.0, 1.0);", story)
    code("double output = pid.update(target, measurement, dt);", story)
    body("Genel amacli PID kontrolor. Kp, Ki, Kd parametreleri "
         "ve cikis sinirlamasi (clamp) ile yapilandirilir. "
         "ROS 2 topic'lerinden gelen verilerle calisir.", story)
    spacer(4, story)

    highlight("2. StabilizationController:", story)
    code("StabilizationController stabilizer(roll_pid, pitch_pid, 4.0);", story)
    code("auto cmd = stabilizer.update(roll_deg, pitch_deg, dt);", story)
    body("EKF'den gelen roll ve pitch acilarini alir, hedef "
         "degeri sifir (duz pozisyon) olan PID'lerden gecirir "
         "ve mm_per_degree olcegiyle X/Y itki mekanizmasi "
         "komutuna donusturur.", story)
    spacer(4, story)

    highlight("3. QpdTracker:", story)
    code("QpdError err = tracker.calculate(A, B, C, D);", story)
    body("QPD sensorunden gelen 4 bolge akimi (A, B, C, D) "
         "kullanilarak boresight hata vektoru hesaplanir.", story)
    spacer(4, story)

    highlight("4. SpiralSearch:", story)
    code("SpiralOffset off = search.update(elapsed_sec);", story)
    body("Hedef kaybi durumunda giderek genisleyen spiral "
         "deseninde arama offseti uretir.", story)
    story.append(PageBreak())

    new_slide("QPD Lazer Takip Algoritmasi", "Aktif geri besleme ile yuksek hassasiyet", story)
    body("QPD (Quadrant Photo Diode), lazer isiginin sensore "
         "dusus noktasini 4 bolgeye ayirarak algilar.", story)
    spacer(4, story)

    highlight("Hata Vektoru Hesabi:", story)
    code("toplam = A + B + C + D", story)
    code("error_x = ((A + D) - (B + C)) / toplam", story)
    code("error_y = ((A + B) - (C + D)) / toplam", story)
    spacer(3, story)
    body("Bu hata vektoru, antenin boresight (optik eksen) "
         "hatasini gosterir.", story)
    spacer(4, story)

    highlight("Calisma Mantigi:", story)
    bullet("toplam < detection_threshold: Lazer hedefte degil -> "
           "Spiral arama baslatilir", story)
    bullet("toplam >= threshold & error kucuk: Aktif takip -> "
           "Hata vektoru Az/El offset'i olarak PID'ye eklenir", story)
    bullet("error_x -> azimut hedefinde duzeltme", story)
    bullet("error_y -> elevasyon hedefinde duzeltme", story)
    spacer(4, story)

    highlight("Neden QPD + Lazer?", story)
    bullet("Teorik uydu yonelimindeki mekanik toleranslari kapatir", story)
    bullet("Platform sarsintilarina karsi ekstra guvence saglar", story)
    bullet("Encoder geri beslemesinden bagimsiz calisir", story)
    bullet("Milimetrik hassasiyette yonlendirme mumkun", story)
    story.append(PageBreak())

    new_slide("Spiral Arama Algoritmasi", "Hedef kaybi durumunda akilli arama", story)
    body("Teorik konumlandirma sonrasi lazer hedefi yakalayamazsa "
         "(QPD toplam sinyali esik alti), sistem spiral arama "
         "moduna gecer.", story)
    spacer(6, story)

    highlight("Matematiksel Model:", story)
    code("radius(t) = min(max_radius_deg, radial_speed * t)", story)
    code("angle(t)  = angular_speed * t", story)
    code("offset_az = radius(t) * cos(angle(t))", story)
    code("offset_el = radius(t) * sin(angle(t))", story)
    spacer(4, story)

    highlight("Parametreler:", story)
    spiral_rows = [
        ["radial_speed_deg_s", "Yari capin buyume hizi", "Derece/saniye"],
        ["angular_speed_rad_s", "Acisal hiz", "Radyan/saniye"],
        ["max_radius_deg", "Maksimum arama yaricapi", "Derece"],
    ]
    story.append(tbl(
        ["Parametre", "Anlami", "Birim"],
        spiral_rows, [115, 140, 65]))
    spacer(8, story)

    highlight("Durum Makinasi:", story)
    code("QPD toplam < threshold  ->  SPIRAL_ARAMA", story)
    code("QPD toplam >= threshold ->  AKTIF_TAKIP", story)
    code("Hata vector < esik      ->  KILITLI (locked)", story)
    story.append(PageBreak())

    new_slide("Gazebo Simulasyonu", "Dijital ikiz ile dogrulama", story)
    body("Gazebo Classic 11, ROS 2 Humble ile birlikte kullanilir. "
         "CAD modeli tamamlanana kadar basit geometrilerle "
         "simulasyon yapilir.", story)
    spacer(4, story)

    highlight("World Dosyasi (mergen_test.world):", story)
    code("Hedef: 3.464m x, 0m y, 2.0m z -> 30 derece elevasyon", story)
    code("Menzil: 4 metre", story)
    code("Hedef geometrisi: Kirmizi silindir (radius 0.5m)", story)
    spacer(4, story)

    highlight("Controller Yapilandirmasi:", story)
    code("controller_manager:", story)
    code("  update_rate: 100", story)
    code("  joint_state_broadcaster:", story)
    code("    type: joint_state_broadcaster/JointStateBroadcaster", story)
    spacer(4, story)

    highlight("Baslatma (Launch):", story)
    code("simulation.launch.py:", story)
    code("  1. mergen_gazebo/gazebo.launch.py", story)
    code("  2. mergen_estimation/imu_filter.launch.py", story)
    code("  3. mergen_control/control.launch.py", story)
    spacer(4, story)

    highlight("Sistem Modlari:", story)
    code("manual    -> Kullanici manuel Az/El giris", story)
    code("automatic -> EKF + SGP4 + PID + QPD (tum sistem)", story)
    code("search    -> Spiral arama aktif", story)
    code("safe      -> Guvenli mod, motorlar durduruldu", story)
    story.append(PageBreak())

    new_slide("Dataset Dogrulama Araci", "CAD olmadan algoritma dogrulama", story)
    body("CAD modeli hazir olmadan once kontrol algoritmalarini "
         "test etmek icin CSV dataset tabanli bir dogrulama "
         "araci gelistirilmistir.", story)
    spacer(4, story)

    highlight("Veri Uretimi (generate_dataset):", story)
    code("Sure: 5 dakika (300 saniye)", story)
    code("Frekans: 100 Hz -> 30.000 satir", story)
    code("Roll: 8 * sin(2*pi*t/10) + Gaussian(0, 0.18)", story)
    code("Pitch: 8 * cos(2*pi*t/10) + Gaussian(0, 0.18)", story)
    code("Yaw: (36*t) %% 360 (sabit donus 36 derece/s)", story)
    code("Target: Az=120, El=30 (sabit)", story)
    code("QPD: ex=0.15*sin(0.7*t), ey=0.12*cos(0.5*t)", story)
    spacer(4, story)

    highlight("Isleme (run_dataset):", story)
    code("1. Kalman filtresi (Q=0.01, R=0.25) -> IMU filtreleme", story)
    code("2. QPD hata vektoru -> Az/El offset", story)
    code("3. Azimuth PID + Elevasyon PID -> PWM", story)
    code("4. Stabilizasyon PID -> X/Y PWM", story)
    code("5. Kilit durumu: |ex|<0.03 & |ey|<0.03", story)
    spacer(4, story)

    highlight("Kullanim:", story)
    code("python dataset_simulator.py --generate --output sample_motion.csv", story)
    code("python dataset_simulator.py --input sample_motion.csv --output sample_result.csv", story)
    story.append(PageBreak())

    new_slide("Dataset Cikti Analizi", "Sample cikti sutunlari ve anlami", story)
    result_rows = [
        ["time_s", "Zaman damgasi", "3.000"],
        ["roll_filtered_deg", "Kalman filtreli roll", "7.59491"],
        ["pitch_filtered_deg", "Kalman filtreli pitch", "-2.29486"],
        ["qpd_error_x", "QPD X hata", "0.12948"],
        ["qpd_error_y", "QPD Y hata", "0.00849"],
        ["azimuth_pwm", "Azimut motor PWM", "1.00000 (limit)"],
        ["elevation_pwm", "Elevasyon motor PWM", "-0.99320"],
        ["stabilizer_x_pwm", "Stabilizasyon X eksen", "-1.00000 (limit)"],
        ["stabilizer_y_pwm", "Stabilizasyon Y eksen", "1.00000 (limit)"],
        ["target_locked", "Kilit durumu", "False"],
    ]
    story.append(tbl(
        ["Sutun", "Aciklama", "Ornek Deger"],
        result_rows, [90, 150, 80]))
    spacer(6, story)

    highlight("Gozlemler:", story)
    bullet("PID ciktisi genellikle limitte (1.0/-1.0) -> yuksek hata", story)
    bullet("target_locked=False -> QPD hatasi threshold'un ustunde", story)
    bullet("Kalman filtresi gurultuyu basariyla bastiriyor", story)
    bullet("Stabilizasyon X/Y surekli olarak roll/pitch'i bastirmaya calisiyor", story)
    story.append(PageBreak())

    new_slide("Firmware Referans Kodu", "ROS 2 -> Gomulu platform gecisi", story)
    body("firmware_reference/teensy_stm32_cpp klasoru, ROS 2 "
         "kontrol algoritmalarinin gomulu platforma tasinmasi "
         "icin bir referans saglar.", story)
    spacer(4, story)

    highlight("main_loop_example.cpp:", story)
    code("MotorOutput update_control_loop(", story)
    code("    float target_az, float target_el,", story)
    code("    float measured_az, float measured_el,", story)
    code("    float raw_roll, float raw_pitch,", story)
    code("    float dt_sec) {", story)
    code("    static KalmanFilter1D roll_filter(0.01, 0.25);", story)
    code("    static KalmanFilter1D pitch_filter(0.01, 0.25);", story)
    code("    static PidController az_pid(2.0, 0.02, 0.15, -1, 1);", story)
    code("    ...", story)
    code("}", story)
    spacer(4, story)

    highlight("KalmanFilter1D:", story)
    code("class KalmanFilter1D {", story)
    code("    float update(float measurement) {", story)
    code("        p += q;  // covariance + process noise", story)
    code("        float k = p / (p + r);  // Kalman gain", story)
    code("        x += k * (measurement - x);  // estimate update", story)
    code("        p *= (1 - k);  // covariance update", story)
    code("        return x;", story)
    code("    }", story)
    code("};", story)
    note("1 boyutlu Kalman filtresi, 7-durumlu EKF'nin "
         "basitlestirilmis versiyonudur. Gercel sistemde "
         "EKF kullanilir.", story)
    story.append(PageBreak())

    # ════════════════════════════════════════════
    # BOLUM 5 — PYTHON ARAYUZ
    # ════════════════════════════════════════════
    section_slide("BILESEN 3: PYTHON ARAYUZ", "Ekip — Tkinter GUI, Uydu Hesabi, ROS Bridge", 5, story)

    new_slide("Tkinter GUI", "Kullanici arayuzu detayli analiz", story)
    body("Python Tkinter kutuphanesi ile hazirlanmis 820x560 "
         "pencere boyutunda kullanici arayuzu. ROS 2 kurulu "
         "olmayan bilgisayarlarda simulasyon modunda calisir.", story)
    spacer(4, story)

    highlight("Ana Bolumler:", story)
    gui_rows = [
        ["1. Komut ve Mod\n(ttk.LabelFrame)", "RadioButton: Otomatik/Manuel\nEntry: Azimuth, Elevasyon\nButton: Manuel Hedef Gonder", "Mod secimi\nManuel acı giris\nHedef iletimi"],
        ["2. Uydu Yonelimi\n(ttk.LabelFrame)", "Entry: Enlem, Boylam\nCombobox: Turksat 4B/5A\nButton: Az/El Hesapla", "GPS koordinatlari\nUydu secimi\nTeorik hesaplama"],
        ["3. Telemetri\n(ttk.LabelFrame)", "Text widget (12 satir)\nOtomatik kaydirma", "Durum mesajlari\nSistem geri bildirimi"],
        ["4. Alt Butonlar", "Parametreleri Kaydet\nGuvenli Mod", "JSON config\nAcil durum"],
    ]
    story.append(tbl(
        ["Bolum", "Bilesenler", "Islev"],
        gui_rows, [100, 160, 90]))
    spacer(6, story)

    highlight("Ozellikler:", story)
    bullet("ui_state.json ile kalici durum kaydi (mode, acilar, konum)", story)
    bullet("Elevasyon girisi 0-90 derece sinirlamasi", story)
    bullet("Otomatik modda uydu konumuna gore Az/El hesaplama", story)
    bullet("Manuel modda dogrudan aci girisi", story)
    bullet("Simulasyon modu (ROS yokken)", story)
    story.append(PageBreak())

    new_slide("Uydu Yonelim Hesaplama", "Jeostasyoner uydu geometrisi", story)
    body("satellite_pointing.py modulu, jeostasyoner (geo-sabit) "
         "uydular icin azimuth ve elevasyon acilarini yaklasik "
         "olarak hesaplar.", story)
    spacer(4, story)

    highlight("Matematiksel Model:", story)
    body("Jeostasyoner uydu, Dunya'nin donusuyla ayni hizda "
         "dondugu icin sabit bir boylamda gorunur. "
         "Hesaplama icin basit kuresel geometri kullanilir:", story)
    code("lat = radians(latitude_deg)", story)
    code("delta_lon = radians(satellite_lon - observer_lon)", story)
    code("R_earth = 6378.137 km  (Dunya yaricapi)", story)
    code("R_geo   = 42164.0 km   (jeostasyoner yorunge)", story)
    code("ratio = R_earth / R_geo", story)
    spacer(3, story)
    code("elevation = atan( (cos(lat)*cos(dlon) - ratio)", story)
    code("                  / sqrt(1 - (cos(lat)*cos(dlon))^2) )", story)
    code("azimuth = atan2(sin(dlon), -sin(lat)*cos(dlon))", story)
    spacer(4, story)

    highlight("Desteklenen Uydular:", story)
    sat_rows = [
        ["Turksat 4B", "50.0 derece Dogu", "Haberlesme, TV yayini"],
        ["Turksat 5A", "31.0 derece Dogu", "Haberlesme, genis bant"],
    ]
    story.append(tbl(
        ["Uydu", "Boylam", "Kullanim"],
        sat_rows, [70, 100, 130]))
    spacer(4, story)
    note("Varsayilan konum: Ankara (39.9208 K, 32.8541 D)", story)

    highlight("Dogrulama Notu:", story)
    body("Bu hesap KTR (Kritik Tasarim Raporu) oncesi yazilim "
         "dogrulamasi icin yeterli yaklasimdir. Nihai sistemde "
         "WGS84, manyetik sapma ve anten montaj offsetleriyle "
         "kalibre edilmelidir.", story)
    story.append(PageBreak())

    new_slide("ROS Bridge", "Simulasyon ve gercek baglanti", story)
    body("MergenRosClient sinifi, arayuz ile ROS 2 sistemi "
         "arasinda ince bir baglanti katmani saglar.", story)
    spacer(4, story)

    highlight("Sinif Arayuzu:", story)
    code("class MergenRosClient:", story)
    code("    def __init__(self):", story)
    code("        self.connected = False", story)
    code("", story)
    code("    def set_mode(self, mode: str) -> str:", story)
    code("        # ROS 2 service call veya simulasyon", story)
    code("        return f'Simulasyon: {mode} secildi'", story)
    code("", story)
    code("    def send_manual_target(az, el) -> str:", story)
    code("        # ROS 2 topic publish veya simulasyon", story)
    code("", story)
    code("    def save_parameters() -> str:", story)
    code("        # ROS 2 service call veya simulasyon", story)
    spacer(4, story)

    highlight("Calisma Modlari:", story)
    bridge_rows = [
        ["Simulasyon", "ROS 2 yok", "Tum islevler taklit\nGerçek baglanti yok", "Gelistirme/test\nbilgisayari"],
        ["Gercek", "ROS 2 Humble\n(Ubuntu 22.04)", "rclpy publisher\nService client", "Terminal sistemi\nile entegrasyon"],
    ]
    story.append(tbl(
        ["Mod", "Durum", "Davranis", "Kullanim"],
        bridge_rows, [55, 70, 130, 85]))
    story.append(PageBreak())

    # ════════════════════════════════════════════
    # BOLUM 6 — STABILIZASYON ORNEGI
    # ════════════════════════════════════════════
    section_slide("BILESEN 4: STABILIZASYON ORNEGI", "Simge/Elif — C++ Referans Kodu", 6, story)

    new_slide("x.cpp: Iki Versiyon", "Basitten gelismise PID + filtre", story)
    body("simge_elif/x.cpp dosyasi, Mergen stabilizasyon sistemi "
         "icin iki versiyon icerir.", story)
    spacer(4, story)

    highlight("Versiyon 1 (Yorum Satiri - Eski):", story)
    code("// Basit model: sabit 0.95 carpani ile filtreleme", story)
    code("float processIMU(float rawData) {", story)
    code("    return rawData * 0.95f;  // 'filtre'", story)
    code("}", story)
    code("// PID: integral windup korumasi YOK", story)
    code("float calculateCorrection(float cur, float tgt) {", story)
    code("    integral += error;    // her kademede artar", story)
    code("    return Kp*error + Ki*integral + Kd*derivative;", story)
    code("}", story)
    bullet("Kp=2.0, Ki=0.5, Kd=0.1 (yuksek integral -> salinim riski)", story)
    bullet("IMU basit sabit carpan, gercek filtre degil", story)
    bullet("Windup korumasi yok -> buyuk ani hareketlerde sorun", story)
    bullet("dt parametresi yok -> sabit dongu varsayimi", story)
    spacer(6, story)

    highlight("Versiyon 2 (Aktif - Gelismis):", story)
    code("// Gercek low-pass filtre (alpha=0.1)", story)
    code("float processIMU(float rawData) {", story)
    code("    prevFiltered = ALPHA * rawData + (1-ALPHA) * prevFiltered;", story)
    code("    return prevFiltered;", story)
    code("}", story)
    code("// dt parametreli PID + windup korumasi", story)
    code("float calculateCorrection(float cur, float tgt, float dt) {", story)
    code("    if (dt <= 0.0f) return 0.0f;", story)
    code("    error = tgt - cur;", story)
    code("    integral = clamp(integral + error*dt, -50, 50);", story)
    code("    derivative = (error - prevError) / dt;", story)
    code("    return Kp*error + Ki*integral + Kd*derivative;", story)
    code("}", story)
    story.append(PageBreak())

    new_slide("Versiyon 2 Detaylari", "Iyi uygulama ornegi", story)
    highlight("Low-Pass Filtre:", story)
    body("ALPHA=0.1 katsayisi ile gelen verinin sadece %10'unu "
         "alir, onceki degerin %90'unu korur. Bu, yuksek "
         "frekansli gurultuyu bastirir.", story)
    code("prevFiltered = 0.1 * raw + 0.9 * prevFiltered", story)
    note("Kucuk ALPHA = cok filtreleme (yavas tepki)", story)
    spacer(6, story)

    highlight("Integral Windup Korumasi:", story)
    body("Integral terimi +/-50 ile sinirlanmistir. Bu sayede "
         "uzun sureli doyma durumunda integral cok buyumez ve "
         "sistem hedefe yaklasinca hizli toparlanir.", story)
    code("integral = clamp(integral + error * dt, -50.0, 50.0);", story)
    spacer(6, story)

    highlight("dt Guvenlik Kontrolu:", story)
    body("dt <= 0 durumunda fonksiyon 0 doner. Bu, "
         "zamanlama hatasi durumunda motorun kontrolsuz "
         "kalkmasini engeller.", story)
    code("if (dt <= 0.0f) return 0.0f;", story)
    spacer(6, story)

    highlight("Test Senaryosu:", story)
    code("Sensor girdileri: {5.0, 3.2, 1.8, 0.5, 0.1}", story)
    code("Her adimda: filter -> PID -> motor komutu", story)
    code("dt = 10ms (100 Hz kontrol)", story)
    story.append(PageBreak())

    # ════════════════════════════════════════════
    # BOLUM 7 — SARTNAME KARSILAMA
    # ════════════════════════════════════════════
    section_slide("SARTNAME KARSILAMA MATRISI", "13 Gereksinim Analizi", 7, story)

    new_slide("Gereksinim Karsilama Tablosu", "Her sartname maddesinin yazilim karsiligi", story)
    req_rows = [
        ["1", "Azimuth 0-360° surekli donus", "Azimuth PID kontroloru\nURDF continuous joint\nKablo koruma (350° uyari)", "Tasarlandi"],
        ["2", "Elevasyon 0-90° hareket", "Elevation PID kontroloru\nLimit kontrolu (0-90)\nSoft/hard limit koruma", "Tasarlandi"],
        ["3", "Manuel mod", "Python GUI ManuelCommand\nROS 2 servis tasarimi\nDogrudan aci girisi", "Tasarlandi"],
        ["4", "Otomatik mod", "IMU+Kalman -> Stabilizasyon\nSGP4 -> Uydu konumu\nPID -> Motor komutu\nQPD -> Aktif takip", "Tasarlandi"],
        ["5", "IMU/Gyro stabilizasyon", "KalmanFilter1D/EKF\nQuaternion estimator\nStabilization controller\nX/Y itki mekanizmasi", "Tasarlandi"],
        ["6", "Lazer tabanli takip", "QPD hata vektoru\nAktif geri besleme PID\nBoresight hata kapama", "Tasarlandi"],
        ["7", "Hedefe tekrar yonelim 8 sn", "Lock state machine\nSpiral arama algoritmasi\nZaman hedefi ve metrik", "Tasarlandi"],
        ["8", "5 dk takip testi", "Dataset simulator (5 dk)\nGazebo test senaryosu\nCSV cikti analizi", "Tasarlandi"],
        ["9", "GPS manuel giris", "Python GUI enlem/boylam\nUydu yonelim hesabi\nVarsayilan: Ankara", "Tasarlandi"],
        ["10", "Turksat 4B/5A yonelim", "satellite_pointing.py\nJeostasyoner hesap\n50.0D ve 31.0D destegi", "Tasarlandi"],
        ["11", "Parametre kalici saklama", "JSON config dosyasi\nui_state.json\nKalibrasyon parametreleri", "Tasarlandi"],
        ["12", "Bilgisayar/tablet arayuzu", "Tkinter tabanli GUI\n820x560 pencere\nROS bridge", "Tasarlandi"],
        ["13", "CAD-Gazebo entegrasyonu", "mergen_description URDF\nMesh/STL hazirligi\nGazebo world dosyasi", "Tasarlandi"],
    ]
    story.append(tbl(
        ["#", "Gereksinim", "Yazilim Karsiligi", "Durum"],
        req_rows, [18, 100, 180, 45]))
    spacer(6, story)
    note("Not: Tum gereksinimler 'Tasarlandi' seviyesindedir. "
         "CAD modeli tamamlaninca dogrulama testleri yapilacaktir.", story)
    story.append(PageBreak())

    # ════════════════════════════════════════════
    # BOLUM 8 — PERFORMANS
    # ════════════════════════════════════════════
    section_slide("PERFORMANS & METRIKLER", "Hiz, Dogruluk, Kaynak Kullanimi", 8, story)

    new_slide("Performans Metrikleri", "Detayli sayisal degerler", story)
    perf_rows = [
        ["Ana dongu periyodu", "10 ms", "100 Hz kontrol", "Gercek zamanli"],
        ["EKF predict+update", "~1.2 ms", "7-durumlu EKF", "Dongunun %12'si"],
        ["SGP4 propagate", "~1.5 ms", "8 iterasyon Kepler", "Dongunun %15'i"],
        ["PID + guvenlik", "~0.2 ms", "Cift eksen + monitor", "Dongunun %2'si"],
        ["Toplam islem suresi", "~3.3 ms", "5 adim toplami", "%67 CPU"],
        ["Telemetri", "100 ms / 72 byte", "10 Hz, UART", "Dusuk yuk"],
        ["Kalman Q (process)", "0.01", "Surec gurultusu", "Ayar parametresi"],
        ["Kalman R (olcum)", "0.25", "Olcum gurultusu", "Ayar parametresi"],
        ["Dataset ornekleme", "100 Hz", "5 dk = 30K satir", "Dogrulama"],
        ["Dataset hareket", "+/-8 derece", "Roll/pitch sinus", "Senaryo"],
        ["QPD esik", "0.05", "Toplam sinyal", "Algila esigi"],
        ["PID PWM limit", "+/-1.0", "Normalize", "Cikis siniri"],
    ]
    story.append(tbl(
        ["Metrik", "Deger", "Aciklama", "Not"],
        perf_rows, [100, 65, 120, 70]))
    story.append(PageBreak())

    new_slide("Performans Goruntuleme", "Dongu suresi dagilimi", story)
    body("5 adimli kontrol dongusunun her bir adiminin "
         "ortalama islem suresi asagida gosterilmistir:", story)
    spacer(8, story)

    # Gorsel bar gosterimi (metin tabanli)
    bar_data = [
        ["Adim 2: Veri Toplama", "0.3ms", "###"],
        ["Adim 3a: EKF", "1.2ms", "############"],
        ["Adim 3b: SGP4", "1.5ms", "###############"],
        ["Adim 4: PID + Guv.", "0.2ms", "##"],
        ["Adim 5: Telemetri", "0.1ms", "#"],
        ["TOPLAM", "3.3ms", "#################################"],
        ["Kalan (bos)", "6.7ms", "##################################################"],
    ]
    rows = [[Paragraph(bar[0], styles["TC"]),
             Paragraph(bar[1], styles["TC"]),
             Paragraph(f'<font color="{C_PRIMARY.hexval()}">{bar[2]}</font>', styles["TC"])]
            for bar in bar_data]
    t = Table(rows, colWidths=[120, 50, 170])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, HexColor("#e0e0e0")),
    ]))
    story.append(t)
    story.append(Spacer(1, 8))
    note("Her dongude ~3.3ms islem + 6.7ms bos = 10ms toplam", story)
    story.append(PageBreak())

    # ════════════════════════════════════════════
    # BOLUM 9 — YOL HARITASI
    # ════════════════════════════════════════════
    section_slide("GELISTIRME YOL HARITASI", "KTR Hazirlik ve Ilerleme Plani", 9, story)

    new_slide("KTR Hazirlik Adimlari", "10 adimli plan", story)
    road_rows = [
        ["1", "Dataset dogrulama", "Kalman/PID parametre ayari", "YAPILDI"],
        ["2", "CAD -> Mesh export", "SolidWorks -> dae/stl", "Bekliyor"],
        ["3", "URDF/Xacro modeli", "Link/joint tanimlama", "Bekliyor"],
        ["4", "Gazebo sensor plugin", "IMU, joint state, motor", "Bekliyor"],
        ["5", "Stewart platform", "Roll/pitch/yaw bozucu", "Bekliyor"],
        ["6", "5 dk takip testi", "Gazebo otomatik test", "Bekliyor"],
        ["7", "8 sn yeniden kilitlenme", "Sinyal kesilme/kilit", "Bekliyor"],
        ["8", "Manuel/otomatik gecis", "Mod testleri", "Bekliyor"],
        ["9", "ROS -> Firmware", "Teensy/STM32 port", "Bekliyor"],
        ["10", "KTR raporu", "Dataset+Gazebo+donanim", "Bekliyor"],
    ]
    story.append(tbl(
        ["#", "Adim", "Detay", "Durum"],
        road_rows, [18, 110, 180, 45]))
    spacer(8, story)

    highlight("Gomulu Platform Entegrasyonu:", story)
    body("ROS 2 kontrol node'larindaki algoritmalarin gomulu "
         "platforma tasinmasi icin izlenecek adimlar:", story)
    bullet("C++ siniflari ROS 2 bagimliliklarindan arindirilir", story)
    bullet("HAL (Hardware Abstraction Layer) fonksiyonlari yazilir", story)
    bullet("FreeRTOS gorevleri: 100 Hz kontrol, 10 Hz telemetri", story)
    bullet("UART uzerinden GUI baglantisi kurulur", story)
    bullet("On bellek (stack) ve gercek zaman kisitlari dogrulanir", story)
    story.append(PageBreak())

    # ════════════════════════════════════════════
    # BOLUM 10 — SONUC
    # ════════════════════════════════════════════
    section_slide("SONUC VE DEGERLENDIRME", "Genel Degerlendirme ve Cikarimlar", 10, story)

    new_slide("Proje Durumu", "Su ana kadar yapilanlar", story)
    highlight("Kodlanmis ve Dogrulanmis Bilesenler:", story)
    bullet("5 adimli gomulu yazilim (C++) - Kerim", story)
    bullet("7-durumlu EKF ile quaternion sensor fuzyonu", story)
    bullet("SGP4 propagator ile TLE'den uydu konumu", story)
    bullet("Anti-windup, deadband, turev filtreli PID kontrolor", story)
    bullet("4 seviyeli guvenlik monitoru (SAFE/SOFT/HARD/FAULT)", story)
    bullet("72 byte telemetri paketi + CRC16 + komut kuyrugu", story)
    bullet("ROS 2 Humble kontrol node'lari (C++)", story)
    bullet("QPD lazer takip ve spiral arama algoritmalari", story)
    bullet("Gazebo Classic simulasyon altyapisi", story)
    bullet("Dataset tabanli dogrulama araci (Python)", story)
    bullet("Tkinter GUI: manuel/otomatik, uydu secimi, telemetri, parametre", story)
    bullet("Teensy/STM32 firmware referans kodu", story)
    bullet("13/13 sartname gereksinimi 'Tasarlandi' seviyesinde", story)
    story.append(PageBreak())

    new_slide("Proje Istatistikleri", "Sayilarla proje", story)
    stats_rows = [
        ["Toplam dosya sayisi", "~50+", "Kod, konfigurasyon, dokumantasyon"],
        ["Toplam kod satiri (tahmini)", "~10.000+", "C++ + Python"],
        ["C++ baslik dosyasi", "8 adet", "BTK Terminal (Kerim)"],
        ["ROS 2 paketi", "4 adet", "control, interfaces, gazebo, bringup"],
        ["ROS 2 mesaj tipi", "6 adet", "ImuFiltered, MotorCommand, vb."],
        ["ROS 2 servis", "3 adet", "SetMode, SetTarget, SaveParameters"],
        ["Dataset kapasitesi", "30.000 satir", "5 dk @ 100 Hz"],
        ["Telemetri paketi", "72 byte", "10 Hz -> 720 byte/s"],
        ["Kontrol frekansi", "100 Hz", "10 ms periyot"],
        ["PID parametresi", "14 adet", "Kp, Ki, Kd vs x 2 eksen"],
        ["Guvenlik seviyesi", "4 seviye", "SAFE -> SOFT -> HARD -> FAULT"],
        ["Hata kodu", "8 adet", "Bitfield ile yonetim"],
    ]
    story.append(tbl(
        ["Metrik", "Deger", "Aciklama"],
        stats_rows, [120, 65, 180]))
    story.append(PageBreak())

    new_slide("SONUC", "Genel Degerlendirme", story)
    story.append(Spacer(1, 20))
    body("UniS projesi, BTK Satellite Terminal Yarismasi "
         "kapsaminda Hareketli Uydu Terminali icin kapsamli "
         "bir yazilim altyapisi sunmaktadir.", story)
    spacer(8, story)
    highlight("Proje Yaklasimi:", story)
    body("CAD modeli tamamlanana kadar dataset tabanli dogrulama, "
         "CAD tamamlandiktan sonra Gazebo simulasyonu ve en son "
         "gomulu donanim entegrasyonu olmak uzere 3 asamali "
         "bir yol haritasi izlenmektedir.", story)
    spacer(8, story)
    highlight("Bir Sonraki Adim:", story)
    body("CAD modelinin tamamlanmasi ile Gazebo simulasyonunda "
         "tum sistemin dogrulanmasi ve ardindan gomulu donanim "
         "platformuna tasinmasi.", story)
    spacer(16, story)
    story.append(HRFlowable(width="60%", thickness=2,
                             color=C_PRIMARY, spaceBefore=6, spaceAfter=12))
    story.append(Paragraph("Tesekkurler", ParagraphStyle(
        "Thanks", fontName="Helvetica-Bold", fontSize=20,
        textColor=C_PRIMARY, alignment=TA_CENTER, leading=26)))
    story.append(Spacer(1, 6))
    story.append(Paragraph("UniS Yazilim Ekibi", ParagraphStyle(
        "Team", fontName="Helvetica", fontSize=14,
        textColor=C_GREY, alignment=TA_CENTER, leading=18)))
    story.append(Paragraph("Kerim, Efe, Elif, Simge", ParagraphStyle(
        "Names", fontName="Helvetica", fontSize=12,
        textColor=C_GREY, alignment=TA_CENTER, leading=16)))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"Hazirlanma Tarihi: {NOW}", ParagraphStyle(
        "Date", fontName="Helvetica", fontSize=10,
        textColor=C_GREY, alignment=TA_CENTER, leading=14)))

    return story


# ═══════════════════════════════════════════════════════════════
#  PDF OLUSTURMA
# ═══════════════════════════════════════════════════════════════

class UniSPresentation(BaseDocTemplate):
    def __init__(self, *args, **kwargs):
        BaseDocTemplate.__init__(self, *args, **kwargs)

    def afterPage(self):
        pass


doc = UniSPresentation(
    str(OUTPUT),
    pagesize=landscape(A4),
    leftMargin=MARGIN, rightMargin=MARGIN,
    topMargin=20*mm, bottomMargin=20*mm,
    title="UniS Hareketli Uydu Terminali - Sunum",
    author="UniS Yazilim Ekibi",
)

frame = Frame(
    MARGIN, 20*mm,
    PAGE_W - 2*MARGIN,
    PAGE_H - 40*mm,
    id='normal'
)

def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(C_GREY)
    canvas.drawCentredString(PAGE_W / 2, 12*mm,
        f"UniS Hareketli Uydu Terminali | Sayfa {doc.page}")
    canvas.drawString(MARGIN, 12*mm, f"{NOW}")
    canvas.drawRightString(PAGE_W - MARGIN, 12*mm,
        "BTK Satellite Terminal Yarismasi")
    canvas.restoreState()

doc.addPageTemplates([PageTemplate(id='main', frames=[frame], onPage=footer)])

story = build()
doc.build(story)
print(f"Sunum PDF olusturuldu: {OUTPUT.resolve()}")
