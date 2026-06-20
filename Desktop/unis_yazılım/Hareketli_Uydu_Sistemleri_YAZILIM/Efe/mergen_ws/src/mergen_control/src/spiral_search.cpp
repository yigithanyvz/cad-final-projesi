#include "mergen_control/spiral_search.hpp"

#include <algorithm>
#include <cmath>

namespace mergen_control {

SpiralSearch::SpiralSearch(double radial_speed_deg_s, double angular_speed_rad_s, double max_radius_deg)
    : radial_speed_deg_s_(radial_speed_deg_s), angular_speed_rad_s_(angular_speed_rad_s), max_radius_deg_(max_radius_deg) {}

SpiralOffset SpiralSearch::update(double elapsed_sec) const {
  const double radius = std::min(max_radius_deg_, radial_speed_deg_s_ * elapsed_sec);
  const double angle = angular_speed_rad_s_ * elapsed_sec;
  return {radius * std::cos(angle), radius * std::sin(angle)};
}

}  // namespace mergen_control
