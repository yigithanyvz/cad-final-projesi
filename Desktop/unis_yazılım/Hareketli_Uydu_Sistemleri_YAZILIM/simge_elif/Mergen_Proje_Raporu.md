# Mergen Hareketli Uydu Terminali - Detayli Proje Raporu

## Proje Hakkinda

Bu proje, UniS yazilim ekibi tarafindan gelistirilen hareketli bir uydu terminali sistemidir. Terminalin amaci, hareketli bir platform uzerinde (arac, gemi vb.) antenin boresight eksenini hedef uyduya (Turksat 4B / Turksat 5A) kilitli tutmaktir. Sistem; IMU, GPS, encoder, TLE/SGP4 ve lazer/QPD geri beslemesini birlikte kullanan kapali dongu bir kontrol mimarisine sahiptir.

## Takim Uyeleri ve Katkilari

| Uye | Klasor | Katki Alani |
| --- | ------ | ----------- |
| Kerim | kerim unis/BTK_Satellite_Terminal/ | Gömülü C++ yazilimi: SGP4, EKF, PID, baslatma, telemetri |
| Efe | Efe/ | ROS 2 arayuzu, dataset simulator, firmware referansi, mimari dokumanlar |
| Elif (Simge) | simge_elif/ | C++ stabilizasyon ornegi, low-pass filtre, PID |

## Klasor Yapisi

```
unis/
├── README.md
├── PID_Algoritma.py
├── run_windows_dataset.bat
├── run_windows_gui.bat
├── run_windows_report_pdf.bat
├── kerim unis/
│   ├── genel bilgi.md
│   └── BTK_Satellite_Terminal/
│       ├── CMakeLists.txt
│       ├── README.md
│       ├── include/
│       │   ├── types.h
│       │   ├── config.h
│       │   ├── initialization.h
│       │   ├── SensorFusion.h
│       │   ├── SatelliteTracker.h
│       │   ├── PIDController.h
│       │   └── telemetry.h
│       └── src/
│           └── main.cpp
├── Efe/
│   ├── README.md
│   ├── tools/
│   │   └── dataset_simulator.py
│   ├── reports/
│   │   ├── OTR_Yazilim_Raporu.pdf
│   │   ├── OTR_Yazilim_Raporu.md
│   │   └── generate_pdf.py
│   ├── datasets/
│   │   ├── sample_motion.csv
│   │   └── sample_result.csv
│   ├── mergen_ws/
│   │   └── src/mergen_interfaces/srv/
│   ├── firmware_reference/
│   │   └── teensy_stm32_cpp/
│   └── docs/
├── arayuz/
│   ├── main.py
│   ├── requirements.txt
│   ├── README.md
│   ├── core/satellite_pointing.py
│   └── ros_bridge/client.py
└── simge_elif/
    └── x.cpp
```

## Sistem Mimarisi

Sistem 4 ana katmandan olusur:

```
┌─────────────────────────────────────────────────────┐
│  KATMAN 4: Arayuz (GUI + ROS 2)                     │
│  Manuel/Otomatik mod, GPS girisi, uydu secimi,      │
│  telemetri izleme, parametre kaydi                  │
├─────────────────────────────────────────────────────┤
│  KATMAN 3: Kontrol (PID + Guvenlik)                 │
│  Azimuth PID | Elevasyon PID | Stabilizasyon PID    │
│  Lazer takip PID | Spiral arama | Limit kontrolu    │
├─────────────────────────────────────────────────────┤
│  KATMAN 2: Kestirim (EKF + SGP4 + Koordinat)        │
│  IMU fuzyonu | Uydu konumu | Platform egim telafisi │
├─────────────────────────────────────────────────────┤
│  KATMAN 1: Algilama (IMU + GPS + Encoder + QPD)     │
│  100 Hz IMU | 1 Hz GPS | Her cycle encoder | QPD    │
└─────────────────────────────────────────────────────┘
```

### Veri Akisi

```
IMU/Gyro -> Kalman + Quaternion -> Stabilizasyon PID -> X/Y motor komutu
GPS + Uydu parametresi -> Azimuth/Elevasyon hedefi -> Motor PID -> Az/El motor komutu
QPD/Lazer -> Hata vektoru -> Aktif takip PID -> Az/El offset duzeltmesi
Encoder -> Gercek motor konumu -> PID geri beslemesi
GUI -> Mod/hedef/parametre -> Kontrol node'lari
```

## 1. Gömülü C++ Yazilimi (Kerim)

### 1.1 Veri Yapilari (types.h)

Temel matematik tipleri: Vec3, Vec3d, Quaternion
Cografi koordinatlar: LLA, ECEF, AzEl
Sensor veri yapilari: IMURawData, GPSData, TLEData, SGP4Elements
Islenmis veri: Orientation, AntennaTarget
Kontrol: PIDState, MotorCommand, EncoderData
Durum makinasi: SystemState (POWER_ON, HW_SELF_TEST, HOMING, CALIBRATING, IDLE, AUTO_TRACKING, MANUAL, ERROR)
Hata kodlari: ErrorCode (IMU_FAULT, GPS_NO_FIX, AZ_MOTOR_FAIL, EL_MOTOR_FAIL, TLE_INVALID, AZ_LIMIT_HIT, EL_LIMIT_HIT, WATCHDOG)
Telemetri: TelemetryPacket (70 byte UART), UserCommand, CommandPacket

### 1.2 Sistem Sabitleri (config.h)

| Sabit | Deger | Aciklama |
| ----- | ----- | -------- |
| MAIN_LOOP_PERIOD_MS | 10 | 100 Hz ana dongu |
| TELEMETRY_PERIOD_MS | 100 | 10 Hz telemetri |
| GPS_UPDATE_PERIOD_MS | 1000 | 1 Hz GPS |
| IMU_SAMPLE_RATE_HZ | 100 | IMU ornekleme hizi |
| AZ_MAX_SPEED_DPS | 60 | Azimut max hiz (derece/s) |
| EL_MAX_SPEED_DPS | 30 | Elevasyon max hiz (derece/s) |
| AZ_KP/AZ_KI/AZ_KD | 2.5 / 0.1 / 0.3 | Azimut PID katsayilari |
| EL_KP/EL_KI/EL_KD | 3.0 / 0.08 / 0.25 | Elevasyon PID katsayilari |
| PID_DEADBAND_DEG | 0.1 | Deadband esigi |
| RSSI_LOCK_THRESHOLD_DB | -90 | Sinyal kilit esigi |

### 1.3 Baslatma ve Kalibrasyon (initialization.h)

- HardwareSelfTest: IMU (MPU-6050), GPS, motor, encoder testi
- HomingProcedure: Limit switch ile sifir noktasi belirleme
- IMUCalibration: 500 ornek ile gyro bias + accel bias kestirimi
- system_initialize(): Test -> Homing -> Kalibrasyon orkestratoru

### 1.4 Sensor Fuzyonu - EKF (SensorFusion.h)

7 boyutlu Extended Kalman Filter:
- Durum: [q0, q1, q2, q3, bx, by, bz] (quaternion + gyro bias)
- Predict: Gyro ile quaternion kinematigi, 7x7 Jacobian
- Update: Ivmeolcer olcumu, Kalman kazanci, kovaryans guncellemesi
- Cikti: Quaternion -> Roll/Pitch/Yaw (ZYX sirasi)

### 1.5 Uydu Takibi - SGP4 (SatelliteTracker.h)

- TLE Parser: Iki satir TLE -> TLEData
- SGP4 Propagator: Hoots & Roehrich, Kepler cozumu (Newton-Raphson), J2/J3 perturba
- Koordinat donusumleri: ECI -> ECEF -> LLA -> Az/El
- Platform egim telafisi (roll/pitch kompanzasyonu)

### 1.6 PID Kontrol (PIDController.h)

- PIDController: Anti-windup, turev filtreleme (EMA), deadband, aci sarmalama
- SafetyMonitor: Hard/soft limit, kablo sarmalama korumasi
- AntennaController: Cift eksenli PID + guvenlik entegrasyonu

### 1.7 Telemetri (telemetry.h)

- TelemetryPublisher: 10 Hz, 70 byte UART paketi, CRC-16/CCITT
- CommandReceiver: 8 komutluk FIFO dairesel kuyruk

### 1.8 Ana Kontrol Dongusu (main.cpp)

```
ADIM 1: Baslatma -> ADIM 2: Veri Toplama -> ADIM 3: Sensor Fuzyonu + Koordinat
-> ADIM 4: PID Kontrol -> ADIM 5: Telemetri (10 Hz)
```

FreeRTOS veya bare-metal super-loop uyumlu.

## 2. Dataset ile CAD Oncesi Dogrulama (Efe)

### dataset_simulator.py

- --generate: 5 dakika, 100 Hz sentetik veri (IMU + QPD)
- --input/--output: Kalman + PID + QPD algoritmalarini calistirir
- Cikti: Filtrelenmis IMU, QPD hata vektoru, PID PWM, kilit durumu

## 3. Python Arayuz (arayuz/)

### main.py
- Tkinter GUI ile manuel/otomatik mod, GPS girisi, uydu secimi
- Turksat 4B/5A yonelim hesabi (satellite_pointing.py)
- ROS 2 opsiyonel entegrasyon (ros_bridge/client.py)

## 4. ROS 2 Servis Tanimlari

- SetMode.srv: string mode -> bool accepted + string message
- SaveParameters.srv: string profile_name -> bool saved + string message

## 5. Firmware Referansi (Efe/firmware_reference/)

Teensy/STM32 icin:
- kalman_filter.hpp: 1D Kalman
- pid_controller.hpp: Klasik PID + clamping
- main_loop_example.cpp: 2x Kalman + 4x PID

## 6. C++ Stabilizasyon Ornegi (Simge/Elif - x.cpp)

MergenStabilizer sinifi ile:
- Low-pass filtre (ALPHA = 0.1) ile IMU gurultusu temizleme
- PID kontrol (Kp=2.0, Ki=0.5, Kd=0.1) ile acisal duzeltme
- Integral windup korumasi (std::clamp ile)
- dt parametresi ile zaman tabanli kontrol
- 5 adimlik simulasyon testi
- Windows UTF-8 uyumlulugu (SetConsoleOutputCP)

## 7. Sartname Karsilama Matrisi

| Sartname Istegi | Karsilama | Durum |
| --------------- | --------- | ------ |
| Azimuth 0-360 derece | Azimuth PID + continuous joint | Tasarlandi |
| Elevasyon 0-90 derece | Elevation PID + limit kontrolu | Tasarlandi |
| Manuel mod | Python GUI + ROS servis | Tasarlandi |
| Otomatik mod | IMU + Kalman + QPD + PID state machine | Tasarlandi |
| IMU/Gyro stabilizasyon | Kalman + quaternion + stabilization PID | Tasarlandi |
| Lazer tabanli takip | QPD hata vektoru + aktif geri besleme PID | Tasarlandi |
| Hedefe tekrar yonelim 8 sn | Lock state machine | Tasarlandi |
| 5 dk takip testi | Dataset + Gazebo altyapisi | Tasarlandi |
| GPS manuel giris | Python GUI uydu yonelim hesabi | Tasarlandi |
| Turksat 4B/5A yonelim | satellite_pointing.py | Tasarlandi |
| Parametrelerin kalici saklanmasi | JSON + ROS servis | Tasarlandi |
| Bilgisayar/tablet arayuzu | Tkinter GUI | Tasarlandi |
| CAD-Gazebo entegrasyonu | URDF/Xacro iskeleti | Tasarlandi |

## 8. Calistirma Komutlari

```
# Dataset olusturma
python Efe/tools/dataset_simulator.py --generate --output Efe/datasets/sample_motion.csv
python Efe/tools/dataset_simulator.py --input Efe/datasets/sample_motion.csv --output Efe/datasets/sample_result.csv

# GUI baslatma
python arayuz/main.py

# PDF rapor
python Efe/reports/generate_pdf.py

# C++ stabilizasyon testi (simge_elif)
# g++ x.cpp -o x.exe && x.exe
```

## 9. Teknik Detaylar

### PID Parametreleri

| Eksen | Kp | Ki | Kd | Max Integral | Deadband | Wrap |
| ----- | -- | -- | -- | ------------ | -------- | ---- |
| Azimuth | 2.5 | 0.1 | 0.3 | 20.0 | 0.1 | Evet |
| Elevasyon | 3.0 | 0.08 | 0.25 | 15.0 | 0.1 | Hayir |

### QPD Hata Vektoru

ex = ((A + D) - (B + C)) / (A + B + C + D)
ey = ((A + B) - (C + D)) / (A + B + C + D)

### Durum Makinasi Gecisleri

POWER_ON -> HW_SELF_TEST -> HOMING -> CALIBRATING -> IDLE
IDLE -> AUTO_TRACKING (otomatik mod)
IDLE -> MANUAL (manuel mod)

## Sonuc

Mergen projesi; IMU tabanli stabilizasyon, TLE/SGP4 ile yorunge hesabi, PID kontrol, lazer/QPD ile aktif geri besleme ve kullanici arayuzu gereksinimlerini karsilayacak sekilde dort katmanli mimari ile tasarlanmistir. CAD modeli tamamlanana kadar dataset tabanli dogrulama, CAD tamamlandiktan sonra Gazebo simulasyonu ve en son gomulu donanim entegrasyonu ile sistem dogrulama asamalari tamamlanacaktir.
