# Mergen Yazılım Sistemi ve C++ Simülasyon Raporu

## 1. Amaç

Bu rapor, Mergen Hareketli Uydu Terminali için güncellenen yazılım yapısını açıklar. Sistem, ÖTR raporundaki mekanik yaklaşım ve şartnamedeki gereksinimler dikkate alınarak yeniden düzenlenmiştir.

Bu revizyonda ana karar şudur: algoritma çekirdeği C++ ile yazılmıştır, Python sadece arayüz ve kullanıcı etkileşimi için kullanılır. ROS ve Gazebo şimdilik devre dışıdır; CAD ve donanım netleştiğinde tekrar entegre edilecektir.

## 2. Şartname ve ÖTR'ye Göre Yazılım Hedefleri

Şartnameye göre sistemin yazılım tarafında karşılaması gereken ana maddeler şunlardır:

| Gereksinim | Yazılım Karşılığı |
| --- | --- |
| Azimuth 0-360 derece takip | Azimuth C++ PID eksen kontrolü |
| Elevasyon 0-90 derece takip | Limitli elevasyon C++ PID eksen kontrolü |
| IMU/Gyro ile stabilizasyon | Mama kabı C++ Kalman + PID algoritması |
| Manuel mod | Python arayüzden hedef açı gönderme |
| Otomatik mod | Uydu parametresi ile azimuth/elevasyon hedefi hesaplama |
| Lazer/QPD takip | Azimuth/elevasyon hedeflerine QPD offset düzeltmesi |
| 8 saniye altında tekrar yönelim | Simülasyon çıktılarında ilk kilitlenme zamanı ölçümü |
| Arayüz | Python Tkinter tabanlı kontrol ve telemetri ekranı |
| Parametre ve veri kaydı | CSV, Markdown ve canlı JSON sonuç dosyaları |

ÖTR'de anlatılan iki ana mekanik mantık yazılıma ayrı ayrı taşınmıştır:

1. Azimuth/elevasyon anten takip sistemi.
2. Mama kabı stabilizasyon alt sistemi.

## 3. Güncel Klasör Yapısı

```text
yazilim/
  simülasyon_çalıştır.bat
  arayüz_çalıştır.bat
  arayuz/
  Efe/
    cpp_core/
    azimuth_elevation_simulation/
    mama_kabi_stabilization_simulation/
    docs/
    firmware_reference/
    mergen_ws/
```

## 4. Dosyaların Görevleri

| Dosya/Klasör | Görev |
| --- | --- |
| `simülasyon_çalıştır.bat` | C++ simülasyonları derler ve çalıştırır |
| `arayüz_çalıştır.bat` | Python arayüzü başlatır |
| `Efe/cpp_core/include/mergen_core.hpp` | Ortak C++ PID, Kalman, eksen modeli ve canlı JSON yazma fonksiyonları |
| `Efe/azimuth_elevation_simulation/src/main.cpp` | Uydu hedefi -> Kalman -> PID -> motor simülasyonu |
| `Efe/mama_kabi_stabilization_simulation/src/main.cpp` | IMU roll/pitch -> Kalman -> PID -> X/Y motor simülasyonu |
| `arayuz/main.py` | Arayüz, hedef açı girme, simülasyon başlatma ve canlı veri izleme |
| `Efe/docs/KTR_Yazilim_Raporu.md` | KTR'ye eklenebilecek yazılım raporu taslağı |
| `Efe/docs/Sunum_Raporu.md` | Sunumda kullanılabilecek sade anlatım raporu |
| `Efe/docs/diger_ekip_calismalari_analizi.md` | Diğer ekip çalışmalarının analizi |

## 5. C++ Ortak Çekirdek

`mergen_core.hpp`, iki simülasyonun ortak kullandığı temiz C++ çekirdektir.

İçerdiği ana sınıflar:

| Sınıf/Fonksiyon | Görev |
| --- | --- |
| `PidController` | Hedef ve mevcut değer arasındaki hatadan motor komutu üretir |
| `KalmanFilter1D` | Gürültülü sensör/hedef verisini yumuşatır |
| `RateLimitedAxis` | Motor, dişli oranı, hız limiti ve backlash etkisini modeller |
| `writeLiveState` | Arayüzün okuyacağı canlı JSON telemetri dosyasını yazar |
| `wrapDegrees` | Azimuth gibi 0-360 derece dönen eksenlerde açıyı doğru sarmalar |

## 6. Azimuth/Elevasyon Simülasyonu

Konum:

```text
Efe/azimuth_elevation_simulation/
```

Bu simülasyon antenin azimuth ve elevasyon hareketini temsil eder.

Akış:

1. Her çalıştırmada yeni ve rastgele gürültülü dataset üretilir.
2. Dataset içinde hedef azimuth, hedef elevasyon, IMU roll/pitch ve QPD hata verileri bulunur.
3. Hedef açılar Kalman filtresinden geçirilir.
4. QPD hata vektörü hedefe küçük offset olarak eklenir.
5. Roll/pitch etkisi hedefe telafi olarak eklenir.
6. Azimuth ve elevasyon PID kontrolcüleri motor PWM benzeri komut üretir.
7. Dişli oranı, hız limiti ve backlash etkileri plant modelinde uygulanır.
8. Motor açıları, hata ve kilit durumu CSV/JSON olarak kaydedilir.

Çıktılar:

```text
Efe/azimuth_elevation_simulation/results/generated_dataset.csv
Efe/azimuth_elevation_simulation/results/simulation_output.csv
Efe/azimuth_elevation_simulation/results/summary.md
Efe/azimuth_elevation_simulation/results/live_state.json
```

## 7. Mama Kabı Stabilizasyon Simülasyonu

Konum:

```text
Efe/mama_kabi_stabilization_simulation/
```

Bu simülasyon, mekanik alt sistem hazır olmasa bile genel stabilizasyon algoritmasını hazırlar.

Akış:

1. Her çalıştırmada yeni roll/pitch IMU dataseti üretilir.
2. Ham roll/pitch verisi Kalman filtresinden geçirilir.
3. Hedef roll ve pitch sıfır kabul edilir.
4. Roll hatası X motor PID kontrolcüsüne verilir.
5. Pitch hatası Y motor PID kontrolcüsüne verilir.
6. PID çıktıları X/Y lineer itki komutuna dönüştürülür.
7. Mekanik gecikme ve hareket sınırı uygulanır.
8. Artık roll/pitch hatası ve stabil oranı kaydedilir.

Çıktılar:

```text
Efe/mama_kabi_stabilization_simulation/results/generated_imu_dataset.csv
Efe/mama_kabi_stabilization_simulation/results/stabilization_output.csv
Efe/mama_kabi_stabilization_simulation/results/summary.md
Efe/mama_kabi_stabilization_simulation/results/live_state.json
```

## 8. Python Arayüz

Arayüz Python/Tkinter ile yazılmıştır. Algoritma Python'da çalışmaz; C++ simülasyonu başlatır ve C++ tarafından üretilen canlı JSON dosyalarını okur.

Arayüz işlevleri:

- Manuel hedef azimuth/elevasyon girme.
- Türksat 4B/5A için yaklaşık azimuth/elevasyon hesaplama.
- C++ simülasyonu hedef açıyla başlatma.
- Motor açılarını ve hata değerlerini canlı gösterme.
- Anlık telemetriyi CSV olarak kaydetme.
- Güvenli modu açıp kapatma.

Güvenli modun anlamı: gerçek sistemde motorları durdurmak, yeni hedef komutunu engellemek ve limit dışı hareketi önlemek için kullanılır. Arayüzde güvenli mod açıkken yeni simülasyon/hareket komutu gönderilmez.

## 9. Diğer Ekip Çalışmaları

Kerim'in çalışması sistem mimarisi açısından güçlü bir taslak sunar: başlatma, veri toplama, sensör füzyonu, PID ve telemetri sıralaması doğru kurulmuştur. Ancak birçok C++ implementasyon dosyası boş veya başlık dosyaları eksiktir; bu nedenle derlenebilir bütünlük yoktur.

Simge/Elif çalışması mama kabı stabilizasyonu için düşük geçiren filtre + PID fikrini gösterir. Bu fikir güncel mama kabı C++ simülasyonunda daha sistematik şekilde kullanılmıştır.

## 10. Çalıştırma

C++ simülasyonlar için `g++` gerekir.

```bat
cd C:\Users\MDH\Desktop\unis\yazilim
simülasyon_çalıştır.bat
```

Belirli hedef açıyla:

```bat
simülasyon_çalıştır.bat 135 42
```

Arayüz:

```bat
arayüz_çalıştır.bat
```

## 11. KTR İçin Kullanılacak Kanıtlar

| Kanıt | Dosya |
| --- | --- |
| Azimuth/elevasyon dataset | `Efe/azimuth_elevation_simulation/results/generated_dataset.csv` |
| Azimuth/elevasyon sonuç | `Efe/azimuth_elevation_simulation/results/simulation_output.csv` |
| Azimuth/elevasyon özet | `Efe/azimuth_elevation_simulation/results/summary.md` |
| Mama kabı dataset | `Efe/mama_kabi_stabilization_simulation/results/generated_imu_dataset.csv` |
| Mama kabı sonuç | `Efe/mama_kabi_stabilization_simulation/results/stabilization_output.csv` |
| Mama kabı özet | `Efe/mama_kabi_stabilization_simulation/results/summary.md` |
| Diğer ekip analizi | `Efe/docs/diger_ekip_calismalari_analizi.md` |
| KTR yazılım taslağı | `Efe/docs/KTR_Yazilim_Raporu.md` |
| Sunum taslağı | `Efe/docs/Sunum_Raporu.md` |

## 12. Sonuç

Yazılım yapısı C++ algoritma çekirdeği ve Python arayüz olacak şekilde profesyonelce ayrılmıştır. Azimuth/elevasyon takip ve mama kabı stabilizasyon simülasyonları ayrı klasörlerde, ayrı çıktılarla çalışır. Datasetler her çalıştırmada değişir; bu sayede algoritma sabit ve ezberlenmiş veriyle değil, daha gerçekçi gürültülü veriyle test edilir.

Bu yapı KTR için güçlü bir yazılım doğrulama temelidir. Sonraki adım, gerçek motor/IMU/encoder seçimine göre parametreleri güncellemek ve CAD tamamlandığında Gazebo entegrasyonuna geçmektir.

## 13. Son C++ Test Sonuçları

MSYS2 içindeki `g++ 15.2.0` ile iki C++ simülasyonu derlenip çalıştırılmıştır.

Azimuth/elevasyon sonucu:

| Metrik | Değer |
| --- | ---: |
| İlk kilitlenme zamanı | 4.19 s |
| Ortalama boresight hatası | 1.214 deg |
| 8 sn sonrası ortalama hata | 0.434 deg |
| Toplam kilit oranı | 97.77 % |
| 8 sn sonrası kilit oranı | 99.23 % |

Mama kabı stabilizasyon sonucu:

| Metrik | Değer |
| --- | ---: |
| İlk stabil zaman | 0.24 s |
| Ortalama artık eğim hatası | 0.307 deg |
| 8 sn sonrası ortalama hata | 0.305 deg |
| Toplam stabil oran | 99.92 % |
| 8 sn sonrası stabil oran | 100 % |

Bu sonuçlar sayısal simülasyon ortamı için şartnamedeki 8 saniye yönelim beklentisini karşılamaktadır. Nihai doğrulama için aynı algoritmanın Gazebo ve gerçek donanım üzerinde de denenmesi gerekir.
