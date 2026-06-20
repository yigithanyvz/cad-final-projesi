#include <algorithm>
#include <cmath>
#include <memory>

#include <geometry_msgs/msg/twist.hpp>
#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/joy.hpp>

class Controller : public rclcpp::Node
{
public:
  Controller()
  : Node("ps4_controller")
  {
    publisher_ = create_publisher<geometry_msgs::msg::Twist>("/stewart/platform_twist", 10);
    subscription_ = create_subscription<sensor_msgs::msg::Joy>(
      "/joy",
      10,
      std::bind(&Controller::callback, this, std::placeholders::_1));
  }

private:
  void callback(const sensor_msgs::msg::Joy::SharedPtr msg)
  {
    if (msg->axes.size() < 5 || msg->buttons.size() < 8) {
      return;
    }

    twist_msg_.linear.x = -msg->axes[0] / 2.0;
    twist_msg_.linear.y = msg->axes[1] / 2.0;
    twist_msg_.angular.x = -msg->axes[4] / 5.0;
    twist_msg_.angular.y = -msg->axes[3] / 5.0;

    if (msg->buttons[7]) {
      twist_msg_.linear.z = std::min(twist_msg_.linear.z + 0.01, 1.0);
    } else if (msg->buttons[6]) {
      twist_msg_.linear.z = std::max(twist_msg_.linear.z - 0.01, 0.0);
    }

    if (msg->buttons[5]) {
      twist_msg_.angular.z = std::min(twist_msg_.angular.z + 0.01, M_PI / 2.0);
    } else if (msg->buttons[4]) {
      twist_msg_.angular.z = std::max(twist_msg_.angular.z - 0.01, -M_PI / 2.0);
    }

    publisher_->publish(twist_msg_);
  }

  geometry_msgs::msg::Twist twist_msg_;
  rclcpp::Publisher<geometry_msgs::msg::Twist>::SharedPtr publisher_;
  rclcpp::Subscription<sensor_msgs::msg::Joy>::SharedPtr subscription_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<Controller>());
  rclcpp::shutdown();
  return 0;
}
