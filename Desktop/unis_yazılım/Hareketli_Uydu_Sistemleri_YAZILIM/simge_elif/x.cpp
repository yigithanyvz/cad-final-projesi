/*#include <iostream>
#include <vector>
#include <cmath>
#include <locale.h> // Windows terminalinde Türkçe karakter desteği için

// MERGEN STABİLİZASYON SINIFI
class MergenStabilizer {
public:
    // PID Parametreleri (Rapor Sayfa 8)
    float Kp = 2.0f;
    float Ki = 0.5f;
    float Kd = 0.1f;
    float previousError = 0.0f;
    float integral = 0.0f;

    // 1. IMU'dan Gelen Veriyi İşleme (Filtreleme Simülasyonu)
    float processIMU(float rawData) {
        return rawData * 0.95f; 
    }

    // 2. PID Kontrol Döngüsü
    float calculateCorrection(float currentAngle, float targetAngle) {
        float error = targetAngle - currentAngle;
        integral += error;
        float derivative = error - previousError;
        previousError = error;
        return (Kp * error) + (Ki * integral) + (Kd * derivative);
    }

    // 3. Motor Tetikleme
    void driveMotors(float correction) {
        std::cout << "[SISTEM] Motorlara gonderilen adim degeri: " << correction << std::endl;
    }
};

int main() {
    // Windows terminalinde Türkçe karakter sorunu olmaması için
    setlocale(LC_ALL, "Turkish");

    MergenStabilizer mergen;
    
    std::cout << "--- MERGEN SOTM SISTEMI BASLATILIYOR ---" << std::endl;

    // Simülasyon: Araç 5 derecelik bir sarsıntı yaptı
    float sensorInput = 5.0f; 
    
    float cleanData = mergen.processIMU(sensorInput);
    float correction = mergen.calculateCorrection(cleanData, 0.0f); 
    mergen.driveMotors(correction);

    std::cout << "--- ISLEM TAMAMLANDI ---" << std::endl;
    
    // Windows'ta terminalin hemen kapanmaması için bir tuş bekle
    std::cout << "Cikmak icin Enter'a basin..." << std::endl;
    std::cin.get(); 

    return 0;
}
*/

// DÜZENLENMİŞ HALİ
#include <iostream>
#include <algorithm> // std::clamp için
#ifdef _WIN32
#include <windows.h>
#endif

class MergenStabilizer {
public:
    float Kp = 2.0f;
    float Ki = 0.5f;
    float Kd = 0.1f;

private:
    float previousError = 0.0f;
    float integral      = 0.0f;
    float prevFiltered  = 0.0f;

    const float DEADBAND_DEG   = 0.1f;  // Ölü bant eşiği (config.h PID_DEADBAND_DEG)
    const float INTEGRAL_LIMIT = 50.0f;
    const float ALPHA          = 0.1f;  // Low-pass filtre katsayısı

public:
    // Gerçek low-pass filtre
    float processIMU(float rawData) {
        prevFiltered = ALPHA * rawData + (1.0f - ALPHA) * prevFiltered;
        return prevFiltered;
    }

    // dt (saniye cinsinden zaman adımı) parametresi eklendi
    float calculateCorrection(float currentAngle, float targetAngle, float dt) {
        if (dt <= 0.0f) return 0.0f; // Güvenlik kontrolü

        float error = targetAngle - currentAngle;

        // Ölü bant: küçük hatalar motor titreşimine yol açar
        if (std::abs(error) < DEADBAND_DEG) {
            previousError = 0.0f;
            integral      = 0.0f;
            return 0.0f;
        }

        // Integral windup koruması ile
        integral = std::clamp(integral + error * dt, -INTEGRAL_LIMIT, INTEGRAL_LIMIT);

        float derivative = (error - previousError) / dt;
        previousError = error;

        return (Kp * error) + (Ki * integral) + (Kd * derivative);
    }

    void driveMotors(float correction) {
        std::cout << "[SISTEM] Motor adim degeri: " << correction << "\n";
    }

    void reset() {
        previousError = 0.0f;
        integral      = 0.0f;
        prevFiltered  = 0.0f;
    }
};

int main() {
#ifdef _WIN32
    SetConsoleOutputCP(65001); // UTF-8 desteği
#endif

    MergenStabilizer mergen;
    const float dt = 0.01f; // 10ms = 100Hz döngü hızı

    std::cout << "--- MERGEN SOTM SISTEMI BASLATILIYOR ---\n";

    // Simülasyon: birkaç adım çalıştır
    float sensorInputs[] = {5.0f, 3.2f, 1.8f, 0.5f, 0.1f};

    for (float raw : sensorInputs) {
        float clean      = mergen.processIMU(raw);
        float correction = mergen.calculateCorrection(clean, 0.0f, dt);
        mergen.driveMotors(correction);
        std::cout << "  Sensor: " << raw
                  << " -> Filtered: " << clean
                  << " -> Duzeltme: " << correction << "\n";
    }

    std::cout << "--- ISLEM TAMAMLANDI ---\n";
    std::cout << "Cikmak icin Enter'a basin...\n";
    std::cin.get();
    return 0;
}