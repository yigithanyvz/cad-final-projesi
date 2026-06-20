#include "mergen_control/stabilization_controller.hpp"

namespace mergen_control {

StabilizationController::StabilizationController(PidController roll_pid, PidController pitch_pid, double mm_per_degree)
    : roll_pid_(roll_pid), pitch_pid_(pitch_pid), mm_per_degree_(mm_per_degree) {}

StabilizerCommand StabilizationController::update(double roll_deg, double pitch_deg, double dt_sec) {
  // Hedef roll/pitch sifirdir; cikis, mama kabi X/Y itki mekanizmasinin lineer komutudur.
  const double x = roll_pid_.update(0.0, roll_deg, dt_sec) * mm_per_degree_;
  const double y = pitch_pid_.update(0.0, pitch_deg, dt_sec) * mm_per_degree_;
  return {x, y};
}

}  // namespace mergen_control
