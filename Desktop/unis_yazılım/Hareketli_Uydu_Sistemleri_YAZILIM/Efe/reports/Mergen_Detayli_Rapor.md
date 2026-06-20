# Mergen Hareketli Uydu Terminali - Detayli Proje Raporu

## Proje Hakkimda

Bu proje, UniS yazilim ekibi tarafindan gelistirilen hareketli bir uydu terminali sistemidir. Terminalin amaci, hareketli bir platform uzerinde (arac, gemi vb.) antenin boresight eksenini hedef uyduya (Turksat 4B / Turksat 5A) kilitli tutmaktir. Sistem; IMU, GPS, encoder, TLE/SGP4 ve lazer/QPD geri beslemesini birlikte kullanan kapali dongu bir kontrol mimarisine sahiptir.

## Takim Uyeleri ve Katkilari

| Uye | Klasor | Katki Alani |
| --- | ------ | ----------- |
| Kerim | `kerim unis/BTK_Satellite_Terminal/` | Gömülü C++ yazilimi: SGP4, EKF, PID, baslatma, telemetri |
| Efe | `Efe/` | ROS 2 arayuzu, dataset simulator, firmware referansi, mimari dokumanlar |
| Elif (Simge) | `simge_elif/` | C++ stabilizasyon ornegi, low-pass filtre, PID |

## Klasor Yapisi

```
unis/
├── README.md                          # Proje genel bilgilendirme
├── PID_Algoritma.py                   # Bos dosya (placeholder)
│
├── run_windows_dataset.bat            # Dataset simulator calistirma
├── run_windows_gui.bat                # GUI calistirma
├── run_windows_report_pdf.bat         # PDF rapor olusturma
│
├── kerim unis/
│   ├── genel bilgi.md                 # Sistem akisi dokumani
│   └── BTK_Satellite_Terminal/        # Gömülü C++ kodu
│       ├── CMakeLists.txt
│       ├── README.md
│       ├── include/                   # Baslik dosyalari
│       │   ├── types.h               # Veri yapilari ve enum'lar
│       │   ├── config.h              # Sistem sabitleri
│       │   ├── initialization.h      # Baslatma, homing, kalibrasyon
│       │   ├── SensorFusion.h        # EKF (Extended Kalman Filter)
│       │   ├── SatelliteTracker.h    # SGP4 propagator + koordinat donusum
│       │   ├── PIDController.h       # PID kontrol + guvenlik
│       │   └── telemetry.h           # Telemetri yayini + komut alici
│       ├── src/
│       │   ├── main.cpp              # Ana kontrol dongusu
│       │   ├── SensorFusion.cpp      # (bos)
│       │   ├── SatelliteTracker.cpp  # (bos)
│       │   └── PIDController.cpp     # (bos)
│       ├── scripts/                  # (bos)
│       ├── rtos/                     # (bos)
│       └── docs/                     # (bos)
│
├── Efe/
│   ├── README.md                     # Mimari aciklamasi
│   ├── tools/
│   │   └── dataset_simulator.py      # CAD oncesi dogrulama araci
│   ├── reports/
│   │   ├── OTR_Yazilim_Raporu.pdf    # On tasarim raporu PDF
│   │   ├── OTR_Yazilim_Raporu.md     # On tasarim raporu kaynagi
│   │   └── generate_pdf.py           # PDF olusturma scripti
│   ├── datasets/
│   │   ├── sample_motion.csv         # Ornek hareket verisi
│   │   └── sample_result.csv         # Ornek sonuc verisi
│   ├── mergen_ws/                    # ROS 2 workspace
│   │   └── src/mergen_interfaces/    # ROS 2 servis tanimlari
│   │       ├── CMakeLists.txt
│   │       ├── package.xml
│   │       └── srv/
│   │           ├── SetMode.srv       # Mod degistirme servisi
│   │           └── SaveParameters.srv# Parametre kaydetme servisi
│   ├── firmware_reference/
│   │   └── teensy_stm32_cpp/         # Teensy/STM32 referans kodu
│   │       ├── README.md
│   │       ├── include/
│   │       │   ├── pid_controller.hpp
│   │       │   └── kalman_filter.hpp
│   │       └── src/
│   │           └── main_loop_example.cpp
│   └── docs/
│       ├── sistem_mimarisi.md        # 4 katmanli mimari dokumani
│       ├── sartname_karsilama_matrisi.md # Sartname gereksinimleri
│       └── gazebo_yol_haritasi.md    # CAD/Gazebo entegrasyon plani
│
├── arayuz/                           # Python Tkinter GUI
│   ├── main.py                       # Ana GUI uygulamasi
│   ├── requirements.txt              # Bagimliliklar
│   ├── README.md                     # Arayuz dokumani
│   ├── core/
│   │   └── satellite_pointing.py     # Uydu yonelim hesaplama
│   └── ros_bridge/
│       └── client.py                 # ROS 2 istemci (simulasyon stub)
│
└── simge_elif/
    └── x.cpp                         # C++ stabilizasyon ornegi
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
│  IMU fuzyonu | Uydu konumu | Platform eğim telafisi │
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

Temel matematik tipleri:
- `Vec3` - 3 boyutlu vektor (float)
- `Vec3d` - 3 boyutlu vektor (double)
- `Quaternion` - Quaternion (w, x, y, z) ile carpma, normalize, conjugate

Cografi koordinatlar:
- `LLA` - Enlem/Boylam/Irtifa (derece, metre)
- `ECEF` - Earth-Centered Earth-Fixed (metre)
- `AzEl` - Azimut/Elevasyon/Mesafe

Sensor veri yapilari:
- `IMURawData` - ivmeolcer (m/s^2) + jiroskop (rad/s) + timestamp
- `GPSData` - LLA konum + hiz + yon + HDOP + uydu sayisi
- `TLEData` - TLE yorunge verisi (tum alanlar)
- `SGP4Elements` - SGP4 onceden hesaplanmis elemanlar

Islenmis veri:
- `Orientation` - Quaternion + Roll/Pitch/Yaw + gyro bias
- `AntennaTarget` - Hedef aci setpoint + uydu bilgisi

Kontrol:
- `PIDState` - Integral, onceki hata, turev, output
- `MotorCommand` - Eksen + yon + PWM gorev dongusu + hiz
- `EncoderData` - Az/El gercek acilar + hiz + timestamp

Durum makinasi:
- `SystemState` - POWER_ON, HW_SELF_TEST, HOMING, CALIBRATING, IDLE, AUTO_TRACKING, MANUAL, ERROR
- `ErrorCode` - IMU_FAULT, GPS_NO_FIX, AZ_MOTOR_FAIL, EL_MOTOR_FAIL, TLE_INVALID, AZ_LIMIT_HIT, EL_LIMIT_HIT, WATCHDOG

Telemetri:
- `TelemetryPacket` - 70 byte'lik UART paketi (magic, timestamp, state, errors, konum, yonelim, acilar, hatalar, RSSI, CRC16)
- `UserCommand` - SET_AUTO_MODE, SET_MANUAL, MANUAL_AZ, MANUAL_EL, LOAD_TLE, HOME, EMERGENCY_STOP
- `CommandPacket` - Komut + payload union

### 1.2 Sistem Sabitleri (config.h)

| Sabit | Deger | Aciklama |
| ----- | ----- | -------- |
| MAIN_LOOP_PERIOD_MS | 10 | 100 Hz ana dongu |
| TELEMETRY_PERIOD_MS | 100 | 10 Hz telemetri |
| GPS_UPDATE_PERIOD_MS | 1000 | 1 Hz GPS |
| TLE_UPDATE_PERIOD_S | 3600 | Saatlik TLE |
| IMU_SAMPLE_RATE_HZ | 100 | IMU ornekleme hizi |
| GYRO_NOISE_SIGMA | 0.005 | Jiroskop gurultu std |
| ACCEL_NOISE_SIGMA | 0.01 | Ivmeolcer gurultu std |
| GRAVITY_MS2 | 9.80665 | Yercekimi sabiti |
| CALIBRATION_SAMPLES | 500 | 5 sn kalibrasyon |
| AZ_LIMIT_MIN/MAX | 0 / 360 | Azimut fiziksel limit |
| EL_LIMIT_MIN/MAX | 0 / 90 | Elevasyon fiziksel limit |
| AZ_MAX_SPEED_DPS | 60 | Azimut max hiz (derece/s) |
| EL_MAX_SPEED_DPS | 30 | Elevasyon max hiz (derece/s) |
| AZ_KP/AZ_KI/AZ_KD | 2.5 / 0.1 / 0.3 | Azimut PID katsayilari |
| EL_KP/EL_KI/EL_KD | 3.0 / 0.08 / 0.25 | Elevasyon PID katsayilari |
| PID_DEADBAND_DEG | 0.1 | Deadband esigi |
| DERIV_FILTER_ALPHA | 0.7 | Turev filtre katsayisi |
| RSSI_LOCK_THRESHOLD_DB | -90 | Sinyal kilit esigi |
| WATCHDOG_TIMEOUT_MS | 500 | WDT suresi |

### 1.3 Baslatma ve Kalibrasyon (initialization.h)

**Donanim Oz-Testi (HardwareSelfTest):**
- IMU kontrolu (I2C adresi 0x68, MPU-6050)
- GPS modulu kontrolu (UART, 9600 baud)
- Azimut motor + encoder testi
- Elevasyon motor + encoder testi
- IMU ivmeolcer kalibrasyon dogrulama (9.8 +/- 2 m/s^2)

**Homing (HomingProcedure):**
- Her iki eksen icin limit switch'e yaklasma
- CW yonunde limit switch'e git (15 sn timeout)
- ~2 derece geri cekilme (mekanik gerilim azaltma)
- Encoder sifirlama (HOME referans noktasi)

**IMU Kalibrasyonu (IMUCalibration):**
- 500 ornek (~5 sn) hareketsiz ortalama
- Gyro bias: ortalama gyro degeri
- Accel bias: ortalama - normalize edilmis yercekimi
- Kalite kontrolu: %5 olcekleme toleransi, <0.1 rad/s bias

**Orkestrator (system_initialize):**
- Test -> Homing -> Kalibrasyon sirasiyla calistir
- Herhangi bir asamada basarisizlik -> ERROR modu

### 1.4 Sensör Füzyonu - EKF (SensorFusion.h)

7 boyutlu Extended Kalman Filter:
- Durum: [q0, q1, q2, q3, bx, by, bz] (quaternion + gyro bias)
- Predict: Gyro okumasi ile quaternion kinematigi
  - q_dot = 0.5 * Omega(w_corrected) * q
  - omega_corrected = omega_measured - bias
  - 7x7 Jacobian F ile kovaryans yayilimi
- Update: Ivmeolcer olcumu ile duzeltme
  - Beklenen ivme = R(q) * [0, 0, g]
  - Inovasyon: accel_raw - h(x)
  - 3x7 olcum Jacobian H
  - Kalman kazanci K = P*H'*S^(-1)
  - Durum + kovaryans guncellemesi
- Guclu ivme detekte: |accel_mag - g| > 3.0 ise update atlanir
- Quaternion normalize ve kovaryans izi ile yakinlasma kontrolu

Cikti: Quaternion -> Roll/Pitch/Yaw (ZYX sirasi)

### 1.5 Uydu Takibi - SGP4 (SatelliteTracker.h)

**TLE Parser:**
- Iki satir TLE formatini TLEData'ya donusturur
- Epoch yil (2-digit -> 4-digit), BSTAR decode, eccentricity

**SGP4 Propagator:**
- Hoots & Roehrich (1980), Vallado (2013) uyarlamasi
- TLE'den ortalama elemanlari turetme (bir kez)
- Newton-Raphson ile Kepler denklemi cozumu (8 iterasyon)
- J2/J3 perturbasyon duzeltmeleri
- Cikti: ECI koordinatlarinda konum (km) + hiz (km/s)

**Koordinat Donusumleri:**
- ECI -> ECEF (Dunya donusu, GAST)
- ECEF -> LLA (WGS-84, Bowring iterasyonu)
- LLA + ECEF -> Az/El (NED cercevesi)
- Platform egim telafisi (Roll/Pitch kompanzasyonu)

### 1.6 PID Kontrol (PIDController.h)

**PIDController (tek eksen):**
- Anti-windup: Cikis doyuktaysa ve hata ayni yondeyse integral dondurma
- Turev filtreleme: EMA dusuk geciren (alpha = 0.7)
- Deadband: +/- 0.1 derece icinde motor durdurma, integral sifirlama
- Aci sarmalama: Azimut icin -180/+180 derece

**SafetyMonitor:**
- Hard limit: Fiziksel limit switch -> aninda durdurma
- Soft limit: Hiz %50 kisitlama
- Kablo sarmalama: Kademeli yavaslatma (350-360 derece)
- Acil durum: Switch tetiklenirse emergency_stop

**AntennaController (cift eksen yonetici):**
- Uydu ufkun altindaysa -> park pozisyonu (0, 0)
- Hiz -> PWM donusumu
- Hedefte mi kontrolu (deadband * 2)

### 1.7 Telemetri (telemetry.h)

**TelemetryPublisher (10 Hz):**
- ~70 byte'lik UART paketi
- Alanlar: magic, timestamp, state, errors, LLA, roll/pitch/yaw, encoder acilari, hedef acilar, hata acilari, uydu bilgisi, RSSI, CRC16
- CRC-16/CCITT (polinom 0x1021)

**CommandReceiver (dairesel kuyruk):**
- 8 komutluk FIFO
- UART'tan byte akisi -> CommandPacket
- polling ile her ana dongude okuma

### 1.8 Ana Kontrol Dongusu (main.cpp)

FreeRTOS veya bare-metal uyumlu super-loop:

```
ADIM 1: Baslatma (bir kez)
  - Donanim testi -> Homing -> IMU kalibrasyon
  - EKF baslatma
  - Varsayilan TLE yukleme (NOAA-19)
  -> IDLE durumu -> AUTO_TRACKING'e gecis

ADIM 2: Veri Toplama (her 10ms)
  - IMU okuma + bias cikarma (100 Hz)
  - GPS okuma + HDOP kontrolu (1 Hz)
  - Encoder okuma (her cycle)
  - Komut kuyrugu polling (her cycle)

ADIM 3: Sensor Fuzyonu + Koordinat
  - EKF predict (gyro) + update (accel)
  - SGP4 propagate (TLE -> ECI -> ECEF -> Az/El)
  - Platform egim telafisi (roll/pitch kompanzasyonu)
  - Anten hedef guncelleme

ADIM 4: Kontrol
  - Komut isleme (mode degisikligi, manuel hedef, TLE, homing, emergency)
  - Limit switch okuma
  - PID + Guvenlik
  - Motor PWM uygulama

ADIM 5: Telemetri (10 Hz)
  - Paket olusturma ve UART gonderimi
  - Takip hatasi denetimi (MAX_TRACKING_ERROR_DEG = 5)
```

## 2. Dataset ile CAD Öncesi Doğrulama (Efe)

### dataset_simulator.py

CAD modeli hazir olmadan kontrol algoritmasini test etmek icin kullanilir.

**Ozellikler:**
- `--generate`: 5 dakikalik, 100 Hz sentetik veri uretir
  - Roll: 8*sin(2*pi*t/10) + gauss(0, 0.18)
  - Pitch: 8*cos(2*pi*t/10) + gauss(0, 0.18)
  - Yaw: 36*t mod 360
  - Hedef: Az=120, El=30 (sabit)
  - Sanal QPD: sin/cos ile merkez etrafinda salinim
- `--input/--output`: Var olan dataset uzerinde algoritma calistirir
  - 1D Kalman filtreleme (roll/pitch)
  - QPD hata vektoru hesabi
  - Azimuth PID + Elevasyon PID
  - Stabilizasyon PID (X/Y)
  - Hedef kilit durumu tespiti

**Cikti:** Filtrelenmis IMU, QPD hata vektoru, PID PWM ciktilari, kilit durumu

## 3. Python Arayüz (arayuz/)

### main.py (Tkinter GUI)

Sartnamedeki bilgisayar/tablet kontrol ihtiyacini karsilar.

**Bilesenler:**
- Komut ve Mod paneli: Otomatik/Manuel mod secimi
- Manuel hedef gonderimi (Azimuth + Elevasyon)
- Uydu Yonelimi paneli: GPS enlem/boylam girisi, Turksat 4B/5A secimi
- Az/El hesaplama butonu (jeostasyoner uydu yaklasimi)
- Telemeti metin kutusu (durum mesajlari)
- Parametre Kaydet (JSON)
- Guvenli Mod butonu

**ROS 2 Entegrasyonu:**
- Su an simulasyon modunda (ROS olmayan bilgisayarda calisir)
- Ubuntu 22.04 + ROS 2 Humble'da rclpy publisher/service client'a genisletilecek

### satellite_pointing.py

Jeostasyoner uydu icin yaklasik Az/El hesabi:
- Turksat 4B: 50.0 dogu boylami
- Turksat 5A: 31.0 dogu boylami
- Kuresel geometri: acos, atan2 ile azimuth/elevasyon

### ros_bridge/client.py

Ince ROS 2 istemci:
- set_mode(mode) -> simulasyon mesaji
- send_manual_target(az, el) -> simulasyon mesaji
- save_parameters() -> simulasyon mesaji

## 4. ROS 2 Servis Tanimlari (Efe/mergen_ws/)

### SetMode.srv
```
string mode          # "automatic", "manual", "safe"
---
bool accepted
string message
```

### SaveParameters.srv
```
string profile_name  # Profil adi
---
bool saved
string message
```

## 5. Firmware Referansi (Efe/firmware_reference/)

Teensy/STM32 mikrodenetleyici icin referans implementasyon:

### kalman_filter.hpp
- 1D Kalman Filter
- process_noise (q_) ve measurement_noise (r_) parametreli
- predict + update tek adimda

### pid_controller.hpp
- Klasik PID (P + I + D)
- Output clamping
- dt guvenlik kontrolu

### main_loop_example.cpp
- 2x Kalman (roll, pitch)
- 4x PID (azimuth, elevation, roll_stab, pitch_stab)
- Statik degiskenlerle hafizada tutma

## 6. Sartname Karsilama Matrisi

| Sartname Istegi | Karsilama | Durum |
| --------------- | --------- | ----- |
| Azimuth 0-360 derece | Azimuth PID + continuous joint | Tasarlandi |
| Elevasyon 0-90 derece | Elevation PID + limit kontrolu | Tasarlandi |
| Manuel mod | Python GUI ManuelCommand + ROS servis | Tasarlandi |
| Otomatik mod | IMU + Kalman + QPD + PID state machine | Tasarlandi |
| IMU/Gyro stabilizasyon | KalmanFilter1D + quaternion + stabilization PID | Tasarlandi |
| Lazer tabanli takip | QPD hata vektoru + aktif geri besleme PID | Tasarlandi |
| Hedefe tekrar yonelim 8 sn | Lock state machine + zaman hedefi | Tasarlandi |
| 5 dk takip testi | Dataset + Gazebo test senaryosu altyapisi | Tasarlandi |
| GPS manuel giris | Python GUI uydu yonelim hesabi | Tasarlandi |
| Turksat 4B/5A yonelim | satellite_pointing.py geostationary hesap | Tasarlandi |
| Parametrelerin kalici saklanmasi | JSON config + ROS servis | Tasarlandi |
| Bilgisayar/tablet arayuzu | Tkinter tabanli Python GUI | Tasarlandi |
| CAD-Gazebo entegrasyonu | mergen_description mesh/URDF iskeleti | Tasarlandi |

## 7. Gazebo Entegrasyon Yol Haritasi

1. SolidWorks montaji tamamlanir, her parca ayri mesh export edilir
2. Mesh dosyalari `mergen_description/meshes/` altina yerlestirilir
3. URDF/Xacro: her parca link, hareketli baglantilar joint
4. Azimuth: continuous joint, Elevasyon: revolute joint (0-90)
5. Stabilizasyon: 2x prismatic joint (CAD tamamlanana kadar)
6. IMU sensoru: Gazebo plugin ile terminal govdesine bagli
7. Motorlar: once joint position controller, sonra ros2_control
8. Stewart platform: roll/pitch/yaw bozucu test node'u
9. Kontrol node'u: IMU + encoder + QPD -> motor komutlari
10. Python arayuz: ayni topic/servislere baglanti

## 8. KTR Icin Gelistirme Yol Haritasi

1. Dataset sonuclariyla Kalman ve PID parametreleri ilk kez ayarlanir
2. CAD modeli mesh export edilir, URDF/Xacro modeline baglanir
3. Gazebo icinde IMU, joint state ve motor kontrol pluginleri aktif
4. Stewart platform hareketi roll/pitch/yaw bozucu olarak simule edilir
5. 5 dakika takip testi, 8 saniye yeniden kilitlenme testi
6. Manuel/otomatik mod testleri kaydedilir
7. Gercek donanim secimi kesinlesince ROS node ciktilari Teensy/STM32 firmware arayuzune baglanir
8. KTR raporunda dataset, Gazebo ve donanim testleri ayni metriklerle sunulur

## 9. Calistirma Komutlari

**Windows:**
```
# GUI baslatma
python arayuz/main.py

# Dataset olusturma ve dogrulama
python Efe/tools/dataset_simulator.py --generate --output Efe/datasets/sample_motion.csv
python Efe/tools/dataset_simulator.py --input Efe/datasets/sample_motion.csv --output Efe/datasets/sample_result.csv

# PDF rapor olusturma
python Efe/reports/generate_pdf.py
```

**Ubuntu 22.04 (ROS 2 Humble):**
```
# ROS 2 workspace derleme
cd mergen_ws
colcon build
source install/setup.bash

# GUI (ROS baglantili)
python3 arayuz/main.py
```

## 10. Teknik Detaylar

### PID Parametreleri

| Eksen | Kp | Ki | Kd | Max Integral | Deadband | Wrap |
| ----- | -- | -- | -- | ------------ | -------- | ---- |
| Azimuth | 2.5 | 0.1 | 0.3 | 20.0 | 0.1 | Evet |
| Elevasyon | 3.0 | 0.08 | 0.25 | 15.0 | 0.1 | Hayir |

### QPD Hata Vektoru

```
ex = ((A + D) - (B + C)) / (A + B + C + D)
ey = ((A + B) - (C + D)) / (A + B + C + D)
```

Toplam sinyal < 0.05 ise hedef tespit edilememis kabul edilir.
ex < 0.03 ve ey < 0.03 ise hedef kilitlenmis kabul edilir.

### Durum Makinasi Gecisleri

```
POWER_ON -> HW_SELF_TEST -> HOMING -> CALIBRATING -> IDLE
IDLE -> AUTO_TRACKING (otomatik mod)
IDLE -> MANUAL (manuel mod)
AUTO_TRACKING/MANUAL -> ERROR (hata durumu)
ERROR -> IDLE (hata cozuldu)
```

### Hata Kodlari (bitmask)

| Bit | Hata |
| --- | ---- |
| 0x0001 | IMU_FAULT |
| 0x0002 | GPS_NO_FIX |
| 0x0004 | AZ_MOTOR_FAIL |
| 0x0008 | EL_MOTOR_FAIL |
| 0x0010 | TLE_INVALID |
| 0x0020 | AZ_LIMIT_HIT |
| 0x0040 | EL_LIMIT_HIT |
| 0x0080 | WATCHDOG |

## Sonuc

Mergen projesi; hareketli bir platform uzerinde uydu takibi yapabilmek icin IMU tabanli stabilizasyon, TLE/SGP4 ile yorunge hesabi, PID kontrol, lazer/QPD ile aktif geri besleme ve kullanici arayuzu gereksinimlerini karsilayacak sekilde tasarlanmistir. Dort katmanli mimari sayesinde algilama, kestirim, kontrol ve arayuz birbirinden bagimsiz gelistirilebilmektedir. CAD modeli tamamlanana kadar dataset tabanli dogrulama, CAD tamamlandiktan sonra Gazebo simulasyonu ve en son gomulu donanim entegrasyonu ile sistem dogrulama asamalari tamamlanacaktir.
