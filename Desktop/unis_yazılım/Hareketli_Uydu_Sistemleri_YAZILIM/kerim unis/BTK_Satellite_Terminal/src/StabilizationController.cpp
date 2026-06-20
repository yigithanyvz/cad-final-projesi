#include "StabilizationController.h"

#include "config.h"

#include <algorithm>
#include <cmath>

StabilizationController::StabilizationController()
    : roll_pid_(makeRollPid()), pitch_pid_(makePitchPid()) {}

StabilizationOutput StabilizationController::update(const StabilizationInput& input) {
    StabilizationOutput out{};
    out.roll_motor_cmd.axis = MotorAxis::STABILIZER_ROLL;
    out.pitch_motor_cmd.axis = MotorAxis::STABILIZER_PITCH;

    if (!input.enabled || input.dt_s <= 0.0f || input.dt_s > 0.2f) {
        reset();
        out.stable = true;
        return out;
    }

    updateFilteredAngles(input.roll_deg, input.pitch_deg);

    const float roll_ff = -input.roll_rate_dps * STAB_RATE_FF_GAIN;
    const float pitch_ff = -input.pitch_rate_dps * STAB_RATE_FF_GAIN;

    const float counter_roll =
        roll_pid_.compute(0.0f, filtered_roll_deg_, input.dt_s, roll_ff);
    const float counter_pitch =
        pitch_pid_.compute(0.0f, filtered_pitch_deg_, input.dt_s, pitch_ff);

    out.filtered_roll_deg = filtered_roll_deg_;
    out.filtered_pitch_deg = filtered_pitch_deg_;
    out.counter_roll_deg = std::clamp(counter_roll, -STAB_MAX_CMD_DEG, STAB_MAX_CMD_DEG);
    out.counter_pitch_deg = std::clamp(counter_pitch, -STAB_MAX_CMD_DEG, STAB_MAX_CMD_DEG);
    out.x_actuator_mm = std::clamp(
        out.counter_roll_deg * STAB_MM_PER_DEG,
        -STAB_MAX_ACTUATOR_MM,
        STAB_MAX_ACTUATOR_MM);
    out.y_actuator_mm = std::clamp(
        out.counter_pitch_deg * STAB_MM_PER_DEG,
        -STAB_MAX_ACTUATOR_MM,
        STAB_MAX_ACTUATOR_MM);

    const float applied_roll_deg = out.x_actuator_mm / STAB_MM_PER_DEG;
    const float applied_pitch_deg = out.y_actuator_mm / STAB_MM_PER_DEG;
    out.residual_roll_deg = filtered_roll_deg_ + applied_roll_deg;
    out.residual_pitch_deg = filtered_pitch_deg_ + applied_pitch_deg;
    out.residual_error_deg = std::hypot(out.residual_roll_deg, out.residual_pitch_deg);
    out.stable = out.residual_error_deg <= STAB_STABLE_ERROR_DEG;
    out.saturated =
        std::fabs(out.x_actuator_mm) >= STAB_MAX_ACTUATOR_MM ||
        std::fabs(out.y_actuator_mm) >= STAB_MAX_ACTUATOR_MM;

    out.roll_motor_cmd = toMotorCommand(MotorAxis::STABILIZER_ROLL, out.counter_roll_deg);
    out.pitch_motor_cmd = toMotorCommand(MotorAxis::STABILIZER_PITCH, out.counter_pitch_deg);
    return out;
}

void StabilizationController::reset() {
    roll_pid_.reset();
    pitch_pid_.reset();
    filtered_roll_deg_ = 0.0f;
    filtered_pitch_deg_ = 0.0f;
    filter_initialized_ = false;
}

StabilizationInput StabilizationController::fromSensors(
    const Orientation& orientation,
    const IMURawData& imu,
    float dt_s,
    bool enabled)
{
    constexpr float kRadToDeg = 57.2957795131f;
    return {
        orientation.roll_deg,
        orientation.pitch_deg,
        imu.gyro_rads.x * kRadToDeg,
        imu.gyro_rads.y * kRadToDeg,
        dt_s,
        enabled
    };
}

void StabilizationController::updateFilteredAngles(float roll_deg, float pitch_deg) {
    if (!filter_initialized_) {
        filtered_roll_deg_ = roll_deg;
        filtered_pitch_deg_ = pitch_deg;
        filter_initialized_ = true;
        return;
    }

    filtered_roll_deg_ =
        STAB_ATTITUDE_ALPHA * roll_deg + (1.0f - STAB_ATTITUDE_ALPHA) * filtered_roll_deg_;
    filtered_pitch_deg_ =
        STAB_ATTITUDE_ALPHA * pitch_deg + (1.0f - STAB_ATTITUDE_ALPHA) * filtered_pitch_deg_;
}

PIDController StabilizationController::makeRollPid() {
    return PIDController({
        STAB_ROLL_KP, STAB_ROLL_KI, STAB_ROLL_KD,
        STAB_MAX_INTEGRAL,
        -STAB_MAX_CMD_DEG, STAB_MAX_CMD_DEG,
        STAB_DEADBAND_DEG, DERIV_FILTER_ALPHA,
        false
    });
}

PIDController StabilizationController::makePitchPid() {
    return PIDController({
        STAB_PITCH_KP, STAB_PITCH_KI, STAB_PITCH_KD,
        STAB_MAX_INTEGRAL,
        -STAB_MAX_CMD_DEG, STAB_MAX_CMD_DEG,
        STAB_DEADBAND_DEG, DERIV_FILTER_ALPHA,
        false
    });
}

MotorCommand StabilizationController::toMotorCommand(MotorAxis axis, float command_deg) {
    const float duty =
        std::clamp(std::fabs(command_deg) / STAB_MAX_CMD_DEG * 100.0f, 0.0f, 100.0f);
    return {
        axis,
        command_deg > 0.0f ? MotorDir::CW :
            (command_deg < 0.0f ? MotorDir::CCW : MotorDir::STOP),
        duty,
        std::fabs(command_deg)
    };
}

DisturbanceSample DisturbanceScenarioGenerator::sample(
    DisturbanceProfileType profile,
    float time_s)
{
    constexpr float kPi = 3.14159265358979323846f;
    const float w = 2.0f * kPi * DISTURBANCE_FREQ_HZ;
    DisturbanceSample out{};
    out.profile = profile;

    switch (profile) {
        case DisturbanceProfileType::SINE_SWEEP:
            out.roll_deg = DISTURBANCE_ROLL_AMP_DEG * std::sin(w * time_s);
            out.pitch_deg = DISTURBANCE_PITCH_AMP_DEG * std::cos(0.73f * w * time_s);
            out.roll_rate_dps = DISTURBANCE_ROLL_AMP_DEG * w * std::cos(w * time_s);
            out.pitch_rate_dps =
                -DISTURBANCE_PITCH_AMP_DEG * 0.73f * w * std::sin(0.73f * w * time_s);
            break;

        case DisturbanceProfileType::STEP_TILT:
            out.roll_deg = time_s > 1.0f ? DISTURBANCE_ROLL_AMP_DEG : 0.0f;
            out.pitch_deg = time_s > 1.5f ? -DISTURBANCE_PITCH_AMP_DEG : 0.0f;
            break;

        case DisturbanceProfileType::ROAD_BUMP: {
            const float center = 2.0f;
            const float width = 0.18f;
            const float x = (time_s - center) / width;
            const float pulse = DISTURBANCE_BUMP_DEG * std::exp(-x * x);
            out.roll_deg = pulse;
            out.pitch_deg = -0.65f * pulse;
            out.roll_rate_dps = -2.0f * x / width * pulse;
            out.pitch_rate_dps = -0.65f * out.roll_rate_dps;
            break;
        }

        case DisturbanceProfileType::MIXED_NOISE:
            out.roll_deg =
                0.55f * DISTURBANCE_ROLL_AMP_DEG * std::sin(w * time_s) +
                0.9f * pseudoNoise(time_s, 3.1f);
            out.pitch_deg =
                0.55f * DISTURBANCE_PITCH_AMP_DEG * std::cos(1.2f * w * time_s) +
                0.9f * pseudoNoise(time_s, 8.7f);
            out.roll_rate_dps =
                0.55f * DISTURBANCE_ROLL_AMP_DEG * w * std::cos(w * time_s);
            out.pitch_rate_dps =
                -0.55f * DISTURBANCE_PITCH_AMP_DEG * 1.2f * w *
                std::sin(1.2f * w * time_s);
            break;

        case DisturbanceProfileType::NONE:
        default:
            break;
    }

    return out;
}

float DisturbanceScenarioGenerator::pseudoNoise(float time_s, float salt) {
    const float v = std::sin(time_s * 12.9898f + salt) * 43758.5453f;
    return 2.0f * (v - std::floor(v)) - 1.0f;
}
