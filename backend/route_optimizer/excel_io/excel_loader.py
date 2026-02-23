# route_optimizer/excel_io/excel_loader.py
from __future__ import annotations
import pandas as pd
from typing import Dict, List, Tuple
from route_optimizer.data_models.types import Employee, Vehicle


def load_testcase_xlsx(path: str) -> Tuple[List[Employee], List[Vehicle], Dict[str, str], pd.DataFrame]:
    """
    Reads sheets:
      - employees
      - vehicles
      - metadata (key,value)
      - baseline (optional, returned as df; not needed for split)
    """
    with pd.ExcelFile(path) as xl:

     emp_df = pd.read_excel(xl, "employees")
     veh_df = pd.read_excel(xl, "vehicles")
     meta_df = pd.read_excel(xl, "metadata")
     baseline_df = pd.read_excel(xl, "baseline") if "baseline" in xl.sheet_names else pd.DataFrame()

    # metadata_kv
    metadata_kv: Dict[str, str] = {}
    for _, r in meta_df.iterrows():
        k = str(r["key"]).strip()
        v = str(r["value"]).strip()
        metadata_kv[k] = v

    employees: List[Employee] = []
    for _, r in emp_df.iterrows():
        employees.append(Employee(
            employee_id=str(r["employee_id"]).strip(),
            priority=int(r["priority"]),
            pickup_lat=float(r["pickup_lat"]),
            pickup_lng=float(r["pickup_lng"]),
            drop_lat=float(r["drop_lat"]),
            drop_lng=float(r["drop_lng"]),
            earliest_pickup=str(r["earliest_pickup"]).strip(),
            latest_drop=str(r["latest_drop"]).strip(),
            vehicle_preference=str(r["vehicle_preference"]).strip().lower(),
            sharing_preference=str(r["sharing_preference"]).strip().lower(),
        ))

    vehicles: List[Vehicle] = []
    for _, r in veh_df.iterrows():
        vehicles.append(Vehicle(
            vehicle_id=str(r["vehicle_id"]).strip(),
            capacity=int(r["capacity"]),
            cost_per_km=float(r.get("cost_per_km", 0.0)),
            avg_speed_kmph=float(r.get("avg_speed_kmph", r.get("avg_speed_kmpl", 25.0))),
            current_lat=float(r["current_lat"]),
            current_lng=float(r["current_lng"]),
            available_from=str(r["available_from"]).strip(),
            category=str(r["category"]).strip().lower(),
        ))

    return employees, vehicles, metadata_kv, baseline_df
