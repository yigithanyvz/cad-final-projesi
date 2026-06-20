#pragma once

#include "types.h"

#include <cstdint>

class CameraObjectDetector {
public:
    LaserSpotData update(const CameraObjectDetection& detection, uint32_t now_ms);
    void reset();

private:
    float filtered_x_norm_ = 0.0f;
    float filtered_y_norm_ = 0.0f;
    uint32_t last_detection_ms_ = 0;
    bool initialized_ = false;

    static bool isUsableDetection(const CameraObjectDetection& detection);
};
