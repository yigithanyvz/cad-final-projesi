# Kullanilan Python Kutuphaneleri ve Algoritma Akis Semasi

## Kullanilan Python Kutuphaneleri

### Proje Bagimliliklari (requirements.txt)

| Kutuphane | Surum | Kullanim Amaci |
|-----------|-------|----------------|
| pyserial | >=3.5 | Seri port (USB/UART) uzerinden Teensy ile haberlesme |
| matplotlib | >=3.5.0 | Lazer hata grafigi (scatter plot) ve gorsellestirme |
| Pillow | >=9.0.0 | Gorsel isleme ve arayuz ikonlari icin |
| rclpy | (ROS2) | ROS2 Python istemci kutuphanesi - Gazebo abonelikleri |
| mergen_interfaces | (ROS2) | Mergen uydu simulasyonu ozel mesaj tanimlari |

### Standart Kutuphaneler (harici kurulum gerektirmez)
| Modul | Kullanim Amaci |
|-------|----------------|
| tkinter | Grafik arayuz (GUI) - pencere, dugme, etiket, liste, text alani |
| tkinter.ttk | Temali arayuz bilesenleri (stil, combobox, progressbar) |
| tkinter.messagebox | Hata/bilgi/uyari mesaj kutulari |
| threading | Arka planda ROS subscriber, seri port/wifi dinleyici thread'i |
| socket | ESP32 ile TCP/IP uzerinden WiFi haberlesmesi |
| queue | Thread'ler arasi veri iletimi icin guvenli kuyruk |
| json | JSON formatinda mesaj serilestirme/deserilestirme |
| logging | Hata ve bilgi loglama |
| dataclasses | SystemState ve TelemetryData gibi veri yapilari |
| enum | Sistem durumu ve komut tipleri icin sabitler |
| typing | Tip bildirimleri (Optional, Callable) |
| time | Zaman bilgisi, uptime hesaplama |
| math | GPS'den aci hesaplama (trigonometrik fonksiyonlar) |
| sys | Platform bilgisi (yazi tipi secimi) |

---

## Algoritma Akis Semasi

### 1. Uygulama Baslangici

```
main() fonksiyonu
  |
  +-- logging.basicConfig() --> logger baslat
  |
  +-- MergenApp() --> UYGULAMA NESNESI
        |
        +-- __init__()
              |
              +-- IOHandler()      --> Seri/Wifi haberlesme yoneticisi (yedek)
              +-- MergenRosClient() --> ROS2/Gazebo bridge (birincil)
              +-- SystemState()    --> Sistem durumu (baslangic: KAPALI)
              +-- _setup_style()   --> Tema renkleri ve stiller
              +-- _build_ui()
              |     |
              |     +-- _build_top_bar()          --> Baglanti durumu, calisma suresi
              |     +-- _build_main_grid()         --> 3 sutunlu panel duzeni
              |     |     +-- connection_panel     --> COM port, WiFi, ROS/Gazebo dugmesi
              |     |     +-- control_panel        --> Baslat/Durdur/Home/Acil, Mod secimi
              |     |     +-- target_panel         --> Uydu secimi, GPS, Az/El, Hedef gonder
              |     |     +-- telemetry_panel      --> Anlik Az/El/Roll/Pitch/Lock/RSSI
              |     |     +-- laser_graph_panel    --> Lazer sapma grafigi (matplotlib)
              |     |     +-- log_panel            --> Sistem mesaj logu
              |     +-- register_callback(...)     --> Telemetri alindiginda calisacak fonks.
              |     +-- after(100, _poll_state)   --> 100ms'de bir durum yoklamasi baslat
              |
              +-- mainloop() --> OLAY DONGUSU (GUI bekler)
```

### 2. Baglanti Kurulumu

```
Kullanici "ROS/Gazebo Baglan" dugmesine basar
  |
  +-- _toggle_ros()
        |
        +-- MergenRosClient.enable()
              |
              +-- rclpy.init() --> ROS2 baslat
              +-- Node olustur: "mergen_gui_client"
              +-- Abonelikler:
              |     /mergen/sim/telemetry_json  (std_msgs/String)
              |     /mergen/telemetry_json      (std_msgs/String)
              |     /mergen/motor_state          (MotorState)
              |     /mergen/imu_filtered         (ImuFiltered)
              +-- Yayinlar:
              |     /mergen/gui/command_json     (std_msgs/String)
              |     /mergen/gui/mode_json         (std_msgs/String)
              |     /mergen/gui/target_json       (std_msgs/String)
              |     /mergen/target_angles         (TargetAngles)
              +-- Spin dongusu (thread): rclpy.spin_once()
              +-- Geri arama: _on_ros_telemetry(RosTelemetry)

Alternatif: Seri/Wifi baglantisi (yedek)
  |
  +-- _toggle_serial() veya _toggle_wifi()
        |
        +-- io_handler.connect_serial(port, baud)
        |     +-- serial.Serial(port, baud)
        |     +-- _start_reader("serial") --> _reader_loop()
        |
        +-- io_handler.connect_wifi(host, port)
              +-- socket.connect((host, port))
              +-- _start_reader("wifi")
```

### 3. Ana Durum Yoklama Dongusu (_poll_state)

```
_poll_state() --> her 100ms'de bir calisir
  |
  +-- ROS modu aktif mi? (Gazebo'den veri geliyor)
  |     |
  |     EVET --> MergenRosClient.last_telemetry'den oku
  |               _on_ros_telemetry(RosTelemetry) cagir
  |                 |
  |                 +-- Az/El/Roll/Pitch/Yaw/Lock/RSSI state'e yansit
  |                 +-- Mod donusumu: String -> SystemMode enum
  |                 +-- Son telemetri zamanini guncelle
  |               |
  |               3sn boyunca telemetri gelmezse:
  |                 state.connection_ok = False
  |
  |     HAYIR --> SIMULASYON modu mu?
  |           |
  |           EVET --> _simulate_update()
  |           |         +-- Zamanlayici ile yapay Az/El/Roll/Pitch degerleri
  |           |         +-- Lazer hatasi icin yapay sapma
  |           |
  |           HAYIR --> io_handler'dan gercek telemetri oku
  |
  +-- _update_ui()
        +-- Telemetri panelini guncelle (Az, El, Roll, Pitch, Lock, RSSI)
        +-- Lazer grafigini guncelle (matplotlib scatter plot)
        +-- Sure gostergesini guncelle
        +-- after(100, _poll_state) --> bir sonraki yoklamayi planla
```

### 4. Kullanici Komutlari

```
Kullanici "BASLAT" dugmesine basar
  |
  +-- _cmd_start()
        |
        +-- _send(CommandMessage(action="start"))
              |
              +-- ROS modu aktifse:
              |     MergenRosClient.publish_command("start")
              |       +-- /mergen/gui/command_json topic'ine JSON yayinla
              |
              +-- Seri/Wifi bagliysa:
              |     io_handler.send_command(cmd)
              |       +-- Serial: port.write()
              |       +-- WiFi:   sock.send()
              |
              +-- SIMULASYON modu aktifse (yalnizca yapay guncelleme)
```

```
Kullanici uydu secer ve hesaplatir
  |
  +-- _calculate_target()
  |     +-- calculate_look_angles(enlem, boylam, uydu_boylami)
  |     |     +-- Trigonometrik hesapla: azimut ve elevasyon
  |     |     +-- Geri don: (az_deg, el_deg)
  |     +-- Arayuzde hedef Az/El degerlerini goster
  |
  +-- _send_target()
        +-- _send(CommandMessage(action="set_target", az=..., el=...))
        +-- ROS modu aktifse:
              MergenRosClient.publish_target(az, el)
                +-- /mergen/gui/target_json topic'ine JSON yayinla
                +-- /mergen/target_angles topic'ine TargetAngles mesaji yayinla
```

```
Acil Durum Butonu
  |
  +-- _cmd_emergency()
        +-- _send(CommandMessage(action="emergency_stop"))
        +-- State'i EMERGENCY_STOP moduna al
        +-- Log mesaji
```

### 5. Telemetri Isleme

```
_on_telemetry(tel: TelemetryData)          -- Seri/Wifi'den gelen
veya
_on_ros_telemetry(tel: RosTelemetry)      -- Gazebo/ROS2'den gelen
  |
  +-- state degiskenlerini guncelle (Az/El/Roll/Pitch/Yaw/Lock/RSSI/Mod)
  |
  +-- Lazer hatasi gecerli mi?
  |     EVET --> _laser_history_x/y'ye yeni noktayi ekle, grafigi guncelle
  |
  +-- Kilit durumu degisti mi?
  |     EVET --> Log mesaji yaz
  |
  +-- last_tel_time = time.time()
```

### 6. Hata Yonetimi

```
_poll_state() icinde:
  |
  +-- ROS modu aktif ve 3sn telemetri yoksa:
  |     state.connection_ok = False
  |     Kirmizi baglanti gostergesi
  |
  +-- ROS modu kapali ve seri bagli degil:
        state.connection_ok = False
```

---

## Modul Yapisi

```
arayuz/
  __init__.py               -- Paket tanimi
  main.py                   -- Ana GUI uygulamasi (tkinter + ROS bridge)
  requirements.txt          -- Bagimlilik listesi
  ui_state.json             -- UI durumu (kalici depolama)

  comm/
    __init__.py
    io_handler.py           -- Seri/Wifi haberlesme (yedek veri kaynagi)
    protocol.py             -- JSON-line protokol tanimlari
    PROTOCOL_REFERENCE.md   -- Protokol referans dokumani

  core/
    __init__.py
    system_state.py         -- Sistem durumu veri yapisi (dataclass + SystemMode enum)
    satellite_pointing.py   -- GPS -> Az/El hesaplama

  ros_bridge/
    __init__.py
    client.py               -- ROS2 subscriber/publisher (birincil veri kaynagi)

  widgets/
    __init__.py
```

## Veri Akisi (Gerzek Hayat - Gazebo Tabanli)

```
[Gazebo Uydu Simulasyonu]
     |
     +-- /mergen/motor_state        (MotorState msg)       --> Az/El
     +-- /mergen/imu_filtered       (ImuFiltered msg)      --> Roll/Pitch/Yaw
     +-- /mergen/sim/telemetry_json (std_msgs/String)      --> JSON telemetri
     |
     v
[MergenRosClient (ros_bridge/client.py)]
     |
     +-- rclpy.Subscriber callback
     |     |
     |     +--> RosTelemetry (dataclass)
     |     +--> _on_ros_telemetry() cagir
     |
     v
[main.py]
     |
     +-- SystemState guncelle
     |     |
     |     v
     +-- [GUI Panelleri]
     |
     | (Kullanici komutlari)
     +-- MergenRosClient.publish_*(...)
           |
           +-- /mergen/gui/command_json
           +-- /mergen/gui/mode_json
           +-- /mergen/gui/target_json
           +-- /mergen/target_angles
           |
           v
     [Gazebo Uydu Simulasyonu / ROS2 node'lari]

Alternatif Veri Akisi (yedek):
  [Teensy (donanim)] --Serial--> [IOHandler] --TelemetryData--> [main.py]
  [ESP32 (donanim)]  --WiFi-->  [IOHandler] --TelemetryData--> [main.py]
```

## ROS2 Mesaj Yapisi

| Topic | Mesaj Tipi | Icerik |
|-------|-----------|--------|
| `/mergen/motor_state` | MergenInterfaces/MotorState | azimuth_deg, elevation_deg, az_setpoint, el_setpoint, motor_temp |
| `/mergen/imu_filtered` | MergenInterfaces/ImuFiltered | roll_deg, pitch_deg, yaw_deg |
| `/mergen/sim/telemetry_json` | std_msgs/String | JSON: az_act, el_act, az_tgt, el_tgt, roll, pitch, yaw, locked, mode, errors, rssi, sat_az, sat_el |
| `/mergen/telemetry_json` | std_msgs/String | Ayni JSON yapisi (canli donanim) |
| `/mergen/gui/command_json` | std_msgs/String | JSON: type="cmd", action, az, el, source="mergen_gui" |
| `/mergen/gui/mode_json` | std_msgs/String | JSON: type="mode", mode, source="mergen_gui" |
| `/mergen/gui/target_json` | std_msgs/String | JSON: type="target", az, el, source="mergen_gui" |
| `/mergen/target_angles` | MergenInterfaces/TargetAngles | azimuth_deg, elevation_deg, source, stamp_sec |
