# cad-final-projesi
# Endüstriyel Tezgah Mengenesi - Katı Modelleme ve Kinematik Analiz Projesi

Bu proje, **Bursa Uludağ Üniversitesi Robotik ve Yapay Zeka Programı** Bilgisayar Destekli Tasarım dersi final teslimi kapsamında geliştirilmiştir. Projede, endüstriyel standartlara uygun bir tezgah mengenesinin tüm parçaları milimetrik hassasiyetle modellenmiş, montaj ilişkileri kurulmuş ve kinematik sınırlandırmaları analiz edilmiştir.

---

## 🛠️ Proje Özellikleri ve Şartname Uyumlaması

Final sınavı yönergesinde belirtilen tüm akademik kriterler projede eksiksiz olarak karşılanmıştır:

* **Parça Sayısı:** Sistem, tekil bir gövdeden ibaret olmayıp **10'dan fazla özgün parçanın** (alt plaka, hareketli çene, vidalı mil, sıkıştırma kolları, pabuçlar ve standart bağlantı elemanları) bir araya getirilmesiyle oluşan kompleks bir montaj mimarisine sahiptir.
* **Malzeme ve Renklendirme:** Her bir bileşene Autodesk Inventor kütüphanesinden gerçeğe en yakın mühendislik malzemeleri (Dökme Demir, Karbon Çeliği vb.) atanmış ve endüstriyel standartlara göre renklendirilmiştir.
* **3 Farklı Hareket Sistemi:** Mekanizma, kolaya kaçan yapılar (Lego adam, basit piston vb.) yerine birbiriyle senkronize çalışan 3 bağımsız mekanik hareket içerir:
    1.  **Rotasyonel Hareket:** Sıkıştırma kolu ve vida milinin kendi ekseni etrafındaki dairesel dönüşü.
    2.  **Lineer Dönüşüm (Vida-Somun):** Helisel (`Screw`) bağ sayesinde dönme hareketinin doğrusal ilerleme kuvvetine dönüştürülmesi.
    3.  **Kılavuzlama (Kızak) Hareketi:** Hareketli çenenin şasi üzerindeki raylarda tek eksende (`Slider/Prismatic`) doğrusal kayma hareketi.

---

## 💻 Proje Yönetimi ve Sürüm Kontrolü (Git/GitHub Workflow)

Bu projenin geliştirme sürecinde, modern mühendislik iş akışlarına sadık kalınarak **Git & GitHub** aktif olarak kullanılmıştır.
* **Çift Cihaz Senkronizasyonu:** Çalışmalar masaüstü bilgisayar ve dizüstü bilgisayar arasında Git repoları üzerinden anlık olarak push/pull edilerek senkronize yürütülmüştür.
* **Şeffaf Geliştirme Geçmişi:** Projenin ilk tasarım aşamasından son revizyonlarına kadar sarf edilen tüm emek, commit geçmişindeki zaman damgalı kayıtlar ile doğrulanabilir durumdadır.

---

## ⚠️ Önemli Simülasyon Notu (Known Issues)

Montaj odasında (`Assembly`) statik ve geometrik olarak kusursuz çalışan mekanizma, `Dynamic Simulation` (Dinamik Simülasyon) ortamına aktarıldığında yazılımsal bir sınırlandırma kısıtı ile karşılaşmıştır.

* **Over-Constraint (Aşırı Sınırlandırma) Çakışması:** Vida milinin ucu ile hareketli çene yüzeyi kısıtlandığında, Inventor'ın otomatik