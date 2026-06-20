// ============================================================
//  main.cpp  —  Ana Kontrol Döngüsü (RTOS / Bare-metal)
//
//  Tüm adımları birleştirir:
//    Adım 1: Başlatma (bir kez)
//    Adım 2: Veri Toplama
//    Adım 3: Sensör Füzyonu + Koordinat Hesaplama
//    Adım 4: PID Kontrol
//    Adım 5: Geri Besleme ve Telemetri
//
//  RTOS: FreeRTOS uyumlu görev yapısı
//        Bare-metal: super-loop kullanılabilir
//  Hareketli Uydu Terminali  |  v1.0
// ============================================================

#include "config.h"
#include "types.h"
#include "initialization.h"
#include "SensorFusion.h"
#include "SatelliteTracker.h"
#include "PIDController.h"
#include "StabilizationController.h"
#include "CameraObjectDetector.h"
#include "LaserTracker.h"
#include "telemetry.h"

// ─── FreeRTOS başlıkları (gerçek sistemde aktif et) ─────────
#ifdef USE_FREERTOS
  #include "FreeRTOS.h"
  #include "task.h"
  #include "semphr.h"
  #include "queue.h"
#else
  // Bare-metal için stub makrolar
  #define vTaskDelay(x)    hal_delay_ms(x)
  #define xTaskGetTickCount() hal_get_tick_ms()
#endif

// ────────────────────────────────────────────────────────────
// Global sistem durumu (RTOS ortamında mutex ile koruyun)
// ────────────────────────────────────────────────────────────

static SystemState   g_state       = SystemState::POWER_ON;
static uint16_t      g_errors      = 0;

// Sensör verileri
static IMURawData    g_imu_raw{};
static GPSData       g_gps{};
static TLEData       g_tle{};
static CameraObjectDetection g_camera_detection{};
static QPDData       g_qpd{};

// İşlenmiş veriler
static Orientation   g_orientation{};
static AntennaTarget g_antenna_target{};
static EncoderData   g_encoder{};
static AzEl          g_sat_azel{};
static LaserSpotData g_laser_spot{};
static LaserTrackingCorrection g_laser_correction{};

// Kontrol çıktısı
static AntennaController::ControlOutput g_ctrl_out{};
static StabilizationOutput g_stab_out{};

// Zamanlama
static uint32_t g_last_imu_tick  = 0;
static uint32_t g_last_gps_tick  = 0;
static uint32_t g_last_tel_tick  = 0;
static bool     g_fine_tracking_seen = false;

// İşlemciler
static ExtendedKalmanFilter g_ekf;
static SGP4Propagator       g_sgp4;
static AntennaController    g_ctrl;
static StabilizationController g_stab;
static CameraObjectDetector g_camera_detector;
static LaserTracker         g_laser_tracker;
static TelemetryPublisher   g_telemetry;
static CommandReceiver      g_cmd_recv;

// Kalibrasyon sonuçları
static IMUCalibration::CalibResult g_imu_calib{};

// ────────────────────────────────────────────────────────────
// HAL stub implementasyonu (platforma özgü)
// ────────────────────────────────────────────────────────────
extern "C" {
    // Bu fonksiyonlar platform HAL katmanında implemente edilir.
    // Burada imzaları referans olarak listelenmiştir.
    bool     hal_imu_init(uint8_t)                              { return true; }
    bool     hal_gps_init(uint8_t, uint32_t)                    { return true; }
    bool     hal_motor_init(MotorAxis)                           { return true; }
    bool     hal_encoder_init(MotorAxis)                         { return true; }
    bool     hal_limit_switch_read(MotorAxis, bool& mn, bool& mx){ mn=false;mx=false; return true; }
    void     hal_motor_set_pwm(MotorAxis, MotorDir, float)       {}
    IMURawData hal_imu_read()                                    { return {}; }
    void     hal_delay_ms(uint32_t)                              {}
    uint32_t hal_get_tick_ms()                                   { return 0; }
    void     hal_watchdog_kick()                                 {}
    void     hal_log(const char* s)                              { (void)s; }
    void     hal_uart_send(uint8_t, const uint8_t*, uint16_t)    {}
    uint16_t hal_uart_recv(uint8_t, uint8_t*, uint16_t)          { return 0; }
    int8_t   hal_get_rssi_dbm()                                  { return -80; }
    CameraObjectDetection hal_camera_read_detection()             { return {}; }
    QPDData  hal_qpd_read(uint8_t)                                { return {}; }

    // Encoder okunması (platform HAL'ından)
    EncoderData hal_encoder_read()                               { return {}; }
    // GPS NMEA parse (platform HAL'ından)
    GPSData hal_gps_read()                                       { return {}; }
}

// ════════════════════════════════════════════════════════════
//  ═══════════════════════════════════════════════════════════
//  ADIM 1 — BAŞLATMA (Ana görev öncesi, bir kez)
//  ═══════════════════════════════════════════════════════════
// ════════════════════════════════════════════════════════════

static bool system_init_phase() {
    g_state = SystemState::HW_SELF_TEST;

    InitResult init = system_initialize();
    if (!init.ready) {
        g_state  = SystemState::ERROR;
        g_errors = init.hw_test.error_flags;
        return false;
    }

    // Kalibrasyon sonuçlarını kaydet
    g_imu_calib = init.imu_calib;

    // EKF'yi kalibrasyon bias'ıyla başlat
    g_ekf.init(g_imu_calib.bias_gyro);

    // Varsayılan TLE yükle (NOAA-19 örnek)
    TLEParser::parse(
        "NOAA 19",
        "1 33591U 09005A   24001.50000000  .00000076  00000-0  65132-4 0  9990",
        "2 33591  99.1000 127.0000 0013500 320.0000  40.0000 14.12345678345678",
        g_tle);
    if (g_tle.valid) g_sgp4.init(g_tle);

    g_state = SystemState::IDLE;
    hal_log("[SISTEM] Hazir. AUTO modda baslatiliyor...");
    g_state = SystemState::AUTO_TRACKING;
    return true;
}

// ════════════════════════════════════════════════════════════
//  ═══════════════════════════════════════════════════════════
//  ADIM 2 — VERİ TOPLAMA
//  ═══════════════════════════════════════════════════════════
// ════════════════════════════════════════════════════════════

static void task_data_acquisition(uint32_t now_ms) {

    // ── IMU: Her 10ms (100Hz) ─────────────────────────────
    if (now_ms - g_last_imu_tick >= MAIN_LOOP_PERIOD_MS) {
        g_last_imu_tick = now_ms;
        g_imu_raw = hal_imu_read();

        // Kalibrasyon bias'ını çıkar
        if (g_imu_calib.success) {
            g_imu_raw.accel_ms2.x -= g_imu_calib.bias_accel.x;
            g_imu_raw.accel_ms2.y -= g_imu_calib.bias_accel.y;
            g_imu_raw.accel_ms2.z -= g_imu_calib.bias_accel.z;
            // Not: Gyro bias EKF tarafından tahmin edilir
        }
    }

    // ── ZED-F9P GNSS/RTK: Her 1000ms (1Hz) ───────────────
    if (now_ms - g_last_gps_tick >= GPS_UPDATE_PERIOD_MS) {
        g_last_gps_tick = now_ms;
        GPSData new_gps = hal_gps_read();
        if (new_gps.fix_valid && new_gps.hdop < GNSS_MAX_HDOP) {
            if (new_gps.timestamp_ms == 0) new_gps.timestamp_ms = now_ms;
            g_gps = new_gps;
            if (g_errors & static_cast<uint16_t>(ErrorCode::GPS_NO_FIX))
                g_errors &= ~static_cast<uint16_t>(ErrorCode::GPS_NO_FIX);
            if (g_errors & static_cast<uint16_t>(ErrorCode::GNSS_STALE))
                g_errors &= ~static_cast<uint16_t>(ErrorCode::GNSS_STALE);
        } else if (!new_gps.fix_valid) {
            g_errors |= static_cast<uint16_t>(ErrorCode::GPS_NO_FIX);
        }
    }

    if (g_gps.timestamp_ms != 0 &&
        now_ms - g_gps.timestamp_ms > GNSS_STALE_TIMEOUT_MS) {
        g_errors |= static_cast<uint16_t>(ErrorCode::GNSS_STALE);
    }

    // ── Encoder: Her döngüde ─────────────────────────────
    g_encoder = hal_encoder_read();

    // ── İnce takip sensörleri: QPD öncelikli, kamera yedek ──
    g_qpd = hal_qpd_read(QPD_ADC_CHANNEL);
    g_camera_detection = hal_camera_read_detection();

    // ── Komut kuyruğu: Her döngüde ───────────────────────
    g_cmd_recv.poll();
}

// ════════════════════════════════════════════════════════════
//  ═══════════════════════════════════════════════════════════
//  ADIM 3 — SENSÖR FÜZYONU ve KOORDİNAT HESAPLAMA
//  ═══════════════════════════════════════════════════════════
// ════════════════════════════════════════════════════════════

static void task_sensor_fusion_and_coords(float dt, uint32_t now_ms) {

    // ── 3A: EKF ile IMU Füzyonu ───────────────────────────
    // Predict: Gyro ile durumu ilerlet
    g_ekf.predict(g_imu_raw.gyro_rads, dt);
    // Update: İvmeölçer ile düzelt
    g_ekf.update(g_imu_raw.accel_ms2);
    // Yönelimi al
    g_orientation = g_ekf.getOrientation();

    // ── 3A.1: Mama kabı roll/pitch stabilizasyonu ─────────
    // KTR nihai mimarisinde IMU/BNO055, az/el hedefi üretmek için değil,
    // alt stabilizasyon mekanizmasının bozucu roll/pitch hareketini bastırmak için kullanılır.
    StabilizationInput stab_input =
        StabilizationController::fromSensors(g_orientation, g_imu_raw, dt, true);
    g_stab_out = g_stab.update(stab_input);

    // ── 3B: SGP4 ile Uydu Konumu ──────────────────────────
    if (g_tle.valid && g_gps.fix_valid) {
        // Şu anki UTC'yi JD'ye çevir (platform saatinden al)
        // Basitlik için sabit JD örneği — gerçekte RTC'den al
        static double jd_base = SGP4Propagator::utcToJD(2024,1,1,0,0,0.0);
        double jd = jd_base + (now_ms / 1000.0) / 86400.0;

        Vec3d r_eci, v_eci;
        if (g_sgp4.propagate(jd, r_eci, v_eci)) {
            // ECI → ECEF
            Vec3d r_ecef = CoordinateTransform::eciToECEF(r_eci, jd);

            // ECEF → Az/El (gözlemci → uydu)
            g_sat_azel = CoordinateTransform::calcAzEl(g_gps.position, r_ecef);
        }
    }

    // ── 3C: KTR az/el hedefi ──────────────────────────────
    // BNO055 roll/pitch verisi anten hedefini doğrudan üretmez; mama kabı
    // stabilizasyonunda kullanılır. Az/el hedefi GNSS + uydu modeli tabanlıdır.
    AntennaTarget base_target{};
    base_target.az_setpoint_deg = g_sat_azel.az_deg;
    base_target.el_setpoint_deg = g_sat_azel.el_deg;
    base_target.satellite_azel  = g_sat_azel;
    base_target.satellite_above_horizon = (g_sat_azel.el_deg > 0.0f);

    // ── 3D: QPD/kamera ince takip düzeltmesi ───────────────
    if (g_qpd.valid && g_qpd.confidence >= QPD_LOCK_THRESHOLD) {
        g_laser_spot = LaserTracker::spotFromQpd(g_qpd);
    } else {
        g_laser_spot = g_camera_detector.update(g_camera_detection, now_ms);
    }

    if (g_laser_spot.detected) {
        g_fine_tracking_seen = true;
        g_errors &= ~static_cast<uint16_t>(ErrorCode::OPTICAL_TRACK_LOST);
    } else if (g_fine_tracking_seen && base_target.satellite_above_horizon) {
        g_errors |= static_cast<uint16_t>(ErrorCode::OPTICAL_TRACK_LOST);
    }

    g_antenna_target = g_laser_tracker.applyCorrection(
        base_target,
        g_laser_spot,
        dt,
        g_laser_correction);
}

// ════════════════════════════════════════════════════════════
//  ═══════════════════════════════════════════════════════════
//  ADIM 4 — KARAR MEKANİZMASI VE KONTROL
//  ═══════════════════════════════════════════════════════════
// ════════════════════════════════════════════════════════════

static void task_control(float dt) {

    // ── Komut İşle ────────────────────────────────────────
    CommandPacket cmd{};
    while (g_cmd_recv.dequeue(cmd)) {
        switch (cmd.cmd) {
            case UserCommand::SET_AUTO_MODE:
                g_state = SystemState::AUTO_TRACKING;
                g_ctrl.reset();
                hal_log("[CMD] Otomatik takip modu.");
                break;

            case UserCommand::SET_MANUAL:
                g_state = SystemState::MANUAL;
                g_ctrl.reset();
                hal_log("[CMD] Manuel mod.");
                break;

            case UserCommand::MANUAL_AZ:
                if (g_state == SystemState::MANUAL) {
                    g_antenna_target.az_setpoint_deg = cmd.payload.angle_deg;
                }
                break;

            case UserCommand::MANUAL_EL:
                if (g_state == SystemState::MANUAL) {
                    g_antenna_target.el_setpoint_deg = cmd.payload.angle_deg;
                }
                break;

            case UserCommand::LOAD_TLE:
                g_tle = cmd.payload.tle;
                if (g_tle.valid) {
                    g_sgp4.init(g_tle);
                    hal_log("[CMD] Yeni TLE yuklendi.");
                }
                break;

            case UserCommand::HOME:
                g_state = SystemState::HOMING;
                {
                    HomingProcedure h;
                    h.performHoming();
                }
                g_state = SystemState::IDLE;
                break;

            case UserCommand::EMERGENCY_STOP:
                g_state = SystemState::ERROR;
                g_errors |= static_cast<uint16_t>(ErrorCode::WATCHDOG);
                hal_log("[ACIL] Acil durdurma komutu alindi!");
                break;

            default: break;
        }
    }

    // ── Limit Switch Oku ──────────────────────────────────
    bool az_sw_min=false, az_sw_max=false;
    bool el_sw_min=false, el_sw_max=false;
    hal_limit_switch_read(MotorAxis::AZIMUTH,   az_sw_min, az_sw_max);
    hal_limit_switch_read(MotorAxis::ELEVATION, el_sw_min, el_sw_max);

    // ── PID + Güvenlik ────────────────────────────────────
    if (g_state == SystemState::AUTO_TRACKING ||
        g_state == SystemState::MANUAL)
    {
        g_ctrl_out = g_ctrl.update(
            g_antenna_target, g_encoder, dt,
            az_sw_min, az_sw_max,
            el_sw_min, el_sw_max);

        // Hata bayrağı güncellemesi
        g_errors |= g_ctrl_out.safety_flags;

        // Motor komutlarını uygula
        MotorDir az_dir = g_ctrl_out.az_cmd.direction;
        MotorDir el_dir = g_ctrl_out.el_cmd.direction;

        hal_motor_set_pwm(MotorAxis::AZIMUTH,
                          az_dir, g_ctrl_out.az_cmd.duty_pct);
        hal_motor_set_pwm(MotorAxis::ELEVATION,
                          el_dir, g_ctrl_out.el_cmd.duty_pct);
    }

    // ── Mama kabı stabilizasyon motorları ─────────────────
    // Stabilizasyon, az/el takip modundan bağımsız olarak gövdeyi sakinleştirir.
    if (g_state != SystemState::ERROR) {
        hal_motor_set_pwm(g_stab_out.roll_motor_cmd.axis,
                          g_stab_out.roll_motor_cmd.direction,
                          g_stab_out.roll_motor_cmd.duty_pct);
        hal_motor_set_pwm(g_stab_out.pitch_motor_cmd.axis,
                          g_stab_out.pitch_motor_cmd.direction,
                          g_stab_out.pitch_motor_cmd.duty_pct);
    }
    else if (g_state == SystemState::ERROR) {
        // Hata durumunda tüm motorları durdur
        hal_motor_set_pwm(MotorAxis::AZIMUTH,   MotorDir::STOP, 0.0f);
        hal_motor_set_pwm(MotorAxis::ELEVATION, MotorDir::STOP, 0.0f);
        hal_motor_set_pwm(MotorAxis::STABILIZER_ROLL, MotorDir::STOP, 0.0f);
        hal_motor_set_pwm(MotorAxis::STABILIZER_PITCH, MotorDir::STOP, 0.0f);
    }
}

// ════════════════════════════════════════════════════════════
//  ═══════════════════════════════════════════════════════════
//  ADIM 5 — GERİ BESLEME ve TELEMETRİ
//  ═══════════════════════════════════════════════════════════
// ════════════════════════════════════════════════════════════

static void task_telemetry(uint32_t now_ms) {
    if (now_ms - g_last_tel_tick < TELEMETRY_PERIOD_MS) return;
    g_last_tel_tick = now_ms;

    g_telemetry.buildAndSend(
        now_ms,
        g_state,
        g_errors,
        g_gps,
        g_orientation,
        g_encoder,
        g_antenna_target,
        g_sat_azel,
        g_stab_out,
        g_laser_correction,
        g_ctrl_out.az_error_deg,
        g_ctrl_out.el_error_deg);

    // ── Motor Geri Bildirimi Kontrolü ─────────────────────
    // Encoder hedeften çok sapmışsa alarm
    if (g_state == SystemState::AUTO_TRACKING) {
        bool az_fault = fabsf(g_ctrl_out.az_error_deg) > MAX_TRACKING_ERROR_DEG;
        bool el_fault = fabsf(g_ctrl_out.el_error_deg) > MAX_TRACKING_ERROR_DEG;
        if (az_fault) {
            g_errors |= static_cast<uint16_t>(ErrorCode::AZ_MOTOR_FAIL);
            hal_log("[UYARI] Azimut takip hatası cok büyük!");
        }
        if (el_fault) {
            g_errors |= static_cast<uint16_t>(ErrorCode::EL_MOTOR_FAIL);
            hal_log("[UYARI] Elevasyon takip hatası çok büyük!");
        }
    }
}

// ════════════════════════════════════════════════════════════
//  ANA FONKSİYON / FREERTOS GÖREV GİRİŞ NOKTASI
// ════════════════════════════════════════════════════════════

// ─────────────────────────────────────────────────────────
//  FreeRTOS görev — Bu fonksiyon xTaskCreate() ile başlatılır
//  Görev parametreleri:
//    Stack: ~4096 word
//    Öncelik: Yüksek (configMAX_PRIORITIES - 1)
//    Periyot: MAIN_LOOP_PERIOD_MS (10ms)
// ─────────────────────────────────────────────────────────
#ifdef USE_FREERTOS
void vSatelliteTrackerTask(void* pvParameters) {
    (void)pvParameters;
#else
void satellite_tracker_main_loop() {
#endif

    // ══ ADIM 1: Başlatma (bir kez) ══════════════════════════
    if (!system_init_phase()) {
        hal_log("[FATAL] Sistem baslatilamadi. Dongu durduruldu.");
#ifdef USE_FREERTOS
        vTaskDelete(nullptr);
#endif
        return;
    }

    uint32_t prev_tick = hal_get_tick_ms();

    // ══ Ana Döngü (2'den 5'e — her ~10ms) ══════════════════
    while (true) {
        hal_watchdog_kick();

        uint32_t now = hal_get_tick_ms();

        // dt hesaplama (saniye cinsinden)
        float dt = static_cast<float>(now - prev_tick) * 0.001f;
        if (dt <= 0.0f) dt = MAIN_LOOP_PERIOD_MS * 0.001f;  // Güvenlik
        if (dt > 0.1f)  dt = 0.1f;                           // Max 100ms clamp
        prev_tick = now;

        // ── ADIM 2: Veri Toplama ──────────────────────────
        task_data_acquisition(now);

        // ── ADIM 3: Sensör Füzyonu & Koordinatlar ─────────
        task_sensor_fusion_and_coords(dt, now);

        // ── ADIM 4: PID Kontrol ───────────────────────────
        task_control(dt);

        // ── ADIM 5: Telemetri ─────────────────────────────
        task_telemetry(now);

        // ── Döngü zamanlama: Kalan süreyi bekle ───────────
#ifdef USE_FREERTOS
        vTaskDelay(pdMS_TO_TICKS(MAIN_LOOP_PERIOD_MS));
#else
        uint32_t elapsed = hal_get_tick_ms() - now;
        if (elapsed < MAIN_LOOP_PERIOD_MS) {
            hal_delay_ms(MAIN_LOOP_PERIOD_MS - elapsed);
        }
#endif
    }
}

// ─────────────────────────────────────────────────────────
//  main() — Donanım başlatma ve FreeRTOS scheduler başlatma
// ─────────────────────────────────────────────────────────
int main() {
#ifdef USE_FREERTOS
    // FreeRTOS görevi oluştur
    xTaskCreate(
        vSatelliteTrackerTask,
        "SAT_TRACKER",
        4096,                          // Stack (word)
        nullptr,
        configMAX_PRIORITIES - 1,      // Yüksek öncelik
        nullptr);

    vTaskStartScheduler();
    // Buraya asla ulaşılmamalı
    for (;;) {}
#else
    // Bare-metal: Doğrudan döngüye gir
    satellite_tracker_main_loop();
    return 0;
#endif
}
