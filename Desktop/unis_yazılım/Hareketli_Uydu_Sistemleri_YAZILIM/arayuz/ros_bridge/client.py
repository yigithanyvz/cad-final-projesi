from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger("mergen.ros_bridge")

_FALLBACK_PATH = Path(__file__).resolve().parent / "ros_bridge_outbox.jsonl"


@dataclass
class RosTelemetry:
    az_actual: float = 0.0
    el_actual: float = 0.0
    az_target: float = 0.0
    el_target: float = 0.0
    roll: float = 0.0
    pitch: float = 0.0
    yaw: float = 0.0
    locked: bool = False
    mode: str = "IDLE"
    errors: int = 0
    rssi: int = -100
    timestamp: float = 0.0
    sat_az: float = 0.0
    sat_el: float = 0.0
    err_deg: float = 0.0


class MergenRosClient:
    BRIDGE_MODES = ("mergen", "stewart")

    def __init__(self) -> None:
        self.connected = False
        self._bridge_mode: str = "mergen"
        self._enabled = False
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._node = None
        self._rclpy = None
        self._last_tel: RosTelemetry = RosTelemetry()
        self._tel_lock = threading.Lock()
        self._callbacks: list[Callable[[RosTelemetry], None]] = []
        self._fallback_path = _FALLBACK_PATH

    @property
    def bridge_mode(self) -> str:
        return self._bridge_mode

    @bridge_mode.setter
    def bridge_mode(self, mode: str) -> None:
        if mode in self.BRIDGE_MODES:
            self._bridge_mode = mode

    @property
    def last_telemetry(self) -> RosTelemetry:
        with self._tel_lock:
            return self._last_tel

    def register_callback(self, cb: Callable[[RosTelemetry], None]) -> None:
        self._callbacks.append(cb)

    def enable(self) -> bool:
        if self._running:
            return self.connected
        self._enabled = True
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return True

    def disable(self) -> None:
        self._running = False
        if self._node is not None and self._rclpy is not None:
            try:
                self._node.destroy_node()
                self._rclpy.shutdown()
            except Exception:
                pass
        self.connected = False

    def publish_command(self, action: str, **kwargs) -> None:
        payload = {"type": "cmd", "action": action, "source": "mergen_gui", **kwargs}
        self._publish("/mergen/gui/command_json", payload)

    def publish_mode(self, mode: str) -> None:
        payload = {"type": "mode", "mode": mode, "source": "mergen_gui"}
        self._publish("/mergen/gui/mode_json", payload)

    def publish_target(self, az: float, el: float) -> None:
        payload = {
            "type": "target",
            "az": round(az, 4),
            "el": round(el, 4),
            "source": "mergen_gui",
        }
        self._publish("/mergen/gui/target_json", payload)
        if self._bridge_mode == "mergen" and self._rclpy is not None and self._node is not None:
            try:
                import mergen_interfaces.msg as mergen_msg

                msg = mergen_msg.TargetAngles()
                msg.stamp_sec = time.time()
                msg.azimuth_deg = az
                msg.elevation_deg = el
                msg.source = "mergen_gui"
                pub = getattr(self._node, "_pub_target_typed", None)
                if pub is None:
                    pub = self._node.create_publisher(
                        mergen_msg.TargetAngles, "/mergen/target_angles", 10
                    )
                    self._node._pub_target_typed = pub
                pub.publish(msg)
            except ImportError:
                pass

    def _publish(self, topic: str, payload: dict) -> None:
        if self.connected and self._rclpy is not None:
            try:
                from std_msgs.msg import String

                msg = String()
                msg.data = json.dumps(
                    payload, separators=(",", ":"), ensure_ascii=False
                )
                pub = getattr(self._node, f"_pub_{topic.replace('/', '_')}", None)
                if pub is None:
                    pub = self._node.create_publisher(String, topic, 10)
                    setattr(self._node, f"_pub_{topic.replace('/', '_')}", pub)
                pub.publish(msg)
                return
            except Exception as exc:
                logger.warning("ROS publish error: %s", exc)
        self._write_fallback(payload)

    def _loop(self) -> None:
        self._rclpy = None
        try:
            import rclpy

            self._rclpy = rclpy
        except ImportError:
            logger.warning(
                "rclpy bulunamadi. ROS2 kurulu degil veya source edilmemis:\n"
                "  source /opt/ros/humble/setup.bash  (veya kullandiginiz surum)\n"
                "  source ~/ros2_ws/install/setup.bash"
            )
            self._running = False
            self.connected = False
            return

        try:
            rclpy.init(args=None)
        except RuntimeError:
            pass

        self._node = self._rclpy.create_node("mergen_gui_client")

        try:
            from std_msgs.msg import String
        except ImportError:
            logger.error("std_msgs bulunamadi. ROS bridge devre disi.")
            self._running = False
            self.connected = False
            return

        self._node.create_subscription(
            String, "/mergen/telemetry_json", self._on_json_tel, 10
        )

        if self._bridge_mode == "mergen":
            self._subscribe_mergen()
        else:
            logger.info("Stewart bridge modu: satellite_bridge uzerinden iletisim.")

        self.connected = True
        logger.info(
            "ROS bridge aktif. Mod: %s. Telemetri dinleniyor.", self._bridge_mode
        )

        while self._running:
            try:
                self._rclpy.spin_once(self._node, timeout_sec=0.05)
            except Exception:
                break
        self.connected = False

    def _subscribe_mergen(self) -> None:
        try:
            from std_msgs.msg import String

            self._node.create_subscription(
                String, "/mergen/sim/telemetry_json", self._on_json_tel, 10
            )
        except Exception:
            pass
        try:
            import mergen_interfaces.msg as mergen_msg

            self._node.create_subscription(
                mergen_msg.MotorState, "/mergen/motor_state", self._on_motor_state, 10
            )
            self._node.create_subscription(
                mergen_msg.ImuFiltered,
                "/mergen/imu_filtered",
                self._on_imu_filtered,
                10,
            )
        except ImportError:
            logger.info(
                "mergen_interfaces bulunamadi. Sadece JSON topiclerine abone olunacak."
            )

    def _on_json_tel(self, msg) -> None:
        try:
            data = json.loads(msg.data)
        except json.JSONDecodeError:
            return
        with self._tel_lock:
            self._last_tel.timestamp = time.time()
            self._last_tel.az_actual = float(
                data.get("az_act", self._last_tel.az_actual)
            )
            self._last_tel.el_actual = float(
                data.get("el_act", self._last_tel.el_actual)
            )
            self._last_tel.az_target = float(
                data.get("az_tgt", self._last_tel.az_target)
            )
            self._last_tel.el_target = float(
                data.get("el_tgt", self._last_tel.el_target)
            )
            self._last_tel.roll = float(data.get("roll", self._last_tel.roll))
            self._last_tel.pitch = float(data.get("pitch", self._last_tel.pitch))
            self._last_tel.yaw = float(data.get("yaw", self._last_tel.yaw))
            self._last_tel.locked = bool(data.get("locked", self._last_tel.locked))
            self._last_tel.errors = int(data.get("errors", self._last_tel.errors))
            self._last_tel.rssi = int(data.get("rssi", self._last_tel.rssi))
            self._last_tel.mode = str(data.get("mode", self._last_tel.mode))
            self._last_tel.sat_az = float(data.get("sat_az", self._last_tel.sat_az))
            self._last_tel.sat_el = float(data.get("sat_el", self._last_tel.sat_el))
            self._last_tel.err_deg = float(data.get("err_deg", self._last_tel.err_deg))
        for cb in self._callbacks:
            try:
                cb(self._last_tel)
            except Exception:
                pass

    def _on_motor_state(self, msg) -> None:
        with self._tel_lock:
            self._last_tel.timestamp = time.time()
            self._last_tel.az_actual = float(
                getattr(msg, "azimuth_deg", self._last_tel.az_actual)
            )
            self._last_tel.el_actual = float(
                getattr(msg, "elevation_deg", self._last_tel.el_actual)
            )
            self._last_tel.az_target = float(
                getattr(msg, "azimuth_setpoint_deg", self._last_tel.az_target)
            )
            self._last_tel.el_target = float(
                getattr(msg, "elevation_setpoint_deg", self._last_tel.el_target)
            )
        for cb in self._callbacks:
            try:
                cb(self._last_tel)
            except Exception:
                pass

    def _on_imu_filtered(self, msg) -> None:
        with self._tel_lock:
            self._last_tel.timestamp = time.time()
            self._last_tel.roll = float(
                getattr(msg, "roll_deg", self._last_tel.roll)
            )
            self._last_tel.pitch = float(
                getattr(msg, "pitch_deg", self._last_tel.pitch)
            )
            self._last_tel.yaw = float(getattr(msg, "yaw_deg", self._last_tel.yaw))

    def _write_fallback(self, payload: dict) -> None:
        try:
            record = {"time": time.time(), **payload, "source": "mergen_gui"}
            with self._fallback_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError:
            pass
