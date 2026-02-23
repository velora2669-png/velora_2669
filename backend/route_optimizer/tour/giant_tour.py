# split_original/tour/giant_tour.py
from __future__ import annotations
import logging
import random
import numpy as np
import pandas as pd
from typing import List, Dict, Optional
from dataclasses import dataclass, field

from route_optimizer.data_models.types import Employee
from route_optimizer.tour.clustering import cluster_employees, ClusteringConfig, Cluster
from route_optimizer.tour.regret_insertion import RegretInsertionBuilder, RegretConfig, Depot, time_to_min

logger = logging.getLogger(__name__)

@dataclass
class GiantTourConfig:
    seed: int = 1337
    clustering: ClusteringConfig = field(default_factory=ClusteringConfig)
    regret: RegretConfig = field(default_factory=RegretConfig)
    order_clusters_by_timeband: bool = True
    perturb_strength: int = 0

class GiantTourBuilder:
    def __init__(self, oracle, employees: List[Employee], office_lat: float, office_lng: float):
        """
        Dynamically builds the required NumPy matrices directly from the DistanceMatrixOracle
        to bypass Pandas indexing slowness entirely.
        """
        self.oracle = oracle
        self.coord_to_idx = {}
        self.idx_to_coord = {}
        
        # Build coordinates registry
        idx = 0
        depot_key = f"{office_lat:.6f},{office_lng:.6f}"
        self.coord_to_idx[depot_key] = idx
        self.idx_to_coord[idx] = (office_lat, office_lng)
        idx += 1
        
        for emp in employees:
            k = f"{emp.pickup_lat:.6f},{emp.pickup_lng:.6f}"
            if k not in self.coord_to_idx:
                self.coord_to_idx[k] = idx
                self.idx_to_coord[idx] = (emp.pickup_lat, emp.pickup_lng)
                idx += 1
                
        # Generate raw NumPy O(1) Arrays
        n = len(self.coord_to_idx)
        self.dist_np = np.zeros((n, n), dtype=float)
        self.time_np = np.zeros((n, n), dtype=float)
        
        for i in range(n):
            lat1, lng1 = self.idx_to_coord[i]
            for j in range(n):
                if i == j: continue
                lat2, lng2 = self.idx_to_coord[j]
                self.dist_np[i, j] = oracle.dist_km(lat1, lng1, lat2, lng2)
                self.time_np[i, j] = oracle.time_min(lat1, lng1, lat2, lng2)

        self.regret_builder = RegretInsertionBuilder(self.dist_np, self.time_np)

    def _get_matrix_index(self, lat: float, lng: float) -> int:
        key = f"{lat:.6f},{lng:.6f}"
        return self.coord_to_idx.get(key, -1)

    def build(self, employees: List[Employee], depot: Depot, config: Optional[GiantTourConfig] = None) -> List[str]:
        if config is None:
            config = GiantTourConfig()

        if not employees:
            return [depot.id, depot.id]

        emp_id_to_idx = {}
        depot_idx = self._get_matrix_index(depot.lat, depot.lng)

        valid_employees = []
        for emp in employees:
            idx = self._get_matrix_index(emp.pickup_lat, emp.pickup_lng)
            if idx != -1:
                emp_id_to_idx[emp.employee_id] = idx
                valid_employees.append(emp)

        emp_data = []
        for e in valid_employees:
            emp_data.append({
                'employee_id': e.employee_id,
                'pickup_lat': e.pickup_lat,
                'pickup_lng': e.pickup_lng,
                'priority': e.priority,
                'earliest_pickup_min': time_to_min(e.earliest_pickup),
                'latest_drop_min': time_to_min(e.latest_drop)
            })
        employees_df = pd.DataFrame(emp_data)

        clusters: List[Cluster] = cluster_employees(
            employees_df, 
            dist_km_mat=self.dist_np, 
            time_min_mat=self.time_np, 
            emp_id_to_idx=emp_id_to_idx, 
            depot_index=depot_idx,
            cfg=config.clustering
        )

        if config.order_clusters_by_timeband:
            clusters.sort(key=lambda c: (c.band_start_min, c.centroid_lat, c.centroid_lng))
        else:
            clusters.sort(key=lambda c: (c.centroid_lat, c.centroid_lng))

        giant_tour_ids = [depot.id]
        emp_map = {e.employee_id: e for e in valid_employees}

        for cl in clusters:
            if cl.members.empty: continue
            cluster_emps = [emp_map[eid] for eid in cl.members['employee_id'] if eid in emp_map]

            sub_tour_ids = self.regret_builder.build_tour(
                cluster_emps, depot, emp_id_to_idx, depot_idx, config.regret
            )
            
            if len(sub_tour_ids) > 2:
                giant_tour_ids.extend(sub_tour_ids[1:-1])

        giant_tour_ids.append(depot.id)

        if config.perturb_strength > 0:
            giant_tour_ids = self._perturb_tour(giant_tour_ids, config.perturb_strength)

        return giant_tour_ids

    def _perturb_tour(self, tour_ids: List[str], strength: int) -> List[str]:
        n = len(tour_ids)
        if n < 4: return tour_ids
        new_tour = tour_ids[:]
        inner_indices = list(range(1, n - 1))
        for _ in range(strength):
            if len(inner_indices) < 2: break
            idx1, idx2 = random.sample(inner_indices, 2)
            new_tour[idx1], new_tour[idx2] = new_tour[idx2], new_tour[idx1]
        return new_tour