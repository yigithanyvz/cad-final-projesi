# UniS Mergen Yazılım

Bu klasör Mergen Hareketli Uydu Terminali yazılım çalışmalarını içerir.

## Ana Kullanım

Azimuth/elevasyon ve mama kabı temel stabilizasyon simülasyonlarını C++ ile çalıştırmak için:

```text
simülasyon_çalıştır.bat
```

Arayüzü açmak için:

```text
arayüz_çalıştır.bat
```

## C++ Derleyici Gereksinimi

Simülasyonlar C++ ile yazılmıştır. Windows üzerinde çalıştırmak için `g++` gerekir.

Önerilen kurulum:

- MSYS2 veya MinGW-w64 kur.
- `g++` komutunun terminalde çalıştığını doğrula.
- Sonra `simülasyon_çalıştır.bat` dosyasını çalıştır.

## Güncel Ana Yapı

- `Efe/cpp_core`: Ortak C++ PID, Kalman, eksen modeli ve yardımcı fonksiyonlar.
- `Efe/azimuth_elevation_simulation`: Uydu takip verisi -> Kalman -> PID -> motor simülasyonu.
- `Efe/mama_kabi_stabilization_simulation`: IMU roll/pitch -> Kalman -> PID -> X/Y motor simülasyonu.
- `arayuz`: Python arayüz; C++ simülasyonu başlatır ve canlı çıktıları gösterir.
- `Efe/mergen_ws`: İleride ROS 2 Humble/Gazebo için kullanılacak iskelet.
- `Efe/firmware_reference`: Mikrodenetleyiciye taşınabilecek C++ referans kodları.
- `_raporlar`: KTR, ÖTR, şartname, sunum ve yazılım raporları.
- `_araclar/rapor_uretimi`: Rapor/sunum üretim scriptleri.
- `_arsiv`: Eski veya belirsiz tekil çalışma dosyaları.

## Çıktılar

Azimuth/elevasyon sonuçları:

```text
Efe/azimuth_elevation_simulation/results/
```

Mama kabı sonuçları:

```text
Efe/mama_kabi_stabilization_simulation/results/
```
