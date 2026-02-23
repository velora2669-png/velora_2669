from typing import Dict, List
from route_optimizer.constraints.time_windows import hhmm_to_min, priority_delay_map
from route_optimizer.data_models.types import Employee, Vehicle, ScheduleItem


def build_employee_timeline_from_schedule(
    schedule: List[ScheduleItem],
    employees_by_id: Dict[str, Employee],
    vehicles_by_id: Dict[str, Vehicle],
    oracle,
    lambda_turnaround_min: int = 0,
) -> Dict[str, Dict[str, float]]:
    """
    Replays the schedule in sequence and returns per-employee timing derived
    from the exact same simulation logic used by verification.
    """
    v_state = {}
    for vid, vehicle in vehicles_by_id.items():
        v_state[vid] = {
            "lat": vehicle.current_lat,
            "lng": vehicle.current_lng,
            "avail": hhmm_to_min(vehicle.available_from),
            "speed": vehicle.avg_speed_kmph,
        }

    employee_timeline: Dict[str, Dict[str, float]] = {}

    for item in schedule:
        st = v_state[item.vehicle_id]
        speed = st["speed"]

        group = [employees_by_id[eid] for eid in item.employee_ids if eid in employees_by_id]
        if not group:
            continue

        first = group[0]
        dead_min = oracle.time_min(st["lat"], st["lng"], first.pickup_lat, first.pickup_lng, speed)
        depart = st["avail"]
        arrive_first = depart + dead_min

        earliest_first = hhmm_to_min(first.earliest_pickup)
        start_pickup = max(arrive_first, earliest_first)

        pickup_times: Dict[str, float] = {}
        t = float(start_pickup)
        for idx, employee in enumerate(group):
            e_earliest = hhmm_to_min(employee.earliest_pickup)
            if t < e_earliest:
                t = float(e_earliest)

            pickup_times[employee.employee_id] = t

            if idx < len(group) - 1:
                nxt = group[idx + 1]
                t += oracle.time_min(
                    employee.pickup_lat,
                    employee.pickup_lng,
                    nxt.pickup_lat,
                    nxt.pickup_lng,
                    speed,
                )

        last = group[-1]
        office_lat, office_lng = last.drop_lat, last.drop_lng
        t += oracle.time_min(last.pickup_lat, last.pickup_lng, office_lat, office_lng, speed)
        office_arrival = int(round(t))

        for employee in group:
            pickup_min = pickup_times.get(employee.employee_id, float(office_arrival))
            employee_timeline[employee.employee_id] = {
                "trip_id": item.trip_id,
                "vehicle_id": item.vehicle_id,
                "pickup_min": float(pickup_min),
                "dropoff_min": float(office_arrival),
                "optimized_time_min": float(max(0.0, office_arrival - pickup_min)),
            }

        st["lat"] = office_lat
        st["lng"] = office_lng
        st["avail"] = office_arrival + lambda_turnaround_min

    return employee_timeline

def verify_and_print_schedule(
    schedule: List[ScheduleItem],
    employees_by_id: Dict[str, Employee],
    vehicles_by_id: Dict[str, Vehicle],
    metadata_kv: Dict[str, str],
    oracle,
    lambda_turnaround_min: int = 0
) -> None:
    p_delay = priority_delay_map(metadata_kv)

    # Track vehicle state as we replay the schedule in order given
    v_state = {}
    for vid, v in vehicles_by_id.items():
        v_state[vid] = {
            "lat": v.current_lat,
            "lng": v.current_lng,
            "avail": hhmm_to_min(v.available_from),
            "speed": v.avg_speed_kmph,
        }

    print("\n===== SCHEDULE VERIFICATION =====")
    for item in schedule:
        vid = item.vehicle_id
        v = vehicles_by_id[vid]
        st = v_state[vid]
        speed = st["speed"]

        group = [employees_by_id[eid] for eid in item.employee_ids]
        first = group[0]

        # Deadhead
        dead_km = oracle.dist_km(st["lat"], st["lng"], first.pickup_lat, first.pickup_lng)
        dead_min = oracle.time_min(st["lat"], st["lng"], first.pickup_lat, first.pickup_lng, speed)
        depart = st["avail"]
        arrive_first = depart + dead_min

        earliest_first = hhmm_to_min(first.earliest_pickup)
        start_pickup = max(arrive_first, earliest_first)
        wait = max(0, earliest_first - arrive_first)

        print(f"\nVehicle {vid} ({v.category}, cap {v.capacity}) doing {item.trip_id} {item.employee_ids}")
        print(f"  Vehicle available at: {depart} min")
        print(f"  Deadhead: {dead_km:.2f} km, {dead_min:.1f} min")
        print(f"  Arrive first pickup: {arrive_first:.1f} min")
        print(f"  Earliest first pickup: {earliest_first} min")
        print(f"  Wait at first pickup: {wait:.1f} min")
        print(f"  Start service at first pickup: {start_pickup:.1f} min")

        # Now simulate pickup-to-pickup-to-office starting at start_pickup.
        # We'll also print arrival times at each pickup manually:
        t = float(start_pickup)

        # Print pickup times in order
        print("  Pickup timeline:")
        for k in range(len(group)):
            e = group[k]
            e_earliest = hhmm_to_min(e.earliest_pickup)
            if t < e_earliest:
                # wait if early (shouldn't happen often after first)
                t = float(e_earliest)

            print(f"    - {e.employee_id}: pickup_time={t:.1f} (earliest={e_earliest})")

            # travel to next pickup
            if k < len(group) - 1:
                n = group[k + 1]
                tt = oracle.time_min(e.pickup_lat, e.pickup_lng, n.pickup_lat, n.pickup_lng, speed)
                t += tt

        # last -> office
        last = group[-1]
        office_lat, office_lng = last.drop_lat, last.drop_lng
        tt_off = oracle.time_min(last.pickup_lat, last.pickup_lng, office_lat, office_lng, speed)
        t += tt_off
        office_arrival = int(round(t))
        print(f"  Office arrival: {office_arrival} min")

        # Check deadlines
        ok = True
        for e in group:
            latest = hhmm_to_min(e.latest_drop)
            allow = int(p_delay.get(int(e.priority), 0))
            limit = latest + allow
            if office_arrival > limit:
                ok = False
                print(f"  ❌ DEADLINE FAIL: {e.employee_id} priority {e.priority} "
                      f"office_arrival={office_arrival} > latest+allow={limit}")
            else:
                print(f"  ✅ deadline ok for {e.employee_id}: {office_arrival} <= {limit}")

        if ok:
            print("  ✅ Trip feasible under current hard rules.")

        # update vehicle state for next trip
        st["lat"] = office_lat
        st["lng"] = office_lng
        st["avail"] = office_arrival + lambda_turnaround_min
        print(f"  Vehicle next available at: {st['avail']} min")
