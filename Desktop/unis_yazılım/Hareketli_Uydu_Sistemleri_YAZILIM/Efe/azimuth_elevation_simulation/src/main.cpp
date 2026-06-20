#include <chrono>
#include <cmath>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <random>
#include <sstream>
#include <string>
#include <thread>
#include <vector>

#include "../../cpp_core/include/mergen_core.hpp"

namespace fs = std::filesystem;

struct DatasetRow {
    double time_s = 0.0;
    double target_azimuth_deg = 120.0;
    double target_elevation_deg = 30.0;
    double imu_roll_deg = 0.0;
    double imu_pitch_deg = 0.0;
    double qpd_error_x = 0.0;
    double qpd_error_y = 0.0;
};

std::vector<std::string> splitCsvLine(const std::string& line) {
    std::vector<std::string> parts;
    std::stringstream stream(line);
    std::string cell;
    while (std::getline(stream, cell, ',')) parts.push_back(cell);
    return parts;
}

void generateDataset(const fs::path& path, unsigned int seed, double target_azimuth, double target_elevation) {
    std::mt19937 rng(seed);
    std::normal_distribution<double> angle_noise(0.0, 0.16);
    std::normal_distribution<double> target_noise(0.0, 0.08);
    std::normal_distribution<double> qpd_noise(0.0, 0.012);

    constexpr double duration_s = 300.0;
    constexpr double rate_hz = 100.0;
    constexpr double dt_s = 1.0 / rate_hz;
    const int samples = static_cast<int>(duration_s * rate_hz);

    fs::create_directories(path.parent_path());
    std::ofstream file(path);
    file << "time_s,target_azimuth_deg,target_elevation_deg,imu_roll_deg,imu_pitch_deg,qpd_error_x,qpd_error_y\n";
    file << std::fixed << std::setprecision(5);

    for (int i = 0; i < samples; ++i) {
        const double t = i * dt_s;
        const double phase = 2.0 * mergen::kPi * t / 10.0;
        const double roll = 8.0 * std::sin(phase) + angle_noise(rng);
        const double pitch = 8.0 * std::cos(phase) + angle_noise(rng);

        // Hedef verisi arayuz/uydu takip katmanindan geliyormus gibi hafif degisken tutulur.
        const double target_az = target_azimuth + 0.15 * std::sin(0.08 * t) + target_noise(rng);
        const double target_el = target_elevation + 0.10 * std::cos(0.06 * t) + target_noise(rng);

        // QPD hedef merkezinden sapmayi normalize olcekli kucuk hata olarak taklit eder.
        const double qpd_x = 0.20 * std::sin(0.55 * t) + qpd_noise(rng);
        const double qpd_y = 0.16 * std::cos(0.47 * t) + qpd_noise(rng);

        file << t << ',' << target_az << ',' << target_el << ',' << roll << ',' << pitch << ',' << qpd_x << ',' << qpd_y << '\n';
    }
}

std::vector<DatasetRow> readDataset(const fs::path& path) {
    std::ifstream file(path);
    if (!file) throw std::runtime_error("Dataset okunamadi: " + path.string());

    std::vector<DatasetRow> rows;
    std::string line;
    std::getline(file, line); // header
    while (std::getline(file, line)) {
        const auto parts = splitCsvLine(line);
        if (parts.size() < 7) continue;
        DatasetRow row;
        row.time_s = std::stod(parts[0]);
        row.target_azimuth_deg = std::stod(parts[1]);
        row.target_elevation_deg = std::stod(parts[2]);
        row.imu_roll_deg = std::stod(parts[3]);
        row.imu_pitch_deg = std::stod(parts[4]);
        row.qpd_error_x = std::stod(parts[5]);
        row.qpd_error_y = std::stod(parts[6]);
        rows.push_back(row);
    }
    return rows;
}

mergen::SummaryMetrics simulate(const std::vector<DatasetRow>& rows, const fs::path& output_csv, const fs::path& live_json) {
    mergen::KalmanFilter1D az_target_filter(0.015, 0.20, 120.0);
    mergen::KalmanFilter1D el_target_filter(0.015, 0.20, 30.0);
    mergen::KalmanFilter1D roll_filter(0.02, 0.35);
    mergen::KalmanFilter1D pitch_filter(0.02, 0.35);

    mergen::PidController az_pid({2.45, 0.030, 0.18, -1.0, 1.0});
    mergen::PidController el_pid({2.65, 0.030, 0.20, -1.0, 1.0});
    mergen::PidController qpd_x_pid({0.55, 0.000, 0.04, -2.0, 2.0});
    mergen::PidController qpd_y_pid({0.55, 0.000, 0.04, -2.0, 2.0});

    mergen::RateLimitedAxis az_axis(0.0, 160.0 / 5.18, 0.18, 0.08);
    mergen::RateLimitedAxis el_axis(0.0, 90.0 / 3.0, 0.16, 0.05);

    std::ofstream out(output_csv);
    out << "time_s,target_azimuth_deg,target_elevation_deg,filtered_azimuth_target_deg,filtered_elevation_target_deg,"
        << "azimuth_deg,elevation_deg,azimuth_motor_pwm,elevation_motor_pwm,roll_filtered_deg,pitch_filtered_deg,"
        << "qpd_offset_azimuth_deg,qpd_offset_elevation_deg,boresight_error_deg,locked\n";
    out << std::fixed << std::setprecision(5);

    double total_error = 0.0;
    double max_error = 0.0;
    double settled_error = 0.0;
    int lock_count = 0;
    int settled_lock_count = 0;
    int settled_count = 0;
    double first_lock = -1.0;

    for (std::size_t i = 0; i < rows.size(); ++i) {
        const auto& row = rows[i];
        const double dt = (i == 0) ? 0.01 : std::max(0.001, row.time_s - rows[i - 1].time_s);

        const double filtered_roll = roll_filter.update(row.imu_roll_deg);
        const double filtered_pitch = pitch_filter.update(row.imu_pitch_deg);
        const double filtered_target_az = az_target_filter.update(row.target_azimuth_deg);
        const double filtered_target_el = mergen::clamp(el_target_filter.update(row.target_elevation_deg), 0.0, 90.0);

        // QPD aktif takip, teorik hedefe kucuk offset bindirir.
        const double qpd_az_offset = qpd_x_pid.update(0.0, row.qpd_error_x, dt);
        const double qpd_el_offset = qpd_y_pid.update(0.0, row.qpd_error_y, dt);

        // Azimuth/elevasyon katmani, mama kabi stabilizasyonundan sonra kalan
        // artik egimi gorur. Bu nedenle ham roll/pitch etkisinin tamamini degil,
        // stabilizasyon sonrasi kucuk bir artik oranini hedefe yansitiyoruz.
        const double compensated_az_target = filtered_target_az + qpd_az_offset + filtered_roll * 0.06;
        const double compensated_el_target = mergen::clamp(filtered_target_el + qpd_el_offset + filtered_pitch * 0.08, 0.0, 90.0);

        const double az_pwm = az_pid.update(compensated_az_target, az_axis.position(), dt, true);
        const double el_pwm = el_pid.update(compensated_el_target, el_axis.position(), dt, false);

        az_axis.update(az_axis.position() + az_pwm * 8.0, dt, true);
        el_axis.update(mergen::clamp(el_axis.position() + el_pwm * 5.0, 0.0, 90.0), dt, false);

        const double az_error = mergen::wrapDegrees(compensated_az_target - az_axis.position());
        const double el_error = compensated_el_target - el_axis.position();
        const double boresight_error = std::hypot(az_error, el_error);
        const bool locked = boresight_error <= 1.0;

        total_error += boresight_error;
        max_error = std::max(max_error, boresight_error);
        if (locked) {
            ++lock_count;
            if (first_lock < 0.0) first_lock = row.time_s;
        }
        if (row.time_s >= 8.0) {
            settled_error += boresight_error;
            ++settled_count;
            if (locked) ++settled_lock_count;
        }

        out << row.time_s << ',' << row.target_azimuth_deg << ',' << row.target_elevation_deg << ','
            << filtered_target_az << ',' << filtered_target_el << ',' << az_axis.position() << ',' << el_axis.position() << ','
            << az_pwm << ',' << el_pwm << ',' << filtered_roll << ',' << filtered_pitch << ','
            << qpd_az_offset << ',' << qpd_el_offset << ',' << boresight_error << ',' << (locked ? "true" : "false") << '\n';

        if (i % 10 == 0 || i + 1 == rows.size()) {
            mergen::writeLiveState(live_json.string(), row.time_s, az_axis.position(), el_axis.position(),
                                   compensated_az_target, compensated_el_target, filtered_roll, filtered_pitch,
                                   boresight_error, locked, "AZ_EL_TRACKING");
        }
    }

    mergen::SummaryMetrics metrics;
    metrics.first_lock_time_s = first_lock;
    metrics.mean_error_deg = total_error / static_cast<double>(rows.size());
    metrics.max_error_deg = max_error;
    metrics.settled_mean_error_deg = settled_error / static_cast<double>(std::max(1, settled_count));
    metrics.lock_ratio_percent = 100.0 * static_cast<double>(lock_count) / static_cast<double>(rows.size());
    metrics.settled_lock_ratio_percent = 100.0 * static_cast<double>(settled_lock_count) / static_cast<double>(std::max(1, settled_count));
    return metrics;
}

void writeSummary(const fs::path& path, const mergen::SummaryMetrics& m, unsigned int seed) {
    std::ofstream file(path);
    file << "# Azimuth/Elevasyon C++ Simulasyon Ozeti\n\n";
    file << "Seed: `" << seed << "`\n\n";
    file << "| Metrik | Deger |\n| --- | ---: |\n";
    file << "| Ilk kilitlenme zamani | " << m.first_lock_time_s << " s |\n";
    file << "| Ortalama boresight hatasi | " << m.mean_error_deg << " deg |\n";
    file << "| Maksimum boresight hatasi | " << m.max_error_deg << " deg |\n";
    file << "| 8 sn sonrasi ortalama hata | " << m.settled_mean_error_deg << " deg |\n";
    file << "| Toplam kilit orani | " << m.lock_ratio_percent << " % |\n";
    file << "| 8 sn sonrasi kilit orani | " << m.settled_lock_ratio_percent << " % |\n";
}

int main(int argc, char** argv) {
    double target_azimuth = 120.0;
    double target_elevation = 30.0;
    bool realtime_delay = false;
    if (argc >= 3) {
        target_azimuth = std::atof(argv[1]);
        target_elevation = std::atof(argv[2]);
    }
    if (argc >= 4) realtime_delay = std::string(argv[3]) == "--realtime";

    const auto now = std::chrono::system_clock::now().time_since_epoch().count();
    const unsigned int seed = static_cast<unsigned int>(now & 0xFFFFFFFFu);

    const fs::path base = fs::path("Efe") / "azimuth_elevation_simulation" / "results";
    fs::create_directories(base);
    const fs::path dataset_path = base / "generated_dataset.csv";
    const fs::path output_path = base / "simulation_output.csv";
    const fs::path summary_path = base / "summary.md";
    const fs::path live_path = base / "live_state.json";

    generateDataset(dataset_path, seed, target_azimuth, target_elevation);
    const auto rows = readDataset(dataset_path);
    const auto metrics = simulate(rows, output_path, live_path);
    writeSummary(summary_path, metrics, seed);

    if (realtime_delay) std::this_thread::sleep_for(std::chrono::milliseconds(100));

    std::cout << "Azimuth/Elevasyon simulasyonu tamamlandi.\n";
    std::cout << "Dataset: " << dataset_path << "\n";
    std::cout << "Sonuc: " << output_path << "\n";
    std::cout << "Ozet: " << summary_path << "\n";
    return 0;
}
