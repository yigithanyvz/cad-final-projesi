# Sartname Karsilama Matrisi

| Sartname Istegi | Yazilim Karsiligi | Durum |
| --- | --- | --- |
| Azimuth 0-360 derece surekli donus | `mergen_control` azimuth PID ve URDF continuous joint | Tasarlandi |
| Elevasyon 0-90 derece hareket | Elevation PID, limit kontrolu ve URDF joint limit | Tasarlandi |
| Manuel mod | Python GUI `ManualCommand`, ROS servis tasarimi | Tasarlandi |
| Otomatik mod | IMU, Kalman, QPD, PID ve hedef state machine | Tasarlandi |
| IMU/Gyro ile stabilizasyon | `KalmanFilter1D`, quaternion estimator, stabilization controller | Tasarlandi |
| Lazer tabanli takip | QPD hata vektoru ve aktif geri besleme PID | Tasarlandi |
| Hedefe tekrar yonelim 8 sn | Lock state machine ve zaman hedefi | Tasarlandi |
| 5 dk takip testi | Dataset ve Gazebo test senaryosu icin altyapi | Tasarlandi |
| GPS manuel giris | Python GUI uydu yonelim hesabi | Tasarlandi |
| Turksat 4B/5A yonelim | `satellite_pointing.py` geostationary hesap | Tasarlandi |
| Parametrelerin kalici saklanmasi | `config/default_params.yaml`, GUI JSON config | Tasarlandi |
| Bilgisayar/tablet arayuzu | Tkinter tabanli Python arayuz | Tasarlandi |
| CAD-Gazebo entegrasyonu | `mergen_description` mesh/URDF iskeleti | Tasarlandi |
