#!/usr/bin/env python3
"""KTR icin C++ simülasyon çıktılarından grafik üretir."""

import csv
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def read_csv(path: str) -> dict:
    rows = []
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({k: float(v) if v.replace('.', '', 1).replace('-', '', 1).isdigit() else v for k, v in row.items()})
    return rows


def plot_az_el(rows, out_dir: str):
    times = [r["time_s"] for r in rows]
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
    ax1.plot(times, [r["target_azimuth_deg"] for r in rows], label="Hedef Azimuth", alpha=0.7)
    ax1.plot(times, [r["azimuth_deg"] for r in rows], label="Gercek Azimuth", alpha=0.7)
    ax1.set_ylabel("Azimuth (derece)")
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax2.plot(times, [r["target_elevation_deg"] for r in rows], label="Hedef Elevasyon", alpha=0.7)
    ax2.plot(times, [r["elevation_deg"] for r in rows], label="Gercek Elevasyon", alpha=0.7)
    ax2.set_xlabel("Zaman (s)")
    ax2.set_ylabel("Elevasyon (derece)")
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    fig.suptitle("Azimuth/Elevasyon - Hedef ve Gercek Degerler")
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "az_el_target_vs_actual.png"), dpi=150)
    plt.close(fig)


def plot_boresight_error(rows, out_dir: str):
    times = [r["time_s"] for r in rows]
    errors = [r["boresight_error_deg"] for r in rows]
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(times, errors, label="Boresight Hatasi", color="crimson", alpha=0.7)
    ax.axhline(1.0, color="green", linestyle="--", alpha=0.5, label="Kilit Siniri (1 deg)")
    ax.set_xlabel("Zaman (s)")
    ax.set_ylabel("Hata (derece)")
    ax.set_title("Boresight Hatasi ve Kilit Durumu")
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, min(10, max(errors) + 1))
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "boresight_error.png"), dpi=150)
    plt.close(fig)


def plot_lock_status(rows, out_dir: str):
    times = [r["time_s"] for r in rows]
    locked = [1 if r["locked"] == "true" or r["locked"] is True else 0 for r in rows]
    fig, ax = plt.subplots(figsize=(10, 2))
    ax.fill_between(times, locked, step="pre", alpha=0.7, color="green")
    ax.set_xlabel("Zaman (s)")
    ax.set_ylabel("Kilit")
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["Yok", "Var"])
    ax.set_title("Kilit Durumu")
    ax.set_ylim(-0.1, 1.1)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "lock_status.png"), dpi=150)
    plt.close(fig)


def plot_qpd_offset(rows, out_dir: str):
    times = [r["time_s"] for r in rows]
    fig, ax = plt.subplots(figsize=(10, 3))
    ax.plot(times, [r["qpd_offset_azimuth_deg"] for r in rows], label="QPD Azimuth Offset", alpha=0.7)
    ax.plot(times, [r["qpd_offset_elevation_deg"] for r in rows], label="QPD Elevasyon Offset", alpha=0.7)
    ax.set_xlabel("Zaman (s)")
    ax.set_ylabel("Offset (derece)")
    ax.set_title("QPD/Lazer Aktif Takip Offseti")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "qpd_offset.png"), dpi=150)
    plt.close(fig)


def plot_stabilization(rows, out_dir: str):
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 6))
    times = [r["time_s"] for r in rows]
    ax1.plot(times, [r["raw_roll_deg"] for r in rows], label="Ham Roll", alpha=0.4)
    ax1.plot(times, [r["filtered_roll_deg"] for r in rows], label="Filtrelenmis Roll", alpha=0.8)
    ax1.set_ylabel("Roll (derece)")
    ax1.set_title("Roll - IMU Verisi")
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax2.plot(times, [r["raw_pitch_deg"] for r in rows], label="Ham Pitch", alpha=0.4)
    ax2.plot(times, [r["filtered_pitch_deg"] for r in rows], label="Filtrelenmis Pitch", alpha=0.8)
    ax2.set_title("Pitch - IMU Verisi")
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax3.plot(times, [r["x_motor_command_mm"] for r in rows], label="X Komut", alpha=0.6)
    ax3.plot(times, [r["x_position_mm"] for r in rows], label="X Pozisyon", alpha=0.6)
    ax3.set_xlabel("Zaman (s)")
    ax3.set_ylabel("X (mm)")
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    ax4.plot(times, [r["y_motor_command_mm"] for r in rows], label="Y Komut", alpha=0.6)
    ax4.plot(times, [r["y_position_mm"] for r in rows], label="Y Pozisyon", alpha=0.6)
    ax4.set_xlabel("Zaman (s)")
    ax4.set_ylabel("Y (mm)")
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    fig.suptitle("Mama Kabi Stabilizasyonu - Kontrol Sinyalleri")
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "stabilization_control.png"), dpi=150)
    plt.close(fig)


def plot_residual_error(rows, out_dir: str):
    times = [r["time_s"] for r in rows]
    errors = [r["stabilization_error_deg"] for r in rows]
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(times, errors, label="Artik Stabilizasyon Hatasi", color="orange", alpha=0.7)
    ax.axhline(1.0, color="green", linestyle="--", alpha=0.5, label="Stabil Siniri (1 deg)")
    ax.set_xlabel("Zaman (s)")
    ax.set_ylabel("Hata (derece)")
    ax.set_title("Mama Kabi Stabilizasyon - Artik Hata")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "residual_error.png"), dpi=150)
    plt.close(fig)


def plot_filtered_imu(rows, out_dir: str):
    times = [r["time_s"] for r in rows]
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 5), sharex=True)
    ax1.plot(times, [r["raw_roll_deg"] for r in rows], label="Ham Roll", alpha=0.4, color="gray")
    ax1.plot(times, [r["filtered_roll_deg"] for r in rows], label="Filtrelenmis Roll", alpha=0.8, color="blue")
    ax1.set_ylabel("Roll (derece)")
    ax1.set_title("Roll - Kalman Filtre Karsilastirmasi")
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax2.plot(times, [r["raw_pitch_deg"] for r in rows], label="Ham Pitch", alpha=0.4, color="gray")
    ax2.plot(times, [r["filtered_pitch_deg"] for r in rows], label="Filtrelenmis Pitch", alpha=0.8, color="red")
    ax2.set_xlabel("Zaman (s)")
    ax2.set_ylabel("Pitch (derece)")
    ax2.set_title("Pitch - Kalman Filtre Karsilastirmasi")
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    fig.suptitle("IMU Verisi - Kalman Filtreleme")
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "kalman_filter_comparison.png"), dpi=150)
    plt.close(fig)


def generate_all(base_dir: str):
    base = Path(base_dir)
    az_el_results = base / "Efe" / "azimuth_elevation_simulation" / "results"
    mama_results = base / "Efe" / "mama_kabi_stabilization_simulation" / "results"
    out_dir = base / "grafikler"
    out_dir.mkdir(exist_ok=True)

    az_el_csv = az_el_results / "simulation_output.csv"
    mama_csv = mama_results / "stabilization_output.csv"

    if az_el_csv.exists():
        rows = read_csv(str(az_el_csv))
        plot_az_el(rows, str(out_dir))
        plot_boresight_error(rows, str(out_dir))
        plot_lock_status(rows, str(out_dir))
        plot_qpd_offset(rows, str(out_dir))
        print(f"[OK] Azimuth/Elevasyon grafikleri: {out_dir}")

    if mama_csv.exists():
        rows = read_csv(str(mama_csv))
        plot_stabilization(rows, str(out_dir))
        plot_residual_error(rows, str(out_dir))
        plot_filtered_imu(rows, str(out_dir))
        print(f"[OK] Mama kabi grafikleri: {out_dir}")

    print(f"\nToplam 8 grafik olusturuldu. Klasor: {out_dir}")


if __name__ == "__main__":
    import sys
    base = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
    generate_all(base)
