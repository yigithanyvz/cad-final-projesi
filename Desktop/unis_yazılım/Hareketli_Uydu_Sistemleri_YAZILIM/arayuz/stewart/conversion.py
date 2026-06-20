from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class StewartTwist:
    """Represents the Twist message sent to the Stewart IK node.

    Mapping:
      linear.x  = sway (left-right translation)
      linear.y  = surge (forward-back translation)
      linear.z  = heave (up-down translation)
      angular.x = roll
      angular.y = pitch  ← maps to satellite elevation
      angular.z = yaw    ← maps to satellite azimuth
    """

    linear_x: float = 0.0
    linear_y: float = 0.0
    linear_z: float = 0.0
    angular_roll: float = 0.0
    angular_pitch: float = 0.0
    angular_yaw: float = 0.0


@dataclass
class AzEl:
    az_deg: float = 0.0
    el_deg: float = 0.0


def degrees_to_radians(deg: float) -> float:
    return math.radians(deg)


def radians_to_degrees(rad: float) -> float:
    return math.degrees(rad)


def normalize_angle(rad: float) -> float:
    return math.atan2(math.sin(rad), math.cos(rad))


def az_el_to_twist(
    az_deg: float,
    el_deg: float,
    home_height_offset: float = 0.0,
    sway: float = 0.0,
    surge: float = 0.0,
    roll_deg: float = 0.0,
) -> StewartTwist:
    """Convert satellite Az/El angles to Stewart platform Twist command.

    Args:
        az_deg: Satellite azimuth in degrees (0-360)
        el_deg: Satellite elevation in degrees (0-90)
        home_height_offset: Additional heave offset
        sway: Lateral translation (x)
        surge: Longitudinal translation (y)
        roll_deg: Roll angle in degrees

    Returns:
        StewartTwist ready to be sent as geometry_msgs/Twist
    """
    return StewartTwist(
        linear_x=float(sway),
        linear_y=float(surge),
        linear_z=float(home_height_offset),
        angular_roll=math.radians(roll_deg),
        angular_pitch=math.radians(el_deg),
        angular_yaw=math.radians(az_deg),
    )


def stewart_pose_to_az_el(
    roll_rad: float,
    pitch_rad: float,
    yaw_rad: float,
) -> AzEl:
    """Extract satellite azimuth and elevation from Stewart platform orientation.

    On the Stewart platform:
      - pitch (angular.y) → elevation angle
      - yaw   (angular.z) → azimuth angle

    Args:
        roll_rad: Roll in radians
        pitch_rad: Pitch in radians
        yaw_rad: Yaw in radians

    Returns:
        AzEl with normalized angles in degrees
    """
    az_deg = math.degrees(normalize_angle(yaw_rad)) % 360.0
    el_deg = max(0.0, min(90.0, math.degrees(pitch_rad)))
    return AzEl(az_deg=az_deg, el_deg=el_deg)


def quaternion_to_rpy(w: float, x: float, y: float, z: float) -> tuple[float, float, float]:
    """Convert quaternion to roll, pitch, yaw in radians."""
    sinr_cosp = 2.0 * (w * x + y * z)
    cosr_cosp = 1.0 - 2.0 * (x * x + y * y)
    roll = math.atan2(sinr_cosp, cosr_cosp)

    sinp = 2.0 * (w * y - z * x)
    pitch = math.copysign(math.pi / 2.0, sinp) if abs(sinp) >= 1.0 else math.asin(sinp)

    siny_cosp = 2.0 * (w * z + x * y)
    cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
    yaw = math.atan2(siny_cosp, cosy_cosp)

    return roll, pitch, yaw


def rpy_to_quaternion(
    roll_rad: float, pitch_rad: float, yaw_rad: float
) -> tuple[float, float, float, float]:
    """Convert roll, pitch, yaw in radians to quaternion (w, x, y, z)."""
    cr = math.cos(roll_rad * 0.5)
    sr = math.sin(roll_rad * 0.5)
    cp = math.cos(pitch_rad * 0.5)
    sp = math.sin(pitch_rad * 0.5)
    cy = math.cos(yaw_rad * 0.5)
    sy = math.sin(yaw_rad * 0.5)

    w = cr * cp * cy + sr * sp * sy
    x = sr * cp * cy - cr * sp * sy
    y = cr * sp * cy + sr * cp * sy
    z = cr * cp * sy - sr * sp * cy
    return w, x, y, z
