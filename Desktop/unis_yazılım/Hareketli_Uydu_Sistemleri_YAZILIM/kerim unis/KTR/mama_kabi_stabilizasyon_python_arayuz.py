import math
import random
import time
import tkinter as tk
from collections import deque
from tkinter import ttk

try:
    from PIL import Image, ImageDraw, ImageFont, ImageTk
except ImportError:
    Image = None
    ImageDraw = None
    ImageFont = None
    ImageTk = None


TAU = math.pi * 2.0
RAD = math.pi / 180.0


class OneAxisKalman:
    def __init__(self):
        self.angle = 0.0
        self.bias = 0.0
        self.p00 = 0.0
        self.p01 = 0.0
        self.p10 = 0.0
        self.p11 = 0.0
        self.q_angle = 0.002
        self.q_bias = 0.004
        self.r_measure = 0.42

    def reset(self):
        self.__init__()

    def update(self, acc_angle, gyro_rate, dt):
        rate = gyro_rate - self.bias
        self.angle += dt * rate

        self.p00 += dt * (dt * self.p11 - self.p01 - self.p10 + self.q_angle)
        self.p01 -= dt * self.p11
        self.p10 -= dt * self.p11
        self.p11 += self.q_bias * dt

        s = self.p00 + self.r_measure
        k0 = self.p00 / s
        k1 = self.p10 / s
        innovation = acc_angle - self.angle
        self.angle += k0 * innovation
        self.bias += k1 * innovation

        p00 = self.p00
        p01 = self.p01
        self.p00 -= k0 * p00
        self.p01 -= k0 * p01
        self.p10 -= k1 * p00
        self.p11 -= k1 * p01
        return self.angle


class PidAxis:
    def __init__(self):
        self.integral = 0.0
        self.prev_error = 0.0
        self.prev_derivative = 0.0
        self.p_term = 0.0
        self.i_term = 0.0
        self.d_term = 0.0
        self.output = 0.0

    def reset(self):
        self.__init__()

    def compute(self, measurement, gyro_rate, dt, kp, ki, kd, deadband, max_cmd, max_integral, ff_gain):
        error = -measurement
        if abs(error) <= deadband:
            error = 0.0
        else:
            error -= math.copysign(deadband, error)

        derivative_raw = (error - self.prev_error) / dt
        derivative = 0.78 * self.prev_derivative + 0.22 * derivative_raw
        candidate_integral = self.integral + error * dt

        p = kp * error
        i = ki * candidate_integral
        d = kd * derivative
        ff = -ff_gain * gyro_rate
        raw = p + i + d + ff
        limited = clamp(raw, -max_cmd, max_cmd)

        if abs(raw - limited) < 1e-6 or sign(error) != sign(raw):
            self.integral = clamp(candidate_integral, -max_integral, max_integral)

        self.prev_error = error
        self.prev_derivative = derivative
        self.p_term = p
        self.i_term = ki * self.integral
        self.d_term = d
        self.output = limited
        return limited


def clamp(value, low, high):
    return max(low, min(high, value))


def sign(value):
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


def euler_to_quaternion(roll_deg, pitch_deg, yaw_deg=0.0):
    r = roll_deg * RAD
    p = pitch_deg * RAD
    y = yaw_deg * RAD
    cr, sr = math.cos(r / 2), math.sin(r / 2)
    cp, sp = math.cos(p / 2), math.sin(p / 2)
    cy, sy = math.cos(y / 2), math.sin(y / 2)
    return {
        "w": cr * cp * cy + sr * sp * sy,
        "x": sr * cp * cy - cr * sp * sy,
        "y": cr * sp * cy + sr * cp * sy,
        "z": cr * cp * sy - sr * sp * cy,
    }


class StabilizationSimulator:
    def __init__(self):
        self.dt = 0.01
        self.t = 0.0
        self.bump_start = -100.0
        self.last_roll = 0.0
        self.last_pitch = 0.0
        self.base_roll = 0.0
        self.base_pitch = 0.0
        self.true_roll = 0.0
        self.true_pitch = 0.0
        self.raw_roll = 0.0
        self.raw_pitch = 0.0
        self.gyro_roll = 0.0
        self.gyro_pitch = 0.0
        self.filtered_roll = 0.0
        self.filtered_pitch = 0.0
        self.roll_cmd = 0.0
        self.pitch_cmd = 0.0
        self.x_comp_deg = 0.0
        self.y_comp_deg = 0.0
        self.x_mm = 0.0
        self.y_mm = 0.0
        self.x_steps = 0
        self.y_steps = 0
        self.residual = 0.0
        self.saturated = False
        self.stable = True
        self.q = {"w": 1.0, "x": 0.0, "y": 0.0, "z": 0.0}
        self.kal_roll = OneAxisKalman()
        self.kal_pitch = OneAxisKalman()
        self.pid_roll = PidAxis()
        self.pid_pitch = PidAxis()
        self.history = deque(maxlen=420)

    def reset(self):
        self.__init__()
        for _ in range(120):
            self.step("engebeli yurume", 6.0, 0.45, True, 2.8, 0.55, 0.42, 0.35)

    def disturbance(self, profile, amp):
        t = self.t
        if profile == "sinus egim":
            roll = amp * math.sin(TAU * 0.52 * t)
            pitch = 0.7 * amp * math.cos(TAU * 0.37 * t + 0.6)
        elif profile == "ani egim":
            roll = amp if 1.2 < t % 6.0 < 3.6 else -0.35 * amp
            pitch = -0.65 * amp if 2.0 < t % 8.0 < 4.8 else 0.25 * amp
        elif profile == "karisik zemin":
            roll = 0.65 * amp * math.sin(TAU * 0.43 * t) + 0.28 * amp * math.sin(TAU * 1.7 * t + 0.4)
            pitch = 0.50 * amp * math.cos(TAU * 0.31 * t + 0.9) + 0.22 * amp * math.sin(TAU * 2.1 * t)
        else:
            roll = 0.55 * amp * math.sin(TAU * 0.80 * t) + 0.22 * amp * math.sin(TAU * 2.4 * t)
            pitch = 0.44 * amp * math.sin(TAU * 0.63 * t + 1.2) + 0.18 * amp * math.cos(TAU * 2.0 * t)

        bump_age = t - self.bump_start
        if 0.0 <= bump_age < 0.38:
            pulse = math.sin(math.pi * bump_age / 0.38)
            roll += amp * 1.35 * pulse
            pitch -= amp * 0.90 * pulse
        return roll, pitch

    def step(self, profile, amp, noise, control_on, kp, ki, kd, deadband):
        max_cmd = 8.0
        max_mm = 10.0
        mm_per_deg = 1.25
        steps_per_mm = 80.0
        ff_gain = 0.035
        max_integral = 6.0
        gate_deg = 8.0

        self.base_roll, self.base_pitch = self.disturbance(profile, amp)

        motor_tau = 0.09
        self.x_comp_deg += (self.pitch_cmd - self.x_comp_deg) * (self.dt / motor_tau)
        self.y_comp_deg += (self.roll_cmd - self.y_comp_deg) * (self.dt / motor_tau)

        flex = 0.1 * math.sin(TAU * 9.0 * self.t) * min(1.0, amp / 8.0)
        self.true_roll = self.base_roll + self.y_comp_deg + flex
        self.true_pitch = self.base_pitch + self.x_comp_deg - 0.7 * flex

        true_roll_rate = (self.true_roll - self.last_roll) / self.dt
        true_pitch_rate = (self.true_pitch - self.last_pitch) / self.dt
        self.last_roll = self.true_roll
        self.last_pitch = self.true_pitch

        spike = random.uniform(-10, 10) if random.random() < 0.006 else 0.0
        self.raw_roll = self.true_roll + random.uniform(-noise, noise) + spike
        self.raw_pitch = self.true_pitch + random.uniform(-noise * 0.9, noise * 0.9) - 0.5 * spike
        self.gyro_roll = true_roll_rate + random.uniform(-noise * 2.2, noise * 2.2) + 0.15
        self.gyro_pitch = true_pitch_rate + random.uniform(-noise * 2.0, noise * 2.0) - 0.1

        accepted_roll = self.raw_roll if abs(self.raw_roll - self.filtered_roll) < gate_deg or self.t < 0.1 else self.filtered_roll
        accepted_pitch = self.raw_pitch if abs(self.raw_pitch - self.filtered_pitch) < gate_deg or self.t < 0.1 else self.filtered_pitch
        self.filtered_roll = 0.82 * self.filtered_roll + 0.18 * accepted_roll
        self.filtered_pitch = 0.82 * self.filtered_pitch + 0.18 * accepted_pitch

        ekf_roll = self.kal_roll.update(self.filtered_roll, self.gyro_roll, self.dt)
        ekf_pitch = self.kal_pitch.update(self.filtered_pitch, self.gyro_pitch, self.dt)
        self.q = euler_to_quaternion(ekf_roll, ekf_pitch)

        if control_on:
            self.roll_cmd = self.pid_roll.compute(ekf_roll, self.gyro_roll, self.dt, kp, ki, kd, deadband, max_cmd, max_integral, ff_gain)
            self.pitch_cmd = self.pid_pitch.compute(ekf_pitch, self.gyro_pitch, self.dt, kp, ki, kd, deadband, max_cmd, max_integral, ff_gain)
        else:
            self.roll_cmd = 0.0
            self.pitch_cmd = 0.0
            self.pid_roll.reset()
            self.pid_pitch.reset()

        self.y_mm = clamp(self.roll_cmd * mm_per_deg, -max_mm, max_mm)
        self.x_mm = clamp(self.pitch_cmd * mm_per_deg, -max_mm, max_mm)
        self.y_steps = round(self.y_mm * steps_per_mm)
        self.x_steps = round(self.x_mm * steps_per_mm)
        self.saturated = abs(self.x_mm) >= max_mm or abs(self.y_mm) >= max_mm
        self.residual = math.hypot(self.true_roll, self.true_pitch)
        self.stable = self.residual < 0.75 and not self.saturated

        self.history.append({
            "t": self.t,
            "raw_roll": self.raw_roll,
            "raw_pitch": self.raw_pitch,
            "ekf_roll": ekf_roll,
            "ekf_pitch": ekf_pitch,
            "true_roll": self.true_roll,
            "true_pitch": self.true_pitch,
            "x_mm": self.x_mm,
            "y_mm": self.y_mm,
            "qw": self.q["w"],
            "qx": self.q["x"],
            "qy": self.q["y"],
            "qz": self.q["z"],
            "p": self.pid_roll.p_term,
            "i": self.pid_roll.i_term,
            "d": self.pid_roll.d_term,
            "cmd": self.roll_cmd,
        })
        self.t += self.dt


class SimApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Mama Kabı Stabilizasyon Simulasyonu")
        self.geometry("1580x940")
        self.minsize(1240, 780)
        self.configure(bg="#f8fafc")
        self.sim = StabilizationSimulator()
        self.running = True
        self.last_time = time.perf_counter()
        self.accumulator = 0.0
        self.frame_count = 0
        self.rotated_text_images = []
        self._build_style()
        self._build_ui()
        self.sim.reset()
        self.after(33, self._tick)

    def _build_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#f8fafc")
        style.configure("Panel.TFrame", background="#ffffff", relief="solid", borderwidth=1)
        style.configure("TLabel", background="#f8fafc", foreground="#0f172a", font=("Arial", 10))
        style.configure("Title.TLabel", background="#f8fafc", foreground="#0f172a", font=("Arial", 22, "bold"))
        style.configure("Muted.TLabel", background="#f8fafc", foreground="#64748b", font=("Arial", 10))
        style.configure("Metric.TLabel", background="#ffffff", foreground="#0f172a", font=("Arial", 11, "bold"))
        style.configure("PanelTitle.TLabel", background="#ffffff", foreground="#0f172a", font=("Arial", 10, "bold"))
        style.configure("TButton", font=("Arial", 10), padding=(10, 7))
        style.configure("Primary.TButton", background="#2563eb", foreground="#ffffff")
        style.map("Primary.TButton", background=[("active", "#1d4ed8")])

    def _build_ui(self):
        top = ttk.Frame(self)
        top.pack(fill="x", padx=18, pady=(14, 8))
        ttk.Label(top, text="Mama Kabı Stabilizasyonu Python Arayuzu", style="Title.TLabel").pack(anchor="w")
        ttk.Label(top, text="IMU -> on isleme -> EKF -> quaternion -> deadband/PID -> X/Y motor komutu", style="Muted.TLabel").pack(anchor="w")

        controls = ttk.Frame(self, style="Panel.TFrame")
        controls.pack(fill="x", padx=18, pady=8)
        self.run_btn = ttk.Button(controls, text="Duraklat", style="Primary.TButton", command=self._toggle)
        self.run_btn.grid(row=0, column=0, padx=8, pady=10)
        ttk.Button(controls, text="Reset", command=self._reset).grid(row=0, column=1, padx=8, pady=10)
        ttk.Button(controls, text="Bozucu Darbe", command=self._bump).grid(row=0, column=2, padx=8, pady=10)

        self.profile = tk.StringVar(value="engebeli yurume")
        profile_box = ttk.Combobox(controls, textvariable=self.profile, state="readonly", width=18)
        profile_box["values"] = ("engebeli yurume", "sinus egim", "ani egim", "karisik zemin")
        profile_box.grid(row=0, column=3, padx=8, pady=10)
        self.control_on = tk.BooleanVar(value=True)
        ttk.Checkbutton(controls, text="Kontrol aktif", variable=self.control_on).grid(row=0, column=4, padx=8, pady=10)

        self.speed = self._scale(controls, "Hiz", 0.25, 4.0, 1.0, 5)
        self.amp = self._scale(controls, "Bozucu", 1.0, 12.0, 6.0, 6)
        self.noise = self._scale(controls, "IMU gurultu", 0.0, 2.5, 0.45, 7)

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=18, pady=8)
        body.columnconfigure(0, weight=4)
        body.columnconfigure(1, weight=0)
        body.rowconfigure(0, weight=1)

        left = ttk.Frame(body, style="Panel.TFrame")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left.rowconfigure(0, weight=7)
        left.rowconfigure(1, weight=1)
        left.rowconfigure(2, weight=1)
        left.columnconfigure(0, weight=1)
        left.columnconfigure(1, weight=1)
        self.scene = tk.Canvas(left, bg="#f8fafc", highlightthickness=0, height=520)
        self.scene.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=10, pady=10)
        self.attitude_chart = tk.Canvas(left, bg="#ffffff", highlightthickness=0, height=145)
        self.attitude_chart.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.motor_chart = tk.Canvas(left, bg="#ffffff", highlightthickness=0, height=145)
        self.motor_chart.grid(row=1, column=1, sticky="nsew", padx=(0, 10), pady=(0, 10))
        self.quat_chart = tk.Canvas(left, bg="#ffffff", highlightthickness=0, height=145)
        self.quat_chart.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.pid_chart = tk.Canvas(left, bg="#ffffff", highlightthickness=0, height=145)
        self.pid_chart.grid(row=2, column=1, sticky="nsew", padx=(0, 10), pady=(0, 10))

        right = ttk.Frame(body, style="Panel.TFrame", width=300)
        right.grid(row=0, column=1, sticky="ns")
        right.grid_propagate(False)
        ttk.Label(right, text="Canli Veri", style="PanelTitle.TLabel").pack(anchor="w", padx=14, pady=(14, 8))
        self.metrics = {}
        metric_names = [
            "Raw Roll", "Raw Pitch", "EKF Roll", "EKF Pitch",
            "q.w", "q.x", "q.y", "q.z", "X hedef", "Y hedef",
            "X step", "Y step", "Residual", "Durum"
        ]
        for name in metric_names:
            row = ttk.Frame(right, style="Panel.TFrame")
            row.pack(fill="x", padx=10, pady=2)
            ttk.Label(row, text=name, style="PanelTitle.TLabel").pack(side="left", padx=7, pady=5)
            label = ttk.Label(row, text="0", style="Metric.TLabel")
            label.pack(side="right", padx=7, pady=5)
            self.metrics[name] = label

        ttk.Label(right, text="PID Ayarlari", style="PanelTitle.TLabel").pack(anchor="w", padx=14, pady=(16, 6))
        self.kp = self._vertical_scale(right, "Kp", 0.4, 5.0, 2.8)
        self.ki = self._vertical_scale(right, "Ki", 0.0, 2.0, 0.55)
        self.kd = self._vertical_scale(right, "Kd", 0.0, 1.5, 0.42)
        self.deadband = self._vertical_scale(right, "Deadband", 0.0, 1.2, 0.35)

    def _scale(self, parent, label, low, high, value, column):
        frame = ttk.Frame(parent)
        frame.grid(row=0, column=column, sticky="ew", padx=8, pady=5)
        ttk.Label(frame, text=label).pack(anchor="w")
        var = tk.DoubleVar(value=value)
        ttk.Scale(frame, variable=var, from_=low, to=high, orient="horizontal", length=150).pack(fill="x")
        return var

    def _vertical_scale(self, parent, label, low, high, value):
        frame = ttk.Frame(parent, style="Panel.TFrame")
        frame.pack(fill="x", padx=14, pady=4)
        ttk.Label(frame, text=label, style="PanelTitle.TLabel").pack(side="left", padx=8)
        var = tk.DoubleVar(value=value)
        ttk.Scale(frame, variable=var, from_=low, to=high, orient="horizontal", length=160).pack(side="right", padx=8, pady=8)
        return var

    def _toggle(self):
        self.running = not self.running
        self.run_btn.configure(text="Duraklat" if self.running else "Baslat")

    def _reset(self):
        self.sim.reset()

    def _bump(self):
        self.sim.bump_start = self.sim.t

    def _tick(self):
        now = time.perf_counter()
        elapsed = min(0.08, now - self.last_time)
        self.last_time = now
        if self.running:
            self.accumulator += elapsed * self.speed.get()
            while self.accumulator >= self.sim.dt:
                self.sim.step(
                    self.profile.get(),
                    self.amp.get(),
                    self.noise.get(),
                    self.control_on.get(),
                    self.kp.get(),
                    self.ki.get(),
                    self.kd.get(),
                    self.deadband.get(),
                )
                self.accumulator -= self.sim.dt
        self.frame_count += 1
        self._draw_scene()
        if self.frame_count % 2 == 0:
            self._draw_charts()
        self._update_metrics()
        self.after(33, self._tick)

    def _update_metrics(self):
        self.metrics["Raw Roll"].configure(text=f"{self.sim.raw_roll:.2f}")
        self.metrics["Raw Pitch"].configure(text=f"{self.sim.raw_pitch:.2f}")
        self.metrics["EKF Roll"].configure(text=f"{self.sim.kal_roll.angle:.2f}")
        self.metrics["EKF Pitch"].configure(text=f"{self.sim.kal_pitch.angle:.2f}")
        self.metrics["q.w"].configure(text=f"{self.sim.q['w']:.3f}")
        self.metrics["q.x"].configure(text=f"{self.sim.q['x']:.3f}")
        self.metrics["q.y"].configure(text=f"{self.sim.q['y']:.3f}")
        self.metrics["q.z"].configure(text=f"{self.sim.q['z']:.3f}")
        self.metrics["X hedef"].configure(text=f"{self.sim.x_mm:.2f} mm")
        self.metrics["Y hedef"].configure(text=f"{self.sim.y_mm:.2f} mm")
        self.metrics["X step"].configure(text=f"{self.sim.x_steps}")
        self.metrics["Y step"].configure(text=f"{self.sim.y_steps}")
        self.metrics["Residual"].configure(text=f"{self.sim.residual:.2f} deg")
        state = "STABLE" if self.sim.stable else ("SATURATED" if self.sim.saturated else "DENGE")
        self.metrics["Durum"].configure(text=state)

    def _draw_scene(self):
        c = self.scene
        c.delete("all")
        self.rotated_text_images.clear()
        w = max(c.winfo_width(), 920)
        h = max(c.winfo_height(), 500)
        c.create_rectangle(0, 0, w, h, fill="#f8fafc", outline="")
        for x in range(0, w, 60):
            c.create_line(x, 0, x, h, fill="#e2e8f0")
        for y in range(0, h, 60):
            c.create_line(0, y, w, y, fill="#e2e8f0")

        cx = w * 0.40
        stewart_y = h * 0.76
        bowl_y = stewart_y - 205
        base_angle = self.sim.base_roll * 0.75
        bowl_angle = clamp(self.sim.true_roll * 0.10, -2.5, 2.5)
        taban_cx, taban_cy = self._rotated_point(cx, stewart_y, 0, -42, base_angle)

        self._draw_rotated_rect(c, cx, stewart_y, 520, 56, base_angle, "#fee2e2", "#dc2626")
        self._draw_rotated_text(c, cx, stewart_y, "Stewart Platformu", base_angle, "#dc2626", ("Arial", 15, "bold"))
        self._draw_rotated_rect(c, taban_cx, taban_cy, 420, 30, base_angle, "#ffffff", "#64748b")
        self._draw_rotated_text(c, taban_cx, taban_cy, "uydu tabanı", base_angle, "#0f172a", ("Arial", 12, "bold"))

        self._draw_bowl(c, cx, bowl_y, bowl_angle, self.sim.true_pitch)
        self._draw_support_rods(c, cx, bowl_y, bowl_angle, taban_cx, taban_cy, base_angle)
        self._draw_actuator(c, cx - 220, stewart_y - 150, self.sim.y_mm, "Y motor", "#16a34a")
        self._draw_actuator(c, cx + 220, stewart_y - 150, self.sim.x_mm, "X motor", "#2563eb")
        c.create_text(cx - 420, stewart_y - 12, text=f"roll {self.sim.true_roll:.2f} deg", anchor="w", fill="#0f172a", font=("Arial", 13, "bold"))
        c.create_text(cx - 420, stewart_y + 18, text=f"pitch {self.sim.true_pitch:.2f} deg", anchor="w", fill="#0f172a", font=("Arial", 13, "bold"))

        x0 = w * 0.71
        y0 = 30
        box_w = min(260, w * 0.25)
        stack = [
            ("IMU", f"raw {self.sim.raw_roll:.2f} / {self.sim.raw_pitch:.2f} deg", "#d97706"),
            ("EKF", f"roll {self.sim.kal_roll.angle:.2f} | pitch {self.sim.kal_pitch.angle:.2f}", "#2563eb"),
            ("Quaternion", f"q {self.sim.q['w']:.3f}, {self.sim.q['x']:.3f}, {self.sim.q['y']:.3f}, {self.sim.q['z']:.3f}", "#7c3aed"),
            ("PID", f"cmd {self.sim.roll_cmd:.2f} / {self.sim.pitch_cmd:.2f} deg", "#dc2626"),
            ("Motor", f"X {self.sim.x_steps} step | Y {self.sim.y_steps} step", "#16a34a"),
        ]
        for i, (title, value, color) in enumerate(stack):
            y = y0 + i * 60
            c.create_rectangle(x0, y, x0 + box_w, y + 44, fill="#ffffff", outline=color, width=2)
            c.create_text(x0 + 12, y + 14, text=title, anchor="w", fill=color, font=("Arial", 10, "bold"))
            c.create_text(x0 + 12, y + 33, text=value, anchor="w", fill="#64748b", font=("Arial", 8))
            if i < len(stack) - 1:
                c.create_line(x0 + box_w / 2, y + 44, x0 + box_w / 2, y + 60, fill="#94a3b8", width=2, arrow=tk.LAST)

    def _draw_rotated_rect(self, c, cx, cy, width, height, angle_deg, fill, outline):
        a = angle_deg * RAD
        pts = []
        for x, y in [(-width / 2, -height / 2), (width / 2, -height / 2), (width / 2, height / 2), (-width / 2, height / 2)]:
            pts.extend((cx + x * math.cos(a) - y * math.sin(a), cy + x * math.sin(a) + y * math.cos(a)))
        c.create_polygon(pts, fill=fill, outline=outline, width=3)

    def _draw_rotated_text(self, c, x, y, text, angle_deg, fill, font):
        if Image is None or ImageTk is None:
            try:
                c.create_text(x, y, text=text, fill=fill, font=font, angle=angle_deg)
            except tk.TclError:
                c.create_text(x, y, text=text, fill=fill, font=font)
            return

        family, size, *style = font
        bold = "bold" in style
        font_path = r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf"
        try:
            pil_font = ImageFont.truetype(font_path, size)
        except OSError:
            pil_font = ImageFont.load_default()

        probe = Image.new("RGBA", (1, 1), (255, 255, 255, 0))
        probe_draw = ImageDraw.Draw(probe)
        bbox = probe_draw.textbbox((0, 0), text, font=pil_font)
        text_w = max(1, bbox[2] - bbox[0])
        text_h = max(1, bbox[3] - bbox[1])
        pad = 12
        img = Image.new("RGBA", (text_w + pad * 2, text_h + pad * 2), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        draw.text((pad - bbox[0], pad - bbox[1]), text, fill=self._hex_to_rgba(fill), font=pil_font)
        rotated = img.rotate(-angle_deg, expand=True, resample=Image.Resampling.BICUBIC)
        photo = ImageTk.PhotoImage(rotated)
        self.rotated_text_images.append(photo)
        c.create_image(x, y, image=photo)

    @staticmethod
    def _hex_to_rgba(color):
        if isinstance(color, str) and color.startswith("#") and len(color) == 7:
            return (
                int(color[1:3], 16),
                int(color[3:5], 16),
                int(color[5:7], 16),
                255,
            )
        if isinstance(color, tuple):
            return color
        return (15, 23, 42, 255)

    def _rotated_point(self, cx, cy, x, y, angle_deg):
        a = angle_deg * RAD
        return (
            cx + x * math.cos(a) - y * math.sin(a),
            cy + x * math.sin(a) + y * math.cos(a),
        )

    def _draw_support_rods(self, c, cx, bowl_y, bowl_angle, base_cx, base_cy, base_angle):
        for side in (-1, 1):
            bx, by = self._rotated_point(base_cx, base_cy, side * 125, -18, base_angle)
            tx, ty = self._rotated_point(cx, bowl_y, side * 128, -36, bowl_angle)
            c.create_line(bx, by, tx, ty, fill="#475569", width=5)
            c.create_oval(bx - 5, by - 5, bx + 5, by + 5, fill="#475569", outline="")
            c.create_oval(tx - 5, ty - 5, tx + 5, ty + 5, fill="#475569", outline="")

    def _draw_bowl(self, c, cx, cy, roll_deg, pitch_deg):
        angle = roll_deg * RAD

        def pt(x, y):
            return (
                cx + x * math.cos(angle) - y * math.sin(angle),
                cy + x * math.sin(angle) + y * math.cos(angle),
            )

        def flat(points):
            out = []
            for x, y in points:
                px, py = pt(x, y)
                out.extend((px, py))
            return out

        width = 280
        rim_y = -52
        rim_h = 48 + abs(pitch_deg) * 0.7
        lower = [(-width / 2, rim_y)]
        for i in range(1, 34):
            u = i / 34
            x = -width / 2 + width * u
            y = rim_y + 115 * math.sin(math.pi * u)
            lower.append((x, y))
        lower.append((width / 2, rim_y))

        c.create_polygon(flat(lower), fill="#dbeafe", outline="#2563eb", width=3, smooth=True)

        rim = []
        for i in range(42):
            a = TAU * i / 42
            rim.append((math.cos(a) * width / 2, rim_y + math.sin(a) * rim_h / 2))
        c.create_polygon(flat(rim), fill="#dbeafe", outline="#2563eb", width=3, smooth=True)

        food = []
        for i in range(36):
            a = TAU * i / 36
            food.append((math.cos(a) * 82, rim_y + 8 + math.sin(a) * 16))
        c.create_polygon(flat(food), fill="#bfdbfe", outline="", smooth=True)

        label_x, label_y = pt(0, rim_y - 55)
        self._draw_rotated_text(c, label_x, label_y, "Mama kabı", roll_deg, "#0f172a", ("Arial", 13, "bold"))

    def _draw_actuator(self, c, x, y, mm, label, color):
        length = 75 + mm * 4
        bar_base = y + 30
        c.create_line(x, bar_base, x, y - 70, fill="#94a3b8", width=7)
        c.create_line(x, bar_base, x, bar_base - length, fill=color, width=7)
        c.create_text(x, y + 58, text=label, fill=color, font=("Arial", 11, "bold"))
        c.create_text(x, y + 76, text=f"{mm:.2f} mm", fill="#64748b", font=("Arial", 10))

    def _draw_charts(self):
        self._draw_chart(self.attitude_chart, "Roll / Pitch Kestirimi", [
            ("raw roll", "#d97706", lambda p: p["raw_roll"]),
            ("EKF roll", "#2563eb", lambda p: p["ekf_roll"]),
            ("plant roll", "#16a34a", lambda p: p["true_roll"]),
            ("plant pitch", "#7c3aed", lambda p: p["true_pitch"]),
        ], -14, 14)
        self._draw_chart(self.motor_chart, "Motor Komutlari", [
            ("X mm", "#2563eb", lambda p: p["x_mm"]),
            ("Y mm", "#16a34a", lambda p: p["y_mm"]),
            ("cmd", "#dc2626", lambda p: p["cmd"]),
        ], -11, 11)
        self._draw_chart(self.quat_chart, "Quaternion", [
            ("qw", "#2563eb", lambda p: p["qw"]),
            ("qx", "#16a34a", lambda p: p["qx"]),
            ("qy", "#d97706", lambda p: p["qy"]),
            ("qz", "#7c3aed", lambda p: p["qz"]),
        ], -0.25, 1.08)
        self._draw_chart(self.pid_chart, "PID Bilesenleri", [
            ("P", "#2563eb", lambda p: p["p"]),
            ("I", "#16a34a", lambda p: p["i"]),
            ("D", "#d97706", lambda p: p["d"]),
            ("cmd", "#dc2626", lambda p: p["cmd"]),
        ], -10, 10)

    def _draw_chart(self, c, title, series, min_y, max_y):
        c.delete("all")
        w = max(c.winfo_width(), 420)
        h = max(c.winfo_height(), 180)
        c.create_rectangle(0, 0, w, h, fill="#ffffff", outline="")
        c.create_text(12, 12, text=title, anchor="nw", fill="#0f172a", font=("Arial", 11, "bold"))
        x0, y0, x1, y1 = 34, 42, w - 34, h - 28
        for i in range(6):
            x = x0 + (x1 - x0) * i / 5
            c.create_line(x, y0, x, y1, fill="#e2e8f0")
        for i in range(5):
            y = y1 - (y1 - y0) * i / 4
            c.create_line(x0, y, x1, y, fill="#e2e8f0")
            val = min_y + (max_y - min_y) * i / 4
            c.create_text(8, y, text=f"{val:.1f}", anchor="w", fill="#64748b", font=("Arial", 8))
        c.create_line(x0, y0, x0, y1, x1, y1, fill="#64748b", width=2)
        if not self.sim.history:
            return
        def py(v):
            return y1 - (clamp(v, min_y, max_y) - min_y) / (max_y - min_y) * (y1 - y0)

        samples = list(self.sim.history)
        if samples:
            max_t = samples[-1]["t"]
            samples = [p for p in samples if p["t"] >= max(0.0, max_t - 8.0)]
        stride = max(1, len(samples) // 220)
        visible = samples[::stride]
        lx = x0 + 8
        for name, color, getter in series:
            pts = []
            count = max(1, len(visible) - 1)
            for index, p in enumerate(visible):
                x = x0 + (x1 - x0) * index / count
                pts.extend((x, py(getter(p))))
            if len(pts) >= 4:
                c.create_line(*pts, fill=color, width=2)
            c.create_line(lx, y0 + 13, lx + 20, y0 + 13, fill=color, width=3)
            c.create_text(lx + 25, y0 + 13, text=name, anchor="w", fill="#0f172a", font=("Arial", 8))
            lx += 90


if __name__ == "__main__":
    app = SimApp()
    app.mainloop()
