#include "mergen_estimation/kalman_filter.hpp"
#include "mergen_estimation/quaternion_estimator.hpp"

#include "mergen_interfaces/msg/imu_filtered.hpp"
#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/imu.hpp"

class ImuFilterNode final : public rclcpp::Node {
public:
  ImuFilterNode()
      : Node("mergen_imu_filter_node"), roll_filter_(0.01, 0.25), pitch_filter_(0.01, 0.25), yaw_filter_(0.01, 0.50) {
    imu_sub_ = create_subscription<sensor_msgs::msg::Imu>(
        "/imu/data", 20, [this](const sensor_msgs::msg::Imu::SharedPtr msg) { handleImu(*msg); });
    filtered_pub_ = create_publisher<mergen_interfaces::msg::ImuFiltered>("/mergen/imu_filtered", 20);
  }

private:
  void handleImu(const sensor_msgs::msg::Imu &msg) {
    const mergen_estimation::Quaternion q{msg.orientation.w, msg.orientation.x, msg.orientation.y, msg.orientation.z};
    const auto euler = mergen_estimation::QuaternionEstimator::toEulerDegrees(q);

    mergen_interfaces::msg::ImuFiltered out;
    out.stamp_sec = now().seconds();
    out.roll_deg = roll_filter_.update(euler.roll_deg);
    out.pitch_deg = pitch_filter_.update(euler.pitch_deg);
    out.yaw_deg = yaw_filter_.update(euler.yaw_deg);
    out.roll_rate_dps = msg.angular_velocity.x;
    out.pitch_rate_dps = msg.angular_velocity.y;
    out.yaw_rate_dps = msg.angular_velocity.z;
    filtered_pub_->publish(out);
  }

  mergen_estimation::KalmanFilter1D roll_filter_;
  mergen_estimation::KalmanFilter1D pitch_filter_;
  mergen_estimation::KalmanFilter1D yaw_filter_;
  rclcpp::Subscription<sensor_msgs::msg::Imu>::SharedPtr imu_sub_;
  rclcpp::Publisher<mergen_interfaces::msg::ImuFiltered>::SharedPtr filtered_pub_;
};

int main(int argc, char **argv) {
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<ImuFilterNode>());
  rclcpp::shutdown();
  return 0;
}
