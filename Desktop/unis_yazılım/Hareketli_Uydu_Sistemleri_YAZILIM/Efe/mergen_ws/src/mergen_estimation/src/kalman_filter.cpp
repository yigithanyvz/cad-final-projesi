#include "mergen_estimation/kalman_filter.hpp"

namespace mergen_estimation {

KalmanFilter1D::KalmanFilter1D(double process_noise, double measurement_noise, double initial_estimate)
    : q_(process_noise), r_(measurement_noise), x_(initial_estimate) {}

double KalmanFilter1D::update(double measurement) {
  p_ += q_;
  const double k = p_ / (p_ + r_);
  x_ += k * (measurement - x_);
  p_ *= (1.0 - k);
  return x_;
}

double KalmanFilter1D::estimate() const { return x_; }

}  // namespace mergen_estimation
