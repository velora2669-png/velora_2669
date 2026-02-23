# route_optimizer/scheduling/multi_trip_scheduler.py
from __future__ import annotations
from typing import Dict, List, Tuple, Optional

from route_optimizer.data_models.types import Trip, Vehicle, Employee, ScheduleItem
from route_optimizer.constraints.time_windows import hhmm_to_min, priority_delay_map
from route_optimizer.constraints.trip_simulator import simulate_segment_to_office


def schedule_trips_greedy(
    trips: List[Trip],
    employees_by_id: Dict[str, Employee],
    vehicles: List[Vehicle],
    metadata_kv: Dict[str, str],
    oracle,
    lambda_turnaround_min: int = 0,

    # NEW: penalty knobs (tune later)
    premium_miss_penalty: float = 50.0,   # if trip wants premium but we give normal
    premium_waste_penalty: float = 50.0,  # if trip doesn't want premium but we use premium vehicle
    allow_late_drop: bool = False,  # Allow late drops with penalty
) -> List[ScheduleItem]:
    """
    Greedy multi-trip scheduler:
    Assign each trip to the cheapest feasible vehicle while respecting
    hard constraints and preferring correct vehicle categories.
    """

    p_delay = priority_delay_map(metadata_kv)

    # -------------------------
    # Helpers: premium need
    # -------------------------
    def trip_premium_count(group: List[Employee]) -> int:
        return sum(1 for e in group if str(e.vehicle_preference).lower() == "premium")

    def trip_needs_premium(group: List[Employee]) -> bool:
        return trip_premium_count(group) > 0

    # -------------------------
    # Mutable vehicle state
    # -------------------------
    v_state: Dict[str, Dict] = {}
    for v in vehicles:
        v_state[v.vehicle_id] = {
            "lat": v.current_lat,
            "lng": v.current_lng,
            "avail": hhmm_to_min(v.available_from),
            "capacity": v.capacity,
            "speed": v.avg_speed_kmph,
            "category": str(v.category).lower(),  # 'premium'/'normal'
        }

    schedule: List[ScheduleItem] = []

    # Sort trips by earliest pickup of first employee
    def trip_key(tr: Trip) -> int:
        first = employees_by_id[tr.employee_ids[0]]
        return hhmm_to_min(first.earliest_pickup)

    trips_sorted = sorted(trips, key=trip_key)

    # -------------------------
    # Main assignment loop
    # -------------------------
    for tr in trips_sorted:
        group = [employees_by_id[eid] for eid in tr.employee_ids]
        g = len(group)

        needs_prem = trip_needs_premium(group)
        prem_cnt = trip_premium_count(group)

        best: Optional[Tuple[str, int, int, float, float, float]] = None
        # tuple: (vehicle_id, depart, office_arrival, deadhead_km, trip_dist_km, total_cost)

        office_lat, office_lng = group[0].drop_lat, group[0].drop_lng

        for vid, st in v_state.items():
            # HARD: capacity
            if g > st["capacity"]:
                continue

            # deadhead to first pickup
            first = group[0]
            dead_km = oracle.dist_km(st["lat"], st["lng"], first.pickup_lat, first.pickup_lng)
            dead_min = oracle.time_min(st["lat"], st["lng"], first.pickup_lat, first.pickup_lng, st["speed"])

            # depart at vehicle availability
            depart = int(st["avail"])
            arrive_first = depart + dead_min

            # wait until earliest pickup
            earliest = hhmm_to_min(first.earliest_pickup)
            start_time = int(max(arrive_first, earliest))

            # simulate trip pickups -> office (deadhead handled separately)
            office_arrival, trip_dist_km, trip_time_min, _dbg = simulate_segment_to_office(
                emps=group,
                oracle=oracle,
                speed_kmph=st["speed"],
                start_time_min=start_time,
            )

            # HARD: latest_drop + allowed delay for every employee (or SOFT with penalty)
            feasible = True
            late_penalty = 0.0
            for e in group:
                latest = hhmm_to_min(e.latest_drop)
                allow = int(p_delay.get(int(e.priority), 0))
                if office_arrival > latest + allow:
                    if not allow_late_drop:
                        feasible = False
                        break
                    else:
                        # Add penalty for being late
                        delay_minutes = office_arrival - (latest + allow)
                        late_penalty += 1000.0 * delay_minutes
            if not feasible:
                continue

            # -------------------------
            # Base cost (distance-based)
            # -------------------------
            total_cost = float(dead_km + trip_dist_km) + late_penalty

            # -------------------------
            # SOFT vehicle preference handling:
            # - If trip wants premium but we give normal -> penalty
            # - If trip doesn't want premium but we use premium -> penalty
            # -------------------------
            if needs_prem and st["category"] != "premium":
                total_cost += premium_miss_penalty * prem_cnt

            if (not needs_prem) and st["category"] == "premium":
                total_cost += premium_waste_penalty

            # choose best
            if best is None or total_cost < best[5]:
                best = (vid, depart, office_arrival, float(dead_km), float(trip_dist_km), float(total_cost))

        if best is None:
            raise RuntimeError(f"No feasible vehicle found for trip {tr.trip_id} {tr.employee_ids}")

        vid, depart, office_arrival, dead_km, trip_dist_km, total_cost = best

        schedule.append(ScheduleItem(
            vehicle_id=vid,
            trip_id=tr.trip_id,
            employee_ids=tr.employee_ids,
            depart_min=depart,
            office_arrival_min=office_arrival,
            deadhead_km=dead_km,
            trip_dist_km=trip_dist_km,
            cost=total_cost,
        ))

        # update vehicle state after trip (now at office)
        v_state[vid]["lat"] = office_lat
        v_state[vid]["lng"] = office_lng
        v_state[vid]["avail"] = int(office_arrival + lambda_turnaround_min)

    return schedule
