#include <algorithm>
#include <chrono>
#include <cmath>
#include <iostream>
#include <random>
#include <thread>
#include <vector>

#ifdef _WIN32
#include <windows.h>
#endif

// ─── Sabitler ───────────────────────────────────────────────
constexpr float PI           = 3.14159265f;
constexpr float DT           = 0.01f;       // 100 Hz
constexpr float GRAVITY_MS2  = 9.80665f;

// Motor limitleri
constexpr float AZ_LIMIT_MIN = 0.0f;
constexpr float AZ_LIMIT_MAX = 360.0f;
constexpr float EL_LIMIT_MIN = 0.0f;
constexpr float EL_LIMIT_MAX = 90.0f;
constexpr float AZ_MAX_SPEED = 60.0f;       // °/s
constexpr float EL_MAX_SPEED = 30.0f;       // °/s

// PID (çıkış = motor hızı °/s)
constexpr float AZ_KP = 8.0f, AZ_KI = 0.0f, AZ_KD = 0.0f;
constexpr float EL_KP = 10.0f, EL_KI = 0.0f, EL_KD = 0.0f;
constexpr float PID_DEADBAND = 0.1f;          // °
constexpr float AZ_OUT_MAX  = 60.0f;          // °/s
constexpr float EL_OUT_MAX  = 30.0f;          // °/s

// Kalman
constexpr float KALMAN_PROCESS = 0.02f;
constexpr float KALMAN_MEASURE = 0.35f;

// ─── 1D Kalman Filtresi ─────────────────────────────────────
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

// ─── PID Kontrolcü ──────────────────────────────────────────
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

        // Ölü bant
        if (std::abs(error) < deadband_) {
            integral_    = 0.0f;
            prev_error_  = 0.0f;
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

// ─── Dört Bölgeli QPD Sensör Simülasyonu ────────────────────
struct QpdData { float a, b, c, d; };

struct QpdResult {
    float error_x;   // yatay hata
    float error_y;   // dikey hata
    float total;     // toplam sinyal gücü
    bool  detected;  // cisim algılandı mı
};

// QPD hatasını normalize et
QpdResult computeQpdError(float a, float b, float c, float d) {
    float total = a + b + c + d;
    if (std::abs(total) < 0.05f) return {0.0f, 0.0f, total, false};
    float ex = ((a + d) - (b + c)) / total;
    float ey = ((a + b) - (c + d)) / total;
    return {ex, ey, total, true};
}

// Gerçek hedef konumunu simüle eder (zamanla yavaşça hareket eden bir cisim)
struct TargetState {
    float true_az;   // gerçek azimut konumu
    float true_el;   // gerçek elevasyon konumu
    float t;         // simülasyon zamanı
};

TargetState simulateTrueTarget(float t) {
    // Cisim 120° azimut, 30° elevasyon civarında yavaşça salınır
    float az = 120.0f + 2.0f * std::sin(0.3f * t);
    float el = 30.0f + 1.0f * std::cos(0.2f * t);
    return {az, el, t};
}

// QPD okumasını hedef konumdan üret (anten nereyi gösteriyorsa)
QpdData simulateQpdReading(float antenna_az, float antenna_el,
                           float target_az, float target_el,
                           std::mt19937& rng) {
    // Anten boresight ile hedef arasındaki açı farkı (QPD görüş alanı içinde)
    float dx = target_az - antenna_az;
    float dy = target_el - antenna_el;
    if (dx > 180.0f) dx -= 360.0f;
    if (dx < -180.0f) dx += 360.0f;

    // QPD normalize çıkış: görüş alanı ±2°, dışında doygun
    float fov = 2.0f;
    float ex = std::clamp(dx / fov, -1.0f, 1.0f);
    float ey = std::clamp(dy / fov, -1.0f, 1.0f);

    std::normal_distribution<float> noise(0.0f, 0.02f);
    float base = 1.0f;
    return {
        base + ex + ey + noise(rng),
        base - ex + ey + noise(rng),
        base - ex - ey + noise(rng),
        base + ex - ey + noise(rng)
    };
}

// ─── Motor ve Encoder Simülasyonu ───────────────────────────
class MotorAxis {
    float pos_;          // encoder okuması (°)
    float max_speed_;    // max hız (°/s)
    float limit_min_, limit_max_;
public:
    MotorAxis(float init, float max_speed, float min_l, float max_l)
        : pos_(init), max_speed_(max_speed), limit_min_(min_l), limit_max_(max_l) {}

    // PID çıkışını (°/s) motor konumuna entegre et
    void applyPwm(float speed_dps, float dt) {
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

    std::cout << "--- LAZER TAKIP SIMULASYONU (QPD + Kalman + PID + Deadband) ---\n\n";

    // Rastgelelik
    std::random_device rd;
    std::mt19937 rng(rd());

    // Bileşenler
    Kalman1D     qpd_x_filter(KALMAN_PROCESS, KALMAN_MEASURE);
    Kalman1D     qpd_y_filter(KALMAN_PROCESS, KALMAN_MEASURE);
    PidController az_pid(AZ_KP, AZ_KI, AZ_KD, PID_DEADBAND, AZ_OUT_MAX);
    PidController el_pid(EL_KP, EL_KI, EL_KD, PID_DEADBAND, EL_OUT_MAX);
    MotorAxis     az_motor(119.0f, AZ_MAX_SPEED, AZ_LIMIT_MIN, AZ_LIMIT_MAX);
    MotorAxis     el_motor(29.0f,  EL_MAX_SPEED, EL_LIMIT_MIN, EL_LIMIT_MAX);

    // Hedef değerler (sabit referans, QPD düzeltmesi uygulanacak)
    const float target_az = 120.0f;
    const float target_el = 30.0f;

    constexpr int STEPS = 500;  // 5 saniye @100Hz
    int lock_count = 0;
    int first_lock_step = -1;
    float max_boresight = 0.0f;

    std::cout << "Zaman(s)  HedefAz  HedefEl  EncoderAz  EncoderEl  "
              << "QPD_x   QPD_y   Filt_x  Filt_y  PWMaz  PWMel  "
              << "Kilit  Hata(°)\n";
    std::cout << "--------------------------------------------------------------------"
              << "------------------\n";

    for (int i = 0; i < STEPS; ++i) {
        float t = i * DT;

        // 1. Lazer/QPD ile cisim algılama
        TargetState true_target = simulateTrueTarget(t);
        QpdData qpd_raw = simulateQpdReading(
            az_motor.position(), el_motor.position(),
            true_target.true_az, true_target.true_el, rng);

        // 2. QPD hatasını hesapla
        QpdResult qpd = computeQpdError(qpd_raw.a, qpd_raw.b, qpd_raw.c, qpd_raw.d);

        // 3. Kalman filtresi ile QPD gürültüsünü temizle
        float filtered_qpd_x = qpd.detected ? qpd_x_filter.update(qpd.error_x) : 0.0f;
        float filtered_qpd_y = qpd.detected ? qpd_y_filter.update(qpd.error_y) : 0.0f;

        // 4. Hata vektörünü hedef açıya offset olarak uygula (aktif takip)
        float compensated_az = target_az + filtered_qpd_x * 2.0f;
        float compensated_el = target_el + filtered_qpd_y * 2.0f;

        // 5. PID kontrol (encoder geri beslemesi ile)
        float az_pwm = az_pid.compute(compensated_az, az_motor.position(), DT);
        float el_pwm = el_pid.compute(compensated_el, el_motor.position(), DT);

        // 6. Motorlara PWM uygula
        az_motor.applyPwm(az_pwm, DT);
        el_motor.applyPwm(el_pwm, DT);

        // 7. Performans metrikleri
        float az_error = compensated_az - az_motor.position();
        float el_error = compensated_el - el_motor.position();
        if (az_error > 180.0f) az_error -= 360.0f;
        if (az_error < -180.0f) az_error += 360.0f;
        float boresight = std::sqrtf(az_error * az_error + el_error * el_error);
        max_boresight = std::max(max_boresight, boresight);
        bool locked = (boresight < 0.2f);
        if (locked) {
            ++lock_count;
            if (first_lock_step < 0) first_lock_step = i;
        }

        // 8. Canlı durum yazdır (her 10 adımda bir)
        if (i % 10 == 0) {
            std::cout << t << "     "
                      << compensated_az << "  " << compensated_el << "     "
                      << az_motor.position() << "        " << el_motor.position() << "      "
                      << qpd.error_x << "  " << qpd.error_y << "  "
                      << filtered_qpd_x << " " << filtered_qpd_y << " "
                      << az_pwm << "   " << el_pwm << "  "
                      << (locked ? "KILITLI" : "ARAMA ") << " "
                      << boresight << "\n";
        }
    }

    // ─── Özet ────────────────────────────────────────────────────
    std::cout << "\n--- SIMULASYON SONUCU ---\n";
    std::cout << "Toplam sure: " << STEPS * DT << " saniye\n";
    std::cout << "Hedef konum: Az=120.0°, El=30.0°\n";
    if (first_lock_step >= 0)
        std::cout << "Ilk kilitlenme: " << first_lock_step * DT << " saniye\n";
    else
        std::cout << "Kilitlenme yok\n";
    std::cout << "Kilit orani: " << (100.0f * lock_count / STEPS) << "%\n";
    std::cout << "Maksimum boresight hatasi: " << max_boresight << "°\n";
    std::cout << "Deadband esigi: " << PID_DEADBAND << "°\n";

    std::cout << "\nCikmak icin Enter'a basin...\n";
    std::cin.get();
    return 0;
}
