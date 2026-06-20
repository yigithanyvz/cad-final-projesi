#include "mergen_control/pid_controller.hpp"

namespace mergen_control {

PidController::PidController(double kp, double ki, double kd, double min_output, double max_output)
    : kp_(kp), ki_(ki), kd_(kd), min_output_(min_output), max_output_(max_output) {}

double PidController::update(double target, double measurement, double dt_sec) {
  if (dt_sec <= 0.0) {
    return 0.0;
  }

  const double error = target - measurement;
  integral_ += error * dt_sec;
  const double derivative = has_previous_error_ ? (error - previous_error_) / dt_sec : 0.0;

  previous_error_ = error;
  has_previous_error_ = true;

  const double output = kp_ * error + ki_ * integral_ + kd_ * derivative;
  return std::clamp(output, min_output_, max_output_);
}

void PidController::reset() {
  integral_ = 0.0;
  previous_error_ = 0.0;
  has_previous_error_ = false;
}

}  // namespace mergen_control
