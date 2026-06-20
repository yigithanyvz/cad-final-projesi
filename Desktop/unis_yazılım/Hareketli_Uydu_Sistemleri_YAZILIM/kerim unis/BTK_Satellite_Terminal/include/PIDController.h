#pragma once

#include "config.h"
#include "types.h"

#include <cstdint>

class PIDController {
public:
    struct Params {
        float kp;
        float ki;
        float kd;
        float max_integral;
        float output_min;
        float output_max;
        float deadband;
        float deriv_alpha;
        bool  wrap_angle;
    };

    explicit PIDController(const Params& p);

    void reset();
    float compute(float target, float measured, float dt, float feed_forward = 0.0f);

    const PIDState& state() const;
    float lastError() const;

private:
    Params   p_;
    PIDState state_{};
};

class SafetyMonitor {
public:
    struct LimitConfig {
        float hard_min;
        float hard_max;
        float soft_min;
        float soft_max;
        float cable_wrap;
    };

    enum class LimitState { SAFE, SOFT, HARD, FAULT };

    struct CheckResult {
        float       az_safe_command;
        float       el_safe_command;
        LimitState  az_state;
        LimitState  el_state;
        bool        emergency_stop;
        uint16_t    error_flags;
    };

    SafetyMonitor();

    CheckResult checkAndLimit(float az_cmd, float el_cmd,
                              float az_pos, float el_pos,
                              bool az_switch_min, bool az_switch_max,
                              bool el_switch_min, bool el_switch_max);

    LimitState evaluateAxis(float pos, bool sw_min, bool sw_max,
                            const LimitConfig& lim, float cmd_in,
                            float& cmd_out);

private:
    LimitConfig az_limits_{};
    LimitConfig el_limits_{};
};

class AntennaController {
public:
    struct ControlOutput {
        MotorCommand az_cmd;
        MotorCommand el_cmd;
        float        az_error_deg;
        float        el_error_deg;
        bool         az_on_target;
        bool         el_on_target;
        uint16_t     safety_flags;
    };

    AntennaController();

    ControlOutput update(const AntennaTarget& target,
                         const EncoderData& encoder,
                         float dt,
                         bool az_sw_min, bool az_sw_max,
                         bool el_sw_min, bool el_sw_max);

    void reset();

private:
    PIDController az_pid_;
    PIDController el_pid_;
    SafetyMonitor safety_;

    ControlOutput update_internal(float az_target, float el_target,
                                  const EncoderData& enc, float dt,
                                  bool az_sw_min, bool az_sw_max,
                                  bool el_sw_min, bool el_sw_max);

    static float speedToDuty(float speed_dps, float max_speed);
    static PIDController makeAzPID();
    static PIDController makeElPID();
};
