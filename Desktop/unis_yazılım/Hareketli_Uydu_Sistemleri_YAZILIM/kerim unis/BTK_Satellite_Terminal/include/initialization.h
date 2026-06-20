#pragma once

#include "types.h"

extern "C" {
    bool     hal_imu_init(uint8_t i2c_addr);
    bool     hal_gps_init(uint8_t uart_ch, uint32_t baud);
    bool     hal_motor_init(MotorAxis axis);
    bool     hal_encoder_init(MotorAxis axis);
    bool     hal_limit_switch_read(MotorAxis axis, bool& min_hit, bool& max_hit);
    void     hal_motor_set_pwm(MotorAxis axis, MotorDir dir, float duty);
    IMURawData hal_imu_read();
    void     hal_delay_ms(uint32_t ms);
    uint32_t hal_get_tick_ms();
    void     hal_watchdog_kick();
    void     hal_log(const char* msg);
}

class HardwareSelfTest {
public:
    struct TestResult {
        bool imu_ok;
        bool gps_ok;
        bool az_motor_ok;
        bool el_motor_ok;
        bool az_encoder_ok;
        bool el_encoder_ok;
        bool stab_roll_motor_ok;
        bool stab_pitch_motor_ok;
        uint16_t error_flags;

        bool all_ok() const;
    };

    TestResult run();
};

class HomingProcedure {
public:
    bool performHoming();

private:
    bool homeAxis(MotorAxis axis, const char* name, float approach_pct, float backoff_pct);
};

class IMUCalibration {
public:
    struct CalibResult {
        Vec3  bias_accel;
        Vec3  bias_gyro;
        float accel_scale;
        bool  success;
    };

    CalibResult calibrate();
};

struct InitResult {
    HardwareSelfTest::TestResult hw_test;
    IMUCalibration::CalibResult imu_calib;
    bool homing_done;
    bool ready;
};

InitResult system_initialize();
