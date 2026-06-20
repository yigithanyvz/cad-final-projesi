from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional


class SystemMode(IntEnum):
    POWER_OFF = 0
    IDLE = 1
    STARTING = 2
    AUTO_TRACKING = 3
    MANUAL = 4
    HOMING = 5
    EMERGENCY_STOP = 6
    ERROR = 7


class TrackingMode(IntEnum):
    NO_TARGET = 0
    TRACKING = 1
    HOLD_LAST = 2
    SEARCHING = 3


@dataclass
class SystemState:
    mode: SystemMode = SystemMode.POWER_OFF
    az_actual: float = 0.0
    el_actual: float = 0.0
    az_target: float = 0.0
    el_target: float = 0.0
    laser_error_x: float = 0.0
    laser_error_y: float = 0.0
    laser_error_px: float = 0.0
    laser_error_py: float = 0.0
    roll: float = 0.0
    pitch: float = 0.0
    yaw: float = 0.0
    locked: bool = False
    gps_lat: float = 39.9208
    gps_lon: float = 32.8541
    uptime_ms: int = 0
    errors: int = 0
    rssi: int = -100
    connection_ok: bool = False
    connection_type: Optional[str] = None
    uptime_seconds: int = 0
    target_detected: bool = False
    target_center_x: float = 0.0
    target_center_y: float = 0.0
    frame_center_x: float = 0.0
    frame_center_y: float = 0.0
    bbox_x: float = 0.0
    bbox_y: float = 0.0
    bbox_w: float = 0.0
    bbox_h: float = 0.0
    confidence: float = 0.0
    vision_fps: float = 0.0
    video_fps: float = 0.0
    lost_frames: int = 0
    tracking_mode: TrackingMode = TrackingMode.NO_TARGET
    last_target_x: float = 0.0
    last_target_y: float = 0.0
    last_target_time: float = 0.0
    telemetry_rate_hz: float = 0.0
    ack_latency_ms: float = 0.0
    last_packet_seq: int = 0
    packet_loss_count: int = 0

    @property
    def tracking_mode_name(self) -> str:
        names = {
            TrackingMode.NO_TARGET: "HEDEF YOK",
            TrackingMode.TRACKING: "TAKIP",
            TrackingMode.HOLD_LAST: "SON KONUMDA BEKLE",
            TrackingMode.SEARCHING: "ARAMA MODU",
        }
        return names.get(self.tracking_mode, "BILINMEYEN")

    @property
    def boresight_error(self) -> float:
        return (self.laser_error_x ** 2 + self.laser_error_y ** 2) ** 0.5

    @property
    def mode_name(self) -> str:
        names = {
            SystemMode.POWER_OFF: "KAPALI",
            SystemMode.IDLE: "BEKLEMEDE",
            SystemMode.STARTING: "BASLIYOR",
            SystemMode.AUTO_TRACKING: "OTOMATIK",
            SystemMode.MANUAL: "MANUEL",
            SystemMode.HOMING: "HOMING",
            SystemMode.EMERGENCY_STOP: "ACIL DURUM",
            SystemMode.ERROR: "HATA",
        }
        return names.get(self.mode, "BILINMEYEN")

    @property
    def connection_status(self) -> str:
        if not self.connection_ok:
            return "Bağlı Değil"
        return f"Bağlı ({self.connection_type})"

    @property
    def error_description(self) -> str:
        if self.errors == 0:
            return "Yok"
        errs = []
        if self.errors & 0x0001:
            errs.append("IMU Hatası")
        if self.errors & 0x0002:
            errs.append("GPS Hatası")
        if self.errors & 0x0004:
            errs.append("Azimut Motor Hatası")
        if self.errors & 0x0008:
            errs.append("Elevasyon Motor Hatası")
        if self.errors & 0x0010:
            errs.append("Hedef Kaybı")
        if self.errors & 0x0020:
            errs.append("Limit Switch")
        if self.errors & 0x0040:
            errs.append("İletişim Hatası")
        if self.errors & 0x0080:
            errs.append("Acil Durum")
        return ", ".join(errs) if errs else f"Kod: 0x{self.errors:04X}"
