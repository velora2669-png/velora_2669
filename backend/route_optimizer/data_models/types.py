# route_optimizer/data_models/types.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Optional, Any


@dataclass(frozen=True)
class Employee:
    employee_id: str
    priority: int
    pickup_lat: float
    pickup_lng: float
    drop_lat: float
    drop_lng: float
    earliest_pickup: str      # "HH:MM"
    latest_drop: str          # "HH:MM"
    vehicle_preference: str   # "premium"|"normal"|"any"
    sharing_preference: str   # "single"|"double"|"triple"|"any"


@dataclass(frozen=True)
class Vehicle:
    vehicle_id: str
    capacity: int
    cost_per_km: float
    avg_speed_kmph: float
    current_lat: float
    current_lng: float
    available_from: str       # "HH:MM"
    category: str             # "premium"|"normal"


@dataclass(frozen=True)
class SegmentEval:
    ok: bool
    reason: str
    office_arrival_min: int = 0
    total_dist_km: float = 0.0
    total_time_min: float = 0.0
    group_size: int = 0
    base_cost: float = 0.0
    total_cost: float = 0.0
    extra: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class Trip:
    trip_id: str
    employee_ids: List[str]
    group_size: int
    office_arrival_min: int
    cost: float
    meta: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class ScheduleItem:
    vehicle_id: str
    trip_id: str
    employee_ids: List[str]
    depart_min: int
    office_arrival_min: int
    deadhead_km: float
    trip_dist_km: float
    cost: float


@dataclass(frozen=True)
class Solution:
    trips: List[Trip]
    schedule: List[ScheduleItem]
    total_cost: float
    meta: Optional[Dict[str, Any]] = None
