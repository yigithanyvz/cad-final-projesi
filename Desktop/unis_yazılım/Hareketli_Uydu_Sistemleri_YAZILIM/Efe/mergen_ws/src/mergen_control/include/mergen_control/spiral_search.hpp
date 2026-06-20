#pragma once

namespace mergen_control {

struct SpiralOffset {
  double azimuth_deg = 0.0;
  double elevation_deg = 0.0;
};

class SpiralSearch {
public:
  SpiralSearch(double radial_speed_deg_s, double angular_speed_rad_s, double max_radius_deg);
  SpiralOffset update(double elapsed_sec) const;

private:
  double radial_speed_deg_s_;
  double angular_speed_rad_s_;
  double max_radius_deg_;
};

}  // namespace mergen_control
