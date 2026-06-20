#pragma once

namespace mergen_estimation {

struct EulerAngles {
  double roll_deg = 0.0;
  double pitch_deg = 0.0;
  double yaw_deg = 0.0;
};

struct Quaternion {
  double w = 1.0;
  double x = 0.0;
  double y = 0.0;
  double z = 0.0;
};

class QuaternionEstimator {
public:
  static EulerAngles toEulerDegrees(const Quaternion &q);
};

}  // namespace mergen_estimation
