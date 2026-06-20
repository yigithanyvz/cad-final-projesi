#!/usr/bin/env python3
"""UniS Projesi Kapsamli PDF Rapor Uretici"""

from __future__ import annotations

from pathlib import Path
from datetime import datetime

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.colors import HexColor, black, white, grey
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer,
        Table, TableStyle, PageBreak, HRFlowable
    )
except ImportError as exc:
    raise SystemExit("PDF uretimi icin `pip install reportlab` calistirin.") from exc


OUTPUT = Path(__file__).with_name("UniS_Proje_Raporu.pdf")
NOW = datetime.now().strftime("%d.%m.%Y")

PRIMARY = HexColor("#1a237e")
SECONDARY = HexColor("#283593")
ACCENT = HexColor("#3949ab")
LIGHT_BG = HexColor("#e8eaf6")

PAGE_W, PAGE_H = A4

styles = getSampleStyleSheet()

styles.add(ParagraphStyle(
    "CoverTitle", fontName="Helvetica-Bold", fontSize=26,
    textColor=white, alignment=TA_CENTER, leading=32, spaceAfter=6))
styles.add(ParagraphStyle(
    "CoverSub", fontName="Helvetica", fontSize=14,
    textColor=HexColor("#bbdefb"), alignment=TA_CENTER, leading=18, spaceAfter=4))
styles.add(ParagraphStyle(
    "CoverInfo", fontName="Helvetica", fontSize=11,
    textColor=HexColor("#c5cae9"), alignment=TA_CENTER, leading=16))
styles.add(ParagraphStyle(
    "SectionTitle", fontName="Helvetica-Bold", fontSize=18,
    textColor=PRIMARY, alignment=TA_LEFT, leading=22, spaceBefore=20, spaceAfter=10))
styles.add(ParagraphStyle(
    "SubSection", fontName="Helvetica-Bold", fontSize=14,
    textColor=SECONDARY, alignment=TA_LEFT, leading=18, spaceBefore=14, spaceAfter=6))
styles.add(ParagraphStyle(
    "SubSub", fontName="Helvetica-Bold", fontSize=12,
    textColor=ACCENT, alignment=TA_LEFT, leading=15, spaceBefore=10, spaceAfter=4))
styles.add(ParagraphStyle(
    "Body", fontName="Helvetica", fontSize=10,
    textColor=black, alignment=TA_JUSTIFY, leading=14, spaceAfter=6))
styles.add(ParagraphStyle(
    "Mono", fontName="Courier", fontSize=8,
    textColor=HexColor("#212121"), alignment=TA_LEFT,
    leading=10, leftIndent=12, spaceAfter=4, spaceBefore=2,
    backColor=HexColor("#f5f5f5")))
styles.add(ParagraphStyle(
    "BulletItem", fontName="Helvetica", fontSize=10,
    textColor=black, alignment=TA_LEFT, leading=14,
    leftIndent=20, bulletIndent=8, spaceAfter=3))
styles.add(ParagraphStyle(
    "TableCell", fontName="Helvetica", fontSize=9,
    textColor=black, alignment=TA_LEFT, leading=12))
styles.add(ParagraphStyle(
    "TableHeader", fontName="Helvetica-Bold", fontSize=9,
    textColor=white, alignment=TA_CENTER, leading=12))
styles.add(ParagraphStyle(
    "Note", fontName="Helvetica-Oblique", fontSize=9,
    textColor=SECONDARY, alignment=TA_LEFT, leading=12,
    leftIndent=10, spaceAfter=6))


def _s(title, story):
    story.append(Paragraph(title, styles["SectionTitle"]))
    story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY, spaceBefore=6, spaceAfter=6))

def _ss(title, story):
    story.append(Paragraph(title, styles["SubSection"]))

def _sss(title, story):
    story.append(Paragraph(title, styles["SubSub"]))

def _b(text, story):
    story.append(Paragraph(text, styles["Body"]))

def _c(text, story):
    story.append(Paragraph(text.replace("\n", "<br/>"), styles["Mono"]))

def _li(text, story):
    story.append(Paragraph(text, styles["BulletItem"], bulletText="\u2022"))

def _note(text, story):
    story.append(Paragraph(text, styles["Note"]))

def _table(headers, rows, col_widths=None):
    data = [[Paragraph(h, styles["TableHeader"]) for h in headers]]
    for row in rows:
        data.append([Paragraph(str(c), styles["TableCell"]) for c in row])
    t = Table(data, colWidths=col_widths, repeatRows=1)
    cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#90caf9")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            cmds.append(("BACKGROUND", (0, i), (-1, i), LIGHT_BG))
    t.setStyle(TableStyle(cmds))
    return t


def build(story):
    # ── KAPAK ──
    story.append(Spacer(1, 60))
    story.append(Paragraph("UNIS", styles["CoverTitle"]))
    story.append(Paragraph("HAREKETLI UYDU TERMINALI", styles["CoverTitle"]))
    story.append(Spacer(1, 20))
    story.append(Paragraph("Proje Kapsamli Teknik Rapor", styles["CoverSub"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph(f"Hazirlanma Tarihi: {NOW}", styles["CoverInfo"]))
    story.append(Paragraph("BTK Satellite Terminal Yarismasi", styles["CoverInfo"]))
    story.append(Spacer(1, 12))
    story.append(HRFlowable(width="60%", thickness=2, color=HexColor("#bbdefb"), spaceBefore=6, spaceAfter=6))
    story.append(Spacer(1, 20))
    story.append(Paragraph("Yazilim Ekibi: Kerim, Efe, Elif, Simge", styles["CoverInfo"]))
    story.append(Paragraph("ROS 2 Humble | Gazebo Classic | C++ | Python | Tkinter", styles["CoverInfo"]))
    story.append(PageBreak())

    # ── ICINDEKILER ──
    _s("Icerik", story)
    toc = [
        "1. Proje Genel Bakis",
        "2. Proje Dizin Yapisi",
        "3. Bilesen 1 - Gomulu Yazilim (Kerim)",
        "   3.1 5 Adimli Yazilim Mimarisi",
        "   3.2 Baslatma ve Kalibrasyon",
        "   3.3 Veri Toplama Katmani",
        "   3.4 Sensor Fuzyonu & EKF",
        "   3.5 SGP4 Uydu Propagatoru",
        "   3.6 PID Kontrol & Guvenlik",
        "   3.7 Telemetri & Haberlesme",
        "4. Bilesen 2 - ROS 2 & Gazebo (Efe)",
        "   4.1 ROS 2 Kontrol Node'lari",
        "   4.2 PID Kontroller (C++)",
        "   4.3 Stabilizasyon Kontrolor",
        "   4.4 QPD Lazer Takip",
        "   4.5 Spiral Arama Algoritmasi",
        "   4.6 Gazebo Simulasyonu",
        "   4.7 Dataset Dogrulama Araci",
        "   4.8 Gomulu Yazilim Referansi",
        "5. Bilesen 3 - Python Arayuz",
        "   5.1 Tkinter GUI",
        "   5.2 Uydu Yonelim Hesaplama",
        "   5.3 ROS Bridge",
        "6. Bilesen 4 - Stabilizasyon Ornegi (Simge/Elif)",
        "7. Sartname Karsilama Matrisi",
        "8. Performans Metrikleri",
        "9. Gelistirme Yol Haritasi",
        "10. Sonuc ve Degerlendirme",
    ]
    for item in toc:
        st = styles["Code"] if item.startswith("   ") else styles["Body"]
        story.append(Paragraph(item, st))
    story.append(PageBreak())

    # ═══ 1. GENEL BAKIS ═══
    _s("1. Proje Genel Bakis", story)
    _b(
        "UniS projesi, BTK Satellite Terminal Yarismasi kapsaminda "
        "gelistirilen bir Hareketli Uydu Terminali (SOTM) yazilim "
        "sistemidir. Amac, hareketli bir platform uzerindeki antenin, "
        "platform hareket halindeyken bir haberlesme uydusuna "
        "kilitli kalmasini saglamaktir.", story)
    _b(
        "Sistem; IMU/Gyro sensor fuzyonu, quaternion tabanli yonelim "
        "kestirimi, PID kontrol, SGP4 uydu konum propagasyonu, lazer/"
        "QPD aktif geri besleme ve spiral arama algoritmalarini "
        "icerir. Dort ana bilesenden olusur:", story)
    _li("<b>Gomulu Yazilim (Kerim):</b> STM32/Teensy uzerinde 5 adimli "
        "gercek zamanli kontrol dongusu (C++)", story)
    _li("<b>ROS 2 &amp; Gazebo (Efe):</b> ROS 2 Humble kontrol node'lari "
        "ve Gazebo Classic simulasyonu (C++/Python)", story)
    _li("<b>Python Arayuz:</b> Tkinter tabanli kullanici arayuzu "
        "(manuel/otomatik mod, uydu yonelimi, telemetri)", story)
    _li("<b>Stabilizasyon Ornegi (Simge/Elif):</b> C++ PID + low-pass "
        "filtre referans kodu", story)
    story.append(Spacer(1, 6))

    _ss("Sistem Mimari Semasi", story)
    arch = [
        "+------------------+    +------------------+    +------------------+",
        "|   ALGILAMA       |    |   KESTIRIM       |    |   KONTROL        |",
        "|  IMU  Gyro       |--->|  Kalman Filtre   |--->|  Stabilizasyon   |",
        "|  GPS  Encoder    |    |  Quaternion      |    |  Azimuth PID     |",
        "|  QPD/Lazer       |    |  SGP4 Propagator |    |  Elevasyon PID   |",
        "|  Limit Switch    |    |  Koord. Donusum  |    |  Lazer Takip PID |",
        "+------------------+    +------------------+    +--------+---------+",
        "                                                          |",
        "                                                          v",
        "                                +------------------+    +------------------+",
        "                                |   ARAYUZ (GUI)   |    |   MOTORLAR      |",
        "                                |  Manuel/Otomatik |    |  Azimut Motor   |",
        "                                |  Uydu Secimi    |    |  Elevasyon Motor|",
        "                                |  GPS Girisi     |    |  X/Y Itki       |",
        "                                |  Telemetri      |    +------------------+",
        "                                |  Parametre Kaydi|",
        "                                +------------------+",
    ]
    for line in arch:
        _c(line, story)
    story.append(PageBreak())

    # ═══ 2. DIZIN YAPISI ═══
    _s("2. Proje Dizin Yapisi", story)
    _b("Proje dosya yapisi asagida gosterilmistir.", story)
    story.append(Spacer(1, 4))
    _table(
        ["Dizin/Dosya", "Aciklama", "Sorumlu"],
        [
            ["unis/", "Kok dizin", "-"],
            ["  kerim unis/", "Gomulu yazilim (BTK Terminal)", "Kerim"],
            ["    BTK_Satellite_Terminal/include/", "8 C++ baslik dosyasi", "Kerim"],
            ["    BTK_Satellite_Terminal/src/", "main.cpp ve diger kaynaklar", "Kerim"],
            ["  Efe/", "ROS 2, Gazebo, dataset, firmware", "Efe"],
            ["    mergen_ws/src/mergen_control/", "Kontrol node'lari (C++)", "Efe"],
            ["    mergen_ws/src/mergen_interfaces/", "Ozel mesaj/servis tanimlari", "Efe"],
            ["    mergen_ws/src/mergen_gazebo/", "Gazebo world & launch", "Efe"],
            ["    mergen_ws/src/mergen_bringup/", "Sistem baslatma", "Efe"],
            ["    firmware_reference/", "Teensy/STM32 referans", "Efe"],
            ["    tools/dataset_simulator.py", "Dataset dogrulama araci", "Efe"],
            ["    reports/", "PDF rapor uretimi (OTR)", "Efe"],
            ["    datasets/", "Ornek CSV datasetleri", "Efe"],
            ["  arayuz/", "Tkinter kullanici arayuzu", "Ekip"],
            ["    core/satellite_pointing.py", "Uydu yonelim hesabi", "Ekip"],
            ["    ros_bridge/client.py", "ROS 2 istemcisi", "Ekip"],
            ["  simge_elif/", "Stabilizasyon C++ ornegi", "Simge/Elif"],
            ["  run_windows_*.bat", "Windows scriptleri", "Ekip"],
        ],
        [120, 280, 60])
    story.append(PageBreak())

    # ═══ 3. KERIM ═══
    _s("3. Bilesen 1 - Gomulu Yazilim (Kerim)", story)
    _b(
        "STM32 veya Teensy icin 5 adimli kontrol dongusu. FreeRTOS "
        "veya bare-metal. 8 baslik dosyasi + main.cpp.", story)

    _ss("3.1 5 Adimli Yazilim Mimarisi", story)
    _table(
        ["Adim", "Islev", "Detay", "Dosya", "Periyot"],
        [
            ["1", "Baslatma ve Kalibrasyon", "Donanim testi, homing, IMU kalibrasyonu",
             "initialization.h", "1 kez"],
            ["2", "Veri Toplama", "IMU 100Hz, GPS 1Hz, Encoder, UART",
             "main.cpp", "10 ms"],
            ["3", "Sensor Fuzyonu & Koord.", "EKF, SGP4, platform tilt telafisi",
             "SensorFusion.h, SatelliteTracker.h", "10 ms"],
            ["4", "PID Kontrol", "Az/El PID, anti-windup, deadband, guvenlik",
             "PIDController.h", "10 ms"],
            ["5", "Telemetri", "72 byte UART paketi, CRC16, komut kuyrugu",
             "telemetry.h", "100 ms"],
        ],
        [35, 100, 150, 100, 45])
    story.append(Spacer(1, 4))
    _c("Toplam: ~3.3 ms (hedef 10 ms) -> %67 CPU", story)
    story.append(Spacer(1, 4))

    _ss("3.2 Baslatma ve Kalibrasyon (Adim 1)", story)
    _b("Sistem acilista uc adim gerceklestirir:", story)
    _li("<b>HardwareSelfTest:</b> IMU (MPU-6050), GPS, motor, encoder "
        "testi. IMU yer cekimi 9.8+/-2 m/s² tolerans.", story)
    _li("<b>HomingProcedure:</b> CW limit switch -> CCW 2 derece -> "
        "encoder=0. 15 sn timeout.", story)
    _li("<b>IMUCalibration:</b> 500 ornek (5 sn). Gyro bias=ortalama, "
        "accel bias=normalize g vektorunden cikarma.", story)
    _b("Basarisizlik durumunda sistem ERROR moduna alinir.", story)

    _ss("3.3 Veri Toplama Katmani (Adim 2)", story)
    _table(
        ["Sensor", "Frekans", "Veri"],
        [
            ["IMU (MPU-6050)", "100 Hz", "accel (m/s²), gyro (rad/s)"],
            ["GPS (NMEA)", "1 Hz", "LLA, HDOP, hiz, yon"],
            ["Encoder", "100 Hz", "az_deg, el_deg, hiz (dps)"],
            ["Limit Switch", "Her dongu", "Min/max bool"],
            ["UART Komut", "Olay bazli", "8 elemanli FIFO kuyruk"],
        ],
        [100, 60, 220])
    _b("IMU'ya kalibrasyon bias'i uygulanir. GPS sadece HDOP < 5m "
       "ise isleme alinir.", story)

    _ss("3.4 Sensor Fuzyonu &amp; EKF (Adim 3A)", story)
    _b("7-durumlu Extended Kalman Filter:", story)
    _c("x = [q0, q1, q2, q3,  bx, by, bz]   (quaternion + gyro bias)", story)
    _b("<b>Predict:</b> q_dot = 0.5*Omega(w_corrected)*q. 7x7 Jacobian "
       "ile kovaryans yayilimi.", story)
    _b("<b>Update:</b> Ivmeolcer: h(x)=R(q)*[0,0,g]^T. Ivme buyuklugu "
       "yer cekiminden %30 saparsa guncelleme atlanir.", story)
    _b("Euler acilarina donusum: ZYX sirasi. Kovaryans izi < 0.005 "
       "ise yakinsama kabul edilir.", story)

    _ss("3.5 SGP4 Uydu Propagatoru (Adim 3B)", story)
    _b("TLE -> ECI -> ECEF -> Az/El:", story)
    _c("TLE -> parse() -> init() -> propagate(JD) -> ECI", story)
    _c("-> eciToECEF() -> calcAzEl() -> Az/El acilari", story)
    _b("Koordinat donusumleri:", story)
    _li("ECI->ECEF: Greenwich Sidereal Time", story)
    _li("ECEF->LLA: WGS-84, Bowring iterasyonu (5 iterasyon)", story)
    _li("LLA->Az/El: NED cercevesi", story)
    _li("<b>Platform Tilt Telafisi (3C):</b> R = Ry(pitch)*Rx(roll) "
        "ile uydu Az/El duzeltmesi", story)

    _ss("3.6 PID Kontrol ve Guvenlik (Adim 4)", story)
    _table(
        ["Parametre", "Azimut", "Elevasyon"],
        [
            ["Kp", "2.5", "3.0"],
            ["Ki", "0.1", "0.08"],
            ["Kd", "0.3", "0.25"],
            ["Max Integral", "20.0", "15.0"],
            ["Deadband", "+/-0.1 derece", "+/-0.1 derece"],
            ["Turev Filtre (alpha)", "0.7", "0.7"],
            ["Max Hiz", "60 dps", "30 dps"],
        ],
        [100, 80, 80])
    _b("Ozellikler: Anti-windup, EMA turev filtreleme, deadband, "
       "aci sarmalama (azimut).", story)
    _b("Guvenlik: SAFE -> SOFT (%50 hiz) -> HARD (durdur) -> "
       "FAULT (acil). Kablo koruma (350 derece).", story)

    _ss("3.7 Telemetri ve Haberlesme (Adim 5)", story)
    _b("10 Hz, 72 byte, UART 115200 baud:", story)
    _table(
        ["Alan", "Byte", "Aciklama"],
        [
            ["Magic (0xABCD)", "2", "Paket basligi"],
            ["Timestamp", "4", "Zaman damgasi (ms)"],
            ["State + Errors", "3", "8 durum, 8 hata kodu"],
            ["GPS (lat/lon/alt)", "12", "WGS-84 koordinatlari"],
            ["Yonelim (r/p/y)", "12", "EKF Euler acilari"],
            ["Encoder (az/el)", "8", "Gercek motor konumu"],
            ["Hedef (az/el)", "8", "Setpoint acilari"],
            ["Hata (az/el)", "8", "Takip hatasi"],
            ["Uydu (az/el/menzil)", "12", "SGP4 ciktisi"],
            ["RSSI + CRC16", "3", "Sinyal + dogrulama"],
        ],
        [110, 35, 180])
    _b("Komutlar: SET_AUTO_MODE, SET_MANUAL, MANUAL_AZ, MANUAL_EL, "
       "LOAD_TLE, HOME, EMERGENCY_STOP.", story)
    story.append(PageBreak())

    # ═══ 4. EFE ═══
    _s("4. Bilesen 2 - ROS 2 &amp; Gazebo (Efe)", story)
    _b("ROS 2 Humble + Gazebo Classic 11. Kontrol node'lari, ozel "
       "mesajlar, simulasyon altyapisi ve dataset araci.", story)

    _ss("4.1 ROS 2 Kontrol Node'lari", story)
    _b("Ana node (control_node.cpp) 100 Hz'de calisir:", story)
    _table(
        ["Topic", "Mesaj", "Aciklama"],
        [
            ["/mergen/imu_filtered", "ImuFiltered", "IMU roll/pitch"],
            ["/mergen/motor_state", "MotorState", "Encoder konumu"],
            ["/mergen/target_angles", "TargetAngles", "Hedef acilari"],
            ["/mergen/motor_command (pub)", "MotorCommand", "PWM + stabilizasyon"],
        ],
        [135, 85, 160])

    _ss("4.2 PID Kontroller (C++)", story)
    _table(
        ["Sinif", "Dosya", "Islev"],
        [
            ["PidController", "pid_controller.cpp", "Genel PID, clamp"],
            ["StabilizationController", "stabilization_controller.cpp",
             "Roll/pitch -> X/Y itki"],
            ["QpdTracker", "qpd_tracker.cpp", "Lazer hata vektoru"],
            ["SpiralSearch", "spiral_search.cpp", "Hedef kaybi arama"],
        ],
        [100, 100, 180])
    _c("Azimuth PID: Kp=2.0, Ki=0.02, Kd=0.15, cikis [-1,1]", story)
    _c("Elevasyon PID: Kp=2.2, Ki=0.02, Kd=0.16, cikis [-1,1]", story)
    _c("Stab X/Y: Kp=1.6, Ki=0.01, Kd=0.10, cikis [-1,1]", story)

    _ss("4.3 Stabilizasyon Kontrolor", story)
    _b("EKF roll/pitch -> PID (hedef=0) -> mm_per_degree -> "
       "X/Y itki komutu. Platform sarsintilarini aktif bastirir.", story)

    _ss("4.4 QPD Lazer Takip", story)
    _b("QPD A/B/C/C bolge akimlarindan hata vektoru:", story)
    _c("ex = ((A+D) - (B+C)) / (A+B+C+D)", story)
    _c("ey = ((A+B) - (C+D)) / (A+B+C+D)", story)
    _b("Toplam sinyal threshold altinda ise hedefte degil. "
       "Hata vektoru Az/El offset'i olarak uygulanir.", story)

    _ss("4.5 Spiral Arama Algoritmasi", story)
    _b("Lazer hedefi yakalayamazsa devreye girer:", story)
    _c("radius(t) = min(max_radius, radial_speed * t)", story)
    _c("offset_az = radius * cos(angular_speed * t)", story)
    _c("offset_el = radius * sin(angular_speed * t)", story)

    _ss("4.6 Gazebo Simulasyonu", story)
    _b("Gazebo Classic 11 + ROS 2 Humble:", story)
    _li("World: 4m menzil, 2m yukseklik, 30 derece elevasyon", story)
    _li("Hedef: kirmizi silindir (radius 0.5m)", story)
    _li("Controller: joint_state_broadcaster @ 100 Hz", story)
    _li("System modlari: manual, automatic, search, safe", story)
    _b("CAD hazir olunca URDF/Xacro: azimuth continuous, "
       "elevasyon revolute (0-90), stabilizasyon prismatic.", story)

    _ss("4.7 Dataset Dogrulama Araci", story)
    _b("CAD oncesi algoritma dogrulama:", story)
    _li("Uretim: 5 dk, 100 Hz, roll/pitch +/-8 derece sinus", story)
    _li("Gurultu: Gaussian (sigma=0.18), QPD sinusoidal hata", story)
    _li("Isleme: Kalman (Q=0.01, R=0.25) + PID + QPD", story)
    _li("Cikti: Filtrelenmis IMU, QPD hata, PWM, kilit durumu", story)
    _c("python dataset_simulator.py --generate --output motion.csv", story)
    _c("python dataset_simulator.py --input motion.csv --output result.csv", story)

    _ss("4.8 Gomulu Yazilim Referansi", story)
    _b("firmware_reference/teensy_stm32_cpp/: KalmanFilter1D, "
       "PidController ve 100 Hz kontrol dongusu ornegi. ROS 2 "
       "algoritmalarinin gomulu platforma tasimmasi icin referans.", story)
    story.append(PageBreak())

    # ═══ 5. ARAYUZ ═══
    _s("5. Bilesen 3 - Python Arayuz", story)
    _b("Tkinter tabanli GUI. ROS 2 yoksa simulasyon modu.", story)

    _ss("5.1 Tkinter GUI", story)
    _b("820x560 pencere, 4 ana bolum:", story)
    _table(
        ["Bolum", "Bilesenler", "Islev"],
        [
            ["Komut ve Mod", "Radio (Oto/Manuel), Entry (az/el), Button",
             "Mod secimi, manuel hedef"],
            ["Uydu Yonelimi", "Entry (enlem/boylam), Combo (Turksat 4B/5A), Button",
             "Az/El hesaplama"],
            ["Telemetri", "Text widget (12 satir)",
             "Durum mesajlari"],
            ["Alt Butonlar", "Kaydet, Guvenli Mod",
             "JSON konfigurasyon"],
        ],
        [80, 140, 140])
    _b("ui_state.json ile durum kaydi. Elevasyon 0-90 siniri.", story)

    _ss("5.2 Uydu Yonelim Hesaplama", story)
    _b("Jeostasyoner uydu hesaplama:", story)
    _c("delta_lon = satellite_lon - observer_lon", story)
    _c("elevation = atan(  (cos(lat)*cos(dlon) - R_e/R_g)", story)
    _c("               / sqrt(1 - (cos(lat)*cos(dlon))^2)  )", story)
    _c("azimuth = atan2(sin(dlon), -sin(lat)*cos(dlon))", story)
    _b("Destek: Turksat 4B (50.0D), Turksat 5A (31.0D). "
       "Varsayilan: Ankara (39.92K, 32.85D).", story)

    _ss("5.3 ROS Bridge", story)
    _b("MergenRosClient: set_mode(), send_manual_target(), "
       "save_parameters(). ROS 2 Humble'da rclpy ile genisletilecek.", story)
    story.append(PageBreak())

    # ═══ 6. SIMGE/ELIF ═══
    _s("6. Bilesen 4 - Stabilizasyon Ornegi (Simge/Elif)", story)
    _b("simge_elif/x.cpp iki versiyon:", story)
    _li("<b>Ilk (yorum):</b> Basit PID (Kp=2.0, Ki=0.5, Kd=0.1), "
        "sabit 0.95 carpanli filtre, windup korumasi yok.", story)
    _li("<b>Guncel:</b> Low-pass (alpha=0.1), dt parametreli PID, "
        "integral clamp (+/-50), reset(), Windows UTF-8 destegi.", story)
    story.append(PageBreak())

    # ═══ 7. SARTNAME ═══
    _s("7. Sartname Karsilama Matrisi", story)
    _table(
        ["Gereksinim", "Yazilim Karsiligi", "Durum"],
        [
            ["Azimuth 0-360 surekli", "Azimuth PID + URDF continuous joint", "Tasarlandi"],
            ["Elevasyon 0-90", "Elevation PID + limit kontrolu", "Tasarlandi"],
            ["Manuel mod", "Python GUI + ROS servis", "Tasarlandi"],
            ["Otomatik mod", "EKF + QPD + PID + state machine", "Tasarlandi"],
            ["IMU/Gyro stabilizasyon", "Kalman + stabilization controller", "Tasarlandi"],
            ["Lazer takip", "QPD hata vektoru + PID", "Tasarlandi"],
            ["8 sn yeniden kilitlenme", "Lock state machine", "Tasarlandi"],
            ["5 dk takip testi", "Dataset + Gazebo senaryosu", "Tasarlandi"],
            ["GPS manuel giris", "GUI uydu yonelim hesabi", "Tasarlandi"],
            ["Turksat 4B/5A yonelim", "satellite_pointing.py", "Tasarlandi"],
            ["Parametre kaydi", "JSON config", "Tasarlandi"],
            ["Bilgisayar/tablet arayuzu", "Tkinter GUI", "Tasarlandi"],
            ["CAD-Gazebo entegrasyonu", "mergen_description URDF", "Tasarlandi"],
        ],
        [115, 190, 60])
    _note("Not: Tum gereksinimler 'Tasarlandi' seviyesinde. "
          "CAD tamamlaninca dogrulama yapilacak.", story)
    story.append(PageBreak())

    # ═══ 8. PERFORMANS ═══
    _s("8. Performans Metrikleri", story)
    _table(
        ["Metrik", "Deger", "Aciklama"],
        [
            ["Ana dongu periyodu", "10 ms", "100 Hz"],
            ["EKF predict+update", "~1.2 ms", "7-durumlu EKF"],
            ["SGP4 propagate", "~1.5 ms", "8 iterasyon Newton-Raphson"],
            ["PID + guvenlik", "~0.2 ms", "Cift eksen"],
            ["Toplam sure", "~3.3 ms", "%67 CPU"],
            ["Telemetri", "100 ms / 72 byte", "10 Hz, UART"],
            ["Dataset", "100 Hz / 5 dk", "30.000 satir"],
            ["Hareket genligi", "+/-8 derece", "Roll/pitch sinus"],
        ],
        [120, 70, 130])
    story.append(PageBreak())

    # ═══ 9. YOL HARITASI ═══
    _s("9. Gelistirme Yol Haritasi", story)
    _table(
        ["#", "Adim", "Detay", "Durum"],
        [
            ["1", "Dataset dogrulama", "Kalman/PID parametre ayari", "Yapilabilir"],
            ["2", "CAD -> Mesh export", "SolidWorks dae/stl", "Bekliyor"],
            ["3", "URDF/Xacro model", "Link/joint tanimlama", "Bekliyor"],
            ["4", "Gazebo plugin", "IMU, motor kontrol", "Bekliyor"],
            ["5", "Stewart platform", "Roll/pitch/yaw bozucu", "Bekliyor"],
            ["6", "5 dk takip testi", "Gazebo otomatik test", "Bekliyor"],
            ["7", "8 sn yeniden kilit", "Sinyal kesilme testi", "Bekliyor"],
            ["8", "Manuel/otomatik mod", "Mod gecis testleri", "Bekliyor"],
            ["9", "ROS -> Firmware", "Teensy/STM32 arayuzu", "Bekliyor"],
            ["10", "KTR raporu", "Dataset+Gazebo+donanim", "Bekliyor"],
        ],
        [20, 110, 200, 60])

    _sss("Gomulu Platform Entegrasyonu", story)
    _b("ROS 2 algoritmalari -> Teensy/STM32:", story)
    _li("C++ siniflari ROS bagimliliklarindan arindirilir", story)
    _li("HAL fonksiyonlari yazilir", story)
    _li("FreeRTOS gorevleri: 100 Hz kontrol, 10 Hz telemetri", story)
    _li("UART uzerinden GUI baglantisi", story)
    story.append(PageBreak())

    # ═══ 10. SONUC ═══
    _s("10. Sonuc ve Degerlendirme", story)
    _b("UniS projesi su ana kadar:", story)
    _li("5 adimli gomulu yazilim (C++) tasarlanip kodlandi", story)
    _li("7-durumlu EKF ile quaternion sensor fuzyonu gerceklesti", story)
    _li("SGP4 propagatoru ile TLE -> uydu konumu hesaplaniyor", story)
    _li("Anti-windup, deadband, turev filtreli PID hazir", story)
    _li("ROS 2 Humble node'lari ve Gazebo altyapisi kuruldu", story)
    _li("QPD lazer takip ve spiral arama algoritmalari tasarlandi", story)
    _li("Dataset dogrulama araci ile CAD oncesi test yapilabiliyor", story)
    _li("Tkinter GUI (manuel/otomatik, uydu secimi, telemetri, parametre) hazir", story)
    _li("Tum sartname gereksinimleri 'Tasarlandi' seviyesinde", story)
    story.append(Spacer(1, 8))
    _b("Sonraki adim: CAD modeli ile Gazebo dogrulama, ardindan "
       "gomulu donanim platformuna tasima.", story)
    story.append(Spacer(1, 16))
    story.append(HRFlowable(width="100%", thickness=2, color=PRIMARY, spaceBefore=6, spaceAfter=6))
    story.append(Spacer(1, 8))
    _b(f"Rapor Tarihi: {NOW}", story)
    _b("Hazirlayan: UniS Yazilim Ekibi (Kerim, Efe, Elif, Simge)", story)

    return story


doc = SimpleDocTemplate(
    str(OUTPUT), pagesize=A4,
    leftMargin=20*mm, rightMargin=20*mm,
    topMargin=20*mm, bottomMargin=20*mm,
    title="UniS Hareketli Uydu Terminali - Proje Raporu",
    author="UniS Yazilim Ekibi",
)

story = build([])


def add_page_number(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(grey)
    canvas.drawCentredString(PAGE_W / 2, 12*mm,
        f"UniS Hareketli Uydu Terminali | Sayfa {doc.page}")
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(HexColor("#90caf9"))
    canvas.drawString(20*mm, PAGE_H - 12*mm, "UniS Proje Raporu")
    canvas.drawRightString(PAGE_W - 20*mm, PAGE_H - 12*mm,
        f"BTK Satellite Terminal Yarismasi | {NOW}")
    canvas.restoreState()


doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
print(f"PDF olusturuldu: {OUTPUT.resolve()}")
