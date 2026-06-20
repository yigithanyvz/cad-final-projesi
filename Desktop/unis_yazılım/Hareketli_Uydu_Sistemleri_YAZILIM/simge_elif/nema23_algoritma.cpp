#include <algorithm>
#include <cmath>
#include <iostream>
#include <random>

#ifdef _WIN32
#include <windows.h>
#endif

constexpr float PI           = 3.14159265f;
constexpr float DT           = 0.01f;

// ─── GERCEK DONANIM PARAMETRELERI ──────────────────────────
// AS5600 Manyetik Encoder: 12-bit (4096 counts/rev)
// full tur 360°, her count = 0.0879°
constexpr float ENCODER_CPR        = 4096.0f;
constexpr float ENCODER_DEG_PER_CNT = 360.0f / ENCODER_CPR;  // 0.0879°

// Azimuth: NEMA 23 Step Motor + DRV8825 (1/32 microstepping)
// Elevasyon: NEMA 17 Step Motor + DRV8825 (1/32 microstepping)
// Iki motor da 1.8° step angle, 200 steps/rev kabul edilir.
constexpr float AZ_MOTOR_FULL_STEP     = 1.8f;
constexpr float AZ_MOTOR_MICROSTEPS    = 32.0f;
constexpr float AZ_MOTOR_STEPS_PER_REV = 200.0f * AZ_MOTOR_MICROSTEPS; // 6400
constexpr float AZ_MOTOR_DEG_PER_STEP  = AZ_MOTOR_FULL_STEP / AZ_MOTOR_MICROSTEPS; // 0.05625°

constexpr float EL_MOTOR_FULL_STEP     = 1.8f;
constexpr float EL_MOTOR_MICROSTEPS    = 32.0f;
constexpr float EL_MOTOR_STEPS_PER_REV = 200.0f * EL_MOTOR_MICROSTEPS; // 6400
constexpr float EL_MOTOR_DEG_PER_STEP  = EL_MOTOR_FULL_STEP / EL_MOTOR_MICROSTEPS; // 0.05625°

// Eksen limitleri (AS5600 0-360°, Slipring ile sinirsiz donus)
// Elevasyon mekanik limit (NEMA 17 dogrudan surus)
constexpr float AZ_LIMIT_MIN = 0.0f;
constexpr float AZ_LIMIT_MAX = 360.0f;
constexpr float EL_LIMIT_MIN = 0.0f;
constexpr float EL_LIMIT_MAX = 90.0f;

// NEMA 23 azimuth, NEMA 17 elevasyon max hiz (yuk altinda, DRV8825 ile 12-24V)
// Azimuth rediktor ile ~60°/s, elevasyon rediktor ile ~30°/s
constexpr float AZ_MAX_SPEED = 60.0f;
constexpr float EL_MAX_SPEED = 30.0f;

// PID katsayilari
constexpr float AZ_KP = 8.0f, AZ_KI = 0.0f, AZ_KD = 0.0f;
constexpr float EL_KP = 10.0f, EL_KI = 0.0f, EL_KD = 0.0f;
// Deadband AS5600 cozunurlugune gore (0.0879° -> 0.1°)
constexpr float PID_DEADBAND = ENCODER_DEG_PER_CNT;
constexpr float AZ_OUT_MAX  = 60.0f;
constexpr float EL_OUT_MAX  = 30.0f;

// Kalman filtresi parametreleri
constexpr float KALMAN_PROCESS = 0.02f;
constexpr float KALMAN_MEASURE = 0.35f;

// ─── 1D Kalman ──────────────────────────────────────────────
class Kalman1D {
    float q_, r_, x_, p_;
public:
    Kalman1D(float process, float measure, float init = 0.0f)
        : q_(process), r_(measure), x_(init), p_(1.0f) {}

    float update(float measurement) {
        p_ += q_;
        float gain = p_ / (p_ + r_);
        x_ += gain * (measurement - x_);
        p_ *= (1.0f - gain);
        return x_;
    }

    void reset(float init = 0.0f) { x_ = init; p_ = 1.0f; }
};

// ─── PID ─────────────────────────────────────────────────────
class PidController {
    float kp_, ki_, kd_, deadband_, max_out_;
    float integral_ = 0.0f;
    float prev_error_ = 0.0f;
public:
    PidController(float kp, float ki, float kd, float deadband, float max_out)
        : kp_(kp), ki_(ki), kd_(kd), deadband_(deadband), max_out_(max_out) {}

    float compute(float target, float measured, float dt) {
        if (dt <= 0.0f || dt > 0.5f) return 0.0f;
        float error = target - measured;
        if (std::abs(error) < deadband_) {
            integral_   = 0.0f;
            prev_error_ = 0.0f;
            return 0.0f;
        }
        integral_ = std::clamp(integral_ + error * dt, -max_out_ / ki_, max_out_ / ki_);
        float derivative = (error - prev_error_) / dt;
        prev_error_ = error;
        float output = kp_ * error + ki_ * integral_ + kd_ * derivative;
        return std::clamp(output, -max_out_, max_out_);
    }

    void reset() { integral_ = 0.0f; prev_error_ = 0.0f; }
};

// ─── HUSKYLENS Kamera ──────────────────────────────────────
// Gravity HUSKYLENS: 320x240 cozunurluk, 120° lens
// Dahili nesne tespiti (renk/etiket/yuz takibi)
// UART/I2C uzerinden bounding box (x, y, w, h) gonderir
// Takip icin etkin FOV ±10° (nesne merkezde tutulur)
struct CameraDetection {
    float pixel_error_x;
    float pixel_error_y;
    float confidence;
    bool  detected;
};

// Simulasyon icin gercek hedef konumu surekli degisir.
// Kontrol hedefi bu degerden degil, HUSKYLENS olcumunden uretilir.
struct TargetState {
    float true_az, true_el, t;
};

TargetState simulateTrueTarget(float t) {
    // Gercek hedef: yalnizca kamera olcumunu simule etmek icin kullanilir.
    float az = 120.0f + 2.0f * std::sin(0.3f * t);
    float el = 30.0f + 1.0f * std::cos(0.2f * t);
    return {az, el, t};
}

// HUSKYLENS etkin takip parametreleri
// Genis acili lens (120°) ama takip modunda ±10° etkin FOV kullanilir
constexpr float CAMERA_FOV_DEG = 10.0f;
constexpr float CAMERA_RES_PX  = 320.0f;
constexpr float PX_PER_DEG     = CAMERA_RES_PX / (2.0f * CAMERA_FOV_DEG);

CameraDetection simulateCameraDetection(float antenna_az, float antenna_el,
                                        float target_az, float target_el,
                                        std::mt19937& rng, float t) {
    float dx = target_az - antenna_az;
    float dy = target_el - antenna_el;
    if (dx > 180.0f) dx -= 360.0f;
    if (dx < -180.0f) dx += 360.0f;

    bool in_fov_x = std::abs(dx) < CAMERA_FOV_DEG;
    bool in_fov_y = std::abs(dy) < CAMERA_FOV_DEG;

    if (!in_fov_x || !in_fov_y) {
        return {0.0f, 0.0f, 0.0f, false};
    }

    float px_err_x = dx * PX_PER_DEG;
    float px_err_y = dy * PX_PER_DEG;

    // HUSKYLENS: ±1 pixel (dahili goruntu isleme kararli)
    std::normal_distribution<float> noise(0.0f, 1.0f);

    // HUSKYLENS tespit güveni (merkezden uzaklaştıkça düşer)
    float dist_from_center = std::sqrt(dx * dx + dy * dy) / CAMERA_FOV_DEG;
    float confidence = std::clamp(1.0f - dist_from_center * 0.2f, 0.5f, 1.0f);

    return {px_err_x + noise(rng), px_err_y + noise(rng), confidence, true};
}

// ─── Step Motor Eksen Simulasyonu ─────────────────────────
// Step motor simulasyonu: pozisyon + hiz
// Gerçek sistemde DRV8825'e step/dir sinyalleri gonderilir
class MotorAxis {
    float pos_;
    float max_speed_;
    float limit_min_, limit_max_;
public:
    MotorAxis(float init, float max_speed, float min_l, float max_l)
        : pos_(init), max_speed_(max_speed), limit_min_(min_l), limit_max_(max_l) {}

    void applySpeed(float speed_dps, float dt) {
        speed_dps = std::clamp(speed_dps, -max_speed_, max_speed_);
        pos_ += speed_dps * dt;
        pos_ = std::clamp(pos_, limit_min_, limit_max_);
    }

    float position() const { return pos_; }
    void reset(float pos = 0.0f) { pos_ = pos; }
};

// ─── Ana Program ────────────────────────────────────────────
int main() {
#ifdef _WIN32
    SetConsoleOutputCP(65001);
#endif

    std::cout << "--- KAMERA TAKIP SIMULASYONU v2 (AZ NEMA 23 / EL NEMA 17) ---\n";
    std::cout << "Teensy 4.1 | HUSKYLENS | AZ:NEMA 23+DRV8825 | EL:NEMA 17+DRV8825 | AS5600\n\n";

    std::random_device rd;
    std::mt19937 rng(rd());

    Kalman1D     kamera_x_filter(KALMAN_PROCESS, KALMAN_MEASURE);
    Kalman1D     kamera_y_filter(KALMAN_PROCESS, KALMAN_MEASURE);
    PidController az_pid(AZ_KP, AZ_KI, AZ_KD, PID_DEADBAND, AZ_OUT_MAX);
    PidController el_pid(EL_KP, EL_KI, EL_KD, PID_DEADBAND, EL_OUT_MAX);
    MotorAxis     az_motor(119.0f, AZ_MAX_SPEED, AZ_LIMIT_MIN, AZ_LIMIT_MAX);
    MotorAxis     el_motor(29.0f,  EL_MAX_SPEED, EL_LIMIT_MIN, EL_LIMIT_MAX);

    constexpr int STEPS = 500;
    int lock_count = 0;
    int first_lock_step = -1;
    float max_boresight = 0.0f;

    std::cout << "Zaman(s)  HedefAz  HedefEl  KameraAz  KameraEl  "
              << "PxErr_x  PxErr_y  Guven  Filt_x Filt_y  "
              << "Hz_(/s)  El_(/s)  Kilit  Hata(°)\n";
    std::cout << "--------------------------------------------------------------------"
              << "------------------------\n";

    for (int i = 0; i < STEPS; ++i) {
        float t = i * DT;

        TargetState target = simulateTrueTarget(t);

        CameraDetection det = simulateCameraDetection(
            az_motor.position(), el_motor.position(),
            target.true_az, target.true_el, rng, t);

        float filtered_px_x = det.detected ? kamera_x_filter.update(det.pixel_error_x) : 0.0f;
        float filtered_px_y = det.detected ? kamera_y_filter.update(det.pixel_error_y) : 0.0f;

        float angle_offset_x = filtered_px_x / PX_PER_DEG * det.confidence;
        float angle_offset_y = filtered_px_y / PX_PER_DEG * det.confidence;
        float compensated_az = az_motor.position() + angle_offset_x;
        float compensated_el = el_motor.position() + angle_offset_y;
        if (compensated_az < AZ_LIMIT_MIN) compensated_az += 360.0f;
        if (compensated_az > AZ_LIMIT_MAX) compensated_az -= 360.0f;
        compensated_el = std::clamp(compensated_el, EL_LIMIT_MIN, EL_LIMIT_MAX);

        float az_speed = az_pid.compute(compensated_az, az_motor.position(), DT);
        float el_speed = el_pid.compute(compensated_el, el_motor.position(), DT);

        az_motor.applySpeed(az_speed, DT);
        el_motor.applySpeed(el_speed, DT);

        float az_error = compensated_az - az_motor.position();
        float el_error = compensated_el - el_motor.position();
        if (az_error > 180.0f) az_error -= 360.0f;
        if (az_error < -180.0f) az_error += 360.0f;
        float boresight = std::sqrt(az_error * az_error + el_error * el_error);
        max_boresight = std::max(max_boresight, boresight);
        bool locked = (boresight < 0.2f);
        if (locked) {
            ++lock_count;
            if (first_lock_step < 0) first_lock_step = i;
        }

        if (i % 10 == 0) {
            std::cout << t << "    "
                      << compensated_az << "  " << compensated_el << "   "
                      << az_motor.position() << "     " << el_motor.position() << "    "
                      << det.pixel_error_x << "   " << det.pixel_error_y << "   "
                      << det.confidence << " "
                      << filtered_px_x << " " << filtered_px_y << " "
                      << az_speed << "  " << el_speed << " "
                      << (locked ? "KILITLI" : "ARAMA ") << " "
                      << boresight << "\n";
        }
    }

    std::cout << "\n--- SIMULASYON SONUCU ---\n";
    std::cout << "Toplam sure: " << STEPS * DT << " saniye\n";
    std::cout << "Kontrol hedefi: HUSKYLENS acisal hata + mevcut motor konumu\n";
    if (first_lock_step >= 0)
        std::cout << "Ilk kilitlenme: " << first_lock_step * DT << " saniye\n";
    else
        std::cout << "Kilitlenme yok\n";
    std::cout << "Kilit orani: " << (100.0f * lock_count / STEPS) << "%\n";
    std::cout << "Maks boresight: " << max_boresight << "\n";

    std::cout << "\n--- DONANIM PARAMETRELERI ---\n";
    std::cout << "Encoder   : AS5600 (12-bit, " << (int)ENCODER_CPR << " CPR, "
              << ENCODER_DEG_PER_CNT << " deg/count)\n";
    std::cout << "Az Motor  : NEMA 23 + DRV8825 (1/" << (int)AZ_MOTOR_MICROSTEPS
              << " microstep, " << (int)AZ_MOTOR_STEPS_PER_REV << " steps/rev, "
              << AZ_MOTOR_DEG_PER_STEP << " deg/microstep)\n";
    std::cout << "El Motor  : NEMA 17 + DRV8825 (1/" << (int)EL_MOTOR_MICROSTEPS
              << " microstep, " << (int)EL_MOTOR_STEPS_PER_REV << " steps/rev, "
              << EL_MOTOR_DEG_PER_STEP << " deg/microstep)\n";
    std::cout << "Kamera    : HUSKYLENS (FOV=" << CAMERA_FOV_DEG
              << ", " << (int)CAMERA_RES_PX << "px)\n";
    std::cout << "Kontrol   : Teensy 4.1 (100 Hz)\n";
    std::cout << "Deadband  : " << PID_DEADBAND << "\n";

    std::cout << "\nCikmak icin Enter'a basin...\n";
    std::cin.get();
    return 0;
}
