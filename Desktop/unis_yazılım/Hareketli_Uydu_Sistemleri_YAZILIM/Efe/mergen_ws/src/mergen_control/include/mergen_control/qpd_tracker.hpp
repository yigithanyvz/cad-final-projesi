#pragma once

namespace mergen_control {

struct QpdError {
  double x = 0.0;
  double y = 0.0;
  bool valid = false;
};

class QpdTracker {
public:
  explicit QpdTracker(double detection_threshold);
  QpdError calculate(double a, double b, double c, double d) const;

private:
  double detection_threshold_;
};

}  // namespace mergen_control
