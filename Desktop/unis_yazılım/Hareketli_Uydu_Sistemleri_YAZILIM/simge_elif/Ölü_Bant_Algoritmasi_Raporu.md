# Ölü Bant (Deadband) Algoritmasi - Proje Raporu

## 1. Giris

Ölü bant (deadband), kontrol sistemlerinde küçük hatalarin yok sayilmasi için kullanilan bir tekniktir. Hareketli uydu terminali projesinde, azimuth ve elevasyon motorlarinin çok küçük açi hatalarinda sürekli titremesini (hunting) önlemek için kullanilir. Bu sayede motor sürücüleri gereksiz yere yorulmaz, güç tüketimi azalir ve mekanik asinma minimuma iner.

## 2. Projede Kullanilan Ölü Bant Algoritmalari

### 2.1 Gömülü C++ PID Kontrolcü (PIDController.h)

Dosya: kerim unis/BTK_Satellite_Terminal/include/PIDController.h

PID sinifinin compute() metodunda ölü bant su sekilde uygulanir:

```
float error = target - measured;
if (p_.wrap_angle) {
    while (error >  180.0f) error -= 360.0f;
    while (error < -180.0f) error += 360.0f;
}
if (fabsf(error) < p_.deadband) {
    state_.integral    = 0.0f;
    state_.prev_error  = 0.0f;
    state_.output      = 0.0f;
    return 0.0f;
}
```

Algoritma adimlari:
1. Hedef ile ölçüm arasindaki fark (hata) hesaplanir
2. Azimuth ekseni için açi sarmalama uygulanir (-180 ile +180 derece arasi)
3. Hatanin mutlak degeri ölü bant esiginden (config.h: PID_DEADBAND_DEG = 0.1 derece) küçükse:
   - Integral terimi sifirlanir (anti-windup)
   - Önceki hata sifirlanir (türev hesaplamasi için)
   - Çikis sifira set edilir
   - Motor komutu üretilmez (0 döner)
4. Hata esigi asarsa normal PID hesaplamasi devam eder

Bu yaklasim sayesinde:
- Anten hedef açiya ulastiginda (+/-0.1 derece hassasiyetle) motor durur
- Integral sifirlandigi için birikmis hata kalmaz
- Türev terimi sifirlandigi için ani geri dönüslerde spike olusmaz

### 2.2 AntennaController (PIDController.h)

Çift eksenli kontrol yöneticisi olan AntennaController::update_internal() metodunda hedefte olma kontrolü:

```
out.az_on_target = (fabsf(out.az_error_deg) < PID_DEADBAND_DEG * 2.0f);
out.el_on_target = (fabsf(out.el_error_deg) < PID_DEADBAND_DEG * 2.0f);
```

Hedefte olma esigi, ölü bant esiginin 2 kati olarak belirlenmistir (0.2 derece). Bu, sistemin hedefe kilitlendi bilgisini telemetriye göndermesi için kullanilir.

### 2.3 C++ Dataset Simulator (mergen_core.hpp, PidController)

Dosya: Efe/cpp_core/include/mergen_core.hpp

Burada ölü bant dolayli olarak RateLimitedAxis sinifinda backlash mekanizmasi ile uygulanir:

```
if (std::abs(error) <= backlash_deg_) return position_deg_;
```

Backlash (0.08 derece azimuth, 0.05 derece elevasyon) küçük hatalarin motor komutuna dönüsmesini engeller ve mekanik bosluklari taklit eder.

### 2.4 Python Dataset Simulator (dataset_simulator.py - eski versiyon)

Python tabanli simulator Pid sinifinda ölü bant bulunmamaktadir. PID çiktisi sadece minimum ve maximum degerler arasinda clamp edilir.

### 2.5 C++ Stabilizasyon Örnegi (x.cpp)

Dosya: simge_elif/x.cpp

MergenStabilizer sinifinda ölü bant bulunmamaktadir ancak integral windup korumasi vardir:

```
integral = std::clamp(integral + error * dt, -INTEGRAL_LIMIT, INTEGRAL_LIMIT);
```

Bu örnek egitim amaçlidir ve gerçek sistemde ölü bant eklenmesi önerilir.

## 3. Proje Spesifik Ölü Bant Parametreleri

| Parametre | Deger | Açiklama |
| --------- | ----- | -------- |
| PID_DEADBAND_DEG | 0.1 derece | Motor durdurma esigi |
| Azimuth hedefte olma | 0.2 derece | PID_DEADBAND_DEG x 2 |
| Elevasyon hedefte olma | 0.2 derece | PID_DEADBAND_DEG x 2 |
| Azimuth backlash | 0.08 derece | Mekanik bosluk simülasyonu |
| Elevasyon backlash | 0.05 derece | Mekanik bosluk simülasyonu |

## 4. Ölü Bant Uygulamasinin Faydalari

### 4.1 Mekanik Avantajlar
- Motor titresimi (hunting) önlenir: +/- 0.1 derece içinde motor sürekli ileri-geri gitmez
- PWM anahtarlama sayisi azalir, MOSFET/sürücü ömrü uzar
- Redüktör ve disli asinmasi minimuma iner
- Kablo sarmalama mekanizmasi gereksiz yorulmaz

### 4.2 Elektriksel Avantajlar
- Güç tüketimi azalir (motor beklemedeyken çekilen akim düser)
- Elektromanyetik girisim (EMI) seviyesi düser
- Pil ile çalisma durumunda enerji tasarrufu saglanir

### 4.3 Sistem Performansi
- PID integral terimi birikmez, windup önlenir
- Hedef degistiginde hizli yanit verilir (integral sifir)
- Türev terimi sifirlandigi için gürültü amplifikasyonu önlenir
- Kararli durum hatasi (steady-state error) kontrol altinda tutulur

## 5. Ölü Bant Seçiminin Mühendislik Analizi

### 5.1 Esik Degeri Belirleme

Ölü bant esigi (0.1 derece) su faktörlere göre belirlenmistir:
1. Encoder çözünürlügü: Kullanilan encoder'in minimum algilayabildigi açi degisimi
2. Mekanik toleranslar: Redüktör boslugu, disli backlash degerleri
3. Sinyal gürültüsü: IMU ve encoder okumalarindaki standart sapma
4. Hedef uydu isin genisligi: Türksat uydulari için tipik isin genisligi

### 5.2 RSSI ve Kilit Esigi Iliskisi

RSSI_LOCK_THRESHOLD_DB = -90.0 (config.h)

Ölü banttan çikildiginda hata 0.1 dereceyi asmis demektir. Bu durumda RSSI seviyesi kontrol edilir. Eger RSSI -90 dBm'nin altindaysa sistem alarm durumuna geçer.

### 5.3 Takip Hatasi Alarmi

MAX_TRACKING_ERROR_DEG = 5.0 (config.h)

Hata 5 dereceyi asarsa acil durum alarmi devreye girer. Bu, ölü bant esiginin 50 kati büyüklügündedir ve sistemin tamamen hedefi kaybettigi anlamina gelir.

## 6. Algoritmanin Dogrulamasi

### 6.1 Dataset Testi

Azimuth/elevasyon simülasyonunda ölü bant etkisi simulation_output.csv dosyasinda gözlemlenebilir:
- azimuth_deg, elevation_deg (gerçek konum)
- azimuth_motor_pwm, elevation_motor_pwm (PID çiktisi)
- boresight_error_deg (bilesik hata)
- locked (kilit durumu)

Hedefe yaklasildiginda (boresight_error < 0.2 derece) motor PWM degeri sifira iner ve locked=true olur.

### 6.2 Kilit Orani Metrikleri

lock_ratio_percent: Toplam süre boyunca hedefte kalma yüzdesi
settled_lock_ratio_percent: 8. saniyeden sonra hedefte kalma yüzdesi

Bu metrikler ölü bant algoritmasinin basarisi hakkinda nicel veri saglar.

## 7. Ölü Bant Algoritmasinin Sözde Kodu

```
Fonksiyon PID_ile_Ölü_Bant(hedef, ölçülen, dt):
    hata = hedef - ölçülen

    // Azimuth için açi sarmalama
    Eger azimuth_ekseni ise:
        hata = normalize_aci(hata, -180, 180)

    // Ölü bant kontrolü
    Eger |hata| < DEADBAND_ESIGI ise:
        integral = 0
        önceki_hata = 0
        çikis = 0
        Döndür 0  // Motor durdur

    // PID hesaplama (ölü bant asildi)
    integral += hata x dt
    türev = (hata - önceki_hata) / dt
    çikis = Kp x hata + Ki x integral + Kd x türev
    çikis = clamp(çikis, min, max)

    // Anti-windup
    Eger çikis doyumda ve hata ayni yönde ise:
        integral güncellenmez

    önceki_hata = hata
    Döndür çikis
```

## 8. Öneriler ve Gelistirme

1. Adaptif ölü bant: Rüzgar, araç titresimi gibi dis etkenlere göre ölü bant esiginin dinamik ayarlanmasi
2. Histerezis eklenmesi: Ölü banta giris ve çikis esiklerinin farkli olmasi (Schmitt tetikleme benzeri)
3. Ivme tabanli ölü bant: Sadece konum hatasina degil, açisal hiz ve ivmeye de bagli esik belirleme
4. QPD entegrasyonu: Lazer takip modunda ölü bant esiginin QPD hassasiyetine göre otomatik ayarlanmasi

## 9. Sonuç

Ölü bant algoritmasi, hareketli uydu terminalinin kararli çalismasi için kritik öneme sahiptir. Projede 0.1 derece esik degeri ile uygulanan bu algoritma, motor titresimini önler, güç tüketimini azaltir ve sistem ömrünü uzatir. Integral sifirlama ve türev temizleme mekanizmalari sayesinde PID kontrolcünün genel performansi iyilestirilmistir. Bu rapor, algoritmanin projenin tüm bilesenlerindeki uygulamasini kapsamli sekilde belgelemektedir.
