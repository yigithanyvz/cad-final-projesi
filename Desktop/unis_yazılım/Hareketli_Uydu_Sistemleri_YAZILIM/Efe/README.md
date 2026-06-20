# Mergen Efe Yazılım Alanı

Bu alan, Mergen projesindeki algoritma ve simülasyon çalışmalarını tutar. Güncel doğrulama çekirdeği C++ ile yazılmıştır.

## Klasörler

| Klasör | Görev |
| --- | --- |
| `cpp_core` | Ortak C++ PID, Kalman, eksen modeli, yardımcı matematik ve canlı JSON yazımı |
| `azimuth_elevation_simulation` | Uydu/arayüz hedef açısını Kalman + PID ile motorlara aktaran simülasyon |
| `mama_kabi_stabilization_simulation` | IMU roll/pitch verisini Kalman + PID ile X/Y stabilizasyon motorlarına aktaran temel simülasyon |
| `mergen_ws` | ROS 2 Humble/Gazebo için ileride kullanılacak workspace iskeleti |
| `firmware_reference` | Teensy/STM32 tarafına taşınabilecek sade C++ kontrol çekirdeği |
| `docs` | Sistem mimarisi, şartname matrisi ve Gazebo yol haritası |

## Ana Çalıştırma

```bat
cd C:\Users\MDH\Desktop\unis\yazilim
simülasyon_çalıştır.bat
```

Belirli hedef açıyla çalıştırma:

```bat
simülasyon_çalıştır.bat 135 42
```

Bu komut iki C++ simülasyonu derler ve çalıştırır.
