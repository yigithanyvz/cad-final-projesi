#pragma once

namespace mergen_estimation {

class KalmanFilter1D {
public:
  KalmanFilter1D(double process_noise, double measurement_noise, double initial_estimate = 0.0);
  double update(double measurement);
  double estimate() const;

private:
  double q_;
  double r_;
  double x_;
  double p_ = 1.0;
};

}  // namespace mergen_estimation
