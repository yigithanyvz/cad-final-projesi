# Mergen Sistemi — Mimarî Akış Diyagramı

```mermaid
flowchart TB
    subgraph KULLANICI["KULLANICI ARAYÜZÜ (Python Tkinter)"]
        GUI["Mergen GUI"]
        CONN["Bağlantı Paneli<br/>Serial / ESP32"]
        CTRL["Kontrol Paneli<br/>Başlat / Durdur / Acil"]
        TARGET["Hedef Paneli<br/>GPS + Manuel + Uydu"]
        TEL["Telemetri Paneli<br/>Az/El/Roll/Pitch/Kilit"]
        LASER_G["Lazer Ofset Grafiği<br/>(matplotlib canlı)"]
        LOG["Sistem Mesajları"]
    end

    subgraph ILETISIM["HABERLEŞME KATMANI"]
        PROTO["JSON-Line Protokolü<br/>{type,action,data}"]
        SERIAL["Serial (USB/UART)<br/>115200 baud"]
        ESP32["ESP32 WiFi (TCP)<br/>Port 5000"]
    end

    subgraph TEENSY["TEENSY 4.x (GÖMÜLÜ SİSTEM)"]
        MAIN["Ana Kontrol Döngüsü<br/>100 Hz"]
        HUSKY["HuskyLens I2C/UART<br/>→ Hedef (x,y,w,h)"]
        LASER["Lazer PWM Kontrol"]
        MOTOR["Step Motor Sürücü<br/>Azimuth + Elevasyon"]
        ENC["Encoder Okuma<br/>Manyetik / Optik"]
        PID["PID Kontrol<br/>Az + El + Lazer"]
        STATE_M["Durum Makinesi<br/>IDLE/AUTO/MANUAL/ERROR"]
    end

    subgraph MOTORLAR["MOTOR SİSTEMİ"]
        AZ_M["Azimuth Step Motor<br/>Planet Dişli / Worm Gear<br/>Sürekli 0-360°"]
        EL_M["Elevasyon Step Motor<br/>Worm Gear (Kendinden Kilitli)<br/>0-90°"]
        MULTI["Multi-Step Motor<br/>(Alt Kısım)"]
        SINGLE["Single Step Motor<br/>(Diğer Eksenler)"]
    end

    subgraph SENSORLER["SENSÖRLER"]
        IMU["IMU (MPU-6050/ICM-20948)<br/>İvmeölçer + Jiroskop<br/>100 Hz"]
        GPS["GPS Modülü<br/>1 Hz Güncelleme"]
        LIMIT["Limit Switch'ler<br/>Az + El"]
    end

    subgraph ENERJI["GÜÇ YÖNETİMİ"]
        PWR["Güç Kaynağı"]
        RELAY["Röle / MOSFET<br/>Sistem Anahtarı"]
        PWR_SEQ["Sıralı Enerji<br/>Önce GUI → Sonra Sistem"]
    end

    %% Bağlantılar
    GUI --> CONN
    GUI --> CTRL
    GUI --> TARGET
    GUI --> TEL
    GUI --> LASER_G
    GUI --> LOG

    CONN --> SERIAL
    CONN --> ESP32
    SERIAL <--> PROTO
    ESP32 <--> PROTO
    PROTO <--> MAIN

    MAIN <--> HUSKY
    MAIN --> LASER
    MAIN --> MOTOR
    MAIN <--> ENC
    MAIN <--> PID
    MAIN <--> STATE_M

    MOTOR --> AZ_M
    MOTOR --> EL_M
    AZ_M --> MULTI
    EL_M --> SINGLE

    MAIN <--> IMU
    MAIN <--> GPS
    MAIN <--> LIMIT

    PWR --> RELAY
    RELAY --> TEENSY
    RELAY --> MOTORLAR
    RELAY --> SENSORLER

    GUI -. "Enerji kontrol" .-> RELAY
```

## SİSTEM ÇALIŞMA AKIŞI

```mermaid
sequenceDiagram
    participant K as Kullanıcı
    participant G as GUI (Python)
    participant C as İletişim (Serial/ESP32)
    participant T as Teensy
    participant H as HuskyLens
    participant M as Motorlar

    Note over K,M: 1. ENERJİ VERME
    K->>G: Bilgisayarı aç
    G->>G: GUI otomatik başlar
    Note over G: Sistem BEKLEMEDE — motorlara enerji yok

    K->>G: COM Port seç / ESP32 IP gir
    K->>G: "SİSTEMİ BAŞLAT" butonuna bas
    G->>C: {"type":"cmd","action":"start"}
    C->>T: start komutu (Serial/WiFi)
    T->>T: Röle/MOSFET ile enerjiyi aç
    T->>T: Donanım öz-testi çalıştır

    Note over T: IMU test, GPS test, motor test, encoder test

    alt Test başarısız
        T->>C: {"type":"error","msg":"Donanım hatası!"}
        C->>G: Hata mesajı göster
        G->>K: Kullanıcıya hata bildirimi
    else Test başarılı
        T->>C: {"type":"ack","status":"ready"}
        C->>G: Sistem hazır
        G->>K: ✅ Sistem hazır — BEKLEMEDE
    end

    Note over K,M: 2. MOD SEÇİMİ

    K->>G: Mod seç: OTOMATİK veya MANUEL
    G->>C: {"type":"cmd","action":"set_mode","mode":"auto"}
    C->>T: Mod komutu

    alt OTOMATİK MOD
        K->>G: GPS koordinatları gir + Uydu seç
        G->>G: Az/El hesapla (calculate_look_angles)
        G->>C: {"type":"cmd","action":"set_gps","lat":39.9,"lon":32.8}
        G->>C: {"type":"cmd","action":"set_target","az":152.3,"el":42.1}
        C->>T: Hedef açıları gönder
        T->>H: Hedef takibi başlat
        H->>T: (x,y,w,h) verisi — sürekli
        T->>T: PID kontrol: Az + El motor
        T->>M: Step motor sürücü sinyalleri
        M->>M: Anteni hedefe yönelt
        T->>C: {"type":"tel","state":3,"az_act":152.1,...} — 10 Hz
        C->>G: Telemetriyi göster + grafiği güncelle
        G->>K: Canlı Az/El + Lazer ofset + Kilit durumu
    else MANUEL MOD
        K->>G: Azimuth (°) + Elevasyon (°) gir
        G->>C: {"type":"cmd","action":"set_target","az":90.0,"el":45.0}
        C->>T: Hedef açı
        T->>M: Motorları hedefe sür
    end

    Note over K,M: 3. LAZER TAKİP
    H->>T: Hedef (x_center, y_center)
    T->>T: Lazer ofset = hedef - merkez
    T->>T: PID ile lazeri hedefe kilitle
    T->>C: {"laser_x":0.05,"laser_y":-0.03,"locked":true}
    C->>G: Grafiği güncelle

    Note over K,M: 4. ACİL DURUM
    K->>G: 🚨 ACİL DURDURMA butonu
    G->>C: {"type":"cmd","action":"emergency_stop"}
    C->>T: Acil dur komutu
    T->>M: Motorları durdur (ENABLE=0)
    T->>T: Röle ile enerjiyi kes
    T->>C: {"type":"ack","status":"emergency_stopped"}
```

## ONAYLI VERİ AKIŞI (JSON-Line Protokolü)

```mermaid
flowchart LR
    subgraph TX["GUI → Teensy Komutları"]
        C1["START<br/>{type:cmd, action:start}"]
        C2["STOP<br/>{type:cmd, action:stop}"]
        C3["SET_MODE<br/>{mode:auto/manual}"]
        C4["SET_TARGET<br/>{az:120.0, el:30.0}"]
        C5["SET_GPS<br/>{lat:39.9, lon:32.8}"]
        C6["EMERGENCY<br/>{action:emergency_stop}"]
        C7["HOME<br/>{action:home}"]
    end

    subgraph RX["Teensy → GUI Telemetrisi"]
        T1["TELEMETRY (10Hz)<br/>{type:tel, state, az_act, el_act,<br/>laser_x, laser_y, locked,<br/>roll, pitch, errors, ...}"]
        T2["ACK<br/>{type:ack, status:ready}"]
        T3["LOG<br/>{type:log, msg:Homing OK}"]
        T4["ERROR<br/>{type:error, msg:IMU fault}"]
    end

    TX -->|JSON\nSerial/WiFi| RX
    RX -->|JSON\nSerial/WiFi| TX
```

## ARAYÜZ DURUM MAKİNESİ

```mermaid
stateDiagram-v2
    [*] --> KAPALI: GUI Başlatıldı
    
    KAPALI --> BEKLEMEDE: Bağlantı kuruldu
    
    BEKLEMEDE --> OTOMATİK: Otomatik Mod Seçildi
    BEKLEMEDE --> MANUEL: Manuel Mod Seçildi
    
    OTOMATİK --> HEDEF_ARA: GPS + Uydu Seçildi
    HEDEF_ARA --> KİLİTLİ: Hedef bulundu (error < 1°)
    HEDEF_ARA --> SPİRAL_TARA: Hedef kayıp
    SPİRAL_TARA --> KİLİTLİ: Tekrar bulundu
    KİLİTLİ --> HEDEF_ARA: Hedef kaybı (error > 2°)
    
    MANUEL --> HEDEF_ARA: Manüel açı girildi
    
    OTOMATİK --> ACİL_DURUM: Acil buton / hata
    MANUEL --> ACİL_DURUM: Acil buton / hata
    KİLİTLİ --> ACİL_DURUM: Acil durum
    
    ACİL_DURUM --> BEKLEMEDE: Sıfırla / Hata çözüldü
    OTOMATİK --> BEKLEMEDE: Durdur
    MANUEL --> BEKLEMEDE: Durdur
    
    BEKLEMEDE --> KAPALI: Bağlantı koptu
    ACİL_DURUM --> KAPALI: Bağlantı koptu
```

## Klasör Yapısı

```
yazilim/arayuz/
├── main.py                    # Ana GUI (Tkinter + ttk + matplotlib)
├── requirements.txt           # pyserial, matplotlib, Pillow
├── comm/
│   ├── __init__.py
│   ├── protocol.py            # JSON-Line protokol tanımları
│   └── io_handler.py          # Serial + ESP32 IO yöneticisi
├── core/
│   ├── __init__.py
│   ├── satellite_pointing.py  # GPS → Az/El hesaplama
│   └── system_state.py        # Sistem durumu veri modeli
└── widgets/
    └── __init__.py
```
