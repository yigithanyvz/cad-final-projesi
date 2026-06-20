from __future__ import annotations

import json
import logging
import queue
import socket
import threading
import time
from typing import Callable, Optional

import serial
import serial.tools.list_ports

from .protocol import (
    CommandMessage,
    TelemetryData,
    parse_message,
)

logger = logging.getLogger("mergen.comm")


class IoHandler:
    def __init__(self) -> None:
        self._serial_port: Optional[serial.Serial] = None
        self._wifi_sock: Optional[socket.socket] = None
        self._wifi_connected = False
        self._read_thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()
        self._rx_queue: queue.Queue = queue.Queue()
        self._callbacks: list[Callable] = []
        self._message_callbacks: list[Callable[[dict], None]] = []
        self._error_callback: Optional[Callable[[str], None]] = None
        self._serial_name: Optional[str] = None
        self._wifi_host: Optional[str] = None
        self._wifi_port: int = 5000
        self._active_path: Optional[str] = None

    @property
    def is_connected(self) -> bool:
        return self._active_path is not None

    @property
    def active_path(self) -> Optional[str]:
        return self._active_path

    def register_callback(self, cb: Callable[[TelemetryData], None]) -> None:
        self._callbacks.append(cb)

    def register_message_callback(self, cb: Callable[[dict], None]) -> None:
        self._message_callbacks.append(cb)

    def set_error_callback(self, cb: Callable[[str], None]) -> None:
        self._error_callback = cb

    def list_serial_ports(self) -> list[str]:
        return [p.device for p in serial.tools.list_ports.comports()]

    def connect_serial(self, port: str, baud: int = 115200) -> bool:
        self.disconnect()
        try:
            ser = serial.Serial(port, baud, timeout=0.05, write_timeout=1)
            self._serial_port = ser
            self._serial_name = f"{port}@{baud}"
            self._active_path = f"Serial:{port}"
            self._start_reader("serial")
            logger.info(f"Serial bağlandı: {port}")
            return True
        except serial.SerialException as e:
            logger.error(f"Serial bağlantı hatası: {e}")
            if self._error_callback:
                self._error_callback(f"Serial bağlantı hatası: {e}")
            return False

    def connect_wifi(self, host: str, port: int = 5000) -> bool:
        self.disconnect()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3.0)
            sock.connect((host, port))
            sock.settimeout(0.05)
            self._wifi_sock = sock
            self._wifi_host = host
            self._wifi_port = port
            self._wifi_connected = True
            self._active_path = f"WiFi:{host}:{port}"
            self._start_reader("wifi")
            logger.info(f"ESP32 bağlandı: {host}:{port}")
            return True
        except (socket.timeout, ConnectionRefusedError, OSError) as e:
            logger.error(f"ESP32 bağlantı hatası: {e}")
            if self._error_callback:
                self._error_callback(f"ESP32 bağlantı hatası: {e}")
            return False

    def disconnect(self) -> None:
        self._running = False
        if (self._read_thread and self._read_thread.is_alive()
                and threading.current_thread() is not self._read_thread):
            self._read_thread.join(timeout=1.0)
        with self._lock:
            if self._serial_port and self._serial_port.is_open:
                try:
                    self._serial_port.close()
                except Exception:
                    pass
            if self._wifi_sock:
                try:
                    self._wifi_sock.close()
                except Exception:
                    pass
        self._serial_port = None
        self._wifi_sock = None
        self._wifi_connected = False
        self._active_path = None
        self._serial_name = None
        self._wifi_host = None
        # Clear queue
        while not self._rx_queue.empty():
            try:
                self._rx_queue.get_nowait()
            except queue.Empty:
                break
        logger.info("Bağlantı kapatıldı")

    def send_command(self, cmd: CommandMessage) -> bool:
        payload = cmd.to_json()
        return self._send_raw(payload)

    def send_raw(self, text: str) -> bool:
        return self._send_raw(text)

    def _send_raw(self, text: str) -> bool:
        if not self._active_path:
            return False
        line = (text + "\n").encode("utf-8", errors="replace")
        with self._lock:
            if self._serial_port and self._serial_port.is_open:
                try:
                    self._serial_port.write(line)
                    return True
                except serial.SerialTimeoutException:
                    logger.warning("Serial write timeout")
                except Exception as e:
                    logger.error(f"Serial write error: {e}")
            elif self._wifi_sock:
                try:
                    self._wifi_sock.sendall(line)
                    return True
                except Exception as e:
                    logger.error(f"WiFi write error: {e}")
                    self._wifi_connected = False
        return False

    def _start_reader(self, source: str) -> None:
        self._running = True
        self._read_thread = threading.Thread(
            target=self._reader_loop, args=(source,), daemon=True
        )
        self._read_thread.start()

    def _reader_loop(self, source: str) -> None:
        buf = ""
        while self._running:
            try:
                if source == "serial":
                    if not self._serial_port or not self._serial_port.is_open:
                        break
                    raw = self._serial_port.read(1024)
                    if not raw:
                        continue
                    chunk = raw.decode("utf-8", errors="replace")
                elif source == "wifi":
                    if not self._wifi_sock:
                        break
                    raw = self._wifi_sock.recv(4096)
                    if not raw:
                        time.sleep(0.01)
                        continue
                    chunk = raw.decode("utf-8", errors="replace")
                else:
                    break
            except (serial.SerialException, OSError, socket.timeout):
                time.sleep(0.01)
                continue
            except Exception as e:
                logger.debug(f"Read error: {e}")
                time.sleep(0.01)
                continue

            buf += chunk
            while "\n" in buf:
                line, buf = buf.split("\n", 1)
                self._process_line(line.strip())

        self._handle_disconnect()

    def _process_line(self, line: str) -> None:
        if not line:
            return
        msg = parse_message(line)
        if msg is None:
            return
        msg_type = msg.get("type")
        for cb in self._message_callbacks:
            try:
                cb(msg)
            except Exception:
                pass
        if msg_type == "tel":
            try:
                tel = TelemetryData.from_json(msg)
                self._rx_queue.put(tel)
                for cb in self._callbacks:
                    try:
                        cb(tel)
                    except Exception:
                        pass
            except Exception as e:
                logger.debug(f"Telemetry parse error: {e}")
        elif msg_type == "ack":
            logger.info(f"ACK: {msg}")
        elif msg_type == "log":
            log_msg = msg.get("msg", "")
            logger.info(f"Teensy: {log_msg}")
        elif msg_type == "error":
            err_msg = msg.get("msg", "Unknown error")
            logger.error(f"Teensy error: {err_msg}")
            if self._error_callback:
                self._error_callback(err_msg)
        elif msg_type == "status":
            status = msg.get("status", "")
            if status == "connected" and self._error_callback:
                self._error_callback("Teensy bağlandı, sistem hazır")

    def _handle_disconnect(self) -> None:
        if self._error_callback:
            self._error_callback("Bağlantı koptu!")
        self.disconnect()

    def get_telemetry(self) -> Optional[TelemetryData]:
        try:
            return self._rx_queue.get_nowait()
        except queue.Empty:
            return None

    def flush_telemetry(self) -> list[TelemetryData]:
        items: list[TelemetryData] = []
        while True:
            t = self.get_telemetry()
            if t is None:
                break
            items.append(t)
        return items
