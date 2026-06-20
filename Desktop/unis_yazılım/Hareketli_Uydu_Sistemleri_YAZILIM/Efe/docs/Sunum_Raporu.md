# Mergen Yazılım Sunum Raporu

## Projede Ne Yapıyoruz?

Mergen, hareketli bir platform üstünde çalışan uydu terminalidir. Platform sallansa bile antenin hedef noktaya bakması gerekir. Yazılım tarafında hedefimiz, sensörlerden gelen veriyi işleyip motorlara doğru komutu vermektir.

## Şu An Kurulan Sistem

Gerçek donanım ve Gazebo şu an kullanılmadığı için iki ayrı C++ simülasyon kuruldu.

1. Azimuth/elevasyon simülasyonu.
2. Mama kabı stabilizasyon simülasyonu.

Bu iki simülasyon her çalıştırmada yeni dataset üretir. Böylece aynı sabit veriyle değil, değişen ve daha gerçekçi gürültülü verilerle algoritma denenir.

## Azimuth/Elevasyon Takip

Bu bölüm antenin sağ-sol ve yukarı-aşağı hareketini temsil eder. Uydu takibinden veya arayüzden hedef açı gelir. Bu hedef açı Kalman filtresiyle yumuşatılır. Sonra PID kontrolcüye verilir. PID çıktısı motor komutuna dönüşür.

## Mama Kabı Stabilizasyonu

Bu bölüm platformun roll/pitch sallantısını azaltmayı temsil eder. IMU verisi Kalman filtresinden geçer. Roll ve pitch hataları PID kontrolcülere girer. Çıkış, X/Y motor düzeltmesi olarak kaydedilir.

## Arayüz

Python arayüz üzerinden hedef açı girilebilir, Türksat 4B/5A için yaklaşık açı hesaplanabilir ve C++ simülasyon başlatılabilir. Arayüz canlı JSON dosyalarını okuyarak motor açılarını ve hata değerlerini gösterir.

## Neden Bu Yapı Profesyonel?

- Algoritma çekirdeği C++ ile yazıldı.
- Simülasyonlar ayrı klasörlere ayrıldı.
- Dataset her çalıştırmada değişiyor.
- Sonuçlar CSV ve Markdown olarak kaydediliyor.
- Arayüz simülasyon sonuçlarını canlı izliyor.
- KTR'ye doğrudan aktarılabilecek rapor dosyaları üretildi.
