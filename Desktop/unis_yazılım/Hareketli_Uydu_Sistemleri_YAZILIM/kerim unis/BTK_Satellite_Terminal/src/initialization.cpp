#include "initialization.h"

#include "config.h"

#include <cmath>

bool HardwareSelfTest::TestResult::all_ok() const {
    return imu_ok && gps_ok && az_motor_ok && el_motor_ok &&
           az_encoder_ok && el_encoder_ok &&
           stab_roll_motor_ok && stab_pitch_motor_ok;
}

HardwareSelfTest::TestResult HardwareSelfTest::run() {
    TestResult result{};

    hal_log("[SELF-TEST] BNO055 IMU kontrol ediliyor...");
    result.imu_ok = hal_imu_init(BNO055_I2C_ADDR);
    if (!result.imu_ok) {
        result.error_flags |= static_cast<uint16_t>(ErrorCode::IMU_FAULT);
        hal_log("[HATA] IMU yanit vermiyor!");
    } else {
        const IMURawData sample = hal_imu_read();
        const float accel_mag = sample.accel_ms2.norm();
        if (std::fabs(accel_mag - GRAVITY_MS2) > 2.0f) {
            result.imu_ok = false;
            result.error_flags |= static_cast<uint16_t>(ErrorCode::IMU_FAULT);
            hal_log("[HATA] IMU ivmeolcer kalibrasyon disinda!");
        } else {
            hal_log("[OK] BNO055 IMU hazir.");
        }
    }

    hal_log("[SELF-TEST] ZED-F9P GNSS/RTK kontrol ediliyor...");
    result.gps_ok = hal_gps_init(GPS_UART_CHANNEL, GPS_BAUD_RATE);
    if (!result.gps_ok) {
        result.error_flags |= static_cast<uint16_t>(ErrorCode::GPS_NO_FIX);
        hal_log("[UYARI] ZED-F9P modulu yanit vermiyor.");
    } else {
        hal_log("[OK] ZED-F9P aktif (GNSS/RTK fix bekleniyor).");
    }

    hal_log("[SELF-TEST] Azimut motoru kontrol ediliyor...");
    result.az_motor_ok = hal_motor_init(MotorAxis::AZIMUTH);
    result.az_encoder_ok = hal_encoder_init(MotorAxis::AZIMUTH);
    if (!result.az_motor_ok) result.error_flags |= static_cast<uint16_t>(ErrorCode::AZ_MOTOR_FAIL);
    if (!result.az_encoder_ok) result.error_flags |= static_cast<uint16_t>(ErrorCode::AZ_MOTOR_FAIL);

    hal_log("[SELF-TEST] Elevasyon motoru kontrol ediliyor...");
    result.el_motor_ok = hal_motor_init(MotorAxis::ELEVATION);
    result.el_encoder_ok = hal_encoder_init(MotorAxis::ELEVATION);
    if (!result.el_motor_ok) result.error_flags |= static_cast<uint16_t>(ErrorCode::EL_MOTOR_FAIL);
    if (!result.el_encoder_ok) result.error_flags |= static_cast<uint16_t>(ErrorCode::EL_MOTOR_FAIL);

    hal_log("[SELF-TEST] Mama kabi X/Y stabilizer motorlari kontrol ediliyor...");
    result.stab_roll_motor_ok = hal_motor_init(MotorAxis::STABILIZER_ROLL);
    result.stab_pitch_motor_ok = hal_motor_init(MotorAxis::STABILIZER_PITCH);
    if (!result.stab_roll_motor_ok || !result.stab_pitch_motor_ok) {
        result.error_flags |= static_cast<uint16_t>(ErrorCode::STAB_MOTOR_FAIL);
        hal_log("[HATA] Mama kabi stabilizasyon motorlari hazir degil!");
    }

    hal_log(result.all_ok() ?
        "[SELF-TEST] Tum donanim testleri BASARILI." :
        "[SELF-TEST] Donanim testleri BASARISIZ.");
    return result;
}

bool HomingProcedure::performHoming() {
    hal_log("[HOMING] Baslaniyor...");
    const bool az_ok = homeAxis(MotorAxis::AZIMUTH, "Azimut", 5.0f, 3.0f);
    const bool el_ok = homeAxis(MotorAxis::ELEVATION, "Elevasyon", 5.0f, 3.0f);
    hal_log((az_ok && el_ok) ?
        "[HOMING] Her iki eksen HOME konumunda." :
        "[HOMING] BASARISIZ.");
    return az_ok && el_ok;
}

bool HomingProcedure::homeAxis(
    MotorAxis axis,
    const char* name,
    float approach_pct,
    float backoff_pct)
{
    constexpr uint32_t kTimeoutMs = 15000;
    const uint32_t start = hal_get_tick_ms();
    bool min_hit = false;
    bool max_hit = false;

    hal_log(name);
    hal_log(": MIN limitine dogru gidiliyor...");
    hal_motor_set_pwm(axis, MotorDir::CW, approach_pct);

    while (!min_hit) {
        hal_watchdog_kick();
        hal_limit_switch_read(axis, min_hit, max_hit);
        hal_delay_ms(5);

        if (hal_get_tick_ms() - start > kTimeoutMs) {
            hal_motor_set_pwm(axis, MotorDir::STOP, 0.0f);
            hal_log("[HATA] Homing timeout!");
            return false;
        }
    }

    hal_motor_set_pwm(axis, MotorDir::STOP, 0.0f);
    hal_delay_ms(100);

    hal_log(name);
    hal_log(": Geri cekiliyor...");
    hal_motor_set_pwm(axis, MotorDir::CCW, backoff_pct);
    hal_delay_ms(400);
    hal_motor_set_pwm(axis, MotorDir::STOP, 0.0f);

    hal_log(name);
    hal_log(": HOME noktasi ayarlandi.");
    return true;
}

IMUCalibration::CalibResult IMUCalibration::calibrate() {
    hal_log("[KALIBRASYON] Lutfen cihazi hareketsiz tutun...");

    Vec3 sum_accel{};
    Vec3 sum_gyro{};
    float sum_accel_mag = 0.0f;

    for (uint32_t i = 0; i < CALIBRATION_SAMPLES; ++i) {
        hal_watchdog_kick();
        const IMURawData d = hal_imu_read();
        sum_accel.x += d.accel_ms2.x;
        sum_accel.y += d.accel_ms2.y;
        sum_accel.z += d.accel_ms2.z;
        sum_gyro.x += d.gyro_rads.x;
        sum_gyro.y += d.gyro_rads.y;
        sum_gyro.z += d.gyro_rads.z;
        sum_accel_mag += d.accel_ms2.norm();
        hal_delay_ms(static_cast<uint32_t>(1000.0f / IMU_SAMPLE_RATE_HZ));
    }

    const float inv_n = 1.0f / static_cast<float>(CALIBRATION_SAMPLES);
    const Vec3 mean_accel{
        sum_accel.x * inv_n,
        sum_accel.y * inv_n,
        sum_accel.z * inv_n
    };
    const Vec3 mean_gyro{
        sum_gyro.x * inv_n,
        sum_gyro.y * inv_n,
        sum_gyro.z * inv_n
    };
    const float mean_mag = sum_accel_mag * inv_n;

    const Vec3 g_ref = mean_accel.normalized() * GRAVITY_MS2;
    const Vec3 bias_accel{
        mean_accel.x - g_ref.x,
        mean_accel.y - g_ref.y,
        mean_accel.z - g_ref.z
    };
    const float scale = mean_mag / GRAVITY_MS2;
    const bool ok = std::fabs(scale - 1.0f) < 0.05f && mean_gyro.norm() < 0.1f;

    hal_log(ok ?
        "[KALIBRASYON] Tamamlandi." :
        "[UYARI] Kalibrasyon kalitesi dusuk.");
    return {bias_accel, mean_gyro, scale, ok};
}

InitResult system_initialize() {
    InitResult result{};

    HardwareSelfTest self_test;
    result.hw_test = self_test.run();
    if (!result.hw_test.all_ok()) {
        hal_log("[INIT] Donanim testi basarisiz.");
        result.ready = false;
        return result;
    }

    HomingProcedure homing;
    result.homing_done = homing.performHoming();
    if (!result.homing_done) {
        hal_log("[INIT] Homing basarisiz.");
        result.ready = false;
        return result;
    }

    IMUCalibration imu_cal;
    result.imu_calib = imu_cal.calibrate();
    result.ready = true;
    hal_log("[INIT] Sistem hazir.");
    return result;
}
