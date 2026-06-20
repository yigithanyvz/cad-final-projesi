#include <algorithm>
#include <cmath>
#include <iostream>

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

// NEMA 17 Step Motor + DRV8825 (1/32 microstepping)
// 1.8° step angle, 200 steps/rev, 32 microsteps = 6400 adim/rev
constexpr float MOTOR_FULL_STEP    = 1.8f;
constexpr float MOTOR_MICROSTEPS   = 32.0f;
constexpr float MOTOR_STEPS_PER_REV = 200.0f * MOTOR_MICROSTEPS; // 6400
constexpr float MOTOR_DEG_PER_STEP = MOTOR_FULL_STEP / MOTOR_MICROSTEPS; // 0.05625°

// Eksen limitleri (AS5600 0-360°, Slipring ile sinirsiz donus)
// Elevasyon mekanik limit (NEMA 17 dogrudan surus)
constexpr float AZ_LIMIT_MIN = 0.0f;
constexpr float AZ_LIMIT_MAX = 360.0f;
constexpr float EL_LIMIT_MIN = 0.0f;
constexpr float EL_LIMIT_MAX = 90.0f;

// NEMA 17 max hiz (yuk altinda, DRV8825 ile 12-24V)
// 60 RPM ~ 360°/s azimuth, rediktor ile ~60°/s
// 30 RPM ~ 180°/s elevation, rediktor ile ~30°/s
constexpr float AZ_MAX_SPEED = 60.0f;
constexpr float EL_MAX_SPEED = 30.0f;

// PID katsayilari
constexpr float AZ_KP = 8.0f, AZ_KI = 0.0f, AZ_KD = 0.0f;
constexpr float EL_KP = 10.0f, EL_KI = 0.0f, EL_KD = 0.0f;
// Deadband AS5600 cozunurlugune gore (0.0879° -> 0.1°)
constexpr float PID_DEADBAND = ENCODER_DEG_PER_CNT;
constexpr float AZ_OUT_MAX  = 60.0f;
constexpr float EL_OUT_MAX  = 30.0f;
constexpr bool  ENABLE_STEP_LOG = false;
constexpr int   LOG_EVERY_STEPS = 50;

// Hedef kaybinda yeniden yakalama/tarama modu
constexpr float SEARCH_AZ_SPEED = 8.0f;
constexpr float SEARCH_EL_SPEED = 4.0f;
constexpr float SEARCH_EL_MIN   = 15.0f;
constexpr float SEARCH_EL_MAX   = 75.0f;
constexpr float BORESIGHT_LOCK_LIMIT_DEG = 0.2f;
constexpr float TRACK_SUCCESS_LIMIT_DEG  = 1.0f;

// Kalman filtresi parametreleri
constexpr float KALMAN_PROCESS = 0.02f;
constexpr float KALMAN_MEASURE = 0.35f;

// Lazer boresight gosterge guvenligi
// Teensy 4.1 pin 33 (MCLK2) transistor base hattini surer.
// Insan algilanirsa pin LOW kabul edilir; base akimi kesilir ve lazer kapanir.
constexpr int LASER_ENABLE_PIN = 33;

// ─── 1D Kalman ──────────────────────────────────────────────
class Kalman1D {
    float x_, gain_;
    bool is_initialized_ = false;
public:
    constexpr Kalman1D(float process, float measure, float init = 0.0f)
        : x_(init), gain_(steadyStateGain(process, measure)) {}

    float update(float measurement) {
        if (!is_initialized_) {
            x_ = measurement;
            is_initialized_ = true;
            return x_;
        }
        x_ += gain_ * (measurement - x_);
        return x_;
    }

    void reset(float init = 0.0f) {
        x_ = init;
        is_initialized_ = false;
    }

private:
    static constexpr float steadyStateGain(float process, float measure) {
        float p = 1.0f;
        float gain = 0.0f;
        float prev_gain = -1.0f;
        constexpr float epsilon = 1e-6f;

        for (int i = 0; i < 100; ++i) {
            p += process;
            gain = p / (p + measure);
            p *= (1.0f - gain);

            float diff = gain - prev_gain;
            if ((diff < 0.0f ? -diff : diff) < epsilon) {
                break;
            }
            prev_gain = gain;
        }
        return gain;
    }
};

// ─── PID ─────────────────────────────────────────────────────
class PidController {
    float kp_, ki_, kd_, deadband_, max_out_;
    float max_integral_out_;
    float inv_dt_;
    float integral_ = 0.0f;
    float prev_error_ = 0.0f;
public:
    PidController(float kp, float ki, float kd, float deadband, float max_out, float dt)
        : kp_(kp), ki_(ki), kd_(kd), deadband_(deadband), max_out_(max_out),
          max_integral_out_(ki != 0.0f ? max_out / ki : 0.0f),
          inv_dt_(dt > 0.0f ? 1.0f / dt : 0.0f) {}

    float compute(float target, float measured, float dt) {
        if (dt <= 0.0f || dt > 0.5f) return 0.0f;
        float error = target - measured;
        if (std::abs(error) < deadband_) {
            integral_   = 0.0f;
            prev_error_ = 0.0f;
            return 0.0f;
        }
        if (ki_ != 0.0f) {
            integral_ = std::clamp(integral_ + error * dt, -max_integral_out_, max_integral_out_);
        }
        float derivative = 0.0f;
        if (kd_ != 0.0f) {
            derivative = (error - prev_error_) * inv_dt_;
            prev_error_ = error;
        }
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
    float x_center;
    float y_center;
    float confidence;
    bool  detected;
    bool  human_detected;
};

struct LaserSafetyState {
    bool enable_pin_high;
    bool laser_powered;
};

LaserSafetyState updateLaserSafety(bool human_detected) {
    bool enable_pin_high = !human_detected;
    return {enable_pin_high, enable_pin_high};
}

// Simulasyon icin gercek hedef konumu surekli degisir.
// Kontrol hedefi bu degerden degil, HUSKYLENS olcumunden uretilir.
struct TargetState {
    float true_az, true_el, t;
};

TargetState simulateTrueTarget(float t) {
    // Gercek hedef: yalnizca kamera olcumunu simule etmek icin kullanilir.
    // Trigonometrik fonksiyon kullanmadan dusuk maliyetli dogrusal hareket.
    float az = 119.0f + 0.8f * t;
    float el = 31.0f - 0.4f * t;
    return {az, el, t};
}

// HUSKYLENS gorus acisi ve koordinat donusumu
// Yatay FOV ~55°, dikey FOV ~42° kabul edilir.
constexpr float CAMERA_FOV_X_DEG = 55.0f;
constexpr float CAMERA_FOV_Y_DEG = 42.0f;
constexpr float CAMERA_RES_X_PX  = 320.0f;
constexpr float CAMERA_RES_Y_PX  = 240.0f;
constexpr float CAMERA_CENTER_X  = CAMERA_RES_X_PX * 0.5f;
constexpr float CAMERA_CENTER_Y  = CAMERA_RES_Y_PX * 0.5f;
constexpr float DEG_PER_PX_X     = CAMERA_FOV_X_DEG / CAMERA_RES_X_PX;
constexpr float DEG_PER_PX_Y     = CAMERA_FOV_Y_DEG / CAMERA_RES_Y_PX;

CameraDetection simulateCameraDetection(float antenna_az, float antenna_el,
                                        float target_az, float target_el) { 
    float dx = target_az - antenna_az;
    float dy = target_el - antenna_el;
    if (dx > 180.0f) dx -= 360.0f;
    if (dx < -180.0f) dx += 360.0f;

    bool in_fov_x = std::abs(dx) < CAMERA_FOV_X_DEG * 0.5f;
    bool in_fov_y = std::abs(dy) < CAMERA_FOV_Y_DEG * 0.5f;

    if (!in_fov_x || !in_fov_y) {
        return {CAMERA_CENTER_X, CAMERA_CENTER_Y, 0.0f, false, false};
    }

    float x_center = CAMERA_CENTER_X + dx / DEG_PER_PX_X;
    float y_center = CAMERA_CENTER_Y + dy / DEG_PER_PX_Y;

    // HUSKYLENS tespit guveni: sqrt yerine eksen bazli yaklasik uzaklik.
    float normalized_error_x = std::abs(dx) / (CAMERA_FOV_X_DEG * 0.5f);
    float normalized_error_y = std::abs(dy) / (CAMERA_FOV_Y_DEG * 0.5f);
    float normalized_error = std::max(normalized_error_x, normalized_error_y);
    float confidence = std::clamp(1.0f - normalized_error * 0.2f, 0.5f, 1.0f);

    return {x_center, y_center, confidence, true, false};
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

    std::cout << "--- KAMERA TAKIP SIMULASYONU v2 (Gercek Donanim Parametreleri) ---\n";
    std::cout << "Teensy 4.1 | HUSKYLENS | NEMA 17+DRV8825 | AS5600\n\n";

    Kalman1D     az_error_filter(KALMAN_PROCESS, KALMAN_MEASURE);
    Kalman1D     el_error_filter(KALMAN_PROCESS, KALMAN_MEASURE);
    PidController az_pid(AZ_KP, AZ_KI, AZ_KD, PID_DEADBAND, AZ_OUT_MAX, DT);
    PidController el_pid(EL_KP, EL_KI, EL_KD, PID_DEADBAND, EL_OUT_MAX, DT);
    MotorAxis     az_motor(119.0f, AZ_MAX_SPEED, AZ_LIMIT_MIN, AZ_LIMIT_MAX);
    MotorAxis     el_motor(29.0f,  EL_MAX_SPEED, EL_LIMIT_MIN, EL_LIMIT_MAX);

    constexpr int STEPS = 500;
    int lock_count = 0;
    int track_success_count = 0;
    int first_lock_step = -1;
    int laser_cut_count = 0;
    int search_count = 0;
    float search_az_dir = 1.0f;
    float search_el_dir = 1.0f;
    float max_boresight_sq = 0.0f;

    if constexpr (ENABLE_STEP_LOG) {
        std::cout << "Zaman(s)  HedefAz  HedefEl  KameraAz  KameraEl  "
                  << "PxErr_x  PxErr_y  Guven  FiltAz FiltEl  "
                  << "Hz_(/s)  El_(/s)  Kilit  Hata(°)\n";
        std::cout << "--------------------------------------------------------------------"
                  << "------------------------\n";
    }

    for (int i = 0; i < STEPS; ++i) {
        float t = i * DT;

        TargetState target = simulateTrueTarget(t);

        CameraDetection det = simulateCameraDetection(
            az_motor.position(), el_motor.position(),
            target.true_az, target.true_el);

        LaserSafetyState laser_safety = updateLaserSafety(det.human_detected);
        if (!laser_safety.laser_powered) ++laser_cut_count;

        float pixel_error_x = det.x_center - CAMERA_CENTER_X;
        float pixel_error_y = det.y_center - CAMERA_CENTER_Y;
        float az_direction_error = pixel_error_x * DEG_PER_PX_X * det.confidence;
        float el_direction_error = pixel_error_y * DEG_PER_PX_Y * det.confidence;
        float filtered_az_error = det.detected ? az_error_filter.update(az_direction_error) : 0.0f;
        float filtered_el_error = det.detected ? el_error_filter.update(el_direction_error) : 0.0f;

        float compensated_az = az_motor.position() + filtered_az_error;
        float compensated_el = el_motor.position() + filtered_el_error;
        if (compensated_az < AZ_LIMIT_MIN) compensated_az += 360.0f;
        if (compensated_az > AZ_LIMIT_MAX) compensated_az -= 360.0f;
        compensated_el = std::clamp(compensated_el, EL_LIMIT_MIN, EL_LIMIT_MAX);

        float az_speed = 0.0f;
        float el_speed = 0.0f;
        if (det.detected) {
            az_speed = az_pid.compute(compensated_az, az_motor.position(), DT);
            el_speed = el_pid.compute(compensated_el, el_motor.position(), DT);
        } else {
            ++search_count;
            if (el_motor.position() >= SEARCH_EL_MAX) search_el_dir = -1.0f;
            if (el_motor.position() <= SEARCH_EL_MIN) search_el_dir = 1.0f;
            az_speed = SEARCH_AZ_SPEED * search_az_dir;
            el_speed = SEARCH_EL_SPEED * search_el_dir;
        }

        az_motor.applySpeed(az_speed, DT);
        el_motor.applySpeed(el_speed, DT);

        float az_error = compensated_az - az_motor.position();
        float el_error = compensated_el - el_motor.position();
        if (az_error > 180.0f) az_error -= 360.0f;
        if (az_error < -180.0f) az_error += 360.0f;
        float boresight_sq = az_error * az_error + el_error * el_error;
        max_boresight_sq = std::max(max_boresight_sq, boresight_sq);
        bool locked = (boresight_sq < BORESIGHT_LOCK_LIMIT_DEG * BORESIGHT_LOCK_LIMIT_DEG);
        bool track_success = (boresight_sq < TRACK_SUCCESS_LIMIT_DEG * TRACK_SUCCESS_LIMIT_DEG);
        if (track_success) {
            ++track_success_count;
        }
        if (locked) {
            ++lock_count;
            if (first_lock_step < 0) first_lock_step = i;
        }

        if constexpr (ENABLE_STEP_LOG) {
            if (i % LOG_EVERY_STEPS == 0) {
                float boresight = std::sqrt(boresight_sq);
                std::cout << t << "    "
                          << compensated_az << "  " << compensated_el << "   "
                          << az_motor.position() << "     " << el_motor.position() << "    "
                          << pixel_error_x << "   " << pixel_error_y << "   "
                          << det.confidence << " "
                          << filtered_az_error << " " << filtered_el_error << " "
                          << az_speed << "  " << el_speed << " "
                          << (locked ? "KILITLI" : "ARAMA ") << " "
                          << boresight << "\n";
            }
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
    std::cout << "Takip basari orani: " << (100.0f * track_success_count / STEPS) << "%\n";
    std::cout << "Maks boresight: " << std::sqrt(max_boresight_sq) << "\n";
    std::cout << "Arama modu adim sayisi: " << search_count << "\n";
    std::cout << "Lazer guvenlik kesme sayisi: " << laser_cut_count << "\n";

    std::cout << "\n--- DONANIM PARAMETRELERI ---\n";
    std::cout << "Encoder   : AS5600 (12-bit, " << (int)ENCODER_CPR << " CPR, "
              << ENCODER_DEG_PER_CNT << " deg/count)\n";
    std::cout << "Motor     : NEMA 17 + DRV8825 (1/" << (int)MOTOR_MICROSTEPS
              << " microstep, " << (int)MOTOR_STEPS_PER_REV << " steps/rev)\n";
    std::cout << "Kamera    : HUSKYLENS (FOV=" << CAMERA_FOV_X_DEG << "x" << CAMERA_FOV_Y_DEG
              << ", " << (int)CAMERA_RES_X_PX << "x" << (int)CAMERA_RES_Y_PX << "px)\n";
    std::cout << "Kontrol   : Teensy 4.1 (100 Hz)\n";
    std::cout << "Deadband  : " << PID_DEADBAND << "\n";
    std::cout << "Kilit     : " << BORESIGHT_LOCK_LIMIT_DEG
              << " deg hassas kilit, " << TRACK_SUCCESS_LIMIT_DEG
              << " deg takip basari esigi\n";
    std::cout << "Arama     : Hedef kaybinda azimuth " << SEARCH_AZ_SPEED
              << " deg/s, elevasyon +/-" << SEARCH_EL_SPEED << " deg/s tarama\n";
    std::cout << "Lazer     : Pin " << LASER_ENABLE_PIN
              << " (MCLK2) HIGH=acik, LOW=insan algilandi/base kesildi\n";

    std::cout << "\nCikmak icin Enter'a basin...\n";
    std::cin.get();
    return 0;
}
