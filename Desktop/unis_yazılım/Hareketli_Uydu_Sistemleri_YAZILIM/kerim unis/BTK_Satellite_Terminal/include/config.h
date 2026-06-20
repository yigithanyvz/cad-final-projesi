#pragma once
// ============================================================
//  config.h  —  Sistem Geneli Sabitler ve Donanım Pinleri
//  Hareketli Uydu Terminali  |  v1.0
// ============================================================

#include <cstdint>

// ─────────────── DÖNGÜ ZAMANLAMA ───────────────
constexpr uint32_t MAIN_LOOP_PERIOD_MS    = 10;   // 100 Hz ana döngü
constexpr uint32_t TELEMETRY_PERIOD_MS    = 100;  // 10 Hz telemetri
constexpr uint32_t GPS_UPDATE_PERIOD_MS   = 1000; // 1 Hz GPS güncelleme
constexpr uint32_t TLE_UPDATE_PERIOD_S    = 3600; // 1 saatte bir TLE güncelle

// ─────────────── NIHAAI KTR DONANIM KARARLARI ──
constexpr uint8_t  BNO055_I2C_ADDR        = 0x28;  // Mama kabı stabilizasyon IMU
constexpr uint8_t  ZED_F9P_UART_CHANNEL   = 1;     // GNSS/RTK konum kaynağı
constexpr uint32_t ZED_F9P_BAUD_RATE      = 38400; // u-blox UART için yaygın hız
constexpr uint8_t  TELEMETRY_UART_CHANNEL = 2;     // SIM7600G-H veya E22 telemetri hattı
constexpr uint8_t  QPD_ADC_CHANNEL        = 0;     // QPD/lazer ince takip girişi

// ─────────────── IMU AYARLARI ──────────────────
constexpr float    IMU_SAMPLE_RATE_HZ     = 100.0f;
constexpr float    GYRO_NOISE_SIGMA       = 0.005f;   // rad/s / sqrt(Hz)
constexpr float    ACCEL_NOISE_SIGMA      = 0.01f;    // m/s² / sqrt(Hz)
constexpr float    GYRO_BIAS_SIGMA        = 1e-5f;    // rad/s² (random walk)
constexpr float    GRAVITY_MS2            = 9.80665f;
constexpr uint32_t CALIBRATION_SAMPLES   = 500;       // ~5 saniye @100Hz

// ─────────────── ZED-F9P GNSS/RTK AYARLARI ─────
constexpr uint8_t  GPS_UART_CHANNEL       = ZED_F9P_UART_CHANNEL; // Eski adla uyumluluk
constexpr uint32_t GPS_BAUD_RATE          = ZED_F9P_BAUD_RATE;
constexpr float    GPS_MIN_ACCURACY_M     = 5.0f;    // HDOP/konum kalitesi kabul eşiği
constexpr float    GNSS_MAX_HDOP          = 5.0f;
constexpr uint32_t GNSS_STALE_TIMEOUT_MS  = 3000;

// ─────────────── MOTOR / EKSENLERİ ─────────────
// Azimut ekseni (0-360°)
constexpr float    AZ_LIMIT_MIN_DEG       = 0.0f;
constexpr float    AZ_LIMIT_MAX_DEG       = 360.0f;
constexpr float    AZ_WRAP_THRESHOLD_DEG  = 350.0f;  // Kablo koruma
constexpr float    AZ_MAX_SPEED_DPS       = 60.0f;   // deg/s

// Elevasyon ekseni (0-90°)
constexpr float    EL_LIMIT_MIN_DEG       = 0.0f;
constexpr float    EL_LIMIT_MAX_DEG       = 90.0f;
constexpr float    EL_MAX_SPEED_DPS       = 30.0f;

// ─────────────── MAMA KABI STABILIZASYON ───────
constexpr float    STAB_ROLL_KP           = 1.8f;
constexpr float    STAB_ROLL_KI           = 0.04f;
constexpr float    STAB_ROLL_KD           = 0.22f;
constexpr float    STAB_PITCH_KP          = 1.8f;
constexpr float    STAB_PITCH_KI          = 0.04f;
constexpr float    STAB_PITCH_KD          = 0.22f;
constexpr float    STAB_MAX_INTEGRAL      = 10.0f;
constexpr float    STAB_DEADBAND_DEG      = 0.05f;
constexpr float    STAB_ATTITUDE_ALPHA    = 0.35f;  // Roll/pitch düşük geçiren filtre
constexpr float    STAB_RATE_FF_GAIN      = 0.06f;  // Gyro dps -> derece karşı komut
constexpr float    STAB_MAX_CMD_DEG       = 12.0f;  // Mekanik platform düzeltme sınırı
constexpr float    STAB_MM_PER_DEG        = 2.5f;   // X/Y lineer tahrik eşdeğeri
constexpr float    STAB_MAX_ACTUATOR_MM   = 25.0f;
constexpr float    STAB_STABLE_ERROR_DEG  = 0.35f;

// ─────────────── PID PARAMETRELERI ─────────────
// Azimut PID
constexpr float    AZ_KP                  = 2.5f;
constexpr float    AZ_KI                  = 0.1f;
constexpr float    AZ_KD                  = 0.3f;
constexpr float    AZ_MAX_INTEGRAL        = 20.0f;

// Elevasyon PID
constexpr float    EL_KP                  = 3.0f;
constexpr float    EL_KI                  = 0.08f;
constexpr float    EL_KD                  = 0.25f;
constexpr float    EL_MAX_INTEGRAL        = 15.0f;

// Ortak PID
constexpr float    PID_DEADBAND_DEG       = 0.1f;   // ±0.1° içinde motor durdurulur
constexpr float    DERIV_FILTER_ALPHA     = 0.7f;   // Türev düşük geçiren filtre

// ─────────────── SGP4 / YÖRÜNGE ────────────────
constexpr double   EARTH_RADIUS_KM        = 6378.137;
constexpr double   EARTH_FLATTENING       = 1.0 / 298.257223563;
constexpr double   GM_KM3_S2              = 398600.4418;   // μ
constexpr double   J2_COEFF               = 1.08262998905e-3;
constexpr double   OMEGA_EARTH_RAD_S      = 7.2921150e-5;  // Dünya dönme hızı

// ─────────────── HABERLEŞME ─────────────────────
constexpr uint8_t  UART_TELEMETRY_CH      = TELEMETRY_UART_CHANNEL;
constexpr uint32_t UART_TELEMETRY_BAUD    = 115200;
constexpr uint16_t TELEMETRY_PACKET_MAGIC = 0xABCD;

// ─────────────── QPD / LAZER INCE TAKIP ────────
constexpr float    CAMERA_FRAME_WIDTH_PX   = 1280.0f;
constexpr float    CAMERA_FRAME_HEIGHT_PX  = 720.0f;
constexpr float    CAMERA_AZ_FOV_DEG       = 40.0f;
constexpr float    CAMERA_EL_FOV_DEG       = 30.0f;
constexpr float    CAMERA_MIN_CONFIDENCE   = 0.45f;
constexpr float    CAMERA_MIN_BOX_AREA_RATIO = 0.0004f;
constexpr float    CAMERA_CENTER_DEADBAND_PX = 3.0f;
constexpr float    CAMERA_DETECTION_SMOOTHING_ALPHA = 0.55f;
constexpr uint32_t CAMERA_MAX_LOST_MS      = 150;
constexpr float    LASER_KP                = 0.10f;
constexpr float    LASER_KI                = 0.01f;
constexpr float    LASER_KD                = 0.004f;
constexpr float    LASER_DEADBAND_DEG      = 0.05f;
constexpr float    LASER_MAX_CORR_DEG      = 2.0f;
constexpr float    LASER_MAX_INTEGRAL      = 10.0f;
constexpr float    LASER_LOCK_ERROR_DEG    = 0.75f;
constexpr float    LASER_AZ_SIGN           = 1.0f;
constexpr float    LASER_EL_SIGN           = 1.0f;
constexpr float    QPD_LOCK_THRESHOLD      = 0.80f;

// ─────────────── SIMULASYON BOZUCU PROFILLERI ──
constexpr float    DISTURBANCE_FREQ_HZ      = 0.10f;
constexpr float    DISTURBANCE_ROLL_AMP_DEG = 8.0f;
constexpr float    DISTURBANCE_PITCH_AMP_DEG = 8.0f;
constexpr float    DISTURBANCE_BUMP_DEG     = 10.0f;

// ─────────────── GÜVENLIK / ALARM ──────────────
constexpr float    RSSI_LOCK_THRESHOLD_DB = -90.0f;  // Sinyal kilit eşiği
constexpr float    MAX_TRACKING_ERROR_DEG = 5.0f;    // Bu kadar hatada alarm ver
constexpr uint32_t WATCHDOG_TIMEOUT_MS    = 500;     // WDT süresi
