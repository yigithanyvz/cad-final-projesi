#pragma once

#include "mergen_control/pid_controller.hpp"

namespace mergen_control {

struct StabilizerCommand {
  double x_mm = 0.0;
  double y_mm = 0.0;
};

class StabilizationController {
public:
  StabilizationController(PidController roll_pid, PidController pitch_pid, double mm_per_degree);
  StabilizerCommand update(double roll_deg, double pitch_deg, double dt_sec);

private:
  PidController roll_pid_;
  PidController pitch_pid_;
  double mm_per_degree_;
};

}  // namespace mergen_control
