1)İlk olarak sistem açıldıgında gerçekleşecek olaylar;
Başlatma ve Kalibrasyon (Initialization - Sadece 1 Kez)
Sistem enerji aldığı anda ilk yaptığı iş "kendini tanımak"tır.

Donanım Testi: IMU, GPS ve motor sürücülere bağlantı var mı?

Sıfır Noktası Belirleme: Anten limit switch'lere çarptırılarak veya manyetik sensörlerle "0 derece" (Home) konumuna getirilir.

Sensör Kalibrasyonu: IMU üzerindeki jiroskobun kaymasını (drift) önlemek için cihaz hareketsizken "bias" değerleri alınır.
2)Veri Toplama Katmanı (Data Acquisition)
Döngü başladığında sistem dış dünyadan gelen verileri okur.

GPS: Enlem, boylam ve irtifa bilgilerini çeker (Terminal nerede?).

IMU (6-Eksen): İvmeölçer ve Jiroskop verileri okunur (Terminal ne yöne bakıyor, eğik mi?).

Uydu Verisi (TLE/SGP4): Takip edilmek istenen uydunun yörünge verileri işlenir (Uydu şu an nerede olmalı?).

Kullanıcı Girişi: Yer istasyonundan (GUI) gelen "Manuel hareket ettir" veya "Otomatik takibe geç" komutları kontrol edilir.
3)Sensör Füzyonu ve Koordinat Hesaplama
Ham veriler "anlamlı bilgiye" dönüştürülür.

Filtreleme: IMU'dan gelen gürültülü veri Extended Kalman Filter (EKF) veya Complementary Filter ile süzülerek net bir "yönelim (orientation)" bilgisi (Roll, Pitch, Yaw) elde edilir.

Koordinat Dönüşümü: Uydunun gökyüzündeki konumu (Azimut/Elevasyon) ile terminalin kendi gövde koordinatları çakıştırılır. Terminal bir araç üzerindeyse ve araç yokuş yukarı duruyorsa, anten bu eğimi telafi etmek için açısını günceller.
4)Karar Mekanizması ve Kontrol (PID)
"Neredeyim ve Nereye Bakmalıyım?" sorusunun cevabı burada verilir.
Hata Hesabı: hata=hedef_acc-mevcut_acc

PID İşleme: Bu hata değeri PID algoritmasına sokulur.

Motor Komutu: PID algoritması çıktı olarak "Motoru şu hızda/şu yöne döndür" bilgisini (PWM veya Step sinyali) üretir.

Güvenlik Kontrolü: Eğer hesaplanan açı antenin fiziksel limitlerinin (kablonun dolanması vb.) dışındaysa hareket durdurulur.
5)Geri Besleme ve Telemetri (Feedback Loop)
Sistem yaptığı işin sonucunu raporlar.

Motor Geri Bildirimi: Encoder verisi okunarak motorun gerçekten hedeflenen yere gidip gitmediği teyit edilir.

Yer İstasyonu Bildirimi: Anlık açılar, sinyal gücü (RSSI) ve hata durumu bilgisayara (GUI) gönderilir.

Döngü Başı: Tüm bu süreç (2'den 5'e kadar) RTOS kullanıyorsan yaklaşık 10ms içinde tamamlanır ve başa döner.











