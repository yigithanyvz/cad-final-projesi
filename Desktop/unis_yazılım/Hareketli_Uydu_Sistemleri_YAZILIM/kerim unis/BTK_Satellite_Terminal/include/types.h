#pragma once
// ============================================================
//  types.h  —  Tüm Veri Yapıları ve Enum'lar
//  Hareketli Uydu Terminali  |  v1.0
// ============================================================

#include <cstdint>
#include <cmath>
#include <array>

// ════════════════════════════════════════════════════════════
//  TEMEL MATEMATİK TİPLERİ
// ════════════════════════════════════════════════════════════

struct Vec3 {
    float x, y, z;
    Vec3(float x=0,float y=0,float z=0): x(x),y(y),z(z){}
    Vec3 operator+(const Vec3& o) const { return {x+o.x, y+o.y, z+o.z}; }
    Vec3 operator-(const Vec3& o) const { return {x-o.x, y-o.y, z-o.z}; }
    Vec3 operator*(float s)       const { return {x*s, y*s, z*s}; }
    float norm()                  const { return sqrtf(x*x + y*y + z*z); }
    Vec3 normalized()             const { float n=norm(); return n>1e-9f ? *this*(1.f/n) : Vec3{}; }
};

struct Vec3d {
    double x, y, z;
};

// Quaternion: q = [w, x, y, z]
struct Quaternion {
    float w, x, y, z;
    Quaternion(float w=1,float x=0,float y=0,float z=0): w(w),x(x),y(y),z(z){}
    float norm() const { return sqrtf(w*w + x*x + y*y + z*z); }
    Quaternion normalized() const {
        float n = norm();
        return n > 1e-9f ? Quaternion{w/n, x/n, y/n, z/n} : Quaternion{};
    }
    Quaternion conjugate() const { return {w, -x, -y, -z}; }
    Quaternion operator*(const Quaternion& q) const {
        return {
            w*q.w - x*q.x - y*q.y - z*q.z,
            w*q.x + x*q.w + y*q.z - z*q.y,
            w*q.y - x*q.z + y*q.w + z*q.x,
            w*q.z + x*q.y - y*q.x + z*q.w
        };
    }
};

// ════════════════════════════════════════════════════════════
//  COĞRAFÎ KOORDİNATLAR
// ════════════════════════════════════════════════════════════

struct LLA {          // Enlem/Boylam/İrtifa
    double lat_deg;   // Enlem  (°, kuzey pozitif)
    double lon_deg;   // Boylam (°, doğu pozitif)
    double alt_m;     // İrtifa (metre, deniz seviyesinden)
};

struct ECEF {         // Earth-Centered Earth-Fixed (metre)
    double x, y, z;
};

struct AzEl {
    float az_deg;     // Azimut   (0-360°, kuzeyden saat yönüne)
    float el_deg;     // Elevasyon (0-90°, ufuktan yukarı)
    float range_km;   // Uyduya mesafe (km)
};

// ════════════════════════════════════════════════════════════
//  SENSÖR HAM VERİSİ
// ════════════════════════════════════════════════════════════

struct IMURawData {
    Vec3     accel_ms2;    // m/s² — ivmeölçer
    Vec3     gyro_rads;    // rad/s — jiroskop
    uint32_t timestamp_ms;
    bool     valid;
};

struct GPSData {
    LLA      position;
    float    speed_ms;      // Hız m/s
    float    heading_deg;   // GPS yönü (araç hareketi yönü)
    float    hdop;          // Yatay konum doğruluk faktörü
    uint8_t  satellites;    // Görünen uydu sayısı
    uint32_t timestamp_ms;
    bool     fix_valid;
};

// KTR nihai mimarisinde konum kaynağı ZED-F9P GNSS/RTK modülüdür.
using GNSSData = GPSData;

// ════════════════════════════════════════════════════════════
//  TLE (TWO LINE ELEMENT) VERİSİ
// ════════════════════════════════════════════════════════════

struct TLEData {
    char     name[25];
    // Satır 1
    uint32_t catalog_num;
    char     classification;
    double   epoch_year;        // 2-digit year
    double   epoch_day;         // Day of year + fractional day
    double   mean_motion_dot;   // rev/day²
    double   mean_motion_ddot;  // rev/day³
    double   bstar;             // Drag term (1/earth radii)
    // Satır 2
    double   inclination_deg;
    double   raan_deg;          // Right Ascension of Asc. Node
    double   eccentricity;
    double   arg_perigee_deg;
    double   mean_anomaly_deg;
    double   mean_motion_revday;
    uint32_t rev_number;
    bool     valid;
};

// SGP4 için ara hesaplama değerleri (bir kez hesaplanır)
struct SGP4Elements {
    double  a;            // Semi-major axis (ER)
    double  e;            // Eccentricity
    double  i;            // Inclination (rad)
    double  Omega;        // RAAN (rad)
    double  omega;        // Arg of perigee (rad)
    double  M0;           // Mean anomaly at epoch (rad)
    double  n0;           // Mean motion at epoch (rad/min)
    double  n_dot;
    double  bstar;
    double  epoch_jd;     // Julian Date at epoch
};

// ════════════════════════════════════════════════════════════
//  İŞLENMİŞ / FÜZE EDİLMİŞ VERİ
// ════════════════════════════════════════════════════════════

// EKF çıktısı — Terminal yönelimi
struct Orientation {
    Quaternion q;           // Birim quaternion
    float      roll_deg;    // Roll açısı
    float      pitch_deg;   // Pitch açısı (elevasyon telafisi için)
    float      yaw_deg;     // Yaw açısı (kuzeyden)
    Vec3       gyro_bias;   // Tahmini jiroskop bias'ı
    bool       converged;
};

// Anten hedef açıları (motor setpoint'leri)
struct AntennaTarget {
    float az_setpoint_deg;   // Azimut hedefi
    float el_setpoint_deg;   // Elevasyon hedefi
    AzEl  satellite_azel;    // Ham uydu Az/El (telafi uygulanmadan önce)
    bool  satellite_above_horizon;
};

// Mama kabı stabilizasyon giriş/çıkışları.
struct StabilizationInput {
    float roll_deg;       // BNO055/EKF roll ölçümü
    float pitch_deg;      // BNO055/EKF pitch ölçümü
    float roll_rate_dps;  // Gyro x açısal hızı (deg/s)
    float pitch_rate_dps; // Gyro y açısal hızı (deg/s)
    float dt_s;
    bool  enabled;
};

// Kamera veya QPD/lazer algılama sonucu.
struct CameraObjectDetection {
    float center_x_px;
    float center_y_px;
    float width_px;
    float height_px;
    float confidence;
    bool  detected;
};

struct LaserSpotData {
    float    x_norm;       // Görüntü merkezine göre normalize x hatası (-1..1)
    float    y_norm;       // Görüntü merkezine göre normalize y hatası (-1..1)
    float    confidence;
    uint32_t timestamp_ms;
    bool     detected;
};

struct QPDData {
    float    x_norm;       // QPD ex hata oranı
    float    y_norm;       // QPD ey hata oranı
    float    total_signal; // Toplam optik güç
    float    confidence;
    uint32_t timestamp_ms;
    bool     valid;
};

struct LaserTrackingCorrection {
    float az_error_deg;
    float el_error_deg;
    float az_correction_deg;
    float el_correction_deg;
    float total_error_deg;
    bool  locked;
    bool  valid;
};

// ════════════════════════════════════════════════════════════
//  PID KONTROL YAPISI
// ════════════════════════════════════════════════════════════

struct PIDState {
    float  integral;
    float  prev_error;
    float  prev_derivative;   // Türev filtrelemesi için
    float  output;
    float  last_dt;
};

// ════════════════════════════════════════════════════════════
//  MOTOR SÜRÜCÜ
// ════════════════════════════════════════════════════════════

enum class MotorAxis : uint8_t {
    AZIMUTH = 0,
    ELEVATION = 1,
    STABILIZER_ROLL = 2,
    STABILIZER_PITCH = 3
};
enum class MotorDir  : uint8_t { STOP = 0, CW = 1, CCW = 2 };

struct MotorCommand {
    MotorAxis axis;
    MotorDir  direction;
    float     duty_pct;    // PWM görev döngüsü 0-100%
    float     speed_dps;   // Hedef açısal hız (°/s)
};

struct EncoderData {
    float    az_deg;       // Azimut encoder açısı
    float    el_deg;       // Elevasyon encoder açısı
    float    az_speed_dps; // Anlık azimut hızı
    float    el_speed_dps; // Anlık elevasyon hızı
    uint32_t timestamp_ms;
    bool     valid;
};

struct StabilizationOutput {
    MotorCommand roll_motor_cmd;
    MotorCommand pitch_motor_cmd;
    float filtered_roll_deg;
    float filtered_pitch_deg;
    float counter_roll_deg;
    float counter_pitch_deg;
    float x_actuator_mm;
    float y_actuator_mm;
    float residual_roll_deg;
    float residual_pitch_deg;
    float residual_error_deg;
    bool  stable;
    bool  saturated;
};

enum class DisturbanceProfileType : uint8_t {
    NONE = 0,
    SINE_SWEEP = 1,
    STEP_TILT = 2,
    ROAD_BUMP = 3,
    MIXED_NOISE = 4
};

struct DisturbanceSample {
    DisturbanceProfileType profile;
    float roll_deg;
    float pitch_deg;
    float roll_rate_dps;
    float pitch_rate_dps;
};

// ════════════════════════════════════════════════════════════
//  SİSTEM DURUMU (State Machine)
// ════════════════════════════════════════════════════════════

enum class SystemState : uint8_t {
    POWER_ON      = 0,
    HW_SELF_TEST  = 1,
    HOMING        = 2,
    CALIBRATING   = 3,
    IDLE          = 4,
    AUTO_TRACKING = 5,
    MANUAL        = 6,
    ERROR         = 7
};

enum class ErrorCode : uint16_t {
    NONE          = 0x0000,
    IMU_FAULT     = 0x0001,
    GPS_NO_FIX    = 0x0002,
    AZ_MOTOR_FAIL = 0x0004,
    EL_MOTOR_FAIL = 0x0008,
    TLE_INVALID   = 0x0010,
    AZ_LIMIT_HIT  = 0x0020,
    EL_LIMIT_HIT  = 0x0040,
    WATCHDOG      = 0x0080,
    STAB_MOTOR_FAIL = 0x0100,
    OPTICAL_TRACK_LOST = 0x0200,
    GNSS_STALE    = 0x0400
};

// ════════════════════════════════════════════════════════════
//  TELEMETRİ PAKETİ (UART üzerinden PC'ye)
// ════════════════════════════════════════════════════════════
#pragma pack(push, 1)
struct TelemetryPacket {
    uint16_t    magic;           // 0xABCD
    uint32_t    timestamp_ms;
    uint8_t     system_state;
    uint16_t    error_flags;
    // Konum
    float       lat_deg;
    float       lon_deg;
    float       alt_m;
    // Yönelim
    float       roll_deg;
    float       pitch_deg;
    float       yaw_deg;
    // Anten açıları (encoder'dan)
    float       az_actual_deg;
    float       el_actual_deg;
    // Hedef açılar
    float       az_target_deg;
    float       el_target_deg;
    // Hata açıları
    float       az_error_deg;
    float       el_error_deg;
    // Uydu bilgisi
    float       sat_az_deg;
    float       sat_el_deg;
    float       sat_range_km;
    // Mama kabı stabilizasyonu
    float       stab_residual_error_deg;
    float       stab_x_actuator_mm;
    float       stab_y_actuator_mm;
    uint8_t     stab_stable;
    uint8_t     stab_saturated;
    // QPD/kamera ince takip
    float       fine_az_error_deg;
    float       fine_el_error_deg;
    uint8_t     fine_tracking_locked;
    // Sinyal
    int8_t      rssi_dbm;
    // Checksum
    uint16_t    crc16;
};
#pragma pack(pop)

// ════════════════════════════════════════════════════════════
//  KULLANICI KOMUTLARI (GUI → Terminal)
// ════════════════════════════════════════════════════════════

enum class UserCommand : uint8_t {
    NONE          = 0,
    SET_AUTO_MODE = 1,
    SET_MANUAL    = 2,
    MANUAL_AZ     = 3,   // payload: float az_deg
    MANUAL_EL     = 4,   // payload: float el_deg
    LOAD_TLE      = 5,   // payload: TLEData
    HOME          = 6,
    EMERGENCY_STOP= 7
};

struct CommandPacket {
    UserCommand cmd;
    union {
        float    angle_deg;
        TLEData  tle;
    } payload;
};
