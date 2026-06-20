# Mergen Haberleşme Protokolü — Teensy/ESP32 Referansı

## Genel Bakış

GUI ile Teensy arasında **JSON-Line** protokolü kullanılır. Her mesaj tek satır JSON, `\n` ile sonlandırılır.

- **Serial (USB):** 115200 baud, 8N1
- **ESP32 WiFi:** TCP, port 5000

---

## Teensy → GUI (Telemetri) — 10 Hz

```json
{"type":"tel","state":3,"az_act":152.1,"el_act":42.0,"az_tgt":152.3,"el_tgt":42.1,"laser_x":0.05,"laser_y":-0.03,"roll":1.2,"pitch":0.5,"yaw":0.0,"locked":true,"gps_lat":39.92,"gps_lon":32.85,"uptime":15000,"errors":0,"rssi":-75}
```

| Alan | Tip | Açıklama |
|------|-----|----------|
| `state` | int | 0=KAPALI 1=BEKLEMEDE 2=STARTING **3=AUTO** **4=MANUAL** 5=HOMING 6=EMERGENCY 7=ERROR |
| `az_act` | float | Gerçek azimuth (°) |
| `el_act` | float | Gerçek elevasyon (°) |
| `az_tgt` | float | Hedef azimuth (°) |
| `el_tgt` | float | Hedef elevasyon (°) |
| `laser_x` | float | Lazer X sapma (HuskyLens piksel / normalize) |
| `laser_y` | float | Lazer Y sapma (HuskyLens piksel / normalize) |
| `roll` | float | IMU roll (°) |
| `pitch` | float | IMU pitch (°) |
| `yaw` | float | IMU yaw (°) |
| `locked` | bool | Hedef kilitli mi? |
| `gps_lat` | float | GPS enlem |
| `gps_lon` | float | GPS boylam |
| `uptime` | int | Çalışma süresi (ms) |
| `errors` | int | Hata bayrakları (bitfield) |
| `rssi` | int | Sinyal gücü (dBm) |

**Hata bitfield:**
- 0x0001 = IMU Hatası
- 0x0002 = GPS Hatası
- 0x0004 = Azimut Motor
- 0x0008 = Elevasyon Motor
- 0x0010 = Hedef Kaybı
- 0x0020 = Limit Switch
- 0x0040 = İletişim Hatası
- 0x0080 = Acil Durum

---

## GUI → Teensy (Komutlar)

### SİSTEMİ BAŞLAT
```json
{"type":"cmd","action":"start"}
```
**Teensy yapması gereken:** Röle/ MOSFET ile motor enerjisini aç → donanım testi → homing → BEKLEMEDE

### SİSTEMİ DURDUR
```json
{"type":"cmd","action":"stop"}
```

### MOD AYARLA
```json
{"type":"cmd","action":"set_mode","mode":"auto"}
{"type":"cmd","action":"set_mode","mode":"manual"}
```

### HEDEF GÖNDER
```json
{"type":"cmd","action":"set_target","az":152.3,"el":42.1}
```

### GPS GÖNDER
```json
{"type":"cmd","action":"set_gps","lat":39.9208,"lon":32.8541}
```

### HOMING
```json
{"type":"cmd","action":"home"}
```

### ACİL DURDURMA
```json
{"type":"cmd","action":"emergency_stop"}
```

### HATA SIFIRLAMA
```json
{"type":"cmd","action":"reset_error"}
```

---

## Diğer Mesajlar

### Teensy → GUI: ACK (başarılı yanıt)
```json
{"type":"ack","status":"ready"}
{"type":"ack","status":"started"}
{"type":"ack","status":"stopped"}
```

### Teensy → GUI: Log mesajı
```json
{"type":"log","msg":"Homing baslatildi"}
{"type":"log","msg":"Hedef 152.3, 42.1 set edildi"}
```

### Teensy → GUI: Hata
```json
{"type":"error","msg":"IMU baslatilamadi"}
{"type":"error","msg":"Motor surucu hatasi"}
```

---

## Teensy (Arduino/PlatformIO) Referans Kodu

```cpp
// Minimal Teensy reference for JSON telemetry output
#include <Arduino.h>

// Telemetri yapisi
struct Telemetry {
  int state = 1;
  float az_act = 0, el_act = 0;
  float az_tgt = 0, el_tgt = 0;
  float laser_x = 0, laser_y = 0;
  float roll = 0, pitch = 0, yaw = 0;
  bool locked = false;
  float gps_lat = 0, gps_lon = 0;
  unsigned long uptime = 0;
  int errors = 0;
  int rssi = -100;
};

void sendTelemetry(const Telemetry& t) {
  Serial.print("{\"type\":\"tel\",");
  Serial.print("\"state\":"); Serial.print(t.state); Serial.print(",");
  Serial.print("\"az_act\":"); Serial.print(t.az_act, 2); Serial.print(",");
  Serial.print("\"el_act\":"); Serial.print(t.el_act, 2); Serial.print(",");
  Serial.print("\"az_tgt\":"); Serial.print(t.az_tgt, 2); Serial.print(",");
  Serial.print("\"el_tgt\":"); Serial.print(t.el_tgt, 2); Serial.print(",");
  Serial.print("\"laser_x\":"); Serial.print(t.laser_x, 4); Serial.print(",");
  Serial.print("\"laser_y\":"); Serial.print(t.laser_y, 4); Serial.print(",");
  Serial.print("\"roll\":"); Serial.print(t.roll, 2); Serial.print(",");
  Serial.print("\"pitch\":"); Serial.print(t.pitch, 2); Serial.print(",");
  Serial.print("\"yaw\":"); Serial.print(t.yaw, 2); Serial.print(",");
  Serial.print("\"locked\":"); Serial.print(t.locked ? "true" : "false"); Serial.print(",");
  Serial.print("\"gps_lat\":"); Serial.print(t.gps_lat, 6); Serial.print(",");
  Serial.print("\"gps_lon\":"); Serial.print(t.gps_lon, 6); Serial.print(",");
  Serial.print("\"uptime\":"); Serial.print(t.uptime); Serial.print(",");
  Serial.print("\"errors\":"); Serial.print(t.errors); Serial.print(",");
  Serial.print("\"rssi\":"); Serial.print(t.rssi);
  Serial.println("}");
}

// Komut cozumleme (JSON) — basit string parser
void processCommand(const String& json) {
  if (json.indexOf("\"action\":\"start\"") >= 0) {
    // Enerjiyi ac, testleri calistir
  } else if (json.indexOf("\"action\":\"set_mode\"") >= 0) {
    if (json.indexOf("\"mode\":\"auto\"") >= 0) {
      // Auto moda gec
    } else if (json.indexOf("\"mode\":\"manual\"") >= 0) {
      // Manuel moda gec
    }
  } else if (json.indexOf("\"action\":\"set_target\"") >= 0) {
    // Extract az, el from JSON
  } else if (json.indexOf("\"action\":\"emergency_stop\"") >= 0) {
    // Motorlari durdur, enerjiyi kes
  }
}

void setup() {
  Serial.begin(115200);
  while (!Serial);
}

void loop() {
  // Serial'den komut oku
  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    line.trim();
    if (line.length() > 0) processCommand(line);
  }

  // HuskyLens oku (I2C/UART)
  // IMU oku (I2C)
  // PID kontrol
  // Motor sur

  // Telemetri gonder (10 Hz)
  static unsigned long lastTel = 0;
  if (millis() - lastTel >= 100) {
    lastTel = millis();
    Telemetry t;
    t.state = 3; // AUTO_TRACKING
    t.az_act = 152.1;
    t.el_act = 42.0;
    t.uptime = millis();
    sendTelemetry(t);
  }
}
```

---

## ESP32 Referans Kodu (WiFi Bridge)

```cpp
#include <WiFi.h>
#include <WebServer.h>

const char* ssid = "MergenTerminal";
const char* password = "mergen2026";

WiFiServer server(5000);
WiFiClient client;

void setup() {
  Serial.begin(115200);
  Serial1.begin(115200, SERIAL_8N1, 16, 17); // Teensy'ye bagli RX/TX

  WiFi.softAP(ssid, password);
  server.begin();
}

void loop() {
  // ESP32'ye WiFi istemci baglantisi
  if (!client.connected()) {
    client = server.available();
    return;
  }

  // Teensy'den gelen telemetriyi WiFi'ye ilet
  if (Serial1.available()) {
    String line = Serial1.readStringUntil('\n');
    client.println(line);
  }

  // WiFi'den gelen komutu Teensy'ye ilet
  if (client.available()) {
    String line = client.readStringUntil('\n');
    Serial1.println(line);
  }
}
```
