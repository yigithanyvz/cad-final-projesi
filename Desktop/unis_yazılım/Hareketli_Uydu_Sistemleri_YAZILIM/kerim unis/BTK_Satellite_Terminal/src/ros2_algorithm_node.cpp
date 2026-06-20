#include "PIDController.h"
#include "SensorFusion.h"
#include "StabilizationController.h"
#include "CameraObjectDetector.h"
#include "LaserTracker.h"
#include "types.h"
#include "config.h"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <memory>

#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/imu.hpp>
#include <sensor_msgs/msg/nav_sat_fix.hpp>
#include <std_msgs/msg/float32_multi_array.hpp>

using namespace std::chrono_literals;

class SatelliteTrackerRos2Node final : public rclcpp::Node
{
public:
  SatelliteTrackerRos2Node()
  : Node("satellite_tracker_algorithm")
  {
    gps_.position = {
      declare_parameter<double>("default_lat_deg", 39.9208),
      declare_parameter<double>("default_lon_deg", 32.8541),
      declare_parameter<double>("default_alt_m", 900.0)};
    gps_.hdop = 1.0f;
    gps_.fix_valid = true;

    ekf_.init({});

    imu_sub_ = create_subscription<sensor_msgs::msg::Imu>(
      "imu", rclcpp::SensorDataQoS(),
      [this](const sensor_msgs::msg::Imu::SharedPtr msg) { onImu(*msg); });

    gps_sub_ = create_subscription<sensor_msgs::msg::NavSatFix>(
      "gps/fix", 10,
      [this](const sensor_msgs::msg::NavSatFix::SharedPtr msg) { onGps(*msg); });

    encoder_sub_ = create_subscription<std_msgs::msg::Float32MultiArray>(
      "encoder", 10,
      [this](const std_msgs::msg::Float32MultiArray::SharedPtr msg) { onEncoder(*msg); });

    target_sub_ = create_subscription<std_msgs::msg::Float32MultiArray>(
      "target_azel", 10,
      [this](const std_msgs::msg::Float32MultiArray::SharedPtr msg) { onTargetAzEl(*msg); });

    qpd_sub_ = create_subscription<std_msgs::msg::Float32MultiArray>(
      "qpd", 10,
      [this](const std_msgs::msg::Float32MultiArray::SharedPtr msg) { onQpd(*msg); });

    camera_sub_ = create_subscription<std_msgs::msg::Float32MultiArray>(
      "camera_detection", 10,
      [this](const std_msgs::msg::Float32MultiArray::SharedPtr msg) { onCameraDetection(*msg); });

    target_pub_ = create_publisher<std_msgs::msg::Float32MultiArray>("target", 10);
    motor_pub_ = create_publisher<std_msgs::msg::Float32MultiArray>("motor_cmd", 10);
    telemetry_pub_ = create_publisher<std_msgs::msg::Float32MultiArray>("telemetry", 10);

    timer_ = create_wall_timer(
      std::chrono::milliseconds(MAIN_LOOP_PERIOD_MS),
      std::bind(&SatelliteTrackerRos2Node::update, this));

    RCLCPP_INFO(get_logger(), "Satellite tracker algorithms are running as a ROS 2 node.");
  }

private:
  static uint32_t stampMs(const rclcpp::Time & stamp)
  {
    return static_cast<uint32_t>(stamp.nanoseconds() / 1000000LL);
  }

  static float directionToFloat(MotorDir dir)
  {
    return static_cast<float>(static_cast<uint8_t>(dir));
  }

  void onImu(const sensor_msgs::msg::Imu & msg)
  {
    imu_raw_.accel_ms2 = {
      static_cast<float>(msg.linear_acceleration.x),
      static_cast<float>(msg.linear_acceleration.y),
      static_cast<float>(msg.linear_acceleration.z)};
    imu_raw_.gyro_rads = {
      static_cast<float>(msg.angular_velocity.x),
      static_cast<float>(msg.angular_velocity.y),
      static_cast<float>(msg.angular_velocity.z)};
    imu_raw_.timestamp_ms = stampMs(msg.header.stamp);
    imu_raw_.valid = true;
  }

  void onGps(const sensor_msgs::msg::NavSatFix & msg)
  {
    gps_.position = {msg.latitude, msg.longitude, msg.altitude};
    gps_.hdop = msg.position_covariance[0] > 0.0 ?
      static_cast<float>(std::sqrt(msg.position_covariance[0])) : 1.0f;
    gps_.timestamp_ms = stampMs(msg.header.stamp);
    gps_.fix_valid = msg.status.status >= sensor_msgs::msg::NavSatStatus::STATUS_FIX;
  }

  void onEncoder(const std_msgs::msg::Float32MultiArray & msg)
  {
    if (msg.data.size() < 2) {
      return;
    }

    encoder_.az_deg = msg.data[0];
    encoder_.el_deg = msg.data[1];
    if (msg.data.size() >= 4) {
      encoder_.az_speed_dps = msg.data[2];
      encoder_.el_speed_dps = msg.data[3];
    }
    encoder_.timestamp_ms = nowMs();
    encoder_.valid = true;
  }

  void onTargetAzEl(const std_msgs::msg::Float32MultiArray & msg)
  {
    if (msg.data.size() < 2) {
      return;
    }

    sat_azel_.az_deg = msg.data[0];
    sat_azel_.el_deg = msg.data[1];
    sat_azel_.range_km = msg.data.size() >= 3 ? msg.data[2] : 0.0f;
    target_.az_setpoint_deg = sat_azel_.az_deg;
    target_.el_setpoint_deg = sat_azel_.el_deg;
    target_.satellite_azel = sat_azel_;
    target_.satellite_above_horizon = sat_azel_.el_deg > 0.0f;
  }

  void onQpd(const std_msgs::msg::Float32MultiArray & msg)
  {
    if (msg.data.size() < 4) {
      qpd_.valid = false;
      return;
    }

    qpd_.x_norm = msg.data[0];
    qpd_.y_norm = msg.data[1];
    qpd_.total_signal = msg.data[2];
    qpd_.confidence = msg.data[3];
    qpd_.timestamp_ms = nowMs();
    qpd_.valid = true;
  }

  void onCameraDetection(const std_msgs::msg::Float32MultiArray & msg)
  {
    if (msg.data.size() < 6) {
      camera_detection_.detected = false;
      return;
    }

    camera_detection_.center_x_px = msg.data[0];
    camera_detection_.center_y_px = msg.data[1];
    camera_detection_.width_px = msg.data[2];
    camera_detection_.height_px = msg.data[3];
    camera_detection_.confidence = msg.data[4];
    camera_detection_.detected = msg.data[5] > 0.5f;
  }

  uint32_t nowMs() const
  {
    return static_cast<uint32_t>(now().nanoseconds() / 1000000LL);
  }

  void update()
  {
    const auto now_ms = nowMs();
    float dt = MAIN_LOOP_PERIOD_MS * 0.001f;
    if (last_update_ms_ != 0) {
      dt = std::clamp((now_ms - last_update_ms_) * 0.001f, 0.001f, 0.1f);
    }
    last_update_ms_ = now_ms;

    if (imu_raw_.valid) {
      ekf_.predict(imu_raw_.gyro_rads, dt);
      ekf_.update(imu_raw_.accel_ms2);
      orientation_ = ekf_.getOrientation();

      const auto stab_input =
        StabilizationController::fromSensors(orientation_, imu_raw_, dt, true);
      stab_out_ = stabilizer_.update(stab_input);
    }

    AntennaTarget base_target{};
    base_target.az_setpoint_deg = sat_azel_.az_deg;
    base_target.el_setpoint_deg = sat_azel_.el_deg;
    base_target.satellite_azel = sat_azel_;
    base_target.satellite_above_horizon = sat_azel_.el_deg > 0.0f;

    if (qpd_.valid && qpd_.confidence >= QPD_LOCK_THRESHOLD) {
      laser_spot_ = LaserTracker::spotFromQpd(qpd_);
    } else {
      laser_spot_ = camera_detector_.update(camera_detection_, now_ms);
    }

    target_ = laser_tracker_.applyCorrection(base_target, laser_spot_, dt, fine_track_);
    ctrl_out_ = controller_.update(target_, encoder_, dt, false, false, false, false);

    publishTarget();
    publishMotorCommand();
    publishTelemetry(now_ms);
  }

  void publishTarget()
  {
    std_msgs::msg::Float32MultiArray msg;
    msg.data = {
      target_.az_setpoint_deg,
      target_.el_setpoint_deg,
      sat_azel_.az_deg,
      sat_azel_.el_deg,
      sat_azel_.range_km,
      target_.satellite_above_horizon ? 1.0f : 0.0f};
    target_pub_->publish(msg);
  }

  void publishMotorCommand()
  {
    std_msgs::msg::Float32MultiArray msg;
    msg.data = {
      directionToFloat(ctrl_out_.az_cmd.direction),
      ctrl_out_.az_cmd.duty_pct,
      ctrl_out_.az_cmd.speed_dps,
      directionToFloat(ctrl_out_.el_cmd.direction),
      ctrl_out_.el_cmd.duty_pct,
      ctrl_out_.el_cmd.speed_dps,
      directionToFloat(stab_out_.roll_motor_cmd.direction),
      stab_out_.roll_motor_cmd.duty_pct,
      stab_out_.x_actuator_mm,
      directionToFloat(stab_out_.pitch_motor_cmd.direction),
      stab_out_.pitch_motor_cmd.duty_pct,
      stab_out_.y_actuator_mm,
      ctrl_out_.az_error_deg,
      ctrl_out_.el_error_deg};
    motor_pub_->publish(msg);
  }

  void publishTelemetry(uint32_t now_ms)
  {
    std_msgs::msg::Float32MultiArray msg;
    msg.data = {
      static_cast<float>(now_ms),
      gps_.fix_valid ? 1.0f : 0.0f,
      static_cast<float>(gps_.position.lat_deg),
      static_cast<float>(gps_.position.lon_deg),
      static_cast<float>(gps_.position.alt_m),
      orientation_.roll_deg,
      orientation_.pitch_deg,
      orientation_.yaw_deg,
      encoder_.az_deg,
      encoder_.el_deg,
      target_.az_setpoint_deg,
      target_.el_setpoint_deg,
      ctrl_out_.az_error_deg,
      ctrl_out_.el_error_deg,
      stab_out_.residual_error_deg,
      stab_out_.stable ? 1.0f : 0.0f,
      fine_track_.az_error_deg,
      fine_track_.el_error_deg,
      fine_track_.locked ? 1.0f : 0.0f,
      static_cast<float>(ctrl_out_.safety_flags)};
    telemetry_pub_->publish(msg);
  }

  uint32_t last_update_ms_{0};

  IMURawData imu_raw_{};
  GPSData gps_{};
  EncoderData encoder_{};
  Orientation orientation_{};
  AzEl sat_azel_{};
  AntennaTarget target_{};
  CameraObjectDetection camera_detection_{};
  QPDData qpd_{};
  LaserSpotData laser_spot_{};
  LaserTrackingCorrection fine_track_{};
  AntennaController::ControlOutput ctrl_out_{};
  StabilizationOutput stab_out_{};

  ExtendedKalmanFilter ekf_;
  AntennaController controller_;
  StabilizationController stabilizer_;
  CameraObjectDetector camera_detector_;
  LaserTracker laser_tracker_;

  rclcpp::Subscription<sensor_msgs::msg::Imu>::SharedPtr imu_sub_;
  rclcpp::Subscription<sensor_msgs::msg::NavSatFix>::SharedPtr gps_sub_;
  rclcpp::Subscription<std_msgs::msg::Float32MultiArray>::SharedPtr encoder_sub_;
  rclcpp::Subscription<std_msgs::msg::Float32MultiArray>::SharedPtr target_sub_;
  rclcpp::Subscription<std_msgs::msg::Float32MultiArray>::SharedPtr qpd_sub_;
  rclcpp::Subscription<std_msgs::msg::Float32MultiArray>::SharedPtr camera_sub_;

  rclcpp::Publisher<std_msgs::msg::Float32MultiArray>::SharedPtr target_pub_;
  rclcpp::Publisher<std_msgs::msg::Float32MultiArray>::SharedPtr motor_pub_;
  rclcpp::Publisher<std_msgs::msg::Float32MultiArray>::SharedPtr telemetry_pub_;
  rclcpp::TimerBase::SharedPtr timer_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<SatelliteTrackerRos2Node>());
  rclcpp::shutdown();
  return 0;
}
