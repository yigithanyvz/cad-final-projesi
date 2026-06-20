# UniS Mergen Yeni Çalışma Ortamı Özeti

Bu doküman, bugüne kadar UniS/Mergen projesinde yapılan işleri yeni bir çalışma ortamına hızlıca aktarmak için hazırlanmıştır.

## 1. Proje Kimliği

| Başlık | Bilgi |
| --- | --- |
| Takım adı | UniS |
| Proje adı | Mergen |
| Yarışma | Hareketli Uydu Terminali Yarışması |
| Kategori | Üniversite ve Üzeri Kategorisi |
| Ana hedef | Hareketli platform üzerinde anten yönelimini hedefte tutabilen uydu terminali konsepti geliştirmek |

## 2. Projenin Kısa Tanımı

Mergen, hareketli bir platform üzerinde çalışan, azimuth ve elevasyon eksenlerinde hedefe yönelim sağlayan ve platform hareketlerinden kaynaklanan roll/pitch bozucularını azaltmayı hedefleyen bir uydu terminali çalışmasıdır.

Projede şu ana kadar üç ana alan üzerinde çalışıldı:

- Yazılım algoritması ve C++ simülasyonları.
- Python tabanlı kontrol/izleme arayüzü.
- KTR/sunum/afiş için dokümantasyon ve tanıtım materyalleri.

## 3. Güncel Ana Klasör Yapısı

```text
yazilim/
  simülasyon_çalıştır.bat
  arayüz_çalıştır.bat
  README.md
  Mergen_Yazilim_Calismalari_Raporu.md
  Mergen_Yazilim_Calismalari_Raporu.pdf
  generate_mergen_yazilim_report_pdf.py
  arayuz/
  afis/
  Efe/
    cpp_core/
    azimuth_elevation_simulation/
    mama_kabi_stabilization_simulation/
    docs/
    firmware_reference/
    mergen_ws/
```

## 4. En Önemli Dosyalar

| Dosya/Klasör | Açıklama |
| --- | --- |
| `simülasyon_çalıştır.bat` | C++ simülasyonları derleyip çalıştırır |
| `arayüz_çalıştır.bat` | Python arayüzü açar |
| `Efe/cpp_core/include/mergen_core.hpp` | Ortak C++ PID, Kalman, eksen modeli ve yardımcı fonksiyonlar |
| `Efe/azimuth_elevation_simulation/src/main.cpp` | Azimuth/elevasyon uydu takip simülasyonu |
| `Efe/mama_kabi_stabilization_simulation/src/main.cpp` | Mama kabı temel stabilizasyon simülasyonu |
| `arayuz/main.py` | Python arayüz; C++ simülasyonu başlatır ve canlı verileri gösterir |
| `Efe/docs/KTR_Yazilim_Raporu.md` | KTR'ye eklenebilecek yazılım raporu taslağı |
| `Efe/docs/Sunum_Raporu.md` | Sunum için sade anlatım raporu |
| `Efe/docs/diger_ekip_calismalari_analizi.md` | Diğer ekip çalışmalarının analizi |
| `Mergen_Yazilim_Calismalari_Raporu.pdf` | Genel yazılım sistemi raporu |
| `afis/mergen_tanitim_afisi.pdf` | Proje tanıtım afişi |
| `afis/mergen_tanitim_afisi.svg` | Düzenlenebilir afiş dosyası |

## 5. Yazılımda Yapılan Ana İşler

### 5.1 C++ Ortak Çekirdek

`Efe/cpp_core/include/mergen_core.hpp` içinde ortak kontrol bileşenleri yazıldı:

- `PidController`: Hedef ve mevcut değer arasındaki hatadan motor komutu üretir.
- `KalmanFilter1D`: Gürültülü sensör/hedef verisini filtreler.
- `RateLimitedAxis`: Motor, dişli oranı, hız limiti ve backlash etkisini basitleştirilmiş olarak modeller.
- `writeLiveState`: Python arayüzün okuyacağı canlı JSON telemetri dosyasını yazar.
- `wrapDegrees`: 0-360 derece azimuth ekseninde açı farkını doğru hesaplar.

### 5.2 Azimuth/Elevasyon Simülasyonu

Klasör:

```text
Efe/azimuth_elevation_simulation/
```

Amaç:

- Uydu/arayüz hedef açısını alır.
- Her çalıştırmada değişen gürültülü dataset üretir.
- Hedef açıyı Kalman filtresinden geçirir.
- QPD benzeri hedef sapması offsetini simüle eder.
- PID ile azimuth/elevasyon motor komutu üretir.
- Motor/dişli davranışını basitleştirilmiş plant modeliyle uygular.
- Sonuçları CSV, Markdown ve JSON olarak kaydeder.

Çıktılar:

```text
Efe/azimuth_elevation_simulation/results/generated_dataset.csv
Efe/azimuth_elevation_simulation/results/simulation_output.csv
Efe/azimuth_elevation_simulation/results/summary.md
Efe/azimuth_elevation_simulation/results/live_state.json
```

### 5.3 Mama Kabı Stabilizasyon Simülasyonu

Klasör:

```text
Efe/mama_kabi_stabilization_simulation/
```

Amaç:

- Roll/pitch IMU dataseti üretir.
- Ham roll/pitch değerlerini Kalman filtresinden geçirir.
- Roll hatasını X ekseni PID kontrolüne verir.
- Pitch hatasını Y ekseni PID kontrolüne verir.
- X/Y lineer itki motor komutunu simüle eder.
- Artık roll/pitch hatasını ve stabil oranını ölçer.

Çıktılar:

```text
Efe/mama_kabi_stabilization_simulation/results/generated_imu_dataset.csv
Efe/mama_kabi_stabilization_simulation/results/stabilization_output.csv
Efe/mama_kabi_stabilization_simulation/results/summary.md
Efe/mama_kabi_stabilization_simulation/results/live_state.json
```

## 6. Python Arayüz

Klasör:

```text
arayuz/
```

Ana dosya:

```text
arayuz/main.py
```

Arayüzün yaptığı işler:

- Manuel azimuth/elevasyon hedefi girme.
- Türksat 4B/5A için yaklaşık hedef açı hesaplama.
- C++ simülasyonları başlatma.
- C++ tarafından üretilen `live_state.json` dosyalarını okuyarak canlı telemetri gösterme.
- Anlık veriyi CSV log dosyasına kaydetme.
- Güvenli mod mantığını temsil etme.

Güvenli modun anlamı:

- Gerçek sistemde motorları durdurma ve yeni hedef komutlarını engelleme modudur.
- Limit dışı açı, sensör kopması, motor arızası veya acil durdurma durumunda kullanılmalıdır.
- Arayüzde güvenli mod açıkken yeni simülasyon/hareket komutu gönderilmez.

## 7. Çalıştırma Adımları

### 7.1 G++ Gereksinimi

Windows'ta C++ simülasyonlar için `g++` gerekir. Bu ortamda MSYS2 üzerinden şu yol kullanıldı:

```text
C:\msys64\ucrt64\bin\g++.exe
```

`simülasyon_çalıştır.bat` dosyası bu yolu otomatik PATH'e ekler.

### 7.2 Simülasyonu Çalıştırma

```bat
cd C:\Users\MDH\Desktop\unis\yazilim
simülasyon_çalıştır.bat
```

Belirli hedef açıyla:

```bat
simülasyon_çalıştır.bat 135 42
```

Burada:

- `135`: azimuth hedef açısı
- `42`: elevasyon hedef açısı

### 7.3 Arayüzü Çalıştırma

```bat
cd C:\Users\MDH\Desktop\unis\yazilim
arayüz_çalıştır.bat
```

## 8. Son Simülasyon Sonuçları

MSYS2 `g++ 15.2.0` ile iki C++ simülasyon derlenip çalıştırıldı.

### 8.1 Azimuth/Elevasyon

| Metrik | Değer |
| --- | ---: |
| İlk kilitlenme zamanı | 4.19 s |
| Ortalama boresight hatası | 1.214 deg |
| 8 sn sonrası ortalama hata | 0.434 deg |
| Toplam kilit oranı | 97.77 % |
| 8 sn sonrası kilit oranı | 99.23 % |

### 8.2 Mama Kabı Stabilizasyonu

| Metrik | Değer |
| --- | ---: |
| İlk stabil zaman | 0.24 s |
| Ortalama artık eğim hatası | 0.307 deg |
| 8 sn sonrası ortalama hata | 0.305 deg |
| Toplam stabil oran | 99.92 % |
| 8 sn sonrası stabil oran | 100 % |

Not: Bunlar gerçek donanım testi değildir; sayısal simülasyon sonucudur.

## 9. Raporlar ve Tanıtım Materyalleri

### 9.1 Yazılım Raporu

```text
Mergen_Yazilim_Calismalari_Raporu.md
Mergen_Yazilim_Calismalari_Raporu.pdf
```

Bu raporda yazılım mimarisi, C++ simülasyonlar, Python arayüz, diğer ekip çalışmaları ve son test sonuçları anlatıldı.

### 9.2 KTR Yazılım Taslağı

```text
Efe/docs/KTR_Yazilim_Raporu.md
```

KTR’ye doğrudan aktarılabilecek yazılım bölümü taslağıdır.

### 9.3 Sunum Raporu

```text
Efe/docs/Sunum_Raporu.md
```

Projeyi sunum diliyle anlatan kısa ve sade dokümandır.

### 9.4 Diğer Ekip Çalışmaları Analizi

```text
Efe/docs/diger_ekip_calismalari_analizi.md
```

Kerim ve Simge/Elif tarafındaki yazılım çalışmalarının güçlü/eksik tarafları özetlendi.

### 9.5 Afiş

```text
afis/mergen_tanitim_afisi.pdf
afis/mergen_tanitim_afisi.svg
```

Teknik sır vermeyen, tanıtım amaçlı A3 afiş tasarlandı.

## 10. Afiş İçeriği

Afişte yer alanlar:

- UniS logosu ve takım adı.
- Proje adı: Mergen.
- Kategori: Hareketli Uydu Terminali.
- Uludağ Yazılım Topluluğu’nun ilk TEKNOFEST takımı vurgusu.
- Amaç, vizyon, görev, yapılan işler.
- Takım üyeleri.
- Ortada uydu/anten temalı görsel.

Teknik sır vermemek için afişe şunlar konmadı:

- PID/Kalman detayları.
- Kod veya algoritma ayrıntısı.
- CAD ölçüleri.
- Mekanik çözüm detayları.

## 11. Diğer Ekip Çalışmalarından Öğrenilenler

### Kerim Çalışması

Güçlü taraflar:

- Başlatma, veri toplama, sensör füzyonu, PID ve telemetri sıralaması doğru kurgulanmış.
- EKF, SGP4, TLE gibi ileri mimari fikirleri var.

Eksikler:

- Bazı C++ dosyaları boş.
- Başlık dosyalarının tamamı mevcut değil.
- Derlenebilir bütünlük henüz yok.

### Simge/Elif Çalışması

Güçlü taraflar:

- Mama kabı için düşük geçiren filtre + PID fikri kurulmuş.
- `dt`, integral sınırı ve low-pass filtre kullanımı iyi bir başlangıç.

Eksikler:

- Tek dosyalık örnek seviyesinde.
- Dataset, çıktı dosyası, tekrar ölçümü ve azimuth/elevasyon kısmı yok.

## 12. Yeni Ortamda Öncelikli Yapılacaklar

1. `simülasyon_çalıştır.bat` ile C++ simülasyonları tekrar çalıştır.
2. Çıktı CSV dosyalarını kontrol et.
3. `arayüz_çalıştır.bat` ile arayüzü açıp hedef açı vererek test et.
4. Gerçek motor, encoder ve IMU modeli seçilince C++ parametrelerini güncelle.
5. CSV çıktılarından otomatik grafik üreten modül ekle.
6. CAD hazır olduğunda Gazebo entegrasyonuna geç.
7. KTR raporuna C++ simülasyon çıktıları, grafikler ve sistem mimarisini ekle.

## 13. Yeni Ortama Taşınacak Minimum Paket

Yeni çalışma ortamına en az şu dosyalar taşınmalıdır:

```text
yazilim/simülasyon_çalıştır.bat
yazilim/arayüz_çalıştır.bat
yazilim/README.md
yazilim/arayuz/
yazilim/Efe/cpp_core/
yazilim/Efe/azimuth_elevation_simulation/
yazilim/Efe/mama_kabi_stabilization_simulation/
yazilim/Efe/docs/
yazilim/Mergen_Yazilim_Calismalari_Raporu.md
yazilim/Mergen_Yazilim_Calismalari_Raporu.pdf
yazilim/afis/
```

ROS/Gazebo daha sonra kullanılacaksa ayrıca taşınmalı:

```text
yazilim/Efe/mergen_ws/
```

## 14. Kısa Özet

Bugüne kadar Mergen projesinde C++ tabanlı iki ayrı algoritma simülasyonu, Python arayüz, KTR/sunum rapor taslakları, diğer ekip çalışmalarının analizi ve tanıtım afişi hazırlandı. Simülasyonlar çalıştırıldı ve şartnamedeki 8 saniye hedefi sayısal ortamda karşılandı. Yeni çalışma ortamında bu yapı, KTR’ye hazırlanacak grafikler ve gerçek donanım/Gazebo entegrasyonu için temel alınmalıdır.
