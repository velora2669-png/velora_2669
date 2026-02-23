# split_original/split/edge_cost.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from route_optimizer.data_models.types import Employee, Vehicle, SegmentEval
from route_optimizer.constraints.time_windows import hhmm_to_min, priority_delay_map
from route_optimizer.constraints.trip_simulator import simulate_segment_to_office
from split.feasibility_cache import FeasibilityCache


def share_limit(pref: str) -> int:
    p = str(pref).lower()
    if p == "single":
        return 1
    if p == "double":
        return 2
    if p == "triple":
        return 3
    return 10**9


@dataclass(frozen=True)
class SplitCostConfig:
    w_dist: float
    w_time: float

    # soft weights
    w_share: float = 20.0
    w_vehicle_pref: float = 10.0
    w_fleet_scarcity: float = 30.0
    w_deadhead_proxy: float = 0.5  # gentle nudge

    # optional hard Tmax
    Tmax: Optional[int] = None


def fleet_count_serving(vehicles: List[Vehicle], group_size: int) -> int:
    return sum(1 for v in vehicles if v.capacity >= group_size)


def fleet_scarcity_penalty(vehicles: List[Vehicle], group_size: int, w: float) -> float:
    cnt = fleet_count_serving(vehicles, group_size)
    if cnt <= 0:
        return 1e9
    return w * (1.0 / cnt)


def get_premium_capacity(vehicles: List[Vehicle]) -> int:
    """Return max capacity of any single premium vehicle."""
    premium_caps = [v.capacity for v in vehicles if str(v.category).lower() == "premium"]
    return max(premium_caps, default=0)


def premium_capacity_mismatch_penalty(group: List[Employee], vehicles: List[Vehicle], w_vehicle_pref: float) -> float:
    """
    Penalize groups with premium-preference employees that exceed the capacity of a SINGLE premium vehicle.
    """
    premium_cnt = sum(1 for e in group if str(e.vehicle_preference).lower() == "premium")
    if premium_cnt == 0:
        return 0.0
    
    group_size = len(group)
    max_premium_vehicle_capacity = get_premium_capacity(vehicles)
    
    if group_size > max_premium_vehicle_capacity and premium_cnt > 0:
        return premium_cnt * w_vehicle_pref * 10.0
    
    return 0.0


def reachable_by_any_vehicle(
    first_emp: Employee,
    vehicles: List[Vehicle],
    oracle,
    p_delay: Dict[int, int],
    allow_early_pickup: bool = False,
    allow_late_drop: bool = False,
) -> Tuple[bool, float]:
    """
    Evaluates if any vehicle can physically drive to the first pickup, collect the employee,
    and make it to the office before the latest_drop deadline.
    Returns: (is_reachable, min_deadhead_km)
    """
    earliest = hhmm_to_min(first_emp.earliest_pickup)
    latest_allowed = hhmm_to_min(first_emp.latest_drop) + int(p_delay.get(int(first_emp.priority), 0))
    
    min_deadhead = float("inf")
    ok = False
    
    for v in vehicles:
        v_avail = hhmm_to_min(v.available_from)
        tt_to_pickup = oracle.time_min(v.current_lat, v.current_lng, first_emp.pickup_lat, first_emp.pickup_lng, v.avg_speed_kmph)
        arrive_at_pickup = v_avail + tt_to_pickup
        
        actual_pickup = arrive_at_pickup if allow_early_pickup else max(arrive_at_pickup, earliest)
        tt_to_office = oracle.time_min(first_emp.pickup_lat, first_emp.pickup_lng, first_emp.drop_lat, first_emp.drop_lng, v.avg_speed_kmph)
        
        # We only care that the vehicle can complete the drop-off in time, NOT that it arrives early.
        if allow_late_drop or (actual_pickup + tt_to_office <= latest_allowed):
            ok = True
            d = oracle.dist_km(v.current_lat, v.current_lng, first_emp.pickup_lat, first_emp.pickup_lng)
            min_deadhead = min(min_deadhead, d)
            
    return ok, (0.0 if min_deadhead == float("inf") else float(min_deadhead))


def eval_segment_cost(
    tour: List[Employee],
    i: int,
    j: int,
    vehicles: List[Vehicle],
    metadata_kv: Dict[str, str],
    oracle,
    cost_cfg: SplitCostConfig,
    cache: Optional[FeasibilityCache] = None,
    start_time_min: int = 0,
    allow_early_pickup: bool = False,
    allow_late_drop: bool = False,
    infeasible_handling_required: bool = False,
) -> SegmentEval:
    if i > j:
        return SegmentEval(ok=False, reason="bad_indices")

    if cache is not None:
        hit = cache.get(i, j)
        if hit is not None:
            return hit

    group = tour[i:j+1]
    g = len(group)

    Qmax = max(v.capacity for v in vehicles) if vehicles else 0
    if g > Qmax:
        ev = SegmentEval(ok=False, reason="capacity_gt_fleet_max", extra={"group_size": g, "Qmax": Qmax})
        if cache: cache.put(i, j, ev)
        return ev

    p_delay = priority_delay_map(metadata_kv)

    # HARD reachability (relaxed in allow_early_pickup mode)
    ok_reach, min_deadhead_km = reachable_by_any_vehicle(
        group[0], vehicles, oracle, p_delay, allow_early_pickup, allow_late_drop
    )
    
    if not ok_reach:
        ev = SegmentEval(ok=False, reason="no_vehicle_reaches_first_pickup", extra={"first": group[0].employee_id})
        if cache: cache.put(i, j, ev)
        return ev

    avg_speed = sum(v.avg_speed_kmph for v in vehicles) / max(1, len(vehicles))
    
    # Restored optimistic DP simulation: keep start_time_min as 0 to encourage grouping
    office_arrival, dist_km, time_min, dbg = simulate_segment_to_office(
        emps=group,
        oracle=oracle,
        speed_kmph=avg_speed,
        start_time_min=start_time_min,
    )

    # HARD latest_drop + priority delay (or SOFT with high penalty if allow_late_drop)
    late_drop_penalty = 0.0
    for e in group:
        latest = hhmm_to_min(e.latest_drop)
        allow = int(p_delay.get(int(e.priority), 0))
        if office_arrival > latest + allow:
            if not allow_late_drop:
                # Hard constraint violation
                ev = SegmentEval(
                    ok=False,
                    reason="latest_drop_priority_violation",
                    office_arrival_min=office_arrival,
                    extra={"employee_id": e.employee_id, "priority": e.priority, "latest": latest, "allow": allow},
                )
                if cache: cache.put(i, j, ev)
                return ev
            else:
                # Soft constraint with very high penalty
                delay_minutes = office_arrival - (latest + allow)
                late_drop_penalty += 1000.0 * delay_minutes

    # HARD Tmax optional
    if cost_cfg.Tmax is not None:
        duration = office_arrival - start_time_min
        if duration > cost_cfg.Tmax:
            ev = SegmentEval(ok=False, reason="tmax_violation", office_arrival_min=office_arrival,
                            extra={"duration": duration, "Tmax": cost_cfg.Tmax})
            if cache: cache.put(i, j, ev)
            return ev

    # base objective
    base = cost_cfg.w_dist * dist_km + cost_cfg.w_time * time_min

    # SOFT sharing penalty
    share_units = 0.0
    for e in group:
        lim = share_limit(e.sharing_preference)
        if g > lim:
            share_units += (g - lim)
    share_pen = cost_cfg.w_share * share_units

    # SOFT vehicle preference penalty (premium requested)
    premium_cnt = sum(1 for e in group if str(e.vehicle_preference).lower() == "premium")
    veh_pen = cost_cfg.w_vehicle_pref * premium_cnt

    if infeasible_handling_required:
        premium_mismatch_pen = premium_capacity_mismatch_penalty(group, vehicles, cost_cfg.w_vehicle_pref)
    else:
        premium_mismatch_pen = 0.0

    # SOFT fleet scarcity penalty
    scarcity_pen = fleet_scarcity_penalty(vehicles, g, cost_cfg.w_fleet_scarcity)

    # SOFT deadhead proxy penalty
    deadhead_pen = cost_cfg.w_deadhead_proxy * min_deadhead_km

    total = base + share_pen + veh_pen + premium_mismatch_pen + scarcity_pen + deadhead_pen + late_drop_penalty

    ev = SegmentEval(
        ok=True,
        reason="ok",
        office_arrival_min=office_arrival,
        total_dist_km=dist_km,
        total_time_min=time_min,
        group_size=g,
        base_cost=base,
        total_cost=total,
        extra={
            "share_units": share_units,
            "premium_cnt": premium_cnt,
            "premium_mismatch_pen": premium_mismatch_pen,
            "scarcity_pen": scarcity_pen,
            "min_deadhead_km": min_deadhead_km,
            "deadhead_pen": deadhead_pen,
            "late_drop_penalty": late_drop_penalty,
            "debug": dbg,
        },
    )
    if cache:
        cache.put(i, j, ev)
    return ev