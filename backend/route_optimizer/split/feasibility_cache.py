# route_optimizer/split/feasibility_cache.py
from __future__ import annotations
from typing import Dict, Tuple, Optional
from route_optimizer.data_models.types import SegmentEval


class FeasibilityCache:
    def __init__(self):
        self._cache: Dict[Tuple[int, int], SegmentEval] = {}

    def get(self, i: int, j: int) -> Optional[SegmentEval]:
        return self._cache.get((i, j))

    def put(self, i: int, j: int, ev: SegmentEval) -> None:
        self._cache[(i, j)] = ev
