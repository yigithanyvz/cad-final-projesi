# TASNIF DISI
# HAREKETLI UYDU TERMINALI YARISMASI 2026
# 4. ALGORITMA TASARIMI - PID KONTROL ANALIZI

Proje kapsaminda yurutulen hassas yonlendirme ve kararli takip sureclerine yonelik olarak, kapali dongu kontrol mimarisinin temel bileseni niteligindeki PID Kontrolcunun muhendislik degerlendirmesi, avantaj-dezavantaj matrisi ve alternatif yontem karsilastirmalari asagida detaylandirilmistir.

| Baslik | Aciklama |
| ------ | -------- |
| Kullanildigi Yer | Kamera goruntu isleme sensorden gelen pixel hatasini motor komutuna donusturmek, azimuth ve elevasyon eksenlerinde antenin hedef uyduya kilitli kalmasini saglamak. |
| Neden Secildi? | Gercek zamanli sistemlerde basit, anlasilir ve dusuk islemci yukuyle yuksek frekansli (100 Hz) kontrol dongusunde calisabilmesi; hata tabanli dogrudan geri besleme saglamasi. |
| Avantaj | Oransal (P) kazanc sayesinde hata aninda motor komutuna donusur; olumlu bant (deadband) mekanizmasi motor titresimini onler, integral ve turev ayriyeten eklenebilir. |
| Dezavantaj | Yalniz P kontrol ile surekli durum hatasi (steady-state error) tamamen giderilemez; integral eklenince windup riski olusur, turev ise gurultuyu amplifiye eder. |
| Alinan Onlem | Kalman filtreler ile sensor gurultusu bastirilmis, deadband (0.1 derece) ile motor hunting onlenmis, anti-windup korumasi (clamp) ve dt dogrulama kontrolleri eklenmistir. |
| Alternatif | LQR (Linear Quadratic Regulator), Model Predictive Control (MPC), Kazanç Planlamali (Gain-Scheduled) Kontrol. |
| Neden Alternatif Secilmedi? | LQR ve MPC dogru sistem modeli gerektirir ve islemci yuku yuksektir; gomulu sistemde 100 Hz dongude PID kadar hafif ve guvenilir degildir. Kazanç planlamali kontrol, sistem dinamigi genis bir calisma araliginda degisiyorsa faydali olabilir ancak mevcut prototip asamasinda ihtiyac duyulmamistir. |

**KTR (Kritik Tasarim Raporu) Metni:**
"PID kontrol algoritmasi, hareketli uydu terminalinin azimuth ve elevasyon eksenlerinde kamera goruntu isleme sensorden alinan pixel hatasini motor komutuna donusturmek ve anteni hedef uyduya kilitli tutmak amaciyla tercih edilmistir. Algoritma, Kalman filtresi ile temizlenmis hata sinyalini oransal kazanc (P) ile olceklendirerek motor hiz komutu uretmekte, deadband esigi (0.1 derece) ile kucuk hatalarda motor titresimini engellemektedir. Bununla birlikte, yalniz P kontrol ile teorik surekli durum hatasinin tamamen giderilememesi ve integral eklendiginde windup riski olusmasi dezavantajlaridir. Bu riskleri azaltmak amaciyla, sensor gurultusu Kalman filtresi ile bastirilmis, deadband mekanizmasi ile motor hunting onlenmis ve anti-windup korumasi (clamp) ile integral birikimi sinirlandirilmistir. Mevcut prototip asamasinda toplanan veriler, P-kontrolun 100 Hz kontrol dongusunde %97 kilit orani ve 0.15 saniye ilk kilitlenme suresi ile yeterli performansi sagladigini gostermektedir."
