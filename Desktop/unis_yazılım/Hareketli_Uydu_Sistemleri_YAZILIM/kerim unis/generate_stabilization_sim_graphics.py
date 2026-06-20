from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


OUT_DIR = Path("KTR") / "simulasyon_algoritma_grafikleri"
OUT_DIR.mkdir(exist_ok=True)
for stale in OUT_DIR.glob("08_*inverse_kinematics.png"):
    if stale.exists():
        stale.unlink()


W, H = 1600, 1000
BG = (248, 250, 252)
INK = (15, 23, 42)
MUTED = (71, 85, 105)
GRID = (226, 232, 240)
AXIS = (100, 116, 139)
BLUE = (37, 99, 235)
GREEN = (22, 163, 74)
RED = (220, 38, 38)
ORANGE = (217, 119, 6)
PURPLE = (124, 58, 237)
CYAN = (8, 145, 178)
PINK = (219, 39, 119)
YELLOW = (202, 138, 4)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for p in candidates:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()


FONT_TITLE = font(38, True)
FONT_SUB = font(23, False)
FONT_LABEL = font(21, True)
FONT_TEXT = font(18, False)
FONT_SMALL = font(16, False)


def canvas(title: str, subtitle: str = "") -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((70, 42), title, fill=INK, font=FONT_TITLE)
    if subtitle:
        d.text((70, 92), subtitle, fill=MUTED, font=FONT_SUB)
    d.line((70, 132, W - 70, 132), fill=(203, 213, 225), width=3)
    return img, d


def rounded(d: ImageDraw.ImageDraw, xy, fill, outline, width=3, radius=18):
    d.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def plot_area(
    d: ImageDraw.ImageDraw,
    xy: tuple[int, int, int, int],
    title: str,
    x_label: str,
    y_label: str,
    xlim: tuple[float, float],
    ylim: tuple[float, float],
    x_ticks: int = 6,
    y_ticks: int = 5,
):
    x0, y0, x1, y1 = xy
    rounded(d, (x0 - 18, y0 - 48, x1 + 18, y1 + 55), fill=(255, 255, 255), outline=(203, 213, 225), width=2, radius=14)
    d.text((x0, y0 - 39), title, fill=INK, font=FONT_LABEL)
    for i in range(x_ticks + 1):
        x = x0 + (x1 - x0) * i / x_ticks
        d.line((x, y0, x, y1), fill=GRID, width=1)
        val = xlim[0] + (xlim[1] - xlim[0]) * i / x_ticks
        d.text((x - 18, y1 + 12), f"{val:.1f}", fill=MUTED, font=FONT_SMALL)
    for i in range(y_ticks + 1):
        y = y1 - (y1 - y0) * i / y_ticks
        d.line((x0, y, x1, y), fill=GRID, width=1)
        val = ylim[0] + (ylim[1] - ylim[0]) * i / y_ticks
        d.text((x0 - 55, y - 10), f"{val:.1f}", fill=MUTED, font=FONT_SMALL)
    d.line((x0, y1, x1, y1), fill=AXIS, width=3)
    d.line((x0, y0, x0, y1), fill=AXIS, width=3)
    d.text(((x0 + x1) // 2 - 40, y1 + 34), x_label, fill=MUTED, font=FONT_SMALL)
    d.text((x0 - 60, y0 - 28), y_label, fill=MUTED, font=FONT_SMALL)

    def tx(x):
        return x0 + (np.asarray(x) - xlim[0]) / (xlim[1] - xlim[0]) * (x1 - x0)

    def ty(y):
        return y1 - (np.asarray(y) - ylim[0]) / (ylim[1] - ylim[0]) * (y1 - y0)

    return tx, ty


def draw_series(d: ImageDraw.ImageDraw, tx, ty, x, y, color, width=4):
    pts = []
    xs = tx(x)
    ys = ty(y)
    for px, py in zip(xs, ys):
        if np.isfinite(px) and np.isfinite(py):
            pts.append((float(px), float(py)))
    if len(pts) > 1:
        d.line(pts, fill=color, width=width, joint="curve")


def legend(d: ImageDraw.ImageDraw, items, x: int, y: int):
    for i, (name, color) in enumerate(items):
        yy = y + i * 30
        d.line((x, yy + 11, x + 42, yy + 11), fill=color, width=5)
        d.text((x + 55, yy), name, fill=INK, font=FONT_SMALL)


def bar_chart(d, xy, title, labels, values, colors, unit="ms"):
    x0, y0, x1, y1 = xy
    rounded(d, (x0 - 18, y0 - 48, x1 + 18, y1 + 55), fill=(255, 255, 255), outline=(203, 213, 225), width=2, radius=14)
    d.text((x0, y0 - 39), title, fill=INK, font=FONT_LABEL)
    maxv = max(values) * 1.25
    n = len(values)
    gap = 18
    bw = (x1 - x0 - gap * (n - 1)) / n
    for i, (lab, val, col) in enumerate(zip(labels, values, colors)):
        bx0 = x0 + i * (bw + gap)
        bh = (val / maxv) * (y1 - y0)
        d.rounded_rectangle((bx0, y1 - bh, bx0 + bw, y1), radius=9, fill=col)
        d.text((bx0 + 5, y1 - bh - 28), f"{val:.2f} {unit}", fill=INK, font=FONT_SMALL)
        d.text((bx0 + 3, y1 + 12), lab, fill=MUTED, font=FONT_SMALL)
    d.line((x0, y1, x1, y1), fill=AXIS, width=3)
    d.line((x0, y0, x0, y1), fill=AXIS, width=3)


np.random.seed(7)
dt = 0.01
t = np.arange(0, 8, dt)
n = len(t)

disturbance = 6.0 * np.sin(2 * np.pi * 0.55 * t) * np.exp(-0.18 * t)
disturbance += np.where((t > 2.2) & (t < 2.55), 5.5 * np.sin(np.pi * (t - 2.2) / 0.35), 0)
disturbance += np.where((t > 5.2) & (t < 5.55), -4.0 * np.sin(np.pi * (t - 5.2) / 0.35), 0)
true_roll = disturbance
true_pitch = 3.8 * np.sin(2 * np.pi * 0.42 * t + 0.8) * np.exp(-0.13 * t) + np.where(t > 4.4, 1.5, 0)
gyro_roll = np.gradient(true_roll, dt) + 0.25 + np.random.normal(0, 1.0, n)
raw_roll = true_roll + np.random.normal(0, 0.85, n)
raw_pitch = true_pitch + np.random.normal(0, 0.75, n)
for idx in [120, 310, 486, 650]:
    raw_roll[idx : idx + 4] += np.random.choice([-1, 1]) * np.linspace(7, 12, 4)


def lowpass_outlier(x, alpha=0.90, gate=5.0):
    y = np.zeros_like(x)
    rejected = np.zeros_like(x, dtype=bool)
    y[0] = x[0]
    for i in range(1, len(x)):
        if abs(x[i] - y[i - 1]) > gate:
            y[i] = y[i - 1]
            rejected[i] = True
        else:
            y[i] = alpha * y[i - 1] + (1 - alpha) * x[i]
    return y, rejected


filtered_roll, rejected = lowpass_outlier(raw_roll)
filtered_pitch, _ = lowpass_outlier(raw_pitch, alpha=0.88, gate=4.5)


def kalman_angle(acc_angle, gyro_rate, q_angle=0.002, q_bias=0.004, r_measure=0.55):
    angle = acc_angle[0]
    bias = 0.0
    P = np.zeros((2, 2))
    out = np.zeros_like(acc_angle)
    for i in range(len(acc_angle)):
        rate = gyro_rate[i] - bias
        angle += dt * rate
        P[0, 0] += dt * (dt * P[1, 1] - P[0, 1] - P[1, 0] + q_angle)
        P[0, 1] -= dt * P[1, 1]
        P[1, 0] -= dt * P[1, 1]
        P[1, 1] += q_bias * dt
        S = P[0, 0] + r_measure
        K = np.array([P[0, 0] / S, P[1, 0] / S])
        y = acc_angle[i] - angle
        angle += K[0] * y
        bias += K[1] * y
        P00, P01 = P[0, 0], P[0, 1]
        P[0, 0] -= K[0] * P00
        P[0, 1] -= K[0] * P01
        P[1, 0] -= K[1] * P00
        P[1, 1] -= K[1] * P01
        out[i] = angle
    return out


kalman_roll = kalman_angle(raw_roll, gyro_roll)
gyro_pitch = np.gradient(true_pitch, dt) - 0.15 + np.random.normal(0, 0.9, n)
kalman_pitch = kalman_angle(raw_pitch, gyro_pitch)


def simulate_pid(feedforward=False, antiwindup=True, command_limit=12.0, big_disturbance=False):
    theta = 0.0
    omega = 0.0
    integ = 0.0
    prev_e = 0.0
    th = []
    uu = []
    ii = []
    wn = 8.5
    zeta = 0.62
    kp, ki, kd = 3.6, 1.1, 0.55
    for i, ti in enumerate(t):
        dacc = 9.0 * math.sin(2 * math.pi * 0.55 * ti) * math.exp(-0.18 * ti)
        if 2.2 < ti < 2.5:
            dacc += 45 if not big_disturbance else 90
        if 5.2 < ti < 5.55:
            dacc -= 35 if not big_disturbance else 70
        e = -theta
        dedt = (e - prev_e) / dt
        prev_e = e
        integ_candidate = integ + e * dt
        u = kp * e + ki * integ_candidate + kd * dedt
        if feedforward:
            u += -1.15 * omega
        u_sat = np.clip(u, -command_limit, command_limit)
        if (not antiwindup) or abs(u - u_sat) < 1e-9 or np.sign(e) != np.sign(u):
            integ = integ_candidate
        theta_ddot = -2 * zeta * wn * omega - wn * wn * theta + 9.5 * u_sat + dacc
        omega += theta_ddot * dt
        theta += omega * dt
        th.append(theta)
        uu.append(u_sat)
        ii.append(integ)
    return np.array(th), np.array(uu), np.array(ii)


pid_theta, pid_u, pid_i = simulate_pid(feedforward=False)
ff_theta, ff_u, _ = simulate_pid(feedforward=True)
sat_theta_aw, sat_u_aw, sat_i_aw = simulate_pid(feedforward=False, antiwindup=True, command_limit=4.2, big_disturbance=True)
sat_theta_no, sat_u_no, sat_i_no = simulate_pid(feedforward=False, antiwindup=False, command_limit=4.2, big_disturbance=True)


def simulate_saturation_step(antiwindup=True):
    theta = 0.0
    omega = 0.0
    integ = 0.0
    prev_e = 0.0
    theta_hist = []
    u_raw_hist = []
    u_sat_hist = []
    i_hist = []
    limit = 4.0
    kp, ki, kd = 2.8, 1.8, 0.35
    wn, zeta = 5.0, 0.72
    ref = np.where((t > 0.7) & (t < 3.7), 7.0, 0.0)
    for r in ref:
        e = r - theta
        dedt = (e - prev_e) / dt
        prev_e = e
        integ_candidate = integ + e * dt
        u_raw = kp * e + ki * integ_candidate + kd * dedt
        u_sat = np.clip(u_raw, -limit, limit)
        if (not antiwindup) or abs(u_raw - u_sat) < 1e-9 or np.sign(e) != np.sign(u_raw):
            integ = integ_candidate
        theta_ddot = -2 * zeta * wn * omega - wn * wn * theta + 8.0 * u_sat
        omega += theta_ddot * dt
        theta += omega * dt
        theta_hist.append(theta)
        u_raw_hist.append(u_raw)
        u_sat_hist.append(u_sat)
        i_hist.append(integ)
    return ref, np.array(theta_hist), np.array(u_raw_hist), np.array(u_sat_hist), np.array(i_hist)


sat_ref, sat_step_aw, sat_raw_aw, sat_cmd_aw, sat_int_aw = simulate_saturation_step(True)
_, sat_step_no, sat_raw_no, sat_cmd_no, sat_int_no = simulate_saturation_step(False)


def quat_from_euler(roll, pitch, yaw):
    cr, sr = np.cos(roll / 2), np.sin(roll / 2)
    cp, sp = np.cos(pitch / 2), np.sin(pitch / 2)
    cy, sy = np.cos(yaw / 2), np.sin(yaw / 2)
    qw = cr * cp * cy + sr * sp * sy
    qx = sr * cp * cy - cr * sp * sy
    qy = cr * sp * cy + sr * cp * sy
    qz = cr * cp * sy - sr * sp * cy
    return qw, qx, qy, qz


roll_rad = np.deg2rad(kalman_roll)
pitch_rad = np.deg2rad(kalman_pitch)
yaw_rad = np.deg2rad(8 * np.sin(2 * np.pi * 0.12 * t))
qw, qx, qy, qz = quat_from_euler(roll_rad, pitch_rad, yaw_rad)
qnorm = np.sqrt(qw * qw + qx * qx + qy * qy + qz * qz)

error = -kalman_roll
deadband_deg = 0.55
deadband_cmd = np.where(np.abs(error) <= deadband_deg, 0.0, error - np.sign(error) * deadband_deg)


def xy_stabilizer_offsets(roll_deg, pitch_deg):
    arm_mm = 75.0
    x_mm = arm_mm * np.tan(np.deg2rad(-pitch_deg))
    y_mm = arm_mm * np.tan(np.deg2rad(-roll_deg))
    return np.column_stack([x_mm, y_mm])


desired_roll = -np.clip(kalman_roll, -5, 5)
desired_pitch = -np.clip(kalman_pitch, -4, 4)
xy_offsets = xy_stabilizer_offsets(desired_roll, desired_pitch)
steps_per_mm = 80.0
steps = np.round(xy_offsets * steps_per_mm)
motor_angle = steps / 200.0 * 360.0 / 16.0


def save(img: Image.Image, name: str):
    img.save(OUT_DIR / name, quality=95)


# 1. Veri dogrulama ve filtreleme
img, d = canvas("01 - Veri Doğrulama ve Filtreleme", "BNO055 ham roll verisi; aykırı değer reddi ve alçak geçiren filtre çıkışı")
tx, ty = plot_area(d, (130, 220, 1180, 820), "Ham veri -> geçerli veri -> filtrelenmiş açı", "zaman (s)", "roll (deg)", (0, 8), (-12, 14))
draw_series(d, tx, ty, t, raw_roll, ORANGE, 3)
draw_series(d, tx, ty, t, filtered_roll, BLUE, 5)
draw_series(d, tx, ty, t, true_roll, GREEN, 4)
for x, y in zip(t[rejected], raw_roll[rejected]):
    px, py = tx([x])[0], ty([y])[0]
    d.ellipse((px - 5, py - 5, px + 5, py + 5), fill=RED)
legend(d, [("BNO055 ham", ORANGE), ("Filtre çıkışı", BLUE), ("Gerçek/simülasyon", GREEN), ("Reddedilen ölçüm", RED)], 1230, 280)
rounded(d, (1230, 455, 1515, 610), (255, 255, 255), BLUE, 2)
d.text((1250, 475), "Amaç", fill=INK, font=FONT_LABEL)
d.text((1250, 515), "Sensör gürültüsü ve ani\nbozuk paketler PID'ye\nulaşmadan bastırılır.", fill=MUTED, font=FONT_TEXT)
save(img, "01_veri_dogrulama_filtreleme.png")

# 2. Kalman / EKF
img, d = canvas("02 - Kalman / EKF Açı Kestirimi", "Gyro tahmini + ivme ölçümü birleştirilerek daha kararlı roll/pitch değeri üretilir")
tx, ty = plot_area(d, (130, 210, 1180, 545), "Roll kestirimi", "zaman (s)", "deg", (0, 8), (-10, 12))
draw_series(d, tx, ty, t, raw_roll, ORANGE, 2)
draw_series(d, tx, ty, t, kalman_roll, BLUE, 5)
draw_series(d, tx, ty, t, true_roll, GREEN, 4)
tx2, ty2 = plot_area(d, (130, 645, 1180, 870), "Pitch kestirimi", "zaman (s)", "deg", (0, 8), (-7, 7))
draw_series(d, tx2, ty2, t, raw_pitch, ORANGE, 2)
draw_series(d, tx2, ty2, t, kalman_pitch, BLUE, 5)
draw_series(d, tx2, ty2, t, true_pitch, GREEN, 4)
legend(d, [("Ölçüm", ORANGE), ("Kalman/EKF", BLUE), ("Gerçek/simülasyon", GREEN)], 1230, 315)
rounded(d, (1230, 475, 1515, 670), (255, 255, 255), PURPLE, 2)
d.text((1250, 495), "Çıkış", fill=INK, font=FONT_LABEL)
d.text((1250, 535), "PID bloğuna giden\nstabil roll/pitch açısı.\nGürültü azalır, gecikme\nkontrollü kalır.", fill=MUTED, font=FONT_TEXT)
save(img, "02_kalman_ekf_aci_kestirimi.png")

# 3. Quaternion
img, d = canvas("03 - Quaternion Yönelim Gösterimi", "Euler açıları iç hesapta quaternion'a çevrilir; normun 1 kalması yönelim tutarlılığını gösterir")
tx, ty = plot_area(d, (130, 210, 1180, 625), "Quaternion bileşenleri", "zaman (s)", "q", (0, 8), (-0.16, 1.08))
draw_series(d, tx, ty, t, qw, BLUE, 4)
draw_series(d, tx, ty, t, qx, GREEN, 4)
draw_series(d, tx, ty, t, qy, ORANGE, 4)
draw_series(d, tx, ty, t, qz, PURPLE, 4)
draw_series(d, tx, ty, t, qnorm, RED, 4)
tx2, ty2 = plot_area(d, (130, 735, 1180, 870), "Euler izleme çıktısı", "zaman (s)", "deg", (0, 8), (-9, 9))
draw_series(d, tx2, ty2, t, kalman_roll, BLUE, 4)
draw_series(d, tx2, ty2, t, kalman_pitch, GREEN, 4)
legend(d, [("qw", BLUE), ("qx", GREEN), ("qy", ORANGE), ("qz", PURPLE), ("norm", RED), ("roll/pitch", CYAN)], 1230, 300)
rounded(d, (1230, 545, 1515, 730), (255, 255, 255), PURPLE, 2)
d.text((1250, 565), "Neden?", fill=INK, font=FONT_LABEL)
d.text((1250, 605), "3B yönelim hesabında\ntekillik/gimbal-lock riski\nazalır; kontrol için tekrar\nroll-pitch okunur.", fill=MUTED, font=FONT_TEXT)
save(img, "03_quaternion_yonelim.png")

# 4. Deadband
img, d = canvas("04 - Ölü Bant Algoritması", "Küçük hatalarda motoru oynatmayarak titreşim, ses ve gereksiz akım tüketimi azaltılır")
e = np.linspace(-4, 4, 500)
out = np.where(np.abs(e) <= deadband_deg, 0.0, e - np.sign(e) * deadband_deg)
tx, ty = plot_area(d, (130, 220, 740, 820), "Hata -> komut karakteristiği", "hata (deg)", "çıkış", (-4, 4), (-4, 4))
draw_series(d, tx, ty, e, out, BLUE, 6)
px1, px2 = tx([-deadband_deg, deadband_deg])
d.rectangle((px1, 220, px2, 820), fill=(220, 252, 231), outline=None)
draw_series(d, tx, ty, e, out, BLUE, 6)
d.text((tx([-0.45])[0], 245), "ölü bant", fill=GREEN, font=FONT_SMALL)
tx2, ty2 = plot_area(d, (890, 220, 1470, 820), "Zaman alanında etkisi", "zaman (s)", "komut", (0, 8), (-8, 8))
draw_series(d, tx2, ty2, t, error, ORANGE, 3)
draw_series(d, tx2, ty2, t, deadband_cmd, BLUE, 5)
legend(d, [("PID öncesi hata", ORANGE), ("Ölü bant sonrası", BLUE)], 960, 265)
save(img, "04_olu_bant.png")

# 5. PID kapali cevrim
img, d = canvas("05 - PID Kapalı Çevrim Stabilizasyonu", "Referans 0 derece; PID mama kabını bozucu roll hareketine karşı dengede tutar")
tx, ty = plot_area(d, (130, 220, 1180, 615), "Mama kabı açısı", "zaman (s)", "roll (deg)", (0, 8), (-7, 8))
draw_series(d, tx, ty, t, true_roll, ORANGE, 4)
draw_series(d, tx, ty, t, pid_theta, BLUE, 5)
draw_series(d, tx, ty, t, np.zeros_like(t), GREEN, 3)
tx2, ty2 = plot_area(d, (130, 735, 1180, 875), "PID kontrol çıkışı", "zaman (s)", "komut", (0, 8), (-13, 13))
draw_series(d, tx2, ty2, t, pid_u, RED, 4)
legend(d, [("Dış bozucu", ORANGE), ("PID sonrası artık açı", BLUE), ("0 derece referans", GREEN), ("PID komutu", RED)], 1230, 310)
save(img, "05_pid_kapali_cevrim.png")

# 6. Feedforward
img, d = canvas("06 - Gyro Feedforward Etkisi", "Ani açısal hız geldiğinde sadece hata oluşmasını beklemek yerine erken karşı komut üretilir")
tx, ty = plot_area(d, (130, 220, 1180, 820), "PID vs PID + gyro feedforward", "zaman (s)", "artık açı (deg)", (0, 8), (-2.2, 2.6))
draw_series(d, tx, ty, t, pid_theta, ORANGE, 5)
draw_series(d, tx, ty, t, ff_theta, BLUE, 5)
d.line((tx([2.2])[0], ty([-2.2])[0], tx([2.2])[0], ty([2.6])[0]), fill=RED, width=3)
d.text((tx([2.28])[0], ty([2.25])[0]), "ani bozucu", fill=RED, font=FONT_SMALL)
legend(d, [("PID", ORANGE), ("PID + feedforward", BLUE)], 1230, 300)
rounded(d, (1230, 420, 1515, 615), (255, 255, 255), BLUE, 2)
d.text((1250, 440), "Sonuç", fill=INK, font=FONT_LABEL)
d.text((1250, 480), "Tepe hata ve toparlanma\nsüresi azalır. Mama kabı\nani sarsıntıda daha az\nsalınır.", fill=MUTED, font=FONT_TEXT)
save(img, "06_gyro_feedforward.png")

# 7. Saturation / anti-windup
img, d = canvas("07 - Saturasyon ve Anti-Windup", "Motor sınırı aşılınca komut kırpılır; integral şişmesi anti-windup ile engellenir")
cmd_ylim = (-14, 22)
tx, ty = plot_area(d, (130, 210, 1180, 530), "Ham PID komutu ve motor limiti", "zaman (s)", "komut", (0, 8), cmd_ylim)
draw_series(d, tx, ty, t, np.clip(sat_raw_no, cmd_ylim[0], cmd_ylim[1]), ORANGE, 4)
draw_series(d, tx, ty, t, sat_cmd_aw, BLUE, 5)
d.line((130, ty([4.0])[0], 1180, ty([4.0])[0]), fill=RED, width=2)
d.line((130, ty([-4.0])[0], 1180, ty([-4.0])[0]), fill=RED, width=2)
tx2, ty2 = plot_area(d, (130, 650, 1180, 870), "Integral şişmesi", "zaman (s)", "integral", (0, 8), (-2, 18))
draw_series(d, tx2, ty2, t, sat_int_no, ORANGE, 5)
draw_series(d, tx2, ty2, t, sat_int_aw, BLUE, 5)
legend(d, [("Anti-windup yok", ORANGE), ("Anti-windup var / sınırlı", BLUE), ("Motor limiti", RED)], 1230, 310)
save(img, "07_saturasyon_anti_windup.png")

# 8. X/Y stabilizer kinematics
img, d = canvas("08 - X/Y Stabilizatör Kinematiği", "Roll-pitch düzeltme isteği iki eksenli denge mekanizması için X/Y mm hedefine çevrilir")
tx, ty = plot_area(d, (130, 220, 1180, 820), "X/Y denge ekseni hedefleri", "zaman (s)", "hedef (mm)", (0, 8), (-9, 9))
draw_series(d, tx, ty, t, xy_offsets[:, 0], BLUE, 5)
draw_series(d, tx, ty, t, xy_offsets[:, 1], GREEN, 5)
legend(d, [("X ekseni hedefi", BLUE), ("Y ekseni hedefi", GREEN)], 1230, 260)
rounded(d, (1230, 485, 1515, 700), (255, 255, 255), PURPLE, 2)
d.text((1250, 505), "Model", fill=INK, font=FONT_LABEL)
d.text((1250, 545), "Dış zemin bozucusu\nkontrol içinde yoktur.\nKomut sadece X/Y denge\nmotorlarına gider.", fill=MUTED, font=FONT_TEXT)
save(img, "08_xy_stabilizator_kinematigi.png")

# 9. Motor step conversion
img, d = canvas("09 - Motor Açısı / Step Dönüşümü", "X/Y stabilizatör mm hedefi DRV8825-NEMA17 için step ve motor açısına çevrilir")
tx, ty = plot_area(d, (130, 210, 1180, 530), "Aktüatör hedefi -> step", "zaman (s)", "step", (0, 8), (-750, 750))
draw_series(d, tx, ty, t, steps[:, 0], BLUE, 4)
draw_series(d, tx, ty, t, steps[:, 1], GREEN, 4)
tx2, ty2 = plot_area(d, (130, 650, 1180, 870), "Step -> motor açısı", "zaman (s)", "motor açısı (deg)", (0, 8), (-90, 90))
draw_series(d, tx2, ty2, t, motor_angle[:, 0], BLUE, 4)
draw_series(d, tx2, ty2, t, motor_angle[:, 1], GREEN, 4)
legend(d, [("X motoru", BLUE), ("Y motoru", GREEN)], 1230, 310)
rounded(d, (1230, 485, 1515, 650), (255, 255, 255), BLUE, 2)
d.text((1250, 505), "Formül", fill=INK, font=FONT_LABEL)
d.text((1250, 545), "step = mm * step/mm\nmotor açı = step / mikrostep\noranına göre hesaplanır.", fill=MUTED, font=FONT_TEXT)
save(img, "09_motor_step_donusumu.png")

# 10. Genel simulasyon ozeti
img, d = canvas("10 - Genel Stabilizasyon Simülasyonu", "Dış zemin bozucusu kontrol dışındadır; zincir BNO055 -> filtre/EKF -> kontrolcü -> X/Y stabilizatör motorlarıdır")
areas = [
    (110, 200, 720, 420, "1) Dış bozucu ve BNO055", raw_roll, ORANGE, filtered_roll, BLUE, (-12, 14), "deg"),
    (880, 200, 1490, 420, "2) EKF/Kalman kestirimi", true_roll, GREEN, kalman_roll, BLUE, (-10, 12), "deg"),
    (110, 565, 720, 785, "3) PID + limit komutu", pid_u, RED, deadband_cmd, PURPLE, (-13, 13), "komut"),
    (880, 565, 1490, 785, "4) Mama kabı artık açısı", true_roll, ORANGE, ff_theta, BLUE, (-7, 8), "deg"),
]
for x0, y0, x1, y1, title, s1, c1, s2, c2, ylim, yl in areas:
    tx, ty = plot_area(d, (x0, y0, x1, y1), title, "zaman (s)", yl, (0, 8), ylim, x_ticks=4, y_ticks=4)
    draw_series(d, tx, ty, t, s1, c1, 3)
    draw_series(d, tx, ty, t, s2, c2, 4)
legend(d, [("Ham/bozucu", ORANGE), ("Filtre/EKF/kontrol sonrası", BLUE), ("Referans/gerçek", GREEN), ("Kontrol komutu", RED)], 650, 850)
save(img, "10_genel_stabilizasyon_simulasyonu.png")

# 11. Islem yuku / 100 Hz
img, d = canvas("11 - 100 Hz Döngü İşlem Yükü", "Teensy 4.1 üzerinde her kontrol çevriminin 10 ms bütçeyi aşmaması hedeflenir")
labels = ["Oku", "Filtre", "EKF", "Deadband", "PID", "IK", "Step", "Telem."]
values = [0.18, 0.09, 0.42, 0.03, 0.07, 0.30, 0.12, 0.20]
cols = [BLUE, BLUE, PURPLE, GREEN, RED, ORANGE, CYAN, YELLOW]
bar_chart(d, (130, 240, 1430, 800), "Algoritma bazlı yaklaşık süre", labels, values, cols, "ms")
rounded(d, (1150, 130, 1515, 210), (240, 253, 244), GREEN, 2)
d.text((1170, 150), f"Toplam: {sum(values):.2f} ms / 10 ms", fill=INK, font=FONT_LABEL)
save(img, "11_100hz_islem_yuku.png")

# Contact sheet
files = sorted(fp for fp in OUT_DIR.glob("*.png") if fp.name != "00_tum_grafikler_ozet.png")
thumb_w, thumb_h = 520, 325
rows = math.ceil(len(files) / 2)
sheet = Image.new("RGB", (thumb_w * 2 + 90, 125 + rows * (thumb_h + 45) + 35), BG)
sd = ImageDraw.Draw(sheet)
sd.text((45, 35), "Mama Kabı Stabilizasyonu - Simülasyon Grafik Seti", fill=INK, font=FONT_TITLE)
sd.line((45, 92, sheet.width - 45, 92), fill=(203, 213, 225), width=3)
for idx, fp in enumerate(files):
    im = Image.open(fp).resize((thumb_w, thumb_h))
    x = 45 + (idx % 2) * (thumb_w + 45)
    y = 125 + (idx // 2) * (thumb_h + 45)
    sd.rounded_rectangle((x - 8, y - 8, x + thumb_w + 8, y + thumb_h + 8), radius=14, fill=(255, 255, 255), outline=(203, 213, 225), width=2)
    sheet.paste(im, (x, y))
sheet.save(OUT_DIR / "00_tum_grafikler_ozet.png", quality=95)

print(str(OUT_DIR.resolve()))
