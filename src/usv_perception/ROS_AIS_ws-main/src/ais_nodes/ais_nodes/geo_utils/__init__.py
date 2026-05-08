import math
from typing import Tuple


# in km
EARTH_RADIUS = 6371
BASE_POINT_NAME = "Haitang"
BASE_POINT_LON = 119.37116703323744
BASE_POINT_LAT = 34.75485890660782

def haversin(phi):
    """phi in radius"""
    return math.pow(math.sin(phi/2), 2)


def reverse_haversin(hs):
    """hs for haversin value"""
    sin_phi_divide_2 = math.sqrt(hs)
    phi_divide_2 = math.asin(sin_phi_divide_2)
    return phi_divide_2 * 2


def haversin_distance(
        coord_1: Tuple[float, float],
        coord_2: Tuple[float, float],
        ) -> float:
    """coords in angles"""
    lon_1, lat_1 = coord_1
    lon_2, lat_2 = coord_2
    # coords to radius
    lon_1 = lon_1 / 180 * math.pi
    lon_2 = lon_2 / 180 * math.pi
    lat_1 = lat_1 / 180 * math.pi
    lat_2 = lat_2 / 180 * math.pi
    # apply haversin equation
    arc_radius_haversin = haversin(lat_2 - lat_1) + math.cos(lat_1) * math.cos(lat_2) * haversin(lon_1 - lon_2)
    arc_radius = reverse_haversin(arc_radius_haversin)
    arc_distance = arc_radius * EARTH_RADIUS
    return arc_distance


def latlon_to_enu(ref_lon, ref_lat, lon, lat):
    """
    enu: east-north-up
    """
    # Local tangent-plane approximation around the reference point.
    # Accurate enough for short-range maritime awareness (km-level).
    radius_m = EARTH_RADIUS * 1000.0
    ref_lat_rad = math.radians(ref_lat)
    dlat = math.radians(lat - ref_lat)
    dlon = math.radians(lon - ref_lon)
    x = radius_m * dlon * math.cos(ref_lat_rad)
    y = radius_m * dlat
    return x, y


def enu_to_latlon(ref_lon, ref_lat, x, y):
    """
    reversed latlon_to_enu
    """
    radius_m = EARTH_RADIUS * 1000.0
    ref_lat_rad = math.radians(ref_lat)
    lat = ref_lat + math.degrees(y / radius_m)
    lon = ref_lon + math.degrees(x / (radius_m * math.cos(ref_lat_rad)))
    return lon, lat


def heading_to_enu_quaternion(heading):
    """
    assume ship head aligned with x-axis
    transform ship heading to enu based quaternion
    """
    theta = heading / 180 * math.pi
    theta_enu = math.pi/2 - theta
    # Yaw-only quaternion in ENU frame.
    half = theta_enu * 0.5
    x = 0.0
    y = 0.0
    z = math.sin(half)
    w = math.cos(half)
    return x, y, z, w


if __name__ == "__main__":
    phi = math.pi / 4
    print(reverse_haversin(haversin(phi)))
    Beijing = (116.39889, 39.93335)
    Guangzhou = (113.27736, 23.15480)
    Nanjing = (118.75667, 32.09714)
    # should be around 1130 km
    print(haversin_distance(Guangzhou, Nanjing))
    # should be around 1888 km
    print(haversin_distance(Beijing, Guangzhou))
