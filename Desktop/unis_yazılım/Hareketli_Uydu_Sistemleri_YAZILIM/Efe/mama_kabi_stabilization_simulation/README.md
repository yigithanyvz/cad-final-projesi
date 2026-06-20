# Mama Kabı Stabilizasyon Simülasyonu

Bu klasör, ÖTR'deki mama kabı alt sisteminin yazılım tarafındaki temel kontrol mantığını C++ ile hazırlar.

Mekanik sistem tam hazır olmadığı için burada amaç gerçek mekanik çözüm değil, genel algoritma iskeletidir:

1. IMU roll/pitch verisi üretilir.
2. Veriler Kalman filtresinden geçirilir.
3. Roll ve pitch hataları ayrı PID kontrolcülere verilir.
4. PID çıktıları X/Y itki motor komutuna çevrilir.
5. Motor gecikmesi ve mekanik hareket sınırı modellenir.
6. Sonuç CSV ve özet rapor olarak kaydedilir.

Çıktılar:

- `results/generated_imu_dataset.csv`
- `results/stabilization_output.csv`
- `results/summary.md`
- `results/live_state.json`
