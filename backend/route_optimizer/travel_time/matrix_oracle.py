# split_original/travel_time/matrix_oracle.py
from __future__ import annotations
import math
import requests
import logging
from typing import List, Tuple, Dict, Any

logger = logging.getLogger(__name__)

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Mathematical fallback for distances."""
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dlmb/2)**2
    return 2 * R * math.asin(math.sqrt(a))


class DistanceMatrixOracle:
    """
    Precomputes an NxN matrix for all unique coordinates.
    Uses OSRM only if metadata allows it, otherwise relies entirely on Haversine.
    """
    def __init__(self, employees: List[Any], metadata_kv: Dict[str, str], default_speed_kmph: float = 25.0):
        self.default_speed_kmph = float(default_speed_kmph)
        self.matrix = {}

        # 1. Gather all unique coordinates in the entire test case
        unique_coords = set()
        for emp in employees:
            unique_coords.add((emp.pickup_lat, emp.pickup_lng))
            unique_coords.add((emp.drop_lat, emp.drop_lng))

        # Add office coordinate
        office_lat = float(metadata_kv.get("office_lat", 0.0))
        office_lng = float(metadata_kv.get("office_lng", 0.0))
        if office_lat != 0.0 and office_lng != 0.0:
            unique_coords.add((office_lat, office_lng))

        self.coords_list = list(unique_coords)

        # 2. Check metadata flag for external maps permission
        # Convert to string, strip whitespace, and check if it equals "true"
        allow_external_str = str(metadata_kv.get("allow_external_maps", "false")).strip().lower()
        self.allow_external_maps = (allow_external_str == "true")

        # 3. Baseline: Instantly precompute all pairs using Haversine
        self._precompute_haversine()

        # 4. Upgrade: Fetch true driving distances from OSRM ONLY if allowed
        if self.allow_external_maps:
            print(f"🌍 External maps allowed. Upgrading distance matrix with OSRM...")
            self._precompute_osrm()
        else:
            print(f"🛑 External maps disabled (allow_external_maps={allow_external_str}). Using Haversine exclusively.")

    def _precompute_haversine(self):
        """Instantly calculates the math distance matrix for all coordinate pairs."""
        for c1 in self.coords_list:
            if c1 not in self.matrix:
                self.matrix[c1] = {}
            for c2 in self.coords_list:
                self.matrix[c1][c2] = haversine_km(c1[0], c1[1], c2[0], c2[1])

    def _precompute_osrm(self):
        """
        Chunks the coordinates to respect OSRM's 100-coordinate limit,
        fetching the matrix in blocks.
        """
        CHUNK_SIZE = 50 # 50 sources + 50 destinations = 100 (Safe for public OSRM)
        n = len(self.coords_list)
        base_url = "http://router.project-osrm.org/table/v1/driving"
        session = requests.Session()

        for i in range(0, n, CHUNK_SIZE):
            for j in range(0, n, CHUNK_SIZE):
                src_chunk = self.coords_list[i:i+CHUNK_SIZE]
                dst_chunk = self.coords_list[j:j+CHUNK_SIZE]

                # OSRM expects: lon,lat
                combined_coords = src_chunk + dst_chunk
                coord_str = ";".join([f"{lon},{lat}" for lat, lon in combined_coords])

                src_indices = ";".join(str(idx) for idx in range(len(src_chunk)))
                dst_indices = ";".join(str(idx) for idx in range(len(src_chunk), len(combined_coords)))

                url = f"{base_url}/{coord_str}"
                params = {
                    "annotations": "distance",
                    "sources": src_indices,
                    "destinations": dst_indices
                }

                try:
                    resp = session.get(url, params=params, timeout=5.0)
                    if resp.status_code == 200:
                        data = resp.json()
                        if data.get("code") == "Ok" and "distances" in data:
                            dist_matrix = data["distances"]
                            # Overwrite Haversine baseline with accurate OSRM driving data
                            for r_idx, c1 in enumerate(src_chunk):
                                for c_idx, c2 in enumerate(dst_chunk):
                                    val = dist_matrix[r_idx][c_idx]
                                    if val is not None and not math.isnan(val):
                                        self.matrix[c1][c2] = val / 1000.0 # Convert meters to km
                except Exception as e:
                    logger.warning(f"OSRM chunk failed, keeping Haversine for this block.")
                    continue

    def dist_km(self, a_lat: float, a_lng: float, b_lat: float, b_lng: float) -> float:
        # ⚡ Instant O(1) Dictionary Lookup during DP routing! ⚡
        try:
            return self.matrix[(a_lat, a_lng)][(b_lat, b_lng)]
        except KeyError:
            # Absolute fallback if somehow a coordinate is asked that wasn't registered
            return haversine_km(a_lat, a_lng, b_lat, b_lng)

    def time_min(self, a_lat: float, a_lng: float, b_lat: float, b_lng: float, speed_kmph: float = None) -> float:
        spd = self.default_speed_kmph if speed_kmph is None else float(speed_kmph)
        d = self.dist_km(a_lat, a_lng, b_lat, b_lng)
        return (d / spd) * 60.0