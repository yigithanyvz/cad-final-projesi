# KTR İçin Yazılım Raporu Taslağı

## Yazılım Amacı

Mergen yazılımı, hareketli platform üzerindeki antenin azimuth ve elevasyon eksenlerinde hedefe yönelmesini, platform roll/pitch bozucularına karşı stabilize kalmasını ve lazer/QPD geri beslemesi ile boresight hatasını azaltmasını hedefler.

## Ana Yazılım Alt Sistemleri

| Alt Sistem | Açıklama |
| --- | --- |
| Azimuth/Elevasyon Takip | Uydu/arayüz hedef açısını Kalman filtresinden geçirir, PID ile motor komutu üretir |
| Mama Kabı Stabilizasyonu | IMU roll/pitch verisini Kalman filtresinden geçirir, PID ile X/Y itki komutu üretir |
| Python Arayüz | Hedef açı seçimi, uydu parametresiyle açı hesaplama, simülasyon başlatma ve canlı veri izleme sağlar |
| ROS/Gazebo Hazırlığı | Gelecekte CAD/Gazebo entegrasyonu için paket iskeletini tutar |

## Azimuth/Elevasyon Algoritması

1. Dataset her çalıştırmada yeniden ve gürültülü üretilir.
2. Hedef azimuth/elevasyon değeri arayüzden veya uydu hesabından gelir.
3. Hedef açı Kalman filtresiyle yumuşatılır.
4. QPD hata vektörü varsa hedef açıya offset olarak eklenir.
5. Encoder benzeri mevcut motor açısı ile hedef açı karşılaştırılır.
6. PID kontrolcü PWM benzeri motor komutu üretir.
7. Dişli oranı, hız sınırı ve backlash etkileri plant modelinde uygulanır.
8. Sonuç CSV ve canlı JSON olarak kaydedilir.

## Mama Kabı Algoritması

1. Roll/pitch IMU dataseti her çalıştırmada yeniden üretilir.
2. Ham roll/pitch verisi Kalman filtresiyle temizlenir.
3. Hedef roll/pitch sıfır kabul edilir.
4. Roll hatası X ekseni PID kontrolcüsüne, pitch hatası Y ekseni PID kontrolcüsüne verilir.
5. PID çıktısı lineer itki komutuna çevrilir.
6. Mekanik gecikme ve hareket sınırı plant modelinde uygulanır.
7. Artık roll/pitch hatası ölçülür.

## Güvenli Modun Anlamı

Güvenli mod, sistemin yeni motor hedefi almamasını ve gerçek sistemde motorları durdurmasını temsil eder. Yarışma sisteminde limit dışı açı, acil durdurma, sensör kopması veya motor arızası durumunda kullanılmalıdır. Arayüzde güvenli mod açıkken yeni simülasyon/hareket komutu gönderilmez.

## KTR İçin Kanıt Dosyaları

| Kanıt | Dosya |
| --- | --- |
| Azimuth/elevasyon dataset | `Efe/azimuth_elevation_simulation/results/generated_dataset.csv` |
| Azimuth/elevasyon sonuç | `Efe/azimuth_elevation_simulation/results/simulation_output.csv` |
| Azimuth/elevasyon özet | `Efe/azimuth_elevation_simulation/results/summary.md` |
| Mama kabı dataset | `Efe/mama_kabi_stabilization_simulation/results/generated_imu_dataset.csv` |
| Mama kabı sonuç | `Efe/mama_kabi_stabilization_simulation/results/stabilization_output.csv` |
| Mama kabı özet | `Efe/mama_kabi_stabilization_simulation/results/summary.md` |

## KTR İçin Geliştirilmesi Gerekenler

- Gerçek motor, encoder ve IMU modeli seçilmeli.
- Gerçek dişli oranı ve backlash ölçümleri konfigürasyona işlenmeli.
- QPD/lazer donanımı netleşince hata modeli güncellenmeli.
- CSV çıktılarından grafik üreten otomatik raporlama eklenmeli.
- CAD hazır olduğunda Gazebo simülasyonuna geçilmeli.

## Son C++ Simülasyon Sonuçları

Azimuth/elevasyon C++ simülasyonu:

| Metrik | Değer |
| --- | ---: |
| İlk kilitlenme zamanı | 4.19 s |
| 8 sn sonrası ortalama hata | 0.434 deg |
| 8 sn sonrası kilit oranı | 99.23 % |

Mama kabı C++ stabilizasyon simülasyonu:

| Metrik | Değer |
| --- | ---: |
| İlk stabil zaman | 0.24 s |
| 8 sn sonrası ortalama hata | 0.305 deg |
| 8 sn sonrası stabil oran | 100 % |

Bu değerler gerçek donanım testi değildir; ancak KTR öncesi algoritmanın tutarlı çalıştığını gösteren sayısal doğrulama kanıtıdır.
