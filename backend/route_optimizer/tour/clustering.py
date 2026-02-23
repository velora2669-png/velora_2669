# split_original/tour/clustering.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import numpy as np
import pandas as pd

from route_optimizer.data_models.types import Employee

@dataclass
class ClusteringConfig:
    max_clusters: int = 10
    min_employees_for_multiple_clusters: int = 20
    geo_seed_radius_km: float = 4.0
    min_time_overlap_min: int = 10
    max_time_band_width_min: int = 45
    time_band_merge_slack_min: int = 5
    seed: int = 1337

    def calculate_target_cluster_size(self, n_employees: int) -> int:
        if n_employees <= self.min_employees_for_multiple_clusters:
            return n_employees
        return max(n_employees // self.max_clusters, 1)

@dataclass
class TimeBand:
    start_min: int
    end_min: int
    members: pd.DataFrame

    def width(self) -> int:
        return max(0, self.end_min - self.start_min)

    def overlaps(self, other: "TimeBand", min_overlap: int) -> bool:
        s = max(self.start_min, other.start_min)
        e = min(self.end_min, other.end_min)
        return (e - s) >= min_overlap

    def merge(self, other: "TimeBand") -> "TimeBand":
        s = max(self.start_min, other.start_min)
        e = min(self.end_min, other.end_min)
        return TimeBand(start_min=s, end_min=e, members=pd.concat([self.members, other.members]))

@dataclass
class Cluster:
    cluster_id: str
    members: pd.DataFrame
    centroid_lat: float
    centroid_lng: float
    band_start_min: int
    band_end_min: int

def latest_feasible_pickup_min(emp_series: pd.Series, dist_mat: np.ndarray, emp_idx: int, depot_idx: int) -> int:
    # Uses raw numpy lookup
    t_to_office = dist_mat[emp_idx, depot_idx]
    return int(emp_series['latest_drop_min'] - t_to_office)

def pickup_band(emp_series: pd.Series, dist_mat: np.ndarray, emp_idx: int, depot_idx: int) -> Tuple[int, int]:
    ep = int(emp_series['earliest_pickup_min'])
    lp = latest_feasible_pickup_min(emp_series, dist_mat, emp_idx, depot_idx)
    return ep, lp

def band_overlap_minutes(a: Tuple[int, int], b: Tuple[int, int]) -> int:
    return min(a[1], b[1]) - max(a[0], b[0])

def _centroid(members: pd.DataFrame) -> Tuple[float, float]:
    if members.empty: return 0.0, 0.0
    return float(members['pickup_lat'].mean()), float(members['pickup_lng'].mean())

def geographic_clusters(employees_df: pd.DataFrame, emp_id_to_idx: Dict[str, int], dist_km_mat: np.ndarray, cfg: ClusteringConfig) -> List[pd.DataFrame]:
    if employees_df.empty: return []
    target_cluster_size = cfg.calculate_target_cluster_size(len(employees_df))
    remaining_df = employees_df.sort_values(by=['pickup_lat', 'pickup_lng', 'employee_id']).copy()
    clusters = []

    while not remaining_df.empty:
        seed_row = remaining_df.iloc[0]
        remaining_df = remaining_df.iloc[1:]
        current_cluster_rows = [seed_row]
        
        if remaining_df.empty:
            clusters.append(pd.DataFrame(current_cluster_rows))
            break

        seed_i = emp_id_to_idx[seed_row['employee_id']]
        rem_indices = [emp_id_to_idx[eid] for eid in remaining_df['employee_id']]
        
        # Fast NumPy lookup
        seed_dists = dist_km_mat[seed_i, rem_indices].astype(float)
        order = np.argsort(seed_dists)

        picked_indices = []
        # 1. Radius check
        for pos in order:
            if len(current_cluster_rows) >= target_cluster_size: break
            if seed_dists[pos] <= cfg.geo_seed_radius_km:
                picked_indices.append(pos)
        
        # 2. Fill
        if len(picked_indices) < (target_cluster_size - 1):
            for pos in order:
                if len(current_cluster_rows) >= target_cluster_size: break
                if pos not in picked_indices: picked_indices.append(pos)
        
        picked_indices.sort(reverse=True)
        for idx in picked_indices:
             current_cluster_rows.append(remaining_df.iloc[idx])
             
        ids_to_drop = [r['employee_id'] for r in current_cluster_rows[1:]]
        remaining_df = remaining_df[~remaining_df['employee_id'].isin(ids_to_drop)]
        clusters.append(pd.DataFrame(current_cluster_rows))

    return clusters

def _build_time_bands_for_geo_cluster(geo_cluster: pd.DataFrame, dist_mat: np.ndarray, emp_id_to_idx: Dict[str, int], depot_index: int, cfg: ClusteringConfig) -> List[TimeBand]:
    items = []
    for _, row in geo_cluster.iterrows():
        ei = emp_id_to_idx[row['employee_id']]
        ep, lp = pickup_band(row, dist_mat, ei, depot_index)
        items.append({'row': row, 'ep': ep, 'lp': lp, 'priority': row['priority'], 'employee_id': row['employee_id']})
    
    items.sort(key=lambda x: (x['ep'], x['lp'], x['priority'], x['employee_id']))
    bands = []

    for item in items:
        row, ep, lp = item['row'], item['ep'], item['lp']
        emp_df = pd.DataFrame([row])
        placed = False
        for b in bands:
            if band_overlap_minutes((ep, lp), (b.start_min, b.end_min)) >= cfg.min_time_overlap_min:
                b.start_min = max(b.start_min, ep)
                b.end_min = min(b.end_min, lp)
                b.members = pd.concat([b.members, emp_df])
                placed = True
                break
        if not placed:
            bands.append(TimeBand(ep, lp, emp_df))

    merged = []
    for b in bands:
        if not merged: merged.append(b); continue
        prev = merged[-1]
        if prev.overlaps(b, cfg.min_time_overlap_min - cfg.time_band_merge_slack_min):
            merged[-1] = prev.merge(b)
        else:
            merged.append(b)

    final = []
    for b in merged:
        if b.width() <= cfg.max_time_band_width_min or len(b.members) <= 1:
            final.append(b)
        else:
            # Recursive split logic
            final.extend(_build_time_bands_for_geo_cluster(b.members, dist_mat, emp_id_to_idx, depot_index, cfg))
    return final

def cluster_employees(employees_df: pd.DataFrame, dist_km_mat: np.ndarray, time_min_mat: np.ndarray, emp_id_to_idx: Dict[str, int], depot_index: int, cfg: Optional[ClusteringConfig] = None) -> List[Cluster]:
    if cfg is None: cfg = ClusteringConfig()
    geo_dfs = geographic_clusters(employees_df, emp_id_to_idx, dist_km_mat, cfg)
    final_clusters = []
    count = 0
    for g_df in geo_dfs:
        bands = _build_time_bands_for_geo_cluster(g_df, time_min_mat, emp_id_to_idx, depot_index, cfg)
        for b in bands:
            clat, clng = _centroid(b.members)
            final_clusters.append(Cluster(f"C{count:03d}", b.members, clat, clng, b.start_min, b.end_min))
            count += 1
    final_clusters.sort(key=lambda c: (c.centroid_lat, c.centroid_lng, c.band_start_min, c.band_end_min))
    return final_clusters