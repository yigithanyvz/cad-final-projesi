#include "mergen_control/qpd_tracker.hpp"

#include <cmath>

namespace mergen_control {

QpdTracker::QpdTracker(double detection_threshold) : detection_threshold_(detection_threshold) {}

QpdError QpdTracker::calculate(double a, double b, double c, double d) const {
  const double total = a + b + c + d;
  if (std::abs(total) < detection_threshold_) {
    return {0.0, 0.0, false};
  }

  // QPD denklemleri rapordaki boresight sapmasini normalize hata vektorune indirger.
  const double error_x = ((a + d) - (b + c)) / total;
  const double error_y = ((a + b) - (c + d)) / total;
  return {error_x, error_y, true};
}

}  // namespace mergen_control
