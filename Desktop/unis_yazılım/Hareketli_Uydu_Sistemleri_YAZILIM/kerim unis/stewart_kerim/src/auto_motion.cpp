#include <chrono>
#include <cmath>
#include <cstdint>
#include <memory>
#include <vector>

#include <geometry_msgs/msg/twist.hpp>
#include <rclcpp/rclcpp.hpp>

using namespace std::chrono_literals;

static constexpr uint32_t RATE_HZ = 50;
static constexpr double DT = 1.0 / RATE_HZ;
static constexpr double DEG8  = 8.0 * M_PI / 180.0;
static constexpr double TRANSLATION = 0.02;
static constexpr double Z_LIFT = 0.5;

struct Move {
  double roll, pitch, yaw;
  double x, y, z;
};

static const std::vector<Move> SEQUENCE = {
  // User's sequence: GÜNEY DOĞU BATI GÜNEY KUZEY DOĞU GÜNEY KUZEY BATI DOĞU BATI KUZEY BATI GÜNEY DOĞU
  // With initial NORTH as described ("ilk 5 saniye hareket etmesin ardindan 8 derece kuzey yonunde yatsin")
  // 1.  North  (front/Y+ down = roll -8 deg, translate Y+)
  { .roll = -DEG8, .pitch = 0.0, .yaw = 0.0, .x = 0.0,    .y =  TRANSLATION, .z = 0.0 },
  // 2.  South
  { .roll =  DEG8, .pitch = 0.0, .yaw = 0.0, .x = 0.0,    .y = -TRANSLATION, .z = 0.0 },
  // 3.  East  (right/X+ down = pitch +8 deg, translate X+)
  { .roll = 0.0,   .pitch = DEG8, .yaw = 0.0, .x =  TRANSLATION, .y = 0.0,    .z = 0.0 },
  // 4.  West
  { .roll = 0.0,   .pitch =-DEG8, .yaw = 0.0, .x = -TRANSLATION, .y = 0.0,    .z = 0.0 },
  // 5.  South
  { .roll =  DEG8, .pitch = 0.0, .yaw = 0.0, .x = 0.0,    .y = -TRANSLATION, .z = 0.0 },
  // 6.  North
  { .roll = -DEG8, .pitch = 0.0, .yaw = 0.0, .x = 0.0,    .y =  TRANSLATION, .z = 0.0 },
  // 7.  East
  { .roll = 0.0,   .pitch = DEG8, .yaw = 0.0, .x =  TRANSLATION, .y = 0.0,    .z = 0.0 },
  // 8.  South
  { .roll =  DEG8, .pitch = 0.0, .yaw = 0.0, .x = 0.0,    .y = -TRANSLATION, .z = 0.0 },
  // 9.  North
  { .roll = -DEG8, .pitch = 0.0, .yaw = 0.0, .x = 0.0,    .y =  TRANSLATION, .z = 0.0 },
  // 10. West
  { .roll = 0.0,   .pitch =-DEG8, .yaw = 0.0, .x = -TRANSLATION, .y = 0.0,    .z = 0.0 },
  // 11. East
  { .roll = 0.0,   .pitch = DEG8, .yaw = 0.0, .x =  TRANSLATION, .y = 0.0,    .z = 0.0 },
  // 12. West
  { .roll = 0.0,   .pitch =-DEG8, .yaw = 0.0, .x = -TRANSLATION, .y = 0.0,    .z = 0.0 },
  // 13. North
  { .roll = -DEG8, .pitch = 0.0, .yaw = 0.0, .x = 0.0,    .y =  TRANSLATION, .z = 0.0 },
  // 14. West
  { .roll = 0.0,   .pitch =-DEG8, .yaw = 0.0, .x = -TRANSLATION, .y = 0.0,    .z = 0.0 },
  // 15. South
  { .roll =  DEG8, .pitch = 0.0, .yaw = 0.0, .x = 0.0,    .y = -TRANSLATION, .z = 0.0 },
  // 16. East
  { .roll = 0.0,   .pitch = DEG8, .yaw = 0.0, .x =  TRANSLATION, .y = 0.0,    .z = 0.0 },
};

class AutoMotion : public rclcpp::Node
{
public:
  AutoMotion()
  : Node("auto_motion"), move_idx_(0), time_(0.0)
  {
    publisher_ = create_publisher<geometry_msgs::msg::Twist>("/stewart/platform_twist", 10);
    timer_ = create_wall_timer(std::chrono::duration<double>(DT),
                               std::bind(&AutoMotion::tick, this));
    RCLCPP_INFO(get_logger(), "Smooth seq: %zu moves, 10s each (5s idle + 5s sine pulse)", SEQUENCE.size());
  }

private:
  static constexpr double CYCLE = 10.0;   // 10 seconds per move

  void tick()
  {
    // Current time within the 10s cycle
    double t = std::fmod(time_, CYCLE);        // [0, 10)
    double s = 1.0;  // scale factor

    if (t < 5.0) {
      // First 5 seconds: neutral
      s = 0.0;
    } else {
      // Next 5 seconds: smooth sine pulse 0→1→0
      double u = (t - 5.0) / 5.0;               // [0, 1) over the 5s move window
      s = std::sin(M_PI * u);
      s = s * s;                                 // sin² = smooth 0→1→0
    }

    const Move &m = SEQUENCE[move_idx_];
    geometry_msgs::msg::Twist msg;
    msg.angular.x = m.roll * s;
    msg.angular.y = m.pitch * s;
    msg.angular.z = m.yaw * s;
    msg.linear.x  = m.x * s;
    msg.linear.y  = m.y * s;
    msg.linear.z  = Z_LIFT;
    publisher_->publish(msg);

    time_ += DT;

    // Advance to next move when cycle completes
    size_t new_idx = static_cast<size_t>(time_ / CYCLE) % SEQUENCE.size();
    if (new_idx != move_idx_) {
      move_idx_ = new_idx;
      if (move_idx_ == 0) {
        RCLCPP_INFO(get_logger(), "Full sequence done, looping");
      }
    }
  }

  size_t move_idx_;
  double time_;
  rclcpp::Publisher<geometry_msgs::msg::Twist>::SharedPtr publisher_;
  rclcpp::TimerBase::SharedPtr timer_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<AutoMotion>());
  rclcpp::shutdown();
  return 0;
}
