# route_optimizer/split/split_dp.py
from __future__ import annotations
from typing import Dict, List, Tuple
from route_optimizer.data_models.types import Employee, Vehicle, Trip
from split.edge_cost import SplitCostConfig, eval_segment_cost
from split.feasibility_cache import FeasibilityCache


def split_dp_from_giant_tour(
    giant_tour: List[Employee],
    vehicles: List[Vehicle],
    metadata_kv: Dict[str, str],
    oracle,
    cost_cfg: SplitCostConfig,
    raise_on_infeasible: bool = True,
    allow_early_pickup: bool = False,
    allow_late_drop: bool = False,
    infeasible_handling_required: bool = False,
) -> Tuple[List[Trip], float]:
    n = len(giant_tour)
    V = [float("inf")] * (n + 1)
    prev = [-1] * (n + 1)

    # Disable cache when using allow_early_pickup or allow_late_drop to avoid stale results
    cache = FeasibilityCache() if (
        not allow_early_pickup and not allow_late_drop) else None
    V[0] = 0.0

    for j in range(1, n + 1):
        best_val = float("inf")
        best_i = -1

        for i in range(j - 1, -1, -1):
            seg = eval_segment_cost(
                tour=giant_tour,
                i=i,
                j=j - 1,
                vehicles=vehicles,
                metadata_kv=metadata_kv,
                oracle=oracle,
                cost_cfg=cost_cfg,
                cache=cache,
                allow_early_pickup=allow_early_pickup,
                allow_late_drop=allow_late_drop,
                infeasible_handling_required=infeasible_handling_required,
            )
            if not seg.ok:
                continue
            cand = V[i] + seg.total_cost
            if cand < best_val:
                best_val = cand
                best_i = i

        if best_i == -1:
            if raise_on_infeasible:
                raise RuntimeError(
                    f"No feasible split ending at {j-1} ({giant_tour[j-1].employee_id})")
            else:
                # Return partial result for infeasible handling
                return [], float('inf')

        V[j] = best_val
        prev[j] = best_i

    # reconstruct
    trips: List[Trip] = []
    j = n
    tcount = 0
    while j > 0:
        i = prev[j]
        seg = eval_segment_cost(
            tour=giant_tour, i=i, j=j-1,
            vehicles=vehicles, metadata_kv=metadata_kv,
            oracle=oracle, cost_cfg=cost_cfg, cache=None,
            allow_early_pickup=allow_early_pickup,
            allow_late_drop=allow_late_drop,
            infeasible_handling_required=infeasible_handling_required,
        )
        tcount += 1
        emp_ids = [giant_tour[k].employee_id for k in range(i, j)]
        trips.append(Trip(
            trip_id=f"T{tcount:02d}",
            employee_ids=emp_ids,
            group_size=seg.group_size,
            office_arrival_min=seg.office_arrival_min,
            cost=seg.total_cost,
            meta=seg.extra,
        ))
        j = i

    trips.reverse()

    # Renumber trip_id in chronological order (T01, T02, ...)
    renumbered: List[Trip] = []
    for idx, tr in enumerate(trips, start=1):
        renumbered.append(Trip(
            trip_id=f"T{idx:02d}",
            employee_ids=tr.employee_ids,
            group_size=tr.group_size,
            office_arrival_min=tr.office_arrival_min,
            cost=tr.cost,
            meta=tr.meta,
        ))
    trips = renumbered

    return trips, V[n]
