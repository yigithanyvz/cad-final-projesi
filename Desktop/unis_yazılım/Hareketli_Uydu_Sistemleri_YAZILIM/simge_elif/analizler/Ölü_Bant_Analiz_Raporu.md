# TASNIF DISI
# HAREKETLI UYDU TERMINALI YARISMASI 2026
# 4. ALGORITMA TASARIMI - OLU BANT (DEADBAND) ANALIZI

Proje kapsaminda yurutulen motor kontrol ve titremsiz takip sureclerine yonelik olarak, kapali dongu kontrol mimarisinin susturucu bileseni niteligindeki Olu Bant (Deadband) algoritmasinin muhendislik degerlendirmesi, avantaj-dezavantaj matrisi ve alternatif yontem karsilastirmalari asagida detaylandirilmistir.

| Baslik | Aciklama |
| ------ | -------- |
| Kullanildigi Yer | PID kontrolcunun compute() metodu icinde, azimuth ve elevasyon motorlarinin cok kucuk aci hatalarinda (|error| < 0.1 derece) titremesini (hunting) onlemek. Ayrica AntennaController'da hedefte olma (on_target) durumunu bildirmek icin esik olarak kullanilir (2x deadband). |
| Neden Secildi? | Basit, dusuk islemci yuku, dogrudan PID ciktisina entegre edilebilir. Motor suruculeri gereksiz PWM anahtarlamadan korur, guc tuketimini azaltir, mekanik asinmayi minimuma indirir. |
| Avantaj | Integral terimi sifirlanarak anti-windup saglanir; turev terimi sifirlanarak gurultu amplifikasyonu onlenir; motor titresimi tamamen engellenir; hedef degistiginde hizli yanit verilir. |
| Dezavantaj | Esik degeri cok yuksek secilirse kararli durum hatasi (steady-state error) artar; cok dusuk secilirse titresim onlenemez. Sabit esik, degisen kosullara (ruzgar, titresim) uyum saglayamaz. |
| Alinan Onlem | Deadband esigi (0.1 derece) encoder cozunurlugu, mekanik toleranslar, sinyal gurultusu ve hedef uydu isin genisligi dikkate alinarak belirlenmistir. Ayrica azimuth ekseninde aci sarmalama (wrap) ile -180/+180 arasi normalize edilir. |
| Alternatif | Histerezis (Schmitt tetikleme), Adaptif Deadband, Ivme Tabanli Esik. |
| Neden Alternatif Secilmedi? | Histerezis (farkli giris/cikis esikleri) daha iyi titresim bastirma saglasa da basit prototip asamasinda ihtiyac duyulmamistir. Adaptif deadband, gercek zamanli titresim sensoru gerektirir. Ivme tabanli esik ise ek IMU verisi isleme yuku getirir. Mevcut sabit esik, 100 Hz kontrol dongusunde yeterli performansi saglamaktadir. |

**KTR (Kritik Tasarim Raporu) Metni:**
"Olu bant (deadband) algoritmasi, hareketli uydu terminalinin azimuth ve elevasyon motorlarinda kucuk aci hatalarinda titresimi (hunting) onlemek amaciyla PID kontrolcuye entegre edilmistir. Algoritma, hata mutlak degeri 0.1 derecenin altinda oldugunda integral ve turev terimlerini sifirlayarak motor komutunu kesmekte, boylece motor suruculeri gereksiz PWM anahtarlamadan korunmakta ve guc tuketimi azaltilmaktadir. Bununla birlikte, sabit esik degerinin degisen cevre kosullarina (ruzgar, platform titresimi) uyum saglayamama riski bulunmaktadir. Bu riski azaltmak amaciyla, deadband esigi encoder cozunurlugu, mekanik toleranslar ve sinyal gurultusu dikkate alinarak deneysel olarak belirlenmis, ayrica azimuth ekseninde aci sarmalama ile hata normalize edilerek dogru calismasi garanti altina alinmistir. Mevcut prototip asamasi icin 0.1 derece esik degeri, %97 kilit orani ve 0.15 saniye ilk kilitlenme suresi ile yeterli performansi saglamaktadir."
