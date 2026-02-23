# split_original/tour/regret_insertion.py
from __future__ import annotations
import logging
import numpy as np
from typing import List, Dict
from dataclasses import dataclass

from route_optimizer.data_models.types import Employee

logger = logging.getLogger(__name__)

def time_to_min(hhmm: str) -> int:
    """Helper to convert HH:MM to minutes from midnight."""
    parts = hhmm.split(':')
    return int(parts[0]) * 60 + int(parts[1])

@dataclass(frozen=True)
class Depot:
    id: str
    lat: float
    lng: float

@dataclass
class RegretConfig:
    k: int = 2
    priority_factor: float = 0.5
    tightness_factor: float = 2.0

class RegretInsertionBuilder:
    def __init__(self, dist_mat: np.ndarray, time_mat: np.ndarray):
        self.dist_mat = dist_mat
        self.time_mat = time_mat

    def build_tour(
        self, 
        employees: List[Employee], 
        depot: Depot,
        emp_id_to_idx: Dict[str, int],
        depot_idx: int,
        config: RegretConfig
    ) -> List[str]:
        if not employees:
            return [depot.id, depot.id]

        # 1. Time-Based Initialization
        sorted_by_time = sorted(employees, key=lambda x: time_to_min(x.earliest_pickup))
        seed_emp = sorted_by_time[0]
        seed_idx = emp_id_to_idx[seed_emp.employee_id]

        # Initial Tour: Depot -> Seed -> Depot
        tour = [depot_idx, seed_idx, depot_idx]
        
        unassigned = [emp_id_to_idx[e.employee_id] for e in employees if e.employee_id != seed_emp.employee_id]
        idx_to_emp = {emp_id_to_idx[e.employee_id]: e for e in employees}

        # 2. Construction Phase (Regret-K)
        while unassigned:
            best_node = -1
            best_pos = -1
            max_regret = -float('inf')
            
            from_nodes = np.array(tour[:-1])
            to_nodes = np.array(tour[1:])
            current_edge_costs = self.dist_mat[from_nodes, to_nodes]
            
            for u in unassigned:
                cost_increase = (
                    self.dist_mat[from_nodes, u] + 
                    self.dist_mat[u, to_nodes] - 
                    current_edge_costs
                )
                
                k_eff = min(config.k, len(cost_increase))
                sorted_costs = np.sort(cost_increase)
                best_cost = sorted_costs[0]
                
                if k_eff > 1:
                    regret = sorted_costs[k_eff - 1] - best_cost
                else:
                    regret = -best_cost 
                
                emp = idx_to_emp[u]
                mult = 1.0
                mult *= (1.0 + (config.priority_factor / max(1, emp.priority)))
                
                ep_min = time_to_min(emp.earliest_pickup)
                ld_min = time_to_min(emp.latest_drop)
                t_off = self.time_mat[u, depot_idx]
                slack = max(5.0, (ld_min - ep_min) - t_off)
                mult *= (1.0 + (config.tightness_factor / slack))
                
                weighted_regret = regret * mult
                
                if weighted_regret > max_regret:
                    max_regret = weighted_regret
                    best_node = u
                    best_edge_idx = np.where(cost_increase == best_cost)[0][0]
                    best_pos = best_edge_idx + 1

            if best_node != -1:
                tour.insert(best_pos, best_node)
                unassigned.remove(best_node)
            else:
                break
        
        # 3. Optimization Phase (Time-Constrained 2-Opt)
        tour = self._two_opt_constrained(tour, idx_to_emp, depot_idx)

        res_ids = []
        for idx in tour:
            if idx == depot_idx: res_ids.append(depot.id)
            else: res_ids.append(idx_to_emp[idx].employee_id)
        return res_ids

    def _two_opt_constrained(self, tour_indices: List[int], idx_to_emp: Dict[int, Employee], depot_idx: int) -> List[int]:
        best_tour = tour_indices[:]
        improved = True
        n = len(tour_indices)
        max_iter = 50 
        count = 0
        
        while improved and count < max_iter:
            improved = False
            count += 1
            for i in range(1, n - 2):
                for j in range(i + 1, n - 1):
                    if j - i == 1: continue
                    
                    A, B = best_tour[i-1], best_tour[i]
                    C, D = best_tour[j], best_tour[j+1]
                    
                    current_dist = self.dist_mat[A, B] + self.dist_mat[C, D]
                    new_dist = self.dist_mat[A, C] + self.dist_mat[B, D]
                    
                    if new_dist < current_dist:
                        new_tour = best_tour[:]
                        new_tour[i:j+1] = best_tour[i:j+1][::-1]
                        
                        if self._is_feasible(new_tour, idx_to_emp, depot_idx):
                            best_tour = new_tour
                            improved = True
                            
        return best_tour

    def _is_feasible(self, tour: List[int], idx_to_emp: Dict[int, Employee], depot_idx: int) -> bool:
        current_time = 0.0 
        for k in range(1, len(tour) - 1): 
            node_idx = tour[k]
            prev_idx = tour[k-1]
            current_time += self.time_mat[prev_idx, node_idx]
            emp = idx_to_emp[node_idx]
            
            current_time = max(current_time, time_to_min(emp.earliest_pickup))
            time_to_depot = self.time_mat[node_idx, depot_idx]
            arrival_at_office = current_time + time_to_depot
            
            if arrival_at_office > time_to_min(emp.latest_drop):
                return False
        return True