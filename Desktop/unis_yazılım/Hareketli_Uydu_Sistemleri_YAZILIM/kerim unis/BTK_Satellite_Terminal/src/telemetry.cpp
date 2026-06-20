#include "telemetry.h"

#include "config.h"

#include <cstring>

uint16_t CRC16::calculate(const uint8_t* data, uint16_t len) {
    uint16_t crc = 0xFFFF;
    for (uint16_t i = 0; i < len; ++i) {
        crc ^= static_cast<uint16_t>(data[i]) << 8;
        for (int b = 0; b < 8; ++b) {
            crc = (crc & 0x8000) ? static_cast<uint16_t>((crc << 1) ^ 0x1021)
                                 : static_cast<uint16_t>(crc << 1);
        }
    }
    return crc;
}

void TelemetryPublisher::buildAndSend(
    uint32_t timestamp_ms,
    SystemState state,
    uint16_t errors,
    const GPSData& gps,
    const Orientation& orient,
    const EncoderData& encoder,
    const AntennaTarget& target,
    const AzEl& sat_azel,
    const StabilizationOutput& stab,
    const LaserTrackingCorrection& fine_track,
    float az_error,
    float el_error)
{
    TelemetryPacket pkt{};
    pkt.magic = TELEMETRY_PACKET_MAGIC;
    pkt.timestamp_ms = timestamp_ms;
    pkt.system_state = static_cast<uint8_t>(state);
    pkt.error_flags = errors;

    pkt.lat_deg = static_cast<float>(gps.position.lat_deg);
    pkt.lon_deg = static_cast<float>(gps.position.lon_deg);
    pkt.alt_m = static_cast<float>(gps.position.alt_m);

    pkt.roll_deg = orient.roll_deg;
    pkt.pitch_deg = orient.pitch_deg;
    pkt.yaw_deg = orient.yaw_deg;

    pkt.az_actual_deg = encoder.az_deg;
    pkt.el_actual_deg = encoder.el_deg;
    pkt.az_target_deg = target.az_setpoint_deg;
    pkt.el_target_deg = target.el_setpoint_deg;
    pkt.az_error_deg = az_error;
    pkt.el_error_deg = el_error;

    pkt.sat_az_deg = sat_azel.az_deg;
    pkt.sat_el_deg = sat_azel.el_deg;
    pkt.sat_range_km = sat_azel.range_km;

    pkt.stab_residual_error_deg = stab.residual_error_deg;
    pkt.stab_x_actuator_mm = stab.x_actuator_mm;
    pkt.stab_y_actuator_mm = stab.y_actuator_mm;
    pkt.stab_stable = stab.stable ? 1 : 0;
    pkt.stab_saturated = stab.saturated ? 1 : 0;

    pkt.fine_az_error_deg = fine_track.az_error_deg;
    pkt.fine_el_error_deg = fine_track.el_error_deg;
    pkt.fine_tracking_locked = fine_track.locked ? 1 : 0;

    pkt.rssi_dbm = hal_get_rssi_dbm();

    const uint16_t crc_len = sizeof(TelemetryPacket) - sizeof(uint16_t);
    pkt.crc16 = CRC16::calculate(reinterpret_cast<const uint8_t*>(&pkt), crc_len);

    hal_uart_send(
        UART_TELEMETRY_CH,
        reinterpret_cast<const uint8_t*>(&pkt),
        sizeof(TelemetryPacket));
    last_pkt_ = pkt;
}

const TelemetryPacket& TelemetryPublisher::lastPacket() const {
    return last_pkt_;
}

void CommandReceiver::poll() {
    uint8_t buf[sizeof(CommandPacket) + 4]{};
    const uint16_t n = hal_uart_recv(UART_TELEMETRY_CH, buf, sizeof(buf));
    if (n < sizeof(CommandPacket)) return;

    CommandPacket cmd{};
    cmd.cmd = static_cast<UserCommand>(buf[0]);
    std::memcpy(&cmd.payload, buf + 1, sizeof(cmd.payload));
    enqueue(cmd);
}

bool CommandReceiver::dequeue(CommandPacket& out) {
    if (count_ == 0) return false;
    out = queue_[head_];
    head_ = static_cast<uint8_t>((head_ + 1) % QUEUE_SIZE);
    --count_;
    return true;
}

bool CommandReceiver::empty() const {
    return count_ == 0;
}

void CommandReceiver::enqueue(const CommandPacket& cmd) {
    if (count_ == QUEUE_SIZE) return;
    queue_[tail_] = cmd;
    tail_ = static_cast<uint8_t>((tail_ + 1) % QUEUE_SIZE);
    ++count_;
}
