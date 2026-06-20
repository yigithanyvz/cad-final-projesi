from __future__ import annotations

import math

SATELLITES: dict[str, float] = {
    "Türksat 4B": 50.0,
    "Türksat 5A": 31.0,
    "Türksat 3A": 42.0,
}

EARTH_RADIUS_KM = 6378.137
GEO_ORBIT_RADIUS_KM = 42164.0


def calculate_look_angles(
    latitude_deg: float, longitude_deg: float, satellite_longitude_deg: float
) -> tuple[float, float]:
    lat = math.radians(latitude_deg)
    delta_lon = math.radians(satellite_longitude_deg - longitude_deg)
    ratio = EARTH_RADIUS_KM / GEO_ORBIT_RADIUS_KM

    cos_lat_dlon = math.cos(lat) * math.cos(delta_lon)
    elevation = math.atan(
        (cos_lat_dlon - ratio) / math.sqrt(1.0 - cos_lat_dlon * cos_lat_dlon)
    )
    azimuth = math.atan2(
        math.sin(delta_lon), -math.sin(lat) * math.cos(delta_lon)
    )
    az_deg = (math.degrees(azimuth) + 360.0) % 360.0
    el_deg = max(0.0, min(90.0, math.degrees(elevation)))
    return az_deg, el_deg
