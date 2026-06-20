#pragma once

#include "types.h"

#include <cstdint>

extern "C" {
    void     hal_uart_send(uint8_t ch, const uint8_t* data, uint16_t len);
    uint16_t hal_uart_recv(uint8_t ch, uint8_t* buf, uint16_t max_len);
    int8_t   hal_get_rssi_dbm();
}

class CRC16 {
public:
    static uint16_t calculate(const uint8_t* data, uint16_t len);
};

class TelemetryPublisher {
public:
    void buildAndSend(uint32_t timestamp_ms,
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
                      float el_error);

    const TelemetryPacket& lastPacket() const;

private:
    TelemetryPacket last_pkt_{};
};

class CommandReceiver {
public:
    static constexpr uint8_t QUEUE_SIZE = 8;

    void poll();
    bool dequeue(CommandPacket& out);
    bool empty() const;

private:
    CommandPacket queue_[QUEUE_SIZE]{};
    uint8_t head_ = 0;
    uint8_t tail_ = 0;
    uint8_t count_ = 0;

    void enqueue(const CommandPacket& cmd);
};
