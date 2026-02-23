# route_optimizer/travel_time/distancehaversine_matrix.py
from __future__ import annotations
import math


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dlmb/2)**2
    return 2 * R * math.asin(math.sqrt(a))


class HaversineOracle:
    """
    Very simple oracle:
      time_min = dist_km / speed_kmph * 60
    """
    def __init__(self, default_speed_kmph: float = 25.0):
        self.default_speed_kmph = float(default_speed_kmph)

    def dist_km(self, a_lat: float, a_lng: float, b_lat: float, b_lng: float) -> float:
        return float(haversine_km(a_lat, a_lng, b_lat, b_lng))

    def time_min(self, a_lat: float, a_lng: float, b_lat: float, b_lng: float, speed_kmph: float = None) -> float:
        spd = self.default_speed_kmph if speed_kmph is None else float(speed_kmph)
        d = self.dist_km(a_lat, a_lng, b_lat, b_lng)
        return (d / spd) * 60.0
