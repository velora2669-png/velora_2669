# route_optimizer/main.py
from __future__ import annotations
from route_optimizer.travel_time.matrix_oracle import DistanceMatrixOracle
from route_optimizer.excel_io.excel_loader import load_testcase_xlsx
from route_optimizer.debug.verify_schedule import (
    verify_and_print_schedule,
    build_employee_timeline_from_schedule,
)
from route_optimizer.hybrid_solver import solve_from_giant_tour
import argparse
import sys
from pathlib import Path

# Add current directory to path to handle imports
sys.path.insert(0, str(Path(__file__).parent))


def _to_float(value, default=0.0):
    try:
        if value is None:
            return default
        result = float(value)
        # Check for NaN
        import math
        if math.isnan(result):
            return default
        return result
    except (TypeError, ValueError):
        return default


def _to_time_minutes(value, default=0.0):
    if value is None:
        return default

    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return default
        if ":" in raw:
            try:
                hours, minutes = raw.split(":", 1)
                return float(int(hours) * 60 + int(minutes))
            except (TypeError, ValueError):
                return default
        return _to_float(raw, default)

    return _to_float(value, default)


def _format_hhmm_from_min(minutes):
    minutes = int(round(_to_float(minutes, 0.0)))
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}"


def _build_baseline_map(baseline_df):
    if baseline_df is None or baseline_df.empty:
        return {}

    normalized = {str(col).strip().lower(): col for col in baseline_df.columns}
    emp_col = normalized.get("employee_id")
    if not emp_col:
        return {}

    cost_col = (
        normalized.get("baseline_cost")
        or normalized.get("cost")
        or normalized.get("baseline")
    )

    time_col = (
        normalized.get("baseline_time")
        or normalized.get("time")
        or normalized.get("baseline_time_min")
        or normalized.get("time_min")
        or normalized.get("duration")
        or normalized.get("duration_min")
    )

    if not cost_col and not time_col:
        return {}

    baseline_map = {}
    for _, row in baseline_df.iterrows():
        emp_id = str(row.get(emp_col, "")).strip()
        if not emp_id:
            continue
        baseline_map[emp_id] = {
            "baseline_cost": _to_float(row.get(cost_col), 0.0) if cost_col else 0.0,
            "baseline_time_min": _to_time_minutes(row.get(time_col), 0.0) if time_col else 0.0,
        }

    return baseline_map


def _compute_optimized_cost_by_employee(sol, emp_by_id, veh_by_id, oracle):
    optimized_cost = {}

    for sched_item in sol.schedule:
        vehicle = veh_by_id.get(sched_item.vehicle_id)
        if not vehicle:
            continue

        employee_ids = sched_item.employee_ids or []
        if not employee_ids:
            continue

        c_veh = vehicle.cost_per_km
        n = len(employee_ids)
        deadhead_km = _to_float(getattr(sched_item, "deadhead_km", 0.0), 0.0)
        trip_dist_km = _to_float(getattr(sched_item, "trip_dist_km", 0.0), 0.0)

        employee_dists = []
        for emp_id in employee_ids:
            emp = emp_by_id.get(emp_id)
            if not emp:
                continue
            dist_to_office = oracle.dist_km(
                emp.pickup_lat,
                emp.pickup_lng,
                emp.drop_lat,
                emp.drop_lng,
            )
            employee_dists.append((emp_id, dist_to_office))

        if not employee_dists:
            continue

        sum_dists = sum(dist for _, dist in employee_dists)

        for emp_id, dist_to_office in employee_dists:
            if sum_dists > 0:
                trip_charge = trip_dist_km * c_veh * dist_to_office / sum_dists
            else:
                trip_charge = trip_dist_km * c_veh / n

            deadhead_charge = deadhead_km * c_veh / n
            total_charge = trip_charge + deadhead_charge
            optimized_cost[emp_id] = optimized_cost.get(emp_id, 0.0) + total_charge

    return optimized_cost

def run_optimizer_from_excel(file_path: str):
    # 1. LOAD DATA
    employees, vehicles, metadata_kv, baseline_df = load_testcase_xlsx(file_path)
    oracle = DistanceMatrixOracle(employees, metadata_kv, default_speed_kmph=25.0)

    emp_by_id = {e.employee_id: e for e in employees}
    veh_by_id = {v.vehicle_id: v for v in vehicles}

    # 2. AUTO GENERATE GIANT TOUR
    from route_optimizer.tour.giant_tour import GiantTourBuilder
    from route_optimizer.tour.regret_insertion import Depot

    office_lat = float(metadata_kv.get("office_lat", 0.0))
    office_lng = float(metadata_kv.get("office_lng", 0.0))
    depot = Depot(id="DEPOT", lat=office_lat, lng=office_lng)

    builder = GiantTourBuilder(oracle, employees, office_lat, office_lng)
    full_tour = builder.build(employees, depot)
    giant_tour_ids = [eid for eid in full_tour if eid != "DEPOT"]

    # 3. RUN SOLVER
    sol = solve_from_giant_tour(
        employees, vehicles, metadata_kv, oracle, giant_tour_ids
    )

    optimized_cost_by_employee = _compute_optimized_cost_by_employee(
        sol, emp_by_id, veh_by_id, oracle
    )
    baseline_by_employee = _build_baseline_map(baseline_df)
    optimized_timeline_by_employee = build_employee_timeline_from_schedule(
        sol.schedule,
        emp_by_id,
        veh_by_id,
        oracle,
        lambda_turnaround_min=0,
    )

    all_employee_ids = sorted(
        {
            *[e.employee_id for e in employees],
            *baseline_by_employee.keys(),
            *optimized_cost_by_employee.keys(),
            *optimized_timeline_by_employee.keys(),
        }
    )

    employee_comparison = []
    baseline_total = 0.0
    optimized_total = 0.0

    for employee_id in all_employee_ids:
        baseline_row = baseline_by_employee.get(employee_id, {})
        timeline_row = optimized_timeline_by_employee.get(employee_id, {})

        baseline_cost = _to_float(baseline_row.get("baseline_cost"), 0.0)
        optimized_cost = _to_float(optimized_cost_by_employee.get(employee_id), 0.0)
        baseline_time_min = _to_time_minutes(baseline_row.get("baseline_time_min"), 0.0)
        optimized_time_min = _to_time_minutes(timeline_row.get("optimized_time_min"), 0.0)

        delta = optimized_cost - baseline_cost
        time_delta = optimized_time_min - baseline_time_min

        cost_savings_pct = ((baseline_cost - optimized_cost) / baseline_cost * 100.0) if baseline_cost > 0 else 0.0
        time_savings_pct = ((baseline_time_min - optimized_time_min) / baseline_time_min * 100.0) if baseline_time_min > 0 else 0.0

        baseline_total += baseline_cost
        optimized_total += optimized_cost

        employee_comparison.append({
            "employee_id": employee_id,
            "vehicle_assigned": timeline_row.get("vehicle_id") or "",
            "baseline_cost": round(baseline_cost, 2),
            "optimized_cost": round(optimized_cost, 2),
            "difference": round(delta, 2),
            "savings": round(-delta, 2),
            "absolute_cost_saving": round(abs(baseline_cost - optimized_cost), 2),
            "baseline_time_min": round(baseline_time_min, 2),
            "optimized_time_min": round(optimized_time_min, 2),
            "baseline_time": _format_hhmm_from_min(baseline_time_min),
            "optimized_time": _format_hhmm_from_min(optimized_time_min),
            "optimized_pickup_time": _format_hhmm_from_min(timeline_row.get("pickup_min", 0.0)),
            "optimized_dropoff_time": _format_hhmm_from_min(timeline_row.get("dropoff_min", 0.0)),
            "time_difference_min": round(time_delta, 2),
            "time_savings_min": round(-time_delta, 2),
            "absolute_time_saving_min": round(abs(baseline_time_min - optimized_time_min), 2),
            "cost_saving_pct": round(cost_savings_pct, 2),
            "time_saving_pct": round(time_savings_pct, 2),
        })

    # 4. Convert result into dictionary (IMPORTANT for Django JSON)
    return {
        "total_cost": sol.total_cost,
        "cost_comparison": {
            "baseline_total": round(baseline_total, 2),
            "optimized_total": round(optimized_total, 2),
            "difference_total": round(optimized_total - baseline_total, 2),
            "savings_total": round(baseline_total - optimized_total, 2),
            "employees": employee_comparison,
        },
        "trips": [
            {
                "trip_id": tr.trip_id,
                "employees": tr.employee_ids,
                "cost": tr.cost,
            }
            for tr in sol.trips
        ],
        "schedule": [
            {
                "vehicle_id": s.vehicle_id,
                "trip_id": s.trip_id,
                "employees": s.employee_ids,
                "depart_min": s.depart_min,
                "arrival_min": s.office_arrival_min,
                "cost": s.cost,
            }
            for s in sol.schedule
        ],
        "employees": [
        {
            "employee_id": e.employee_id,
            "pickup_lat": e.pickup_lat,
            "pickup_lng": e.pickup_lng,
            "drop_lat": e.drop_lat,
            "drop_lng": e.drop_lng,
        }
        for e in employees
    ],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--testcase", required=True)
    ap.add_argument("--tour", required=False, help="Comma-separated employee_ids in giant tour order")
    args = ap.parse_args()

    # ==========================================
    # 1. LOAD DATA & INITIALIZE ORACLE ONCE
    # ==========================================
    employees, vehicles, metadata_kv, _ = load_testcase_xlsx(args.testcase)
    oracle = DistanceMatrixOracle(employees, metadata_kv, default_speed_kmph=25.0)

    # Convert to fast lookup dictionaries
    emp_by_id = {e.employee_id: e for e in employees}
    veh_by_id = {v.vehicle_id: v for v in vehicles}

    # ==========================================
    # 2. GENERATE OR PARSE GIANT TOUR
    # ==========================================
    if args.tour:
        giant_tour_ids = [x.strip() for x in args.tour.split(",") if x.strip()]
    else:
        from route_optimizer.tour.giant_tour import GiantTourBuilder
        from route_optimizer.tour.regret_insertion import Depot
        
        office_lat = float(metadata_kv.get("office_lat", 0.0))
        office_lng = float(metadata_kv.get("office_lng", 0.0))
        depot = Depot(id="DEPOT", lat=office_lat, lng=office_lng)
        
        builder = GiantTourBuilder(oracle, employees, office_lat, office_lng)
        full_tour = builder.build(employees, depot)
        
        giant_tour_ids = [eid for eid in full_tour if eid != "DEPOT"]
        print(f"🌍 Auto-Generated Giant Tour: {giant_tour_ids}")

    # ==========================================
    # 3. RUN THE SOLVER
    # ==========================================
    sol = solve_from_giant_tour(employees, vehicles, metadata_kv, oracle, giant_tour_ids)

    print("Total cost:", sol.total_cost)

    # Display relaxation information if applicable
    if sol.meta and "infeasibility_reason" in sol.meta:
        print("\n" + "="*70)
        print("⚠️  INFEASIBLE HANDLING REPORT")
        print("="*70)
        print(f"\nOriginal Problem: INFEASIBLE")
        print(f"Reason: {sol.meta['infeasibility_reason']}")
        print(f"\nConstraints Relaxed:")
        for relaxation in sol.meta.get('relaxations_applied', []):
            print(f"  • {relaxation}")
        print(f"\nNote: {sol.meta.get('note', '')}")
        print("\nHard constraints still enforced:")
        print("  • Time windows (earliest pickup, latest drop)")
        print("  • Vehicle capacity limits")
        print("  • Priority-based maximum delay limits")
        print("="*70 + "\n")

    print("\nTrips:")
    for tr in sol.trips:
        print(tr.trip_id, tr.employee_ids, tr.cost)

    print("\nSchedule:")
    for s in sol.schedule:
        print(s.vehicle_id, s.trip_id, s.employee_ids, s.depart_min, s.office_arrival_min, s.cost)

    # ==========================================
    # 4. CALCULATE PER-EMPLOYEE CHARGES
    # ==========================================
    print("\n" + "="*70)
    print("PER-EMPLOYEE CHARGES")
    print("="*70)

    total_employee_charges = {}

    for sched_item in sol.schedule:
        vehicle = veh_by_id[sched_item.vehicle_id]
        c_veh = vehicle.cost_per_km
        n = len(sched_item.employee_ids)

        deadhead_km = sched_item.deadhead_km
        trip_dist_km = sched_item.trip_dist_km

        # Calculate each employee's distance to office
        employee_dists = []
        for emp_id in sched_item.employee_ids:
            emp = emp_by_id[emp_id]
            dist_to_office = oracle.dist_km(emp.pickup_lat, emp.pickup_lng, emp.drop_lat, emp.drop_lng)
            employee_dists.append((emp_id, dist_to_office))

        sum_dists = sum(d for _, d in employee_dists)

        # Calculate charges
        print(f"\n{sched_item.trip_id} on {sched_item.vehicle_id} (cost_per_km={c_veh:.2f}):")
        print(f"  Trip distance: {trip_dist_km:.2f} km, Deadhead: {deadhead_km:.2f} km")

        for emp_id, dist_to_office in employee_dists:
            # Proportional trip cost + equal deadhead share
            if sum_dists > 0:
                trip_charge = (trip_dist_km * c_veh * dist_to_office / sum_dists)
            else:
                trip_charge = (trip_dist_km * c_veh / n)

            deadhead_charge = (deadhead_km * c_veh / n)
            total_charge = trip_charge + deadhead_charge

            # Track total per employee
            if emp_id not in total_employee_charges:
                total_employee_charges[emp_id] = 0.0
            total_employee_charges[emp_id] += total_charge

            print(f"  {emp_id}: trip={trip_charge:.2f}, deadhead={deadhead_charge:.2f}, total={total_charge:.2f}")

    print("\n" + "="*70)
    print("TOTAL CHARGES PER EMPLOYEE")
    print("="*70)
    for emp_id in sorted(total_employee_charges.keys()):
        print(f"{emp_id}: ${total_employee_charges[emp_id]:.2f}")
    print("="*70 + "\n")

    # ==========================================
    # 5. VERIFY SCHEDULE FEASIBILITY
    # ==========================================
    verify_and_print_schedule(
        sol.schedule,
        emp_by_id,
        veh_by_id,
        metadata_kv,
        oracle,
        lambda_turnaround_min=0,
    )


if __name__ == "__main__":
    main()