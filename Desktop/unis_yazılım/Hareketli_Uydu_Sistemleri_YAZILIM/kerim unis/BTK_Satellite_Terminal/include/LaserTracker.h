#pragma once

#include "types.h"

class LaserTracker {
public:
    static LaserSpotData spotFromQpd(const QPDData& qpd);

    AntennaTarget applyCorrection(const AntennaTarget& base_target,
                                  const LaserSpotData& spot,
                                  float dt_s,
                                  LaserTrackingCorrection& correction);

    void reset();

private:
    float az_integral_ = 0.0f;
    float el_integral_ = 0.0f;
    float prev_az_error_deg_ = 0.0f;
    float prev_el_error_deg_ = 0.0f;
    bool initialized_ = false;

    static float normalizeAz(float az_deg);
};
