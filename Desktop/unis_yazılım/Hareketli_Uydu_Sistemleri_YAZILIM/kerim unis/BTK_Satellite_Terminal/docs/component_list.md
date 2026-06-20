# Gazebo Uyumlu Algoritma Component Listesi

Bu liste KTR nihai donanim kararlarina gore ayrik ROS 2/Gazebo node veya kutuphane componenti olarak kullanilabilecek cekirdek algoritmalari tanimlar.

## Core algorithm components

1. `sensor_fusion_component`
   - Girdi: BNO055 IMU roll/pitch/gyro verisi
   - Cikti: filtrelenmis roll/pitch ve gyro bias
   - Not: Bu cikti azimuth/elevasyon hedefi uretmek icin degil, stabilizasyon icin kullanilir.
   - Kod temeli: `ExtendedKalmanFilter`

2. `stabilization_controller_component`
   - Girdi: filtrelenmis roll/pitch ve gyro rate
   - Cikti: mama kabi roll/pitch joint hedefi, X/Y actuator mm hedefi, residual hata
   - Kod temeli: `StabilizationController`

3. `satellite_pointing_component`
   - Girdi: ZED-F9P GNSS/RTK LLA konumu, zaman, hedef uydu parametresi
   - Cikti: ham uydu azimuth/elevation hedefi
   - Kod temeli: `SGP4Propagator`, `CoordinateTransform`

4. `az_el_controller_component`
   - Girdi: hedef az/el, az/el encoder state
   - Cikti: DRV8825/NEMA 17 azimuth/elevation motor komutu
   - Kod temeli: `AntennaController`, `PIDController`, `SafetyMonitor`

5. `camera_object_detection_component`
   - Girdi: kamera frame veya kamera HAL bounding-box sonucu
   - Cikti: normalize hedef merkez hatasi, algilama guveni, kilit durumu
   - Kod temeli: `CameraObjectDetector`, `LaserTracker`

6. `disturbance_scenario_component`
   - Girdi: profil tipi ve simulasyon zamani
   - Cikti: Gazebo base/platform roll/pitch bozucusu
   - Kod temeli: `DisturbanceScenarioGenerator`

7. `telemetry_component`
   - Girdi: sistem durumu, konum, encoder, stabilizasyon ve takip ciktilari
   - Cikti: GUI/ROS topic/CSV icin paketlenmis telemetri
   - Kod temeli: `TelemetryPublisher`

## Gazebo tarafindaki onerilen baglanti

```text
BNO055 IMU veya Gazebo IMU
  -> sensor_fusion_component
  -> stabilization_controller_component
  -> stabilized_platform roll/pitch joints

ZED-F9P GNSS/RTK + target satellite + time
  -> satellite_pointing_component
  -> az_el_controller_component
  -> azimuth/elevation joints

Camera/image detection
  -> camera_object_detection_component
  -> fine pointing correction
  -> az_el_controller_component

disturbance_scenario_component
  -> base_link roll/pitch disturbance

telemetry_component
  -> GUI, logger, plots
```

## Baslangic testleri

1. Sadece `STABILIZE_ONLY` modunda sinus bozucu hareket ver.
2. Residual roll/pitch RMS hatasini olc.
3. Sonra `FULL_TRACKING` modunda ayni bozucuyu uydu hedefi ve kamera hedef algilama ile birlikte calistir.
4. Az/el hedef hatasi ile residual stabilizasyon hatasini ayri grafikle.
