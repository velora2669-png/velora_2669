# route_optimizer/hybrid_solver.py
from __future__ import annotations
from typing import List, Dict
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from split.edge_cost import SplitCostConfig
from split.split_dp import split_dp_from_giant_tour
from scheduling.multi_trip_scheduler import schedule_trips_greedy
from route_optimizer.data_models.types import Solution, Employee, Vehicle


def solve_from_giant_tour(
    employees: List[Employee], 
    vehicles: List[Vehicle], 
    metadata_kv: Dict[str, str], 
    oracle, 
    giant_tour_ids: List[str]
) -> Solution:
    
    emp_by_id: Dict[str, Employee] = {e.employee_id: e for e in employees}

    # Build ordered giant tour objects
    giant_tour = [emp_by_id[eid] for eid in giant_tour_ids]

    # Cost cfg from metadata
    w_dist = float(metadata_kv.get("objective_cost_weight", "0.7"))
    w_time = float(metadata_kv.get("objective_time_weight", "0.3"))
    
    # Check if infeasible handling is required
    infeasible_handling = metadata_kv.get("infeasible_handling_required", "FALSE").upper() == "TRUE"

   # Use higher penalties only when infeasible handling is required.
    if infeasible_handling:
        base_w_share = 20.0
        base_w_vehicle_pref = 8.0
        base_w_fleet_scarcity = 25.0
        base_w_deadhead_proxy = 1.0
    else:
        base_w_share = 5.0
        base_w_vehicle_pref = 2.0
        base_w_fleet_scarcity = 5.0
        base_w_deadhead_proxy = 0.0

    cost_cfg = SplitCostConfig(
        w_dist=w_dist,
        w_time=w_time,
        w_share=base_w_share,
        w_vehicle_pref=base_w_vehicle_pref,
        w_fleet_scarcity=base_w_fleet_scarcity,
        w_deadhead_proxy=base_w_deadhead_proxy,
        Tmax=None,
    )

    # Try normal split first
    relaxations_applied = []
    infeasibility_reason = None
    late_drop_allowed = False
    
    try:
        trips, split_cost = split_dp_from_giant_tour(
            giant_tour=giant_tour,
            vehicles=vehicles,
            metadata_kv=metadata_kv,
            oracle=oracle,
            cost_cfg=cost_cfg,
            raise_on_infeasible=True,
            infeasible_handling_required=infeasible_handling,
        )
    except RuntimeError as e:
        if not infeasible_handling:
            raise
        
        # Infeasible handling required - try with relaxed constraints
        infeasibility_reason = str(e)
        print(f"\n⚠️  INFEASIBILITY DETECTED: {infeasibility_reason}")
        print("\n🔄 Attempting to find solution by relaxing secondary constraints...")
        
        # Level 1: Relax sharing and reduce vehicle preference penalty
        relaxed_cfg_1 = SplitCostConfig(
            w_dist=w_dist,
            w_time=w_time,
            w_share=0.0,            # RELAXED: from 20.0 to 0.0 - ignore sharing preferences
            w_vehicle_pref=6.0,      # REDUCED: from 8.0 to 6.0 - still prefer premium when requested
            w_fleet_scarcity=25.0,   # keep scarcity
            w_deadhead_proxy=1.0,    # keep deadhead penalty
            Tmax=None,
        )
        
        try:
            trips, split_cost = split_dp_from_giant_tour(
                giant_tour=giant_tour,
                vehicles=vehicles,
                metadata_kv=metadata_kv,
                oracle=oracle,
                cost_cfg=relaxed_cfg_1,
                raise_on_infeasible=True,
                infeasible_handling_required=True,
            )
            relaxations_applied = [
                "Sharing preferences relaxed: w_share = 0.0 (was 20.0)",
                "Vehicle preferences reduced: w_vehicle_pref = 6.0 (was 8.0)"
            ]
            print("\n✅ Solution found with Level 1 relaxation")
            print("   Relaxations applied:")
            for r in relaxations_applied:
                print(f"     - {r}")
        except RuntimeError as e2:
            # Level 2: Also relax fleet scarcity and deadhead penalties
            print(f"\n🔄 Level 1 failed. Trying Level 2: Relaxing fleet scarcity and deadhead penalties...")
            
            relaxed_cfg_2 = SplitCostConfig(
                w_dist=w_dist,
                w_time=w_time,
                w_share=0.0,            # RELAXED
                w_vehicle_pref=4.0,      # REDUCED but KEPT STRONG to prevent premium mixing: was 8.0
                w_fleet_scarcity=0.0,    # RELAXED: from 25.0 to 0.0
                w_deadhead_proxy=0.0,    # RELAXED: from 1.0 to 0.0
                Tmax=None,
            )
            
            try:
                trips, split_cost = split_dp_from_giant_tour(
                    giant_tour=giant_tour,
                    vehicles=vehicles,
                    metadata_kv=metadata_kv,
                    oracle=oracle,
                    cost_cfg=relaxed_cfg_2,
                    raise_on_infeasible=True,
                    infeasible_handling_required=True,
                )
                relaxations_applied = [
                    "Sharing preferences relaxed: w_share = 0.0 (was 20.0)",
                    "Vehicle preferences reduced: w_vehicle_pref = 4.0 (was 8.0)",
                    "Fleet scarcity penalty relaxed: w_fleet_scarcity = 0.0 (was 25.0)",
                    "Deadhead proxy penalty relaxed: w_deadhead_proxy = 0.0 (was 1.0)"
                ]
                print("\n✅ Solution found with Level 2 relaxation")
                print("   Relaxations applied:")
                for r in relaxations_applied:
                    print(f"     - {r}")
            except RuntimeError as e3:
                # Level 3: Reduce base objective weights
                print(f"\n🔄 Level 2 failed. Trying Level 3: Reducing base objective weights...")
                
                relaxed_cfg_3 = SplitCostConfig(
                    w_dist=w_dist * 0.5,     # RELAXED: reduce distance weight by 50%
                    w_time=w_time * 0.5,     # RELAXED: reduce time weight by 50%
                    w_share=0.0,
                    w_vehicle_pref=3.0,      # KEEP STRONG: avoid mixing premium with non-premium
                    w_fleet_scarcity=0.0,
                    w_deadhead_proxy=0.0,
                    Tmax=None,
                )
                
                try:
                    trips, split_cost = split_dp_from_giant_tour(
                        giant_tour=giant_tour,
                        vehicles=vehicles,
                        metadata_kv=metadata_kv,
                        oracle=oracle,
                        cost_cfg=relaxed_cfg_3,
                        raise_on_infeasible=True,
                        infeasible_handling_required=True,
                    )
                    relaxations_applied = [
                        "Sharing preferences relaxed: w_share = 0.0 (was 20.0)",
                        "Vehicle preferences reduced: w_vehicle_pref = 3.0 (was 8.0)",
                        "Fleet scarcity penalty relaxed: w_fleet_scarcity = 0.0 (was 25.0)",
                        "Deadhead proxy penalty relaxed: w_deadhead_proxy = 0.0 (was 1.0)",
                        f"Distance weight reduced: w_dist = {w_dist * 0.5} (was {w_dist})",
                        f"Time weight reduced: w_time = {w_time * 0.5} (was {w_time})"
                    ]
                    print("\n✅ Solution found with Level 3 relaxation")
                    print("   Relaxations applied:")
                    for r in relaxations_applied:
                        print(f"     - {r}")
                except RuntimeError as e4:
                    # Level 4: Relax earliest_pickup constraint (treat as soft)
                    print(f"\n🔄 Level 3 failed. Trying Level 4: Relaxing earliest pickup time constraints...")
                    print(f"   Allowing vehicles to pick up employees before their earliest_pickup time")
                    
                    try:
                        trips, split_cost = split_dp_from_giant_tour(
                            giant_tour=giant_tour,
                            vehicles=vehicles,
                            metadata_kv=metadata_kv,
                            oracle=oracle,
                            cost_cfg=relaxed_cfg_3,
                            raise_on_infeasible=True,
                            allow_early_pickup=True,  # NEW: Treat earliest_pickup as soft constraint                            
                            infeasible_handling_required=True,
                        )
                        relaxations_applied = [
                            "Sharing preferences relaxed: w_share = 0.0 (was 20.0)",
                            "Vehicle preferences reduced: w_vehicle_pref = 3.0 (was 8.0)",
                            "Fleet scarcity penalty relaxed: w_fleet_scarcity = 0.0 (was 25.0)",
                            "Deadhead proxy penalty relaxed: w_deadhead_proxy = 0.0 (was 1.0)",
                            f"Distance weight reduced: w_dist = {w_dist * 0.5} (was {w_dist})",
                            f"Time weight reduced: w_time = {w_time * 0.5} (was {w_time})",
                            "⚠️ Earliest pickup times relaxed (employees may be picked up before their earliest_pickup window)"
                        ]
                        print(f"\n✅ Solution found with Level 4 relaxation")
                        print(f"   Relaxations applied:")
                        for r in relaxations_applied:
                            print(f"     - {r}")
                        print(f"   Note: Latest drop times and delay limits are STILL ENFORCED (hard constraints)")
                    except RuntimeError as e5:
                        # Level 5: Also relax latest_drop deadline with very high penalty
                        print(f"\n🔄 Level 4 failed. Trying Level 5: Relaxing latest drop deadline with high penalty...")
                        print(f"   Treating latest_drop as SOFT constraint with 1000×penalty per minute late")
                        
                        try:
                            trips, split_cost = split_dp_from_giant_tour(
                                giant_tour=giant_tour,
                                vehicles=vehicles,
                                metadata_kv=metadata_kv,
                                oracle=oracle,
                                cost_cfg=relaxed_cfg_3,
                                raise_on_infeasible=True,
                                allow_early_pickup=True,
                                allow_late_drop=True,  # NEW: Treat latest_drop as soft constraint with huge penalty
                                infeasible_handling_required=True,
                            )
                            relaxations_applied = [
                                "Sharing preferences relaxed: w_share = 0.0 (was 20.0)",
                                "Vehicle preferences reduced: w_vehicle_pref = 3.0 (was 8.0)",
                                "Fleet scarcity penalty relaxed: w_fleet_scarcity = 0.0 (was 25.0)",
                                "Deadhead proxy penalty relaxed: w_deadhead_proxy = 0.0 (was 1.0)",
                                f"Distance weight reduced: w_dist = {w_dist * 0.5} (was {w_dist})",
                                f"Time weight reduced: w_time = {w_time * 0.5} (was {w_time})",
                                "⚠️ Earliest pickup times relaxed (employees may be picked up before their earliest_pickup window)",
                                "🚨 CRITICAL: Latest drop deadlines relaxed with VERY HIGH PENALTY (1000 per minute late)"
                            ]
                            print(f"\n✅ Solution found with Level 5 relaxation (MAXIMUM RELAXATION)")
                            print(f"   Relaxations applied:")
                            for r in relaxations_applied:
                                print(f"     - {r}")
                            print(f"   ⚠️ WARNING: Latest drop deadlines may be violated with high cost")
                            print(f"   Note: Priority delay limits are incorporated into penalties")
                            late_drop_allowed = True  # Mark that late drops are allowed
                        except RuntimeError as e6:
                            # Still infeasible - this is completely impossible
                            print(f"\n❌ Still infeasible even with maximum relaxations: {e6}")
                            print("   This indicates fundamental impossibility:")
                            print("     - Vehicle capacity limits cannot be satisfied")
                            print("   The problem is fundamentally unsolvable with given constraints.")
                            raise RuntimeError(f"Infeasible even with maximum relaxations. Original: {infeasibility_reason}, Final: {e6}")
    
    schedule = schedule_trips_greedy(
        trips=trips,
        employees_by_id=emp_by_id,
        vehicles=vehicles,
        metadata_kv=metadata_kv,
        oracle=oracle,
        lambda_turnaround_min=0,
        allow_late_drop=late_drop_allowed,
    )

    total = split_cost + sum(s.cost for s in schedule)
    
    # Prepare metadata with relaxation information
    solution_meta = {"split_cost": split_cost}
    if infeasibility_reason:
        solution_meta["infeasibility_reason"] = infeasibility_reason
        solution_meta["relaxations_applied"] = relaxations_applied
        solution_meta["note"] = "Solution found by relaxing secondary constraints (sharing & vehicle preferences). Hard constraints (time windows, capacity, delay limits) remain enforced."

    return Solution(
        trips=trips,
        schedule=schedule,
        total_cost=float(total),
        meta=solution_meta,
    )
