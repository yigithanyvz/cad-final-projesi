#include "kalman_filter.hpp"
#include "pid_controller.hpp"

struct MotorOutput {
  float azimuth_pwm;
  float elevation_pwm;
  float stabilizer_x_pwm;
  float stabilizer_y_pwm;
};

MotorOutput update_control_loop(float target_az, float target_el, float measured_az, float measured_el,
                                float raw_roll, float raw_pitch, float dt_sec) {
  static KalmanFilter1D roll_filter(0.01f, 0.25f);
  static KalmanFilter1D pitch_filter(0.01f, 0.25f);
  static PidController az_pid(2.0f, 0.02f, 0.15f, -1.0f, 1.0f);
  static PidController el_pid(2.2f, 0.02f, 0.16f, -1.0f, 1.0f);
  static PidController roll_pid(1.6f, 0.01f, 0.10f, -1.0f, 1.0f);
  static PidController pitch_pid(1.6f, 0.01f, 0.10f, -1.0f, 1.0f);

  const float roll = roll_filter.update(raw_roll);
  const float pitch = pitch_filter.update(raw_pitch);

  return {
      az_pid.update(target_az, measured_az, dt_sec),
      el_pid.update(target_el, measured_el, dt_sec),
      roll_pid.update(0.0f, roll, dt_sec),
      pitch_pid.update(0.0f, pitch, dt_sec),
  };
}
