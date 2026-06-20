#pragma once

class PidController {
public:
  PidController(float kp, float ki, float kd, float min_output, float max_output)
      : kp_(kp), ki_(ki), kd_(kd), min_output_(min_output), max_output_(max_output) {}

  float update(float target, float measurement, float dt_sec) {
    if (dt_sec <= 0.0f) {
      return 0.0f;
    }
    const float error = target - measurement;
    integral_ += error * dt_sec;
    const float derivative = has_previous_ ? (error - previous_error_) / dt_sec : 0.0f;
    previous_error_ = error;
    has_previous_ = true;
    float output = kp_ * error + ki_ * integral_ + kd_ * derivative;
    if (output > max_output_) output = max_output_;
    if (output < min_output_) output = min_output_;
    return output;
  }

private:
  float kp_;
  float ki_;
  float kd_;
  float min_output_;
  float max_output_;
  float integral_ = 0.0f;
  float previous_error_ = 0.0f;
  bool has_previous_ = false;
};
