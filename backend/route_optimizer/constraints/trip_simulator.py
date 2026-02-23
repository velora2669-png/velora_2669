# route_optimizer/constraints/trip_simulator.py
from __future__ import annotations
from typing import List, Tuple, Dict, Any
from route_optimizer.data_models.types import Employee
from route_optimizer.constraints.time_windows import hhmm_to_min


def simulate_segment_to_office(
    emps: List[Employee],
    oracle,
    speed_kmph: float,
    start_time_min: int,
) -> Tuple[int, float, float, Dict[str, Any]]:
    """
    Simulate pickup in given order, waiting allowed for earliest pickup.
    Returns:
      office_arrival_min, total_dist_km, total_time_min, debug
    """
    t = float(start_time_min)
    total_dist = 0.0
    total_time = 0.0

    # pickup -> pickup
    for k in range(len(emps)):
        e = emps[k]
        earliest = hhmm_to_min(e.earliest_pickup)
        if t < earliest:
            t = float(earliest)

        if k < len(emps) - 1:
            n = emps[k + 1]
            d = oracle.dist_km(e.pickup_lat, e.pickup_lng, n.pickup_lat, n.pickup_lng)
            tt = oracle.time_min(e.pickup_lat, e.pickup_lng, n.pickup_lat, n.pickup_lng, speed_kmph)
            total_dist += d
            total_time += tt
            t += tt

    # last pickup -> office
    last = emps[-1]
    office_lat, office_lng = emps[0].drop_lat, emps[0].drop_lng
    d = oracle.dist_km(last.pickup_lat, last.pickup_lng, office_lat, office_lng)
    tt = oracle.time_min(last.pickup_lat, last.pickup_lng, office_lat, office_lng, speed_kmph)
    total_dist += d
    total_time += tt
    t += tt

    return int(round(t)), float(total_dist), float(total_time), {
        "start_time": start_time_min,
        "end_time": int(round(t)),
    }
