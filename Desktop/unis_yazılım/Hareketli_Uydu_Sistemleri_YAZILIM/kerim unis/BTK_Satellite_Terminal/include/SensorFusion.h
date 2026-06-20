#pragma once

#include "types.h"

#include <array>

using Mat7x7 = std::array<std::array<float, 7>, 7>;
using Vec7 = std::array<float, 7>;

namespace mat {

Mat7x7 identity();
Mat7x7 add(const Mat7x7& A, const Mat7x7& B);
Mat7x7 mul(const Mat7x7& A, const Mat7x7& B);
Mat7x7 transpose(const Mat7x7& A);
void normalize_q(Vec7& x);

struct Mat3x3 {
    float a[3][3]{};

    float det() const;
    Mat3x3 inv() const;
};

} // namespace mat

class ExtendedKalmanFilter {
public:
    void init(const Vec3& bias_gyro);
    void predict(const Vec3& gyro_raw, float dt);
    void update(const Vec3& accel_raw);
    Orientation getOrientation() const;

private:
    Vec7 x_{};
    Mat7x7 P_{};
    Mat7x7 Q_{};
    float R_[3][3] = {};
    bool initialized_ = false;
};
