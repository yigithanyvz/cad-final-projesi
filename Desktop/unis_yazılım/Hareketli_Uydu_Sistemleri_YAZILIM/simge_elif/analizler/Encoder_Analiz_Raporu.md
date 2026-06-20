# TASNİF DIŞI
# HAREKETLİ UYDU TERMİNALİ YARIŞMASI 2026
# 4. ALGORİTMA TASARIMI - ENCODER ANALİZİ

Proje kapsamında yürütülen konum geri beslemesi ve hassas yönlendirme süreçlerine yönelik olarak, kapalı döngü kontrol mimarisinin sensör bileşeni niteliğindeki manyetik encoder konum sensörünün mühendislik değerlendirmesi, avantaj-dezavantaj matrisi ve alternatif yöntem karşılaştırmaları aşağıda detaylandırılmıştır.

| Başlık | Açıklama |
| ------ | -------- |
| Kullanıldığı Yer | Azimuth ve elevasyon eksenlerinde motor miline veya döner eksene yerleştirilen mıknatısın açısal konumunu temassız olarak ölçer; PID kontrolcüye geri besleme sağlar. Her kontrol döngüsünde (100 Hz) okunur, telemetri paketinde (10 Hz) gönderilir. |
| Neden Seçildi? | Manyetik encoder, mil üzerindeki mıknatısın manyetik alan yönünü algılayarak mutlak açısal konumu doğrudan ölçer. Temassız yapısı sayesinde sürtünme ve mekanik aşınma oluşturmaz; düşük hızda ve durma anında da konum bilgisini koruyarak PID kapalı döngüsü için güvenilir geri besleme sağlar. |
| Avantaj | Mutlak konum geri beslemesi sağlar; toz, titreşim ve sınırlı hizalama hatalarına optik encoderlara göre daha dayanıklıdır. PID hatası encoder okuması ile hedef arasındaki farktan hesaplanır (target - measured). Homing prosedürü ile sıfır noktası doğrulanır. |
| Dezavantaj | Manyetik encoder performansı mıknatıs-çip hizalamasına, hava aralığına ve çevredeki manyetik alan girişimlerine duyarlıdır. Konum verisi encoder olmadan elde edilemez; mekanik montaj, manyetik merkezleme ve kalibrasyon gerektirir. |
| Alınan Önlem | Encoder okuması her döngüde (100 Hz) yapılır; deadband (0.1 derece) etkin çözünürlük tabanı olarak kullanılır; homing ile referans noktası belirlenir; hata 5 dereceyi aşarsa motor hatası alarmı verilir. Mıknatıs hizalaması ve sensör hava aralığı montaj sırasında kontrol edilir. |
| Alternatif | Optik encoder, Sensorless FOC (Field Oriented Control), Hall effect sensor, Resolver. |
| Neden Alternatif Seçilmedi? | Optik encoder toz, hizalama ve mekanik montaj hassasiyetine daha duyarlıdır; sensorless FOC düşük hızda konum kestiremez; Hall sensor yeterli çözünürlük sağlamaz; resolver manyetik encodere göre daha pahalı ve ağırdır. Mevcut prototip aşaması için manyetik encoder en uygun dayanıklılık, maliyet ve performans dengesini sunmaktadır. |

**KTR (Kritik Tasarım Raporu) Metni:**
"Manyetik encoder konum sensörü, hareketli uydu terminalinin azimuth ve elevasyon eksenlerinde motor milinin veya döner eksenin anlık açısal konumunu temassız olarak ölçmek ve PID kontrolcüye geri besleme sağlamak amacıyla kullanılmaktadır. Algoritma, her 10 ms'lik kontrol döngüsünde manyetik encoder okunarak hedef açı ile ölçülen açı arasındaki farkı hata sinyali olarak PID kontrolcüye iletmekte, böylece kapalı döngü pozisyon kontrolü gerçekleştirilmektedir. Manyetik encoderın temassız ölçüm prensibi, mekanik aşınmayı azaltmakta ve düşük hızlarda mutlak konum bilgisinin korunmasını sağlamaktadır. Bu yöntemde ölçüm doğruluğunu etkileyen temel riskler mıknatıs-sensör hizalaması, hava aralığı ve çevresel manyetik girişimlerdir. Bu riski azaltmak amacıyla, etkin çözünürlük tabanı olarak 0.1 derece deadband eşiği kullanılmakta, homing prosedürü ile sıfır referansı doğrulanmakta, montaj sırasında mıknatıs hizalaması kontrol edilmekte ve encoder hatası 5 dereceyi aştığında motor hatası alarmı devreye girmektedir."
