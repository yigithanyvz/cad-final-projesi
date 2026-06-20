#include <algorithm>
#include <cmath>
#include <iostream>
#include <random>

#ifdef _WIN32
#include <windows.h>
#endif

constexpr float PI           = 3.14159265f;
constexpr float DT           = 0.01f;

constexpr float AZ_LIMIT_MIN = 0.0f;
constexpr float AZ_LIMIT_MAX = 360.0f;
constexpr float EL_LIMIT_MIN = 0.0f;
constexpr float EL_LIMIT_MAX = 90.0f;
constexpr float AZ_MAX_SPEED = 60.0f;
constexpr float EL_MAX_SPEED = 30.0f;

constexpr float AZ_KP = 8.0f, AZ_KI = 0.0f, AZ_KD = 0.0f;
constexpr float EL_KP = 10.0f, EL_KI = 0.0f, EL_KD = 0.0f;
constexpr float PID_DEADBAND = 0.1f;
constexpr float AZ_OUT_MAX  = 60.0f;
constexpr float EL_OUT_MAX  = 30.0f;

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

// ─── Kamera Görüntü İşleme Simülasyonu ─────────────────────
// Kameradan alinan görüntüde cismin merkezden sapmasini pixel olarak döndürür.
// Gerçek sistemde OpenCV vb. ile cisim tespiti ve bounding box merkezi hesaplanir.
struct CameraDetection {
    float pixel_error_x;  // yatay sapma (pixel, pozitif=sag)
    float pixel_error_y;  // dikey sapma (pixel, pozitif=asagi)
    float confidence;     // tespit güveni (0-1)
    bool  detected;       // cisim görüntüde var mi
};

// Gerçek cisim konumu (zamanla hareket eder)
struct TargetState {
    float true_az, true_el, t;
};

TargetState simulateTrueTarget(float t) {
    float az = 120.0f + 2.0f * std::sin(0.3f * t);
    float el = 30.0f + 1.0f * std::cos(0.2f * t);
    return {az, el, t};
}

// Kameranin görüş alani (FOV) ve çözünürlük
constexpr float CAMERA_FOV_DEG = 5.0f;      // ±5° görüş alani
constexpr float CAMERA_RES_PX  = 640.0f;     // yatay çözünürlük (pixel)
constexpr float PX_PER_DEG     = CAMERA_RES_PX / (2.0f * CAMERA_FOV_DEG); // pixel/°

// Kameradan cisim tespiti simülasyonu:
// Anten yönü ile cisim arasindaki açi farkini pixel hatasina çevirir.
CameraDetection simulateCameraDetection(float antenna_az, float antenna_el,
                                        float target_az, float target_el,
                                        std::mt19937& rng, float t) {
    // Anten (kamera) ile cisim arasindaki açi farki
    float dx = target_az - antenna_az;
    float dy = target_el - antenna_el;
    if (dx > 180.0f) dx -= 360.0f;
    if (dx < -180.0f) dx += 360.0f;

    // Görüş alani içinde mi?
    bool in_fov_x = std::abs(dx) < CAMERA_FOV_DEG;
    bool in_fov_y = std::abs(dy) < CAMERA_FOV_DEG;

    if (!in_fov_x || !in_fov_y) {
        // Cisim görüş alani disinda -> tespit yok
        return {0.0f, 0.0f, 0.0f, false};
    }

    // Açiyi pixel hatasina çevir
    float px_err_x = dx * PX_PER_DEG;
    float px_err_y = dy * PX_PER_DEG;

    // Gürültü ekle (kamera sensoru + titreşim)
    std::normal_distribution<float> noise(0.0f, 3.0f);  // ±3 pixel gürültü

    // Tespit güveni: merkezden uzaklaştikça düşer, kenarlarda bulaniklik
    float dist_from_center = std::sqrt(dx * dx + dy * dy) / CAMERA_FOV_DEG;
    float confidence = std::clamp(1.0f - dist_from_center * 0.3f, 0.3f, 1.0f);
    confidence *= (0.9f + 0.1f * std::sin(0.5f * t));

    return {px_err_x + noise(rng), px_err_y + noise(rng), confidence, true};
}

// ─── Motor ──────────────────────────────────────────────────
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

    std::cout << "--- KAMERA TAKIP SIMULASYONU (Goruntu + Kalman + PID + Deadband) ---\n\n";

    std::random_device rd;
    std::mt19937 rng(rd());

    Kalman1D     kamera_x_filter(KALMAN_PROCESS, KALMAN_MEASURE);
    Kalman1D     kamera_y_filter(KALMAN_PROCESS, KALMAN_MEASURE);
    PidController az_pid(AZ_KP, AZ_KI, AZ_KD, PID_DEADBAND, AZ_OUT_MAX);
    PidController el_pid(EL_KP, EL_KI, EL_KD, PID_DEADBAND, EL_OUT_MAX);
    MotorAxis     az_motor(119.0f, AZ_MAX_SPEED, AZ_LIMIT_MIN, AZ_LIMIT_MAX);
    MotorAxis     el_motor(29.0f,  EL_MAX_SPEED, EL_LIMIT_MIN, EL_LIMIT_MAX);

    constexpr float TARGET_AZ = 120.0f;
    constexpr float TARGET_EL = 30.0f;

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

        // 1. Cisim konumunu güncelle
        TargetState target = simulateTrueTarget(t);

        // 2. Kamera ile cisim tespiti
        CameraDetection det = simulateCameraDetection(
            az_motor.position(), el_motor.position(),
            target.true_az, target.true_el, rng, t);

        // 3. Kalman ile pixel gürültüsünü temizle
        float filtered_px_x = det.detected ? kamera_x_filter.update(det.pixel_error_x) : 0.0f;
        float filtered_px_y = det.detected ? kamera_y_filter.update(det.pixel_error_y) : 0.0f;

        // 4. Pixel hatasini açi hatasina çevir ve hedefe offset uygula
        float angle_offset_x = filtered_px_x / PX_PER_DEG * det.confidence;
        float angle_offset_y = filtered_px_y / PX_PER_DEG * det.confidence;
        float compensated_az = TARGET_AZ + angle_offset_x;
        float compensated_el = TARGET_EL + angle_offset_y;

        // 5. PID kontrol (encoder geri beslemesi ile)
        float az_speed = az_pid.compute(compensated_az, az_motor.position(), DT);
        float el_speed = el_pid.compute(compensated_el, el_motor.position(), DT);

        // 6. Motorlari hareket ettir
        az_motor.applySpeed(az_speed, DT);
        el_motor.applySpeed(el_speed, DT);

        // 7. Metrikler
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
    std::cout << "Hedef: Az=120.0, El=30.0\n";
    if (first_lock_step >= 0)
        std::cout << "Ilk kilitlenme: " << first_lock_step * DT << " saniye\n";
    else
        std::cout << "Kilitlenme yok\n";
    std::cout << "Kilit orani: " << (100.0f * lock_count / STEPS) << "%\n";
    std::cout << "Maks boresight: " << max_boresight << "\n";
    std::cout << "Kamera FOV: " << CAMERA_FOV_DEG << " cozunurluk: " << (int)CAMERA_RES_PX << "px\n";
    std::cout << "Deadband: " << PID_DEADBAND << "\n";

    std::cout << "\nCikmak icin Enter'a basin...\n";
    std::cin.get();
    return 0;
}
