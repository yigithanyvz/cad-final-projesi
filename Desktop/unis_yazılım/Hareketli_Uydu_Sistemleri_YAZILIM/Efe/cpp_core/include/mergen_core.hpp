#pragma once

#include <algorithm>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <sstream>
#include <string>

namespace mergen {

constexpr double kPi = 3.14159265358979323846;

inline double clamp(double value, double minimum, double maximum) {
    return std::max(minimum, std::min(maximum, value));
}

inline double wrapDegrees(double angle_deg) {
    while (angle_deg > 180.0) angle_deg -= 360.0;
    while (angle_deg < -180.0) angle_deg += 360.0;
    return angle_deg;
}

inline double degToRad(double degrees) {
    return degrees * kPi / 180.0;
}

struct PidGains {
    double kp = 0.0;
    double ki = 0.0;
    double kd = 0.0;
    double min_output = -1.0;
    double max_output = 1.0;
};

class PidController {
public:
    explicit PidController(PidGains gains) : gains_(gains) {}

    double update(double target, double measurement, double dt_s, bool cyclic_degrees = false) {
        if (dt_s <= 0.0) return 0.0;

        double error = target - measurement;
        if (cyclic_degrees) error = wrapDegrees(error);

        const double candidate_integral = integral_ + error * dt_s;
        const double derivative = has_previous_ ? (error - previous_error_) / dt_s : 0.0;
        const double raw_output = gains_.kp * error + gains_.ki * candidate_integral + gains_.kd * derivative;
        const double output = clamp(raw_output, gains_.min_output, gains_.max_output);

        // Anti-windup: cikis doyuma gittiginde integratoru ayni yonde buyutmuyoruz.
        const bool saturated_high = raw_output > gains_.max_output && error > 0.0;
        const bool saturated_low = raw_output < gains_.min_output && error < 0.0;
        if (!saturated_high && !saturated_low) integral_ = candidate_integral;

        previous_error_ = error;
        has_previous_ = true;
        return output;
    }

    void reset() {
        integral_ = 0.0;
        previous_error_ = 0.0;
        has_previous_ = false;
    }

private:
    PidGains gains_;
    double integral_ = 0.0;
    double previous_error_ = 0.0;
    bool has_previous_ = false;
};

class KalmanFilter1D {
public:
    KalmanFilter1D(double process_noise, double measurement_noise, double initial_estimate = 0.0)
        : q_(process_noise), r_(measurement_noise), x_(initial_estimate) {}

    double update(double measurement) {
        p_ += q_;
        const double gain = p_ / (p_ + r_);
        x_ += gain * (measurement - x_);
        p_ *= (1.0 - gain);
        return x_;
    }

    double estimate() const { return x_; }

private:
    double q_ = 0.01;
    double r_ = 0.25;
    double x_ = 0.0;
    double p_ = 1.0;
};

class RateLimitedAxis {
public:
    RateLimitedAxis(double initial_position_deg, double max_velocity_deg_s, double time_constant_s, double backlash_deg)
        : position_deg_(initial_position_deg), max_velocity_deg_s_(max_velocity_deg_s),
          time_constant_s_(time_constant_s), backlash_deg_(backlash_deg) {}

    double update(double command_position_deg, double dt_s, bool cyclic) {
        double error = command_position_deg - position_deg_;
        if (cyclic) error = wrapDegrees(error);
        if (std::abs(error) <= backlash_deg_) return position_deg_;

        const double desired_velocity = error / std::max(time_constant_s_, 0.001);
        const double velocity = clamp(desired_velocity, -max_velocity_deg_s_, max_velocity_deg_s_);
        position_deg_ += velocity * dt_s;
        if (cyclic) {
            while (position_deg_ >= 360.0) position_deg_ -= 360.0;
            while (position_deg_ < 0.0) position_deg_ += 360.0;
        }
        return position_deg_;
    }

    double position() const { return position_deg_; }

private:
    double position_deg_ = 0.0;
    double max_velocity_deg_s_ = 30.0;
    double time_constant_s_ = 0.15;
    double backlash_deg_ = 0.0;
};

struct SummaryMetrics {
    double first_lock_time_s = -1.0;
    double mean_error_deg = 0.0;
    double max_error_deg = 0.0;
    double settled_mean_error_deg = 0.0;
    double lock_ratio_percent = 0.0;
    double settled_lock_ratio_percent = 0.0;
};

inline void writeLiveState(const std::string& path,
                           double time_s,
                           double azimuth_deg,
                           double elevation_deg,
                           double target_azimuth_deg,
                           double target_elevation_deg,
                           double roll_deg,
                           double pitch_deg,
                           double error_deg,
                           bool locked,
                           const std::string& mode) {
    std::ofstream file(path, std::ios::trunc);
    file << std::fixed << std::setprecision(4);
    file << "{\n";
    file << "  \"time_s\": " << time_s << ",\n";
    file << "  \"azimuth_deg\": " << azimuth_deg << ",\n";
    file << "  \"elevation_deg\": " << elevation_deg << ",\n";
    file << "  \"target_azimuth_deg\": " << target_azimuth_deg << ",\n";
    file << "  \"target_elevation_deg\": " << target_elevation_deg << ",\n";
    file << "  \"roll_deg\": " << roll_deg << ",\n";
    file << "  \"pitch_deg\": " << pitch_deg << ",\n";
    file << "  \"boresight_error_deg\": " << error_deg << ",\n";
    file << "  \"locked\": " << (locked ? "true" : "false") << ",\n";
    file << "  \"mode\": \"" << mode << "\"\n";
    file << "}\n";
}

inline std::string timestampSeedText(unsigned int seed) {
    std::ostringstream stream;
    stream << seed;
    return stream.str();
}

}  // namespace mergen
