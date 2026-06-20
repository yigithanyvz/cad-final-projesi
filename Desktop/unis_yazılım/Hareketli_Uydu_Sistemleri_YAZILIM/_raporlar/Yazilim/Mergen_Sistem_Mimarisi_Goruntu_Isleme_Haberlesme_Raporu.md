# MERGEN PROJESI

## Sistem Mimarisi, Goruntu Isleme ve Donanim Haberlesme Raporu

Bu dokuman, Mergen Projesi kapsaminda gerceklestirilen teknik beyin firtinasi ve degerlendirmeler sonucunda kararlastirilan sistem mimarisini, gorev dagilimlarini, donanim secimlerini ve veri haberlesme protokollerini ozetlemek amaciyla hazirlanmistir.

## 1. Donanim Bilesenleri ve Rol Analizi

Sistemde kullanilacak temel donanim bilesenleri ve bu bilesenlerin secilme gerekceleri asagida detaylandirilmistir:

- **Teensy 4.1 (Alt Sistem Lideri / Gercek Zamanli Denetleyici):** 600 MHz saat hizi (ARM Cortex-M7) ve zengin donanim cevre birimleri (8x UART, yerlesik Ethernet, 3x CAN Bus) ile sistemin ana yurutucusudur. Motor kontrolu (PID), telemetri paketleme ve gercek zamanli kritik dongulerin yonetiminden sorumludur.

- **OV3660 3MP USB Kamera Modulu:** Hedef takibi prototipi icin secilmistir. Tak-calistir (UVC surucusuz) yapisi sayesinde OpenCV entegrasyonu kolaydir. 64 derece dar gorus acisina (FOV) sahip oldugundan, mekanik yonlendirme/gimbal sistemleriyle desteklenmesi veya ilerleyen asamalarda genis acili lenslerle optimize edilmesi planlanmaktadir.

- **Bilgisayar (Merkezi Islem Birimi - PC):** Yuksek matris hesaplama gucu, RAM ve GPU kapasitesi sayesinde goruntu islemenin (OpenCV/nesne takibi) yapilacagi ana platformdur.

## 2. Mimari Tasarim ve Gorev Dagilimi

Mikrokontrolculerin (Teensy 4.1 veya alternatif olarak dusunulen Raspberry Pi Pico gibi) RAM ve islemci mimarileri, yuksek cozunurluklu goruntu matrislerini (frame) gercek zamanli islemek icin uygun degildir. Bu durum darboğaza (bottleneck) ve sistem kilitlenmelerine yol acabilir. Bu nedenle projede "Dagitik Islem" (Distributed Processing) mimarisi secilmistir.

| Birim | Gorevleri | Veri Trafigi |
| --- | --- | --- |
| Kamera (USB) | Goruntuyu anlik yakalama ve iletme | Ham video akisi dogrudan PC'ye |
| Bilgisayar (PC) | OpenCV ile hedef tespiti ve X/Y koordinat hesabi | Kameradan veri alir, Teensy'ye hedef koordinati yollar |
| Teensy 4.1 | Motor yonlendirme, sensor okuma, telemetri uretimi | PC'den koordinat alir, PC'ye anlik telemetri basar |

**Onemli Karar:** Maliyet, agirlik ve islem kararliligi dengesi gozetilerek; goruntu isleme karti olarak araya Raspberry Pi Pico veya pahali ek kartlar koymak yerine, kameranin dogrudan bilgisayara baglanmasi ve Teensy ile cift yonlu seri haberlesme yapilmasi kararlastirilmistir.

## 3. Kablo Secimi ve Fiziksel Katman (Physical Layer)

Sistemin en kritik ihtiyaclarindan biri, bilgisayardan Teensy'ye koordinat akisi saglanirken ayni anda Teensy'den bilgisayara sistem durum verilerinin (telemetri) kesintisiz iletilmesidir. Bunun icin:

- **Kablo Turu:** Kaliteli, elektromanyetik parazit korumali (ferrit bogumlu) standart USB kablosu.
- **Haberlesme Tipi:** Full-duplex (tam cift yonlu) seri haberlesme. USB hattinda uplink (koordinat/hata verisi gonderme) ve downlink (telemetri alma) islemleri ayni baglanti uzerinden yurutulebilir.
- **Hiz Kapasitesi:** Teensy 4.1'in USB High Speed destegi, bu hafif veri trafigi icin yeterli kararliligi saglar.

## 4. Protokol ve Veri Paketleme Mimarisi (JSON)

Verilerin kaybolmasini, sirasinin kaymasini onlemek ve gelecekte sisteme eklenebilecek yeni sensor verilerine karsi esnekligi korumak amaciyla duz metin (plain text) yerine JSON formatinin kullanilmasi degerlendirilmistir. Veri paketlerinin sonu satir sonu karakteri ile isaretlenecektir.

### 4.1. Python (PC) Tarafi Ornek Iletisim Yapisi

Goruntu isleme dongusunu aksatmamak icin telemetri okuma islemi ayri bir thread uzerinden asenkron yonetilir:

```python
import serial
import json
import threading

ser = serial.Serial("COM3", 115200, timeout=0.1)


def telemetri_oku():
    while True:
        if ser.in_waiting > 0:
            gelen = ser.readline().decode("utf-8").strip()
            print(f"Telemetri: {gelen}")


threading.Thread(target=telemetri_oku, daemon=True).start()

while True:
    veri = {"x": 150, "y": 220, "lock": True, "cnt": 1}
    ser.write((json.dumps(veri) + "\n").encode("utf-8"))
```

### 4.2. Teensy 4.1 (Arduino C++) Tarafi Ornek Karsilama Yapisi

Gelen veriler ArduinoJson kutuphanesi yardimiyla deserialize edilir ve hata kontrolleriyle guvenli kilinir:

```cpp
#include <ArduinoJson.h>

unsigned long sonZaman = 0;

void loop() {
    if (Serial.available() > 0) {
        String gelenJson = Serial.readStringUntil('\n');
        StaticJsonDocument<128> doc;
        DeserializationError error = deserializeJson(doc, gelenJson);

        if (!error) {
            int target_x = doc["x"];
            int target_y = doc["y"];
            // Motor kontrol fonksiyonlari burada tetiklenecek.
        }
    }

    if (millis() - sonZaman >= 100) {
        sonZaman = millis();
        Serial.println("{\"volt\":11.8,\"status\":1}");
    }
}
```
