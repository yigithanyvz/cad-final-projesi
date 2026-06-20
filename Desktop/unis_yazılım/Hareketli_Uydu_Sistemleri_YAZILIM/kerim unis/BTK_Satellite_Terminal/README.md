# Hareketli Uydu Terminali — Yazılım Mimarisi

## Degisiklik Adi: KTR-Core

KTR-Core, KTR dosyasindaki nihai mimariye gore algoritma katmaninin
moduller halinde ayrilmis halidir. Header dosyalari arayuzleri,
`src/*.cpp` dosyalari ise gercek implementasyonu tasir.

Ana ayrim:

```
BNO055 -> EKF -> Mama kabi stabilizasyon PID -> X/Y stabilizer motor
ZED-F9P + TLE/SGP4 -> Az/El hedefi -> QPD/Kamera ince takip -> Az/El motor PID
```

Yeni cekirdek dosyalar:

| Dosya | Gorev |
|---|---|
| `SensorFusion.cpp` | EKF, quaternion ve IMU roll/pitch/yaw hesabi |
| `SatelliteTracker.cpp` | TLE, uydu konumu ve Az/El hedef uretimi |
| `PIDController.cpp` | PID, anti-windup, deadband ve safety limitleri |
| `StabilizationController.cpp` | Mama kabi roll/pitch stabilizasyonu |
| `CameraObjectDetector.cpp` | Kamera hedef merkez hatasi filtreleme |
| `LaserTracker.cpp` | QPD/kamera ince takip duzeltmesi |
| `initialization.cpp` | Self-test, homing, IMU kalibrasyonu |
| `telemetry.cpp` | UART telemetri ve komut kuyrugu |

## Proje Yapısı

```
satellite_tracker/
├── include/
│   ├── config.h           ← Tüm sabitler, pin tanımları, PID parametreleri
│   ├── types.h            ← Veri yapıları (Vec3, Quaternion, LLA, TLEData, ...)
│   ├── initialization.h   ← Adım 1: Donanım testi, Homing, IMU kalibrasyonu
│   ├── ekf_filter.h       ← Adım 3: Extended Kalman Filter (7-durumlu)
│   ├── sgp4_propagator.h  ← Adım 2/3: TLE parser + SGP4 + Koordinat dönüşüm
│   ├── pid_controller.h   ← Adım 4: PID, güvenlik monitörü, anten kontrolörü
│   └── telemetry.h        ← Adım 5: Telemetri paketi, komut alıcı
└── src/
    └── main.cpp           ← Tüm adımları birleştiren ana döngü
```

---

## 5 Adım Yazılım Mimarisi

### Adım 1 — Başlatma ve Kalibrasyon
> `initialization.h` → `HardwareSelfTest`, `HomingProcedure`, `IMUCalibration`

| Sınıf | İşlev |
|---|---|
| `HardwareSelfTest` | IMU, GPS, motor sürücü haberleşme testi |
| `HomingProcedure` | Limit switch'e git → geri çekil → encoder = 0 |
| `IMUCalibration` | 500 örnek alarak gyro/accel bias tahmin et |

**Homing akışı:**
```
[CW yavaş hareket] → [Limit switch tetiklendi] → [STOP]
→ [200ms bekle] → [CCW 2° geri çekil] → [Encoder sıfırla]
```

---

### Adım 2 — Veri Toplama
> `main.cpp` → `task_data_acquisition()`

| Kaynak | Hız | Veri |
|---|---|---|
| IMU (MPU-6050) | 100 Hz | accel_ms2, gyro_rads |
| GPS (NMEA) | 1 Hz | LLA, HDOP, uydu sayısı |
| Encoder | 100 Hz | az_deg, el_deg |
| UART (GUI) | Olay tabanlı | CommandPacket |

---

### Adım 3 — Sensör Füzyonu ve Koordinat Hesaplama

#### 3A: EKF — Extended Kalman Filter
> `ekf_filter.h` → `ExtendedKalmanFilter`

**Durum Vektörü (7 boyut):**
```
x = [q0, q1, q2, q3,  bx, by, bz]
     ───────────────  ─────────────
     Birim quaternion  Gyro bias (rad/s)
```

**İki adım:**
- `predict(gyro, dt)` — Quaternion kinematiği + kovaryans yayılımı  
- `update(accel)` — İvmeölçer yerçekimi ile düzeltme

**Filtreleme karşılaştırması:**

| Yöntem | Avantaj | Dezavantaj |
|---|---|---|
| Complementary Filter | Basit, hızlı | Bias tahmini yok |
| **EKF (bu proje)** | Bias tahmini, optimal | Hesap yükü |
| UKF | Yüksek nonlineer doğruluk | En ağır |

#### 3B: SGP4 — Uydu Konum Propagatörü
> `sgp4_propagator.h` → `SGP4Propagator`

```
TLE (ham metin)
    ↓ TLEParser::parse()
TLEData (yapısal)
    ↓ SGP4Propagator::init()
SGP4Elements (önceden hesaplanmış)
    ↓ SGP4Propagator::propagate(JD)
ECI konum/hız (km, km/s)
    ↓ CoordinateTransform::eciToECEF()
ECEF (km)
    ↓ CoordinateTransform::calcAzEl(observer_LLA)
AzEl (°, °, km)
```

#### 3C: Platform Tilt Telafisi
```
sat_azel + [roll, pitch] (EKF'den)
    ↓ CoordinateTransform::compensatePlatformTilt()
compensated_azel  ← motora gidecek gerçek setpoint
```

---

### Adım 4 — PID Kontrol

> `pid_controller.h` → `PIDController`, `SafetyMonitor`, `AntennaController`

**PID Formülü:**

```
hata = hedef_açı - encoder_açısı

P  = Kp × hata
I  = Ki × Σ(hata × dt)          [anti-windup ile]
D  = Kd × EMA(Δhata / dt)       [türev filtresi ile]

output = P + I + D               [sınırlanmış: -60°/s … +60°/s]
```

**Güvenlik katmanları:**

```
SAFE  → Komut olduğu gibi geçer
SOFT  → %50 hız azaltma (yazılım limiti yakını)
HARD  → Motor DURDURULUR (limitte)
FAULT → Acil durum (fiziksel switch tetiklendi)
```

**Anti-Windup:** Çıkış doyuktaysa VE hata aynı yöndeyse integratör dondurulur.

---

### Adım 5 — Geri Besleme ve Telemetri

> `telemetry.h` → `TelemetryPublisher`, `CommandReceiver`

**Paket yapısı (72 byte, UART @ 115200 baud):**
```
[0xABCD][timestamp][state][errors]
[lat][lon][alt][roll][pitch][yaw]
[az_actual][el_actual][az_target][el_target]
[az_error][el_error]
[sat_az][sat_el][sat_range][rssi]
[CRC16]
```

**Döngü performansı:**

| Görev | Süre (hedef) | Süre (tipik) |
|---|---|---|
| IMU okuma | 0.5 ms | 0.3 ms |
| EKF predict+update | 1.5 ms | 1.2 ms |
| SGP4 propagate | 2.0 ms | 1.5 ms |
| PID + güvenlik | 0.3 ms | 0.2 ms |
| Telemetri paket | 0.2 ms | 0.1 ms |
| **TOPLAM** | **~4.5 ms** | **~3.3 ms** |
| Ana döngü periyodu | **10 ms** | → %67 CPU kullanımı |

---

## Konfigürasyon (config.h)

```cpp
// PID'i ayarlamak için sadece bu sabitleri değiştirin:
constexpr float AZ_KP = 2.5f;   // Büyütmek → daha hızlı tepki, ama salınım
constexpr float AZ_KI = 0.1f;   // Sabit hatayı sıfırlar
constexpr float AZ_KD = 0.3f;   // Salınımı azaltır
```

## Derleme

```bash
mkdir build && cd build
cmake .. -DTARGET_SIM=ON
make -j4
./satellite_tracker
```

## Lisans
Yarışma projesi — Tüm hakları saklıdır.
