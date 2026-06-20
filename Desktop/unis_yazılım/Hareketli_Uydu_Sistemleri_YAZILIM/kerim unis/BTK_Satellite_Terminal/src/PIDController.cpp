#include "PIDController.h"

#include <algorithm>
#include <cmath>

PIDController::PIDController(const Params& p)
    : p_(p), state_{} {}

void PIDController::reset() {
    state_ = {};
}

float PIDController::compute(float target, float measured, float dt, float feed_forward) {
    if (dt <= 0.0f || dt > 0.5f) return 0.0f;
    state_.last_dt = dt;

    float error = target - measured;
    if (p_.wrap_angle) {
        while (error > 180.0f) error -= 360.0f;
        while (error < -180.0f) error += 360.0f;
    }

    if (std::fabs(error) < p_.deadband) {
        state_.integral = 0.0f;
        state_.prev_error = 0.0f;
        state_.output = std::clamp(feed_forward, p_.output_min, p_.output_max);
        return state_.output;
    }

    const float p_term = p_.kp * error;

    const bool anti_windup =
        (state_.output >= p_.output_max && error > 0.0f) ||
        (state_.output <= p_.output_min && error < 0.0f);
    if (!anti_windup) {
        state_.integral += error * dt;
    }
    state_.integral = std::clamp(state_.integral, -p_.max_integral, p_.max_integral);
    const float i_term = p_.ki * state_.integral;

    const float d_raw = (error - state_.prev_error) / dt;
    const float d_filt =
        p_.deriv_alpha * d_raw + (1.0f - p_.deriv_alpha) * state_.prev_derivative;
    const float d_term = p_.kd * d_filt;

    state_.prev_error = error;
    state_.prev_derivative = d_filt;

    state_.output = std::clamp(
        p_term + i_term + d_term + feed_forward,
        p_.output_min,
        p_.output_max);
    return state_.output;
}

const PIDState& PIDController::state() const {
    return state_;
}

float PIDController::lastError() const {
    return state_.prev_error;
}

SafetyMonitor::SafetyMonitor() {
    az_limits_ = {AZ_LIMIT_MIN_DEG, AZ_LIMIT_MAX_DEG, 2.0f, 358.0f, AZ_WRAP_THRESHOLD_DEG};
    el_limits_ = {EL_LIMIT_MIN_DEG, EL_LIMIT_MAX_DEG, 1.0f, 89.0f, 0.0f};
}

SafetyMonitor::CheckResult SafetyMonitor::checkAndLimit(
    float az_cmd, float el_cmd,
    float az_pos, float el_pos,
    bool az_switch_min, bool az_switch_max,
    bool el_switch_min, bool el_switch_max)
{
    CheckResult res{};
    res.az_state = evaluateAxis(
        az_pos, az_switch_min, az_switch_max, az_limits_, az_cmd, res.az_safe_command);
    res.el_state = evaluateAxis(
        el_pos, el_switch_min, el_switch_max, el_limits_, el_cmd, res.el_safe_command);

    if (res.az_state == LimitState::HARD || res.az_state == LimitState::FAULT) {
        res.error_flags |= static_cast<uint16_t>(ErrorCode::AZ_LIMIT_HIT);
    }
    if (res.el_state == LimitState::HARD || res.el_state == LimitState::FAULT) {
        res.error_flags |= static_cast<uint16_t>(ErrorCode::EL_LIMIT_HIT);
    }

    res.emergency_stop = az_switch_min || az_switch_max || el_switch_min || el_switch_max;
    return res;
}

SafetyMonitor::LimitState SafetyMonitor::evaluateAxis(
    float pos, bool sw_min, bool sw_max,
    const LimitConfig& lim, float cmd_in,
    float& cmd_out)
{
    cmd_out = cmd_in;

    if (sw_min || sw_max) {
        cmd_out = 0.0f;
        return LimitState::FAULT;
    }
    if (pos <= lim.hard_min && cmd_in < 0.0f) {
        cmd_out = 0.0f;
        return LimitState::HARD;
    }
    if (pos >= lim.hard_max && cmd_in > 0.0f) {
        cmd_out = 0.0f;
        return LimitState::HARD;
    }
    if (pos <= lim.soft_min || pos >= lim.soft_max) {
        cmd_out = cmd_in * 0.5f;
        return LimitState::SOFT;
    }
    if (lim.cable_wrap > 0.0f && pos >= lim.cable_wrap) {
        const float scale =
            1.0f - (pos - lim.cable_wrap) / (lim.hard_max - lim.cable_wrap);
        cmd_out = cmd_in * std::clamp(scale, 0.0f, 1.0f);
        return LimitState::SOFT;
    }

    return LimitState::SAFE;
}

AntennaController::AntennaController()
    : az_pid_(makeAzPID()), el_pid_(makeElPID()), safety_() {}

AntennaController::ControlOutput AntennaController::update(
    const AntennaTarget& target,
    const EncoderData& encoder,
    float dt,
    bool az_sw_min, bool az_sw_max,
    bool el_sw_min, bool el_sw_max)
{
    if (!target.satellite_above_horizon) {
        az_pid_.reset();
        el_pid_.reset();
        return update_internal(
            0.0f, 0.0f, encoder, dt,
            az_sw_min, az_sw_max, el_sw_min, el_sw_max);
    }

    return update_internal(
        target.az_setpoint_deg,
        target.el_setpoint_deg,
        encoder,
        dt,
        az_sw_min,
        az_sw_max,
        el_sw_min,
        el_sw_max);
}

void AntennaController::reset() {
    az_pid_.reset();
    el_pid_.reset();
}

AntennaController::ControlOutput AntennaController::update_internal(
    float az_target, float el_target,
    const EncoderData& enc, float dt,
    bool az_sw_min, bool az_sw_max,
    bool el_sw_min, bool el_sw_max)
{
    ControlOutput out{};
    out.az_error_deg = az_target - enc.az_deg;
    out.el_error_deg = el_target - enc.el_deg;
    while (out.az_error_deg > 180.0f) out.az_error_deg -= 360.0f;
    while (out.az_error_deg < -180.0f) out.az_error_deg += 360.0f;

    const float az_raw = az_pid_.compute(az_target, enc.az_deg, dt);
    const float el_raw = el_pid_.compute(el_target, enc.el_deg, dt);

    const auto safety_res = safety_.checkAndLimit(
        az_raw, el_raw,
        enc.az_deg, enc.el_deg,
        az_sw_min, az_sw_max,
        el_sw_min, el_sw_max);
    out.safety_flags = safety_res.error_flags;

    const float az_safe = safety_res.az_safe_command;
    out.az_cmd.axis = MotorAxis::AZIMUTH;
    out.az_cmd.speed_dps = std::fabs(az_safe);
    out.az_cmd.duty_pct = speedToDuty(std::fabs(az_safe), AZ_MAX_SPEED_DPS);
    out.az_cmd.direction =
        az_safe > 0.0f ? MotorDir::CW : (az_safe < 0.0f ? MotorDir::CCW : MotorDir::STOP);

    const float el_safe = safety_res.el_safe_command;
    out.el_cmd.axis = MotorAxis::ELEVATION;
    out.el_cmd.speed_dps = std::fabs(el_safe);
    out.el_cmd.duty_pct = speedToDuty(std::fabs(el_safe), EL_MAX_SPEED_DPS);
    out.el_cmd.direction =
        el_safe > 0.0f ? MotorDir::CW : (el_safe < 0.0f ? MotorDir::CCW : MotorDir::STOP);

    out.az_on_target = std::fabs(out.az_error_deg) < PID_DEADBAND_DEG * 2.0f;
    out.el_on_target = std::fabs(out.el_error_deg) < PID_DEADBAND_DEG * 2.0f;

    if (safety_res.emergency_stop) {
        out.az_cmd.direction = MotorDir::STOP;
        out.el_cmd.direction = MotorDir::STOP;
        out.az_cmd.duty_pct = 0.0f;
        out.el_cmd.duty_pct = 0.0f;
    }

    return out;
}

float AntennaController::speedToDuty(float speed_dps, float max_speed) {
    return std::clamp(speed_dps / max_speed * 100.0f, 0.0f, 100.0f);
}

PIDController AntennaController::makeAzPID() {
    return PIDController({
        AZ_KP, AZ_KI, AZ_KD,
        AZ_MAX_INTEGRAL,
        -AZ_MAX_SPEED_DPS, AZ_MAX_SPEED_DPS,
        PID_DEADBAND_DEG, DERIV_FILTER_ALPHA,
        true
    });
}

PIDController AntennaController::makeElPID() {
    return PIDController({
        EL_KP, EL_KI, EL_KD,
        EL_MAX_INTEGRAL,
        -EL_MAX_SPEED_DPS, EL_MAX_SPEED_DPS,
        PID_DEADBAND_DEG, DERIV_FILTER_ALPHA,
        false
    });
}
