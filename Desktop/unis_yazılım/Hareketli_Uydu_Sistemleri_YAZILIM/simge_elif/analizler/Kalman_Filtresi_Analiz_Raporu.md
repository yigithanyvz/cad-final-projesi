# Kalman Filtresi Analiz Raporu - Kamera Tabanli Takip

## 1. Giris

Kalman filtresi, gurultulu olcumlerden sistemin gercek durumunu kestirmek icin kullanilan bir recursive (oz yinelemeli) algoritmadir. Hareketli uydu terminali projesinde, kamera goruntu isleme sensorunden gelen pixel hata sinyalindeki sensor gurultusunu temizlemek ve hedef konumunu daha kararli bir sekilde tahmin etmek icin 1D Kalman filtresi kullanilmaktadir. Bu rapor, kamera tabanli takip simulasyonunda kullanilan Kalman filtresinin analizini sunmaktadir.

## 2. Kalman Filtresi Teorisi

### 2.1 1D Kalman Filtresi Matematigi

1D Kalman filtresi, tek boyutlu durum kestirimi icin kullanilan basit ama guclu bir varyanttir. Iki ana adimdan olusur:

**Predict (Tahmin) Adimi:**
```
p_k = p_{k-1} + q
```

Burada:
- p: Kestirim kovaryansi (belirsizlik olcusu)
- q: Islem (process) gurultu kovaryansi (sistemin ne kadar hizli degistigini modeller)

**Update (Guncelleme) Adimi:**
```
K = p / (p + r)
x = x + K * (measurement - x)
p = p * (1 - K)
```

Burada:
- K: Kalman kazanci (olcume ne kadar guvenilecegini belirler)
- r: Olcum (measurement) gurultu kovaryansi (sensorun ne kadar guvenilir oldugu)
- x: Kestirilen durum (filtrelenmis deger)
- measurement: Sensor olcumu (ham pixel hatasi)

Kalman kazanci K, 0 ile 1 arasinda bir deger alir:
- K -> 1: Olcume cok guven (gurultu az, sensor guvenilir)
- K -> 0: Onceki kestirime guven (gurultu cok, sensor guvenilmez)

### 2.2 Denge Durumu Analizi

1D Kalman filtresi, sabit q ve r parametreleri icin bir denge durumuna (steady-state) ulasir:

K_ss = (q / (2 * r)) * (sqrt(1 + 4 * r / q) - 1)

Projede kullanilan q=0.02, r=0.35 degerleri icin:
K_ss = (0.02 / (2 * 0.35)) * (sqrt(1 + 4 * 0.35 / 0.02) - 1)
K_ss = 0.0286 * (sqrt(1 + 70) - 1)
K_ss = 0.0286 * 7.427
K_ss = 0.212

Denge Kalman kazanci yaklasik 0.21'dir. Bu, filtrenin her adimda olcume yaklasik %21 oraninda guvendigi, %79 oraninda onceki kestirime dayandigi anlamina gelir.

### 2.3 Zaman Sabiti Analizi

1D Kalman filtresinin zaman sabiti (tau), filtreleme davranisini tanimlar:

tau = DT * (1 - K_ss) / K_ss

Proje parametreleri ile (DT = 0.01 sn):
tau = 0.01 * (1 - 0.212) / 0.212
tau = 0.01 * 3.717
tau = 0.0372 saniye (yaklasik 37.2 ms)

Bu, filtrenin bir adim degisiklige yaklasik 37 ms'de yanit verdigi anlamina gelir. Bu deger, 100 Hz kontrol dongusu icin uygun bir gecikme seviyesidir.

## 3. Projede Kullanilan Kalman Filtresi

### 3.1 Kamera Takip Simulasyonu (kamera_takip_simulasyonu.cpp)

Dosya: simge_elif/kamera_takip_simulasyonu.cpp

Kalman1D sinifi:

```
class Kalman1D {
    float q_, r_, x_, p_;
public:
    Kalman1D(float process, float measure, float init = 0.0f)
        : q_(process), r_(measure), x_(init), p_(1.0f) {}

    float update(float measurement) {
        p_ += q_;
        float gain = p_ / (p_ + r_);
        x_ += gain * (measurement - x_);
        p_ *= (1.0f - gain);
        return x_;
    }

    void reset(float init = 0.0f) { x_ = init; p_ = 1.0f; }
};
```

Kamerada iki adet Kalman1D filtresi kullanilir:
- kamera_x_filter: Yatay (azimuth) pixel hatasi icin
- kamera_y_filter: Dikey (elevasyon) pixel hatasi icin

### 3.2 Veri Akisi

```
Kamera Sensaru -> Pixel Hatasi (px_x, px_y) -> Kalman1D -> Filtrelenmis Pixel
-> Pixel/Aci Donusumu (PX_PER_DEG) -> Guven Skoru Carpimi -> PID Kontrol -> Motor
```

### 3.3 Kamera Sensor Modeli

Kamera sensoru, cisim tespiti icin asagidaki parametrelerle modellenmistir:

| Parametre | Deger | Aciklama |
| --------- | ----- | -------- |
| CAMERA_FOV_DEG | 5.0 | Goruntu acisi (+/-5 derece) |
| CAMERA_RES_PX | 640 | Cozunurluk (yatay pixel) |
| PX_PER_DEG | 64.0 | Pixel/derece orani |
| Sensor Gurultusu | +/-3 px | Gaussian gurultu (std=3) |
| Gorus alani | +/-5 | Maksimum algilama acisi |
| Guven skoru | 0.3 - 1.0 | Merkezden uzakliga gore azalir |

Kameranin gorus alani (FOV), QPD'ye gore daha genistir (QPD +/-2 derece, Kamera +/-5 derece). Bu sayede:
- Cisim goruntuden cikmadan once daha genis bir aci araliginda takip yapilabilir
- Ancak cozunurluk ayni pixel sayisinda daha dusuk acisal hassasiyet sunar

## 4. C++ Simulasyon Parametreleri

### 4.1 Kalman Parametreleri

| Parametre | Deger | Aciklama |
| --------- | ----- | -------- |
| KALMAN_PROCESS (q) | 0.02 | Islem gurultu kovaryansi |
| KALMAN_MEASURE (r) | 0.35 | Olcum gurultu kovaryansi |
| Baslangic kovaryansi (p) | 1.0 | Ilk belirsizlik degeri |
| Denge K kazanci | 0.212 | Kararli durum Kalman kazanci |
| Zaman sabiti (tau) | 37.2 ms | Filtre yanit suresi |

### 4.2 Kontrol Parametreleri

| Parametre | Azimuth | Elevasyon | Aciklama |
| --------- | ------- | --------- | -------- |
| Kp | 8.0 | 10.0 | Oransal kazanc |
| Ki | 0.0 | 0.0 | Integral kazanc (kullanilmiyor) |
| Kd | 0.0 | 0.0 | Turev kazanc (kullanilmiyor) |
| Deadband | 0.1 derece | 0.1 derece | Olu bant esigi |
| Max hiz | 60 derece/s | 30 derece/s | Motor limitleri |
| Max cikis | 60 derece/s | 30 derece/s | PID cikis limiti |

### 4.3 Hedef ve Sensor Modeli

| Parametre | Deger | Aciklama |
| --------- | ----- | -------- |
| Hedef Azimuth | 120.0 derece | Sabit hedef konumu |
| Hedef Elevasyon | 30.0 derece | Sabit hedef konumu |
| Hedef salinimi | +/-2 derece Az, +/-1 derece El | Hareketli platform simulasyonu |
| Salinim frekansi | 0.3 rad/s Az, 0.2 rad/s El | Dusuk frekansli platform hareketi |
| Kamera gurultusu | +/-3 pixel Gaussian | Goruuntu sensor gurultusu |

## 5. Analiz Metrikleri

### 5.1 Simulasyon Sonuclari

Kamera takip simulasyonu 500 adim (5 saniye, 100 Hz) icin calistirilmistir:

| Metrik | Deger |
| ------ | ----- |
| Ilk kilitlenme suresi | 0.15 saniye |
| Kilit orani | %97 |
| Maks boresight hatasi | 2.40 derece |
| Kararli durum boresight | ~0.1 derece |
| Deadband | 0.1 derece |

### 5.2 Filtre Performans Degerlendirmesi

Kalman filtresinin kamera uygulamasindaki performansi:

1. **Gurultu Bastirma**: Kamera sensorundeki +/-3 pixel Gaussian gurultu, Kalman cikisinda +/-1 pixel seviyesine indigozlemlenmistir. Bu yaklasik 3:1 oraninda bir gurultu bastirma saglar.

2. **Gecikme**: Denge Kalman kazanci K=0.212, yaklasik 37 ms zaman sabiti olusturur. Bu, 100 Hz kontrol dongusunde 3-4 ornekleme periyoduna esdegerdir.

3. **Gecici Yanit**: Kalman filtresi, hedef hareketindeki ani degisikliklere yaklasik 37 ms icinde uyum saglar. Bu, platformun maksimum 60 derece/s azimuth hizinda yaklasik 2.2 derecelik bir dinamik hataya karsilik gelir.

4. **Duragan Durum**: Kilitli durumda (deadband icinde), Kalman cikisi stabil kalir ve motor titresimine neden olmaz.

### 5.3 q/r Orani Analizi

q/r orani, filtrenin davranisini belirleyen en onemli parametredir:

| q/r Orani | K_ss | Zaman Sabiti | Karakter |
| --------- | ---- | ------------ | -------- |
| 0.01 (q=0.01, r=1.0) | 0.095 | 95 ms | Cok yumusak, yavas |
| 0.057 (q=0.02, r=0.35) | 0.212 | 37 ms | Dengeli (su anki) |
| 0.10 (q=0.035, r=0.35) | 0.270 | 27 ms | Orta hassasiyet |
| 0.50 (q=0.175, r=0.35) | 0.500 | 10 ms | Hassas, gurultulu |
| 1.00 (q=0.35, r=0.35) | 0.618 | 6 ms | Cok hassas, gurultulu |

Su anki q/r=0.057 degeri, kamera sensor gurultusu (+/-3 px) icin dengeli bir filtreleme saglar. Daha yuksek q/r orani, hedef hareketlerine daha hizli yanit verir ancak gurultuyu daha az bastirir.

## 6. QPD ve Kamera Karsilastirmasi

| Ozellik | QPD (Lazer) | Kamera (Goruntu) |
| ------- | ----------- | ---------------- |
| Gorus alani | +/-2 derece | +/-5 derece |
| Cozunurluk | Yok (nor. error) | 640 px, 64 px/derece |
| Gurultu modeli | Gaussian, dusuk | Gaussian, orta (+/-3 px) |
| Kalman ayni mi? | Evet (1D Kalman) | Evet (1D Kalman) |
| Kalman parametreleri | q=0.02, r=0.35 | q=0.02, r=0.35 |
| q/r Orani | 0.057 | 0.057 |
| Ek faktor | Pixel olcekleme | Guven skoru carpimi |

Her iki sensor icin de ayni Kalman parametreleri (q=0.02, r=0.35) kullanilmistir. Kamera sensorunde ayrica bir **guven skoru (confidence)** kavrami vardir: cisim goruntu merkezine ne kadar yakinsa guven o kadar yuksektir (0.3 - 1.0 arasi). Bu skor, Kalman cikisindaki pixel/aci donusumune carpilarak filtrelenmis sinyali olceklendirir.

## 7. Algoritmanin Dogrulamasi

### 7.1 Test Kosullari

- Hedef konumu: Azimuth 120 derece, Elevasyon 30 derece (sabit)
- Platform hareketi: Sinusoidal salinim (+/-2 derece Az, +/-1 derece El)
- Kamera gurultusu: +/-3 pixel Gaussian
- Deadband: 0.1 derece
- PID: Sadece P kontrol (Ki=0, Kd=0)

### 7.2 Kritik Metrikler

1. **Ilk Kilitlenme Suresi**: 0.15 saniye (< 1 saniye hedefi)
2. **Kilit Orani**: %97 (> %95 hedefi)
3. **Maks Boresight**: 2.40 derece (ilk yakalama aninda)
4. **Kararli Durum Boresight**: ~0.1 derece (deadband icinde)

## 8. Kalman Filtresi Sozde Kodu

```
Fonksiyon Kalman1D_Filtrele(olcum):
    // Tahmin (Predict)
    p = p + q

    // Kalman kazanci
    K = p / (p + r)

    // Guncelleme (Update)
    x = x + K * (olcum - x)
    p = p * (1 - K)

    // Filtrelenmis deger
    Dondur x

Baslangic:
    x = 0.0  (ilk kestirim)
    p = 1.0  (yuksek baslangic belirsizligi)
    q = 0.02 (proses gurultusu)
    r = 0.35 (olcum gurultusu)

Her kontrol dongusunde (100 Hz):
    // Kamera ham olcumu (pixel hatasi)
    ham_px = kameradan_cisim_tespiti()

    // Kalman filtreleme
    filtrelenmis_px = Kalman1D_Filtrele(ham_px)

    // Pixel -> Aci donusumu
    aci_hatasi = filtrelenmis_px / PX_PER_DEG * confidence

    // PID kontrol
    motor_hizi = PID(hedef_aci + aci_hatasi, encoder_konumu)
```

## 9. Oneriler ve Gelistirme

1. **Adaptif q/r**: Kamera sensor gurultusu, isik kosullarina gore degisebilir. q ve r parametrelerinin, guven skoruna veya piksel varyansina gore dinamik ayarlanmasi performansi artirabilir.

2. **FOV Disinda Davranis**: Cisim kameranin gorus alanindan ciktiginda Kalman filtresi sifir girisi alir. Bu durumda onceki kestirimin korunmasi veya spiral arama moduna gecilmesi degerlendirilmelidir.

3. **Multi-Rate Kalman**: Kamera (30-60 fps) ile kontrol dongusu (100 Hz) arasindaki frekans farki icin, kamera olcumleri geldikce Kalman guncellemesi yapilmali, gelmedigi zamanlarda sadece predict adimi calistirilmalidir.

4. **Guven Skoru Entegrasyonu**: Guven skoru, Kalman filtresinin r parametresini dinamik olarak degistirmek icin kullanilabilir (dusuk guven = yuksek r).

5. **Boresight Duzeltme**: Kamera kalibrasyonu (intrinsic/extrinsic parametreler) ile pixel hatalarinin acisal sapmaya dogru donusumu saglanmalidir.

## 10. Sonuc

Kamera tabanli takip sisteminde kullanilan 1D Kalman filtresi (q=0.02, r=0.35), +/-3 pixel Gaussian sensor gurultusu altinda %97 kilit orani saglamaktadir. Filtrenin denge Kalman kazanci 0.212 ve zaman sabiti yaklasik 37 ms'dir. Bu degerler, 100 Hz kontrol dongusu icin uygun bir denge noktasidir. QPD tabanli sistemle karsilastirildiginda ayni Kalman parametreleri kullanilmasina ragmen, kamera sensorunde ayrica bir guven skoru mekanizmasi bulunmaktadir. Kamera, QPD'ye gore daha genis gorus alani (+/-5 derece vs +/-2 derece) sunarken, acisal cozunurlugu daha dusuktur.
