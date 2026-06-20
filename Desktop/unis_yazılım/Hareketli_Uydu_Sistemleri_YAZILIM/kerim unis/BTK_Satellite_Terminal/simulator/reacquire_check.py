import argparse
import random
import statistics

import sotm_simulator as sim


class ValueVar:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


def make_headless_simulator(seed, mode, noise, laser_source):
    random.seed(seed)
    app = sim.SotmSimulator.__new__(sim.SotmSimulator)

    app.time_s = 0.0
    app.az_actual = 0.0
    app.el_actual = 25.0
    app.az_target = 0.0
    app.el_target = sim.LASER_TARGET_EL_DEG
    app.az_error = 0.0
    app.el_error = 0.0
    app.spot_x_norm = 0.0
    app.spot_y_norm = 0.0
    app.camera_center_x_px = sim.CAMERA_FRAME_WIDTH_PX * 0.5
    app.camera_center_y_px = sim.CAMERA_FRAME_HEIGHT_PX * 0.5
    app.camera_confidence = 0.0
    app.camera_detected = False
    app.camera_frame = None
    app.camera_photo = None
    app.camera_source = sim.CameraTargetSource(render_frames=False, use_real_camera=False)
    app.camera_status = app.camera_source.status
    app.artificial_x_norm = random.uniform(-0.62, 0.62)
    app.artificial_y_norm = random.uniform(-0.50, 0.50)
    app.target_x_norm = 0.0
    app.target_y_norm = 0.0
    app.laser_dot_x_norm = 0.0
    app.laser_dot_y_norm = 0.0
    app.prev_mode = None
    app.reacquire_active = True
    app.reacquire_start_s = 0.0
    app.reacquire_time_s = None
    app.reacquire_passed = None
    app.lock_hold_s = 0.0
    app.random_sat_az = random.uniform(0.0, 360.0)
    app.random_sat_el = random.uniform(15.0, 70.0)
    app.prev_base_az = None
    app.prev_base_el = None
    app.az_target_rate_dps = 0.0
    app.el_target_rate_dps = 0.0

    app.az_pid = sim.PID(2.5, 0.1, 0.3, 20.0, -sim.AZ_MAX_SPEED_DPS, sim.AZ_MAX_SPEED_DPS, 0.1, True)
    app.el_pid = sim.PID(3.0, 0.08, 0.25, 15.0, -sim.EL_MAX_SPEED_DPS, sim.EL_MAX_SPEED_DPS, 0.1, False)
    app.camera_detector = sim.CameraObjectDetector()
    app.laser = sim.LaserTracker()

    app.mode_var = ValueVar(mode)
    app.laser_source_var = ValueVar(laser_source)
    app.satellite_var = ValueVar("Turksat 4B")
    app.laser_var = ValueVar(True)
    app.noise_var = ValueVar(noise)
    app.camera_index_var = ValueVar(0)
    app.lat_var = ValueVar(39.9208)
    app.lon_var = ValueVar(32.8541)
    app.alt_var = ValueVar(900.0)
    app.laser_target_az = 0.0
    app.laser_target_el = sim.LASER_TARGET_EL_DEG

    app.reset()
    return app


def run_trial(seed, mode, noise, seconds, laser_source):
    app = make_headless_simulator(seed, mode, noise, laser_source)
    steps = int(seconds / sim.MAIN_DT_S)
    for _ in range(steps):
        app._simulate_step()
        if app.reacquire_time_s is not None:
            return app.reacquire_time_s
    return None


def main():
    parser = argparse.ArgumentParser(description="Headless reacquire test for the SoTM simulator.")
    parser.add_argument("--trials", type=int, default=200)
    parser.add_argument("--seconds", type=float, default=10.0)
    parser.add_argument("--mode", default="Lazer Takip", choices=["Lazer Takip", "Uydu Yonelimi", "Uydu Yönelimi"])
    parser.add_argument("--laser-source", default="Kamera Modu", choices=["Kamera Modu", "Yapay Cisim Modu"])
    parser.add_argument("--no-noise", action="store_true")
    parser.add_argument("--allow-failures", type=int, default=0)
    args = parser.parse_args()

    mode = "Uydu Yönelimi" if args.mode == "Uydu Yonelimi" else args.mode
    results = [
        run_trial(seed, mode, not args.no_noise, args.seconds, args.laser_source)
        for seed in range(args.trials)
    ]
    locked = [value for value in results if value is not None]
    passed = [value for value in locked if value <= sim.REACQUIRE_LIMIT_S]
    failures = [
        (seed, value)
        for seed, value in enumerate(results)
        if value is None or value > sim.REACQUIRE_LIMIT_S
    ]

    print(f"mode={mode} laser_source={args.laser_source} trials={args.trials} noise={not args.no_noise}")
    print(f"passed={len(passed)}/{args.trials} limit={sim.REACQUIRE_LIMIT_S:.2f}s")
    if locked:
        print(
            "lock_time_s "
            f"min={min(locked):.2f} "
            f"median={statistics.median(locked):.2f} "
            f"max={max(locked):.2f}"
        )
    if failures:
        print(f"failures={failures[:10]}")

    if len(failures) > args.allow_failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
