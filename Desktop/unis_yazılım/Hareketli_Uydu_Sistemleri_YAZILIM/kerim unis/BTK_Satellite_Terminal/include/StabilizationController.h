#pragma once

#include "PIDController.h"
#include "types.h"

class StabilizationController {
public:
    StabilizationController();

    StabilizationOutput update(const StabilizationInput& input);
    void reset();

    static StabilizationInput fromSensors(const Orientation& orientation,
                                          const IMURawData& imu,
                                          float dt_s,
                                          bool enabled);

private:
    PIDController roll_pid_;
    PIDController pitch_pid_;
    float filtered_roll_deg_ = 0.0f;
    float filtered_pitch_deg_ = 0.0f;
    bool filter_initialized_ = false;

    void updateFilteredAngles(float roll_deg, float pitch_deg);

    static PIDController makeRollPid();
    static PIDController makePitchPid();
    static MotorCommand toMotorCommand(MotorAxis axis, float command_deg);
};

class DisturbanceScenarioGenerator {
public:
    static DisturbanceSample sample(DisturbanceProfileType profile, float time_s);

private:
    static float pseudoNoise(float time_s, float salt);
};
