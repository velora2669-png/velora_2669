# route_optimizer/constraints/time_windows.py
from __future__ import annotations
from typing import Dict


def hhmm_to_min(s: str) -> int:
    s = str(s).strip()
    parts = s.split(":")
    h = int(parts[0])
    m = int(parts[1])
    return h * 60 + m


def priority_delay_map(metadata_kv: Dict[str, str]) -> Dict[int, int]:
    return {
        1: int(metadata_kv.get("priority_1_max_delay_min", "0")),
        2: int(metadata_kv.get("priority_2_max_delay_min", "0")),
        3: int(metadata_kv.get("priority_3_max_delay_min", "0")),
        4: int(metadata_kv.get("priority_4_max_delay_min", "0")),
        5: int(metadata_kv.get("priority_5_max_delay_min", "0")),
    }
