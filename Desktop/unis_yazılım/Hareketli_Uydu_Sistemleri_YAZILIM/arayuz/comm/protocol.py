from __future__ import annotations

import json
import time
from dataclasses import dataclass
from enum import IntEnum
from typing import Optional


PROTOCOL_VERSION = 1


class SystemState(IntEnum):
    POWER_OFF = 0
    IDLE = 1
    STARTING = 2
    AUTO_TRACKING = 3
    MANUAL = 4
    HOMING = 5
    EMERGENCY_STOP = 6
    ERROR = 7


class CommandType(IntEnum):
    START_SYSTEM = 1
    STOP_SYSTEM = 2
    EMERGENCY_STOP = 3
    SET_MODE = 4
    SET_TARGET = 5
    SET_GPS = 6
    HOME = 7
    RESET_ERROR = 8
    SET_PARAM = 9
    PING = 10
    REBOOT = 11


class MsgType:
    CMD = "cmd"
    TEL = "tel"
    VISION = "vision"
    STATUS = "status"
    LOG = "log"
    ACK = "ack"
    ERROR = "error"


@dataclass
class CommandMessage:
    action: str
    seq: Optional[int] = None
    mode: Optional[str] = None
    az: Optional[float] = None
    el: Optional[float] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    params: Optional[dict] = None

    def to_json(self) -> str:
        payload = {
            "type": MsgType.CMD,
            "protocol_version": PROTOCOL_VERSION,
            "timestamp_ms": int(time.time() * 1000),
            "action": self.action,
        }
        if self.seq is not None:
            payload["seq"] = self.seq
        if self.mode is not None:
            payload["mode"] = self.mode
        if self.az is not None:
            payload["az"] = round(self.az, 4)
        if self.el is not None:
            payload["el"] = round(self.el, 4)
        if self.lat is not None:
            payload["lat"] = round(self.lat, 6)
        if self.lon is not None:
            payload["lon"] = round(self.lon, 6)
        if self.params is not None:
            payload["params"] = self.params
        return json.dumps(payload, separators=(",", ":"))


@dataclass
class TelemetryData:
    protocol_version: int = PROTOCOL_VERSION
    seq: int = 0
    timestamp_ms: int = 0
    state: int = 0
    az_actual: float = 0.0
    el_actual: float = 0.0
    az_target: float = 0.0
    el_target: float = 0.0
    laser_error_x: float = 0.0
    laser_error_y: float = 0.0
    roll: float = 0.0
    pitch: float = 0.0
    yaw: float = 0.0
    locked: bool = False
    gps_lat: float = 0.0
    gps_lon: float = 0.0
    uptime_ms: int = 0
    errors: int = 0
    rssi: int = -100
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

    @classmethod
    def from_json(cls, data: dict) -> TelemetryData:
        return cls(
            protocol_version=data.get("protocol_version", PROTOCOL_VERSION),
            seq=data.get("seq", 0),
            timestamp_ms=data.get("timestamp_ms", data.get("uptime", 0)),
            state=data.get("state", 0),
            az_actual=data.get("az_act", 0.0),
            el_actual=data.get("el_act", 0.0),
            az_target=data.get("az_tgt", 0.0),
            el_target=data.get("el_tgt", 0.0),
            laser_error_x=data.get("laser_x", 0.0),
            laser_error_y=data.get("laser_y", 0.0),
            roll=data.get("roll", 0.0),
            pitch=data.get("pitch", 0.0),
            yaw=data.get("yaw", 0.0),
            locked=bool(data.get("locked", False)),
            gps_lat=data.get("gps_lat", 0.0),
            gps_lon=data.get("gps_lon", 0.0),
            uptime_ms=data.get("uptime", 0),
            errors=data.get("errors", 0),
            rssi=data.get("rssi", -100),
            target_detected=bool(data.get("target_detected", data.get("detected", False))),
            target_center_x=data.get("target_cx", data.get("center_x", 0.0)),
            target_center_y=data.get("target_cy", data.get("center_y", 0.0)),
            frame_center_x=data.get("frame_cx", 0.0),
            frame_center_y=data.get("frame_cy", 0.0),
            bbox_x=data.get("bbox_x", 0.0),
            bbox_y=data.get("bbox_y", 0.0),
            bbox_w=data.get("bbox_w", 0.0),
            bbox_h=data.get("bbox_h", 0.0),
            confidence=data.get("confidence", 0.0),
            vision_fps=data.get("vision_fps", data.get("fps", 0.0)),
            video_fps=data.get("video_fps", 0.0),
            lost_frames=data.get("lost_frames", 0),
        )


def parse_message(line: str) -> Optional[dict]:
    line = line.strip()
    if not line:
        return None
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        return None
