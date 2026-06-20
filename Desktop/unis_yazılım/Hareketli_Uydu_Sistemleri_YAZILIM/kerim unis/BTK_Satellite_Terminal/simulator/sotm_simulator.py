import math
import random
import tkinter as tk
from tkinter import ttk

try:
    import cv2
except ImportError:
    cv2 = None

try:
    from PIL import Image, ImageDraw, ImageTk
except ImportError:
    Image = None
    ImageDraw = None
    ImageTk = None


MAIN_DT_S = 0.02
DISPLAY_PERIOD_MS = 20

AZ_MAX_SPEED_DPS = 60.0
EL_MAX_SPEED_DPS = 30.0
EL_MIN_DEG = 0.0
EL_MAX_DEG = 90.0

LASER_TARGET_RANGE_M = 4.0
LASER_TARGET_HEIGHT_M = 2.0
LASER_TARGET_EL_DEG = math.degrees(math.atan2(LASER_TARGET_HEIGHT_M, LASER_TARGET_RANGE_M))
CAMERA_FRAME_WIDTH_PX = 1280.0
CAMERA_FRAME_HEIGHT_PX = 720.0
CAMERA_AZ_FOV_DEG = 40.0
CAMERA_EL_FOV_DEG = 30.0
CAMERA_MIN_CONFIDENCE = 0.45
CAMERA_MIN_BOX_AREA_RATIO = 0.0004
CAMERA_CENTER_DEADBAND_PX = 3.0
CAMERA_DETECTION_SMOOTHING_ALPHA = 0.55
CAMERA_MAX_LOST_S = 0.15
CAMERA_BOX_WIDTH_PX = 64.0
CAMERA_BOX_HEIGHT_PX = 48.0
CAMERA_NOISE_PX = 2.5
CAMERA_DISPLAY_BG = "#08111f"
LASER_DOT_MAX_STEP_NORM = 0.045
ARTIFICIAL_TARGET_STEP_NORM = 0.055
ARTIFICIAL_TARGET_FAST_STEP_NORM = 0.12
ARTIFICIAL_TARGET_LIMIT_NORM = 0.92
LASER_KP = 0.10
LASER_KI = 0.01
LASER_KD = 0.004
LASER_MAX_CORR_DEG = 2.0
LASER_MAX_INTEGRAL = 10.0
LASER_LOCK_ERROR_DEG = 0.75
REACQUIRE_LIMIT_S = 8.0
TARGET_RATE_FF_GAIN = 1.0
TARGET_RATE_FILTER_ALPHA = 0.72
TARGET_RATE_RESET_DEG = 8.0

EARTH_RADIUS_KM = 6378.137
EARTH_FLATTENING = 1.0 / 298.257223563
GEO_ORBIT_RADIUS_KM = 42164.0


def clamp(value, min_value, max_value):
    return max(min_value, min(max_value, value))


def normalize_az(az_deg):
    while az_deg >= 360.0:
        az_deg -= 360.0
    while az_deg < 0.0:
        az_deg += 360.0
    return az_deg


def angle_error_deg(target, measured):
    err = target - measured
    while err > 180.0:
        err -= 360.0
    while err < -180.0:
        err += 360.0
    return err


class PID:
    def __init__(self, kp, ki, kd, max_integral, out_min, out_max, deadband, wrap):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.max_integral = max_integral
        self.out_min = out_min
        self.out_max = out_max
        self.deadband = deadband
        self.wrap = wrap
        self.integral = 0.0
        self.prev_error = 0.0
        self.prev_deriv = 0.0
        self.output = 0.0

    def reset(self):
        self.integral = 0.0
        self.prev_error = 0.0
        self.prev_deriv = 0.0
        self.output = 0.0

    def compute(self, target, measured, dt_s, feed_forward=0.0):
        if self.wrap:
            err = angle_error_deg(target, measured)
        else:
            err = target - measured

        if abs(err) < self.deadband:
            self.integral = 0.0
            self.prev_error = err
            self.prev_deriv = 0.0
            self.output = clamp(feed_forward, self.out_min, self.out_max)
            return self.output, err

        saturated_same_direction = (
            (self.output >= self.out_max and err > 0.0) or
            (self.output <= self.out_min and err < 0.0)
        )
        if not saturated_same_direction:
            self.integral = clamp(
                self.integral + err * dt_s,
                -self.max_integral,
                self.max_integral,
            )

        d_raw = (err - self.prev_error) / dt_s
        d_filt = 0.7 * d_raw + 0.3 * self.prev_deriv

        self.prev_error = err
        self.prev_deriv = d_filt
        self.output = clamp(
            self.kp * err + self.ki * self.integral + self.kd * d_filt + feed_forward,
            self.out_min,
            self.out_max,
        )
        return self.output, err


class CameraObjectDetector:
    def __init__(self):
        self.filtered_x_norm = 0.0
        self.filtered_y_norm = 0.0
        self.last_detection_s = 0.0
        self.initialized = False

    def reset(self):
        self.filtered_x_norm = 0.0
        self.filtered_y_norm = 0.0
        self.last_detection_s = 0.0
        self.initialized = False

    def update(self, center_x_px, center_y_px, box_w_px, box_h_px, detected, confidence, now_s):
        if not self._usable(center_x_px, center_y_px, box_w_px, box_h_px, detected, confidence):
            if self.initialized and now_s - self.last_detection_s > CAMERA_MAX_LOST_S:
                self.reset()
            return 0.0, 0.0, False, 0.0

        dx_px = center_x_px - CAMERA_FRAME_WIDTH_PX * 0.5
        dy_px = CAMERA_FRAME_HEIGHT_PX * 0.5 - center_y_px

        if abs(dx_px) < CAMERA_CENTER_DEADBAND_PX:
            dx_px = 0.0
        if abs(dy_px) < CAMERA_CENTER_DEADBAND_PX:
            dy_px = 0.0

        x_norm = clamp(dx_px / (CAMERA_FRAME_WIDTH_PX * 0.5), -1.0, 1.0)
        y_norm = clamp(dy_px / (CAMERA_FRAME_HEIGHT_PX * 0.5), -1.0, 1.0)
        alpha = clamp(CAMERA_DETECTION_SMOOTHING_ALPHA, 0.0, 1.0)

        if not self.initialized:
            self.filtered_x_norm = x_norm
            self.filtered_y_norm = y_norm
            self.initialized = True
        else:
            self.filtered_x_norm = alpha * x_norm + (1.0 - alpha) * self.filtered_x_norm
            self.filtered_y_norm = alpha * y_norm + (1.0 - alpha) * self.filtered_y_norm

        self.last_detection_s = now_s
        return self.filtered_x_norm, self.filtered_y_norm, True, confidence

    def _usable(self, center_x_px, center_y_px, box_w_px, box_h_px, detected, confidence):
        if not detected or confidence < CAMERA_MIN_CONFIDENCE:
            return False
        if (
            center_x_px < 0.0
            or center_x_px >= CAMERA_FRAME_WIDTH_PX
            or center_y_px < 0.0
            or center_y_px >= CAMERA_FRAME_HEIGHT_PX
            or box_w_px <= 0.0
            or box_h_px <= 0.0
        ):
            return False

        area_ratio = (box_w_px * box_h_px) / (CAMERA_FRAME_WIDTH_PX * CAMERA_FRAME_HEIGHT_PX)
        return area_ratio >= CAMERA_MIN_BOX_AREA_RATIO


class CameraTargetSource:
    def __init__(self, render_frames=True, use_real_camera=True):
        self.cap = None
        self.connected = False
        self.using_real_camera = False
        self.render_frames = render_frames
        self.use_real_camera = use_real_camera
        self.status = "kamera beklemede"
        self.synthetic_center_x_px = CAMERA_FRAME_WIDTH_PX * 0.68
        self.synthetic_center_y_px = CAMERA_FRAME_HEIGHT_PX * 0.42

    def connect(self, camera_index=0):
        if self.connected:
            return self.using_real_camera

        if not self.use_real_camera:
            self.status = "sanal kamera"
            self.connected = True
            self.using_real_camera = False
            return False

        if cv2 is None:
            self.status = "OpenCV yok; sanal kamera"
            self.connected = True
            self.using_real_camera = False
            return False

        backend = cv2.CAP_DSHOW if hasattr(cv2, "CAP_DSHOW") else 0
        cap = cv2.VideoCapture(int(camera_index), backend)
        if not cap or not cap.isOpened():
            if cap:
                cap.release()
            self.status = f"kamera {int(camera_index)} acilamadi; sanal kamera"
            self.connected = True
            self.using_real_camera = False
            return False

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_FRAME_WIDTH_PX)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_FRAME_HEIGHT_PX)
        self.cap = cap
        self.connected = True
        self.using_real_camera = True
        self.status = f"kamera {int(camera_index)} bagli"
        return True

    def disconnect(self):
        if self.cap is not None:
            self.cap.release()
        self.cap = None
        self.connected = False
        self.using_real_camera = False
        self.status = "kamera beklemede"

    def read(self, now_s, noise_enabled, camera_index=0):
        if not self.connected:
            self.connect(camera_index)

        if self.using_real_camera and self.cap is not None:
            ok, frame = self.cap.read()
            if ok:
                frame = cv2.resize(frame, (int(CAMERA_FRAME_WIDTH_PX), int(CAMERA_FRAME_HEIGHT_PX)))
                return self._detect_from_frame(frame)

            self.status = "kamera okunamadi; sanal kamera"
            self.using_real_camera = False

        return self._synthetic_detection(now_s, noise_enabled)

    def _detect_from_frame(self, frame_bgr):
        hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
        saturation_mask = cv2.inRange(hsv, (0, 45, 40), (179, 255, 255))

        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 60, 150)
        edges = cv2.dilate(edges, None, iterations=2)
        mask = cv2.bitwise_or(saturation_mask, edges)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        frame_area = CAMERA_FRAME_WIDTH_PX * CAMERA_FRAME_HEIGHT_PX
        best_box = None
        best_area = 0.0
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < frame_area * CAMERA_MIN_BOX_AREA_RATIO:
                continue
            x, y, w, h = cv2.boundingRect(contour)
            if w < 12 or h < 12:
                continue
            if area > best_area:
                best_area = area
                best_box = (float(x), float(y), float(w), float(h))

        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        frame_image = Image.fromarray(frame_rgb) if Image is not None else None

        if best_box is None:
            return {
                "center_x_px": CAMERA_FRAME_WIDTH_PX * 0.5,
                "center_y_px": CAMERA_FRAME_HEIGHT_PX * 0.5,
                "box_w_px": 0.0,
                "box_h_px": 0.0,
                "detected": False,
                "confidence": 0.0,
                "frame": frame_image,
                "status": "kamera bagli; hedef aranıyor",
            }

        x, y, w, h = best_box
        confidence = clamp(best_area / (frame_area * 0.08), CAMERA_MIN_CONFIDENCE, 0.98)
        return {
            "center_x_px": x + w * 0.5,
            "center_y_px": y + h * 0.5,
            "box_w_px": w,
            "box_h_px": h,
            "detected": True,
            "confidence": confidence,
            "frame": frame_image,
            "status": "kamera bagli",
        }

    def _synthetic_detection(self, now_s, noise_enabled):
        phase = now_s * 0.55
        self.synthetic_center_x_px = CAMERA_FRAME_WIDTH_PX * (0.62 + 0.19 * math.sin(phase))
        self.synthetic_center_y_px = CAMERA_FRAME_HEIGHT_PX * (0.48 + 0.16 * math.cos(phase * 0.74))

        noise_x = random.gauss(0.0, CAMERA_NOISE_PX) if noise_enabled else 0.0
        noise_y = random.gauss(0.0, CAMERA_NOISE_PX) if noise_enabled else 0.0
        center_x = clamp(self.synthetic_center_x_px + noise_x, 0.0, CAMERA_FRAME_WIDTH_PX - 1.0)
        center_y = clamp(self.synthetic_center_y_px + noise_y, 0.0, CAMERA_FRAME_HEIGHT_PX - 1.0)

        frame = None
        if self.render_frames and Image is not None and ImageDraw is not None:
            frame = Image.new("RGB", (int(CAMERA_FRAME_WIDTH_PX), int(CAMERA_FRAME_HEIGHT_PX)), (8, 17, 31))
            draw = ImageDraw.Draw(frame)
            for x in range(0, int(CAMERA_FRAME_WIDTH_PX), 80):
                draw.line((x, 0, x, int(CAMERA_FRAME_HEIGHT_PX)), fill=(16, 38, 62))
            for y in range(0, int(CAMERA_FRAME_HEIGHT_PX), 80):
                draw.line((0, y, int(CAMERA_FRAME_WIDTH_PX), y), fill=(16, 38, 62))
            bbox = (
                center_x - CAMERA_BOX_WIDTH_PX * 0.5,
                center_y - CAMERA_BOX_HEIGHT_PX * 0.5,
                center_x + CAMERA_BOX_WIDTH_PX * 0.5,
                center_y + CAMERA_BOX_HEIGHT_PX * 0.5,
            )
            draw.ellipse(bbox, fill=(230, 186, 56), outline=(255, 232, 142), width=4)

        return {
            "center_x_px": center_x,
            "center_y_px": center_y,
            "box_w_px": CAMERA_BOX_WIDTH_PX,
            "box_h_px": CAMERA_BOX_HEIGHT_PX,
            "detected": True,
            "confidence": 0.92,
            "frame": frame,
            "status": self.status,
        }


class LaserTracker:
    def __init__(self):
        self.az_integral = 0.0
        self.el_integral = 0.0
        self.prev_az_error = 0.0
        self.prev_el_error = 0.0
        self.initialized = False
        self.locked = False
        self.total_error = 0.0
        self.az_corr = 0.0
        self.el_corr = 0.0

    def reset(self):
        self.az_integral = 0.0
        self.el_integral = 0.0
        self.prev_az_error = 0.0
        self.prev_el_error = 0.0
        self.initialized = False
        self.locked = False
        self.total_error = 0.0
        self.az_corr = 0.0
        self.el_corr = 0.0

    def update(self, spot_x_norm, spot_y_norm, detected, confidence, dt_s):
        if not detected or confidence < CAMERA_MIN_CONFIDENCE:
            self.reset()
            return 0.0, 0.0

        az_error = clamp(spot_x_norm, -1.0, 1.0) * (CAMERA_AZ_FOV_DEG * 0.5)
        el_error = clamp(spot_y_norm, -1.0, 1.0) * (CAMERA_EL_FOV_DEG * 0.5)

        self.az_integral = clamp(
            self.az_integral + az_error * dt_s,
            -LASER_MAX_INTEGRAL,
            LASER_MAX_INTEGRAL,
        )
        self.el_integral = clamp(
            self.el_integral + el_error * dt_s,
            -LASER_MAX_INTEGRAL,
            LASER_MAX_INTEGRAL,
        )

        az_deriv = 0.0 if not self.initialized else (az_error - self.prev_az_error) / dt_s
        el_deriv = 0.0 if not self.initialized else (el_error - self.prev_el_error) / dt_s

        self.prev_az_error = az_error
        self.prev_el_error = el_error
        self.initialized = True

        self.az_corr = clamp(
            LASER_KP * az_error + LASER_KI * self.az_integral + LASER_KD * az_deriv,
            -LASER_MAX_CORR_DEG,
            LASER_MAX_CORR_DEG,
        )
        self.el_corr = clamp(
            LASER_KP * el_error + LASER_KI * self.el_integral + LASER_KD * el_deriv,
            -LASER_MAX_CORR_DEG,
            LASER_MAX_CORR_DEG,
        )
        self.total_error = math.hypot(az_error, el_error)
        self.locked = self.total_error <= LASER_LOCK_ERROR_DEG
        return self.az_corr, self.el_corr


def lla_to_ecef_km(lat_deg, lon_deg, alt_m):
    a = EARTH_RADIUS_KM
    f = EARTH_FLATTENING
    e2 = 2.0 * f - f * f
    lat = math.radians(lat_deg)
    lon = math.radians(lon_deg)
    alt = alt_m / 1000.0
    n = a / math.sqrt(1.0 - e2 * math.sin(lat) * math.sin(lat))
    return (
        (n + alt) * math.cos(lat) * math.cos(lon),
        (n + alt) * math.cos(lat) * math.sin(lon),
        (n * (1.0 - e2) + alt) * math.sin(lat),
    )


def calc_geo_azel(lat_deg, lon_deg, alt_m, sat_lon_deg):
    sat_lon = math.radians(sat_lon_deg)
    sat = (
        GEO_ORBIT_RADIUS_KM * math.cos(sat_lon),
        GEO_ORBIT_RADIUS_KM * math.sin(sat_lon),
        0.0,
    )
    obs = lla_to_ecef_km(lat_deg, lon_deg, alt_m)
    dx = sat[0] - obs[0]
    dy = sat[1] - obs[1]
    dz = sat[2] - obs[2]
    rng = math.sqrt(dx * dx + dy * dy + dz * dz)

    lat = math.radians(lat_deg)
    lon = math.radians(lon_deg)
    slat = math.sin(lat)
    clat = math.cos(lat)
    slon = math.sin(lon)
    clon = math.cos(lon)

    north = -slat * clon * dx - slat * slon * dy + clat * dz
    east = -slon * dx + clon * dy
    down = -clat * clon * dx - clat * slon * dy - slat * dz

    el = math.degrees(math.asin(-down / rng))
    az = math.degrees(math.atan2(east, north))
    if az < 0.0:
        az += 360.0
    return az, el, rng


def compensate_attitude(az_deg, el_deg, roll_deg, pitch_deg, yaw_deg):
    az_r = math.radians(normalize_az(az_deg - yaw_deg))
    el_r = math.radians(el_deg)

    ux = math.cos(el_r) * math.sin(az_r)
    uy = math.cos(el_r) * math.cos(az_r)
    uz = math.sin(el_r)

    pr = math.radians(pitch_deg)
    rr = math.radians(roll_deg)
    cp = math.cos(pr)
    sp = math.sin(pr)
    cr = math.cos(rr)
    sr = math.sin(rr)

    bx = cp * ux + sp * sr * uy + sp * cr * uz
    by = cr * uy - sr * uz
    bz = -sp * ux + cp * sr * uy + cp * cr * uz

    bz = clamp(bz, -1.0, 1.0)
    el_comp = math.degrees(math.asin(bz))
    az_comp = math.degrees(math.atan2(bx, by))
    return normalize_az(az_comp), clamp(el_comp, EL_MIN_DEG, EL_MAX_DEG)


class SotmSimulator:
    def __init__(self, root):
        self.root = root
        self.root.title("SoTM Uydu Terminali Simulasyonu")
        self.running = False
        self.time_s = 0.0

        self.az_actual = 0.0
        self.el_actual = 25.0
        self.az_target = 0.0
        self.el_target = 30.0
        self.az_error = 0.0
        self.el_error = 0.0
        self.spot_x_norm = 0.0
        self.spot_y_norm = 0.0
        self.camera_center_x_px = CAMERA_FRAME_WIDTH_PX * 0.5
        self.camera_center_y_px = CAMERA_FRAME_HEIGHT_PX * 0.5
        self.camera_confidence = 0.0
        self.camera_detected = False
        self.camera_frame = None
        self.camera_photo = None
        self.camera_source = CameraTargetSource()
        self.camera_status = self.camera_source.status
        self.artificial_x_norm = random.uniform(-0.62, 0.62)
        self.artificial_y_norm = random.uniform(-0.50, 0.50)
        self.target_x_norm = 0.0
        self.target_y_norm = 0.0
        self.laser_dot_x_norm = 0.0
        self.laser_dot_y_norm = 0.0
        self.prev_mode = None
        self.reacquire_active = True
        self.reacquire_start_s = 0.0
        self.reacquire_time_s = None
        self.reacquire_passed = None
        self.lock_hold_s = 0.0
        self.random_sat_az = random.uniform(0.0, 360.0)
        self.random_sat_el = random.uniform(15.0, 70.0)
        self.prev_base_az = None
        self.prev_base_el = None
        self.az_target_rate_dps = 0.0
        self.el_target_rate_dps = 0.0

        self.az_pid = PID(2.5, 0.1, 0.3, 20.0, -AZ_MAX_SPEED_DPS, AZ_MAX_SPEED_DPS, 0.1, True)
        self.el_pid = PID(3.0, 0.08, 0.25, 15.0, -EL_MAX_SPEED_DPS, EL_MAX_SPEED_DPS, 0.1, False)
        self.camera_detector = CameraObjectDetector()
        self.laser = LaserTracker()

        self.mode_var = tk.StringVar(value="Lazer Takip")
        self.laser_source_var = tk.StringVar(value="Kamera Modu")
        self.satellite_var = tk.StringVar(value="Turksat 4B")
        self.laser_var = tk.BooleanVar(value=True)
        self.noise_var = tk.BooleanVar(value=True)
        self.camera_index_var = tk.IntVar(value=0)
        self.lat_var = tk.DoubleVar(value=39.9208)
        self.lon_var = tk.DoubleVar(value=32.8541)
        self.alt_var = tk.DoubleVar(value=900.0)
        self.laser_target_az = 0.0
        self.laser_target_el = LASER_TARGET_EL_DEG
        self.status_vars = {}

        self._build_ui()
        self._draw_static()
        self.root.bind_all("<Left>", self._on_arrow_key)
        self.root.bind_all("<Right>", self._on_arrow_key)
        self.root.bind_all("<Up>", self._on_arrow_key)
        self.root.bind_all("<Down>", self._on_arrow_key)
        if self.mode_var.get() == "Lazer Takip":
            self._connect_camera_for_laser()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._tick()

    def _build_ui(self):
        main = ttk.Frame(self.root, padding=10)
        main.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(main, width=760, height=520, bg="#0b1020", highlightthickness=0)
        self.canvas.grid(row=0, column=0, rowspan=24, sticky="nsew", padx=(0, 12))
        self.canvas.bind("<Configure>", self._on_canvas_resize)

        panel = ttk.Frame(main)
        panel.grid(row=0, column=1, sticky="nw")

        ttk.Label(panel, text="Mod").grid(row=0, column=0, sticky="w")
        self.mode_combo = ttk.Combobox(
            panel,
            textvariable=self.mode_var,
            values=["Lazer Takip", "Uydu Yönelimi"],
            state="readonly",
            width=18,
        )
        self.mode_combo.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        self.mode_combo.bind("<<ComboboxSelected>>", self._on_mode_changed)

        self.laser_source_frame = ttk.LabelFrame(panel, text="Lazer takip modu")
        self.laser_source_frame.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        ttk.Radiobutton(
            self.laser_source_frame,
            text="Kamera Modu",
            value="Kamera Modu",
            variable=self.laser_source_var,
            command=self._on_laser_source_changed,
        ).grid(row=0, column=0, sticky="w", padx=6, pady=(4, 1))
        ttk.Radiobutton(
            self.laser_source_frame,
            text="Yapay Cisim Modu",
            value="Yapay Cisim Modu",
            variable=self.laser_source_var,
            command=self._on_laser_source_changed,
        ).grid(row=1, column=0, sticky="w", padx=6, pady=(1, 5))

        ttk.Label(panel, text="Uydu secimi").grid(row=4, column=0, sticky="w")
        ttk.Combobox(
            panel,
            textvariable=self.satellite_var,
            values=["Turksat 4B", "Turksat 5A"],
            state="readonly",
            width=18,
        ).grid(row=5, column=0, sticky="ew", pady=(0, 8))

        ttk.Checkbutton(panel, text="Kamera ile lazer duzeltmesi", variable=self.laser_var).grid(row=6, column=0, sticky="w")
        ttk.Checkbutton(panel, text="Olcum gurultusu", variable=self.noise_var).grid(row=7, column=0, sticky="w", pady=(0, 8))

        ttk.Label(panel, text="Kamera no").grid(row=8, column=0, sticky="w")
        ttk.Spinbox(
            panel,
            textvariable=self.camera_index_var,
            from_=0,
            to=5,
            increment=1,
            width=8,
            command=self.reconnect_camera,
        ).grid(row=9, column=0, sticky="ew", pady=(0, 5))

        ttk.Button(panel, text="Baslat / Durdur", command=self.toggle).grid(row=10, column=0, sticky="ew", pady=2)
        ttk.Button(panel, text="Sifirla", command=self.reset).grid(row=11, column=0, sticky="ew", pady=2)
        ttk.Button(panel, text="Anten Sapmasi Ver", command=self.inject_pointing_error).grid(row=12, column=0, sticky="ew", pady=(2, 12))

        self._spin(panel, "ZED-F9P lat", self.lat_var, 13, -90.0, 90.0)
        self._spin(panel, "ZED-F9P lon", self.lon_var, 15, -180.0, 180.0)

        ttk.Label(panel, text="Canli Bilgiler", font=("Segoe UI", 10, "bold")).grid(row=17, column=0, sticky="w", pady=(14, 4))
        info = ttk.Frame(panel)
        info.grid(row=18, column=0, sticky="ew")
        for row, key in enumerate([
            "time",
            "camera",
            "disturbance",
            "world_target",
            "body_target",
            "cmd_target",
            "actual",
            "motor_error",
            "target_rate",
            "laser_error",
            "laser_corr",
            "lock",
            "reacquire",
        ]):
            self.status_vars[key] = tk.StringVar(value="-")
            ttk.Label(info, textvariable=self.status_vars[key], font=("Consolas", 9)).grid(row=row, column=0, sticky="w", pady=1)

        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=0)
        main.rowconfigure(0, weight=1)
        self._update_laser_source_visibility()

    def _spin(self, parent, label, variable, row, min_value, max_value):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w")
        ttk.Spinbox(
            parent,
            textvariable=variable,
            from_=min_value,
            to=max_value,
            increment=0.1,
            width=12,
        ).grid(row=row + 1, column=0, sticky="ew", pady=(0, 5))

    def _update_laser_source_visibility(self):
        if self.mode_var.get() == "Lazer Takip":
            self.laser_source_frame.grid()
        else:
            self.laser_source_frame.grid_remove()

    def _artificial_mode_enabled(self):
        return (
            self.mode_var.get() == "Lazer Takip"
            and self.laser_source_var.get() == "Yapay Cisim Modu"
        )

    def _randomize_artificial_target(self):
        self.artificial_x_norm = random.uniform(-0.62, 0.62)
        self.artificial_y_norm = random.uniform(-0.50, 0.50)
        self.target_x_norm = self.artificial_x_norm
        self.target_y_norm = self.artificial_y_norm

    def _on_laser_source_changed(self):
        self._reset_laser_camera_state()
        self.reacquire_active = True
        self.reacquire_start_s = self.time_s
        self.reacquire_time_s = None
        self.reacquire_passed = None
        self.lock_hold_s = 0.0
        if self._artificial_mode_enabled():
            self.camera_source.disconnect()
            self.camera_status = "yapay cisim modu"
        else:
            self._connect_camera_for_laser()

    def _on_mode_changed(self, _event=None):
        self._update_laser_source_visibility()
        if self.mode_var.get() == "Lazer Takip":
            self._reset_laser_camera_state()
            if not self._artificial_mode_enabled():
                self._connect_camera_for_laser()
        else:
            self.camera_source.disconnect()
            self.camera_status = self.camera_source.status
            self.camera_frame = None
            self.camera_photo = None

    def _connect_camera_for_laser(self):
        if self._artificial_mode_enabled():
            self.camera_status = "yapay cisim modu"
            return
        self.camera_source.connect(self.camera_index_var.get())
        self.camera_status = self.camera_source.status

    def reconnect_camera(self):
        if self.mode_var.get() != "Lazer Takip" or self._artificial_mode_enabled():
            return
        self.camera_source.disconnect()
        self.camera_frame = None
        self.camera_photo = None
        self._connect_camera_for_laser()

    def toggle(self):
        self.running = not self.running
        if self.running and self.mode_var.get() == "Lazer Takip":
            self.laser_var.set(True)
            self._connect_camera_for_laser()

    def _on_arrow_key(self, event):
        if not self._artificial_mode_enabled():
            return None

        step = ARTIFICIAL_TARGET_FAST_STEP_NORM if (event.state & 0x0001) else ARTIFICIAL_TARGET_STEP_NORM
        dx = 0.0
        dy = 0.0
        if event.keysym == "Left":
            dx = -step
        elif event.keysym == "Right":
            dx = step
        elif event.keysym == "Up":
            dy = step
        elif event.keysym == "Down":
            dy = -step
        else:
            return None

        self.artificial_x_norm = clamp(
            self.artificial_x_norm + dx,
            -ARTIFICIAL_TARGET_LIMIT_NORM,
            ARTIFICIAL_TARGET_LIMIT_NORM,
        )
        self.artificial_y_norm = clamp(
            self.artificial_y_norm + dy,
            -ARTIFICIAL_TARGET_LIMIT_NORM,
            ARTIFICIAL_TARGET_LIMIT_NORM,
        )
        self.target_x_norm = self.artificial_x_norm
        self.target_y_norm = self.artificial_y_norm
        return "break"

    def _reset_laser_camera_state(self):
        self.camera_detector.reset()
        self.laser.reset()
        self.spot_x_norm = 0.0
        self.spot_y_norm = 0.0
        if self._artificial_mode_enabled():
            self._randomize_artificial_target()
            self.camera_source.disconnect()
            self.camera_status = "yapay cisim modu"
        else:
            self.target_x_norm = 0.0
            self.target_y_norm = 0.0
        self.laser_dot_x_norm = 0.0
        self.laser_dot_y_norm = 0.0
        self.camera_confidence = 0.0
        self.camera_detected = False
        self.camera_frame = None
        self.camera_photo = None

    def reset(self):
        self.time_s = 0.0
        self.laser_target_az = random.uniform(0.0, 360.0)
        self.laser_target_el = LASER_TARGET_EL_DEG
        self.az_actual = normalize_az(self.laser_target_az + random.choice([-1.0, 1.0]) * random.uniform(15.0, 45.0))
        self.el_actual = clamp(self.laser_target_el + random.choice([-1.0, 1.0]) * random.uniform(8.0, 20.0), EL_MIN_DEG, EL_MAX_DEG)
        self.az_pid.reset()
        self.el_pid.reset()
        self._reset_laser_camera_state()
        self._reset_target_rate()
        self.prev_mode = None
        self.reacquire_active = True
        self.reacquire_start_s = 0.0
        self.reacquire_time_s = None
        self.reacquire_passed = None
        self.lock_hold_s = 0.0

    def inject_pointing_error(self):
        self.az_actual = normalize_az(self.az_actual + random.choice([-1.0, 1.0]) * random.uniform(12.0, 35.0))
        self.el_actual = clamp(self.el_actual + random.choice([-1.0, 1.0]) * random.uniform(8.0, 18.0), EL_MIN_DEG, EL_MAX_DEG)
        self.reacquire_active = True
        self.reacquire_start_s = self.time_s
        self.reacquire_time_s = None
        self.reacquire_passed = None
        self.lock_hold_s = 0.0
        self._reset_laser_camera_state()
        self._reset_target_rate()

    def _on_close(self):
        self.camera_source.disconnect()
        self.root.destroy()

    def _base_target_world(self):
        mode = self.mode_var.get()
        if mode == "Uydu Yönelimi":
            sat_lon = 50.0 if self.satellite_var.get() == "Turksat 4B" else 31.0
            return calc_geo_azel(
                self.lat_var.get(),
                self.lon_var.get(),
                self.alt_var.get(),
                sat_lon,
            )[:2]
        return self.laser_target_az, self.laser_target_el

    def _update_reacquire_state(self, locked):
        mode = self.mode_var.get()
        if self.prev_mode is None:
            self.prev_mode = mode
        elif mode != self.prev_mode:
            self.reacquire_active = True
            self.reacquire_start_s = self.time_s
            self.reacquire_time_s = None
            self.reacquire_passed = None
            self.lock_hold_s = 0.0
            self._reset_target_rate()
            self.prev_mode = mode

        if not self.reacquire_active and not locked:
            self.reacquire_active = True
            self.reacquire_start_s = self.time_s
            self.reacquire_time_s = None
            self.reacquire_passed = None
            self.lock_hold_s = 0.0

        if self.reacquire_active:
            if locked:
                self.lock_hold_s += MAIN_DT_S
                if self.lock_hold_s >= 0.25:
                    self.reacquire_time_s = self.time_s - self.reacquire_start_s
                    self.reacquire_passed = self.reacquire_time_s <= REACQUIRE_LIMIT_S
                    self.reacquire_active = False
            else:
                self.lock_hold_s = 0.0

    def _disturbance(self):
        w = 2.0 * math.pi / 10.0
        roll = 8.0 * math.sin(w * self.time_s)
        pitch = 8.0 * math.cos(0.81 * w * self.time_s)
        yaw = normalize_az((self.time_s * 360.0 / 10.0))
        return roll, pitch, yaw

    def _reset_target_rate(self):
        self.prev_base_az = None
        self.prev_base_el = None
        self.az_target_rate_dps = 0.0
        self.el_target_rate_dps = 0.0

    def _target_rate_feedforward(self, base_az, base_el):
        if self.prev_base_az is None or self.prev_base_el is None:
            self.prev_base_az = base_az
            self.prev_base_el = base_el
            return 0.0, 0.0

        az_step = angle_error_deg(base_az, self.prev_base_az)
        el_step = base_el - self.prev_base_el
        self.prev_base_az = base_az
        self.prev_base_el = base_el

        if abs(az_step) > TARGET_RATE_RESET_DEG or abs(el_step) > TARGET_RATE_RESET_DEG:
            self.az_target_rate_dps = 0.0
            self.el_target_rate_dps = 0.0
            return 0.0, 0.0

        raw_az_rate = az_step / MAIN_DT_S
        raw_el_rate = el_step / MAIN_DT_S
        alpha = TARGET_RATE_FILTER_ALPHA
        self.az_target_rate_dps = alpha * raw_az_rate + (1.0 - alpha) * self.az_target_rate_dps
        self.el_target_rate_dps = alpha * raw_el_rate + (1.0 - alpha) * self.el_target_rate_dps

        return (
            clamp(TARGET_RATE_FF_GAIN * self.az_target_rate_dps, -AZ_MAX_SPEED_DPS, AZ_MAX_SPEED_DPS),
            clamp(TARGET_RATE_FF_GAIN * self.el_target_rate_dps, -EL_MAX_SPEED_DPS, EL_MAX_SPEED_DPS),
        )

    def _camera_detection_from_error(self, true_az_err, true_el_err):
        raw_x_norm = true_az_err / (CAMERA_AZ_FOV_DEG * 0.5)
        raw_y_norm = true_el_err / (CAMERA_EL_FOV_DEG * 0.5)
        visible = abs(raw_x_norm) < 1.0 and abs(raw_y_norm) < 1.0

        noise_x_px = random.gauss(0.0, CAMERA_NOISE_PX) if self.noise_var.get() else 0.0
        noise_y_px = random.gauss(0.0, CAMERA_NOISE_PX) if self.noise_var.get() else 0.0

        if visible:
            self.camera_center_x_px = (
                CAMERA_FRAME_WIDTH_PX * 0.5
                + raw_x_norm * CAMERA_FRAME_WIDTH_PX * 0.5
                + noise_x_px
            )
            self.camera_center_y_px = (
                CAMERA_FRAME_HEIGHT_PX * 0.5
                - raw_y_norm * CAMERA_FRAME_HEIGHT_PX * 0.5
                + noise_y_px
            )
            edge_penalty = 0.25 * max(abs(raw_x_norm), abs(raw_y_norm))
            self.camera_confidence = clamp(0.95 - edge_penalty, CAMERA_MIN_CONFIDENCE, 0.95)
        else:
            self.camera_center_x_px = CAMERA_FRAME_WIDTH_PX * 0.5
            self.camera_center_y_px = CAMERA_FRAME_HEIGHT_PX * 0.5
            self.camera_confidence = 0.0

        self.camera_detected = visible
        return self.camera_detector.update(
            self.camera_center_x_px,
            self.camera_center_y_px,
            CAMERA_BOX_WIDTH_PX,
            CAMERA_BOX_HEIGHT_PX,
            self.camera_detected,
            self.camera_confidence,
            self.time_s,
        )

    def _artificial_detection_sample(self):
        noise_x = random.gauss(0.0, CAMERA_NOISE_PX) if self.noise_var.get() else 0.0
        noise_y = random.gauss(0.0, CAMERA_NOISE_PX) if self.noise_var.get() else 0.0
        center_x = clamp(
            CAMERA_FRAME_WIDTH_PX * (0.5 + self.artificial_x_norm * 0.5) + noise_x,
            0.0,
            CAMERA_FRAME_WIDTH_PX - 1.0,
        )
        center_y = clamp(
            CAMERA_FRAME_HEIGHT_PX * (0.5 - self.artificial_y_norm * 0.5) + noise_y,
            0.0,
            CAMERA_FRAME_HEIGHT_PX - 1.0,
        )

        frame = None
        if Image is not None and ImageDraw is not None:
            frame = Image.new("RGB", (int(CAMERA_FRAME_WIDTH_PX), int(CAMERA_FRAME_HEIGHT_PX)), (8, 17, 31))
            draw = ImageDraw.Draw(frame)
            for x in range(0, int(CAMERA_FRAME_WIDTH_PX), 80):
                draw.line((x, 0, x, int(CAMERA_FRAME_HEIGHT_PX)), fill=(16, 38, 62))
            for y in range(0, int(CAMERA_FRAME_HEIGHT_PX), 80):
                draw.line((0, y, int(CAMERA_FRAME_WIDTH_PX), y), fill=(16, 38, 62))
            bbox = (
                center_x - CAMERA_BOX_WIDTH_PX * 0.5,
                center_y - CAMERA_BOX_HEIGHT_PX * 0.5,
                center_x + CAMERA_BOX_WIDTH_PX * 0.5,
                center_y + CAMERA_BOX_HEIGHT_PX * 0.5,
            )
            draw.rectangle(bbox, fill=(230, 186, 56), outline=(255, 232, 142), width=4)

        return {
            "center_x_px": center_x,
            "center_y_px": center_y,
            "box_w_px": CAMERA_BOX_WIDTH_PX,
            "box_h_px": CAMERA_BOX_HEIGHT_PX,
            "detected": True,
            "confidence": 0.95,
            "frame": frame,
            "status": "yapay cisim modu",
        }

    def _camera_detection_from_source(self):
        if self._artificial_mode_enabled():
            sample = self._artificial_detection_sample()
        else:
            sample = self.camera_source.read(
                self.time_s,
                self.noise_var.get(),
                self.camera_index_var.get(),
            )
        self.camera_frame = sample["frame"]
        self.camera_status = sample["status"]
        self.camera_center_x_px = sample["center_x_px"]
        self.camera_center_y_px = sample["center_y_px"]
        self.camera_confidence = sample["confidence"]
        self.camera_detected = sample["detected"]

        self.target_x_norm, self.target_y_norm, detected, confidence = self.camera_detector.update(
            self.camera_center_x_px,
            self.camera_center_y_px,
            sample["box_w_px"],
            sample["box_h_px"],
            self.camera_detected,
            self.camera_confidence,
            self.time_s,
        )
        self.spot_x_norm = self.target_x_norm
        self.spot_y_norm = self.target_y_norm
        return detected, confidence

    def _simulate_camera_laser_step(self):
        self.time_s += MAIN_DT_S
        detected, confidence = self._camera_detection_from_source()

        if detected and self.laser_var.get():
            err_x_norm = clamp(self.target_x_norm - self.laser_dot_x_norm, -1.0, 1.0)
            err_y_norm = clamp(self.target_y_norm - self.laser_dot_y_norm, -1.0, 1.0)
            az_corr, el_corr = self.laser.update(err_x_norm, err_y_norm, True, confidence, MAIN_DT_S)

            laser_az_deg = self.laser_dot_x_norm * (CAMERA_AZ_FOV_DEG * 0.5)
            laser_el_deg = self.laser_dot_y_norm * (CAMERA_EL_FOV_DEG * 0.5)
            az_setpoint = laser_az_deg + az_corr
            el_setpoint = laser_el_deg + el_corr

            az_speed, self.az_error = self.az_pid.compute(az_setpoint, laser_az_deg, MAIN_DT_S, 0.0)
            el_speed, self.el_error = self.el_pid.compute(el_setpoint, laser_el_deg, MAIN_DT_S, 0.0)

            az_step = clamp(
                err_x_norm * 0.08 + az_speed * MAIN_DT_S / (CAMERA_AZ_FOV_DEG * 0.5),
                -LASER_DOT_MAX_STEP_NORM,
                LASER_DOT_MAX_STEP_NORM,
            )
            el_step = clamp(
                err_y_norm * 0.08 + el_speed * MAIN_DT_S / (CAMERA_EL_FOV_DEG * 0.5),
                -LASER_DOT_MAX_STEP_NORM,
                LASER_DOT_MAX_STEP_NORM,
            )
            self.laser_dot_x_norm = clamp(self.laser_dot_x_norm + az_step, -1.0, 1.0)
            self.laser_dot_y_norm = clamp(self.laser_dot_y_norm + el_step, -1.0, 1.0)

            lock_error = math.hypot(
                (self.target_x_norm - self.laser_dot_x_norm) * (CAMERA_AZ_FOV_DEG * 0.5),
                (self.target_y_norm - self.laser_dot_y_norm) * (CAMERA_EL_FOV_DEG * 0.5),
            )
            self.laser.locked = lock_error <= LASER_LOCK_ERROR_DEG
            self.laser.total_error = lock_error
        else:
            self.laser.reset()
            self.az_error = 0.0
            self.el_error = 0.0
            self.laser_dot_x_norm *= 0.98
            self.laser_dot_y_norm *= 0.98
            self.laser.locked = False
            self.laser.total_error = 0.0

        self.az_target = self.target_x_norm * (CAMERA_AZ_FOV_DEG * 0.5)
        self.el_target = self.target_y_norm * (CAMERA_EL_FOV_DEG * 0.5)
        self.az_actual = self.laser_dot_x_norm * (CAMERA_AZ_FOV_DEG * 0.5)
        self.el_actual = self.laser_dot_y_norm * (CAMERA_EL_FOV_DEG * 0.5)
        self.az_target_rate_dps = self.az_error / MAIN_DT_S if MAIN_DT_S > 0.0 else 0.0
        self.el_target_rate_dps = self.el_error / MAIN_DT_S if MAIN_DT_S > 0.0 else 0.0
        self._update_reacquire_state(self.laser.locked)

        return 0.0, 0.0, 0.0, self.az_target, self.el_target, self.az_actual, self.el_actual

    def _camera_preview_step(self):
        self._connect_camera_for_laser()
        self._camera_detection_from_source()

        self.az_target = self.target_x_norm * (CAMERA_AZ_FOV_DEG * 0.5)
        self.el_target = self.target_y_norm * (CAMERA_EL_FOV_DEG * 0.5)
        self.az_actual = self.laser_dot_x_norm * (CAMERA_AZ_FOV_DEG * 0.5)
        self.el_actual = self.laser_dot_y_norm * (CAMERA_EL_FOV_DEG * 0.5)

        preview_error = math.hypot(
            (self.target_x_norm - self.laser_dot_x_norm) * (CAMERA_AZ_FOV_DEG * 0.5),
            (self.target_y_norm - self.laser_dot_y_norm) * (CAMERA_EL_FOV_DEG * 0.5),
        )
        self.laser.locked = self.camera_detected and preview_error <= LASER_LOCK_ERROR_DEG
        self.laser.total_error = preview_error if self.camera_detected else 0.0
        return 0.0, 0.0, 0.0, self.az_target, self.el_target, self.az_actual, self.el_actual

    def _simulate_step(self):
        if self.mode_var.get() == "Lazer Takip":
            return self._simulate_camera_laser_step()

        self.time_s += MAIN_DT_S
        roll, pitch, yaw = self._disturbance()
        world_az, world_el = self._base_target_world()
        base_az, base_el = compensate_attitude(world_az, world_el, roll, pitch, yaw)
        az_ff, el_ff = self._target_rate_feedforward(base_az, base_el)

        true_az_err = angle_error_deg(base_az, self.az_actual)
        true_el_err = base_el - self.el_actual

        self.spot_x_norm, self.spot_y_norm, detected, confidence = (
            self._camera_detection_from_error(true_az_err, true_el_err)
        )

        laser_enabled = self.laser_var.get() and self.mode_var.get() == "Lazer Takip"
        if laser_enabled:
            az_corr, el_corr = self.laser.update(self.spot_x_norm, self.spot_y_norm, detected, confidence, MAIN_DT_S)
        else:
            self.camera_detector.reset()
            self.laser.reset()
            az_corr, el_corr = 0.0, 0.0

        self.az_target = normalize_az(base_az + az_corr)
        self.el_target = clamp(base_el + el_corr, EL_MIN_DEG, EL_MAX_DEG)

        az_speed, self.az_error = self.az_pid.compute(self.az_target, self.az_actual, MAIN_DT_S, az_ff)
        el_speed, self.el_error = self.el_pid.compute(self.el_target, self.el_actual, MAIN_DT_S, el_ff)

        self.az_actual = normalize_az(self.az_actual + az_speed * MAIN_DT_S)
        self.el_actual = clamp(self.el_actual + el_speed * MAIN_DT_S, EL_MIN_DEG, EL_MAX_DEG)

        lock_error = math.hypot(angle_error_deg(base_az, self.az_actual), base_el - self.el_actual)
        locked = lock_error <= LASER_LOCK_ERROR_DEG
        self.laser.locked = locked
        self.laser.total_error = lock_error
        self._update_reacquire_state(locked)

        return roll, pitch, yaw, world_az, world_el, base_az, base_el

    def _draw_static(self):
        self.canvas.delete("all")
        width = max(self.canvas.winfo_width(), 300)
        height = max(self.canvas.winfo_height(), 300)
        self.cx = width * 0.5
        self.cy = height * 0.52
        self.target_radius = max(80.0, min(width, height) * 0.42)
        step = self.target_radius / 6.0

        for idx in range(1, 7):
            radius = step * idx
            color = "#17345f" if radius < 200 else "#244b80"
            self.canvas.create_oval(
                self.cx - radius,
                self.cy - radius,
                self.cx + radius,
                self.cy + radius,
                outline=color,
            )
        self.canvas.create_line(self.cx - self.target_radius, self.cy, self.cx + self.target_radius, self.cy, fill="#1e6b8f")
        self.canvas.create_line(self.cx, self.cy - self.target_radius, self.cx, self.cy + self.target_radius, fill="#1e6b8f")
        self.canvas.create_text(self.cx, 28, text="Kamera Goruntusu ve Hedef Merkezi", fill="#d6e7ff", font=("Segoe UI", 14, "bold"))
        self.canvas.create_text(self.cx, min(height - 22, self.cy + self.target_radius + 28), text="Merkez = boresight kilidi", fill="#7ea6c8", font=("Segoe UI", 10))

    def _on_canvas_resize(self, _event):
        self._draw_static()

    def _camera_view_rect(self):
        width = max(self.canvas.winfo_width(), 300)
        height = max(self.canvas.winfo_height(), 300)
        aspect = CAMERA_FRAME_WIDTH_PX / CAMERA_FRAME_HEIGHT_PX
        view_w = width
        view_h = view_w / aspect
        if view_h > height:
            view_h = height
            view_w = view_h * aspect
        x0 = (width - view_w) * 0.5
        y0 = (height - view_h) * 0.5
        return x0, y0, view_w, view_h

    def _camera_norm_to_canvas(self, x_norm, y_norm):
        x0, y0, view_w, view_h = self._camera_view_rect()
        return (
            x0 + (0.5 + x_norm * 0.5) * view_w,
            y0 + (0.5 - y_norm * 0.5) * view_h,
        )

    def _draw_camera_dynamic(self, state):
        x0, y0, view_w, view_h = self._camera_view_rect()
        if self.camera_frame is not None and ImageTk is not None:
            resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS", 1)
            image = self.camera_frame.resize((int(view_w), int(view_h)), resample)
            self.camera_photo = ImageTk.PhotoImage(image)
            self.canvas.create_image(x0, y0, image=self.camera_photo, anchor="nw", tags="dynamic")
        else:
            self.canvas.create_rectangle(x0, y0, x0 + view_w, y0 + view_h, fill=CAMERA_DISPLAY_BG, outline="#17345f", tags="dynamic")

        cx, cy = self._camera_norm_to_canvas(0.0, 0.0)
        target_x, target_y = self._camera_norm_to_canvas(self.target_x_norm, self.target_y_norm)
        laser_x, laser_y = self._camera_norm_to_canvas(self.laser_dot_x_norm, self.laser_dot_y_norm)

        box_w = CAMERA_BOX_WIDTH_PX / CAMERA_FRAME_WIDTH_PX * view_w
        box_h = CAMERA_BOX_HEIGHT_PX / CAMERA_FRAME_HEIGHT_PX * view_h
        target_color = "#ffcc33" if self.camera_detected else "#6f7785"
        self.canvas.create_rectangle(
            target_x - box_w * 0.5,
            target_y - box_h * 0.5,
            target_x + box_w * 0.5,
            target_y + box_h * 0.5,
            outline=target_color,
            width=2,
            tags="dynamic",
        )
        self.canvas.create_oval(target_x - 5, target_y - 5, target_x + 5, target_y + 5, fill=target_color, outline="", tags="dynamic")

        self.canvas.create_line(laser_x, laser_y, target_x, target_y, fill="#7fa4ff", dash=(4, 4), tags="dynamic")
        self.canvas.create_line(cx - 18, cy, cx + 18, cy, fill="#35ff7a", tags="dynamic")
        self.canvas.create_line(cx, cy - 18, cx, cy + 18, fill="#35ff7a", tags="dynamic")
        self.canvas.create_oval(cx - 4, cy - 4, cx + 4, cy + 4, outline="#35ff7a", width=2, tags="dynamic")
        self.canvas.create_oval(laser_x - 9, laser_y - 9, laser_x + 9, laser_y + 9, fill="#35ff7a", outline="white", tags="dynamic")

        roll, pitch, yaw, world_az, world_el, base_az, base_el = state
        self.status_vars["time"].set(f"Sure        : {self.time_s:6.1f} s  mod: {self.mode_var.get()}")
        self.status_vars["camera"].set(f"Kamera      : {self.camera_status}")
        self.status_vars["disturbance"].set(f"Hedef px    : x {self.camera_center_x_px:6.0f}  y {self.camera_center_y_px:6.0f}  guven {self.camera_confidence:4.2f}")
        self.status_vars["world_target"].set(f"Hedef aci   : az {world_az:+7.2f}  el {world_el:+6.2f}")
        self.status_vars["body_target"].set(f"Lazer nokta : az {base_az:+7.2f}  el {base_el:+6.2f}")
        self.status_vars["cmd_target"].set(f"Komut       : az {self.az_target:+7.2f}  el {self.el_target:+6.2f}")
        self.status_vars["actual"].set(f"Nokta       : az {self.az_actual:+7.2f}  el {self.el_actual:+6.2f}")
        self.status_vars["motor_error"].set(f"Motor hata  : az {self.az_error:+7.2f}  el {self.el_error:+6.2f}")
        self.status_vars["target_rate"].set(f"Hata hizi   : az {self.az_target_rate_dps:+7.2f}  el {self.el_target_rate_dps:+6.2f}")
        self.status_vars["laser_error"].set(f"Kamera hata : {self.laser.total_error:6.2f} deg")
        self.status_vars["laser_corr"].set(f"Lazer duz.  : az {self.laser.az_corr:+7.2f}  el {self.laser.el_corr:+6.2f}")
        self.status_vars["lock"].set(f"Kilit       : {'EVET' if self.laser.locked else 'HAYIR'}")
        if self.reacquire_time_s is not None:
            result = "GECTI" if self.reacquire_passed else "KALDI"
            self.status_vars["reacquire"].set(f"8 sn testi  : {self.reacquire_time_s:5.2f} s  {result}")
        elif self.reacquire_active:
            elapsed = self.time_s - self.reacquire_start_s
            self.status_vars["reacquire"].set(f"8 sn testi  : araniyor {elapsed:5.2f} s")
        else:
            self.status_vars["reacquire"].set("8 sn testi  : beklemede")

    def _draw_dynamic(self, state):
        self.canvas.delete("dynamic")
        if self.mode_var.get() == "Lazer Takip":
            self._draw_camera_dynamic(state)
            return

        scale = self.target_radius * 0.95
        spot_x = self.cx + self.spot_x_norm * scale
        spot_y = self.cy - self.spot_y_norm * scale
        locked = self.laser.locked
        spot_color = "#35ff7a" if locked else "#ffcc33"
        self.canvas.create_oval(spot_x - 8, spot_y - 8, spot_x + 8, spot_y + 8, fill=spot_color, outline="white", tags="dynamic")
        self.canvas.create_line(self.cx, self.cy, spot_x, spot_y, fill="#8aa4ff", dash=(3, 3), tags="dynamic")

        roll, pitch, yaw, world_az, world_el, base_az, base_el = state
        self.status_vars["time"].set(f"Sure        : {self.time_s:6.1f} s  mod: {self.mode_var.get()}")
        self.status_vars["disturbance"].set(f"Bozucu      : roll {roll:+6.2f}  pitch {pitch:+6.2f}  yaw {yaw:6.1f}")
        if self.mode_var.get() == "Lazer Takip":
            self.status_vars["world_target"].set(f"Kamera hedef: menzil {LASER_TARGET_RANGE_M:g} m  yukseklik {LASER_TARGET_HEIGHT_M:g} m  az {world_az:7.2f}  el {world_el:6.2f}")
        else:
            self.status_vars["world_target"].set(f"{self.satellite_var.get():12}: az {world_az:7.2f}  el {world_el:6.2f}")
        self.status_vars["body_target"].set(f"Govde hedef : az {base_az:7.2f}  el {base_el:6.2f}")
        self.status_vars["cmd_target"].set(f"Komut hedef : az {self.az_target:7.2f}  el {self.el_target:6.2f}")
        self.status_vars["actual"].set(f"Gercek aci  : az {self.az_actual:7.2f}  el {self.el_actual:6.2f}")
        self.status_vars["motor_error"].set(f"Motor hata  : az {self.az_error:+7.2f}  el {self.el_error:+6.2f}")
        self.status_vars["target_rate"].set(f"Hedef hizi  : az {self.az_target_rate_dps:+7.2f}  el {self.el_target_rate_dps:+6.2f}")
        self.status_vars["laser_error"].set(f"Kamera hata : {self.laser.total_error:6.2f} deg")
        self.status_vars["laser_corr"].set(f"Lazer duz.  : az {self.laser.az_corr:+7.2f}  el {self.laser.el_corr:+6.2f}")
        self.status_vars["lock"].set(f"Kilit       : {'EVET' if locked else 'HAYIR'}")
        if self.reacquire_time_s is not None:
            result = "GECTI" if self.reacquire_passed else "KALDI"
            self.status_vars["reacquire"].set(f"8 sn testi  : {self.reacquire_time_s:5.2f} s  {result}")
        elif self.reacquire_active:
            elapsed = self.time_s - self.reacquire_start_s
            self.status_vars["reacquire"].set(f"8 sn testi  : araniyor {elapsed:5.2f} s")
        else:
            self.status_vars["reacquire"].set("8 sn testi  : beklemede")

    def _tick(self):
        if self.running:
            state = self._simulate_step()
        elif self.mode_var.get() == "Lazer Takip":
            state = self._camera_preview_step()
        else:
            roll, pitch, yaw = self._disturbance()
            world_az, world_el = self._base_target_world()
            base_az, base_el = compensate_attitude(world_az, world_el, roll, pitch, yaw)
            lock_error = math.hypot(angle_error_deg(base_az, self.az_actual), base_el - self.el_actual)
            self.laser.locked = lock_error <= LASER_LOCK_ERROR_DEG
            self.laser.total_error = lock_error
            self._update_reacquire_state(self.laser.locked)
            state = (roll, pitch, yaw, world_az, world_el, base_az, base_el)

        self._draw_dynamic(state)
        self.root.after(DISPLAY_PERIOD_MS, self._tick)


def main():
    root = tk.Tk()
    app = SotmSimulator(root)
    root.minsize(1080, 580)
    root.mainloop()


if __name__ == "__main__":
    main()
