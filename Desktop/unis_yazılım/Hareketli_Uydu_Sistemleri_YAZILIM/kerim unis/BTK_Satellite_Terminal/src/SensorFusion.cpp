#include "SensorFusion.h"

#include "config.h"

#include <cmath>

namespace mat {

Mat7x7 identity() {
    Mat7x7 m{};
    for (int i = 0; i < 7; ++i) m[i][i] = 1.0f;
    return m;
}

Mat7x7 add(const Mat7x7& A, const Mat7x7& B) {
    Mat7x7 C{};
    for (int i = 0; i < 7; ++i) {
        for (int j = 0; j < 7; ++j) {
            C[i][j] = A[i][j] + B[i][j];
        }
    }
    return C;
}

Mat7x7 mul(const Mat7x7& A, const Mat7x7& B) {
    Mat7x7 C{};
    for (int i = 0; i < 7; ++i) {
        for (int k = 0; k < 7; ++k) {
            if (A[i][k] == 0.0f) continue;
            for (int j = 0; j < 7; ++j) {
                C[i][j] += A[i][k] * B[k][j];
            }
        }
    }
    return C;
}

Mat7x7 transpose(const Mat7x7& A) {
    Mat7x7 T{};
    for (int i = 0; i < 7; ++i) {
        for (int j = 0; j < 7; ++j) {
            T[j][i] = A[i][j];
        }
    }
    return T;
}

void normalize_q(Vec7& x) {
    const float n = std::sqrt(
        x[0] * x[0] + x[1] * x[1] + x[2] * x[2] + x[3] * x[3]);
    if (n < 1e-9f) return;
    x[0] /= n;
    x[1] /= n;
    x[2] /= n;
    x[3] /= n;
}

float Mat3x3::det() const {
    return a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1])
         - a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0])
         + a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0]);
}

Mat3x3 Mat3x3::inv() const {
    const float d = det();
    if (std::fabs(d) < 1e-12f) return {};
    const float inv_d = 1.0f / d;
    Mat3x3 r{};
    r.a[0][0] = (a[1][1] * a[2][2] - a[1][2] * a[2][1]) * inv_d;
    r.a[0][1] = (a[0][2] * a[2][1] - a[0][1] * a[2][2]) * inv_d;
    r.a[0][2] = (a[0][1] * a[1][2] - a[0][2] * a[1][1]) * inv_d;
    r.a[1][0] = (a[1][2] * a[2][0] - a[1][0] * a[2][2]) * inv_d;
    r.a[1][1] = (a[0][0] * a[2][2] - a[0][2] * a[2][0]) * inv_d;
    r.a[1][2] = (a[0][2] * a[1][0] - a[0][0] * a[1][2]) * inv_d;
    r.a[2][0] = (a[1][0] * a[2][1] - a[1][1] * a[2][0]) * inv_d;
    r.a[2][1] = (a[0][1] * a[2][0] - a[0][0] * a[2][1]) * inv_d;
    r.a[2][2] = (a[0][0] * a[1][1] - a[0][1] * a[1][0]) * inv_d;
    return r;
}

} // namespace mat

void ExtendedKalmanFilter::init(const Vec3& bias_gyro) {
    x_[0] = 1.0f;
    x_[1] = 0.0f;
    x_[2] = 0.0f;
    x_[3] = 0.0f;
    x_[4] = bias_gyro.x;
    x_[5] = bias_gyro.y;
    x_[6] = bias_gyro.z;

    P_ = mat::identity();
    for (int i = 0; i < 4; ++i) P_[i][i] = 0.01f;
    for (int i = 4; i < 7; ++i) P_[i][i] = 0.001f;

    Q_ = {};
    const float q_q = GYRO_NOISE_SIGMA * GYRO_NOISE_SIGMA * (1.0f / IMU_SAMPLE_RATE_HZ);
    const float q_b = GYRO_BIAS_SIGMA * GYRO_BIAS_SIGMA * (1.0f / IMU_SAMPLE_RATE_HZ);
    for (int i = 0; i < 4; ++i) Q_[i][i] = q_q;
    for (int i = 4; i < 7; ++i) Q_[i][i] = q_b;

    const float r_a = ACCEL_NOISE_SIGMA * ACCEL_NOISE_SIGMA;
    R_[0][0] = r_a;
    R_[1][1] = r_a;
    R_[2][2] = r_a;

    initialized_ = true;
}

void ExtendedKalmanFilter::predict(const Vec3& gyro_raw, float dt) {
    if (!initialized_ || dt <= 0.0f || dt > 0.1f) return;

    const float wx = gyro_raw.x - x_[4];
    const float wy = gyro_raw.y - x_[5];
    const float wz = gyro_raw.z - x_[6];

    const float q0 = x_[0];
    const float q1 = x_[1];
    const float q2 = x_[2];
    const float q3 = x_[3];
    const float half_dt = 0.5f * dt;

    x_[0] = q0 + half_dt * (-wx * q1 - wy * q2 - wz * q3);
    x_[1] = q1 + half_dt * ( wx * q0 + wz * q2 - wy * q3);
    x_[2] = q2 + half_dt * ( wy * q0 - wz * q1 + wx * q3);
    x_[3] = q3 + half_dt * ( wz * q0 + wy * q1 - wx * q2);
    mat::normalize_q(x_);

    Mat7x7 F = mat::identity();
    F[0][0] = 1.0f;         F[0][1] = -half_dt * wx; F[0][2] = -half_dt * wy; F[0][3] = -half_dt * wz;
    F[1][0] = half_dt * wx; F[1][1] = 1.0f;          F[1][2] =  half_dt * wz; F[1][3] = -half_dt * wy;
    F[2][0] = half_dt * wy; F[2][1] = -half_dt * wz; F[2][2] = 1.0f;          F[2][3] =  half_dt * wx;
    F[3][0] = half_dt * wz; F[3][1] =  half_dt * wy; F[3][2] = -half_dt * wx; F[3][3] = 1.0f;
    F[0][4] =  half_dt * q1; F[0][5] =  half_dt * q2; F[0][6] =  half_dt * q3;
    F[1][4] = -half_dt * q0; F[1][5] =  half_dt * q3; F[1][6] = -half_dt * q2;
    F[2][4] = -half_dt * q3; F[2][5] = -half_dt * q0; F[2][6] =  half_dt * q1;
    F[3][4] =  half_dt * q2; F[3][5] = -half_dt * q1; F[3][6] = -half_dt * q0;

    const Mat7x7 Ft = mat::transpose(F);
    P_ = mat::add(mat::mul(mat::mul(F, P_), Ft), Q_);
}

void ExtendedKalmanFilter::update(const Vec3& accel_raw) {
    if (!initialized_) return;

    const float accel_mag = accel_raw.norm();
    if (std::fabs(accel_mag - GRAVITY_MS2) > 3.0f) return;

    const float q0 = x_[0];
    const float q1 = x_[1];
    const float q2 = x_[2];
    const float q3 = x_[3];

    const float hx = 2.0f * (q1 * q3 - q0 * q2) * GRAVITY_MS2;
    const float hy = 2.0f * (q0 * q1 + q2 * q3) * GRAVITY_MS2;
    const float hz = (q0 * q0 - q1 * q1 - q2 * q2 + q3 * q3) * GRAVITY_MS2;

    const float innov[3] = {
        accel_raw.x - hx,
        accel_raw.y - hy,
        accel_raw.z - hz
    };

    float H[3][7] = {};
    H[0][0] = -2.0f * q2 * GRAVITY_MS2; H[0][1] =  2.0f * q3 * GRAVITY_MS2;
    H[0][2] = -2.0f * q0 * GRAVITY_MS2; H[0][3] =  2.0f * q1 * GRAVITY_MS2;
    H[1][0] =  2.0f * q1 * GRAVITY_MS2; H[1][1] =  2.0f * q0 * GRAVITY_MS2;
    H[1][2] =  2.0f * q3 * GRAVITY_MS2; H[1][3] =  2.0f * q2 * GRAVITY_MS2;
    H[2][0] =  2.0f * q0 * GRAVITY_MS2; H[2][1] = -2.0f * q1 * GRAVITY_MS2;
    H[2][2] = -2.0f * q2 * GRAVITY_MS2; H[2][3] =  2.0f * q3 * GRAVITY_MS2;

    mat::Mat3x3 S{};
    for (int i = 0; i < 3; ++i) {
        for (int j = 0; j < 3; ++j) {
            float sum = 0.0f;
            for (int k = 0; k < 7; ++k) {
                float ph_kj = 0.0f;
                for (int l = 0; l < 7; ++l) {
                    ph_kj += P_[k][l] * H[j][l];
                }
                sum += H[i][k] * ph_kj;
            }
            S.a[i][j] = sum + R_[i][j];
        }
    }

    const mat::Mat3x3 S_inv = S.inv();
    float K[7][3] = {};
    for (int i = 0; i < 7; ++i) {
        for (int j = 0; j < 3; ++j) {
            for (int l = 0; l < 3; ++l) {
                float ph = 0.0f;
                for (int k = 0; k < 7; ++k) {
                    ph += P_[i][k] * H[l][k];
                }
                K[i][j] += ph * S_inv.a[l][j];
            }
        }
    }

    for (int i = 0; i < 7; ++i) {
        for (int j = 0; j < 3; ++j) {
            x_[i] += K[i][j] * innov[j];
        }
    }
    mat::normalize_q(x_);

    Mat7x7 KH{};
    for (int i = 0; i < 7; ++i) {
        for (int j = 0; j < 7; ++j) {
            for (int k = 0; k < 3; ++k) {
                KH[i][j] += K[i][k] * H[k][j];
            }
        }
    }

    Mat7x7 IKH = mat::identity();
    for (int i = 0; i < 7; ++i) {
        for (int j = 0; j < 7; ++j) {
            IKH[i][j] -= KH[i][j];
        }
    }
    P_ = mat::mul(IKH, P_);
}

Orientation ExtendedKalmanFilter::getOrientation() const {
    Orientation o{};
    o.q = Quaternion{x_[0], x_[1], x_[2], x_[3]};
    o.gyro_bias = Vec3{x_[4], x_[5], x_[6]};

    const float q0 = x_[0];
    const float q1 = x_[1];
    const float q2 = x_[2];
    const float q3 = x_[3];
    constexpr float kRadToDeg = 57.2957795131f;

    const float sinr_cosp = 2.0f * (q0 * q1 + q2 * q3);
    const float cosr_cosp = 1.0f - 2.0f * (q1 * q1 + q2 * q2);
    o.roll_deg = std::atan2(sinr_cosp, cosr_cosp) * kRadToDeg;

    const float sinp = 2.0f * (q0 * q2 - q3 * q1);
    if (std::fabs(sinp) >= 1.0f) {
        o.pitch_deg = std::copysign(90.0f, sinp);
    } else {
        o.pitch_deg = std::asin(sinp) * kRadToDeg;
    }

    const float siny_cosp = 2.0f * (q0 * q3 + q1 * q2);
    const float cosy_cosp = 1.0f - 2.0f * (q2 * q2 + q3 * q3);
    o.yaw_deg = std::atan2(siny_cosp, cosy_cosp) * kRadToDeg;

    float trace = 0.0f;
    for (int i = 0; i < 4; ++i) trace += P_[i][i];
    o.converged = trace < 0.005f;

    return o;
}
