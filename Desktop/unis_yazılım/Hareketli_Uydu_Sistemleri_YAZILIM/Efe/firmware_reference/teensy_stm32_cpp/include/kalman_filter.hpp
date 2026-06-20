#pragma once

class KalmanFilter1D {
public:
  KalmanFilter1D(float process_noise, float measurement_noise)
      : q_(process_noise), r_(measurement_noise) {}

  float update(float measurement) {
    p_ += q_;
    const float k = p_ / (p_ + r_);
    x_ += k * (measurement - x_);
    p_ *= (1.0f - k);
    return x_;
  }

private:
  float q_;
  float r_;
  float x_ = 0.0f;
  float p_ = 1.0f;
};
