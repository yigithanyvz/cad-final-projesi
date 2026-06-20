# Gazebo ve CAD Entegrasyon Yol Haritasi

1. SolidWorks montaji tamamlanir ve her ana parca ayri mesh olarak export edilir.
2. Gazebo icin `dae` tercih edilir; sadece geometrik dogrulama icin `stl` yeterlidir.
3. Mesh dosyalari `mergen_description/meshes/` altina yerlestirilir.
4. URDF/Xacro modelinde her parca bir `link`, hareketli baglantilar `joint` olarak tanimlanir.
5. Azimuth ekseni continuous joint, elevasyon ekseni 0-90 derece limitli revolute joint olur.
6. Stabilizasyon mekanizmasi CAD tamamlanana kadar iki adet prismatic joint ile modellenir.
7. IMU sensoru Gazebo plugin ile terminal govdesine baglanir.
8. Motorlar once Gazebo joint position controller ile, sonra gerekirse `ros2_control` ile surulur.
9. Stewart platform bozucu hareketi roll/pitch/yaw sinyali ureten test node'u ile simule edilir.
10. Kontrol node'u IMU, encoder ve QPD benzeri hata verisini alip motor komutlarini yayinlar.
11. Python arayuz ayni topic ve servislere baglanarak manuel/otomatik komut verir.

CAD hazir degilken dogrulama sirasi:

1. Dataset ile IMU roll/pitch/yaw verisi uretilir.
2. Kalman filtresi gurultulu acilari temizler.
3. Stabilizasyon PID ciktilari X/Y mekanizma komutuna donusturulur.
4. QPD hata verisi sanal olarak uretilir.
5. Azimuth/elevasyon PID ciktilari hedefe kilitlenme davranisi icin izlenir.
6. Sonuclar CSV olarak kaydedilir ve KTR icin grafik/tabloya donusturulur.
