# Azimuth ve Elevasyon Uydu Takip Simülasyonu

Bu klasör, ÖTR ve şartnamedeki azimuth/elevasyon takip algoritmasını C++ ile simüle eder.

Simülasyon akışı:

1. Her çalıştırmada yeni, gürültülü dataset üretilir.
2. Dataset satır satır okunur.
3. Uydu/arayüz hedef açısı Kalman filtresinden geçirilir.
4. Encoder benzeri mevcut motor açısı ile hedef açı karşılaştırılır.
5. Azimuth ve elevasyon PID kontrolcüleri motor komutu üretir.
6. Motor/dişli plant modeli komutu fiziksel hareket gibi uygular.
7. Sonuç CSV, özet rapor ve canlı durum JSON dosyası üretilir.

Çıktılar:

- `results/generated_dataset.csv`
- `results/simulation_output.csv`
- `results/summary.md`
- `results/live_state.json`
