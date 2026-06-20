#include <algorithm>
#include <array>
#include <memory>
#include <string>
#include <thread>
#include <vector>

#include <gazebo/common/PID.hh>
#include <gazebo/gazebo.hh>
#include <gazebo/physics/physics.hh>
#include <rclcpp/rclcpp.hpp>
#include <std_msgs/msg/float32_multi_array.hpp>

namespace gazebo
{
class SDFJointController : public ModelPlugin
{
public:
  SDFJointController() = default;

  ~SDFJointController() override
  {
    if (executor_) {
      executor_->cancel();
    }
    if (ros_thread_.joinable()) {
      ros_thread_.join();
    }
  }

  void Load(physics::ModelPtr model, sdf::ElementPtr) override
  {
    model_ = model;

    const std::array<std::string, 6> joint_names = {
      "piston1_prismatic_joint",
      "piston2_prismatic_joint",
      "piston3_prismatic_joint",
      "piston4_prismatic_joint",
      "piston5_prismatic_joint",
      "piston6_prismatic_joint",
    };

    common::PID pid(1000.0, 0.1, 100.0);
    for (const auto & name : joint_names) {
      auto joint = model_->GetJoint(name);
      if (!joint) {
        gzerr << "Stewart joint_controller could not find joint [" << name << "]\n";
        continue;
      }

      joints_.push_back(joint);
      model_->GetJointController()->SetPositionPID(joint->GetScopedName(), pid);
    }

    if (joints_.size() != joint_names.size()) {
      gzerr << "Stewart joint_controller loaded only " << joints_.size()
            << " of " << joint_names.size() << " piston joints\n";
      return;
    }

    if (!rclcpp::ok()) {
      int argc = 0;
      char ** argv = nullptr;
      rclcpp::init(argc, argv);
    }

    node_ = std::make_shared<rclcpp::Node>("stewart_gazebo_joint_controller");
    subscription_ = node_->create_subscription<std_msgs::msg::Float32MultiArray>(
      "/" + model_->GetName() + "/position_cmd",
      rclcpp::QoS(10),
      std::bind(&SDFJointController::setPosition, this, std::placeholders::_1));

    executor_ = std::make_shared<rclcpp::executors::SingleThreadedExecutor>();
    executor_->add_node(node_);
    ros_thread_ = std::thread([this]() { executor_->spin(); });

    gzmsg << "Stewart joint_controller attached to model [" << model_->GetName()
          << "] and listening on /" << model_->GetName() << "/position_cmd\n";
  }

private:
  void setPosition(const std_msgs::msg::Float32MultiArray::SharedPtr msg)
  {
    const auto count = std::min(joints_.size(), msg->data.size());
    for (std::size_t i = 0; i < count; ++i) {
      model_->GetJointController()->SetPositionTarget(
        joints_[i]->GetScopedName(), msg->data[i]);
    }
  }

  physics::ModelPtr model_;
  std::vector<physics::JointPtr> joints_;

  rclcpp::Node::SharedPtr node_;
  rclcpp::Subscription<std_msgs::msg::Float32MultiArray>::SharedPtr subscription_;
  std::shared_ptr<rclcpp::executors::SingleThreadedExecutor> executor_;
  std::thread ros_thread_;
};

GZ_REGISTER_MODEL_PLUGIN(SDFJointController)
}  // namespace gazebo
