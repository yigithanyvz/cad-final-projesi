#include "LaserTracker.h"

#include "config.h"

#include <algorithm>
#include <cmath>

LaserSpotData LaserTracker::spotFromQpd(const QPDData& qpd) {
    LaserSpotData spot{};
    spot.timestamp_ms = qpd.timestamp_ms;
    if (!qpd.valid || qpd.total_signal <= 0.0f || qpd.confidence < QPD_LOCK_THRESHOLD) {
        return spot;
    }

    spot.x_norm = std::clamp(qpd.x_norm, -1.0f, 1.0f);
    spot.y_norm = std::clamp(qpd.y_norm, -1.0f, 1.0f);
    spot.confidence = qpd.confidence;
    spot.detected = true;
    return spot;
}

AntennaTarget LaserTracker::applyCorrection(
    const AntennaTarget& base_target,
    const LaserSpotData& spot,
    float dt_s,
    LaserTrackingCorrection& correction)
{
    correction = {};

    if (!spot.detected || spot.confidence < CAMERA_MIN_CONFIDENCE ||
        dt_s <= 0.0f || dt_s > 0.2f) {
        reset();
        return base_target;
    }

    correction.az_error_deg =
        std::clamp(spot.x_norm, -1.0f, 1.0f) * (CAMERA_AZ_FOV_DEG * 0.5f);
    correction.el_error_deg =
        std::clamp(spot.y_norm, -1.0f, 1.0f) * (CAMERA_EL_FOV_DEG * 0.5f);

    if (std::fabs(correction.az_error_deg) < LASER_DEADBAND_DEG) {
        correction.az_error_deg = 0.0f;
    }
    if (std::fabs(correction.el_error_deg) < LASER_DEADBAND_DEG) {
        correction.el_error_deg = 0.0f;
    }

    az_integral_ = std::clamp(
        az_integral_ + correction.az_error_deg * dt_s,
        -LASER_MAX_INTEGRAL,
        LASER_MAX_INTEGRAL);
    el_integral_ = std::clamp(
        el_integral_ + correction.el_error_deg * dt_s,
        -LASER_MAX_INTEGRAL,
        LASER_MAX_INTEGRAL);

    const float az_deriv =
        initialized_ ? (correction.az_error_deg - prev_az_error_deg_) / dt_s : 0.0f;
    const float el_deriv =
        initialized_ ? (correction.el_error_deg - prev_el_error_deg_) / dt_s : 0.0f;

    prev_az_error_deg_ = correction.az_error_deg;
    prev_el_error_deg_ = correction.el_error_deg;
    initialized_ = true;

    correction.az_correction_deg = LASER_AZ_SIGN * std::clamp(
        LASER_KP * correction.az_error_deg +
        LASER_KI * az_integral_ +
        LASER_KD * az_deriv,
        -LASER_MAX_CORR_DEG,
        LASER_MAX_CORR_DEG);

    correction.el_correction_deg = LASER_EL_SIGN * std::clamp(
        LASER_KP * correction.el_error_deg +
        LASER_KI * el_integral_ +
        LASER_KD * el_deriv,
        -LASER_MAX_CORR_DEG,
        LASER_MAX_CORR_DEG);

    correction.total_error_deg =
        std::hypot(correction.az_error_deg, correction.el_error_deg);
    correction.locked = correction.total_error_deg <= LASER_LOCK_ERROR_DEG;
    correction.valid = true;

    AntennaTarget corrected = base_target;
    corrected.az_setpoint_deg =
        normalizeAz(base_target.az_setpoint_deg + correction.az_correction_deg);
    corrected.el_setpoint_deg = std::clamp(
        base_target.el_setpoint_deg + correction.el_correction_deg,
        EL_LIMIT_MIN_DEG,
        EL_LIMIT_MAX_DEG);
    return corrected;
}

void LaserTracker::reset() {
    az_integral_ = 0.0f;
    el_integral_ = 0.0f;
    prev_az_error_deg_ = 0.0f;
    prev_el_error_deg_ = 0.0f;
    initialized_ = false;
}

float LaserTracker::normalizeAz(float az_deg) {
    while (az_deg >= 360.0f) az_deg -= 360.0f;
    while (az_deg < 0.0f) az_deg += 360.0f;
    return az_deg;
}
