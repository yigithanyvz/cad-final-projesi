# Sistem Mimarisi

Mergen yazilim mimarisi dort katmandan olusur.

| Katman | Gorev |
| --- | --- |
| Algilama | IMU, gyro, encoder, QPD/lazer ve GPS verisini almak |
| Kestirim | Kalman filtresi, quaternion tabanli yonelim ve hata vektoru cikarmak |
| Kontrol | Stabilizasyon, azimuth, elevasyon ve lazer takip PID dongulerini calistirmak |
| Arayuz | Manuel/otomatik mod, uydu secimi, GPS girisi, telemetri ve parametre kaydi |

Veri akisi:

```text
IMU/Gyro -> Kalman + Quaternion -> Stabilizasyon PID -> X/Y motor komutu
GPS + Uydu parametresi -> Azimuth/Elevasyon hedefi -> Motor PID -> Az/El motor komutu
QPD/Lazer -> Hata vektoru -> Aktif takip PID -> Az/El offset duzeltmesi
Encoder -> Gercek motor konumu -> PID geri beslemesi
GUI -> Mod/hedef/parametre -> Kontrol node'lari
```

Kontrol mantigi:

- Sistem acilista kayitli parametreleri yukler.
- Otomatik modda once teorik uydu yonelimi hesaplanir.
- Hedef yakalanamiyorsa spiral arama devreye girer.
- Lazer/QPD sinyali yeterli seviyeye cikarsa aktif takip moduna gecilir.
- Aktif takipte QPD hata vektoru PID ile azimuth/elevasyon offsetine donusturulur.
- IMU stabilizasyon dongusu surekli calisir ve platform roll/pitch bozucularini bastirir.
