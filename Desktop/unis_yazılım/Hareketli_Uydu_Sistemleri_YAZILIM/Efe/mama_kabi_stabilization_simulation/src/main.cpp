#include <chrono>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <random>
#include <sstream>
#include <string>
#include <vector>

#include "../../cpp_core/include/mergen_core.hpp"

namespace fs = std::filesystem;

struct ImuRow {
    double time_s = 0.0;
    double raw_roll_deg = 0.0;
    double raw_pitch_deg = 0.0;
};

class StabilizerPlant {
public:
    std::pair<double, double> update(double target_x_mm, double target_y_mm, double dt_s) {
        target_x_mm = mergen::clamp(target_x_mm, -40.0, 40.0);
        target_y_mm = mergen::clamp(target_y_mm, -40.0, 40.0);
        const double alpha = dt_s / std::max(0.12, dt_s);
        x_mm_ += alpha * (target_x_mm - x_mm_);
        y_mm_ += alpha * (target_y_mm - y_mm_);
        return {x_mm_, y_mm_};
    }

private:
    double x_mm_ = 0.0;
    double y_mm_ = 0.0;
};

std::vector<std::string> splitCsvLine(const std::string& line) {
    std::vector<std::string> parts;
    std::stringstream stream(line);
    std::string cell;
    while (std::getline(stream, cell, ',')) parts.push_back(cell);
    return parts;
}

void generateImuDataset(const fs::path& path, unsigned int seed) {
    std::mt19937 rng(seed);
    std::normal_distribution<double> noise(0.0, 0.18);
    constexpr double duration_s = 300.0;
    constexpr double rate_hz = 100.0;
    constexpr double dt_s = 1.0 / rate_hz;
    const int samples = static_cast<int>(duration_s * rate_hz);

    fs::create_directories(path.parent_path());
    std::ofstream file(path);
    file << "time_s,raw_roll_deg,raw_pitch_deg\n";
    file << std::fixed << std::setprecision(5);
    for (int i = 0; i < samples; ++i) {
        const double t = i * dt_s;
        const double phase = 2.0 * mergen::kPi * t / 10.0;
        const double roll = 8.0 * std::sin(phase) + noise(rng);
        const double pitch = 8.0 * std::cos(phase) + noise(rng);
        file << t << ',' << roll << ',' << pitch << '\n';
    }
}

std::vector<ImuRow> readImuDataset(const fs::path& path) {
    std::ifstream file(path);
    if (!file) throw std::runtime_error("IMU dataset okunamadi: " + path.string());
    std::string line;
    std::getline(file, line);
    std::vector<ImuRow> rows;
    while (std::getline(file, line)) {
        const auto parts = splitCsvLine(line);
        if (parts.size() < 3) continue;
        rows.push_back({std::stod(parts[0]), std::stod(parts[1]), std::stod(parts[2])});
    }
    return rows;
}

mergen::SummaryMetrics simulate(const std::vector<ImuRow>& rows, const fs::path& output_csv, const fs::path& live_json) {
    mergen::KalmanFilter1D roll_filter(0.02, 0.35);
    mergen::KalmanFilter1D pitch_filter(0.02, 0.35);
    mergen::PidController roll_pid({1.0, 0.0, 0.05, -8.0, 8.0});
    mergen::PidController pitch_pid({1.0, 0.0, 0.05, -8.0, 8.0});
    StabilizerPlant plant;

    std::ofstream out(output_csv);
    out << "time_s,raw_roll_deg,raw_pitch_deg,filtered_roll_deg,filtered_pitch_deg,"
        << "x_motor_command_mm,y_motor_command_mm,x_position_mm,y_position_mm,residual_roll_deg,residual_pitch_deg,stabilization_error_deg,stable\n";
    out << std::fixed << std::setprecision(5);

    double total_error = 0.0;
    double max_error = 0.0;
    int stable_count = 0;
    double settled_error = 0.0;
    int settled_stable_count = 0;
    int settled_count = 0;
    double first_stable_time = -1.0;

    for (std::size_t i = 0; i < rows.size(); ++i) {
        const auto& row = rows[i];
        const double dt = (i == 0) ? 0.01 : std::max(0.001, row.time_s - rows[i - 1].time_s);
        const double roll = roll_filter.update(row.raw_roll_deg);
        const double pitch = pitch_filter.update(row.raw_pitch_deg);
        const double x_command_mm = roll_pid.update(0.0, roll, dt) * 4.0;
        const double y_command_mm = pitch_pid.update(0.0, pitch, dt) * 4.0;
        const auto [x_mm, y_mm] = plant.update(x_command_mm, y_command_mm, dt);

        const double residual_roll = roll + x_mm / 4.0;
        const double residual_pitch = pitch + y_mm / 4.0;
        const double error = std::hypot(residual_roll, residual_pitch);
        const bool stable = error <= 1.0;

        total_error += error;
        max_error = std::max(max_error, error);
        if (stable) {
            ++stable_count;
            if (first_stable_time < 0.0) first_stable_time = row.time_s;
        }
        if (row.time_s >= 8.0) {
            settled_error += error;
            ++settled_count;
            if (stable) ++settled_stable_count;
        }

        out << row.time_s << ',' << row.raw_roll_deg << ',' << row.raw_pitch_deg << ',' << roll << ',' << pitch << ','
            << x_command_mm << ',' << y_command_mm << ',' << x_mm << ',' << y_mm << ',' << residual_roll << ',' << residual_pitch << ','
            << error << ',' << (stable ? "true" : "false") << '\n';

        if (i % 10 == 0 || i + 1 == rows.size()) {
            mergen::writeLiveState(live_json.string(), row.time_s, 0.0, 0.0, 0.0, 0.0, residual_roll, residual_pitch, error, stable, "MAMA_KABI_STABILIZATION");
        }
    }

    mergen::SummaryMetrics metrics;
    metrics.first_lock_time_s = first_stable_time;
    metrics.mean_error_deg = total_error / static_cast<double>(rows.size());
    metrics.max_error_deg = max_error;
    metrics.settled_mean_error_deg = settled_error / static_cast<double>(std::max(1, settled_count));
    metrics.lock_ratio_percent = 100.0 * stable_count / static_cast<double>(rows.size());
    metrics.settled_lock_ratio_percent = 100.0 * settled_stable_count / static_cast<double>(std::max(1, settled_count));
    return metrics;
}

void writeSummary(const fs::path& path, const mergen::SummaryMetrics& m, unsigned int seed) {
    std::ofstream file(path);
    file << "# Mama Kabi C++ Stabilizasyon Simulasyon Ozeti\n\n";
    file << "Seed: `" << seed << "`\n\n";
    file << "| Metrik | Deger |\n| --- | ---: |\n";
    file << "| Ilk stabil zaman | " << m.first_lock_time_s << " s |\n";
    file << "| Ortalama artik egim hatasi | " << m.mean_error_deg << " deg |\n";
    file << "| Maksimum artik egim hatasi | " << m.max_error_deg << " deg |\n";
    file << "| 8 sn sonrasi ortalama hata | " << m.settled_mean_error_deg << " deg |\n";
    file << "| Toplam stabil oran | " << m.lock_ratio_percent << " % |\n";
    file << "| 8 sn sonrasi stabil oran | " << m.settled_lock_ratio_percent << " % |\n";
}

int main() {
    const auto now = std::chrono::system_clock::now().time_since_epoch().count();
    const unsigned int seed = static_cast<unsigned int>(now & 0xFFFFFFFFu);
    const fs::path base = fs::path("Efe") / "mama_kabi_stabilization_simulation" / "results";
    fs::create_directories(base);
    const fs::path dataset_path = base / "generated_imu_dataset.csv";
    const fs::path output_path = base / "stabilization_output.csv";
    const fs::path summary_path = base / "summary.md";
    const fs::path live_path = base / "live_state.json";

    generateImuDataset(dataset_path, seed);
    const auto rows = readImuDataset(dataset_path);
    const auto metrics = simulate(rows, output_path, live_path);
    writeSummary(summary_path, metrics, seed);

    std::cout << "Mama kabi stabilizasyon simulasyonu tamamlandi.\n";
    std::cout << "Dataset: " << dataset_path << "\n";
    std::cout << "Sonuc: " << output_path << "\n";
    std::cout << "Ozet: " << summary_path << "\n";
    return 0;
}
