#include "mergen_control/pid_controller.hpp"
#include "mergen_control/stabilization_controller.hpp"

#include <chrono>
#include <memory>

#include "mergen_interfaces/msg/imu_filtered.hpp"
#include "mergen_interfaces/msg/motor_command.hpp"
#include "mergen_interfaces/msg/motor_state.hpp"
#include "mergen_interfaces/msg/target_angles.hpp"
#include "rclcpp/rclcpp.hpp"

using namespace std::chrono_literals;

class ControlNode final : public rclcpp::Node {
public:
  ControlNode()
      : Node("mergen_control_node"),
        az_pid_(2.0, 0.02, 0.15, -1.0, 1.0),
        el_pid_(2.2, 0.02, 0.16, -1.0, 1.0),
        stabilizer_(mergen_control::PidController(1.6, 0.01, 0.10, -1.0, 1.0),
                    mergen_control::PidController(1.6, 0.01, 0.10, -1.0, 1.0),
                    4.0) {
    imu_sub_ = create_subscription<mergen_interfaces::msg::ImuFiltered>(
        "/mergen/imu_filtered", 10,
        [this](const mergen_interfaces::msg::ImuFiltered::SharedPtr msg) { latest_imu_ = *msg; });
    motor_sub_ = create_subscription<mergen_interfaces::msg::MotorState>(
        "/mergen/motor_state", 10,
        [this](const mergen_interfaces::msg::MotorState::SharedPtr msg) { latest_motor_ = *msg; });
    target_sub_ = create_subscription<mergen_interfaces::msg::TargetAngles>(
        "/mergen/target_angles", 10,
        [this](const mergen_interfaces::msg::TargetAngles::SharedPtr msg) { latest_target_ = *msg; });
    command_pub_ = create_publisher<mergen_interfaces::msg::MotorCommand>("/mergen/motor_command", 10);
    timer_ = create_wall_timer(10ms, [this]() { update(); });
  }

private:
  void update() {
    const double dt = 0.01;
    const auto stab = stabilizer_.update(latest_imu_.roll_deg, latest_imu_.pitch_deg, dt);

    mergen_interfaces::msg::MotorCommand cmd;
    cmd.stamp_sec = now().seconds();
    cmd.azimuth_deg = latest_target_.azimuth_deg;
    cmd.elevation_deg = latest_target_.elevation_deg;
    cmd.stabilizer_x_mm = stab.x_mm;
    cmd.stabilizer_y_mm = stab.y_mm;
    cmd.azimuth_pwm = az_pid_.update(latest_target_.azimuth_deg, latest_motor_.azimuth_deg, dt);
    cmd.elevation_pwm = el_pid_.update(latest_target_.elevation_deg, latest_motor_.elevation_deg, dt);
    cmd.stabilizer_x_pwm = stab.x_mm;
    cmd.stabilizer_y_pwm = stab.y_mm;
    command_pub_->publish(cmd);
  }

  mergen_control::PidController az_pid_;
  mergen_control::PidController el_pid_;
  mergen_control::StabilizationController stabilizer_;
  mergen_interfaces::msg::ImuFiltered latest_imu_;
  mergen_interfaces::msg::MotorState latest_motor_;
  mergen_interfaces::msg::TargetAngles latest_target_;
  rclcpp::Subscription<mergen_interfaces::msg::ImuFiltered>::SharedPtr imu_sub_;
  rclcpp::Subscription<mergen_interfaces::msg::MotorState>::SharedPtr motor_sub_;
  rclcpp::Subscription<mergen_interfaces::msg::TargetAngles>::SharedPtr target_sub_;
  rclcpp::Publisher<mergen_interfaces::msg::MotorCommand>::SharedPtr command_pub_;
  rclcpp::TimerBase::SharedPtr timer_;
};

int main(int argc, char **argv) {
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<ControlNode>());
  rclcpp::shutdown();
  return 0;
}
