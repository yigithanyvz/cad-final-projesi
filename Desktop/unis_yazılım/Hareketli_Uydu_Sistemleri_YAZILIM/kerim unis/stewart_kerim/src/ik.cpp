#include <cmath>
#include <memory>

#include <Eigen/Core>
#include <geometry_msgs/msg/twist.hpp>
#include <rclcpp/rclcpp.hpp>
#include <std_msgs/msg/float32_multi_array.hpp>

class IK : public rclcpp::Node
{
public:
  IK()
  : Node("ik"), height_(2.0)
  {
    b_ << -0.101, 0.8, 0.25, 1,
           0.101, 0.8, 0.25, 1,
           0.743, -0.313, 0.25, 1,
           0.642, -0.487, 0.25, 1,
          -0.643, -0.486, 0.25, 1,
          -0.744, -0.311, 0.25, 1;

    p_ << -0.642, 0.487, -0.05, 1,
           0.642, 0.487, -0.05, 1,
           0.743, 0.313, -0.05, 1,
           0.101, -0.8, -0.05, 1,
          -0.101, -0.8, -0.05, 1,
          -0.743, 0.313, -0.05, 1;

    position_msg_.data.resize(6, 0.0f);
    publisher_ = create_publisher<std_msgs::msg::Float32MultiArray>(
      "/stewart/position_cmd", 10);
    subscription_ = create_subscription<geometry_msgs::msg::Twist>(
      "/stewart/platform_twist",
      10,
      std::bind(&IK::callback, this, std::placeholders::_1));
  }

private:
  void callback(const geometry_msgs::msg::Twist::SharedPtr msg)
  {
    const float x = msg->linear.x;
    const float y = msg->linear.y;
    const float z = msg->linear.z;
    const float roll = msg->angular.x;
    const float pitch = msg->angular.y;
    const float yaw = msg->angular.z;

    Eigen::Matrix<float, 4, 4> transform =
      transformationMatrix(x, y, z + height_, roll, pitch, yaw);

    for (std::size_t i = 0; i < 6; ++i) {
      Eigen::Matrix<float, 4, 1> length =
        transform * p_.row(i).transpose() - b_.row(i).transpose();
      position_msg_.data[i] =
        std::sqrt(std::pow(length(0), 2) + std::pow(length(1), 2) + std::pow(length(2), 2)) -
        height_;
    }

    publisher_->publish(position_msg_);
  }

  Eigen::Matrix<float, 4, 4> transformationMatrix(
    float x, float y, float z, float roll, float pitch, float yaw)
  {
    Eigen::Matrix<float, 4, 4> transform;
    transform << std::cos(yaw) * std::cos(pitch),
      -std::sin(yaw) * std::cos(roll) + std::cos(yaw) * std::sin(pitch) * std::sin(roll),
      std::sin(yaw) * std::sin(roll) + std::cos(yaw) * std::sin(pitch) * std::cos(roll), x,
      std::sin(yaw) * std::cos(pitch),
      std::cos(yaw) * std::cos(roll) + std::sin(yaw) * std::sin(pitch) * std::sin(roll),
      -std::cos(yaw) * std::sin(roll) + std::sin(yaw) * std::sin(pitch) * std::cos(roll), y,
      -std::sin(pitch), std::cos(pitch) * std::sin(roll), std::cos(pitch) * std::cos(yaw), z,
      0, 0, 0, 1;
    return transform;
  }

  float height_;
  Eigen::Matrix<float, 6, 4> b_;
  Eigen::Matrix<float, 6, 4> p_;
  std_msgs::msg::Float32MultiArray position_msg_;
  rclcpp::Publisher<std_msgs::msg::Float32MultiArray>::SharedPtr publisher_;
  rclcpp::Subscription<geometry_msgs::msg::Twist>::SharedPtr subscription_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<IK>());
  rclcpp::shutdown();
  return 0;
}
