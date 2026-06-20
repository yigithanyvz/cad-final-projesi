#include "CameraObjectDetector.h"

#include "config.h"

#include <algorithm>
#include <cmath>

LaserSpotData CameraObjectDetector::update(
    const CameraObjectDetection& detection,
    uint32_t now_ms)
{
    LaserSpotData target{};
    target.timestamp_ms = now_ms;

    if (!isUsableDetection(detection)) {
        if (initialized_ && now_ms - last_detection_ms_ > CAMERA_MAX_LOST_MS) {
            reset();
        }
        return target;
    }

    const float frame_w = CAMERA_FRAME_WIDTH_PX;
    const float frame_h = CAMERA_FRAME_HEIGHT_PX;
    float dx_px = detection.center_x_px - frame_w * 0.5f;
    float dy_px = frame_h * 0.5f - detection.center_y_px;

    if (std::fabs(dx_px) < CAMERA_CENTER_DEADBAND_PX) dx_px = 0.0f;
    if (std::fabs(dy_px) < CAMERA_CENTER_DEADBAND_PX) dy_px = 0.0f;

    const float x_norm = std::clamp(dx_px / (frame_w * 0.5f), -1.0f, 1.0f);
    const float y_norm = std::clamp(dy_px / (frame_h * 0.5f), -1.0f, 1.0f);
    const float alpha = std::clamp(CAMERA_DETECTION_SMOOTHING_ALPHA, 0.0f, 1.0f);

    if (!initialized_) {
        filtered_x_norm_ = x_norm;
        filtered_y_norm_ = y_norm;
        initialized_ = true;
    } else {
        filtered_x_norm_ = alpha * x_norm + (1.0f - alpha) * filtered_x_norm_;
        filtered_y_norm_ = alpha * y_norm + (1.0f - alpha) * filtered_y_norm_;
    }

    last_detection_ms_ = now_ms;
    target.x_norm = filtered_x_norm_;
    target.y_norm = filtered_y_norm_;
    target.confidence = detection.confidence;
    target.detected = true;
    return target;
}

void CameraObjectDetector::reset() {
    filtered_x_norm_ = 0.0f;
    filtered_y_norm_ = 0.0f;
    last_detection_ms_ = 0;
    initialized_ = false;
}

bool CameraObjectDetector::isUsableDetection(const CameraObjectDetection& detection) {
    if (!detection.detected || detection.confidence < CAMERA_MIN_CONFIDENCE) {
        return false;
    }

    const float frame_w = CAMERA_FRAME_WIDTH_PX;
    const float frame_h = CAMERA_FRAME_HEIGHT_PX;
    if (detection.center_x_px < 0.0f || detection.center_x_px >= frame_w ||
        detection.center_y_px < 0.0f || detection.center_y_px >= frame_h ||
        detection.width_px <= 0.0f || detection.height_px <= 0.0f) {
        return false;
    }

    const float area_ratio =
        (detection.width_px * detection.height_px) / (frame_w * frame_h);
    return area_ratio >= CAMERA_MIN_BOX_AREA_RATIO;
}
