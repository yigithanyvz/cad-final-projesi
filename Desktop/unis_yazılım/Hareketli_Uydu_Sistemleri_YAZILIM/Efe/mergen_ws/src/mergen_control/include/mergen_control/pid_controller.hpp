#pragma once

#include <algorithm>

namespace mergen_control {

class PidController {
public:
  PidController(double kp, double ki, double kd, double min_output, double max_output);

  double update(double target, double measurement, double dt_sec);
  void reset();

private:
  double kp_;
  double ki_;
  double kd_;
  double min_output_;
  double max_output_;
  double integral_ = 0.0;
  double previous_error_ = 0.0;
  bool has_previous_error_ = false;
};

}  // namespace mergen_control
