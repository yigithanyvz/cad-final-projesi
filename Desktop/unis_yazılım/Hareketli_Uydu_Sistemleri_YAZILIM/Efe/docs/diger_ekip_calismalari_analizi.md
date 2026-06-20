# Diğer Yazılım Çalışmalarının Analizi

Bu doküman, `yazilim` klasöründe Efe dışındaki mevcut yazılım çalışmalarını özetler.

## Kerim Unis Çalışması

Konum:

```text
kerim unis/
```

Gözlemler:

- `genel bilgi.md`, sistemin açılış, veri toplama, sensör füzyonu, PID kontrol ve telemetri adımlarını doğru sırayla açıklıyor.
- `BTK_Satellite_Terminal/README.md`, KTR için değerli olabilecek daha ileri bir mimari anlatıyor: EKF, SGP4, TLE, PID, güvenlik monitörü ve telemetri.
- `src/main.cpp`, genel döngüyü ayrıntılı şekilde tasarlamış. Ancak çok sayıda başlık dosyası henüz repoda görünmüyor veya uygulanmamış.
- `SensorFusion.cpp`, `SatelliteTracker.cpp`, `PIDController.cpp` dosyaları boş. Bu nedenle çalışma şu an mimari taslak seviyesinde.

Kullanılabilir taraflar:

- Başlatma/kalibrasyon akışı.
- Veri toplama -> sensör füzyonu -> koordinat hesaplama -> PID -> telemetri sıralaması.
- KTR raporunda sistem mimarisi anlatımı için kaynak olabilir.

Eksik taraflar:

- Derlenebilir bütünlük yok.
- EKF/SGP4/PID sınıflarının gerçek implementasyonları eksik.
- Donanım HAL fonksiyonları stub olarak duruyor.

## Simge/Elif Çalışması

Konum:

```text
simge_elif/x.cpp
```

Gözlemler:

- Mama kabı stabilizasyonu için düşük geçiren filtre + PID mantığı kurulmuş.
- İlk versiyona göre düzeltilmiş sürümde `dt`, integral sınırı ve low-pass filtre kullanılmış.
- Bu çalışma temel stabilizasyon fikrini anlatmak için faydalı.

Eksik taraflar:

- Tek dosyalık ve küçük ölçekli örnek.
- Dataset, çıktı dosyası ve tekrar ölçümü yok.
- Azimuth/elevasyon veya QPD/lazer takip kısmı yok.

## Efe Güncel Çalışmasıyla Birleştirme

Efe içinde kurulan yeni C++ simülasyon yapısı, bu çalışmaların kullanılabilir fikirlerini daha sistematik hale getirir:

- Kerim'in 5 adımlı mimarisi genel sistem akışına dahil edildi.
- Simge/Elif'in low-pass/PID stabilizasyon fikri mama kabı temel algoritmasına benzer şekilde C++ yapıya taşındı.
- Efe çalışması, bu fikirleri dataset üreten, CSV sonuç veren ve arayüzle bağlanabilen profesyonel iki ayrı simülasyona ayırır.
