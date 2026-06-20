#include "mergen_estimation/quaternion_estimator.hpp"

#include <algorithm>
#include <cmath>

namespace mergen_estimation {

EulerAngles QuaternionEstimator::toEulerDegrees(const Quaternion &q) {
  constexpr double rad_to_deg = 57.29577951308232;

  const double sinr_cosp = 2.0 * (q.w * q.x + q.y * q.z);
  const double cosr_cosp = 1.0 - 2.0 * (q.x * q.x + q.y * q.y);
  const double roll = std::atan2(sinr_cosp, cosr_cosp);

  const double sinp = 2.0 * (q.w * q.y - q.z * q.x);
  const double pitch = std::asin(std::clamp(sinp, -1.0, 1.0));

  const double siny_cosp = 2.0 * (q.w * q.z + q.x * q.y);
  const double cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z);
  const double yaw = std::atan2(siny_cosp, cosy_cosp);

  return {roll * rad_to_deg, pitch * rad_to_deg, yaw * rad_to_deg};
}

}  // namespace mergen_estimation
