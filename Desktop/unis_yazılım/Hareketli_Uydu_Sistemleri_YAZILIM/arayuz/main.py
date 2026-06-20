from __future__ import annotations

import logging
import json
import os
import queue
import sys
import time
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Optional

_APP_DIR = os.path.dirname(os.path.abspath(__file__))
_PARENT_DIR = os.path.dirname(_APP_DIR)
if _PARENT_DIR not in sys.path:
    sys.path.insert(0, _PARENT_DIR)

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib

matplotlib.use("TkAgg")
import matplotlib.patches as mpatches

from arayuz.comm.io_handler import IoHandler
from arayuz.comm.protocol import CommandMessage, TelemetryData
from arayuz.core.system_state import SystemMode, SystemState, TrackingMode
from arayuz.core.satellite_pointing import SATELLITES, calculate_look_angles
from arayuz.ros_bridge.client import MergenRosClient, RosTelemetry

logger = logging.getLogger("mergen.gui")

FONT_FAMILY = "Segoe UI" if sys.platform == "win32" else "Helvetica"

COLORS = {
    "bg": "#1a1a2e",
    "bg2": "#16213e",
    "bg3": "#0f3460",
    "accent": "#e94560",
    "accent2": "#533483",
    "success": "#2ecc71",
    "warning": "#f39c12",
    "error": "#e74c3c",
    "text": "#ecf0f1",
    "text_dim": "#95a5a6",
    "panel_bg": "#1e2a45",
    "entry_bg": "#0d1b2a",
    "border": "#2a3a5c",
}


class MergenApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Mergen Terminal Kontrol Sistemi v2.0")
        self.geometry("1400x850")
        self.minsize(1200, 750)
        self.configure(bg=COLORS["bg"])

        self._io = IoHandler()
        self._ros = MergenRosClient()
        self._state = SystemState()
        self._last_tel_time: float = 0.0
        self._laser_history_x: list[float] = []
        self._laser_history_y: list[float] = []
        self._start_time: float = 0.0
        self._event_queue: queue.Queue[tuple[str, object]] = queue.Queue(maxsize=200)
        self._cmd_seq = 0
        self._pending_commands: dict[int, tuple[str, float]] = {}
        self._last_tel_counter_time = time.time()
        self._tel_count_since_rate = 0
        self._telemetry_timeout_warning = 0.5
        self._telemetry_timeout_hold = 1.5
        self._telemetry_timeout_lost = 3.0
        self._hold_last_seconds = 1.0
        self._lost_frame_hold_threshold = 5
        self._lost_frame_search_threshold = 20
        self._last_failsafe_action = "normal"
        self._run_dir = self._create_run_dir()
        self._simulation_mode = True
        self._ros_mode = False
        self._stewart_mode = False
        
        # EKLENEN ÖZELLİKLER - ALGORİTMA VE GÜVENLİK
        self._replay_mode = False
        self._replay_frames = []
        self._replay_idx = 0
        
        self._slew_rate_enabled = tk.BooleanVar(value=True)
        self._slew_rate_limit = tk.DoubleVar(value=15.0) # derece/sn
        self._desired_az = 0.0
        self._desired_el = 0.0
        
        self._calib_offset_x = 0.0
        self._calib_offset_y = 0.0
        
        self._style = ttk.Style(self)
        self._setup_style()
        self._build_ui()
        self._io.register_callback(self._on_telemetry)
        self._io.register_message_callback(self._on_raw_message)
        self._io.set_error_callback(self._on_comm_error)
        self._ros.register_callback(self._on_ros_telemetry)

        self.after(100, self._poll_state)

    def _create_run_dir(self) -> Path:
        stamp = time.strftime("%Y%m%d_%H%M%S")
        run_dir = Path(_APP_DIR) / "runs" / stamp
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    def _write_jsonl(self, name: str, payload: dict) -> None:
        record = {
            "time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "time_ms": int(time.time() * 1000),
            **payload,
        }
        try:
            with (self._run_dir / name).open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
        except OSError:
            pass

    def _setup_style(self) -> None:
        style = self._style
        style.theme_use("clam")
        style.configure(".", background=COLORS["bg"], foreground=COLORS["text"],
                        font=(FONT_FAMILY, 10))
        style.configure("TLabel", background=COLORS["bg"], foreground=COLORS["text"])
        style.configure("TLabelframe", background=COLORS["bg"], foreground=COLORS["accent"],
                        bordercolor=COLORS["border"], lightcolor=COLORS["border"],
                        darkcolor=COLORS["border"])
        style.configure("TLabelframe.Label", background=COLORS["bg"], foreground=COLORS["accent"],
                        font=(FONT_FAMILY, 11, "bold"))
        style.configure("TButton", background=COLORS["bg3"], foreground=COLORS["text"],
                        bordercolor=COLORS["border"], font=(FONT_FAMILY, 10))
        style.map("TButton", background=[("active", COLORS["accent"])])
        style.configure("Accent.TButton", background=COLORS["accent"], foreground="white",
                        font=(FONT_FAMILY, 10, "bold"))
        style.map("Accent.TButton", background=[("active", "#c0392b")])
        style.configure("Danger.TButton", background=COLORS["error"], foreground="white",
                        font=(FONT_FAMILY, 10, "bold"))
        style.map("Danger.TButton", background=[("active", "#c0392b")])
        style.configure("Success.TButton", background=COLORS["success"], foreground="white",
                        font=(FONT_FAMILY, 10, "bold"))
        style.map("Success.TButton", background=[("active", "#27ae60")])
        style.configure("TEntry", fieldbackground=COLORS["entry_bg"], foreground=COLORS["text"],
                        bordercolor=COLORS["border"], insertcolor=COLORS["text"])
        style.configure("TCombobox", fieldbackground=COLORS["entry_bg"], foreground=COLORS["text"],
                        bordercolor=COLORS["border"])
        style.configure("TRadiobutton", background=COLORS["bg"], foreground=COLORS["text"])
        style.configure("TMenubutton", background=COLORS["bg3"], foreground=COLORS["text"])
        style.configure("Status.TLabel", background=COLORS["bg2"], foreground=COLORS["text_dim"],
                        font=(FONT_FAMILY, 9))
        style.configure("Value.TLabel", background=COLORS["panel_bg"], foreground=COLORS["text"],
                        font=(FONT_FAMILY, 12, "bold"))
        style.configure("ValueSmall.TLabel", background=COLORS["panel_bg"], foreground=COLORS["text"],
                        font=(FONT_FAMILY, 10))
        style.configure("Title.TLabel", background=COLORS["bg"], foreground=COLORS["accent"],
                        font=(FONT_FAMILY, 14, "bold"))
        style.configure("Panel.TFrame", background=COLORS["panel_bg"])
        style.configure("PanelBg.TLabelframe", background=COLORS["panel_bg"])
        style.configure("PanelBg.TLabelframe.Label", background=COLORS["panel_bg"],
                        foreground=COLORS["accent"])

    def _build_ui(self) -> None:
        self._build_top_bar()
        self._build_main_grid()

    def _build_top_bar(self) -> None:
        bar = tk.Frame(self, bg=COLORS["bg2"], height=40)
        bar.pack(fill="x", padx=0, pady=0)
        bar.pack_propagate(False)

        tk.Label(bar, text="⚡ MERGEN", bg=COLORS["bg2"],
                 fg=COLORS["accent"], font=(FONT_FAMILY, 14, "bold")).pack(side="left", padx=15)

        self._conn_indicator = tk.Canvas(bar, width=16, height=16,
                                          bg=COLORS["bg2"], highlightthickness=0)
        self._conn_indicator.pack(side="left", padx=(0, 5))
        self._conn_dot = self._conn_indicator.create_oval(2, 2, 14, 14,
                                                           fill=COLORS["text_dim"], outline="")

        self._conn_label = tk.Label(bar, text="Bağlı Değil", bg=COLORS["bg2"],
                                     fg=COLORS["text_dim"], font=(FONT_FAMILY, 9))
        self._conn_label.pack(side="left", padx=(0, 20))

        self._status_label = tk.Label(bar, text="SİSTEM KAPALI", bg=COLORS["bg2"],
                                       fg=COLORS["text_dim"], font=(FONT_FAMILY, 10, "bold"))
        self._status_label.pack(side="left", padx=20)

        self._uptime_label = tk.Label(bar, text="Süre: --:--:--", bg=COLORS["bg2"],
                                       fg=COLORS["text_dim"], font=(FONT_FAMILY, 9))
        self._uptime_label.pack(side="right", padx=15)

        self._sim_indicator = tk.Label(bar, text="🔷 SİMÜLASYON", bg=COLORS["bg2"],
                                        fg=COLORS["warning"], font=(FONT_FAMILY, 9, "bold"))
        self._sim_indicator.pack(side="right", padx=15)

    def _build_main_grid(self) -> None:
        viewport = tk.Frame(self, bg=COLORS["bg"])
        viewport.pack(fill="both", expand=True, padx=8, pady=(4, 8))
        viewport.rowconfigure(0, weight=1)
        viewport.columnconfigure(0, weight=1)

        self._main_canvas = tk.Canvas(
            viewport,
            bg=COLORS["bg"],
            highlightthickness=0,
            borderwidth=0,
        )
        v_scroll = ttk.Scrollbar(viewport, orient="vertical", command=self._main_canvas.yview)
        h_scroll = ttk.Scrollbar(viewport, orient="horizontal", command=self._main_canvas.xview)
        self._main_canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        self._main_canvas.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")

        outer = tk.Frame(self._main_canvas, bg=COLORS["bg"])
        self._main_window = self._main_canvas.create_window((0, 0), window=outer, anchor="nw")

        def _sync_scroll_region(_event=None) -> None:
            self._main_canvas.configure(scrollregion=self._main_canvas.bbox("all"))

        def _resize_inner(event) -> None:
            self._main_canvas.itemconfigure(self._main_window, width=max(event.width, 1500))
            _sync_scroll_region()

        outer.bind("<Configure>", _sync_scroll_region)
        self._main_canvas.bind("<Configure>", _resize_inner)
        self._main_canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self._main_canvas.bind_all("<Shift-MouseWheel>", self._on_shift_mousewheel)

        outer.columnconfigure(0, weight=1, minsize=460)
        outer.columnconfigure(1, weight=1, minsize=460)
        outer.columnconfigure(2, weight=1, minsize=460)
        outer.rowconfigure(0, weight=0, minsize=310)
        outer.rowconfigure(1, weight=0, minsize=330)
        outer.rowconfigure(2, weight=0, minsize=230)
        outer.rowconfigure(3, weight=0, minsize=170)

        self._build_connection_panel(outer)
        self._build_control_panel(outer)
        self._build_target_panel(outer)
        self._build_telemetry_panel(outer)
        self._build_laser_graph_panel(outer)
        self._build_vision_panel(outer)
        self._build_safety_panel(outer)
        self._build_calibration_panel(outer)
        self._build_log_panel(outer)

    def _on_mousewheel(self, event) -> None:
        if hasattr(self, "_main_canvas"):
            self._main_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_shift_mousewheel(self, event) -> None:
        if hasattr(self, "_main_canvas"):
            self._main_canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")

    def _build_connection_panel(self, parent: tk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="BAĞLANTI", style="PanelBg.TLabelframe")
        frame.grid(row=0, column=0, padx=4, pady=4, sticky="nsew")
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="COM Port:").grid(row=0, column=0, sticky="w", padx=6, pady=3)
        self._combo_port = ttk.Combobox(frame, values=self._io.list_serial_ports(),
                                         width=16, state="readonly")
        self._combo_port.grid(row=0, column=1, sticky="ew", padx=6, pady=3)

        ttk.Label(frame, text="ESP32 IP:").grid(row=1, column=0, sticky="w", padx=6, pady=3)
        self._wifi_entry = ttk.Entry(frame, width=20)
        self._wifi_entry.insert(0, "192.168.4.1")
        self._wifi_entry.grid(row=1, column=1, sticky="ew", padx=6, pady=3)

        btn_frame = tk.Frame(frame, bg=COLORS["panel_bg"])
        btn_frame.grid(row=2, column=0, columnspan=2, pady=6)

        self._btn_serial = ttk.Button(btn_frame, text="🔌 Serial Bağlan",
                                       command=self._toggle_serial, style="TButton", width=16)
        self._btn_serial.pack(side="left", padx=3)

        self._btn_wifi = ttk.Button(btn_frame, text="📡 ESP32 Bağlan",
                                      command=self._toggle_wifi, style="TButton", width=16)
        self._btn_wifi.pack(side="left", padx=3)

        ttk.Button(btn_frame, text="⏹ Bağlantıyı Kes",
                    command=self._disconnect, style="Danger.TButton", width=14).pack(side="left", padx=3)

        ttk.Button(btn_frame, text="🔄 Portları Tara",
                    command=self._refresh_ports, style="TButton", width=14).pack(side="left", padx=3)

        ros_frame = tk.Frame(frame, bg=COLORS["panel_bg"])
        ros_frame.grid(row=3, column=0, columnspan=2, pady=(8, 2), sticky="ew")
        ros_frame.columnconfigure(1, weight=1)

        self._btn_ros = ttk.Button(ros_frame, text="🧪 ROS/Gazebo Bağlan",
                                    command=self._toggle_ros, style="TButton")
        self._btn_ros.pack(side="left", padx=3)

        self._ros_indicator = tk.Label(ros_frame, text="● ROS Kapalı",
                                        bg=COLORS["panel_bg"], fg=COLORS["text_dim"],
                                        font=(FONT_FAMILY, 8))
        self._ros_indicator.pack(side="left", padx=(6, 0))

        self._btn_stewart = ttk.Button(ros_frame, text="🛰️ Stewart Bağlan",
                                        command=self._toggle_stewart, style="TButton")
        self._btn_stewart.pack(side="left", padx=3)

        self._stewart_indicator = tk.Label(ros_frame, text="● Stewart Kapalı",
                                            bg=COLORS["panel_bg"], fg=COLORS["text_dim"],
                                            font=(FONT_FAMILY, 8))
        self._stewart_indicator.pack(side="left", padx=(6, 0))

    def _build_control_panel(self, parent: tk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="SİSTEM KONTROLÜ", style="PanelBg.TLabelframe")
        frame.grid(row=0, column=1, padx=4, pady=4, sticky="nsew")
        frame.columnconfigure(1, weight=1)

        self._btn_start = ttk.Button(frame, text="▶ SİSTEMİ BAŞLAT",
                                      command=self._cmd_start, style="Success.TButton")
        self._btn_start.grid(row=0, column=0, columnspan=2, pady=6, padx=10, sticky="ew")

        self._btn_stop = ttk.Button(frame, text="⏹ SİSTEMİ DURDUR",
                                     command=self._cmd_stop, style="TButton")
        self._btn_stop.grid(row=1, column=0, columnspan=2, pady=6, padx=10, sticky="ew")

        self._btn_home = ttk.Button(frame, text="🏠 HOMING YAP",
                                     command=self._cmd_home, style="TButton")
        self._btn_home.grid(row=2, column=0, columnspan=2, pady=6, padx=10, sticky="ew")

        self._btn_emergency = ttk.Button(frame, text="🚨 ACİL DURDURMA",
                                          command=self._cmd_emergency, style="Danger.TButton")
        self._btn_emergency.grid(row=3, column=0, columnspan=2, pady=6, padx=10, sticky="ew")

        sep = ttk.Separator(frame, orient="horizontal")
        sep.grid(row=4, column=0, columnspan=2, sticky="ew", pady=8, padx=10)

        ttk.Label(frame, text="Mod Seçimi:").grid(row=5, column=0, sticky="w", padx=10, pady=3)
        self._mode_var = tk.StringVar(value="auto")
        auto_rb = ttk.Radiobutton(frame, text="🔴 Otomatik", variable=self._mode_var,
                                   value="auto", command=self._cmd_set_mode)
        auto_rb.grid(row=5, column=1, sticky="w", padx=6, pady=3)
        manual_rb = ttk.Radiobutton(frame, text="🔵 Manuel", variable=self._mode_var,
                                     value="manual", command=self._cmd_set_mode)
        manual_rb.grid(row=6, column=1, sticky="w", padx=6, pady=3)

        ttk.Label(frame, text="", style="Status.TLabel").grid(row=7, column=0)  # spacer

        ttk.Label(frame, text="Hata Durumu:", style="Status.TLabel").grid(row=8, column=0, sticky="w", padx=10, pady=3)
        self._error_var = tk.StringVar(value="Yok")
        ttk.Label(frame, textvariable=self._error_var, style="ValueSmall.TLabel").grid(row=8, column=1, sticky="w", padx=6, pady=3)

    def _build_target_panel(self, parent: tk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="HEDEF VE KONUM", style="PanelBg.TLabelframe")
        frame.grid(row=0, column=2, padx=4, pady=4, sticky="nsew")
        frame.columnconfigure(1, weight=1)

        # ── BÖLÜM 1: GPS / Uydu Yönelimi ──────────────────────
        ttk.Label(frame, text="─── KISIM 1: GPS / Uydu Yönelimi ───",
                  style="Status.TLabel").grid(row=0, column=0, columnspan=2,
                                              sticky="w", padx=6, pady=(6, 2))
        ttk.Label(frame, text="⬇ Koordinatlarınızı girip uydu seçin, "
                  "hesapla'ya basın → size göre Az/El bulunsun",
                  style="Status.TLabel", wraplength=220).grid(
            row=1, column=0, columnspan=2, sticky="w", padx=6, pady=(0, 4))

        ttk.Label(frame, text="Uydu:").grid(row=2, column=0, sticky="w", padx=6, pady=2)
        self._sat_var = tk.StringVar(value="Türksat 5A")
        ttk.Combobox(frame, textvariable=self._sat_var,
                      values=list(SATELLITES.keys()), state="readonly", width=18).grid(
            row=2, column=1, sticky="ew", padx=6, pady=2)

        ttk.Label(frame, text="Enlem:").grid(row=3, column=0, sticky="w", padx=6, pady=2)
        self._lat_entry = ttk.Entry(frame, width=14)
        self._lat_entry.insert(0, "39.9208")
        self._lat_entry.grid(row=3, column=1, sticky="ew", padx=6, pady=2)

        ttk.Label(frame, text="Boylam:").grid(row=4, column=0, sticky="w", padx=6, pady=2)
        self._lon_entry = ttk.Entry(frame, width=14)
        self._lon_entry.insert(0, "32.8541")
        self._lon_entry.grid(row=4, column=1, sticky="ew", padx=6, pady=2)

        ttk.Button(frame, text="🎯  AZ/EL HESAPLA  →  Otomatik Açıları Bul",
                    command=self._calculate_target, style="TButton").grid(
            row=5, column=0, columnspan=2, pady=4, padx=10, sticky="ew")

        # Hesaplanan değerler — kutu içinde göster
        result_bg = tk.Frame(frame, bg=COLORS["entry_bg"], highlightbackground=COLORS["border"],
                             highlightthickness=1)
        result_bg.grid(row=6, column=0, columnspan=2, sticky="ew", padx=6, pady=4)

        tk.Label(result_bg, text="→ Hedef Azimuth:", bg=COLORS["entry_bg"],
                 fg=COLORS["text_dim"], font=(FONT_FAMILY, 9)).grid(row=0, column=0, sticky="w", padx=6, pady=2)
        self._calc_az_var = tk.StringVar(value="--- °")
        tk.Label(result_bg, textvariable=self._calc_az_var, bg=COLORS["entry_bg"],
                 fg=COLORS["warning"], font=(FONT_FAMILY, 11, "bold")).grid(row=0, column=1, sticky="w", padx=6, pady=2)

        tk.Label(result_bg, text="→ Hedef Elevasyon:", bg=COLORS["entry_bg"],
                 fg=COLORS["text_dim"], font=(FONT_FAMILY, 9)).grid(row=1, column=0, sticky="w", padx=6, pady=2)
        self._calc_el_var = tk.StringVar(value="--- °")
        tk.Label(result_bg, textvariable=self._calc_el_var, bg=COLORS["entry_bg"],
                 fg=COLORS["warning"], font=(FONT_FAMILY, 11, "bold")).grid(row=1, column=1, sticky="w", padx=6, pady=2)

        tk.Label(result_bg, text="(GPS'iniz + uydu boylamına göre hesaplanır)",
                 bg=COLORS["entry_bg"], fg=COLORS["text_dim"],
                 font=(FONT_FAMILY, 7)).grid(row=2, column=0, columnspan=2, pady=(0, 2))

        # ── BÖLÜM 2: Manuel Açı Girişi ─────────────────────────
        sep1 = ttk.Separator(frame, orient="horizontal")
        sep1.grid(row=7, column=0, columnspan=2, sticky="ew", pady=6, padx=10)

        ttk.Label(frame, text="─── KISIM 2: Manuel Açı Girişi ───",
                  style="Status.TLabel").grid(row=8, column=0, columnspan=2,
                                              sticky="w", padx=6, pady=(2, 2))
        ttk.Label(frame, text="⬇ Açıyı elle yazıp Hedef Gönder'e basın → "
                  "Teensy'ye iletilir",
                  style="Status.TLabel", wraplength=220).grid(
            row=9, column=0, columnspan=2, sticky="w", padx=6, pady=(0, 4))

        ttk.Label(frame, text="Azimuth (°)  (0-360):").grid(row=10, column=0, sticky="w", padx=6, pady=2)
        self._az_entry = ttk.Entry(frame, width=14)
        self._az_entry.insert(0, "120.0")
        self._az_entry.grid(row=10, column=1, sticky="ew", padx=6, pady=2)

        ttk.Label(frame, text="Elevasyon (°)  (0-90):").grid(row=11, column=0, sticky="w", padx=6, pady=2)
        self._el_entry = ttk.Entry(frame, width=14)
        self._el_entry.insert(0, "30.0")
        self._el_entry.grid(row=11, column=1, sticky="ew", padx=6, pady=2)

        ttk.Button(frame, text="📡  HEDEF GÖNDER  →  Teensy'ye Açıları İlet",
                    command=self._send_target, style="Accent.TButton").grid(
            row=12, column=0, columnspan=2, pady=6, padx=10, sticky="ew")
        ttk.Label(frame, text="Bu açılar Teensy'ye gider, motorlar hedefe kilitlenir",
                  style="Status.TLabel").grid(row=13, column=0, columnspan=2,
                                              sticky="w", padx=6, pady=(0, 4))

    def _build_telemetry_panel(self, parent: tk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="CANLI TELEMETRİ", style="PanelBg.TLabelframe")
        frame.grid(row=1, column=0, padx=4, pady=4, sticky="nsew")
        frame.columnconfigure(1, weight=1)

        rows_data = [
            ("Azimuth (Gerçek):", "az_actual", "0.00°"),
            ("Elevasyon (Gerçek):", "el_actual", "0.00°"),
            ("Azimuth (Hedef):", "az_target", "0.00°"),
            ("Elevasyon (Hedef):", "el_target", "0.00°"),
            ("Hata (Boresight):", "error", "0.00°"),
            ("Roll:", "roll", "0.00°"),
            ("Pitch:", "pitch", "0.00°"),
            ("Yaw:", "yaw", "0.00°"),
            ("Kilit Durumu:", "lock", "⬜ KİLİTSİZ"),
            ("Lazer X Sapma:", "laser_x", "0.00 px"),
            ("Lazer Y Sapma:", "laser_y", "0.00 px"),
            ("RSSI:", "rssi", "-100 dBm"),
        ]

        self._tel_vars: dict[str, tk.StringVar] = {}
        for i, (label, key, default) in enumerate(rows_data):
            ttk.Label(frame, text=label, style="Status.TLabel").grid(
                row=i, column=0, sticky="w", padx=8, pady=2)
            var = tk.StringVar(value=default)
            self._tel_vars[key] = var
            lbl = ttk.Label(frame, textvariable=var, style="ValueSmall.TLabel")
            lbl.grid(row=i, column=1, sticky="w", padx=8, pady=2)

        self._lock_indicator = tk.Canvas(frame, width=20, height=20,
                                          bg=COLORS["panel_bg"], highlightthickness=0)
        self._lock_indicator.grid(row=8, column=2, padx=(0, 8), pady=2)
        self._lock_dot = self._lock_indicator.create_oval(2, 2, 18, 18,
                                                           fill=COLORS["text_dim"], outline="")

    def _build_laser_graph_panel(self, parent: tk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="LAZER OFSET GRAFİĞİ", style="PanelBg.TLabelframe")
        frame.grid(row=1, column=1, columnspan=2, padx=4, pady=4, sticky="nsew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        self._fig = Figure(dpi=80, facecolor=COLORS["panel_bg"])
        self._fig.subplots_adjust(left=0.08, right=0.95, top=0.92, bottom=0.08)
        self._ax = self._fig.add_subplot(111)
        self._ax.set_facecolor("#0d1b2a")
        self._ax.set_xlim(-3, 3)
        self._ax.set_ylim(-3, 3)
        self._ax.set_aspect("equal")
        self._ax.grid(True, alpha=0.15, color="white", linewidth=0.5)
        self._ax.axhline(0, color="white", linewidth=0.5, alpha=0.3)
        self._ax.axvline(0, color="white", linewidth=0.5, alpha=0.3)
        self._ax.set_xlabel("X (px)", color=COLORS["text_dim"], fontsize=8)
        self._ax.set_ylabel("Y (px)", color=COLORS["text_dim"], fontsize=8)
        self._ax.tick_params(colors=COLORS["text_dim"], labelsize=7)

        # Target crosshair
        self._ax.plot(0, 0, marker="+", color=COLORS["success"], markersize=12,
                       linewidth=2, label="Hedef")
        # Laser dot
        (self._laser_dot,) = self._ax.plot(0, 0, marker="o", color=COLORS["error"],
                                            markersize=10, label="Lazer")
        (self._laser_plot_line,) = self._ax.plot([], [], color=COLORS["accent"],
                                                 alpha=0.3, linewidth=0.8)
        # Lock radius circle
        self._lock_zone = self._ax.add_patch(
            mpatches.Circle((0, 0), 1.0, fill=False, edgecolor=COLORS["success"],
                            linestyle="--", linewidth=1, alpha=0.5)
        )
        self._ax.legend(loc="upper right", fontsize=7, facecolor=COLORS["panel_bg"],
                         edgecolor=COLORS["border"], labelcolor=COLORS["text"])

        self._canvas = FigureCanvasTkAgg(self._fig, master=frame)
        self._canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

    def _build_vision_panel(self, parent: tk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="HEDEF TAKİP ALGORİTMASI", style="PanelBg.TLabelframe")
        frame.grid(row=2, column=0, padx=4, pady=4, sticky="nsew")
        frame.columnconfigure(1, weight=1)

        self._vision_vars: dict[str, tk.StringVar] = {}
        rows = [
            ("Takip Durumu:", "tracking", "HEDEF YOK"),
            ("Hedef Tespit:", "detected", "Yok"),
            ("Merkez Hatası:", "center_error", "0.0 px, 0.0 px"),
            ("BBox:", "bbox", "--"),
            ("Güven:", "confidence", "0.00"),
            ("Kayıp Frame:", "lost_frames", "0"),
            ("FPS:", "fps", "Video 0.0 / Vision 0.0"),
        ]
        for row, (label, key, value) in enumerate(rows):
            ttk.Label(frame, text=label, style="Status.TLabel").grid(
                row=row, column=0, sticky="w", padx=6, pady=2)
            var = tk.StringVar(value=value)
            self._vision_vars[key] = var
            ttk.Label(frame, textvariable=var, style="ValueSmall.TLabel", wraplength=330).grid(
                row=row, column=1, sticky="w", padx=6, pady=2)

    def _build_safety_panel(self, parent: tk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="OPERASYON GÜVENLİĞİ VE KAYIT", style="PanelBg.TLabelframe")
        frame.grid(row=2, column=1, padx=4, pady=4, sticky="nsew")
        frame.columnconfigure(1, weight=1)

        self._safety_vars: dict[str, tk.StringVar] = {}
        rows = [
            ("Fail-safe:", "failsafe", "Normal"),
            ("Telemetri Hz:", "telemetry_hz", "0.0 Hz"),
            ("ACK Gecikmesi:", "ack", "-- ms"),
            ("Paket Kaybı:", "packet_loss", "0"),
            ("Oturum Kaydı:", "recording", str(self._run_dir)),
        ]
        for row, (label, key, value) in enumerate(rows):
            ttk.Label(frame, text=label, style="Status.TLabel").grid(
                row=row, column=0, sticky="w", padx=6, pady=2)
            var = tk.StringVar(value=value)
            self._safety_vars[key] = var
            ttk.Label(frame, textvariable=var, style="ValueSmall.TLabel", wraplength=330).grid(
                row=row, column=1, sticky="w", padx=6, pady=2)

    def _build_calibration_panel(self, parent: tk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="KALİBRASYON", style="PanelBg.TLabelframe")
        frame.grid(row=2, column=2, padx=4, pady=4, sticky="nsew")
        frame.columnconfigure(1, weight=1)

        self._calib_entries: dict[str, ttk.Entry] = {}
        rows = [
            ("Kamera CX:", "frame_cx", "160.0"),
            ("Kamera CY:", "frame_cy", "120.0"),
            ("Lazer Offset X:", "offset_x", "0.0"),
            ("Lazer Offset Y:", "offset_y", "0.0"),
            ("Lock Eşiği px:", "lock_px", "20.0"),
        ]
        for row, (label, key, value) in enumerate(rows):
            ttk.Label(frame, text=label, style="Status.TLabel").grid(
                row=row, column=0, sticky="w", padx=6, pady=2)
            entry = ttk.Entry(frame, width=12)
            entry.insert(0, value)
            entry.grid(row=row, column=1, sticky="ew", padx=6, pady=2)
            self._calib_entries[key] = entry

        ttk.Button(frame, text="Kalibrasyonu Uygula",
                   command=self._apply_calibration, style="TButton").grid(
            row=len(rows), column=0, columnspan=2, sticky="ew", padx=6, pady=5)

    def _build_log_panel(self, parent: tk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="SİSTEM MESAJLARI", style="PanelBg.TLabelframe")
        frame.grid(row=3, column=0, columnspan=3, padx=4, pady=4, sticky="nsew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        self._log_text = tk.Text(frame, height=6, bg="#0d1b2a", fg=COLORS["text"],
                                  font=("Consolas", 9), insertbackground=COLORS["text"],
                                  relief="flat", borderwidth=0, wrap="word")
        self._log_text.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self._log_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self._log_text.configure(yscrollcommand=scrollbar.set)

        self._log("Mergen Terminal Kontrol Sistemi başlatıldı.")
        self._log("Haberleşme: Teensy (Serial) veya ESP32 (WiFi) üzerinden.")
        self._log("Sistem başlatmak için: Önce bağlan → sonra SİSTEMİ BAŞLAT.")

    def _log(self, msg: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        self._log_text.insert("end", f"[{timestamp}] {msg}\n")
        self._log_text.see("end")
        self._write_jsonl("events.jsonl", {"event": "ui_log", "message": msg})

    def _apply_calibration(self) -> None:
        try:
            self._state.frame_center_x = float(self._calib_entries["frame_cx"].get())
            self._state.frame_center_y = float(self._calib_entries["frame_cy"].get())
            self._calib_offset_x = float(self._calib_entries["offset_x"].get())
            self._calib_offset_y = float(self._calib_entries["offset_y"].get())
            lock_px = float(self._calib_entries["lock_px"].get())
        except ValueError:
            messagebox.showerror("Kalibrasyon Hatası", "Kalibrasyon değerleri sayısal olmalı.")
            return
        self._send(CommandMessage(action="set_param", params={
            "frame_cx": self._state.frame_center_x,
            "frame_cy": self._state.frame_center_y,
            "laser_offset_x": self._calib_offset_x,
            "laser_offset_y": self._calib_offset_y,
            "lock_threshold_px": lock_px,
        }))
        self._write_jsonl("config_snapshot.jsonl", {
            "event": "calibration_applied",
            "frame_cx": self._state.frame_center_x,
            "frame_cy": self._state.frame_center_y,
            "laser_offset_x": self._calib_offset_x,
            "laser_offset_y": self._calib_offset_y,
            "lock_threshold_px": lock_px,
        })
        self._log("Kalibrasyon uygulandı: hedef merkezi kamera merkezine göre takip edilecek.")

    # ─── COMMANDS ──────────────────────────────────────────────

    def _send(self, cmd: CommandMessage) -> None:
        has_connection = self._io.is_connected or self._ros_mode
        if not has_connection and not self._simulation_mode:
            messagebox.showwarning("Bağlantı Yok", "Önce Teensy/ESP32 veya ROS/Gazebo'ya bağlanın.")
            return
        self._cmd_seq += 1
        cmd.seq = self._cmd_seq
        self._pending_commands[cmd.seq] = (cmd.action, time.time())
        self._write_jsonl("commands.jsonl", {
            "direction": "gui_to_controller",
            "seq": cmd.seq,
            "action": cmd.action,
            "mode": cmd.mode,
            "az": cmd.az,
            "el": cmd.el,
            "params": cmd.params,
        })
        if self._simulation_mode:
            self._log(f"[SIM] Komut: {cmd.action.upper()} {cmd.mode or ''}")
            self._state.ack_latency_ms = 0.0
        if self._ros_mode:
            self._ros.publish_command(cmd.action, mode=cmd.mode, az=cmd.az, el=cmd.el)
        if self._io.is_connected:
            self._io.send_command(cmd)

    def _cmd_start(self) -> None:
        self._log("Sistem başlatılıyor...")
        self._start_time = time.time()
        self._send(CommandMessage(action="start"))
        if self._simulation_mode:
            self._state.mode = SystemMode.IDLE
            self._update_ui()

    def _cmd_stop(self) -> None:
        self._log("Sistem durduruluyor...")
        self._send(CommandMessage(action="stop"))
        if self._simulation_mode:
            self._state.mode = SystemMode.POWER_OFF
            self._update_ui()

    def _cmd_home(self) -> None:
        self._log("Homing başlatılıyor...")
        self._send(CommandMessage(action="home"))

    def _cmd_emergency(self) -> None:
        self._log("🚨 ACİL DURDURMA!")
        self._send(CommandMessage(action="emergency_stop"))
        if self._simulation_mode:
            self._state.mode = SystemMode.EMERGENCY_STOP
            self._update_ui()

    def _cmd_set_mode(self) -> None:
        mode = self._mode_var.get()
        self._send(CommandMessage(action="set_mode", mode=mode))
        if self._ros_mode:
            self._ros.publish_mode(mode)
        if self._simulation_mode:
            self._state.mode = SystemMode.AUTO_TRACKING if mode == "auto" else SystemMode.MANUAL
            self._log(f"Mod: {'OTOMATIK' if mode == 'auto' else 'MANUEL'}")
            self._update_ui()

    def _calculate_target(self) -> None:
        try:
            lat = float(self._lat_entry.get())
            lon = float(self._lon_entry.get())
            sat_lon = SATELLITES[self._sat_var.get()]
            az, el = calculate_look_angles(lat, lon, sat_lon)
        except (ValueError, KeyError) as e:
            messagebox.showerror("Hatalı Giriş", f"Geçersiz değer: {e}")
            return

        self._calc_az_var.set(f"{az:.2f}°")
        self._calc_el_var.set(f"{el:.2f}°")
        self._az_entry.delete(0, "end")
        self._az_entry.insert(0, f"{az:.2f}")
        self._el_entry.delete(0, "end")
        self._el_entry.insert(0, f"{el:.2f}")
        self._log(f"Hedef hesaplandı: Az={az:.2f}°, El={el:.2f}° ({self._sat_var.get()})")

    def _send_target(self) -> None:
        try:
            az = float(self._az_entry.get()) % 360.0
            el = min(90.0, max(0.0, float(self._el_entry.get())))
        except ValueError:
            messagebox.showerror("Hatalı Giriş", "Azimuth ve elevasyon sayısal olmalı.")
            return
        self._send(CommandMessage(action="set_target", az=az, el=el))
        if self._ros_mode:
            self._ros.publish_target(az, el)
        self._state.az_target = az
        self._state.el_target = el
        self._log(f"Hedef gönderildi: Az={az:.2f}°, El={el:.2f}°")

    # ─── CONNECTION ────────────────────────────────────────────

    def _toggle_serial(self) -> None:
        if self._io.active_path and self._io.active_path.startswith("Serial"):
            self._disconnect()
            return
        port = self._combo_port.get()
        if not port:
            messagebox.showwarning("Port Seçilmedi", "Lütfen bir COM portu seçin.")
            return
        ok = self._io.connect_serial(port)
        if ok:
            self._state.connection_ok = True
            self._state.connection_type = f"Serial:{port}"
            self._simulation_mode = False
            self._sim_indicator.configure(text="🔴 GERÇEK DONANIM", fg=COLORS["error"])
            self._log(f"Serial bağlandı: {port}")
        self._update_connection_ui()

    def _toggle_wifi(self) -> None:
        if self._io.active_path and self._io.active_path.startswith("WiFi"):
            self._disconnect()
            return
        host = self._wifi_entry.get().strip()
        if not host:
            messagebox.showwarning("IP Girilmedi", "ESP32 IP adresini girin.")
            return
        ok = self._io.connect_wifi(host)
        if ok:
            self._state.connection_ok = True
            self._state.connection_type = f"WiFi:{host}"
            self._simulation_mode = False
            self._sim_indicator.configure(text="🔴 GERÇEK DONANIM", fg=COLORS["error"])
            self._log(f"ESP32 bağlandı: {host}")
        self._update_connection_ui()

    def _disconnect(self) -> None:
        self._io.disconnect()
        self._state.connection_ok = False
        self._state.connection_type = None
        self._simulation_mode = True
        self._sim_indicator.configure(text="🔷 SİMÜLASYON", fg=COLORS["warning"])
        self._log("Bağlantı kapatıldı, simülasyon moduna geçildi.")
        self._update_connection_ui()

    def _refresh_ports(self) -> None:
        ports = self._io.list_serial_ports()
        self._combo_port.configure(values=ports)
        if ports:
            self._combo_port.set(ports[0])
        self._log(f"Portlar tarandı: {len(ports)} port bulundu.")

    def _toggle_ros(self) -> None:
        if self._ros_mode:
            if self._stewart_mode:
                self._toggle_stewart()
            self._ros.disable()
            self._ros_mode = False
            self._simulation_mode = True
            self._ros_indicator.configure(text="● ROS Kapalı", fg=COLORS["text_dim"])
            self._btn_ros.configure(text="🧪 ROS/Gazebo Bağlan")
            self._sim_indicator.configure(text="🔷 SİMÜLASYON", fg=COLORS["warning"])
            self._log("ROS/Gazebo bağlantısı kapatıldı.")
        else:
            if self._stewart_mode:
                self._toggle_stewart()
            self._ros.bridge_mode = "mergen"
            ok = self._ros.enable()
            if ok:
                self._ros_mode = True
                self._simulation_mode = False
                self._ros_indicator.configure(text="● ROS Bağlı", fg=COLORS["success"])
                self._btn_ros.configure(text="🧪 ROS/Gazebo Kes")
                self._sim_indicator.configure(text="🟢 GAZEBO SİMÜLASYON", fg=COLORS["success"])
                self._log("ROS/Gazebo bridge aktif. Telemetri bekleniyor...")
            else:
                self._log("ROS/Gazebo bağlantısı kurulamadı. rclpy eksik olabilir.")
        self._update_connection_ui()

    def _toggle_stewart(self) -> None:
        if self._stewart_mode:
            self._ros.bridge_mode = "mergen"
            self._stewart_mode = False
            self._simulation_mode = True
            self._stewart_indicator.configure(text="● Stewart Kapalı", fg=COLORS["text_dim"])
            self._btn_stewart.configure(text="🛰️ Stewart Bağlan")
            if not self._ros_mode:
                self._ros.disable()
                self._sim_indicator.configure(text="🔷 SİMÜLASYON", fg=COLORS["warning"])
            else:
                self._sim_indicator.configure(text="🟢 GAZEBO SİMÜLASYON", fg=COLORS["success"])
            self._log("Stewart bridge kapatıldı.")
        else:
            if self._ros_mode:
                self._ros.bridge_mode = "stewart"
            else:
                self._ros.bridge_mode = "stewart"
                ok = self._ros.enable()
                if not ok:
                    self._log("Stewart bağlantısı kurulamadı. rclpy eksik olabilir.")
                    return
                self._ros_mode = True
                self._ros_indicator.configure(text="● ROS Bağlı", fg=COLORS["success"])
                self._btn_ros.configure(text="🧪 ROS/Gazebo Kes")
            self._stewart_mode = True
            self._simulation_mode = False
            self._stewart_indicator.configure(text="● Stewart Bağlı", fg=COLORS["accent"])
            self._btn_stewart.configure(text="🛰️ Stewart Kes")
            self._sim_indicator.configure(text="🛰️ STEWART PLATFORM", fg=COLORS["accent"])
            self._log("Stewart bridge aktif. satellite_bridge üzerinden 100Hz PID çalışıyor.")
        self._update_connection_ui()

    def _update_connection_ui(self) -> None:
        if self._state.connection_ok:
            self._conn_indicator.itemconfig(self._conn_dot, fill=COLORS["success"])
            self._conn_label.configure(text=self._state.connection_status, fg=COLORS["success"])
        else:
            self._conn_indicator.itemconfig(self._conn_dot, fill=COLORS["text_dim"])
            self._conn_label.configure(text="Bağlı Değil", fg=COLORS["text_dim"])

    # ─── CALLBACKS ─────────────────────────────────────────────

    def _queue_event(self, kind: str, payload: object) -> None:
        try:
            self._event_queue.put_nowait((kind, payload))
        except queue.Full:
            try:
                self._event_queue.get_nowait()
                self._event_queue.put_nowait((kind, payload))
            except queue.Empty:
                pass

    def _on_raw_message(self, msg: dict) -> None:
        self._queue_event("raw", msg)

    def _on_telemetry(self, tel: TelemetryData) -> None:
        self._queue_event("telemetry", tel)

    def _apply_telemetry(self, tel: TelemetryData) -> None:
        self._last_tel_time = time.time()
        self._tel_count_since_rate += 1
        if tel.seq and self._state.last_packet_seq and tel.seq > self._state.last_packet_seq + 1:
            self._state.packet_loss_count += tel.seq - self._state.last_packet_seq - 1
        if tel.seq:
            self._state.last_packet_seq = tel.seq
        self._state.mode = SystemMode(tel.state) if tel.state in [e.value for e in SystemMode] else self._state.mode
        self._state.az_actual = tel.az_actual
        self._state.el_actual = tel.el_actual
        self._state.az_target = tel.az_target
        self._state.el_target = tel.el_target
        self._state.laser_error_x = tel.laser_error_x
        self._state.laser_error_y = tel.laser_error_y
        self._state.roll = tel.roll
        self._state.pitch = tel.pitch
        self._state.yaw = tel.yaw
        self._state.locked = tel.locked
        self._state.gps_lat = tel.gps_lat
        self._state.gps_lon = tel.gps_lon
        self._state.uptime_ms = tel.uptime_ms
        self._state.errors = tel.errors
        self._state.rssi = tel.rssi
        self._state.target_detected = tel.target_detected
        self._state.target_center_x = tel.target_center_x
        self._state.target_center_y = tel.target_center_y
        self._state.frame_center_x = tel.frame_center_x or self._state.frame_center_x
        self._state.frame_center_y = tel.frame_center_y or self._state.frame_center_y
        self._state.bbox_x = tel.bbox_x
        self._state.bbox_y = tel.bbox_y
        self._state.bbox_w = tel.bbox_w
        self._state.bbox_h = tel.bbox_h
        self._state.confidence = tel.confidence
        self._state.vision_fps = tel.vision_fps
        self._state.video_fps = tel.video_fps
        self._state.lost_frames = tel.lost_frames
        self._update_tracking_state()
        self._write_jsonl("telemetry.jsonl", {"seq": tel.seq, "state": tel.state,
                                               "az_act": tel.az_actual, "el_act": tel.el_actual,
                                               "target_detected": tel.target_detected,
                                               "laser_x": self._state.laser_error_x,
                                               "laser_y": self._state.laser_error_y,
                                               "locked": tel.locked})

    def _on_comm_error(self, msg: str) -> None:
        self._queue_event("error", msg)

    def _on_ros_telemetry(self, tel: RosTelemetry) -> None:
        self._queue_event("ros", tel)

    def _apply_ros_telemetry(self, tel: RosTelemetry) -> None:
        self._last_tel_time = time.time()
        self._tel_count_since_rate += 1
        self._state.connection_ok = True
        self._state.az_actual = tel.az_actual
        self._state.el_actual = tel.el_actual
        self._state.az_target = tel.az_target
        self._state.el_target = tel.el_target
        self._state.roll = tel.roll
        self._state.pitch = tel.pitch
        self._state.yaw = tel.yaw
        self._state.locked = tel.locked
        self._state.errors = tel.errors
        self._state.rssi = tel.rssi
        mode_map = {
            "IDLE": SystemMode.IDLE,
            "STARTING": SystemMode.STARTING,
            "AUTO_TRACKING": SystemMode.AUTO_TRACKING,
            "MANUAL": SystemMode.MANUAL,
            "HOMING": SystemMode.HOMING,
            "EMERGENCY": SystemMode.EMERGENCY_STOP,
            "ERROR": SystemMode.ERROR,
        }
        self._state.mode = mode_map.get(tel.mode.upper(), self._state.mode)

    def _process_event_queue(self) -> None:
        while True:
            try:
                kind, payload = self._event_queue.get_nowait()
            except queue.Empty:
                break
            if kind == "telemetry":
                self._apply_telemetry(payload)  # type: ignore[arg-type]
            elif kind == "ros":
                self._apply_ros_telemetry(payload)  # type: ignore[arg-type]
            elif kind == "error":
                self._log(f"⚠ {payload}")
            elif kind == "raw":
                self._handle_raw_message(payload)  # type: ignore[arg-type]

    def _handle_raw_message(self, msg: dict) -> None:
        if msg.get("type") != "ack":
            return
        ack_seq = msg.get("seq") or msg.get("ack_seq")
        if ack_seq in self._pending_commands:
            action, sent_at = self._pending_commands.pop(ack_seq)
            latency_ms = (time.time() - sent_at) * 1000.0
            self._state.ack_latency_ms = latency_ms
            self._write_jsonl("commands.jsonl", {
                "direction": "controller_to_gui",
                "seq": ack_seq,
                "action": action,
                "ack_latency_ms": round(latency_ms, 2),
            })

    # ─── POLLING (UI update) ──────────────────────────────────

    def _poll_state(self) -> None:
        self._process_event_queue()
        self._update_rate_metrics()
        self._update_failsafe()
        if self._ros_mode:
            if not self._ros.connected:
                self._state.connection_ok = False
                if self._ros_indicator.cget("fg") != COLORS["error"]:
                    self._ros_indicator.configure(text="● ROS HATA", fg=COLORS["error"])
            else:
                tel = self._ros.last_telemetry
                if tel.timestamp > 0:
                    self._on_ros_telemetry(tel)
                if time.time() - self._last_tel_time > 3.0:
                    self._state.connection_ok = False
        elif self._simulation_mode:
            self._simulate_update()
        self._update_ui()
        self.after(100, self._poll_state)

    def _update_rate_metrics(self) -> None:
        now = time.time()
        elapsed = now - self._last_tel_counter_time
        if elapsed >= 1.0:
            self._state.telemetry_rate_hz = self._tel_count_since_rate / elapsed
            self._tel_count_since_rate = 0
            self._last_tel_counter_time = now

    def _update_tracking_state(self) -> None:
        now = time.time()
        s = self._state
        if s.target_detected:
            s.tracking_mode = TrackingMode.TRACKING
            s.last_target_x = s.target_center_x
            s.last_target_y = s.target_center_y
            s.last_target_time = now
            frame_cx = s.frame_center_x or float(self._calib_entries["frame_cx"].get())
            frame_cy = s.frame_center_y or float(self._calib_entries["frame_cy"].get())
            s.laser_error_px = s.target_center_x - frame_cx - self._calib_offset_x
            s.laser_error_py = s.target_center_y - frame_cy - self._calib_offset_y
            s.laser_error_x = s.laser_error_px / 50.0
            s.laser_error_y = s.laser_error_py / 50.0
            try:
                lock_px = float(self._calib_entries["lock_px"].get())
            except ValueError:
                lock_px = 20.0
            s.locked = abs(s.laser_error_px) <= lock_px and abs(s.laser_error_py) <= lock_px
            return

        missing_for = now - s.last_target_time if s.last_target_time else 999.0
        if s.lost_frames < self._lost_frame_hold_threshold and missing_for <= self._hold_last_seconds:
            s.tracking_mode = TrackingMode.HOLD_LAST
        elif s.lost_frames >= self._lost_frame_search_threshold or missing_for > self._hold_last_seconds:
            s.tracking_mode = TrackingMode.SEARCHING
        else:
            s.tracking_mode = TrackingMode.NO_TARGET

    def _update_failsafe(self) -> None:
        if self._simulation_mode or not (self._io.is_connected or self._ros_mode):
            return
        if not self._last_tel_time:
            return
        elapsed = time.time() - self._last_tel_time
        action = "normal"
        if elapsed > self._telemetry_timeout_lost:
            action = "telemetry_lost_laser_off"
        elif elapsed > self._telemetry_timeout_hold:
            action = "telemetry_hold_last"
        elif elapsed > self._telemetry_timeout_warning:
            action = "telemetry_warning"

        if action == self._last_failsafe_action:
            return
        self._last_failsafe_action = action
        if action == "telemetry_hold_last":
            self._state.tracking_mode = TrackingMode.HOLD_LAST
            self._send(CommandMessage(action="safe_hold", params={"reason": "telemetry_timeout"}))
            self._log("Fail-safe: telemetri gecikti, son konumda bekleme komutu gönderildi.")
        elif action == "telemetry_lost_laser_off":
            self._state.tracking_mode = TrackingMode.SEARCHING
            self._send(CommandMessage(action="laser_off", params={"reason": "telemetry_lost"}))
            self._log("Fail-safe: telemetri kayıp, lazer kapatma komutu gönderildi.")
        elif action == "telemetry_warning":
            self._log("Fail-safe uyarı: telemetri gecikmesi algılandı.")

    def _simulate_update(self) -> None:
        if self._state.mode == SystemMode.POWER_OFF:
            return
        t = time.time()
        dt = t - self._start_time if self._start_time > 0 else 0
        self._state.uptime_seconds = int(dt)

        if self._state.mode in (SystemMode.AUTO_TRACKING, SystemMode.MANUAL):
            import math
            phase = 2 * math.pi * dt / 15.0
            target_az = float(self._az_entry.get()) if self._az_entry.get() else 120.0
            target_el = float(self._el_entry.get()) if self._el_entry.get() else 30.0

            self._state.az_target = target_az
            self._state.el_target = target_el

            convergence = min(1.0, dt / 4.0)
            noise_x = 0.15 * math.sin(phase * 1.3)
            noise_y = 0.12 * math.cos(phase * 1.7)

            self._state.az_actual = target_az + (1.0 - convergence) * 5.0 * math.sin(phase * 0.5) + noise_x
            self._state.el_actual = target_el + (1.0 - convergence) * 3.0 * math.cos(phase * 0.4) + noise_y

            self._state.laser_error_x = 2.0 * (1.0 - convergence) * math.sin(phase * 0.7) + 0.1 * noise_x
            self._state.laser_error_y = 2.0 * (1.0 - convergence) * math.cos(phase * 0.9) + 0.1 * noise_y
            self._state.laser_error_px = self._state.laser_error_x * 50
            self._state.laser_error_py = self._state.laser_error_y * 50
            self._state.frame_center_x = float(self._calib_entries["frame_cx"].get())
            self._state.frame_center_y = float(self._calib_entries["frame_cy"].get())
            self._state.target_detected = int(dt) % 18 < 14
            if self._state.target_detected:
                self._state.target_center_x = self._state.frame_center_x + self._state.laser_error_px
                self._state.target_center_y = self._state.frame_center_y + self._state.laser_error_py
                self._state.bbox_x = self._state.target_center_x - 30
                self._state.bbox_y = self._state.target_center_y - 20
                self._state.bbox_w = 60
                self._state.bbox_h = 40
                self._state.confidence = 0.82 + 0.08 * math.sin(phase)
                self._state.lost_frames = 0
            else:
                self._state.lost_frames += 1
            self._state.video_fps = 30.0
            self._state.vision_fps = 25.0
            self._update_tracking_state()

            self._state.error = (self._state.laser_error_x ** 2 + self._state.laser_error_y ** 2) ** 0.5
            self._state.locked = self._state.error < 1.0

            self._state.roll = 1.5 * math.sin(phase * 0.3)
            self._state.pitch = 1.2 * math.cos(phase * 0.25)
            self._state.yaw = 0.5 * math.sin(phase * 0.1)

            self._state.rssi = -80 + int(10 * math.sin(phase * 0.05))

    def _update_ui(self) -> None:
        s = self._state

        # Connection
        self._update_connection_ui()

        # Status
        mode = s.mode_name
        status_colors = {
            "KAPALI": COLORS["text_dim"],
            "BEKLEMEDE": COLORS["warning"],
            "OTOMATIK": COLORS["success"],
            "MANUEL": COLORS["accent"],
            "HOMING": COLORS["warning"],
            "ACIL DURUM": COLORS["error"],
            "HATA": COLORS["error"],
        }
        color = status_colors.get(mode, COLORS["text_dim"])
        self._status_label.configure(text=f"{'●' if mode != 'KAPALI' else '○'} {mode}", fg=color)

        # Uptime
        if s.uptime_seconds > 0:
            h, rem = divmod(s.uptime_seconds, 3600)
            m, sec = divmod(rem, 60)
            self._uptime_label.configure(text=f"Süre: {h:02d}:{m:02d}:{sec:02d}")

        # Error
        self._error_var.set(s.error_description)

        # Telemetry
        self._tel_vars["az_actual"].set(f"{s.az_actual:.2f}°")
        self._tel_vars["el_actual"].set(f"{s.el_actual:.2f}°")
        self._tel_vars["az_target"].set(f"{s.az_target:.2f}°")
        self._tel_vars["el_target"].set(f"{s.el_target:.2f}°")
        self._tel_vars["error"].set(f"{s.boresight_error:.3f}°")
        self._tel_vars["roll"].set(f"{s.roll:.2f}°")
        self._tel_vars["pitch"].set(f"{s.pitch:.2f}°")
        self._tel_vars["yaw"].set(f"{s.yaw:.2f}°")
        self._tel_vars["laser_x"].set(f"{s.laser_error_px:.1f} px")
        self._tel_vars["laser_y"].set(f"{s.laser_error_py:.1f} px")
        self._tel_vars["rssi"].set(f"{s.rssi} dBm")

        # Vision/state-machine status. HuskyLens tracks only the target;
        # laser error is derived from target center minus calibrated camera center.
        self._vision_vars["tracking"].set(s.tracking_mode_name)
        self._vision_vars["detected"].set("Var" if s.target_detected else "Yok")
        self._vision_vars["center_error"].set(f"{s.laser_error_px:.1f} px, {s.laser_error_py:.1f} px")
        if s.bbox_w > 0 and s.bbox_h > 0:
            self._vision_vars["bbox"].set(
                f"x={s.bbox_x:.0f}, y={s.bbox_y:.0f}, w={s.bbox_w:.0f}, h={s.bbox_h:.0f}")
        else:
            self._vision_vars["bbox"].set("--")
        self._vision_vars["confidence"].set(f"{s.confidence:.2f}")
        self._vision_vars["lost_frames"].set(str(s.lost_frames))
        self._vision_vars["fps"].set(f"Video {s.video_fps:.1f} / Vision {s.vision_fps:.1f}")

        self._safety_vars["failsafe"].set(self._last_failsafe_action)
        self._safety_vars["telemetry_hz"].set(f"{s.telemetry_rate_hz:.1f} Hz")
        self._safety_vars["ack"].set(f"{s.ack_latency_ms:.1f} ms" if s.ack_latency_ms >= 0 else "-- ms")
        self._safety_vars["packet_loss"].set(str(s.packet_loss_count))

        if s.locked:
            self._tel_vars["lock"].set("🔒 KİLİTLİ")
            self._lock_indicator.itemconfig(self._lock_dot, fill=COLORS["success"])
        else:
            self._tel_vars["lock"].set("🔓 KİLİTSİZ")
            self._lock_indicator.itemconfig(self._lock_dot, fill=COLORS["error"])

        # Laser graph
        self._laser_history_x.append(s.laser_error_x)
        self._laser_history_y.append(s.laser_error_y)
        if len(self._laser_history_x) > 200:
            self._laser_history_x = self._laser_history_x[-200:]
            self._laser_history_y = self._laser_history_y[-200:]

        self._laser_dot.set_data([s.laser_error_x], [s.laser_error_y])
        if len(self._laser_history_x) > 1:
            self._laser_plot_line.set_data(self._laser_history_x, self._laser_history_y)

        # Lock zone color
        if s.locked:
            self._lock_zone.set_edgecolor(COLORS["success"])
            self._lock_zone.set_alpha(0.8)
        else:
            self._lock_zone.set_edgecolor(COLORS["warning"])
            self._lock_zone.set_alpha(0.4)

        self._canvas.draw_idle()


def run() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
    app = MergenApp()
    app.mainloop()


if __name__ == "__main__":
    run()
